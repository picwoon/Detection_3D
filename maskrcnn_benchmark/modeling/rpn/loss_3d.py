# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
"""
This file contains specific functions for computing losses on the RPN
file
"""

import torch
from torch.nn import functional as F

from ..balanced_positive_negative_sampler import BalancedPositiveNegativeSampler
from ..utils import cat

from maskrcnn_benchmark.layers import smooth_l1_loss
from maskrcnn_benchmark.modeling.matcher import Matcher
from maskrcnn_benchmark.structures.boxlist3d_ops import boxlist_iou_3d, cat_boxlist_3d

DEBUG = True
SHOW_POS_NEG_ANCHORS = DEBUG and True
SHOW_PRED_GT = DEBUG and False
SHOW_POS_ANCHOR_IOU = DEBUG and False

class RPNLossComputation(object):
    """
    This class computes the RPN loss.
    """

    def __init__(self, proposal_matcher, fg_bg_sampler, box_coder):
        """
        Arguments:
            proposal_matcher (Matcher)
            fg_bg_sampler (BalancedPositiveNegativeSampler)
            box_coder (BoxCoder)
        """
        # self.target_preparator = target_preparator
        self.proposal_matcher = proposal_matcher
        self.fg_bg_sampler = fg_bg_sampler
        self.box_coder = box_coder

    def match_targets_to_anchors(self, anchor, target):
        if target.bbox3d.shape[0] == 0:
          matched_idxs = torch.ones([anchor.bbox3d.shape[0]], dtype=torch.int64, device=anchor.bbox3d.device) * (-1)
          matched_targets = anchor
        else:
          match_quality_matrix = boxlist_iou_3d(anchor, target)
          matched_idxs = self.proposal_matcher(match_quality_matrix)
          #anchor.show_together(target, 200)
          # RPN doesn't need any fields from target
          # for creating the labels, so clear them all
          target = target.copy_with_fields([])
          # get the targets corresponding GT for each anchor
          # NB: need to clamp the indices because we can have a single
          # GT in the image, and matched_idxs can be -2, which goes
          # out of bounds
          matched_targets = target[matched_idxs.clamp(min=0)]
        matched_targets.add_field("matched_idxs", matched_idxs)

        if SHOW_POS_ANCHOR_IOU:
          num_gt = target.bbox3d.shape[0]
          for j in range(num_gt):
            sampled_pos_inds = torch.nonzero(matched_idxs==j).squeeze(1)
            #sampled_pos_inds = torch.nonzero(match_quality_matrix[j] > 0.3).squeeze(1)

            iou_j = match_quality_matrix[j][sampled_pos_inds]
            anchors_pos_j = anchor[sampled_pos_inds]
            print(f'{iou_j.shape[0]} anchor matched as positive. All anchor centroids are shown.')
            anchors_pos_j.show_together(target[j], points=anchor.bbox3d[:,0:3])

            for i in range(iou_j.shape[0]):
              print(f'{i}th iou: {iou_j[i]}')
              anchors_pos_j[i].show_together(target[j])
            #anchor.show_together(target[j],100)
            import pdb; pdb.set_trace()  # XXX BREAKPOINT
            pass

        return matched_targets

    def prepare_targets(self, anchors, targets):
        labels = []
        regression_targets = []
        batch_size = anchors.batch_size()
        assert batch_size == len(targets)
        for bi in range(batch_size):
            # merge anchors of all scales
            anchors_per_image = anchors.example(bi)
            targets_per_image = targets[bi]

            matched_targets = self.match_targets_to_anchors(
                anchors_per_image, targets_per_image
            )

            matched_idxs = matched_targets.get_field("matched_idxs")
            labels_per_image = matched_idxs >= 0
            labels_per_image = labels_per_image.to(dtype=torch.float32)
            # discard anchors that go out of the boundaries of the image
            #labels_per_image[~anchors_per_image.get_field("visibility")] = -1

            # discard indices that are between thresholds
            inds_to_discard = matched_idxs == Matcher.BETWEEN_THRESHOLDS
            labels_per_image[inds_to_discard] = -1

            # compute regression targets
            regression_targets_per_image = self.box_coder.encode(
                matched_targets.bbox3d, anchors_per_image.bbox3d
            )

            labels.append(labels_per_image)
            regression_targets.append(regression_targets_per_image)

        return labels, regression_targets

    def __call__(self, anchors, objectness, box_regression, targets):
        """
        Arguments:
            anchors (BoxList): box num: N
            objectness (list[Tensor]): len=scale_num
            box_regression (list[Tensor]): len=scale_num
            targets (list[BoxList]): len = batch size

        Returns:
            objectness_loss (Tensor)
            box_loss (Tensor
        """
        labels, regression_targets = self.prepare_targets(anchors, targets)
        sampled_pos_inds, sampled_neg_inds = self.fg_bg_sampler(labels)
        sampled_pos_inds = torch.nonzero(torch.cat(sampled_pos_inds, dim=0)).squeeze(1)
        sampled_neg_inds = torch.nonzero(torch.cat(sampled_neg_inds, dim=0)).squeeze(1)

        batch_size = anchors.batch_size()

        if SHOW_POS_NEG_ANCHORS:
            assert batch_size == 1
            #anchors_per_image = cat_boxlist_3d(anchors)
            anchors_per_image = anchors
            anchor_num = anchors_per_image.bbox3d.shape[0]
            targets_per_image = targets[0]

            anchors_pos = anchors_per_image[sampled_pos_inds]
            pos_num = sampled_pos_inds.shape[0]
            print(f'totally {pos_num}/{anchor_num} positive anchors')
            anchors_pos.show_together(targets[0])

            show_1_by_1 = False
            if show_1_by_1:
              for ai in range(pos_num):
                anchors_pos_ai = anchors_per_image[sampled_pos_inds[ai:ai+1]]
                anchors_pos_ai.show_together(targets[0])

            anchors_neg = anchors_per_image[sampled_neg_inds]
            print(f'totally {sampled_neg_inds.shape[0]}/{anchor_num} negative anchors')
            anchors_neg.show_together(targets[0])
            import pdb; pdb.set_trace()  # XXX BREAKPOINT
            pass

        sampled_inds = torch.cat([sampled_pos_inds, sampled_neg_inds], dim=0)

        objectness_flattened = []
        box_regression_flattened = []
        # for each feature level, permute the outputs to make them be in the
        # same format as the labels. Note that the labels are computed for
        # all feature levels concatenated, so we keep the same representation
        # for the objectness and the box_regression
        for objectness_per_level, box_regression_per_level in zip(
            objectness, box_regression
        ):
            N, A, H, W = objectness_per_level.shape
            objectness_per_level = objectness_per_level.permute(0, 2, 3, 1).reshape(
                N, -1
            )
            box_regression_per_level = box_regression_per_level.view(N, -1, 7, H, W)
            box_regression_per_level = box_regression_per_level.permute(0, 3, 4, 1, 2)
            box_regression_per_level = box_regression_per_level.reshape(N, -1, 7)
            objectness_flattened.append(objectness_per_level)
            box_regression_flattened.append(box_regression_per_level)
        # concatenate on the first dimension (representing the feature levels), to
        # take into account the way the labels were generated (with all feature maps
        # being concatenated as well)
        objectness = cat(objectness_flattened, dim=1).reshape(-1)
        box_regression = cat(box_regression_flattened, dim=1).reshape(-1, 7)

        labels = torch.cat(labels, dim=0)
        regression_targets = torch.cat(regression_targets, dim=0)

        box_loss = smooth_l1_loss(
            box_regression[sampled_pos_inds],
            regression_targets[sampled_pos_inds],
            beta=1.0 / 9,
            size_average=False,
        ) / (sampled_inds.numel())

        objectness_loss = F.binary_cross_entropy_with_logits(
            objectness[sampled_inds], labels[sampled_inds]
        )

        if SHOW_PRED_GT:
            examples_idxscope = anchors.examples_idxscope
            for bi in range(batch_size):
              import numpy as np
              idxs_i = examples_idxscope[bi].to(sampled_pos_inds.device).to(torch.int64)
              mask_i = (sampled_pos_inds >= idxs_i[0]) * (sampled_pos_inds < idxs_i[1])
              sampled_pos_inds_i = sampled_pos_inds[mask_i] - idxs_i[0]
              box_regression_pos = box_regression[sampled_pos_inds_i]
              regression_targets_pos = regression_targets[sampled_pos_inds_i + idxs_i[0]]
              anchors_i = anchors.example(bi)
              print(sampled_pos_inds_i)
              anchors_pos_i = anchors_i[sampled_pos_inds_i]
              #anchors_pos_i.show()

              boxes_pred = self.box_coder.decode(box_regression_pos, anchors_pos_i.bbox3d)
              boxes_pred = boxes_pred.cpu().data.numpy()
              boxes_gt = self.box_coder.decode(regression_targets_pos, anchors_pos_i.bbox3d)
              boxes_gt = boxes_gt.cpu().data.numpy()
              boxes_show = np.concatenate([boxes_pred, boxes_gt], 0)
              labels_show = np.array([1]*boxes_pred.shape[0] + [0]*boxes_gt.shape[0])
              from utils3d.bbox3d_ops import Bbox3D
              Bbox3D.draw_bboxes(boxes_show, 'Z', True, labels_show)
              import pdb;
              pdb.set_trace()  # XXX BREAKPOINT
              pass

            #for bi in range(batch_size):
            #    anchors_per_image = [a.example(bi) for a in anchors]
            #    anchors_per_image = cat_boxlist_3d(anchors_per_image)
            #    targets_per_image = targets[bi]

        #if torch.isnan(box_loss) or torch.isinf(box_loss) or torch.isnan(objectness_loss) or torch.isinf(objectness_loss):
        #  pass
        #  import pdb; pdb.set_trace()  # XXX BREAKPOINT
        return objectness_loss, box_loss


def make_rpn_loss_evaluator(cfg, box_coder):
    matcher = Matcher(
        cfg.MODEL.RPN.FG_IOU_THRESHOLD,
        cfg.MODEL.RPN.BG_IOU_THRESHOLD,
        allow_low_quality_matches=True,
    )

    fg_bg_sampler = BalancedPositiveNegativeSampler(
        cfg.MODEL.RPN.BATCH_SIZE_PER_IMAGE, cfg.MODEL.RPN.POSITIVE_FRACTION
    )

    loss_evaluator = RPNLossComputation(matcher, fg_bg_sampler, box_coder)
    return loss_evaluator
