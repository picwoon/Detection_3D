# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
import torch

from .box_head_3d.box_head import build_roi_box_head
from .mask_head_3d.mask_head import build_roi_mask_head


class CombinedROIHeads(torch.nn.ModuleDict):
    """
    Combines a set of individual heads (for box prediction or masks) into a single
    head.
    """

    def __init__(self, cfg, heads):
        super(CombinedROIHeads, self).__init__(heads)
        self.cfg = cfg.clone()
        if cfg.MODEL.MASK_ON and cfg.MODEL.ROI_MASK_HEAD.SHARE_BOX_FEATURE_EXTRACTOR:
            self.mask.feature_extractor = self.box.feature_extractor

    def forward(self, features, proposals, targets=None):
        losses = {}
        # TODO rename x to roi_box_features, if it doesn't increase memory consumption
        x, detections, loss_box = self.box(features, proposals, targets)
        losses.update(loss_box)
        if self.cfg.MODEL.MASK_ON:
            mask_features = features
            # optimization: during training, if we share the feature extractor between
            # the box and the mask heads, then we can reuse the features already computed
            if (
                self.training
                and self.cfg.MODEL.ROI_MASK_HEAD.SHARE_BOX_FEATURE_EXTRACTOR
            ):
                mask_features = x
            # During training, self.box() will return the unaltered proposals as "detections"
            # this makes the API consistent during training and testing
            x, detections, loss_mask = self.mask(mask_features, detections, targets)
            losses.update(loss_mask)
        return x, detections, losses


def build_roi_heads__(cfg):
  sep_classes = cfg.MODEL.SEPERATE_CLASSES
  if len(cfg.MODEL.SEPERATE_CLASSES) == 0:
    return build_roi_heads_(cfg), None
  else:
    cfg0 = cfg.clone()
    cfg1 = cfg.clone()
    cfg0['INPUT']['CLASSES'] = ['background'] + sep_classes
    cfg1['INPUT']['CLASSES'] = cfg.MODEL.REMAIN_CLASSES
    cfg0['MODEL']['SEPERATE_CLASSES'] = []
    cfg1['MODEL']['SEPERATE_CLASSES'] = []
    roi_heads0 = build_roi_heads_(cfg0)
    roi_heads1 = build_roi_heads_(cfg1)
    return roi_heads0, roi_heads1

def build_roi_heads(cfg):
    # individually create the heads, that will be combined together
    # afterwards
    roi_heads = []
    if not cfg.MODEL.RPN_ONLY:
        roi_heads.append(("box", build_roi_box_head(cfg)))

    # combine individual heads in a single module
    if roi_heads:
        roi_heads = CombinedROIHeads(cfg, roi_heads)

    return roi_heads
