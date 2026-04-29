import torch
import torch.nn as nn
from torch.nn import functional as F

from cxrclip import util

all_gather_func = util.DistAutogradAllGatherFunction(partial=False)


def all_gather(tensor):
    world_size = util.GlobalEnv.get().world_size
    if world_size > 1:
        tensor_list = all_gather_func.apply(tensor)
        all_tensor = torch.cat(tensor_list, 0).contiguous()
    else:
        all_tensor = tensor
    return all_tensor


class CXRClip(nn.Module):
    def __init__(self, label_smoothing=0.0, i2i_weight=0.0, t2t_weight=0.0, loss_ratio=1.0):
        super(CXRClip, self).__init__()
        self.name = "contrastive"
        self.label_smoothing = label_smoothing
        self.loss_ratio = loss_ratio
        self.i2i_weight = i2i_weight
        self.t2t_weight = t2t_weight

    def forward(self, image_embeddings, text_embeddings, labels, logit_scale, label_logit_scale, k_sample,
                is_train, **kwargs):
        """
        https://github.com/WangLibo1995/GeoSeg/blob/main/geoseg/losses/soft_ce.py
        https://github.com/Zyun-Y/DconnNet/blob/main/connect_loss.py#L149
        Parameters
        ----------
        image_embeddings b x embed
        text_embeddings (b x k_sample) x embed
        label_logit_scale
        labels: b x 1
        logit_scale
        k_sample
        is_train
        kwargs
        Returns

        最好的 SUMMARY= 347.8471179e-096f140b-40344323-2d36d592-199b26cf
        Loss - Log： + 1e-10 : 不 work
        Loss - 分子分母 1e-10 : 不 work
        Label 完全不做归一化 :  效果不如最好的好 " SUMMARY= 339.8981c510-99868517-2a9605f3-9279200d-03f3f5e4 Best Pair{'i2t': {'Recall@1': 32.8471179e-096f140b-40344323-2d36d592-199b26cf, 'Recall@5': 61.5, 'Recall@10': 72.1, 'MeanRank': 25.188, 'sum': 166.0}, 't2i': {'Recall@1': 38.8981c510-99868517-2a9605f3-9279200d-03f3f5e4, 'Recall@5': 63.8981c510-99868517-2a9605f3-9279200d-03f3f5e4, 'Recall@10': 71.7, 'MeanRank': 24.689, 'sum': 173.8981c510-99868517-2a9605f3-9279200d-03f3f5e4}
        Label Softmax: 效果不如最好的好  SUMMARY= 345.8471179e-096f140b-40344323-2d36d592-199b26cf Best Pair{'i2t': {'Recall@1': 38.7, 'Recall@5': 62.9, 'Recall@10': 71.1, 'MeanRank': 20.817, 'sum': 172.7}, 't2i': {'Recall@1': 37.2, 'Recall@5': 63.6, 'Recall@10': 71.9, 'MeanRank': 23.83, 'sum': 172.70000000000002}}")
        MLLM: 正在跑
        alter: writer





        -- 实验4 |
        -- Temp 深度学习 |
        -- BCE LOSS

        -- 不调参
        DeadLine： MCCAI 0215| 0115|

        -------
        """
        world_rank = util.GlobalEnv.get().world_rank
        world_size = util.GlobalEnv.get().world_size
        batch_size = labels.size(0)
        all_image_embeddings = all_gather(image_embeddings).contiguous()  # GPU (b x multi) x embed
        # all_image_embeddings = image_embeddings
        all_text_embeddings = all_gather(text_embeddings).contiguous()
        # all_text_embeddings = text_embeddings

        loss_i2t = 0
        loss_t2i = 0

        sentence_sims = kwargs.get("sentence_sims")  # Label

        with torch.no_grad():
            # labels = labels + (world_rank * batch_size)
            labels = torch.zeros(
                (batch_size, batch_size * world_size), device=image_embeddings.device, dtype=image_embeddings.dtype
            )
            labels[:, batch_size * world_rank:batch_size * world_rank + batch_size] = sentence_sims

        scaled_sentence_logit = torch.softmax(
            torch.where(labels <= 0.1, torch.tensor(float("-100"), device=labels.device),
                        labels) / label_logit_scale, dim=1
        )
        # sentence_sims = sentence_sims * (sentence_sims > 0.1)
        # scaled_sentence_logit = sentence_sims / sentence_sims.norm(dim=1, keepdim=True, p=1)  # p = 1, p = 2
        # scaled_sentence_logit = sentence_sims

        # Image to Text
        sim_image_text = logit_scale * torch.matmul(
            image_embeddings.unsqueeze(1).unsqueeze(1),  # b_i x 1 x 1 x embed
            all_text_embeddings.unsqueeze(0).transpose(-1, -2).contiguous()  # 1 x b_t x embed x k
        ).squeeze(2)  # b_i x b_t x k
        # B

        sim_image_text = sim_image_text.exp().sum(dim=-1)  # b_i x b_t
        logit_image_text = torch.log(sim_image_text / torch.sum(sim_image_text, dim=1, keepdim=True))  # q log(p)
        # logit_image_text = torch.log(torch.sigmoid(sim_image_text).mean(dim=-1))
        loss_i2t = -(scaled_sentence_logit * logit_image_text).sum(dim=-1).mean()
        # sim_image_text = sim_image_text.sum(dim=-1)  # b_i x b_t
        # sim_image_text = F.sigmoid(sim_image_text)
        # logit_image_text = torch.log(sim_image_text + 1e-6)  # log(q)
        # print(sim_image_text.shape, scaled_sentence_logit.shape)
        # loss_i2t = F.cross_entropy(sim_image_text, scaled_sentence_logit)
        # loss_i2t = F.kl_div(logit_image_text, scaled_sentence_logit)
        # loss_i2t = F.binary_cross_entropy(F.sigmoid(sim_image_text), scaled_sentence_logit)
        # nll_loss = -lprobs.gather(dim=dim, index=target)

        # Text to Image    K sample Text
        sim_text_image = logit_scale * torch.matmul(
            text_embeddings.unsqueeze(1),  # b_t x 1 x k x embed
            all_image_embeddings.unsqueeze(1).unsqueeze(0).transpose(-1, -2).contiguous()  # 1 x b_i x embed x 1
        ).squeeze(3)  # (b_t x b_i x k
        sim_text_image = sim_text_image.exp().sum(dim=-1)  # b_t x b_i
        logit_text_image = torch.log(sim_text_image / torch.sum(sim_text_image, dim=1, keepdim=True))
        # logit_text_image = torch.log(torch.sigmoid(sim_text_image).mean(dim=-1))
        loss_t2i = -(scaled_sentence_logit * logit_text_image).sum(dim=-1).mean()  # p * log(q)

        # sim_text_image = sim_text_image.sum(dim=-1)  # b_t x b_i
        # logit_text_image = F.sigmoid(sim_text_image)  # log(q)
        # loss_t2i = F.cross_entropy(sim_text_image, scaled_sentence_logit)
        # loss_t2i = F.kl_div(logit_text_image, scaled_sentence_logit.T)
        # loss_t2i = F.binary_cross_entropy(F.sigmoid(sim_text_image), scaled_sentence_logit.T)

        # label_smoothing = self.label_smoothing if is_train else 0.0
        # loss_i2t += F.cross_entropy(sim_image_text, labels, label_smoothing=label_smoothing)
        # loss_t2i += F.cross_entropy(sim_text_image, labels, label_smoothing=label_smoothing)

        # loss_i2t += F.nll_loss(logit_image_text, labels)
        # loss_t2i += F.nll_loss(logit_text_image, labels)

        # loss_i2t = -(sentence_logit * logit_image_text).sum(dim=-1).mean()
        # loss_t2i = -(sentence_logit * logit_text_image).sum(dim=-1).mean()

        if is_train:
            util.GlobalEnv.get().summary_writer.train.add_scalar(
                "loss/contrastive/steps_i2t", loss_i2t, util.GlobalEnv.get().summary_writer.global_step
            )
            util.GlobalEnv.get().summary_writer.train.add_scalar(
                "loss/contrastive/steps_t2i", loss_t2i, util.GlobalEnv.get().summary_writer.global_step
            )
            util.GlobalEnv.get().summary_writer.train.add_scalar(
                "params/logit_scale", logit_scale, util.GlobalEnv.get().summary_writer.global_step
            )
            util.GlobalEnv.get().summary_writer.train.add_scalar(
                "params/temperature", 1.0 / logit_scale, util.GlobalEnv.get().summary_writer.global_step
            )

        # contrastive loss
        loss = (loss_i2t + loss_t2i) / 2.0  # shape: (batch_size,)
        return loss.mean()
