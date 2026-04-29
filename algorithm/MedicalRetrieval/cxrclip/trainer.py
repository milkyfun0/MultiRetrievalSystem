import gc
import logging
import math
import os
import shutil
from typing import Dict

import numpy as np
import torch
import torch.distributed as dist
from omegaconf import OmegaConf
from torch.nn.parallel import DistributedDataParallel as DDP
from tqdm import tqdm

from . import util
from .data import DataModule
from .loss import build_loss
from .model import build_model
from .optimizer import build_optimizer
from .scheduler import build_scheduler

log = logging.getLogger(__name__)


def run(local_rank, cfg: Dict):
    if "tokenizer" in cfg:
        assert (
                cfg["tokenizer"]["pretrained_model_name_or_path"] == cfg["model"]["text_encoder"]["name"]
        ), "tokenizer should be same to text_encoder"

    distributed = local_rank != -1
    if distributed:
        dist.init_process_group(backend="nccl")
        device = torch.device(f"cuda:{local_rank}")
        torch.cuda.set_device(device)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"DistEnv: {util.GlobalEnv.get()}")

    log.info(f"{device}: Load datasets")
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
        tokenizer_config=cfg["tokenizer"] if "tokenizer" in cfg else None,
        loss_config=cfg["loss"],
        transform_config=cfg["transform"],
    )
    train_dataloader, train_sampler = datamodule.train_dataloader(distributed=distributed)
    valid_dataloaders = datamodule.valid_dataloader(distributed=distributed)
    test_dataloaders = datamodule.test_dataloader()

    log.info(f"{device}: Build the model")
    model = build_model(cfg["model"], cfg["loss"], datamodule.tokenizer).cuda()
    model = model.to(device)
    if distributed:
        model = DDP(model, device_ids=[device], find_unused_parameters=True)
    # if util.GlobalEnv.get().master:
    #     log.info(f"{device}: Model info:\n{model}")

    log.info(f"{device}: Build the loss function")
    loss_func = build_loss(cfg["loss"])

    log.info(f"{device}: Build the optimizer")
    optimizer = build_optimizer(model, cfg["optimizer"])

    log.info(f"{device}: Build the LR scheulder")
    if "total_epochs" in cfg["scheduler"]["config"]:
        # with open_dict(cfg):
        cfg["scheduler"]["config"]["total_steps"] = len(train_dataloader) * cfg["scheduler"]["config"]["total_epochs"]
    if "warmup_epochs" in cfg["scheduler"]["config"]:
        # with open_dict(cfg):
        if isinstance(cfg["scheduler"]["config"]["warmup_epochs"], int):
            cfg["scheduler"]["config"]["warmup_steps"] = len(train_dataloader) * cfg["scheduler"]["config"][
                "warmup_epochs"]
        elif isinstance(cfg["scheduler"]["config"]["warmup_epochs"], float):
            cfg["scheduler"]["config"]["warmup_steps"] = cfg["scheduler"]["config"]["warmup_epochs"]

    scheduler = build_scheduler(optimizer, cfg["scheduler"])
    scaler = torch.cuda.amp.GradScaler() if cfg["base"]["amp"] else None

    if local_rank < 1:
        import nltk

        # log.info("Download nltk module")
        # nltk.download("punkt")

    # train
    log.info(f"{device}: Train the model")
    if "total_epoch" in cfg["scheduler"]:
        total_epochs = cfg["scheduler"]["total_epoch"]
        cfg["scheduler"]["config"]["total_steps"] = total_epochs * len(train_dataloader)
    else:
        total_epochs = math.ceil(cfg["scheduler"]["config"]["total_steps"] / len(train_dataloader))

    # tensorboard
    util.GlobalEnv.get().summary_writer.train = util.DistSummaryWriter(cfg["base"]["output"]["tensorboard"] + "/train")
    util.GlobalEnv.get().summary_writer.valid = util.DistSummaryWriter(cfg["base"]["output"]["tensorboard"] + "/valid")
    util.GlobalEnv.get().summary_writer.global_step = 0
    util.GlobalEnv.get().summary_writer.train.add_text(
        "hyperparams/config", "\n".join(["\t" + line for line in OmegaConf.to_yaml(cfg).splitlines()]), 0
    )
    if util.GlobalEnv.get().master:
        os.makedirs(cfg["base"]["output"]["checkpoint"], exist_ok=True)

    # training
    # best_loss = ckpt['train_loss'] if cfg.test.resume else 9e9
    # epoch_resume = ckpt['epoch'] if cfg.test.resume else 0
    best_loss = 9e9
    epoch_resume = 0
    best_score = 0
    best_pair = {
        "i2t": None,
        "t2i": None
    }
    patience = 0
    for epoch in range(epoch_resume, total_epochs):
        if local_rank == -1 or local_rank == 0:
            torch.cuda.empty_cache()
            # print(valid_clip(model, valid_dataloaders))
            test_dataloader = test_dataloaders["mimic_cxr"]
            i2t_result, t2i_result = valid_clip(model, test_dataloader)
            log.info(f"-------------------Epoch {epoch} ------------------------")
            log.info(f"{str(i2t_result)}")
            log.info(f"{str(t2i_result)}")
            if best_score < i2t_result["sum"] + t2i_result["sum"]:
                best_score = i2t_result["sum"] + t2i_result["sum"]
                best_pair = {"i2t": i2t_result, "t2i": t2i_result}
                patience = 0
            if util.GlobalEnv.get().master:
                filename = os.path.join(cfg["base"]["output"]["checkpoint"], "model")
                checkpoint = f"{filename}.tar"
                model_state_dict = model.state_dict() if local_rank == -1 else model.module.state_dict()
                torch.save(
                    {
                        "model": model_state_dict,
                        "optimizer": optimizer.state_dict(),
                        "scheduler": scheduler.state_dict(),
                        "config": cfg,
                        "epoch": epoch + 1,
                    },
                    checkpoint,
                )
                log.info(f"Epoch {epoch}, last-model saved")
                shutil.copyfile(checkpoint, f"{filename}-best.tar")
                log.info(f"{filename}-best.tar saved")

            test_dataloader = test_dataloaders["chexpert"]
            i2t_result, t2i_result = valid_clip(model, test_dataloader)
            log.info(f"-------------------chexpert5x200 ------------------------")
            log.info(f"{str(i2t_result)}")
            log.info(f"{str(t2i_result)}")
            log.info(i2t_result["sum"] + t2i_result["sum"])

            test_dataloader = test_dataloaders["iuxray"]
            i2t_result, t2i_result = valid_clip(model, test_dataloader)
            log.info(f"------------------iuxray------------------------")
            log.info(f"{str(i2t_result)}")
            log.info(f"{str(t2i_result)}")
            log.info(i2t_result["sum"] + t2i_result["sum"])

            log.info(("{Patience", patience, " SUMMARY= " + str(best_score) + " Best Pair" + str(best_pair)))
            patience += 1
            if patience >= 25:
                return

        if train_sampler is not None:
            train_sampler.set_epoch(epoch)

        if 30 < epoch <= 33 or 33 < epoch <= 36 or 40 < epoch <= 43:
        # if 26 < epoch <= 28 or 30 < epoch <= 33 or 40 < epoch <= 43:
            for param_group in optimizer.param_groups:
                param_group['lr'] /= 2
            log.info(f"Learning rate decayed by 2x at epoch {epoch}. New LR: {optimizer.param_groups[0]['lr']}")

        train_loss_dict = train(
            model,
            device,
            loss_func,
            optimizer,
            scheduler,
            train_dataloader,
            epoch,
            total_epochs,
            scaler,
            cfg["scheduler"]["config"]["total_steps"],
        )

        val_loss_dict_per_dataset = validate(
            model, device, loss_func, valid_dataloaders, epoch, total_epochs, local_rank, cfg["base"]["amp"]
        )

        # tensorboard
        for k, v in train_loss_dict.items():
            util.GlobalEnv.get().summary_writer.train.add_scalar(f"loss_per_epoch/{k}", v, epoch + 1)

        avg_val_loss_per_loss = {"total": 0.0}
        for loss_key in loss_func.loss_list:
            avg_val_loss_per_loss[loss_key.name] = 0.0

        for data_name, loss_dict in val_loss_dict_per_dataset.items():
            for loss_key, v in loss_dict.items():
                util.GlobalEnv.get().summary_writer.valid.add_scalar(f"loss_per_epoch/{loss_key}/{data_name}", v,
                                                                     epoch + 1)
                avg_val_loss_per_loss[loss_key] += v

        for loss_key in avg_val_loss_per_loss:
            avg_val_loss_per_loss[loss_key] /= len(valid_dataloaders)
            util.GlobalEnv.get().summary_writer.valid.add_scalar(f"loss_per_epoch/{loss_key}",
                                                                 avg_val_loss_per_loss[loss_key], epoch + 1)

        if util.GlobalEnv.get().master:
            # best model
            if avg_val_loss_per_loss[cfg["base"]["loss_best"]] < best_loss:
                filename = os.path.join(cfg["base"]["output"]["checkpoint"], "model")
                checkpoint = f"{filename}.tar"
                model_state_dict = model.state_dict() if local_rank == -1 else model.module.state_dict()
                torch.save(
                    {
                        "model": model_state_dict,
                        "optimizer": optimizer.state_dict(),
                        "scheduler": scheduler.state_dict(),
                        "config": cfg,
                        "epoch": epoch + 1,
                        "train_loss": train_loss_dict["total"],
                    },
                    checkpoint,
                )
                log.info(f"Epoch {epoch}, last-model saved")
                shutil.copyfile(checkpoint, f"{filename}-best.tar")
                log.info(f"{filename}-best.tar saved")
                best_loss = avg_val_loss_per_loss[cfg["base"]["loss_best"]]

        torch.cuda.empty_cache()
        gc.collect()

    util.GlobalEnv.get().summary_writer.train.close()
    util.GlobalEnv.get().summary_writer.valid.close()
    log.info(f"{device}: Training has been completed")


