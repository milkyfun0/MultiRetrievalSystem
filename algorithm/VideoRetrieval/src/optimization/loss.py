import torch
import torch.nn.functional as F
from torch import nn
from torch.autograd import Variable
import torch.distributed as dist

def cosine_sim(im, s):
    """Cosine similarity between all the image and sentence pairs
    """
    return im.mm(s.t())


def order_sim(im, s):
    """Order embeddings similarity measure $max(0, s-im)$
    """
    YmX = (s.unsqueeze(1).expand(s.size(0), im.size(0), s.size(1))
           - im.unsqueeze(0).expand(s.size(0), im.size(0), s.size(1)))
    score = -YmX.clamp(min=0).pow(2).sum(2).sqrt().t()
    return score


class TripletContrastiveLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(TripletContrastiveLoss, self).__init__()
        self.margin = cfg.margin
        if cfg.measure == 'order':
            self.sim = order_sim
        else:
            self.sim = cosine_sim

        self.max_violation = cfg.max_violation

    def forward(self, im, s):
        # compute image-sentence score matrix
        scores = self.sim(im, s)
        diagonal = scores.diag().view(im.size(0), 1)
        d1 = diagonal.expand_as(scores)
        d2 = diagonal.t().expand_as(scores)

        # compare every diagonal score to scores in its column
        # caption.txt retrieval
        cost_s = (self.margin + scores - d1).clamp(min=0)
        # compare every diagonal score to scores in its row
        # image retrieval
        cost_im = (self.margin + scores - d2).clamp(min=0)

        # clear diagonals
        mask = torch.eye(scores.size(0)) > .5
        I = Variable(mask)
        if torch.cuda.is_available():
            I = I.cuda()
        cost_s = cost_s.masked_fill_(I, 0)
        cost_im = cost_im.masked_fill_(I, 0)

        # keep the maximum violating negative for each query
        if self.max_violation:
            cost_s = cost_s.max(1)[0]
            cost_im = cost_im.max(0)[0]

        return cost_s.sum() + cost_im.sum()


class NCEContrastiveLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(NCEContrastiveLoss, self).__init__()
        self.temp = cfg.temp

    def forward(self, vis_feat, text_feat):

        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) / self.temp  # temperature
        v2t = t2v.permute(1, 0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label
        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label)).mean()
        return loss


class HardNegLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(HardNegLoss, self).__init__()
        self.hard_negative_num = cfg.hard_negative_num

    def forward(self, vis_feat, text_feat):
        sim_matrix = torch.matmul(text_feat, vis_feat.permute(1, 0))  # temperature
        bsz = sim_matrix.shape[0]
        retrieval_mask = torch.eye(bsz, dtype=torch.long).to(device=sim_matrix.device)
        hard_neg_t2v = torch.topk(sim_matrix-10000*retrieval_mask, self.hard_negative_num, dim=1)[0]
        hard_neg_v2t = torch.topk(sim_matrix.transpose(0, 1)-10000*retrieval_mask, self.hard_negative_num, dim=1)[0]
        sample_t2v = torch.cat([sim_matrix.diag().view(-1, 1), hard_neg_t2v], -1)
        sample_v2t = torch.cat([sim_matrix.diag().view(-1, 1), hard_neg_v2t], -1)
        retrieval_label = torch.zeros(bsz, dtype=torch.long).to(device=sim_matrix.device)
        loss = (F.cross_entropy(sample_t2v, retrieval_label) + F.cross_entropy(sample_v2t, retrieval_label)).mean()
        return loss



class MILNCEContrastiveLoss(nn.Module):
    def __init__(self,cfg):
        super(MILNCEContrastiveLoss, self).__init__()
        self.temp = cfg.temp

    def forward(self, video_embd, text_embd):
        x = torch.matmul(video_embd, text_embd.t()) / self.temp

        x = x.view(video_embd.shape[0], video_embd.shape[0], -1)
        nominator = x * torch.eye(x.shape[0])[:,:,None].to(x.device)
        nominator = nominator.sum(dim=1)
        nominator = torch.logsumexp(nominator, dim=1)
        mask = (1-torch.eye(x.shape[0])[:,:,None].to(x.device).repeat(1,1,x.shape[-1]))
        denominator = torch.cat((x[mask>0].reshape(x.shape[0], x.shape[1]-1, x.shape[2]), x.permute(1,0,2)), dim=1).view(x.shape[0], -1)
        denominator = torch.logsumexp(denominator, dim=1)
        return torch.mean(denominator - nominator)
    

