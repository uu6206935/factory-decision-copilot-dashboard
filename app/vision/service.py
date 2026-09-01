from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from ..config import ROOT, RUNTIME_DIR
from ..database import recent_vision_events, save_review_item, save_vision_event
from .detectors import build_detector
from .models import CameraConfig, VisionResult, VisionRule
from .ocr import read_qr_codes
from .rules import evaluate_rules
from .tracking import TrackerAdapter

VISION_DIR = RUNTIME_DIR / "vision"
SNAPSHOT_DIR = VISION_DIR / "snapshots"
REVIEW_DIR = VISION_DIR / "review"
for p in (VISION_DIR, SNAPSHOT_DIR, REVIEW_DIR):
    p.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = ROOT / "config" / "cameras.json"
_DETECTOR_CACHE: dict[str, tuple[str, Any]] = {}
_TRACKER_CACHE: dict[str, TrackerAdapter] = {}


def _detector_for(cfg: CameraConfig):
    signature = json.dumps(cfg.detector, sort_keys=True, ensure_ascii=False, default=str)
    cached = _DETECTOR_CACHE.get(cfg.id)
    if cached and cached[0] == signature:
        return cached[1]
    detector = build_detector(cfg.detector, ROOT)
    _DETECTOR_CACHE[cfg.id] = (signature, detector)
    return detector


def _tracker_for(cfg: CameraConfig) -> TrackerAdapter:
    tracker = _TRACKER_CACHE.get(cfg.id)
    if tracker is None:
        tracker = TrackerAdapter()
        _TRACKER_CACHE[cfg.id] = tracker
    return tracker


def _rule(obj: dict[str, Any]) -> VisionRule:
    return VisionRule(
        id=str(obj.get("id", "rule")), type=str(obj.get("type", "forbidden_class")),
        class_name=obj.get("class_name"), min_count=obj.get("min_count"), max_count=obj.get("max_count"),
        severity=str(obj.get("severity", "warning")), message=str(obj.get("message", "")),
        confidence=float(obj.get("confidence", 0.25)), polygon=obj.get("polygon"),
    )


def load_cameras() -> list[CameraConfig]:
    if not CONFIG_PATH.exists():
        return []
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    out = []
    for c in raw:
        out.append(CameraConfig(
            id=str(c["id"]), name=str(c.get("name", c["id"])), equipment_id=str(c.get("equipment_id", "")),
            source=str(c.get("source", "")), detector=dict(c.get("detector") or {}),
            rules=[_rule(x) for x in c.get("rules", [])], target_id=c.get("target_id"), enabled=bool(c.get("enabled", True)),
        ))
    return out


def camera_by_id(camera_id: str) -> CameraConfig:
    for c in load_cameras():
        if c.id == camera_id:
            return c
    raise KeyError(f"camera not found: {camera_id}")


def _source_value(source: str):
    if source.startswith("webcam://"):
        return int(source.split("//", 1)[1] or 0)
    p = Path(source)
    if not p.is_absolute():
        p = ROOT / p
    return str(p) if p.exists() else source


def read_frame(source: str) -> np.ndarray:
    src = _source_value(source)
    if isinstance(src, str) and Path(src).exists() and Path(src).suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        frame = cv2.imread(src)
        if frame is None:
            raise RuntimeError(f"cannot read image: {src}")
        return frame
    cap = cv2.VideoCapture(src)
    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"cannot read camera/video source: {source}")
        return frame
    finally:
        cap.release()