def train(model, device, loss_func, optimizer, scheduler, dataloader, epoch, total_epochs, scaler, total_step,
          print_step=5):
    model.train()
    if util.GlobalEnv.get().local_rank < 1:
        progress_iter = tqdm(enumerate(dataloader), desc=f"[{epoch:03d}/{total_epochs:03d} epoch train]",
                             total=len(dataloader))
    else:
        progress_iter = enumerate(dataloader)

    avg_loss_dict = {"total": 0.0}
    for k in loss_func.loss_list:
        avg_loss_dict[k.name] = 0.0
    if not scaler:
        if hasattr(model, "module"):
            model.module.half()
        else:
            model.half()
    step_num = 1
    for idx, batch in progress_iter:
        if idx % step_num == 0:
            optimizer.zero_grad(set_to_none=True)

        if scaler:
            with torch.cuda.amp.autocast():
                outputs = model(batch, device)
                loss_dict = loss_func(**outputs, is_train=True)
            total_loss = loss_dict["total"]
            scaler.scale(total_loss).backward()
            # if idx % step_num == 0:
            #     for param in model.parameters():
            #         if param.grad is not None:
            #             param.grad /= step_num
            # torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=16)
            scaler.step(optimizer)
            scaler.update()
        else:
            batch["images"] = batch["images"].half()
            outputs = model(batch, device)
            loss_dict = loss_func(**outputs, is_train=True)
            total_loss = loss_dict["total"]
            total_loss.backward()
            # if idx % step_num == 0:
            #     for param in model.parameters():
            #         if param.grad is not None:
            #             param.grad /= step_num
            # torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=8471179e-096f140b-40344323-2d36d592-199b26cf)
            optimizer.step()

        # if idx % step_num == 0:
        scheduler.step()
        util.GlobalEnv.get().summary_writer.global_step = scheduler._step_count

        for k in loss_dict:
            avg_loss_dict[k] += loss_dict[k].item()

        if idx % print_step == 0 and util.GlobalEnv.get().local_rank < 1:
            for k, lr in enumerate(scheduler.get_last_lr()):
                util.GlobalEnv.get().summary_writer.train.add_scalar(f"hyperparam/lr-{k}", lr, scheduler._step_count)
            util.GlobalEnv.get().summary_writer.train.add_scalar("loss", total_loss, scheduler._step_count)

            for k in loss_dict:
                util.GlobalEnv.get().summary_writer.train.add_scalar(f"loss/{k}", loss_dict[k], scheduler._step_count)

            progress_iter.set_postfix(
                {
                    "lr": [f"{v:.8f}" for v in scheduler.get_last_lr()],
                    "loss": f"{total_loss:.6f}",
                    "CUDA-Mem": f"{torch.cuda.memory_usage(device)}%",
                    "CUDA-Util": f"{torch.cuda.utilization(device)}%",
                }
            )
        if total_step == scheduler._step_count:
            break

    for k in avg_loss_dict:
        avg_loss_dict[k] = avg_loss_dict[k] / len(dataloader)

    return avg_loss_dict


