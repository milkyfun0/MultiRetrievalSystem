from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
import math


class QuickGELU(nn.Module):
    def forward(self, x: torch.Tensor):
        return x * torch.sigmoid(1.702 * x)


def compute_wasserstein_logits(q_norm: torch.Tensor,
                               k_norm: torch.Tensor,
                               var_trace: torch.Tensor,
                               lambda_var: float,
                               tau: float,
                               head_dim: int) -> torch.Tensor:
    """
    Compute attention logits using 2-Wasserstein distance:
      W2^2 = 2*(1 - cos) + var_trace
    logits = -W2^2 / (tau * sqrt(head_dim))
           = (2*cos - var_trace - 2) / (tau * sqrt(head_dim))

    Args:
        q_norm:    (B, H, T, D head_dim normalized)
        k_norm:    (B, H, S, D)
        var_trace: (B, H, 1, S) variance trace per head
        lambda_var: positive scaling for var term
        tau:        positive temperature
        head_dim:   dimension per head
    Returns:
        logits:    (B, H, T, S)
    """
    # cosine similarity
    cos_sim = torch.matmul(q_norm, k_norm.transpose(-2, -1))  # (B,H,T,S)
    # scaled var penalty
    var_penalty = lambda_var * var_trace  # (B,H,1,S)
    # W2^2 = 2*(1 - cos) + var_trace
    # logits = -W2^2 / (tau*sqrt(d))
    #      = (2*cos - var_trace - 2) / (tau*sqrt(d))
    numer = 2 * cos_sim - var_penalty - 2.0
    denom = tau * math.sqrt(head_dim)
    logits = numer / denom
    return logits


class CosWassersteinAttention(nn.Module):
    """
    Attention combining cosine similarity and variance via Wasserstein-2.
    Uses compute_wasserstein_logits to include the -2 constant.
    """

    def __init__(self, num_heads: int, head_dim: int, dropout: float = 0.0):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = head_dim
        # learnable raw parameters
        self.raw_lambda = nn.Parameter(torch.tensor(1.0))
        self.raw_tau = nn.Parameter(torch.tensor(1.0))
        self.dropout = nn.Dropout(dropout)

    def forward(self,
                q: torch.Tensor,  # (B, H, T, d)
                k: torch.Tensor,  # (B, H, S, d)
                v: torch.Tensor,  # (B, H, S, d)
                var_k: torch.Tensor,  # (B, H, S, d)
                mask: torch.Tensor = None
                ):
        # compute positive weights
        lambda_var = F.softplus(self.raw_lambda)
        tau = F.softplus(self.raw_tau)

        # normalize for cosine
        q_norm = F.normalize(q, dim=-1)
        k_norm = F.normalize(k, dim=-1)

        # variance trace: sum over head_dim
        var_trace = var_k.sum(dim=-1, keepdim=True).transpose(-2, -1)  # (B,H,1,S)

        # logits including -2 constant
        logits = compute_wasserstein_logits(q_norm, k_norm, var_trace,
                                            lambda_var, tau, self.head_dim)

        # mask
        if mask is not None:
            logits = logits.masked_fill(mask.unsqueeze(1).unsqueeze(2), float('-inf'))

        # attention weights
        attn = torch.softmax(logits, dim=-1)
        attn = self.dropout(attn)

        # output
        out = torch.matmul(attn, v)
        return out, attn


