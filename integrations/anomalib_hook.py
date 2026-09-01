"""Optional visual anomaly hook.

Install separately when image inspection is needed:
    pip install anomalib

Anomalib is Apache-2.0 licensed. This file does not vendor anomalib source; it
provides a stable place to connect PatchCore/EfficientAD inference output to the
Factory Decision Copilot evidence model.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VisionAnomaly:
    image_id: str
    anomaly_score: float
    label: str
    heatmap_path: str | None = None


def normalize_anomalib_prediction(image_id: str, pred_score: float, pred_label: int, heatmap_path: str | None = None) -> VisionAnomaly:
    return VisionAnomaly(
        image_id=image_id,
        anomaly_score=float(pred_score),
        label="NG" if int(pred_label) else "OK",
        heatmap_path=heatmap_path,
    )
