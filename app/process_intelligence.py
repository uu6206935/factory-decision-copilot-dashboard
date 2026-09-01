from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import choose_role_tables_multi, load_role_frame, scan_tables


def _load_process(data_dir: Path) -> pd.DataFrame:
    profiles, _ = scan_tables(data_dir)
    roles = choose_role_tables_multi(profiles)
    rp = roles.get("process") or []
    if not rp:
        return pd.DataFrame()
    df = load_role_frame(data_dir, rp)
    for c in ["start_time", "end_time", "timestamp"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def process_snapshot(data_dir: Path, target_id: str | None = None) -> dict:
    df = _load_process(data_dir)
    if df.empty or not {"vehicle_id", "equipment_id"}.issubset(df.columns):
        return {"available": False, "variants": [], "bottlenecks": [], "deviations": []}
    order_col = next((c for c in ["start_time", "timestamp", "end_time"] if c in df.columns), None)
    sequences: dict[str, list[str]] = {}
    cycle_rows = []
    for vid, g in df.groupby("vehicle_id"):
        if order_col:
            g = g.sort_values(order_col)
        seq = g["equipment_id"].astype(str).tolist()
        sequences[str(vid)] = seq
        if "start_time" in g.columns and "end_time" in g.columns:
            dur = (g["end_time"] - g["start_time"]).dt.total_seconds() / 60
            for eq, minutes in zip(g["equipment_id"].astype(str), dur):
                if pd.notna(minutes) and minutes >= 0:
                    cycle_rows.append((eq, float(minutes)))
    variants = Counter(" → ".join(v) for v in sequences.values())
    modal = variants.most_common(1)[0][0] if variants else ""
    variant_rows = [{"path": p, "count": n, "share": n / max(len(sequences), 1)} for p, n in variants.most_common(12)]
    deviations = []
    for vid, seq in sequences.items():
        path = " → ".join(seq)
        if modal and path != modal:
            deviations.append({"target_id": vid, "path": path, "expected": modal, "severity": "warning"})
    if target_id:
        deviations.sort(key=lambda x: 0 if str(x["target_id"]).upper() == str(target_id).upper() else 1)
    bottlenecks = []
    if cycle_rows:
        cdf = pd.DataFrame(cycle_rows, columns=["equipment_id", "minutes"])
        stats = cdf.groupby("equipment_id")["minutes"].agg(["median", "mean", "count"]).reset_index()
        stats["p90"] = cdf.groupby("equipment_id")["minutes"].quantile(0.9).values
        stats = stats.sort_values("p90", ascending=False)
        bottlenecks = stats.head(10).round(3).to_dict("records")
    return {
        "available": True,
        "case_count": len(sequences),
        "modal_path": modal,
        "variants": variant_rows,
        "deviations": deviations[:50],
        "bottlenecks": bottlenecks,
        "target_path": " → ".join(sequences.get(str(target_id), [])) if target_id else None,
    }


def pm4py_available() -> bool:
    try:
        import pm4py  # type: ignore  # noqa:F401
        return True
    except Exception:
        return False
