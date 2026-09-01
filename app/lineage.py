from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .approval_center import decorate_catalog, recent_history
from .schema import DISPLAY_LABELS
from .i18n import ja_role, ja_signal, ja_join_mode, ja_reason

ROLE_TO_SIGNAL = {
    "quality": "quality",
    "process": "process",
    "equipment_logs": "equipment_logs",
    "maintenance": "maintenance",
    "parts": "parts",
}


def _nid(prefix: str, value: str) -> str:
    return f"{prefix}:{value}"


def _basename(path: str) -> str:
    return Path(path).name or path


def build_lineage(catalog: dict[str, Any], capabilities: dict[str, Any]) -> dict[str, Any]:
    """Build file → table → semantic column → JOIN → analysis lineage graph."""
    catalog = decorate_catalog(catalog)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()

    def add_node(node: dict[str, Any]) -> None:
        if node["id"] in seen_nodes:
            return
        seen_nodes.add(node["id"])
        nodes.append(node)

    def add_edge(source: str, target: str, *, kind: str, label: str = "", status: str = "", details: dict[str, Any] | None = None) -> None:
        eid = f"{source}->{target}:{kind}:{label}"
        if eid in seen_edges:
            return
        seen_edges.add(eid)
        edges.append({"id": eid, "source": source, "target": target, "kind": kind, "label": label, "status": status, "details": details or {}})

    histories = recent_history(1000)
    history_by_source: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    history_by_table: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for h in histories:
        after = h.get("after") or {}
        source = str(after.get("source") or "")
        table_key = str(after.get("table_key") or "")
        if source:
            history_by_source[source].append(h)
        if table_key:
            history_by_table[table_key].append(h)

    # Files first. Use the full catalog so PDFs/images/audio also appear even without tables.
    for f in catalog.get("files", []):
        path = str(f.get("relative_path") or "")
        fid = _nid("file", path)
        add_node({
            "id": fid, "layer": 0, "kind": "file", "label": _basename(path), "sub": path,
            "status": "active", "details": {**f, "approval_history": history_by_source.get(_basename(path), [])[:20]},
        })

    table_by_key: dict[str, dict[str, Any]] = {}
    columns_by_table_canonical: dict[tuple[str, str], str] = {}
    role_tables: defaultdict[str, list[str]] = defaultdict(list)

    for t in catalog.get("tables", []):
        table_key = str(t.get("table_key") or "")
        table_by_key[table_key] = t
        tid = _nid("table", table_key)
        role = str(t.get("role") or "unknown")
        role_tables[role].append(tid)
        approval = t.get("approval", {})
        add_node({
            "id": tid, "layer": 1, "kind": "table",
            "label": str(t.get("sheet") or _basename(str(t.get("source") or table_key))),
            "sub": f"{t.get('source')} · {ja_role(role)}",
            "status": approval.get("status", "pending"),
            "details": {
                "table_key": table_key, "source": t.get("source"), "sheet": t.get("sheet"), "rows": t.get("rows"),
                "role": role, "role_score": t.get("role_score"), "approval": approval, "approval_history": history_by_table.get(table_key, [])[:20],
            },
        })
        # Link the source file to the table. Uploaded files may live below uploads/ while source only stores basename.
        source = str(t.get("source") or "")
        matching = [n for n in nodes if n.get("kind") == "file" and (_basename(n.get("sub", "")) == source or n.get("sub") == source)]
        if matching:
            add_edge(matching[0]["id"], tid, kind="contains", label="テーブル")

        for c in t.get("column_profiles", []):
            canonical = str(c.get("canonical") or "")
            # Show all proposed/approved semantic columns; unresolved raw columns are still visible as raw nodes.
            raw = str(c.get("raw") or "")
            cid = _nid("column", f"{table_key}::{raw}")
            approval_c = c.get("approval", {})
            label = DISPLAY_LABELS.get(canonical, canonical) if canonical else raw
            sub = f"{raw} → {DISPLAY_LABELS.get(canonical, canonical)}" if canonical else f"{raw} → 未解釈"
            add_node({
                "id": cid, "layer": 2, "kind": "column", "label": label, "sub": sub,
                "status": approval_c.get("status", "pending"),
                "details": {
                    "table_key": table_key, "raw": raw, "canonical": canonical, "confidence": c.get("confidence"),
                    "examples": c.get("examples", [])[:5], "reasons": c.get("reasons", []), "approval": approval_c,
                },
            })
            add_edge(tid, cid, kind="maps", label=raw, status=approval_c.get("status", "pending"))
            if canonical:
                columns_by_table_canonical[(table_key, canonical)] = cid

    # JOIN nodes connect the participating semantic columns (fall back to tables when a composite key is used).
    for j in catalog.get("joins", []):
        join_id = str(j.get("id") or "")
        jid = _nid("join", join_id)
        approval = j.get("approval", {})
        status = approval.get("status", j.get("governance_status", "pending"))
        add_node({
            "id": jid, "layer": 3, "kind": "join", "label": str(j.get("label") or DISPLAY_LABELS.get(str(j.get("key") or ""), str(j.get("key") or "結合"))),
            "sub": f"{j.get('left')} ↔ {j.get('right')}", "status": status,
            "details": {**j, "mode_label": ja_join_mode(j.get("mode")), "reason_label": ja_reason(j.get("reason")), "left_role_label": ja_role(j.get("left_role")), "right_role_label": ja_role(j.get("right_role")), "approval": approval},
        })
        key = str(j.get("key") or "")
        canonical_keys = [x.strip() for x in key.replace(" + ", "+").split("+") if x.strip()]
        for side in ["left", "right"]:
            table_key = str(j.get(side) or "")
            linked = False
            for canonical in canonical_keys:
                cid = columns_by_table_canonical.get((table_key, canonical))
                if cid:
                    add_edge(cid, jid, kind="join_key", label=DISPLAY_LABELS.get(canonical, canonical), status=status, details={"side": side})
                    linked = True
            if not linked:
                tid = _nid("table", table_key)
                if tid in seen_nodes:
                    add_edge(tid, jid, kind="join_table", label=key, status=status, details={"side": side})

    # Analysis modules. Active modules are prominent; waiting modules are still included to show what additional data unlocks.
    modules = capabilities.get("modules", {})
    for mid, m in modules.items():
        mnid = _nid("module", mid)
        enabled = bool(m.get("enabled"))
        add_node({
            "id": mnid, "layer": 4, "kind": "module", "label": str(m.get("name") or mid),
            "sub": "稼働中" if enabled else "データ待ち", "status": "active" if enabled else "waiting",
            "details": m,
        })
        required = list(m.get("requires_all") or []) + list(m.get("requires_any") or [])
        # Direct role/table → module lineage.
        for signal in required:
            if signal in role_tables:
                for tid in role_tables[signal]:
                    add_edge(tid, mnid, kind="enables", label=ja_signal(signal), status="active" if enabled else "waiting")
            else:
                # Document/vision/acoustic are file-backed rather than structured table roles.
                ext_groups = {
                    "documents": {".pdf", ".docx", ".txt", ".md"},
                    "acoustic": {".wav"},
                    "vision": {".png", ".jpg", ".jpeg", ".bmp", ".webp"},
                }
                exts = ext_groups.get(signal, set())
                for n in nodes:
                    if n.get("kind") == "file" and Path(str(n.get("sub") or "")).suffix.lower() in exts:
                        add_edge(n["id"], mnid, kind="enables", label=ja_signal(signal), status="active" if enabled else "waiting")

        # Approved/pending joins whose endpoint roles together satisfy a multi-role module also flow into that module.
        if len(required) >= 2:
            req = set(required)
            for j in catalog.get("joins", []):
                roles = {str(j.get("left_role") or ""), str(j.get("right_role") or "")}
                if req.issubset(roles):
                    add_edge(_nid("join", str(j.get("id") or "")), mnid, kind="supports_analysis", label=" + ".join(ja_signal(x) for x in sorted(req)), status=j.get("approval", {}).get("status", "pending"))

    by_kind = {k: sum(1 for n in nodes if n.get("kind") == k) for k in ["file", "table", "column", "join", "module"]}
    status_counts: defaultdict[str, int] = defaultdict(int)
    for n in nodes:
        status_counts[str(n.get("status") or "unknown")] += 1
    return {
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "nodes": len(nodes), "edges": len(edges), "by_kind": by_kind,
            "approved": status_counts.get("approved", 0), "pending": status_counts.get("pending", 0),
            "held": status_counts.get("held", 0), "rejected": status_counts.get("rejected", 0),
            "active_modules": capabilities.get("active_count", 0),
        },
        "layers": [
            {"id": 0, "label": "ファイル"}, {"id": 1, "label": "テーブル"}, {"id": 2, "label": "意味付けされた列"},
            {"id": 3, "label": "結合"}, {"id": 4, "label": "分析"},
        ],
    }
