from __future__ import annotations

"""Interpretable threshold forecasting for equipment telemetry.

This is intentionally *not* called Remaining Useful Life.  Without labelled
failure histories, a model cannot honestly estimate RUL.  Instead this module
fits a local trend and estimates when a signal would cross a robust abnormal
operating band if the recent trend continued.
"""

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .sensor_ai import SENSOR_COLUMNS, _load_logs


@dataclass
class ThresholdForecast:
    equipment_id: str
    signal: str
    latest: float
    lower_limit: float
    upper_limit: float
    trend_per_minute: float
    minutes_to_limit: float | None
    direction: str
    state: str

    def as_dict(self) -> dict:
        return asdict(self)


def threshold_forecast(data_dir: Path, horizon_min: int = 480) -> dict:
    df = _load_logs(data_dir)
    if df.empty or "equipment_id" not in df.columns:
        return {"available": False, "items": []}
    items: list[ThresholdForecast] = []
    for eq, g in df.groupby("equipment_id"):
        if "timestamp" in g.columns:
            g = g.sort_values("timestamp")
        for signal in SENSOR_COLUMNS:
            if signal not in g.columns:
                continue
            cols = [signal] + (["timestamp"] if "timestamp" in g.columns else [])
            xdf = g[cols].copy()
            xdf[signal] = pd.to_numeric(xdf[signal], errors="coerce")
            xdf = xdf.dropna(subset=[signal])
            if len(xdf) < 12:
                continue
            vals = xdf[signal].astype(float).to_numpy()
            split = max(8, int(len(vals) * 0.60))
            base = vals[:split]
            med = float(np.median(base))
            mad = float(np.median(np.abs(base - med)))
            scale = max(1.4826 * mad, float(np.std(base)), max(abs(med) * 0.01, 1e-6))
            lo, hi = med - 4.0 * scale, med + 4.0 * scale
            n = min(12, len(vals))
            recent = vals[-n:]
            if "timestamp" in xdf.columns and xdf["timestamp"].notna().sum() >= n:
                t = pd.to_datetime(xdf["timestamp"], errors="coerce").iloc[-n:]
                t0 = t.iloc[0]
                minutes = (t - t0).dt.total_seconds().to_numpy(dtype=float) / 60.0
                if not np.all(np.isfinite(minutes)) or np.ptp(minutes) < 1e-9:
                    minutes = np.arange(n, dtype=float)
            else:
                minutes = np.arange(n, dtype=float)
            slope = float(np.polyfit(minutes, recent, 1)[0]) if n >= 3 else 0.0
            latest = float(recent[-1])
            ttl: float | None = None
            direction = "stable"
            if slope > 1e-12:
                direction = "upper"
                candidate = (hi - latest) / slope
                if candidate >= 0:
                    ttl = float(candidate)
            elif slope < -1e-12:
                direction = "lower"
                candidate = (lo - latest) / slope
                if candidate >= 0:
                    ttl = float(candidate)
            already = latest < lo or latest > hi
            if already:
                state = "critical"
                ttl = 0.0
            elif ttl is not None and ttl <= horizon_min * 0.25:
                state = "critical"
            elif ttl is not None and ttl <= horizon_min:
                state = "warning"
            else:
                state = "healthy"
            items.append(ThresholdForecast(str(eq), signal, latest, lo, hi, slope, ttl, direction, state))
    items.sort(key=lambda x: (x.minutes_to_limit is None, x.minutes_to_limit if x.minutes_to_limit is not None else 1e99))
    return {
        "available": bool(items),
        "horizon_min": horizon_min,
        "items": [x.as_dict() for x in items],
        "note": "Trend-to-threshold forecast, not failure probability or RUL.",
    }


def sktime_available() -> bool:
    try:
        import sktime  # type: ignore  # noqa:F401
        return True
    except Exception:
        return False
