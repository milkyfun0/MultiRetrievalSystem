import os
import sys

proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '././'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

import torch
from torch.utils.data import DataLoader
from transformers import CLIPTokenizerFast

from src.modeling.VidCLIP import VidCLIP
from src.datasets.dataset_video_retrieval import (
    HDVILAVideoRetrievalDataset,
    VideoRetrievalCollator,
    VideoEmbedDataset,
    VideoEmbedCollator,
    TextEmbedDataset,
    TextEmbedCollator,
)
from src.datasets.dataloader import PrefetchLoader
from src.configs.config import shared_configs
from src.utils.misc import set_random_seed
from src.utils.logger import LOGGER, TB_LOGGER
from src.utils.load_save import load_state_dict_with_mismatch
from src.utils.distributed import AllGather
from src.utils.metrics import cal_cossim, compute_metrics, np_softmax

allgather = AllGather.apply


def get_runtime_device(local_rank: int = 0):
    if torch.cuda.is_available():
        return torch.device(f"cuda:{local_rank}")
    return torch.device("cpu")


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


def init_device(args, local_rank):
    device = get_runtime_device(local_rank)

    if torch.cuda.is_available():
        n_gpu = torch.cuda.device_count()
        try:
            torch.cuda.set_device(local_rank)
        except Exception:
            pass
    else:
        n_gpu = 0

    LOGGER.info("device: {} n_gpu: {}".format(device, n_gpu))
    args.n_gpu = n_gpu
    return device, n_gpu


def mk_text_dataloader(dataset_name, vis_format, anno_path, vis_dir, cfg, tokenizer, mode):
    is_train = mode == "train"
    dataset = TextEmbedDataset(
        cfg=cfg,
        vis_dir=vis_dir,
        anno_path=anno_path,
        vis_format=vis_format,
        mode=mode
    )

    batch_size = cfg.train_batch_size if is_train else cfg.test_batch_size
    vret_collator = TextEmbedCollator(
        tokenizer=tokenizer, max_length=cfg.max_txt_len, is_train=is_train
    )
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=cfg.n_workers,
        pin_memory=cfg.pin_mem,
        collate_fn=vret_collator.collate_batch
    )
    return dataloader


def mk_video_dataloader(dataset_name, vis_format, anno_path, vis_dir, cfg, tokenizer, mode):
    is_train = mode == "train"
    dataset = VideoEmbedDataset(
        cfg=cfg,
        vis_dir=vis_dir,
        anno_path=anno_path,
        vis_format=vis_format,
        mode=mode
    )

    batch_size = cfg.train_batch_size if is_train else cfg.test_batch_size
    vret_collator = VideoEmbedCollator(
        tokenizer=tokenizer, max_length=cfg.max_txt_len, is_train=is_train
    )
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=cfg.n_workers,
        pin_memory=cfg.pin_mem,
        collate_fn=vret_collator.collate_batch
    )
    return dataloader


def setup_dataloaders(cfg, tokenizer, texts, video_paths):
    LOGGER.info("Init. train_loader and val_loader.")

    video_dataloader = mk_video_dataloader(
        dataset_name="video_dataloader",
        vis_format="video",
        anno_path=None,
        vis_dir=video_paths,
        cfg=cfg,
        tokenizer=tokenizer,
        mode="test"
    )
    text_dataloader = mk_text_dataloader(
        dataset_name="text_dataloader",
        vis_format="video",
        anno_path=texts,
        vis_dir=None,
        cfg=cfg,
        tokenizer=tokenizer,
        mode="test"
    )
    return text_dataloader, video_dataloader


def setup_model(cfg, device=None):
    LOGGER.info("Setup model.")

    model = VidCLIP(cfg)

    if cfg.e2e_weights_path:
        LOGGER.info(f"Loading e2e weights from {cfg.e2e_weights_path}")
        load_state_dict_with_mismatch(model, cfg.e2e_weights_path)

    if hasattr(cfg, "overload_logit_scale"):
        model.overload_logit_scale(cfg.overload_logit_scale)

    model.to(device)

    LOGGER.info("Setup model done!")
    return model


def get_model(ckpt_path):
    cfg = shared_configs.get_pretraining_args()
    set_random_seed(cfg.seed)
    cfg.e2e_weights_path = ckpt_path

    device, n_gpu = init_device(cfg, 0)
    cfg.n_gpu = n_gpu
    cfg.world_size = n_gpu

    model = setup_model(cfg, device=device)
    tokenizer = CLIPTokenizerFast.from_pretrained(cfg.clip_weights)
    model.eval()
    return cfg, model, tokenizer


@torch.no_grad()
def encode(cfg, texts, video_paths, model, tokenizer):
    device = next(model.parameters()).device

    texts = _normalize_str_list(texts)
    video_paths = _normalize_str_list(video_paths)

    text_features = []
    video_features = []

    if len(texts) > 0:
        text_dataloader = mk_text_dataloader(
            dataset_name="text_dataloader",
            vis_format="video",
            anno_path=texts,
            vis_dir=None,
            cfg=cfg,
            tokenizer=tokenizer,
            mode="test"
        )

        for text_batch in text_dataloader:
            text_input_ids = text_batch["text_input_ids"].to(device, non_blocking=True)
            text_input_mask = text_batch["text_input_mask"].to(device, non_blocking=True)

            text_feature = model.forward_text(
                text_input_ids=text_input_ids,
                text_input_mask=text_input_mask,
            )
            text_features.append(text_feature.detach().cpu())

    if len(video_paths) > 0:
        video_dataloader = mk_video_dataloader(
            dataset_name="video_dataloader",
            vis_format="video",
            anno_path=None,
            vis_dir=video_paths,
            cfg=cfg,
            tokenizer=tokenizer,
            mode="test"
        )

        for video_batch in video_dataloader:
            video = video_batch["video"].to(device, non_blocking=True)
            video_feature = model.forward_video(video)
            video_features.append(video_feature.detach().cpu())

    text_features = torch.cat(text_features, dim=0) if len(text_features) > 0 else []
    video_features = torch.cat(video_features, dim=0) if len(video_features) > 0 else []

    return text_features, video_features


if __name__ == "__main__":
    texts = ["hello world"]
    video_paths = ["analysis/video28/video28.mp4"]
    ckpt_path = "ckpts/model_step_10547.pt"

    cfg, model, tokenizer = get_model(ckpt_path)
    text_features, video_features = encode(cfg, texts, video_paths, model, tokenizer)

    if isinstance(text_features, list):
        print("text_features: []")
    else:
        print("text_features:", text_features.shape)

    if isinstance(video_features, list):
        print("video_features: []")
    else:
        print("video_features:", video_features.shape)