class CrossAttentionBlock(nn.Module):
    """
    Single cross-attention block using CosWassersteinAttention.
    """

    def __init__(self, d_model: int, nhead: int,
                 dim_feedforward: int = 2048,
                 dropout: float = 0.1,
                 activation: str = "relu"):
        super().__init__()
        assert d_model % nhead == 0, "d_model must be divisible by nhead"
        self.d_model = d_model
        self.nhead = nhead
        self.head_dim = d_model // nhead

        # projections
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

        # Wasserstein attention
        self.attn = CosWassersteinAttention(nhead, self.head_dim, dropout)

        # CLIP-style MLP
        self.mlp = nn.Sequential(OrderedDict([
            ("c_fc", nn.Linear(d_model, d_model * 4)),
            ("gelu", QuickGELU()),
            ("c_proj", nn.Linear(d_model * 4, d_model))
        ]))

        # norms and dropout
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.norm3 = nn.LayerNorm(d_model)
        self.norm4 = nn.LayerNorm(d_model)
        self.dropout_attn = nn.Dropout(dropout)
        self.dropout_ff = nn.Dropout(dropout)

    def forward(self,
                query: torch.Tensor,  # (B, T, D)
                key: torch.Tensor,  # (B, S, D)
                var: torch.Tensor,  # (B, S, D)
                attn_mask: torch.Tensor = None
                ):
        B, T, D = query.shape
        _, S, _ = key.shape

        # project + reshape
        q = self.q_proj(self.norm1(query)).view(B, T, self.nhead, self.head_dim).transpose(1, 2)
        k = self.k_proj(self.norm2(key)).view(B, S, self.nhead, self.head_dim).transpose(1, 2)
        v = self.v_proj(self.norm2(key)).view(B, S, self.nhead, self.head_dim).transpose(1, 2)
        var_k = var.view(B, S, self.nhead, self.head_dim).transpose(1, 2)

        # attention
        attn_out, attn_w = self.attn(q, k, v, var_k, attn_mask)

        # concat + proj
        attn_out = attn_out.transpose(1, 2).reshape(B, T, D)
        x = query + self.dropout_attn(self.out_proj(attn_out))

        # MLP
        x2 = self.mlp(self.norm3(x))
        x = x + self.dropout_ff(x2)
        x = self.norm4(x)
        return x, attn_w


class MemoryBank(nn.Module):
    def __init__(self, d_model: int, num_prototype=8):
        super().__init__()
        self.d_model = d_model
        self.num_prototype = num_prototype

        # Initialize prototype vectors with Xavier uniform initialization
        self.prototype = nn.Parameter(torch.zeros(self.num_prototype, self.d_model), requires_grad=True)
        nn.init.xavier_uniform_(self.prototype)

        # MLP for processing prototype attention weights (visual branch)
        self.video_mlp1 = nn.Sequential(OrderedDict([
            ("c_fc", nn.Linear(self.num_prototype, d_model)),
            ("gelu", QuickGELU()),
            ("c_proj", nn.Linear(d_model, d_model))
        ]))
        # Second MLP for visual features
        self.video_mlp2 = nn.Sequential(OrderedDict([
            ("c_fc", nn.Linear(d_model, d_model)),
            ("gelu", QuickGELU())  # Added activation for better flow
        ]))

        # MLP for processing prototype attention weights (text branch)
        self.text_mlp1 = nn.Sequential(OrderedDict([
            ("c_fc", nn.Linear(self.num_prototype, d_model)),
            ("gelu", QuickGELU()),
            ("c_proj", nn.Linear(d_model, d_model))
        ]))
        # Second MLP for text features
        self.text_mlp2 = nn.Sequential(OrderedDict([
            ("c_fc", nn.Linear(d_model, d_model)),
            ("gelu", QuickGELU())  # Added activation for consistency
        ]))

        # Initialize MLP weights properly
        for m in [self.video_mlp1, self.video_mlp2, self.text_mlp1, self.text_mlp2]:
            for name, param in m.named_parameters():
                if 'weight' in name:
                    if 'c_fc' in name:
                        nn.init.xavier_uniform_(param)
                    elif 'c_proj' in name:
                        nn.init.xavier_uniform_(param, gain=1e-5)  # Smaller gain for output layers
                elif 'bias' in name:
                    nn.init.constant_(param, 0.0)

        # Alpha parameter for controlling memory bank influence
        self.alpha = nn.Parameter(torch.tensor(0.0), requires_grad=False)
        # Temperature parameter for attention (optional)
        self.temperature = nn.Parameter(torch.tensor(1.0), requires_grad=True)

    def activation(self, x):
        return torch.where(x < 0, torch.zeros_like(x), torch.tanh(x))

    def forward(self, video_features: torch.Tensor):
        B, T, D = video_features.shape
        prototype = self.prototype / self.prototype.norm(dim=-1, keepdim=True)
        video_features = F.normalize(video_features, p=2, dim=-1)
        similarity = torch.matmul(video_features, prototype.t())  # (B, T, K)
        # for i in range(len(similarity)):
        #     print(f"video {i}", similarity[i])
        video_var = self.video_mlp1(similarity)  # (B, T, D)
        video_var = self.video_mlp2(video_var) + video_var  # (B, T, D)
        video_var = self.activation(video_var)

        # print(similarity.shape)# (B, T, D)

        text_var = self.text_mlp1(similarity)  # (B, T, D)
        text_var = text_var.mean(dim=-2)
        text_var = self.text_mlp2(text_var) + text_var
        text_var = self.activation(self.alpha * text_var)
        return text_var, video_var