def annotate(frame: np.ndarray, detections, rules: list[VisionRule] | None = None) -> np.ndarray:
    img = frame.copy()
    for r in rules or []:
        if r.polygon and len(r.polygon) >= 3:
            pts = np.asarray(r.polygon, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(img, [pts], True, (0, 180, 255), 2, cv2.LINE_AA)
            x, y = map(int, r.polygon[0])
            cv2.putText(img, r.id, (x, max(18, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 2, cv2.LINE_AA)
    for d in detections:
        color = (55, 80, 235) if d.class_name == "defect" else (70, 190, 105)
        cv2.rectangle(img, (int(d.x1), int(d.y1)), (int(d.x2), int(d.y2)), color, 2)
        label = f"{d.class_name} {d.score:.2f}" + (f" #{d.track_id}" if d.track_id is not None else "")
        cv2.putText(img, label, (int(d.x1), max(18, int(d.y1) - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return img


def _save_image(prefix: str, camera_id: str, frame: np.ndarray) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"{stamp}_{camera_id}_{prefix}.jpg"
    path = SNAPSHOT_DIR / filename
    cv2.imwrite(str(path), frame)
    return filename


def analyze_frame(cfg: CameraConfig, frame: np.ndarray, actor: str = "local-demo") -> VisionResult:
    t0 = time.perf_counter()
    detector = _detector_for(cfg)
    detections = detector.detect(frame)
    if bool(cfg.detector.get("tracking", False)):
        detections = _tracker_for(cfg).update(detections)
    qr_codes = read_qr_codes(frame)
    events = evaluate_rules(detections, cfg.rules)
    raw_name = _save_image("raw", cfg.id, frame)
    annotated = annotate(frame, detections, cfg.rules)
    ann_name = _save_image("annotated", cfg.id, annotated)
    latency_ms = (time.perf_counter() - t0) * 1000
    resolved_target_id = cfg.target_id or (qr_codes[0] if qr_codes else None)
    metadata = {"target_id": resolved_target_id, "configured_target_id": cfg.target_id, "qr_codes": qr_codes, "actor": actor, "detector": detector.name}
    for e in events:
        save_vision_event(
            camera_id=cfg.id, equipment_id=cfg.equipment_id, severity=str(e["severity"]), rule_id=str(e["rule_id"]),
            event_type=str(e["type"]), message=str(e["message"]), snapshot_path=ann_name,
            detections=[d.as_dict() for d in detections], metadata=metadata,
        )
    # Active-learning / human-review queue: retain ambiguous detections and every critical incident.
    ambiguous = [d for d in detections if 0.25 <= d.score < 0.65]
    if ambiguous or any(str(e.get("severity")) in {"critical", "high"} for e in events):
        review_file = REVIEW_DIR / raw_name
        cv2.imwrite(str(review_file), frame)
        save_review_item(cfg.id, cfg.equipment_id, raw_name, [d.as_dict() for d in detections], metadata)
    return VisionResult(
        camera_id=cfg.id, equipment_id=cfg.equipment_id, detections=detections, qr_codes=qr_codes, events=events,
        raw_snapshot=raw_name, annotated_snapshot=ann_name, detector=detector.name, latency_ms=latency_ms,
        frame_width=int(frame.shape[1]), frame_height=int(frame.shape[0]),
    )

def capture_once(camera_id: str, actor: str = "local-demo") -> VisionResult:
    cfg = camera_by_id(camera_id)
    if not cfg.enabled:
        raise RuntimeError(f"camera disabled: {camera_id}")
    return analyze_frame(cfg, read_frame(cfg.source), actor)

def analyze_image_bytes(camera_id: str, data: bytes, actor: str = "local-demo") -> VisionResult:
    cfg = camera_by_id(camera_id)
    arr = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("uploaded file is not a decodable image")
    return analyze_frame(cfg, frame, actor)


def vision_dashboard() -> dict[str, Any]:
    cams = load_cameras()
    return {
        "cameras": cams,
        "events": recent_vision_events(30),
        "snapshot_base": "/runtime-assets/snapshots/",
        "review_base": "/runtime-assets/review/",
    }


def evidence_for(vehicle_id: str | None, equipment_ids: list[str] | None = None, limit: int = 20) -> list[dict[str, Any]]:
    ids = {str(x) for x in (equipment_ids or []) if x}
    out = []
    for e in recent_vision_events(limit):
        md = e.get("metadata") or {}
        if vehicle_id and str(md.get("target_id") or "").upper() == str(vehicle_id).upper():
            out.append(e); continue
        if vehicle_id and any(str(q).upper() == str(vehicle_id).upper() for q in (md.get("qr_codes") or [])):
            out.append(e); continue
        if ids and str(e.get("equipment_id")) in ids:
            out.append(e)
    return out
