from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from .config import DATA_DIR
from .capabilities import detect_capabilities
from .data_quality import run_data_quality
from .database import save_snapshot
from .ingest import load_chunks
from .metrics import CATALOG_CHUNKS, CATALOG_FILES, CATALOG_TABLES
from .provenance import build_file_catalog
from .schema import catalog_as_dict, discover_join_candidates, scan_tables
from .vectorstore import SearchBackend


@dataclass
class PlatformState:
    chunks: list
    profiles: list
    warnings: list[str]
    retriever: SearchBackend
    file_catalog: list[dict]
    data_quality: dict
    capabilities: dict
    joins: list[dict]
    snapshot_id: int | None = None


_lock = RLock()
_STATE: PlatformState | None = None


def rebuild(save: bool = True) -> PlatformState:
    global _STATE
    with _lock:
        chunks, warnings = load_chunks(DATA_DIR)
        profiles, sw = scan_tables(DATA_DIR)
        files = build_file_catalog(DATA_DIR)
        retriever = SearchBackend(chunks)
        dq = run_data_quality(DATA_DIR)
        caps = detect_capabilities(DATA_DIR, profiles=profiles, chunks=chunks)
        joins = discover_join_candidates(DATA_DIR, profiles)
        state = PlatformState(chunks, profiles, warnings + sw, retriever, files, dq, caps, joins)
        CATALOG_CHUNKS.set(len(chunks)); CATALOG_TABLES.set(len(profiles)); CATALOG_FILES.set(len(files))
        if save:
            try:
                state.snapshot_id = save_snapshot(len(files), len(profiles), len(chunks), files)
            except Exception:
                state.snapshot_id = None
        _STATE = state
        return state


def get_state() -> PlatformState:
    global _STATE
    return _STATE or rebuild(save=False)


def catalog_payload() -> dict:
    s = get_state()
    tables = catalog_as_dict(s.profiles)
    review_tables = sum(1 for t in tables if t.get("review_required"))
    mapped_cols = sum(len(t.get("mapping", {})) for t in tables)
    total_cols = sum(len(t.get("columns", [])) for t in tables)
    auto_cols = sum(1 for t in tables for c in t.get("column_profiles", []) if c.get("status") in {"auto", "approved", "learned"})
    return {
        "data_dir": str(DATA_DIR),
        "files": s.file_catalog,
        "tables": tables,
        "joins": s.joins,
        "schema_summary": {
            "engine": "local_semantic_profile_v2 + DeepSeek-V4-Flash semantic reasoning",
            "tables": len(tables),
            "review_tables": review_tables,
            "mapped_columns": mapped_cols,
            "total_columns": total_cols,
            "auto_columns": auto_cols,
            "join_candidates": len(s.joins),
            "high_confidence_joins": sum(1 for j in s.joins if j.get("confidence", 0) >= 0.9),
        },
        "data_quality": s.data_quality,
        "warnings": s.warnings,
        "retrieval_backend": s.retriever.backend,
        "snapshot_id": s.snapshot_id,
        "capabilities": s.capabilities,
    }