def validate(model, device, loss_func, dataloader_dict, epoch, total_epochs, local_rank, amp, print_step=10):
    model.train()
    loss_dict_per_dataset = dict()
    with torch.no_grad():
        for data_name, dataloader in dataloader_dict.items():
            avg_loss_dict = {"total": 0.0}
            for loss_key in loss_func.loss_list:
                avg_loss_dict[loss_key.name] = 0.0

            if util.GlobalEnv.get().local_rank < 1:
                progress_iter = tqdm(enumerate(dataloader), desc=f"[{epoch:03d}/{total_epochs:03d} epoch valid]",
                                     total=len(dataloader))
            else:
                progress_iter = enumerate(dataloader)

            for idx, batch in progress_iter:
                if amp:
                    with torch.cuda.amp.autocast():
                        outputs = model(batch, device)
                        loss_dict = loss_func(**outputs, is_train=False)
                else:
                    outputs = model(batch, device)
                    loss_dict = loss_func(**outputs, is_train=False)

                if util.GlobalEnv.get().world_size > 1:
                    for loss_key in loss_dict:
                        dist.all_reduce(loss_dict[loss_key], dist.ReduceOp.SUM)
                        loss_dict[loss_key] = loss_dict[loss_key] / util.GlobalEnv.get().world_size

                for loss_key in loss_dict:
                    avg_loss_dict[loss_key] += loss_dict[loss_key].item()

                if (idx % print_step == 0 or idx == len(dataloader) - 1) and local_rank < 1:
                    progress_iter.set_postfix(
                        {
                            "loss": f'{avg_loss_dict["total"]:.6f}',
                            "CUDA-Mem(%)": torch.cuda.memory_usage(device),
                            "CUDA-Util(%)": torch.cuda.utilization(device),
                        }
                    )

            for loss_key in avg_loss_dict:
                avg_loss_dict[loss_key] = avg_loss_dict[loss_key] / len(dataloader)

            loss_dict_per_dataset[data_name] = avg_loss_dict
    return loss_dict_per_dataset


