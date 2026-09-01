"""Generate a minimal CVAT image manifest from the vision review queue.

The actual CVAT server is intentionally not bundled.  CVAT can be deployed as
an independent annotation service, keeping labeling infrastructure separated
from the production decision-support service.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.database import recent_review_items


def export_manifest(output: Path) -> int:
    rows = []
    for x in recent_review_items(10000):
        rows.append({
            "name": str(x.get("image_path", "")),
            "camera_id": x.get("camera_id"),
            "equipment_id": x.get("equipment_id"),
            "predictions": x.get("detections") or [],
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(rows)
