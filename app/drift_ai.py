from __future__ import annotations

"""Lightweight manufacturing data-drift checks.

The built-in implementation intentionally avoids binding the product to any
single monitoring vendor.  It uses interpretable PSI + location/scale shift
metrics and can be replaced or complemented by Evidently in deployments that
want richer monitoring reports.
"""

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .sensor_ai import SENSOR_COLUMNS, _load_logs


@dataclass
class DriftSignal:
    equipment_id: str
    signal: str
    psi: float
    median_shift_pct: float
    scale_shift_pct: float
    drift_score: float
    state: str

    def as_dict(self) -> dict:
        return asdict(self)


def _psi(reference: np.ndarray, current: np.ndarray, bins: int = 8) -> float:
    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]
    if len(reference) < 10 or len(current) < 5:
        return 0.0
    edges = np.quantile(reference, np.linspace(0, 1, bins + 1))
    edges = np.unique(edges)
    if len(edges) < 3:
        lo = min(float(reference.min()), float(current.min()))
        hi = max(float(reference.max()), float(current.max()))
        if hi <= lo:
            return 0.0
        edges = np.linspace(lo, hi, bins + 1)
    edges[0] = -np.inf
    edges[-1] = np.inf
    r, _ = np.histogram(reference, bins=edges)
    c, _ = np.histogram(current, bins=edges)
    r = np.clip(r / max(r.sum(), 1), 1e-6, None)
    c = np.clip(c / max(c.sum(), 1), 1e-6, None)
    return float(np.sum((c - r) * np.log(c / r)))


def drift_snapshot(data_dir: Path, recent_fraction: float = 0.25) -> dict:
    df = _load_logs(data_dir)
    if df.empty or "equipment_id" not in df.columns:
        return {"available": False, "signals": [], "summary": {"critical": 0, "warning": 0, "healthy": 0}}
    rows: list[DriftSignal] = []
    for eq, group in df.groupby("equipment_id"):
        if "timestamp" in group.columns:
            group = group.sort_values("timestamp")
        for signal in SENSOR_COLUMNS:
            if signal not in group.columns:
                continue
            s = pd.to_numeric(group[signal], errors="coerce").dropna().astype(float).to_numpy()
            if len(s) < 20:
                continue
            n_cur = max(5, int(round(len(s) * recent_fraction)))
            if len(s) - n_cur < 10:
                n_cur = max(5, len(s) // 3)
            reference, current = s[:-n_cur], s[-n_cur:]
            if len(reference) < 10:
                continue
            psi = _psi(reference, current)
            med_ref = float(np.median(reference))
            med_cur = float(np.median(current))
            std_ref = float(np.std(reference))
            std_cur = float(np.std(current))
            med_shift = ((med_cur - med_ref) / abs(med_ref) * 100.0) if abs(med_ref) > 1e-9 else 0.0
            scale_shift = ((std_cur - std_ref) / max(std_ref, 1e-9) * 100.0) if std_ref > 1e-9 else 0.0
            # PSI >= .25 is conventionally substantial. Combine it with
            # interpretable operating-point and variance shifts.
            score = float(np.clip(max(psi / 0.35, abs(med_shift) / 30.0, abs(scale_shift) / 75.0), 0, 1))
            state = "critical" if score >= 0.70 else "warning" if score >= 0.35 else "healthy"
            rows.append(DriftSignal(str(eq), signal, psi, med_shift, scale_shift, score, state))
    rows.sort(key=lambda x: x.drift_score, reverse=True)
    summary = {k: sum(1 for x in rows if x.state == k) for k in ("critical", "warning", "healthy")}
    return {"available": bool(rows), "signals": [x.as_dict() for x in rows], "summary": summary, "method": "PSI + median/scale shift"}


def evidently_available() -> bool:
    try:
        import evidently  # type: ignore  # noqa:F401
        return True
    except Exception:
        return False
