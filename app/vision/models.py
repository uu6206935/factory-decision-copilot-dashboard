from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Detection:
    class_id: int
    class_name: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float
    track_id: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisionRule:
    id: str
    type: str
    class_name: str | None = None
    min_count: int | None = None
    max_count: int | None = None
    severity: str = "warning"
    message: str = ""
    confidence: float = 0.25
    polygon: list[list[float]] | None = None


@dataclass
class CameraConfig:
    id: str
    name: str
    equipment_id: str
    source: str
    detector: dict[str, Any] = field(default_factory=dict)
    rules: list[VisionRule] = field(default_factory=list)
    target_id: str | None = None
    enabled: bool = True


@dataclass
class VisionResult:
    camera_id: str
    equipment_id: str
    detections: list[Detection]
    qr_codes: list[str]
    events: list[dict[str, Any]]
    raw_snapshot: str | None
    annotated_snapshot: str | None
    detector: str
    latency_ms: float
    frame_width: int
    frame_height: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "equipment_id": self.equipment_id,
            "detections": [d.as_dict() for d in self.detections],
            "qr_codes": self.qr_codes,
            "events": self.events,
            "raw_snapshot": self.raw_snapshot,
            "annotated_snapshot": self.annotated_snapshot,
            "detector": self.detector,
            "latency_ms": self.latency_ms,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
        }
