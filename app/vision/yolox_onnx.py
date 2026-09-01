from __future__ import annotations

"""YOLOX ONNX inference adapter using OpenCV DNN.

Portions of preprocessing/postprocessing logic are adapted from YOLOX:
Copyright (c) 2021-2022 Megvii Inc. and affiliates, Apache License 2.0.

The preprocessing/postprocessing/NMS math follows the Apache-2.0 YOLOX
reference implementation from Megvii-BaseDetection/YOLOX. See THIRD_PARTY.md.
This module intentionally does not bundle model weights.
"""

from pathlib import Path

import cv2
import numpy as np

from .models import Detection


def _preproc(img: np.ndarray, input_size: tuple[int, int]) -> tuple[np.ndarray, float]:
    if len(img.shape) == 3:
        padded = np.ones((input_size[0], input_size[1], 3), dtype=np.uint8) * 114
    else:
        padded = np.ones(input_size, dtype=np.uint8) * 114
    ratio = min(input_size[0] / img.shape[0], input_size[1] / img.shape[1])
    resized = cv2.resize(
        img,
        (int(img.shape[1] * ratio), int(img.shape[0] * ratio)),
        interpolation=cv2.INTER_LINEAR,
    ).astype(np.uint8)
    padded[: int(img.shape[0] * ratio), : int(img.shape[1] * ratio)] = resized
    blob = padded.transpose((2, 0, 1))
    return np.ascontiguousarray(blob, dtype=np.float32), ratio


def _demo_postprocess(outputs: np.ndarray, img_size: tuple[int, int], p6: bool = False) -> np.ndarray:
    grids = []
    expanded_strides = []
    strides = [8, 16, 32] if not p6 else [8, 16, 32, 64]
    hsizes = [img_size[0] // stride for stride in strides]
    wsizes = [img_size[1] // stride for stride in strides]
    for hsize, wsize, stride in zip(hsizes, wsizes, strides):
        xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
        grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
        grids.append(grid)
        shape = grid.shape[:2]
        expanded_strides.append(np.full((*shape, 1), stride))
    grids = np.concatenate(grids, 1)
    expanded_strides = np.concatenate(expanded_strides, 1)
    outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
    outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides
    return outputs


def _nms(boxes: np.ndarray, scores: np.ndarray, nms_thr: float) -> list[int]:
    if boxes.size == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / np.maximum(areas[i] + areas[order[1:]] - inter, 1e-9)
        inds = np.where(ovr <= nms_thr)[0]
        order = order[inds + 1]
    return keep


class YoloXOnnxDetector:
    """Inference for a user-supplied YOLOX ONNX model.

    Compatible with standard YOLOX export output shaped [1, N, 5+C].
    Uses OpenCV DNN so the default vision add-on needs no ONNX Runtime install.
    ONNX Runtime/OpenVINO can be swapped in at deployment time.
    """

    name = "yolox-onnx-opencv"

    def __init__(
        self,
        model_path: str | Path,
        class_names: list[str],
        input_size: tuple[int, int] = (640, 640),
        score_threshold: float = 0.3,
        nms_threshold: float = 0.45,
        p6: bool = False,
    ):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLOX ONNX model not found: {self.model_path}")
        self.class_names = class_names
        self.input_size = input_size
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.p6 = p6
        self.net = cv2.dnn.readNetFromONNX(str(self.model_path))

    def detect(self, frame: np.ndarray) -> list[Detection]:
        img, ratio = _preproc(frame, self.input_size)
        self.net.setInput(img[None, :, :, :])
        output = self.net.forward()
        if isinstance(output, (list, tuple)):
            output = output[0]
        pred = _demo_postprocess(np.asarray(output).copy(), self.input_size, self.p6)[0]
        boxes = pred[:, :4]
        scores_all = pred[:, 4:5] * pred[:, 5:]
        cls_inds = scores_all.argmax(1)
        cls_scores = scores_all[np.arange(len(cls_inds)), cls_inds]
        valid = cls_scores >= self.score_threshold
        if not np.any(valid):
            return []
        boxes = boxes[valid]
        cls_inds = cls_inds[valid]
        cls_scores = cls_scores[valid]
        xyxy = np.ones_like(boxes)
        xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2
        xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2
        xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2
        xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2
        xyxy /= max(ratio, 1e-9)
        keep = _nms(xyxy, cls_scores, self.nms_threshold)
        h, w = frame.shape[:2]
        out: list[Detection] = []
        for i in keep:
            cid = int(cls_inds[i])
            name = self.class_names[cid] if 0 <= cid < len(self.class_names) else f"class_{cid}"
            x1, y1, x2, y2 = xyxy[i].tolist()
            out.append(Detection(
                class_id=cid,
                class_name=name,
                score=float(cls_scores[i]),
                x1=float(np.clip(x1, 0, w - 1)),
                y1=float(np.clip(y1, 0, h - 1)),
                x2=float(np.clip(x2, 0, w - 1)),
                y2=float(np.clip(y2, 0, h - 1)),
            ))
        return out
