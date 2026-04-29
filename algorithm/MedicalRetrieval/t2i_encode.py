import ast
from typing import Dict, List
import os

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

import hydra
import torch
from PIL import Image
from omegaconf import DictConfig
from torch.utils.data import default_collate, DataLoader
from torch.utils.data.dataset import Dataset

from cxrclip import convert_dictconfig_to_dict
from cxrclip.data import DataModule
from cxrclip.data.data_utils import load_transform, transform_image
from cxrclip.model import build_model

# 全局变量，用来传递 ckpt_path
CKPT_PATH = ""

# 存储结果，解决 Hydra 不能 return 的问题
HYDRA_RESULT = None


def get_runtime_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _normalize_str_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        raise ValueError("input must be str, list, tuple or null")

    result = []
    for x in items:
        if x is None:
            continue
        s = str(x).strip()
        if s == "":
            continue
        result.append(s)
    return result


class ImageEmbedDataset(Dataset):
    def __init__(
            self,
            name: str,
            data_path: list,
            split: str = None,
            data_frac: float = 1.0,
            tokenizer=None,
            text_max_length: int = 150,
            transform_config: Dict = None,
            normalize: str = "huggingface",
            **kwargs
    ):
        super().__init__()
        self.name = name
        self.text_max_length = text_max_length
        self.image_transforms = load_transform(split="test", transform_config=transform_config)
        self.normalize = normalize
        self.data = data_path

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        image_path = self.data[index]
        if image_path.startswith("["):
            image_path = ast.literal_eval(image_path)[0]

        image = Image.open(image_path).convert("RGB")
        image = transform_image(self.image_transforms, image, normalize=self.normalize)
        return {"images": image, "image_path": image_path}

    @staticmethod
    def collate_fn(instances: List):
        collate = default_collate(instances)
        collate["image_paths"] = [ins["image_path"] for ins in instances]
        return collate


class TextEmbedDataset(Dataset):
    def __init__(
            self,
            name: str,
            data_path: list,
            split: str = None,
            data_frac: float = 1.0,
            tokenizer=None,
            text_max_length: int = 150,
            transform_config: Dict = None,
            normalize: str = "huggingface",
            **kwargs
    ):
        super().__init__()
        self.name = name
        self.tokenizer = tokenizer
        self.text_max_length = text_max_length
        self.data = data_path

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return {"text": self.data[index]}

    def collate_fn(self, instances: List):
        collate = default_collate(instances)
        text_tokens = self.tokenizer(
            collate["text"],
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            max_length=self.text_max_length,
        )
        collate["text_tokens"] = text_tokens
        collate["texts"] = [ins["text"] for ins in instances]
        return collate


def inference_dataloader(dataloader_config, transform_config, tokenizer, text, image_path):
    text_dataset = TextEmbedDataset(
        "text_dataset",
        text,
        transform_config=transform_config,
        tokenizer=tokenizer,
    )
    text_dataloader = DataLoader(
        text_dataset,
        collate_fn=text_dataset.collate_fn,
        **dataloader_config["test"]
    )

    image_dataset = ImageEmbedDataset(
        "image_dataset",
        image_path,
        transform_config=transform_config,
    )
    image_dataloader = DataLoader(
        image_dataset,
        collate_fn=ImageEmbedDataset.collate_fn,
        **dataloader_config["test"]
    )
    return text_dataloader, image_dataloader


def load_model_weights(model, ckpt_path: str):
    ckpt = torch.load(ckpt_path, map_location="cpu")

    if "model" not in ckpt:
        raise KeyError(f"'model' not found in checkpoint, available keys: {list(ckpt.keys())}")

    state_dict = ckpt["model"]

    # 去掉 module. 前缀
    if isinstance(state_dict, dict) and len(state_dict) > 0:
        if all(k.startswith("module.") for k in state_dict.keys()):
            state_dict = {k[len("module."):]: v for k, v in state_dict.items()}

    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    print("missing keys:", missing)
    print("unexpected keys:", unexpected)


