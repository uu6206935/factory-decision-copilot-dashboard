from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RUNTIME_DIR
from .platform import get_state
from .schema import DISPLAY_LABELS

APPROVAL_STORE = RUNTIME_DIR / "approval_center.json"
VALID_STATUSES = {"pending", "approved", "held", "rejected"}

# summary() feeds the small approval-count badge that every single page
# renders through main.py's ctx(), but it was doing a full deepcopy of the
# catalog plus a full approval-item build just to reduce it to three numbers.
# Every approval-store write is immediately followed by a rebuild() call
# (see main.py:_apply_approval_decision), so the platform snapshot id is a
# safe invalidation signal here too.
_summary_cache: dict[str, Any] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty() -> dict[str, Any]:
    return {"version": 1, "items": {}, "history": []}


def load_store() -> dict[str, Any]:
    if not APPROVAL_STORE.exists():
        return _empty()
    try:
        obj = json.loads(APPROVAL_STORE.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return _empty()
        obj.setdefault("version", 1)
        obj.setdefault("items", {})
        obj.setdefault("history", [])
        return obj
    except Exception:
        return _empty()


def _save_store(obj: dict[str, Any]) -> None:
    APPROVAL_STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = APPROVAL_STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(APPROVAL_STORE)


def make_schema_id(table_key: str, raw: str) -> str:
    return f"schema::{table_key}::{raw}"


def make_role_id(table_key: str) -> str:
    return f"role::{table_key}"


def make_join_id(join_id: str) -> str:
    return f"join::{join_id}"


def parse_item_id(item_id: str) -> tuple[str, str, str | None]:
    if item_id.startswith("schema::"):
        body = item_id[len("schema::"):]
        table_key, sep, raw = body.rpartition("::")
        return "schema", table_key, raw if sep else None
    if item_id.startswith("role::"):
        return "role", item_id[len("role::"):], None
    if item_id.startswith("join::"):
        return "join", item_id[len("join::"):], None
    return "unknown", item_id, None


def record_decision(
    item_id: str,
    status: str,
    actor: str,
    *,
    details: dict[str, Any] | None = None,
    note: str = "",
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"unsupported approval status: {status}")
    store = load_store()
    before = deepcopy(store["items"].get(item_id, {}))
    ts = _now()
    after = {
        **before,
        "status": status,
        "actor": actor,
        "updated_at": ts,
        "note": note or "",
    }
    if details:
        after.update(details)
    store["items"][item_id] = after
    store["history"].append({
        "id": len(store["history"]) + 1,
        "timestamp": ts,
        "actor": actor,
        "item_id": item_id,
        "item_type": parse_item_id(item_id)[0],
        "from_status": before.get("status", "pending"),
        "to_status": status,
        "note": note or "",
        "before": before,
        "after": after,
    })
    # Bound local history so a long-running pilot does not grow the JSON forever.
    if len(store["history"]) > 10000:
        store["history"] = store["history"][-10000:]
    _save_store(store)
    return after


def recent_history(limit: int = 100) -> list[dict[str, Any]]:
    rows = load_store().get("history", [])
    return list(reversed(rows[-max(1, min(limit, 1000)):]))


def _persisted(item_id: str) -> dict[str, Any]:
    return load_store().get("items", {}).get(item_id, {})


def decorate_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    """Attach governance status/actor/time to schema rows, roles and joins."""
    out = deepcopy(catalog)
    store = load_store().get("items", {})
    for table in out.get("tables", []):
        role_id = make_role_id(table.get("table_key", ""))
        role_state = store.get(role_id, {})
        table["approval"] = {
            "item_id": role_id,
            "status": role_state.get("status", "pending"),
            "actor": role_state.get("actor", ""),
            "updated_at": role_state.get("updated_at", ""),
        }
        for col in table.get("column_profiles", []):
            item_id = make_schema_id(table.get("table_key", ""), str(col.get("raw", "")))
            state = store.get(item_id, {})
            # Existing user-approved schema memory remains governed as approved even
            # when it predates the Approval Center history file.
            default_status = "approved" if col.get("status") == "approved" else "pending"
            col["approval"] = {
                "item_id": item_id,
                "status": state.get("status", default_status),
                "actor": state.get("actor", "legacy" if default_status == "approved" else ""),
                "updated_at": state.get("updated_at", ""),
                "note": state.get("note", ""),
            }
    for join in out.get("joins", []):
        item_id = make_join_id(str(join.get("id", "")))
        state = store.get(item_id, {})
        default_status = "approved" if join.get("status") == "accepted" else "pending"
        governed = state.get("status", default_status)
        join["approval"] = {
            "item_id": item_id,
            "status": governed,
            "actor": state.get("actor", "legacy" if default_status == "approved" else ""),
            "updated_at": state.get("updated_at", ""),
            "note": state.get("note", ""),
        }
        # Expose governance status to UI without changing the deterministic JOIN engine.
        join["governance_status"] = governed
    return out


def build_center(catalog: dict[str, Any], history_limit: int = 100) -> dict[str, Any]:
    catalog = decorate_catalog(catalog)
    items: list[dict[str, Any]] = []
    for table in catalog.get("tables", []):
        table_key = table.get("table_key", "")
        role_approval = table.get("approval", {})
        items.append({
            "id": role_approval.get("item_id") or make_role_id(table_key),
            "type": "role",
            "type_label": "データ種別",
            "title": f"{table.get('source')}{' / ' + table.get('sheet') if table.get('sheet') else ''}",
            "subtitle": "この表のデータ種別",
            "source": table.get("source", ""),
            "sheet": table.get("sheet", ""),
            "table_key": table_key,
            "suggested": table.get("role") or "未確定",
            "suggested_value": table.get("role") or "",
            "confidence": float(table.get("role_score") or 0),
            "status": role_approval.get("status", "pending"),
            "actor": role_approval.get("actor", ""),
            "updated_at": role_approval.get("updated_at", ""),
            "note": role_approval.get("note", ""),
            "reasons": [f"compatible: {', '.join(table.get('compatible_roles', [])) or 'none'}"],
            "samples": [],
            "can_approve": bool(table.get("role")),
        })
        for col in table.get("column_profiles", []):
            approval = col.get("approval", {})
            canonical = col.get("canonical") or ""
            items.append({
                "id": approval.get("item_id") or make_schema_id(table_key, str(col.get("raw", ""))),
                "type": "schema",
                "type_label": "列意味",
                "title": str(col.get("raw", "")),
                "subtitle": f"{table.get('source')}{' / ' + table.get('sheet') if table.get('sheet') else ''}",
                "source": table.get("source", ""),
                "sheet": table.get("sheet", ""),
                "table_key": table_key,
                "raw": str(col.get("raw", "")),
                "suggested": DISPLAY_LABELS.get(canonical, canonical) if canonical else "未解釈",
                "suggested_value": canonical,
                "confidence": float(col.get("confidence") or 0),
                "status": approval.get("status", "pending"),
                "actor": approval.get("actor", ""),
                "updated_at": approval.get("updated_at", ""),
                "note": approval.get("note", ""),
                "reasons": list(col.get("reasons", [])),
                "samples": list(col.get("examples", []))[:5],
                "alternatives": list(col.get("alternatives", [])),
                "can_approve": bool(canonical),
            })
    for join in catalog.get("joins", []):
        approval = join.get("approval", {})
        items.append({
            "id": approval.get("item_id") or make_join_id(str(join.get("id", ""))),
            "type": "join",
            "type_label": "結合",
            "title": str(join.get("label") or join.get("key") or "結合"),
            "subtitle": f"{join.get('left')} ↔ {join.get('right')}",
            "left": join.get("left"),
            "right": join.get("right"),
            "join_id": join.get("id"),
            "suggested": str(join.get("label") or join.get("key") or ""),
            "suggested_value": str(join.get("id") or ""),
            "confidence": float(join.get("confidence") or 0),
            "status": approval.get("status", "pending"),
            "actor": approval.get("actor", ""),
            "updated_at": approval.get("updated_at", ""),
            "note": approval.get("note", ""),
            "reasons": [str(join.get("reason") or "")],
            "samples": [],
            "can_approve": True,
            "mode": join.get("mode", ""),
        })

    # Pending first, then held, approved, rejected. Within state, higher confidence first.
    order = {"pending": 0, "held": 1, "approved": 2, "rejected": 3}
    items.sort(key=lambda x: (order.get(x.get("status"), 9), -float(x.get("confidence") or 0), x.get("type", ""), x.get("title", "")))
    counts = {s: sum(1 for i in items if i.get("status") == s) for s in VALID_STATUSES}
    type_counts = {t: sum(1 for i in items if i.get("type") == t and i.get("status") == "pending") for t in ["schema", "role", "join"]}
    return {
        "items": items,
        "counts": counts,
        "pending_by_type": type_counts,
        "total": len(items),
        "history": recent_history(history_limit),
    }


def summary(catalog: dict[str, Any]) -> dict[str, Any]:
    try:
        sid = get_state().snapshot_id
    except Exception:
        sid = None
    if sid is not None and _summary_cache.get("snapshot_id") == sid:
        return _summary_cache["value"]
    center = build_center(catalog, history_limit=1)
    value = {"counts": center["counts"], "pending_by_type": center["pending_by_type"], "total": center["total"]}
    if sid is not None:
        _summary_cache["snapshot_id"] = sid
        _summary_cache["value"] = value
    return value
