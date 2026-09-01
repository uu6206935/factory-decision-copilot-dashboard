from __future__ import annotations

"""Optional ByteTrack integration through the MIT-licensed supervision toolkit."""

from typing import Any

from .models import Detection


class TrackerAdapter:
    def __init__(self):
        self.available = False
        self._tracker: Any = None
        try:
            import supervision as sv  # type: ignore
            self._sv = sv
            self._tracker = sv.ByteTrack()
            self.available = True
        except Exception:
            self._sv = None

    def update(self, detections: list[Detection]) -> list[Detection]:
        if not self.available or not detections:
            return detections
        import numpy as np
        sv = self._sv
        boxes = np.asarray([[d.x1, d.y1, d.x2, d.y2] for d in detections], dtype=float)
        conf = np.asarray([d.score for d in detections], dtype=float)
        cls = np.asarray([d.class_id for d in detections], dtype=int)
        sd = sv.Detections(xyxy=boxes, confidence=conf, class_id=cls)
        tracked = self._tracker.update_with_detections(sd)
        if len(tracked) == 0:
            return []
        class_names = {d.class_id: d.class_name for d in detections}
        out: list[Detection] = []
        for i, box in enumerate(tracked.xyxy):
            cid = int(tracked.class_id[i]) if tracked.class_id is not None else -1
            score = float(tracked.confidence[i]) if tracked.confidence is not None else 1.0
            tid = int(tracked.tracker_id[i]) if tracked.tracker_id is not None else None
            out.append(Detection(
                class_id=cid,
                class_name=class_names.get(cid, f"class_{cid}"),
                score=score,
                x1=float(box[0]), y1=float(box[1]), x2=float(box[2]), y2=float(box[3]),
                track_id=tid,
            ))
        return out
