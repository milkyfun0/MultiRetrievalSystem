from typing import Dict

import torch

from .warmup_cosine import LinearWarmupCosineAnnealingLR


def build_scheduler(optimizer, lr_config: Dict):
    schedule_name = lr_config["name"].lower()
    if schedule_name == "constant":
        # scheduler = torch.optim.lr_scheduler.ConstantLR(optimizer, **lr_config["config"])
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=100, gamma=1)

    elif schedule_name == "cosine":
        # lr_config["config"]["warmup_steps"] = lr_config["config"]["warmup_epochs"]
        # lr_config["config"]["total_steps"] = lr_config["config"]["total_epochs"]
        scheduler = LinearWarmupCosineAnnealingLR(optimizer, **lr_config["config"])
    else:
        raise NotImplementedError(f"got not implemented scheduler : {schedule_name}")
    return scheduler
