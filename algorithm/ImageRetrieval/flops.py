#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/4/13 上午12:32
# @Author  : CaoQixuan
# @File    : flops.py
# @Description :
import torch

import torch
from thop import profile, clever_format

from dataset import get_loader
from models.base_distill.base_distall import Network
from utils import get_options, params_count
from ptflops import get_model_complexity_info


def calculate_thop_flops(net, x):
    flops, params = profile(net, inputs=(x,))
    flops, params = clever_format([flops, params], '%.3f')
    print(f"运算量：{flops}, 参数量：{params}")
    print(params_count(net))


def calculate_ptflops_flops(net, x):
    flops, params = get_model_complexity_info(net, (3, 224, 224), as_strings=True, print_per_layer_stat=True)
    print(f"模型 FLOPs: {flops}")
    print(f"模型参数量: {params}")


import time


# 假设你有一个模型 `model` 和输入 `input_tensor`
def measure_execution_time(net, input_tensor):
    start_time = time.time()  # 记录开始时间
    output = net(input_tensor)  # 执行模型
    end_time = time.time()  # 记录结束时间
    execution_time = end_time - start_time
    print(f"模型执行时间: {execution_time * 1000:.6f} 秒")
    return output


if __name__ == '__main__':
    opt = get_options(model_name="base_distill")
    model = Network(opt)
    model.eval()
    image = torch.rand(1, 3, 224, 224)
    # measure_execution_time(model.visual_student, image)
    calculate_thop_flops(model.visual_student, image)
    calculate_ptflops_flops(model.visual_student, image)
