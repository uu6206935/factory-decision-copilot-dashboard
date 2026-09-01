"""Export the visual human-review queue to Label Studio task JSON.

Label Studio itself is an optional external service.  This exporter is useful
for an air-gapped deployment: export tasks, annotate in Label Studio, then use
its COCO/YOLO export for detector retraining.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.database import recent_review_items


def export_tasks(output: Path, public_asset_prefix: str = "/runtime-assets/review/") -> int:
    tasks = []
    for item in recent_review_items(10000):
        tasks.append({
            "data": {
                "image": public_asset_prefix + str(item.get("image_path", "")),
                "camera_id": item.get("camera_id"),
                "equipment_id": item.get("equipment_id"),
            },
            "meta": {
                "predictions": item.get("detections") or [],
                "source": "factory-decision-copilot",
            },
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(tasks)
