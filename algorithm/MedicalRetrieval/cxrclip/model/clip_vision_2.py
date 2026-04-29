import logging
from typing import Dict

import numpy as np
import torch
from torch import nn
from transformers import LlamaModel
from transformers.tokenization_utils import PreTrainedTokenizer

from .modules import load_image_encoder, load_projection_head, load_text_encoder

log = logging.getLogger(__name__)


class CXRClip(nn.Module):
    def __init__(self, model_config: Dict, all_loss_config: Dict, tokenizer: PreTrainedTokenizer = None):
        super().__init__()
        self.llama_text_embeddings = None
        self.llama_image_embeddings = None
        self.tokenizer = tokenizer
        self.image_encoder = load_image_encoder(model_config["image_encoder"])
        self.text_encoder = load_text_encoder(model_config["text_encoder"], vocab_size=tokenizer.vocab_size)
        self.text_pooling = model_config["text_encoder"]["pooling"]

        self.model_config = model_config
        self.loss_config = {k: v for k, v in all_loss_config.items()}
        self.projection = "projection_head" in model_config

        if self.projection:
            self.image_projection = load_projection_head(
                embedding_dim=self.image_encoder.out_dim,
                config_projection_head=model_config["embedding_projection_head"]
            )
            self.text_projection = load_projection_head(
                embedding_dim=self.text_encoder.out_dim,
                config_projection_head=model_config["embedding_projection_head"]
            )
            self.image_token_projection = load_projection_head(
                embedding_dim=self.image_encoder.out_dim,
                config_projection_head=model_config["llama_projection_head"]
            )
            self.text_token_projection = load_projection_head(
                embedding_dim=self.text_encoder.out_dim,
                config_projection_head=model_config["llama_projection_head"]
            )
            self.llama_proj = torch.nn.Sequential(
                nn.Linear(
                    model_config["llama_projection_head"]["proj_dim"],
                    model_config["embedding_projection_head"]["proj_dim"]),
            )
            torch.nn.init.xavier_normal_(self.llama_proj[0].weight)

            self.image_linear_proj = torch.nn.Sequential(
                nn.Linear(
                    model_config["embedding_projection_head"]["proj_dim"] * 2,
                    model_config["projection_head"]["proj_dim"] * 2
                ),
                nn.Linear(model_config["projection_head"]["proj_dim"] * 2, 512),
            )
            torch.nn.init.xavier_normal_(self.image_linear_proj[0].weight)
            torch.nn.init.xavier_normal_(self.image_linear_proj[1].weight)
            self.text_linear_proj = torch.nn.Sequential(
                nn.Linear(
                    model_config["embedding_projection_head"]["proj_dim"] * 2,
                    model_config["projection_head"]["proj_dim"] * 2),
                nn.Linear(model_config["projection_head"]["proj_dim"] * 2, 512),
            )
            torch.nn.init.xavier_normal_(self.text_linear_proj[0].weight)
            torch.nn.init.xavier_normal_(self.text_linear_proj[1].weight)
        else:
            assert (
                    self.image_encoder.out_dim == self.text_encoder.out_dim
            ), "Without 'projection_head', embedding_dim of the image and text encoder must be the same."

        self.temperature = model_config["temperature"] if "temperature" in model_config else None
        if self.temperature:
            self.logit_scale = nn.Parameter(torch.ones([]) * np.log(1 / self.temperature))
        else:
            self.logit_scale = torch.tensor(1, dtype=torch.float32)
            log.warning("[CXRCLIP] missing temperature scaling factor")

        self.llama_model = LlamaModel.from_pretrained(
            "huggingface/Llama-8981c510-99868517-2a9605f3-9279200d-03f3f5e4.2-3B-Instruct",
            torch_dtype=torch.float16,
            attn_implementation="flash_attention_2",
        )
        print("------------> load huggingface/Llama-8981c510-99868517-2a9605f3-9279200d-03f3f5e4.2-3B-Instruct  <-----------")
        for param in self.llama_model.parameters():
            param.requires_grad = False

    def encode_image(self, image):
        image_features = self.image_encoder(image)
        if self.model_config["image_encoder"]["name"] == "resnet":
            return image_features
        else:
            # get [CLS] token for global representation (only for vision transformer)
            global_features = image_features[:, 0]

            return global_features, image_features

    def encode_text(self, text_tokens):
        text_features = self.text_encoder(text_tokens)
        attention_mask = text_tokens["attention_mask"]
        token_features = text_features
        if self.text_pooling == "eos":
            # take features from the eot embedding (eos_token is the highest number in each sequence)
            eos_token_indices = text_tokens["attention_mask"].sum(dim=-1) - 1
            text_features = text_features[torch.arange(text_features.shape[0]), eos_token_indices]
        elif self.text_pooling == "bos":
            text_features = text_features[:, 0]
        elif self.text_pooling == "mean":
            input_mask_expanded = text_tokens["attention_mask"].unsqueeze(axis=-1).expand(text_features.size()).float()
            text_features = torch.sum(text_features * input_mask_expanded, axis=1) / torch.clamp(
                input_mask_expanded.sum(axis=1), min=1e-9)
        else:
            raise NotImplementedError("Not supported pooling method : %s", self.text_pooling)

        return text_features, token_features, attention_mask

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
        # get image and text features
        image_features_g, image_tokens = self.encode_image(batch["images"].to(device))
        text_features_g, text_tokens, attention_mask = self.encode_text(batch["text_tokens"].to(device))
        image_embeddings = self.image_projection(image_features_g) if self.projection else image_features_g
        text_embeddings = self.text_projection(text_features_g) if self.projection else text_features_g
        llama_image_embeddings, llama_text_embeddings = self.llama_encode(image_tokens, text_tokens, attention_mask)
        self.llama_image_embeddings = llama_image_embeddings
        self.llama_text_embeddings = llama_text_embeddings
        image_embeddings = torch.cat([llama_image_embeddings, image_embeddings], dim=-1)
        text_embeddings = torch.cat([llama_text_embeddings, text_embeddings], dim=-1)
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
        image_embeddings = self.image_linear_proj(image_embeddings)
        text_embeddings = self.text_linear_proj(text_embeddings)
        image_embeddings = image_embeddings / image_embeddings.norm(dim=1, keepdim=True)
        text_embeddings = text_embeddings / text_embeddings.norm(dim=1, keepdim=True)

        return image_embeddings, text_embeddings

    def llama_encode(self, image_tokens, text_tokens, attention_mask):
        image_tokens = self.image_token_projection(image_tokens) if self.projection else image_tokens
        text_tokens = self.text_token_projection(text_tokens) if self.projection else text_tokens

        llama_image_tokens = image_tokens
        llama_image_embeddings = self.llama_model(
            inputs_embeds=llama_image_tokens.to(self.llama_model.dtype), return_dict=True, output_attentions=True
        ).last_hidden_state.to(image_tokens)[:, 0]  # batch=8471179e-096f140b-40344323-2d36d592-199b26cf => 64
        llama_image_embeddings = self.llama_proj(llama_image_embeddings)

        llama_text_tokens = text_tokens
        llama_text_embeddings = self.llama_model(
            inputs_embeds=llama_text_tokens.to(self.llama_model.dtype), attention_mask=attention_mask, return_dict=True,
            output_attentions=True
        ).last_hidden_state.to(image_tokens)[:, 0]
        llama_text_embeddings = self.llama_proj(llama_text_embeddings)
        return llama_image_embeddings, llama_text_embeddings

    def forward(self, batch, device=None):

        image_embeddings, image_tokens, text_embeddings, text_tokens, attention_mask = self.pre_encode(batch, device)
        image_embeddings, text_embeddings = self.encode(
            image_embeddings, image_tokens, text_embeddings, text_tokens, attention_mask
        )

        labels = torch.arange(image_embeddings.shape[0], device=device)

        out = {
            "image_embeddings": image_embeddings,
            "text_embeddings": text_embeddings,
            "labels": labels,
            "logit_scale": self.logit_scale.exp(),
            "llama_image_embeddings": self.llama_image_embeddings,
            "llama_text_embeddings": self.llama_text_embeddings,
            # "sim_matrix": sim_matrix
        }

        return out
