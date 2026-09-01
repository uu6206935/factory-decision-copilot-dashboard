from __future__ import annotations

from collections import Counter

from .models import Detection, VisionRule


def _point_in_polygon(x: float, y: float, polygon: list[list[float]] | None) -> bool:
    if not polygon or len(polygon) < 3:
        return False
    # Ray casting: dependency-free and deterministic.
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = float(polygon[i][0]), float(polygon[i][1])
        xj, yj = float(polygon[j][0]), float(polygon[j][1])
        cross = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi)
        if cross:
            inside = not inside
        j = i
    return inside


def _in_zone(d: Detection, polygon: list[list[float]] | None) -> bool:
    return _point_in_polygon((d.x1 + d.x2) / 2.0, (d.y1 + d.y2) / 2.0, polygon)


def evaluate_rules(detections: list[Detection], rules: list[VisionRule]) -> list[dict]:
    counts = Counter(d.class_name for d in detections if d.score >= 0)
    events: list[dict] = []
    for r in rules:
        eligible = [d for d in detections if d.class_name == r.class_name and d.score >= r.confidence]
        count = counts.get(r.class_name or "", 0)
        zone_eligible = [d for d in eligible if _in_zone(d, r.polygon)] if r.polygon else eligible
        triggered = False
        detail_count = count
        if r.type in {"forbidden_class", "class_forbidden"}:
            triggered = bool(eligible)
        elif r.type in {"required_class", "class_required"}:
            triggered = not bool(eligible)
        elif r.type == "min_count":
            triggered = count < int(r.min_count or 0)
        elif r.type == "max_count":
            triggered = count > int(r.max_count or 0)
        elif r.type in {"zone_forbidden_class", "forbidden_in_zone"}:
            triggered = bool(zone_eligible)
            detail_count = len(zone_eligible)
        elif r.type in {"zone_required_class", "required_in_zone"}:
            triggered = not bool(zone_eligible)
            detail_count = len(zone_eligible)
        if triggered:
            msg = r.message or f"Vision rule {r.id} triggered ({r.type}: {r.class_name}, count={detail_count})"
            events.append({
                "rule_id": r.id, "type": r.type, "class_name": r.class_name, "count": detail_count,
                "severity": r.severity, "message": msg, "polygon": r.polygon,
            })
    return events
