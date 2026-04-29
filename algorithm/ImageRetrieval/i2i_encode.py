#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/5/4 下午12:05
# @Author  : CaoQixuan
# @File    : AnalyzeAttentionMapVisual.py
# @Description :

import torch
from PIL import Image
from torch.utils import data
from torchvision import transforms

from models.base_distill.base_distall import Network
from utils import get_options, get_device

base_transform = transforms.Compose([
    transforms.Resize([224, 224]),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])]
)


class ImageEmbedDataset(data.Dataset):
    def __init__(self, path, flag="test", transform=None):
        super(ImageEmbedDataset, self).__init__()
        self.flag = flag
        self.path = path
        self.images = path
        self.length = len(self.images)
        self.transform = self.transform = base_transform if transform is None else transform

    def __getitem__(self, index):
        image_path = self.images[index]

        img_pil = Image.open(image_path).convert('RGB')
        img = self.transform(img_pil)

        return {
            "image": img,
        }

    def __len__(self):
        return self.length


def get_model(ckpt_path):
    opt = get_options("base_distill")
    model = Network(opt)
    state_dict = torch.load(
        ckpt_path
    )
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    model.to(get_device())
    return opt, model


# @torch.no_grad()
# def encode(opt, model, image_paths):
#     image_loader = torch.utils.data.DataLoader(
#         ImageEmbedDataset(image_paths),
#         batch_size=opt["train"]["batch_size"],
#         num_workers=opt["train"]["num_works"],
#         shuffle=False,
#     )
#     image_features = []
#     for data_pair in image_loader:
#         features = model.encode(data_pair)
#         image_features.append(features)
#
#     image_features = torch.cat(image_features, dim=0).cpu()
#
#     return image_features
@torch.no_grad()
def encode(opt, model, image_paths):
    if image_paths is None:
        return []
    if isinstance(image_paths, str):
        image_paths = [image_paths]

    image_paths = [p for p in image_paths if p is not None and str(p).strip() != ""]

    if len(image_paths) == 0:
        return []

    image_loader = torch.utils.data.DataLoader(
        ImageEmbedDataset(image_paths),
        batch_size=opt["train"]["batch_size"],
        num_workers=opt["train"]["num_works"],
        shuffle=False,
    )

    image_features = []
    for data_pair in image_loader:
        features = model.encode(data_pair)
        image_features.append(features)

    if len(image_features) == 0:
        return []

    image_features = torch.cat(image_features, dim=0).cpu()
    return image_features


if __name__ == '__main__':
    image_paths = ["analyze_valid/attention/AID/airport/a_query_airport_224.jpg"]
    ckpt_path = "analyze_valid/base_distill_patchmask/augment_base_distill_float32_NWEP_RESISC45_256_2024-09-21-13-44-39/base_distill_NWEP_RESISC45_256_0.9648.pt"
    opt, model = get_model(ckpt_path=ckpt_path)
    image_features = encode(opt, model, image_paths)
    print(image_features.shape)
