from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from .models import Detection
from .yolox_onnx import YoloXOnnxDetector


class Detector(Protocol):
    name: str
    def detect(self, frame: np.ndarray) -> list[Detection]: ...


class DemoDefectDetector:
    """A deterministic local demo detector.

    Detects red regions as `defect` and the large blue/gray part region as
    `part`. It exists so the product demo works with no model downloads.
    Replace with YOLOX/Anomalib for production.
    """

    name = "demo-color-defect"

    def detect(self, frame: np.ndarray) -> list[Detection]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        red1 = cv2.inRange(hsv, np.array([0, 80, 80]), np.array([12, 255, 255]))
        red2 = cv2.inRange(hsv, np.array([168, 80, 80]), np.array([179, 255, 255]))
        mask = cv2.bitwise_or(red1, red2)
        detections: list[Detection] = []
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 80:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            score = min(0.99, 0.65 + area / max(frame.shape[0] * frame.shape[1], 1) * 8)
            detections.append(Detection(1, "defect", float(score), x, y, x + w, y + h))
        # Blue-ish part region for the sample image.
        blue = cv2.inRange(hsv, np.array([85, 25, 35]), np.array([135, 255, 255]))
        contours, _ = cv2.findContours(blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            cnt = max(contours, key=cv2.contourArea)
            if cv2.contourArea(cnt) > 1000:
                x, y, w, h = cv2.boundingRect(cnt)
                detections.append(Detection(0, "part", 0.96, x, y, x + w, y + h))
        return detections


class UltralyticsOptionalDetector:
    """Optional adapter only.

    The upstream open-source Ultralytics package is AGPL-3.0. It is NOT a
    default dependency of this proprietary product. Use only when the
    deployment has an appropriate Ultralytics license / legal approval.
    """

    name = "ultralytics-optional"

    def __init__(self, model_path: str, score_threshold: float = 0.25):
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover - optional
            raise RuntimeError("ultralytics is not installed; see license notes before enabling") from exc
        self.model = YOLO(model_path)
        self.score_threshold = score_threshold

    def detect(self, frame: np.ndarray) -> list[Detection]:  # pragma: no cover - optional
        result = self.model.predict(frame, verbose=False, conf=self.score_threshold)[0]
        names = result.names
        out: list[Detection] = []
        if result.boxes is None:
            return out
        for box in result.boxes:
            xyxy = box.xyxy[0].detach().cpu().numpy().tolist()
            cid = int(box.cls[0].item())
            score = float(box.conf[0].item())
            out.append(Detection(cid, str(names.get(cid, cid)), score, *map(float, xyxy)))
        return out


class AnomalibHttpDetector:
    """Adapter for an external Anomalib inference sidecar.

    Expected JSON response: {"anomaly_score": 0.83, "pred_label": 1,
    "bbox": [x1,y1,x2,y2] (optional)}.  A full-frame box is used when the
    sidecar only returns image-level anomaly classification.
    """

    name = "anomalib-http"

    def __init__(self, endpoint: str, score_threshold: float = 0.5, timeout_sec: float = 3.0):
        self.endpoint = endpoint
        self.score_threshold = score_threshold
        self.timeout_sec = timeout_sec

    def detect(self, frame: np.ndarray) -> list[Detection]:
        import requests
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            raise RuntimeError("failed to encode frame")
        r = requests.post(
            self.endpoint,
            files={"image": ("frame.jpg", encoded.tobytes(), "image/jpeg")},
            timeout=self.timeout_sec,
        )
        r.raise_for_status()
        data = r.json()
        score = float(data.get("anomaly_score", data.get("score", 0.0)))
        label = int(data.get("pred_label", 1 if score >= self.score_threshold else 0))
        if not label or score < self.score_threshold:
            return []
        h, w = frame.shape[:2]
        bbox = data.get("bbox") or [0, 0, w - 1, h - 1]
        return [Detection(0, "visual_anomaly", score, *map(float, bbox), metadata={"sidecar": self.endpoint})]


def _load_classes(cfg: dict[str, Any]) -> list[str]:
    classes = cfg.get("class_names")
    if isinstance(classes, list) and classes:
        return [str(x) for x in classes]
    classes_file = cfg.get("classes_file")
    if classes_file and Path(classes_file).exists():
        return [x.strip() for x in Path(classes_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    # COCO names are intentionally not embedded; production factories should use their own classes.
    return ["part", "defect"]


def build_detector(cfg: dict[str, Any], root: Path) -> Detector:
    kind = str(cfg.get("type", "demo")).lower()
    if kind == "demo":
        return DemoDefectDetector()
    if kind in {"yolox", "yolox_onnx", "yolox-onnx"}:
        model = Path(str(cfg.get("model", "models/yolox.onnx")))
        if not model.is_absolute():
            model = root / model
        size = cfg.get("input_size", [640, 640])
        return YoloXOnnxDetector(
            model_path=model,
            class_names=_load_classes(cfg),
            input_size=(int(size[0]), int(size[1])),
            score_threshold=float(cfg.get("score_threshold", 0.3)),
            nms_threshold=float(cfg.get("nms_threshold", 0.45)),
            p6=bool(cfg.get("p6", False)),
        )
    if kind in {"anomalib_http", "anomalib-sidecar"}:
        return AnomalibHttpDetector(str(cfg.get("endpoint", "http://127.0.0.1:8010/infer")), float(cfg.get("score_threshold", 0.5)), float(cfg.get("timeout_sec", 3.0)))
    if kind in {"ultralytics", "ultralytics_yolo"}:
        model = Path(str(cfg.get("model", "models/model.pt")))
        if not model.is_absolute():
            model = root / model
        return UltralyticsOptionalDetector(str(model), float(cfg.get("score_threshold", 0.25)))
    raise ValueError(f"unsupported detector type: {kind}")
