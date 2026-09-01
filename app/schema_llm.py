from __future__ import annotations

"""DeepSeek V4 Flash enhancement for low-confidence schema inference."""

import hashlib
import json
import threading
from typing import Any

from .config import DEEPSEEK_SCHEMA_REASONING, DEEPSEEK_SEND_SAMPLE_VALUES, RUNTIME_DIR
from .deepseek import available as deepseek_available, json_chat

# Rebuild runs on every startup and every approval/upload/reload action, but a
# table's ambiguous columns only change when its data changes. Caching each
# table's enhancement result behind a fingerprint of its own input turns every
# rebuild after the first (with the same data) into a zero-network-call rebuild,
# which is most of what makes startup/screen actions feel slow.
_CACHE_PATH = RUNTIME_DIR / "llm_schema_cache.json"
_CACHE_LOCK = threading.Lock()


def available() -> bool:
    return bool(DEEPSEEK_SCHEMA_REASONING and deepseek_available())


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


def enhance(table_name: str, columns: list[dict[str, Any]], canonical_fields: dict[str, str]) -> dict[str, dict[str, Any]]:
    if not available():
        return {}
    compact = []
    for c in columns:
        if float(c.get("confidence", 0)) >= 0.95:
            continue
        item = {
            "raw": c.get("raw"),
            "dtype": c.get("dtype"),
            "semantic_type": c.get("semantic_type"),
            "null_rate": c.get("null_rate"),
            "unique_ratio": c.get("unique_ratio"),
            "numeric_ratio": c.get("numeric_ratio"),
            "datetime_ratio": c.get("datetime_ratio"),
            "local_guess": c.get("canonical"),
            "local_confidence": c.get("confidence"),
            "local_reasons": c.get("reasons", [])[:5],
        }
        if DEEPSEEK_SEND_SAMPLE_VALUES:
            item["examples"] = c.get("examples", [])[:20]
        compact.append(item)
    if not compact:
        return {}

    fingerprint = hashlib.sha256(
        json.dumps({"table": table_name, "compact": compact, "fields": sorted(canonical_fields)}, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()
    cache = _load_cache()
    cached_entry = cache.get(table_name)
    if isinstance(cached_entry, dict) and cached_entry.get("fingerprint") == fingerprint:
        return cached_entry.get("result", {})

    obj = json_chat(
        system=(
            "You are a conservative manufacturing data schema classifier. "
            "Output valid JSON only. Never invent fields outside the supplied canonical schema."
        ),
        user=(
            f"Classify ambiguous columns in this manufacturing table.\n"
            f"Table: {table_name}\n"
            f"Allowed canonical fields: {canonical_fields}\n"
            f"Columns: {compact}\n\n"
            "Return JSON exactly like: "
            '{"columns":[{"raw":"original","canonical":"allowed_key_or_null","confidence":0.0,"reason":"短い日本語の判断理由"}]}. '
            "Use >=0.95 only for very clear semantics. If ambiguous, use null or confidence below 0.8. Write reason in Japanese."
        ),
        thinking=False,
        reasoning_effort="low",
        max_tokens=2200,
    )
    out: dict[str, dict[str, Any]] = {}
    for row in obj.get("columns", []):
        if not isinstance(row, dict):
            continue
        raw = str(row.get("raw") or "")
        canonical = row.get("canonical")
        try:
            conf = float(row.get("confidence") or 0)
        except Exception:
            conf = 0.0
        if canonical is not None and canonical not in canonical_fields:
            continue
        out[raw] = {
            "canonical": canonical,
            "confidence": max(0.0, min(1.0, conf)),
            "reason": str(row.get("reason") or "DeepSeek Flash semantic inference"),
        }
    with _CACHE_LOCK:
        # Re-read right before writing: tables are scanned concurrently, so a stale
        # `cache` snapshot from before this network call would otherwise clobber
        # another table's entry saved in the meantime.
        fresh_cache = _load_cache()
        fresh_cache[table_name] = {"fingerprint": fingerprint, "result": out}
        _save_cache(fresh_cache)
    return out
