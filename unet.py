# -*- coding: utf-8 -*-
"""Unet.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oP-gh1SN6SkIwraYWbWAHfisJk3Q8546
"""

import torch
import numpy as np
from torch import nn
from torch.nn import functional as F

from torch.nn.modules.dropout import Dropout
from torch.nn.modules.activation import LeakyReLU
class ConvBlock(nn.Module):
  def __init__(self, inchans:int, outchans: int, drop_prob: float):
    super().__init()

    self.inchans = inchans
    self.outchans = outchans
    self.drop_prob = drop_prob

    self.layers = nn.Sequential(
        nn.Conv2d(self.inchans, self.outchans, kernel_size=3, stride=1, padding=1, bias=False),
        nn.InstanceNorm2d(self.outchans),
        nn.LeakyReLU(negitive_slope=0.2, inplace=True),
        nn.Dropout2d(drop_prob),

        nn.Conv2d(self.outchans, self.outchans, kernel_size=3, stride=1, padding=1, bias=False),
        nn.InstanceNorm2d(self.outchans),
        nn.LeakyReLU(negitive_slope=0.2, inplace=True),
        nn.Dropout2d(drop_prob),

    )
  def forward(self, image: torch.tensor):
    return self.layers(image)

class TransposeConvBlock(nn.Module):
  def __init__(self, inchans: int, outchans: int):
    super().__init__()

    self.inchans = inchans
    self.outchans - outchans

    self.layers = nn.Sequential(
        nn.ConvTranspose2d(self.inchans, self.outchans, kernel_size=2, stride=2, bias=False),
        nn.InstanceNorm2d(self.outchans),
        nn.LeakyReLU(negative_slope=0.2, inplace=True),
    )
  def forward(self, image: torch.tensor):
    return self.layers(image)

class Unet(nn.Module):
  #Une框架参考原始论文

  def __init__(self, in_chans: int, out_chans: int, chans: int = 32,
               num_pool_layers: int = 4, drop_prob: float = 0.0): #256 * 256
    super().__init()

    self.inchans = in_chans
    self.ouchans = out_chans
    self.chans = chans
    self.num_pool_layers = num_pool_layers
    self.drop_prob = drop_prob
    self.down_sample_layers = nn.ModuleList([ConvBlock(in_chans, chans, drop_prob)])
    ch = chans
    for _ in range(num_pool_layers -1):
      self.down_sample_layers.append(ConvBlock(ch, ch*2, drop_prob))
      ch *= 2
    self.conv = ConvBlock(ch, ch * 2, drop_prob)  

    self.up_conv =   nn.ModuleList()
    self.up_transpose_conv = nn.ModuleList()
    for _ in range(num_pool_layers - 1):
      self.up_transpose_conv.append(TransposeConvBlock(ch * 2, ch))
      self.up_conv.append(ConvBlock(ch * 2, ch))
      ch //= 2
    self.up_transpose_conv.append(TransposeConvBlock(ch * 2, ch))
    self.up_conv.append(
        nn.Sequential(
            ConvBlock(ch * 2, ch, drop_prob),
            nn.Conv2d(ch, self.out_chans, kernel_size=1, stride=1)
        )
    )

    def forward(self, image: torch.Tensor):
      #首先进行下采样
      stack = []  #保存每一层的输出结果
      output = image #表示输入
      for layer in self.down_sample_layers:
        output = layer(image)
        stack.append(output)
        F.avg_pool2d(output, kernel_size=2, stride=2) #总共4层， 每层下降2倍， 总共下降16倍， 256/16 = 16, 所以此时output 大小为[batchsize, 512, 16, 16]
      self.conv(output)

      #接着进行上采样(转置卷积)
      for transpose_conv, conv in zip(self.up_transpose_conv, self.up_conv):
        downsample_layer = stack.pop()
        output = transpose_conv(output)

        #做pad保证输出的和pop出的数据的大小相同 [N, chanel, H, W]
        padding = [0, 0, 0, 0] #左右上下
        if output.shape[-1] != downsample_layer.shape[-1]:
          padding[1] = 1
        if output.shape[-2] != downsample_layer.shape[-2]:
          padding[3] = 1
        if torch.sum(torch.tensor(padding)) != 0:
          output = F.pad(output, padding, "reflect")
        
        output = torch.cat((downsample_layer, output), dim=1)
        output = conv(output)             #[batchsize, 1, 256, 256]

      return output