@torch.no_grad()
def valid_clip(model, test_data_loader):
    model.eval()
    num_gpus = torch.cuda.device_count()
    # if num_gpus > 1:
    model = model.module

    image_cls_features = []
    image_tokens = []
    text_cls_features = []
    attention_masks = []
    text_tokens = []

    # test_data_loader = test_data_loader["mimic_cxr"]
    image_paths = []
    text_contents = []
    for idx, data in enumerate(tqdm(test_data_loader, desc="valid generating features")):
        image_paths.extend(data["image_path"])
        text_contents.extend(data["texts"])
        image_cls_feature, image_token, text_cls_feature, text_token, attention_mask = model.pre_encode(data)
        image_cls_features.append(image_cls_feature)
        image_tokens.append(image_token)
        text_cls_features.append(text_cls_feature)
        attention_masks.append(attention_mask)
        text_tokens.append(text_token)

    image_cls_features = torch.cat(image_cls_features, dim=0)
    image_tokens = torch.cat(image_tokens, dim=0)
    text_cls_features = torch.cat(text_cls_features, dim=0)
    attention_masks = torch.cat(attention_masks, dim=0)
    text_tokens = torch.cat(text_tokens, dim=0)

    batch_size = test_data_loader.batch_size
    image_share_steps = (len(image_cls_features) - 1) // batch_size + 1
    text_share_steps = (len(text_cls_features) - 1) // batch_size + 1

    sims = torch.zeros((len(image_cls_features), len(text_cls_features)), device=image_cls_features.device)  # 1 * N
    for i in tqdm(range(image_share_steps), desc="image share"):
        image_start_id, image_end_id = i * batch_size, min((i + 1) * batch_size, len(image_cls_features))
        for j in range(text_share_steps):
            text_start_id, text_end_id = j * batch_size, min((j + 1) * batch_size, len(text_cls_features))
            image_cls_feature, text_cls_feature = model.encode(
                image_cls_features[image_start_id:image_end_id],
                image_tokens[image_start_id:image_end_id],
                text_cls_features[text_start_id:text_end_id],
                text_tokens[text_start_id:text_end_id],
                attention_masks[text_start_id:text_end_id],
            )
            image_cls_feature = image_cls_feature / image_cls_feature.norm(p=2, dim=-1, keepdim=True)
            text_cls_feature = text_cls_feature / text_cls_feature.norm(p=2, dim=-1, keepdim=True)
            sim = image_cls_feature @ text_cls_feature.t()
            sims[image_start_id:image_end_id, text_start_id:text_end_id] = sim


    sims = sims.cpu().numpy()
    image_paths = []
    text_contents = []
    i2t_result = i2t(sims)
    i2t_result = {
        "Recall@1": i2t_result[0], "Recall@5": i2t_result[1],
        "Recall@10": i2t_result[2], "MeanRank": i2t_result[4],
        'sum': i2t_result[0] + i2t_result[1] + i2t_result[2]}
    t2i_result = t2i(sims)
    t2i_result = {
        "Recall@1": t2i_result[0], "Recall@5": t2i_result[1],
        "Recall@10": t2i_result[2], "MeanRank": t2i_result[4],
        'sum': t2i_result[0] + t2i_result[1] + t2i_result[2]
    }
    return i2t_result, t2i_result


