import torch
from torch import nn
from torchvision.models.resnet import resnet50
from transformers import AutoConfig, AutoModel, SwinModel, ViTModel


class HuggingfaceImageEncoder(nn.Module):
    def __init__(
            self,
            name: str = "google/vit-base-patch16-224",
            pretrained: bool = True,
            gradient_checkpointing: bool = False,
            cache_dir: str = "huggingface",
            model_type: str = "vit",
            local_files_only: bool = False,
    ):
        super().__init__()
        self.model_type = model_type
        if pretrained:
            if self.model_type == "swin":
                cache_dir = "huggingface"
                self.image_encoder = AutoModel.from_pretrained(
                    name,
                    # cache_dir=cache_dir,
                    # local_files_only=True

                )
            else:
                self.image_encoder = AutoModel.from_pretrained(
                    name,
                    ignore_mismatched_sizes=True,
                    # attn_implementation="flash_attention_2",
                    # torch_dtype=torch.float16,
                )
        else:
            # initializing with a config file does not load the weights associated with the model
            model_config = AutoConfig.from_pretrained(name, cache_dir=cache_dir, local_files_only=local_files_only)
            if type(model_config).__name__ == "ViTConfig":
                self.image_encoder = ViTModel(model_config, add_pooling_layer=False)
            else:
                # TODO: add vision models if needed
                raise NotImplementedError(f"Not support training from scratch : {type(model_config).__name__}")

        if gradient_checkpointing and self.image_encoder.supports_gradient_checkpointing:
            self.image_encoder.gradient_checkpointing_enable()
        if self.model_type == "vit":
            self.out_dim = self.image_encoder.config.projection_dim
        else:
            self.out_dim = self.image_encoder.config.hidden_size

    def forward(self, image):
        input_type = image.dtype
        if self.model_type == "vit":
            output = self.image_encoder.vision_model(image, return_dict=True)
            output["last_hidden_state"] = self.image_encoder.visual_projection(output["last_hidden_state"])
        elif self.model_type == "swin":
            output = self.image_encoder(pixel_values=image)
        return output["last_hidden_state"]  # (batch, seq_len, hidden_size)


class ResNet50(nn.Module):
    def __init__(self, name: str = "resnet50", pretrained: bool = True):
        super().__init__()
        if pretrained:
            self.resnet = resnet50(pretrained=True)
        else:
            # TODO: add vision models if needed
            raise NotImplementedError(f"Not support training from scratch : {name}")

        self.out_dim = 2048
        del self.resnet.fc
        # self.resnet = nn.SyncBatchNorm.convert_sync_batchnorm(self.resnet)

    def forward(self, x):
        # See note [TorchScript super()]
        x = self.resnet.conv1(x)
        x = self.resnet.bn1(x)
        x = self.resnet.relu(x)
        x = self.resnet.maxpool(x)

        x = self.resnet.layer1(x)
        x = self.resnet.layer2(x)
        x = self.resnet.layer3(x)
        x = self.resnet.layer4(x)

        x = self.resnet.avgpool(x)
        x = torch.flatten(x, 1)
        # x = self.fc(x)

        return x
