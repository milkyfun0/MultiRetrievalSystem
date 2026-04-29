import logging
from typing import Dict

import numpy as np
import torch
from bert_score import BERTScorer
from torch import nn
from transformers.tokenization_utils import PreTrainedTokenizer
import sys
import time
import os
from collections import defaultdict
import torch
import pandas
from torch import nn

from bert_score.utils import bert_cos_score_idf, get_model, get_tokenizer

from .modules import load_image_encoder, load_projection_head, load_text_encoder

log = logging.getLogger(__name__)


class BerScore(nn.Module):
    def __init__(self, model_type, num_layers=12, use_fast_tokenizer=False, all_layers=False):
        super(BerScore, self).__init__()
        self.model_type = model_type
        self.num_layers = num_layers
        self.use_fast_tokenizer = use_fast_tokenizer
        self.tokenizer = get_tokenizer(model_type, use_fast_tokenizer)
        self.model = get_model(model_type, num_layers, all_layers)
        self.model.eval()
        self.all_layers = all_layers
        self.idf_dict = defaultdict(lambda: 1.0)
        self.idf_dict[self.tokenizer.sep_token_id] = 0
        self.idf_dict[self.tokenizer.cls_token_id] = 0

    @torch.no_grad()
    def forward(self, cands, refs, verbose=False, batch_size=64, rescale_with_baseline=True, baseline_path=None,
                lang="en", return_hash=False):
        start = time.perf_counter()
        all_preds = bert_cos_score_idf(
            self.model,
            refs,
            cands,
            self.tokenizer,
            self.idf_dict,
            verbose=verbose,
            device=self.model.device,
            batch_size=batch_size,
            all_layers=self.all_layers,
        ).cpu()
        use_custom_baseline = baseline_path is not None
        if rescale_with_baseline:
            if os.path.isfile(baseline_path):
                if not self.all_layers:
                    baselines = torch.from_numpy(
                        pandas.read_csv(baseline_path).iloc[self.num_layers].to_numpy()
                    )[1:].float()
                else:
                    baselines = (
                        torch.from_numpy(pandas.read_csv(baseline_path).to_numpy())[:, 1:]
                        .unsqueeze(1)
                        .float()
                    )

                all_preds = (all_preds - baselines) / (1 - baselines)
            else:
                print(
                    f"Warning: Baseline not Found for {self.model_type} on {lang} at {baseline_path}",
                    file=sys.stderr,
                )

        out = all_preds[..., 0], all_preds[..., 1], all_preds[..., 2]  # P, R, F

        if verbose:
            time_diff = time.perf_counter() - start
            print(
                f"done in {time_diff:.2f} seconds, {len(refs) / time_diff:.2f} sentences/sec"
            )
        return {
            "P": out[0],
            "R": out[1],
            "F": out[2],
        }


"""
emilyalsentzer/Bio_ClinicalBERT 12
distilbert-base-uncased 5
microsoft/deberta-v3-base 12
microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext 12
ncbi/MedCPT-Query-Encoder 12
"""


