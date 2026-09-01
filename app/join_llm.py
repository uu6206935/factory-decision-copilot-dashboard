from __future__ import annotations

"""DeepSeek Flash semantic validation for cross-file JOIN candidates."""

import hashlib
import json
from typing import Any

from .config import DEEPSEEK_JOIN_REASONING, DEEPSEEK_SEND_SAMPLE_VALUES, RUNTIME_DIR
from .deepseek import available as deepseek_available, json_chat

# Same rationale as schema_llm's cache: rebuild() re-runs on every startup and
# every approval/upload/reload action, so without caching this call re-hits the
# network every single time even when no table changed.
_CACHE_PATH = RUNTIME_DIR / "llm_join_cache.json"


def available() -> bool:
    return bool(DEEPSEEK_JOIN_REASONING and deepseek_available())


def _load_cache() -> dict[str, Any]:
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict[str, Any]) -> None:
    try:
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = _CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_CACHE_PATH)
    except Exception:
        pass


def enhance(profiles: list[Any], local_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not available() or len(profiles) < 2:
        return local_candidates

    tables = []
    for p in profiles[:24]:
        columns = []
        for c in p.column_profiles[:50]:
            item = {
                "raw": c.get("raw"),
                "canonical": c.get("canonical"),
                "confidence": c.get("confidence"),
                "dtype": c.get("dtype"),
                "unique_ratio": c.get("unique_ratio"),
            }
            if DEEPSEEK_SEND_SAMPLE_VALUES:
                item["examples"] = c.get("examples", [])[:8]
            columns.append(item)
        tables.append({
            "table_key": p.table_key,
            "role": p.inferred_role,
            "compatible_roles": p.compatible_roles,
            "rows": p.rows,
            "columns": columns,
        })

    compact_local = [{k: x.get(k) for k in ["id", "left", "right", "key", "mode", "confidence", "reason"]} for x in local_candidates[:50]]

    fingerprint = hashlib.sha256(
        json.dumps({"tables": tables, "local": compact_local}, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()
    cache = _load_cache()
    if cache.get("fingerprint") == fingerprint:
        return cache.get("result", local_candidates)

    try:
        obj = json_chat(
            system=(
                "You are a conservative manufacturing data integration architect. "
                "Validate or propose JOIN relationships using only supplied schemas. Output JSON only. "
                "Do not propose unsafe exact timestamp equality; use time_window/asof when time alignment is needed."
            ),
            user=(
                f"Tables: {tables}\n\nLocal deterministic JOIN candidates: {compact_local}\n\n"
                "Return JSON: "
                '{"joins":[{"left":"table_key","right":"table_key","key":"vehicle_id|equipment_id|part_lot|part_no|process|timestamp|equipment_id + timestamp","mode":"equi_join|time_window|asof_join","confidence":0.0,"reason":"日本語の短い理由"}]}. '
                "Only propose joins that are semantically useful and defensible. Keep at most 30. Write every reason in Japanese."
            ),
            thinking=False,
            reasoning_effort="low",
            max_tokens=3000,
        )
    except Exception:
        return local_candidates

    by_id = {str(x.get("id")): dict(x) for x in local_candidates}
    profile_keys = {p.table_key for p in profiles}
    for row in obj.get("joins", []):
        if not isinstance(row, dict):
            continue
        left, right = str(row.get("left") or ""), str(row.get("right") or "")
        key, mode = str(row.get("key") or ""), str(row.get("mode") or "")
        if left not in profile_keys or right not in profile_keys or left == right:
            continue
        if mode not in {"equi_join", "time_window", "asof_join"}:
            continue
        if key not in {"vehicle_id", "equipment_id", "part_lot", "part_no", "process", "timestamp", "equipment_id + timestamp"}:
            continue
        try:
            conf = max(0.0, min(0.99, float(row.get("confidence") or 0)))
        except Exception:
            continue
        join_id = f"{left}|{right}|{key}|{mode}"
        reverse_id = f"{right}|{left}|{key}|{mode}"
        target_id = join_id if join_id in by_id else reverse_id if reverse_id in by_id else join_id
        if target_id in by_id:
            existing = by_id[target_id]
            # DeepSeek can add semantic support, but cannot override strong local evidence downward.
            existing["confidence"] = round(max(float(existing.get("confidence", 0)), conf), 3)
            existing["reason"] = str(existing.get("reason", "")) + "; DeepSeek Flash: " + str(row.get("reason") or "semantic validation")
            if existing["confidence"] >= 0.95 and existing.get("status") != "accepted":
                existing["status"] = "auto"
        elif conf >= 0.78:
            by_id[target_id] = {
                "id": target_id,
                "left": left,
                "right": right,
                "left_role": next((p.inferred_role for p in profiles if p.table_key == left), None),
                "right_role": next((p.inferred_role for p in profiles if p.table_key == right), None),
                "key": key,
                "label": key,
                "mode": mode,
                "confidence": round(conf, 3),
                "reason": "DeepSeek Flash semantic proposal: " + str(row.get("reason") or ""),
                "status": "review",
            }
    result = sorted(by_id.values(), key=lambda x: float(x.get("confidence", 0)), reverse=True)[:100]
    _save_cache({"fingerprint": fingerprint, "result": result})
    return result
