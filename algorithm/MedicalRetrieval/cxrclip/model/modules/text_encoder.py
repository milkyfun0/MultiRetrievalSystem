import torch
from torch import nn
from transformers import AutoConfig, AutoModel, BertModel


def resize_text_pos_embed(posemb, context_length):
    """
    Adjust the position embeddings for the text when loading from state_dict.
    This is necessary when the length of the position embeddings in the pretrained model
    differs from the context length of the current model.

    Args:
        posemb (torch.Tensor): The position embeddings to be resized. Shape: (old_context_length, embedding_dim)
        context_length (int): The context length that the current model expects.

    Returns:
        torch.Tensor: The resized position embeddings.
    """
    # 如果输入的是二维向量 [sequence_length, embedding_dim]
    if len(posemb.shape) == 2:
        posemb = posemb.unsqueeze(0)  # 添加 batch 维度 -> [1, sequence_length, embedding_dim]

    # 插值或者其他的操作都需要三维张量 [batch_size, sequence_length, embedding_dim]
    if posemb.shape[1] == context_length:
        return posemb.squeeze(0)  # 如果已经匹配，直接返回去除 batch 维度的张量

    print(f'Resizing text position embedding from size: {posemb.shape[1]} to size: {context_length}')

    # 使用线性插值调整嵌入长度
    posemb = torch.nn.functional.interpolate(posemb, size=(context_length,), mode='linear', align_corners=False)

    return posemb.squeeze(0)  # 移除 batch 维度，返回二维张量


class HuggingfaceTextEncoder(nn.Module):
    def __init__(
            self,
            name: str = "bert-base-uncased",
            vocab_size: int = None,
            pretrained: bool = True,
            gradient_checkpointing: bool = False,
            cache_dir: str = "huggingface/",
            local_files_only: bool = True,
            trust_remote_code: bool = False,
    ):
        super().__init__()
        self.name = name
        if pretrained:

            if self.name == "openai/clip-vit-base-patch32":
                self.text_encoder = AutoModel.from_pretrained(
                    name,
                    # vocab_size=vocab_size,
                    ignore_mismatched_sizes=True,
                    # attn_implementation="flash_attention_2",
                    # torch_dtype=torch.float16,
                )
            else:
                self.text_encoder = AutoModel.from_pretrained(
                    name,
                    # vocab_size=vocab_size,
                    # cache_dir=cache_dir,
                    # local_files_only=True,
                    # trust_remote_code=trust_remote_code,
                )
        else:
            # initializing with a config file does not load the weights associated with the model
            model_config = AutoConfig.from_pretrained(
                name,
                # vocab_size=vocab_size,
                ignore_mismatched_sizes=True,
                cache_dir=cache_dir,
                local_files_only=local_files_only,
                trust_remote_code=trust_remote_code,
            )
            if type(model_config).__name__ == "BertConfig":
                self.text_encoder = BertModel(model_config)
            else:
                # TODO: add text models if needed
                raise NotImplementedError(f"Not support training from scratch : {type(model_config).__name__}")

        if gradient_checkpointing and self.text_encoder.supports_gradient_checkpointing:
            self.text_encoder.gradient_checkpointing_enable()

        # self.out_dim = self.text_encoder.config.hidden_size

        if self.name == "openai/clip-vit-base-patch32":
            self.out_dim = self.text_encoder.config.projection_dim
            # if self.text_encoder.text
        else:
            self.out_dim = self.text_encoder.config.hidden_size

    def forward(self, x, show=False):
        if self.name == "openai/clip-vit-base-patch32":
            output = self.text_encoder.text_model(**x, return_dict=True)
            output["last_hidden_state"] = self.text_encoder.text_projection(output["last_hidden_state"])
        else:
            output = self.text_encoder(**x)

        if show:
            return output

        return output["last_hidden_state"]  # (batch, seq_len, hidden_size)
