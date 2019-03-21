# xyz Jan 2019

import torch
import torch.nn as nn
import sparseconvnet as scn
from .sparseConvNetTensor import SparseConvNetTensor

DEBUG = False


class FPN_Net(torch.nn.Module):
    _show = DEBUG
    def __init__(self, full_scale, dimension, raw_elements, reps, nPlanesF, nPlaneM, residual_blocks,
                  fpn_scales, downsample=[[2,2,2], [2,2,2]], leakiness=0):
        '''
        downsample:[kernel, stride]
        '''
        nn.Module.__init__(self)

        self.down_kernels =  downsample[0]
        self.down_strides = downsample[1]
        self.fpn_scales = fpn_scales
        scale_num = len(nPlanesF)
        assert len(self.down_kernels) == scale_num - 1 == len(self.down_strides), f"nPlanesF len = {scale_num}, kernels num = {len(self.down_kernels)}"
        assert all([len(ks)==3 for ks in self.down_kernels])
        assert all([len(ss)==3 for ss in self.down_strides])
        self._merge = 'add'  # 'cat' or 'add'

        ele_channels = {'xyz':3, 'normal':3, 'color':3}
        in_channels = sum([ele_channels[e] for e in raw_elements])

        self.layers_in = scn.Sequential(
                scn.InputLayer(dimension,full_scale, mode=4),
                scn.SubmanifoldConvolution(dimension, in_channels, nPlanesF[0], 3, False))

        self.layers_out = scn.Sequential(
            scn.BatchNormReLU(nPlanesF[0]),
            scn.OutputLayer(dimension))

        self.linear = nn.Linear(nPlanesF[0], 20)

        #**********************************************************************#

        def block(m, a, b):
            if residual_blocks: #ResNet style blocks
                m.add(scn.ConcatTable()
                      .add(scn.Identity() if a == b else scn.NetworkInNetwork(a, b, False))
                      .add(scn.Sequential()
                        .add(scn.BatchNormLeakyReLU(a,leakiness=leakiness))
                        .add(scn.SubmanifoldConvolution(dimension, a, b, 3, False))
                        .add(scn.BatchNormLeakyReLU(b,leakiness=leakiness))
                        .add(scn.SubmanifoldConvolution(dimension, b, b, 3, False)))
                 ).add(scn.AddTable())
            else: #VGG style blocks
                m.add(scn.Sequential()
                     .add(scn.BatchNormLeakyReLU(a,leakiness=leakiness))
                     .add(scn.SubmanifoldConvolution(dimension, a, b, 3, False)))

        def down(m, nPlane_in, nPlane_downed, scale):
            m.add(scn.Sequential()
                  .add(scn.BatchNormLeakyReLU(nPlane_in,leakiness=leakiness))
                  .add(scn.Convolution(dimension, nPlane_in, nPlane_downed,
                          self.down_kernels[scale], self.down_strides[scale], False)))

        def up(m, nPlane_in, nPlane_uped, scale):
           m.add( scn.BatchNormLeakyReLU(nPlane_in, leakiness=leakiness)).add(
                      scn.Deconvolution(dimension, nPlane_in, nPlane_uped,
                      self.down_kernels[scale], self.down_strides[scale], False))


        scales_num = len(nPlanesF)
        m_downs = nn.ModuleList()
        m_shortcuts = nn.ModuleList()
        for k in range(scales_num):
            m = scn.Sequential()
            if k > 0:
              down(m, nPlanesF[k-1], nPlanesF[k], k-1)
            for _ in range(reps):
                block(m, nPlanesF[k], nPlanesF[k])
            m_downs.append(m)

            m = scn.SubmanifoldConvolution(dimension, nPlanesF[k], nPlaneM, 1, False)
            m_shortcuts.append(m)

        ###
        m_ups = nn.ModuleList()
        m_mergeds = nn.ModuleList()
        for k in range(scales_num-1, 0, -1):
            m = scn.Sequential()
            up(m, nPlaneM, nPlaneM, k-1)
            m_ups.append(m)

            m_mergeds.append(scn.SubmanifoldConvolution(dimension, nPlaneM, nPlaneM, 3, False))

            #m = scn.Sequential()
            #for i in range(reps):
            #    block(m, nPlanesF[k-1] * (1+int(self._merge=='cat') if i == 0 else 1), nPlanesF[-1])
            #m_ups_decoder.append(m)

        self.m_downs = m_downs
        self.m_shortcuts = m_shortcuts
        self.m_ups = m_ups
        self.m_mergeds = m_mergeds

    def forward(self, net0):
      if self._show: print(f'\ninput: {net0[0].shape}')
      net1 = self.layers_in(net0)
      net_scales = self.forward_fpn(net1)

      #net_scales = [n.to_dict() for n in net_scales]

      return net_scales
      #net = net_scales[-1]
      #net = self.layers_out(net)
      #net = self.linear(net)

      #if self._show:
      #  print(f'\nend {net.shape}\n')
      #return net

    def forward_fpn(self, net):
      #if self._show:
      #  print('FPN_Net input:')
      #  sparse_shape(net)

      scales_num = len(self.m_downs)
      downs = []
      #if self._show:    print('\ndowns:')
      for m in self.m_downs:
        net = m(net)
        #if self._show:  sparse_shape(net)
        downs.append(net)

      net = self.m_shortcuts[-1](net)
      ups = [net]
      #if self._show:    print('\nups:')
      fpn_scales_from_back = [scales_num-1-i for i in self.fpn_scales]
      fpn_scales_from_back.sort()
      for k in range(scales_num-1):
        if k >= max(fpn_scales_from_back):
          continue
        j = scales_num-1-k-1
        net = self.m_ups[k](net)
        #if self._show:  sparse_shape(net)
        shorcut = self.m_shortcuts[j]( downs[j] )
        net = scn.add_feature_planes([ net, shorcut ])
        #net = self.m_ups_decoder[k](net)
        #if self._show:  sparse_shape(net)
        ups.append(self.m_mergeds[k](net))

      fpn_maps = [ups[i] for i in fpn_scales_from_back]

      if self._show:
        print('\n\ndowns:')
        [sparse_shape(t) for t in downs]

        print('\n\nups:')
        [sparse_shape(t) for t in ups]

        print('\n\nFPN_Net out:')
        [sparse_shape(t) for t in fpn_maps]
        [sparse_real_size(t) for t in fpn_maps]
      return fpn_maps


def sparse_shape(t):
  print(f'{t.features.shape}, {t.spatial_size}')

def sparse_real_size(t):
  loc = t.get_spatial_locations()
  loc_min = loc.min(0)[0]
  loc_max = loc.max(0)[0]
  print(f"\nmin: {loc_min}\nmax: {loc_max}")
