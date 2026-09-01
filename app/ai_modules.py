from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .causal_ai import readiness_note
from .acoustic_ai import snapshot as acoustic_snapshot
from .drift_ai import drift_snapshot, evidently_available
from .config import DATA_DIR
from .capabilities import detect_capabilities
from .optimization import plan_from_health
from .platform import get_state
from .predictive_ai import threshold_forecast, sktime_available
from .process_intelligence import process_snapshot
from .sensor_ai import equipment_health
from .vision.service import load_cameras

# Every module here re-scans/recomputes straight from disk. Data only changes
# on rebuild(), so both entry points below are cached behind the platform
# snapshot id -- otherwise every /intelligence view (and every dashboard card
# that calls module_status) redoes the same statistics from scratch.
_status_cache: dict[str, Any] = {}
_snapshot_cache: dict[str, Any] = {}


def _has(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _current_snapshot_id() -> int | None:
    try:
        return get_state().snapshot_id
    except Exception:
        return None


def module_status() -> dict:
    sid = _current_snapshot_id()
    if sid is not None and _status_cache.get("snapshot_id") == sid:
        return _status_cache["value"]
    health = [x.as_dict() for x in equipment_health(DATA_DIR)]
    caps = detect_capabilities(DATA_DIR)
    value = {
        "capability_registry": caps,
        "vision": {"state": "ready" if caps["signals"]["vision"] else "waiting_data", "cameras": len(load_cameras()), "opencv": _has("cv2"), "onnxruntime": _has("onnxruntime"), "supervision": _has("supervision"), "paddleocr": _has("paddleocr")},
        "sensor_ai": {"state": "ready" if caps["signals"]["equipment_logs"] else "waiting_data", "equipment": len(health), "river": _has("river"), "pyod": _has("pyod")},
        "process": {"state": "ready" if caps["signals"]["process"] else "waiting_data", "pm4py": _has("pm4py"), "note": "built-in variant/bottleneck mining; PM4Py is optional and license-sensitive"},
        "optimization": {"state": "ready" if caps["signals"]["equipment_logs"] else "waiting_data", "ortools": _has("ortools")},
        "causal": readiness_note(),
        "edge": {"onnxruntime": _has("onnxruntime"), "openvino": _has("openvino")},
        "active_learning": {"state": "ready", "label_studio": "external integration supported", "cvat": "external integration supported"},
        "drift": {"state": "ready" if caps["signals"]["equipment_logs"] else "waiting_data", "evidently": evidently_available()},
        "acoustic": {"state": "ready" if caps["signals"]["acoustic"] else "waiting_data", "mode": "local-dsp", "ml_backend": "optional"},
        "data_engine": {"duckdb": _has("duckdb"), "iotdb": "external integration supported"},
        "predictive": {"state": "ready" if caps["signals"]["equipment_logs"] else "waiting_data", "sktime": sktime_available(), "note": "threshold forecast built in; RUL requires labelled failure history"},
    }
    if sid is not None:
        _status_cache["snapshot_id"] = sid
        _status_cache["value"] = value
    return value


def intelligence_snapshot(target_id: str | None = None) -> dict:
    sid = _current_snapshot_id()
    cache_key = (sid, target_id)
    if sid is not None and _snapshot_cache.get("key") == cache_key:
        return _snapshot_cache["value"]
    modules = module_status()
    health = [x.as_dict() for x in equipment_health(DATA_DIR)]
    value = {
        "modules": modules,
        "sensor_health": health,
        "process": process_snapshot(DATA_DIR, target_id),
        "maintenance_plan": plan_from_health(health),
        "drift": drift_snapshot(DATA_DIR),
        "acoustic": acoustic_snapshot(DATA_DIR),
        "predictive": threshold_forecast(DATA_DIR),
    }
    if sid is not None:
        _snapshot_cache["key"] = cache_key
        _snapshot_cache["value"] = value
    return value