def i2t(sims, return_ranks=False):
    """
    Images->Text (Image Annotation)
    Images: (N, n_region, d) matrix of images
    Captions: (N, max_n_word, d) matrix of captions
    CapLens: (N) array of caption lengths
    sims: (N, N) matrix of similarity im-cap
    """
    npts = sims.shape[0]
    ranks = np.zeros(npts)
    top1 = np.zeros(npts)
    top5 = np.zeros((npts, 5))
    top10 = np.zeros((npts, 10))

    for index in range(npts):
        inds = np.argsort(-1 * sims[index])
        tmp = np.where(inds == index)[0][0]
        ranks[index] = tmp
        top1[index] = inds[0]
        top5[index] = inds[0:5]
        top10[index] = inds[0:10]

    # Compute metrics
    r1 = 100.0 * len(np.where(ranks < 1)[0]) / len(ranks)
    r5 = 100.0 * len(np.where(ranks < 5)[0]) / len(ranks)
    r10 = 100.0 * len(np.where(ranks < 10)[0]) / len(ranks)
    medr = np.floor(np.median(ranks)) + 1
    meanr = ranks.mean() + 1
    MRR = np.sum(1 / (ranks + 1)) / len(ranks)
    if return_ranks:
        return (r1, r5, r10, medr, meanr, MRR), (ranks, top1, top5, top10)
    else:
        return (r1, r5, r10, medr, meanr, MRR)


def t2i(sims, return_ranks=False):
    """
    Text->Images (Image Search)
    Images: (N, n_region, d) matrix of images
    Captions: (N, max_n_word, d) matrix of captions
    CapLens: (N) array of caption lengths
    sims: (N, N) matrix of similarity im-cap
    """
    npts = sims.shape[0]
    ranks = np.zeros(npts)
    top1 = np.zeros(npts)
    top5 = np.zeros((npts, 5))
    top10 = np.zeros((npts, 10))

    # --> (5N(caption), N(image))
    sims = sims.T

    for index in range(npts):
        inds = np.argsort(-1 * sims[index])
        ranks[index] = np.where(inds == index)[0][0]
        top1[index] = inds[0]
        top5[index] = inds[0:5]
        top10[index] = inds[0:10]

    # Compute metrics
    r1 = 100.0 * len(np.where(ranks < 1)[0]) / len(ranks)
    r5 = 100.0 * len(np.where(ranks < 5)[0]) / len(ranks)
    r10 = 100.0 * len(np.where(ranks < 10)[0]) / len(ranks)
    medr = np.floor(np.median(ranks)) + 1
    meanr = ranks.mean() + 1
    MRR = np.sum(1 / (ranks + 1)) / len(ranks)
    if return_ranks:
        return (r1, r5, r10, medr, meanr, MRR), (ranks, top1, top5, top10)
    else:
        return (r1, r5, r10, medr, meanr, MRR)