class CrossAttentionStack(nn.Module):
    """
    Stack of CrossAttentionBlock layers.
    """

    def __init__(self, num_layers: int, d_model: int, nhead: int,
                 dim_feedforward: int = 2048,
                 dropout: float = 0.1,
                 activation: str = "relu"):
        super().__init__()
        self.layers = nn.ModuleList([
            CrossAttentionBlock(d_model, nhead,
                                dim_feedforward, dropout, activation)
            for _ in range(num_layers)
        ])
        self.memory_bank = MemoryBank(d_model, num_prototype=12)

    def query_sample(self, query: torch.Tensor, query_var: torch.Tensor, k_sample: int = 2):
        """
        Args:
            k_sample:
            query: (B, T, D)
            query_var: (B, D)
        Returns:
            sample_query: (B, T * k_sample, D)
        """
        return query
        # print(query.shape, query_var.shape)
        B, T, D = query.shape
        k = k_sample

        # 1. Random sampling T * k_sample times with mean 0 and variance query_var
        # Expand query_var to match the required shape (B, T, k_sample, D)
        std = torch.sqrt(query_var).unsqueeze(1).unsqueeze(2)  # (B, 1, 1, D)
        noise = torch.randn(B, T, k, D, device=query.device, dtype=query.dtype, ) * std * self.alpha_activate(
            self.alpha) * 0

        # 2. Add query to the noise
        # Expand query to match shape (B, T, k_sample, D)
        query_expanded = query.unsqueeze(2).expand(-1, -1, k, -1)  # (B, T, k, D)
        sampled = query_expanded + noise

        # 3. Reshape to (B, T * k_sample, D)
        sample_query = sampled.reshape(B, T * k, D)

        return sample_query

    def forward(
            self,
            query: torch.Tensor,  # (T, D)
            key: torch.Tensor,  # (B, S, D)
            attn_mask: torch.Tensor = None,
            k_sample: int = 2,
    ):
        batch_size = key.shape[0]  # b <=(b,M=4,512)
        query = query.unsqueeze(0).repeat(batch_size, 1, 1)
        query_var, video_var = self.memory_bank(key)
        weights = []

        query_sample = self.query_sample(query, query_var, k_sample)
        x = query_sample

        for layer in self.layers:
            x, w = layer(x, key, video_var, attn_mask)
            weights.append(w)
        return x

    # def forward(self, query, features):
    #     batch_size = features.shape[0]  # b <=(b,M=4,512)
    #     dim_num = features.shape[2]

    #     enco_others = features.permute(1, 0, 2)  # (M,b,512)
    #     h_attr = query # (a,512)

    #     if len(h_attr.size()) == 2: # (a,512)
    #         h_attr = h_attr.unsqueeze(0).repeat(batch_size, 1, 1)  # -> (b,a,512)
    #         h_attr_batch = h_attr.permute(1,0,2)  # -> (a,b,512)
    #     else:
    #         h_attr_batch = h_attr.permute(1,0,2) # (a=b,1,512)->(1,a=b,512) or (b,a,512)

    #     hs, _ = self.event_decoder(h_attr_batch, enco_others)  # query：(a,b,512), K,V：(M,b,512)
    #     hs = hs[-1].permute(1, 0, 2) # -> (B, a, 512)

    #     return hs


# ====== 测试示例 ======
if __name__ == "__main__":
    # 超参数
    B_V = 2  # 视频 batch
    B_T = 3  # 文本序列长度
    B_F = 4  # 视频帧数
    D = 8  # 特征维度
    H = 2  # 头数
    L = 2  # 层数

    # 随机输入
    query = torch.randn(B_V, B_T, D)
    key = torch.randn(B_V, B_F, D)
    # 模拟视频分布方差，非负
    var = torch.rand(B_V, B_F, D)
    # 可选掩码：屏蔽最后一帧
    attn_mask = torch.zeros(B_V, B_F)
    attn_mask[:, -1] = float('-inf')

    # 实例化 CrossAttentionStack
    model = CrossAttentionStack(num_layers=L, d_model=D, nhead=H)
    # 前向
    out, weights = model(query, key, var, attn_mask)

    print("输出形状:", out.shape)  # 期望 (B_V, B_T, D)
    print("注意力权重层数:", len(weights))  # 期望 L 层
    print("第一层权重形状:", weights[0].shape)  # 期望 (B_V, H, B_T, B_F)