class VarianceLoss(nn.Module):
    """
    Compute Variance Loss
    """
    def __init__(self):
        super(VarianceLoss, self).__init__()
        self.mse = nn.MSELoss(reduce=True, size_average=True)

    # sims (K,K)
    def forward(self, prototype):
        prototype = prototype / prototype.norm(p=2, dim=-1, keepdim=True)  
        vv = prototype @ prototype.T
        K = vv.size(0)
        label = torch.zeros(vv.shape).to(vv.device)
        mask = 1 - torch.eye(K).to(vv.device)
        vv_m = mask * vv
        loss = self.mse(vv_m, label)
        return loss

class NCELearnableTempLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(NCELearnableTempLoss, self).__init__()
        self.cfg = cfg
        self.varianceLoss = VarianceLoss()


    def forward(self, vis_feat, text_feat, temp, proxy_logits=None, pos_logits=None):
        logit_scale = temp.exp()
        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        v2t = t2v.permute(1, 0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label

        if proxy_logits is not None:
            t2v_proxy = proxy_logits * logit_scale
            v2t_proxy = t2v_proxy.permute(1, 0)

        proxy_loss = 0 
        proxy_loss = proxy_loss + F.cross_entropy(t2v_proxy, t2v_label)
        proxy_loss = proxy_loss + F.cross_entropy(v2t_proxy, v2t_label, weight=pos_logits.detach().flatten())

        
        loss = 0
        loss = loss + F.cross_entropy(t2v, t2v_label)
        loss = loss + F.cross_entropy(v2t, v2t_label, weight=pos_logits.detach().flatten())

        loss = loss + self.cfg.L_pos_beta * proxy_loss

        # proxy_loss = F.cross_entropy(t2v_proxy, t2v_label) * self.cfg.L_p_alpha + F.cross_entropy(v2t_proxy, v2t_label) * self.cfg.L_p_alpha
        # pos_loss = F.cross_entropy(t2v_pos, t2v_label) * self.cfg.L_pos_beta + F.cross_entropy(v2t_pos, v2t_label) * self.cfg.L_pos_beta

        # loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label) + proxy_loss + pos_loss).mean()
        # loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label) + proxy_loss).mean()
        loss = loss + self.varianceLoss(pos_logits) * 0

        # print(F.cross_entropy(v2t_proxy, v2t_label).shape, pos_logits.shape)

        return loss
    
class NCELearnableOneToMany(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(NCELearnableOneToMany, self).__init__()
        self.cfg = cfg
        self.varianceLoss = VarianceLoss()

    def forward(self, vis_feat, text_feat, temp, proxy_logits=None, pos_logits=None):

        loss = 0

        logit_scale = temp.exp()
        label = torch.arange(vis_feat.shape[0], device=vis_feat.device)
        b_v = vis_feat.shape[0]
        k = text_feat.shape[0] // b_v
        global_sim = torch.matmul(text_feat, vis_feat.permute(1, 0)) * logit_scale  # temperature

        # t2v = global_sim.reshape(b_v, -1, b_v).transpose(-1, -2).mean(dim=-1)
        t2v = global_sim
        # t2v 在 axis = 1 维度复制k次然后 flatten
        t2v_label = label.repeat_interleave(k) # b_v * k, b_v 

        # v2t = global_sim.reshape(b_v, -1, b_v)[:, 0, :].T
        v2t = global_sim.reshape(b_v, -1, b_v).transpose(-1, -2).mean(dim=-1).T

        v2t_label = label
        
        loss =  loss + (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label)).mean()


        if proxy_logits is not None:
            cross_sim = proxy_logits * logit_scale
            # t2v_proxy = cross_sim.reshape(b_v, -1, b_v).transpose(-1, -2).mean(dim=-1)
            t2v_proxy = cross_sim
            v2t_proxy = cross_sim.reshape(b_v, -1, b_v).transpose(-1, -2).mean(-1)
            loss = loss + F.cross_entropy(t2v_proxy, t2v_label) * self.cfg.L_p_alpha + F.cross_entropy(
                v2t_proxy, v2t_label) * self.cfg.L_p_alpha
            
        # pos_loss = F.cross_entropy(t2v_pos, t2v_label) * self.cfg.L_pos_beta + F.cross_entropy(v2t_pos, v2t_label) * self.cfg.L_pos_beta
        # loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label) + proxy_loss + pos_loss).mean()
        # k 是由 一个text feature 多次采样得到的 
        # loss = loss + self.varianceLoss(pos_logits) * 100
        # t2t = torch.matmul(text_feat, text_feat.permute(1, 0)) * logit_scale # b_v x k, b_v x k
        # 补充下面缺失的多正样本对比学习函数，一条数据有 k-1 条正样本 和 他自己，其他是负样本
        # sim 矩阵：N x N
        # device = vis_feat.device
        # N = text_feat.shape[0]                  # 文本样本总数 = b_v * k
        # t2t = torch.matmul(text_feat, text_feat.t()) * logit_scale
        # # # 构造同组掩码
        # group_mask = t2v_label.unsqueeze(1).eq(t2v_label.unsqueeze(0))  # [N, N]
        # self_mask = torch.eye(N, device=device).bool()                 # [N, N]
        # pos_mask = group_mask & ~self_mask                           # 排除自身 [N, N]
        # # log.txt-softmax
        # log_prob = F.log_softmax(t2t, dim=1)                            # [N, N]
        # # 每个 anchor 上，对 positives 求平均
        # # loss_i = -1/(k-1) * sum_{j∈Pos(i)} log.txt p_{ij}
        # loss_t2t = -(pos_mask.float() * log_prob).sum(dim=1) / (k - 1)  # [N]
        # loss += loss_t2t.mean() * 0.1
        # print(loss_t2t.mean())
        return loss
    
class NCELearnableTextSample(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(NCELearnableTextSample, self).__init__()
        self.cfg = cfg
        self.varianceLoss = VarianceLoss()

    def forward(self, vis_feat, text_feat, temp, proxy_logits=None, pos_logits=None):
        """
        Args:
            vis_feat: Visual features [b_v, d]
            text_feat: Text features [b_v, d]
            temp: Temperature parameter [scalar]
            proxy_logits: Proxy logits [b_v, k, b_v]
            pos_logits: (未使用，可移除)
        """
        loss = 0
        device = vis_feat.device
        b_v = vis_feat.shape[0]  # 批量大小

        logit_scale = temp.exp()
        label = torch.arange(b_v, device=device)

        global_sim = torch.matmul(text_feat, vis_feat.t()) * logit_scale  # [b_v, b_v]

        t2v_loss = F.cross_entropy(global_sim, label)
        v2t_loss = F.cross_entropy(global_sim.t(), label)

        loss = loss + (t2v_loss + v2t_loss)

        if proxy_logits is not None:
            
            k = proxy_logits.size(0) // proxy_logits.size(1)  # 每个样本的代理数
            cross_sim = proxy_logits * logit_scale  # [b_v, k, b_v]

            t2v_proxy = cross_sim.reshape(-1, b_v)  # [b_v * k, b_v]
            t2v_label = label.unsqueeze(1).repeat(1, k).flatten()  # [b_v * k]

            v2t_proxy = cross_sim.reshape(b_v, k, b_v).permute(1, 0, 2).reshape(k * b_v, b_v)
            v2t_label = label.unsqueeze(0).repeat(k, 1).flatten()

            proxy_loss = F.cross_entropy(t2v_proxy, t2v_label) + F.cross_entropy(v2t_proxy, v2t_label)
            loss = loss + proxy_loss * self.cfg.L_p_alpha

        return loss


class VidImgNCELearnableTempLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(VidImgNCELearnableTempLoss, self).__init__()

    def forward(self, vis_feat, text_feat, img_feat, cap_feat, temp):
        vis_feat = torch.cat([vis_feat, img_feat], dim=0)
        text_feat = torch.cat([text_feat, cap_feat], dim=0)
        logit_scale = temp.exp()
        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        v2t = t2v.permute(1, 0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label
        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label)).mean()
        return loss

class VidImgDivideNCELearnableTempLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(VidImgDivideNCELearnableTempLoss, self).__init__()

    def forward(self, vis_feat, text_feat, img_feat, cap_feat, temp):
        logit_scale = temp.exp()
        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        v2t = t2v.permute(1, 0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label

        t2v_2 = torch.matmul(img_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        v2t_2 = t2v_2.permute(1, 0)
        t2v_label_2 = torch.arange(t2v_2.shape[0], device=t2v_2.device)
        v2t_label_2 = t2v_label_2
        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label) +\
            F.cross_entropy(t2v_2, t2v_label_2) + F.cross_entropy(v2t_2, v2t_label_2)).mean()
        return loss

class NCELearnableTempDSLLoss(nn.Module):
    """
    Compute contrastive loss
    """

    def __init__(self, cfg):
        super(NCELearnableTempDSLLoss, self).__init__()

    def forward(self, vis_feat, text_feat, temp):
        logit_scale = temp.exp()
        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        v2t = t2v.permute(1, 0)
        t2v = t2v * F.softmax(t2v, dim=0)
        v2t = v2t * F.softmax(v2t, dim=0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label
        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label)).mean()
        return loss