def build_model_and_cfg(cfg: DictConfig):
    global CKPT_PATH
    cfg.model.mask_ratio = 0.5
    cfg.model.k_sample = 2
    cfg = convert_dictconfig_to_dict(cfg)

    data_config = {}
    if "data_train" in cfg:
        data_config["train"] = cfg["data_train"]
    if "data_valid" in cfg:
        data_config["valid"] = cfg["data_valid"]
    if "data_test" in cfg:
        data_config["test"] = cfg["data_test"]

    if cfg["model"]["image_encoder"]["name"] == "resnet":
        for _split in data_config:
            for _dataset in data_config[_split]:
                data_config[_split][_dataset]["normalize"] = "imagenet"

    datamodule = DataModule(
        data_config=data_config,
        dataloader_config=cfg["dataloader"],
        tokenizer_config=cfg.get("tokenizer"),
        loss_config=cfg["loss"],
        transform_config=cfg["transform"],
    )
    model = build_model(cfg["model"], cfg["loss"], datamodule.tokenizer)

    # 加载权重
    # if CKPT_PATH:
    # ckpt = torch.load(CKPT_PATH, map_location="cpu")
    # print(ckpt["state_dict"])
    # model.load_state_dict(ckpt["state_dict"])
    if CKPT_PATH:
        load_model_weights(model, CKPT_PATH)

    device = get_runtime_device()
    model.to(device).eval()

    return cfg, model, datamodule.tokenizer


@hydra.main(version_base=None, config_path="configs", config_name="train")
def main(cfg: DictConfig):
    global HYDRA_RESULT
    HYDRA_RESULT = build_model_and_cfg(cfg)


@torch.no_grad()
def encode(cfg, text, image_path, model, tokenizer):
    device = next(model.parameters()).device

    text = _normalize_str_list(text)
    image_path = _normalize_str_list(image_path)

    text_feats = []
    img_feats = []

    if len(text) > 0:
        text_dataset = TextEmbedDataset(
            name="text_dataset",
            data_path=text,
            transform_config=cfg["transform"],
            tokenizer=tokenizer,
        )
        text_dataloader = DataLoader(
            text_dataset,
            collate_fn=text_dataset.collate_fn,
            **cfg["dataloader"]["test"]
        )

        for b in text_dataloader:
            text_tokens = {
                k: v.to(device, non_blocking=True)
                for k, v in b["text_tokens"].items()
            }
            feat, _, _ = model.encode_text(text_tokens)
            text_feats.append(feat.detach().cpu())

    if len(image_path) > 0:
        image_dataset = ImageEmbedDataset(
            name="image_dataset",
            data_path=image_path,
            transform_config=cfg["transform"],
        )
        image_dataloader = DataLoader(
            image_dataset,
            collate_fn=ImageEmbedDataset.collate_fn,
            **cfg["dataloader"]["test"]
        )

        for b in image_dataloader:
            feat, _ = model.encode_image(
                b["images"].to(device, non_blocking=True)
            )
            img_feats.append(feat.detach().cpu())

    text_feats = torch.cat(text_feats, dim=0) if len(text_feats) > 0 else []
    img_feats = torch.cat(img_feats, dim=0) if len(img_feats) > 0 else []

    return text_feats, img_feats


if __name__ == "__main__":
    # CKPT_PATH = "path/to/model-best.tar"
    text_input = ["hello world"]
    image_input = ["baseline/original_image.jpg"]

    main()
    cfg, model, tokenizer = HYDRA_RESULT
    text_feats, img_feats = encode(cfg, text_input, image_input, model, tokenizer)

    if isinstance(text_feats, list):
        print("text_feats: []")
    else:
        print("text_feats:", text_feats.shape)

    if isinstance(img_feats, list):
        print("img_feats: []")
    else:
        print("img_feats:", img_feats.shape)
