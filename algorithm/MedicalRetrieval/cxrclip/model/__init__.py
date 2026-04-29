from typing import Dict

from torch import nn
from transformers.tokenization_utils import PreTrainedTokenizer
import torch
from .clip import CXRClip
from .image_classification import CXRClassification


def build_model(model_config: Dict, loss_config: Dict, tokenizer: PreTrainedTokenizer = None) -> nn.Module:
    if model_config["name"].lower() == "clip_custom":
        model = CXRClip(model_config, loss_config, tokenizer)
        # model.load_state_dict(torch.load("/mnt/data/sx1025/Medical/CXR-CLIP/outputs/Ksample4Ratio0.32025-01-29/21-09-16/checkpoints/model-best.tar")["model"])
    elif model_config["name"].lower() == "finetune_classification":
        model_type = model_config["image_encoder"]["model_type"] if "model_type" in model_config["image_encoder"] else "vit"
        model = CXRClassification(model_config, model_type)
    else:
        raise KeyError(f"Not supported model: {model_config['name']}")
    return model