class NCELearnableTempLoss_vs_vc(nn.Module):
    """
    Compute contrastive loss: video-sub + video-cap
    """

    def __init__(self, cfg):
        super(NCELearnableTempLoss_vs_vc, self).__init__()

    def forward(self, vis_feat, text_feat, img_feat, cap_feat, temp):
        logit_scale = temp.exp()
        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        v2t = t2v.permute(1, 0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label

        t2v_2 = torch.matmul(vis_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        v2t_2 = t2v_2.permute(1, 0)
        t2v_label_2 = torch.arange(t2v_2.shape[0], device=t2v_2.device)
        v2t_label_2 = t2v_label_2
        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label) + \
            F.cross_entropy(t2v_2, t2v_label_2) + F.cross_entropy(v2t_2, v2t_label_2)).mean()
        return loss

class NCELearnableTempLoss_vs_vc_fc(nn.Module):
    """
    Compute contrastive loss: video-sub + video-cap
    """

    def __init__(self, cfg):
        super(NCELearnableTempLoss_vs_vc_fc, self).__init__()

    def forward(self, vis_feat, text_feat, img_feat, cap_feat, temp):
        logit_scale = temp.exp()
        t2v = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        v2t = t2v.permute(1, 0)
        t2v_label = torch.arange(t2v.shape[0], device=t2v.device)
        v2t_label = t2v_label

        t2v_2 = torch.matmul(vis_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        v2t_2 = t2v_2.permute(1, 0)
        t2v_label_2 = torch.arange(t2v_2.shape[0], device=t2v_2.device)
        v2t_label_2 = t2v_label_2

        t2v_3 = torch.matmul(img_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        v2t_3 = t2v_3.permute(1, 0)
        t2v_label_3 = torch.arange(t2v_3.shape[0], device=t2v_3.device)
        v2t_label_3 = t2v_label_3
        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(v2t, v2t_label) + \
            F.cross_entropy(t2v_2, t2v_label_2) + F.cross_entropy(v2t_2, v2t_label_2) +\
            F.cross_entropy(t2v_3, t2v_label_3) + F.cross_entropy(v2t_3, v2t_label_3)).mean()
        return loss

class NCELearnableTempLoss_vsc(nn.Module):
    """
    Compute contrastive loss: video-(sub,cap)
    """

    def __init__(self, cfg):
        super(NCELearnableTempLoss_vsc, self).__init__()

    def forward(self, vis_feat, text_feat, img_feat, cap_feat, temp):
        assert text_feat.shape[0] == cap_feat.shape[0]
        logit_scale = temp.exp()
        v2t = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        t2v = v2t.permute(1, 0)
        t2v_label = torch.arange(v2t.shape[0], device=v2t.device)

        v2t_2 = torch.matmul(vis_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        t2v_2 = v2t_2.permute(1, 0)
        t2v_label_2 = torch.arange(v2t_2.shape[0], device=v2t_2.device)

        diag = torch.eye(v2t.shape[0], dtype=torch.bool).to(v2t.device)
        v2t_pos = v2t[diag].reshape(v2t.shape[0], 1)
        v2t_neg = v2t[~diag].reshape(v2t.shape[0], -1)
        v2t_pos_2 = v2t_2[diag].reshape(v2t_2.shape[0], 1)
        v2t_neg_2 = v2t_2[~diag].reshape(v2t_2.shape[0], -1)
        v2t = torch.cat([v2t_pos, v2t_neg, v2t_neg_2], dim=1)
        v2t_2 = torch.cat([v2t_pos_2, v2t_neg, v2t_neg_2], dim=1)
        v2t_label = torch.zeros(v2t.shape[0], dtype=torch.long).to(v2t.device)

        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(t2v_2, t2v_label_2) + \
            F.cross_entropy(v2t, v2t_label) + F.cross_entropy(v2t_2, v2t_label)).mean()
        return loss

class NCELearnableTempLoss_vsc_fc(nn.Module):
    """
    Compute contrastive loss: video-(sub,cap)
    """

    def __init__(self, cfg):
        super(NCELearnableTempLoss_vsc_fc, self).__init__()

    def forward(self, vis_feat, text_feat, img_feat, cap_feat, temp):
        assert text_feat.shape[0] == cap_feat.shape[0]
        logit_scale = temp.exp()
        v2t = torch.matmul(vis_feat, text_feat.permute(1, 0)) * logit_scale  # temperature
        t2v = v2t.permute(1, 0)
        t2v_label = torch.arange(v2t.shape[0], device=v2t.device)

        v2t_2 = torch.matmul(vis_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        t2v_2 = v2t_2.permute(1, 0)
        t2v_label_2 = torch.arange(v2t_2.shape[0], device=v2t_2.device)

        diag = torch.eye(v2t.shape[0], dtype=torch.bool).to(v2t.device)
        v2t_pos = v2t[diag].reshape(v2t.shape[0], 1)
        v2t_neg = v2t[~diag].reshape(v2t.shape[0], -1)
        v2t_pos_2 = v2t_2[diag].reshape(v2t_2.shape[0], 1)
        v2t_neg_2 = v2t_2[~diag].reshape(v2t_2.shape[0], -1)
        v2t = torch.cat([v2t_pos, v2t_neg, v2t_neg_2], dim=1)
        v2t_2 = torch.cat([v2t_pos_2, v2t_neg, v2t_neg_2], dim=1)
        v2t_label = torch.zeros(v2t.shape[0], dtype=torch.long).to(v2t.device)

        v2t_3 = torch.matmul(img_feat, cap_feat.permute(1, 0)) * logit_scale  # temperature
        t2v_3 = v2t_3.permute(1, 0)
        t2v_label_3 = torch.arange(t2v_3.shape[0], device=t2v_3.device)
        v2t_label_3 = t2v_label_3

        loss = (F.cross_entropy(t2v, t2v_label) + F.cross_entropy(t2v_2, t2v_label_2) + \
            F.cross_entropy(v2t, v2t_label) + F.cross_entropy(v2t_2, v2t_label) + \
            F.cross_entropy(t2v_3, t2v_label_3) + F.cross_entropy(v2t_3, v2t_label_3)).mean()
        return loss

def build_loss_func(cfg):
    loss_func = globals()[cfg.loss_name](cfg)
    return loss_func

if __name__ == '__main__':
    from easydict import EasyDict as edict
    cfg = edict({'loss_name':'MILNCELoss', 'temp':0.05})
    print(cfg.loss_name)
    loss_func = build_loss_func(cfg)
    print(loss_func.temp)
    video_embd = torch.randn(64,1024)
    text_embd = torch.randn(1280,1024)
    print(loss_func(video_embd, text_embd))


