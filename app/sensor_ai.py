from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import choose_role_tables_multi, load_role_frame, scan_tables

SENSOR_COLUMNS = ["current_a", "temperature_c", "vibration_mm_s", "pressure_mpa", "torque_nm"]


@dataclass
class SensorSignalHealth:
    name: str
    latest: float | None
    baseline_median: float | None
    robust_z: float
    shift_pct: float
    trend_per_step: float
    anomaly_score: float


@dataclass
class EquipmentHealth:
    equipment_id: str
    health_score: float
    risk_score: float
    state: str
    signals: list[SensorSignalHealth]
    source_files: list[str]

    def as_dict(self):
        return {**asdict(self), "signals": [asdict(x) for x in self.signals]}


def _load_logs(data_dir: Path) -> pd.DataFrame:
    profiles, _ = scan_tables(data_dir)
    roles = choose_role_tables_multi(profiles)
    rp = roles.get("equipment_logs") or []
    if not rp:
        return pd.DataFrame()
    df = load_role_frame(data_dir, rp)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    for c in SENSOR_COLUMNS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _signal_health(s: pd.Series, name: str) -> SensorSignalHealth | None:
    s = pd.to_numeric(s, errors="coerce").dropna().astype(float)
    if len(s) < 6:
        return None
    target_n = max(1, min(5, len(s) // 5))
    recent = s.tail(target_n)
    baseline = s.iloc[:-target_n]
    if len(baseline) < 4:
        baseline = s.head(max(4, len(s) - 1))
        recent = s.tail(1)
    med = float(baseline.median())
    mad = float((baseline - med).abs().median())
    sigma = 1.4826 * mad
    std = float(baseline.std(ddof=0))
    scale = sigma if sigma > 1e-9 else (std if std > 1e-9 else 1.0)
    latest = float(recent.mean())
    rz = float(abs(latest - med) / scale)
    pct = float((latest - med) / med * 100) if abs(med) > 1e-9 else 0.0
    x = np.arange(len(s), dtype=float)
    slope = float(np.polyfit(x, s.to_numpy(), 1)[0]) if len(s) >= 3 else 0.0
    # intentionally interpretable heuristic, not failure probability
    anomaly = float(np.clip(max(rz / 4.0, abs(pct) / 30.0), 0, 1))
    return SensorSignalHealth(name, latest, med, rz, pct, slope, anomaly)


def equipment_health(data_dir: Path) -> list[EquipmentHealth]:
    df = _load_logs(data_dir)
    if df.empty or "equipment_id" not in df.columns:
        return []
    out: list[EquipmentHealth] = []
    for eq, group in df.groupby("equipment_id"):
        if "timestamp" in group.columns:
            group = group.sort_values("timestamp")
        sigs = [x for c in SENSOR_COLUMNS if c in group.columns for x in [_signal_health(group[c], c)] if x is not None]
        if not sigs:
            continue
        risk = float(np.clip(np.mean(sorted((s.anomaly_score for s in sigs), reverse=True)[:3]), 0, 1))
        health = 1.0 - risk
        state = "critical" if risk >= 0.65 else "warning" if risk >= 0.35 else "healthy"
        src = sorted(set(group.get("_source_file", pd.Series(dtype=str)).dropna().astype(str)))
        out.append(EquipmentHealth(str(eq), health, risk, state, sigs, src))
    return sorted(out, key=lambda x: x.risk_score, reverse=True)


def river_online_scores(rows: list[dict]) -> list[float]:
    """Optional streaming anomaly detector using River HalfSpaceTrees.

    Returns one score per row. This dependency is optional so the core product
    stays lightweight; install requirements-ai.txt to enable it.
    """
    try:
        from river import anomaly, preprocessing  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("river is not installed") from exc
    model = preprocessing.MinMaxScaler() | anomaly.HalfSpaceTrees(seed=42)
    scores = []
    for row in rows:
        x = {str(k): float(v) for k, v in row.items() if isinstance(v, (int, float)) and np.isfinite(v)}
        scores.append(float(model.score_one(x)))
        model.learn_one(x)
    return scores