class CXRClip(nn.Module):
    def __init__(self, model_config: Dict, all_loss_config: Dict, tokenizer: PreTrainedTokenizer = None):
        super().__init__()
        self.k_sample = model_config["k_sample"]
        self.mask_ratio = model_config["mask_ratio"]
        self.tokenizer = tokenizer
        # print(model_config["image_encoder"])
        self.image_encoder = load_image_encoder(model_config["image_encoder"])
        self.text_encoder = load_text_encoder(model_config["text_encoder"], vocab_size=tokenizer.vocab_size)
        # self.text_sim_encoder = load_text_encoder(model_config["text_encoder"], vocab_size=tokenizer.vocab_size)
        self.bert_score = None
        self.text_pooling = model_config["text_encoder"]["pooling"]

        self.model_config = model_config
        self.loss_config = {k: v for k, v in all_loss_config.items()}
        self.projection = "projection_head" in model_config

        if self.projection:
            self.image_projection = load_projection_head(
                embedding_dim=self.image_encoder.out_dim,
                config_projection_head=model_config["projection_head"]
            )
            self.text_projection = load_projection_head(
                embedding_dim=self.text_encoder.out_dim,
                config_projection_head=model_config["projection_head"]
            )
        else:
            assert (
                    self.image_encoder.out_dim == self.text_encoder.out_dim
            ), "Without 'projection_head', embedding_dim of the image and text encoder must be the same."

        self.temperature = model_config["temperature"] if "temperature" in model_config else None
        if self.temperature:
            self.logit_scale = nn.Parameter(torch.ones([]) * np.log(1 / self.temperature))
            self.label_logit_scale = nn.Parameter(torch.ones([]) * np.log(1 / self.temperature))
        else:
            self.logit_scale = torch.tensor(1, dtype=torch.float32)
            log.warning("[CXRCLIP] missing temperature scaling factor")

    def encode_image(self, image):
        image_features = self.image_encoder(image)
        if self.model_config["image_encoder"]["name"] == "resnet":
            return image_features, image_features
        else:
            # get [CLS] token for global representation (only for vision transformer)
            global_features = image_features[:, 0].contiguous()
            global_features = self.image_projection(
                global_features).contiguous() if self.projection else global_features

            return global_features, image_features

    def get_sentence_sim(self, text):
        text_features = self.text_sim_encoder(text)
        attention_mask = text["attention_mask"]
        if self.text_pooling == "eos":
            # take features from the eot embedding (eos_token is the highest number in each sequence)
            eos_token_indices = attention_mask.sum(dim=-1) - 1
            text_features = text_features[torch.arange(text_features.shape[0]), eos_token_indices]
        elif self.text_pooling == "bos":
            text_features = text_features[:, 0]
        elif self.text_pooling == "mean":
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(text_features.size()).float()
            text_features = torch.sum(text_features * input_mask_expanded, axis=1) / torch.clamp(
                input_mask_expanded.sum(axis=1), min=1e-9)
        else:
            raise NotImplementedError("Not supported pooling method : %s", self.text_pooling)

        text_features = text_features / text_features.norm(dim=1, keepdim=True)
        return (text_features @ text_features.T).detach()

    def encode_text(self, text):
        """
        Parameters
        ----------
        text:
            input_ids
            attention_mask
        Returns
        -------
        text_features, token_features, attention_mask
        """
        # text_features = self.text_encoder(text)
        # attention_mask = text["attention_mask"]
        if not self.training:
            text_features = self.text_encoder(text)
            attention_mask = text["attention_mask"]
        else:
            # text_features = []
            # attention_mask = []
            # for i in range(self.k_sample):
            #     text_mask = self.text_masked_language_modeling(text, self.mask_ratio, 1)
            #     text_feature = self.text_encoder(text_mask)
            #     attention_mask.append(text["attention_mask"])
            #     text_features.append(text_feature)
            # text_feature = self.text_encoder(text)
            # text_features.append(text_feature)
            # attention_mask.append(text["attention_mask"])
            # text_features = torch.cat(text_features, dim=0).contiguous()
            # attention_mask = torch.cat(attention_mask, dim=0).contiguous()

            new_text = self.text_masked_language_modeling(text, self.mask_ratio, self.k_sample)
            text_features = self.text_encoder(new_text).contiguous()
            attention_mask = new_text["attention_mask"]

        token_features = text_features
        if self.text_pooling == "eos":
            # take features from the eot embedding (eos_token is the highest number in each sequence)
            eos_token_indices = attention_mask.sum(dim=-1) - 1
            text_features = text_features[torch.arange(text_features.shape[0]), eos_token_indices]
        elif self.text_pooling == "bos":
            text_features = text_features[:, 0]
        elif self.text_pooling == "mean":
            input_mask_expanded = attention_mask.unsqueeze(-1).expand(text_features.size()).float()
            text_features = torch.sum(text_features * input_mask_expanded, axis=1) / torch.clamp(
                input_mask_expanded.sum(axis=1), min=1e-9)
        else:
            raise NotImplementedError("Not supported pooling method : %s", self.text_pooling)

        text_features = self.text_projection(text_features).contiguous() if self.projection else text_features

        return text_features, token_features, attention_mask

    def text_masked_language_modeling(self, text, mask_ratio=0.15, k_sample=1):
        """

        Parameters
        ----------
        text:
            input_ids
            attention_mask
        mask_ratio
        k_sample
        Returns
        -------
        """
        mask_token_id = self.tokenizer.mask_token_id
        b, context_length = text["input_ids"].shape
        input_ids = text["input_ids"]
        attention_mask = text["attention_mask"]

        mask = (torch.rand(b, k_sample, context_length).to(input_ids.device) >= mask_ratio).to(
            input_ids.dtype).contiguous()
        input_ids_masked = input_ids.unsqueeze(1) * mask + (1 - mask) * mask_token_id  # b x k x context_length
        attention_mask_masked = attention_mask.unsqueeze(1) * (mask >= 0).to(attention_mask.dtype)

        input_ids_masked = input_ids_masked.reshape(b * k_sample, context_length).contiguous()
        attention_mask_masked = attention_mask_masked.reshape(b * k_sample, context_length).contiguous()
        return {
            "input_ids": input_ids_masked,
            "attention_mask": attention_mask_masked,
        }

    def label_smoothing(self, labels, epsilon=0.1):
        """
        对 one-hot 标签进行平滑处理
        
        参数:
        labels (torch.Tensor): 形状为 (n, n) 的 one-hot 标签矩阵
        epsilon (float): 平滑系数，控制平滑程度 (0 < epsilon < 1)
        
        返回:
        torch.Tensor: 平滑后的标签矩阵
        """
        # 验证输入
        assert len(labels.shape) == 2, "输入标签必须是二维矩阵"
        assert labels.shape[0] == labels.shape[1], "输入矩阵必须是方阵(n x n)"
        assert 0 < epsilon < 1, "平滑系数必须在 (0, 1) 范围内"
        n = labels.shape[0]  # 类别数量
        # 创建均匀分布部分
        uniform_dist = torch.ones_like(labels) / n
        # 应用标签平滑公式
        smoothed_labels = (1 - epsilon) * labels + epsilon * uniform_dist

        return smoothed_labels

    def pre_encode(self, batch, device=None):
        """
        Args:
            batch: dict  images, text_tokens, image_views, text_tokens2
            device:

        Returns:
            image_embeddings: num_image x embed_dim
            text_embeddings: num_text x embed_dim
            attention_mask: num_text x context_length
            image_tokens: num_image x patches x embed_dim
            text_tokens: num_text x context_length x embed_dim
        """
        device = self.image_projection.projection.weight.device
        sentence_sims = self.get_bert_score(batch["texts"]).to(device)
        print("sentence_sims", sentence_sims)
        image_features_g, image_tokens = self.encode_image(batch["images"])
        text_features_g, text_tokens, attention_mask = self.encode_text(batch["text_tokens"])

        image_embeddings = self.image_projection(image_features_g).contiguous() if self.projection else image_features_g
        text_embeddings = self.text_projection(text_features_g).contiguous() if self.projection else text_features_g
        return image_embeddings, image_tokens, text_embeddings, text_tokens, attention_mask

    def encode(self, image_embeddings, image_tokens, text_embeddings, text_tokens, attention_mask):
        """
        Parameters
        ----------
        attention_mask
        text_tokens
        text_embeddings
        image_tokens
        image_embeddings
        """
        image_embeddings = image_embeddings / image_embeddings.norm(dim=1, keepdim=True)
        text_embeddings = text_embeddings / text_embeddings.norm(dim=1, keepdim=True)

        return image_embeddings, text_embeddings

    def get_bert_score(self, texts):
        n = len(texts)
        texts = [t[:512] for t in texts]  # 简单截断前 512 字符
        source_str = []
        target_str = []
        for i in range(n):
            for j in range(n):
                source_str.append(texts[i])
                target_str.append(texts[j])
        # _, _, f = self.bert_scorer.score(cands=source_str, refs=target_str)
        # sims = f
        sims = self.bert_score(
            source_str,
            target_str,
            batch_size=n
        )["F"]
        return sims.reshape(n, n)

    def forward(self, batch, device=None):
        device = self.image_projection.projection.weight.device
        # sentence_sims = batch["sentence_sims"].to(device)
        sentence_sims = self.get_bert_score(batch["texts"]).to(device)

        # sentence_sims = self.get_sentence_sim(batch["text_tokens"].to(device))
        # sentence_sims = self.label_smoothing(batch["sentence_sims"].to(device))
        # print(sentence_sims)
        image_embeddings, image_tokens, text_embeddings, text_tokens, attention_mask = self.pre_encode(batch, device)

        image_embeddings, text_embeddings = self.encode(
            image_embeddings, image_tokens, text_embeddings, text_tokens, attention_mask
        )
        labels = torch.arange(image_embeddings.shape[0], device=device)
        batch_size, embed_dim = image_embeddings.shape[0], image_embeddings.shape[1]

        out = {
            "image_embeddings": image_embeddings,
            "text_embeddings": text_embeddings.view(batch_size, self.k_sample, embed_dim),
            "labels": labels,
            "logit_scale": self.logit_scale.exp(),
            "label_logit_scale": self.label_logit_scale.exp(),
            "k_sample": self.k_sample,
            "sentence_sims": sentence_sims,
            # "sentence_sims": sentence_sims,

        }

        return out
