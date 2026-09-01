from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import ROOT

DASHBOARD_DATA_DIR = ROOT / "sample_data" / "dashboard"


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DASHBOARD_DATA_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _num(value: str, cast=float) -> float | int:
    try:
        return cast(value)
    except (TypeError, ValueError):
        return 0


# Each KPI has its own good/warn/bad cutline (an OEE of 82% reads as healthy,
# but an achievement rate of 82% does not) rather than one shared threshold.
_THRESHOLDS = {
    "oee": (75, 65),
    "availability": (85, 80),
    "achievement": (88, 75),
    "quality": (90, 80),
}


def _kpi_state(pct: float, metric: str = "quality") -> str:
    good, warn = _THRESHOLDS.get(metric, (90, 80))
    if pct >= good:
        return "good"
    if pct >= warn:
        return "warn"
    return "bad"


def production_dashboard_data(factory_name: str = "元町工場") -> dict[str, Any]:
    kpi_rows = _read_csv("production_kpis.csv")
    lines = []
    factory_kpi = None
    for row in kpi_rows:
        entry = {
            "key": row["line_key"],
            "label": row["line_label"],
            "oee": _num(row["oee_pct"], int),
            "availability": _num(row["availability_pct"], int),
            "achievement": _num(row["achievement_pct"], int),
            "quality": _num(row["quality_pct"], int),
            "plan_qty": _num(row["plan_qty"], int),
            "actual_qty": _num(row["actual_qty"], int),
        }
        entry["oee_state"] = _kpi_state(entry["oee"], "oee")
        entry["availability_state"] = _kpi_state(entry["availability"], "availability")
        entry["achievement_state"] = _kpi_state(entry["achievement"], "achievement")
        entry["quality_state"] = _kpi_state(entry["quality"], "quality")
        if entry["key"] == "all":
            factory_kpi = entry
        else:
            lines.append(entry)

    trend_rows = _read_csv("oee_trend.csv")
    oee_trend = {
        "labels": [r["time"] for r in trend_rows],
        "series": {
            "line1": [_num(r["line1"]) for r in trend_rows],
            "line2": [_num(r["line2"]) for r in trend_rows],
            "line3": [_num(r["line3"]) for r in trend_rows],
            "line4": [_num(r["line4"]) for r in trend_rows],
            "all": [_num(r["all"]) for r in trend_rows],
        },
    }

    progress_rows = _read_csv("production_progress.csv")
    production_progress = {
        "labels": [f"{int(r['hour']):02d}:00" for r in progress_rows],
        "line1": [_num(r["line1"], int) for r in progress_rows],
        "line2": [_num(r["line2"], int) for r in progress_rows],
        "line3": [_num(r["line3"], int) for r in progress_rows],
        "line4": [_num(r["line4"], int) for r in progress_rows],
        "cumulative_actual": [_num(r["cumulative_actual"], int) for r in progress_rows],
        "target": [_num(r["target"], int) for r in progress_rows],
    }

    return {
        "factory_name": factory_name,
        "factory_kpi": factory_kpi,
        "lines": lines,
        "oee_trend": oee_trend,
        "production_progress": production_progress,
    }


def equipment_monitor_data() -> dict[str, Any]:
    gauge_rows = _read_csv("equipment_gauges.csv")
    gauges = {
        row["metric_key"]: {
            "label": row["metric_label"],
            "value": _num(row["value"]),
            "min": _num(row["min"]),
            "max": _num(row["max"]),
            "unit": row["unit"],
        }
        for row in gauge_rows
    }

    status = {row["key"]: row["value"] for row in _read_csv("equipment_status.csv")}

    timeline_rows = _read_csv("equipment_status_timeline.csv")
    devices: dict[str, list[dict[str, str]]] = {}
    for row in timeline_rows:
        devices.setdefault(row["device"], []).append(
            {"start": row["start"], "end": row["end"], "state": row["state"]}
        )

    stop_reasons = [
        {"reason": r["reason"], "percent": _num(r["percent"])}
        for r in _read_csv("stop_reason_breakdown.csv")
    ]

    monthly_rows = _read_csv("uptime_downtime_monthly.csv")
    categories = ["稼働", "段取り替え", "メンテナンス", "設備停止", "その他"]
    uptime_monthly = {
        "labels": [r["month"] for r in monthly_rows],
        "series": {cat: [_num(r[cat], int) for r in monthly_rows] for cat in categories},
    }

    pareto_rows = _read_csv("stop_reason_pareto.csv")
    pareto = {
        "labels": [r["reason"] for r in pareto_rows],
        "minutes": [_num(r["minutes"], int) for r in pareto_rows],
        "cum_pct": [_num(r["cum_pct"]) for r in pareto_rows],
    }

    return {
        "gauges": gauges,
        "status": status,
        "devices": devices,
        "stop_reasons": stop_reasons,
        "uptime_monthly": uptime_monthly,
        "pareto": pareto,
    }


def bolt_torque_data() -> dict[str, Any]:
    reading_rows = _read_csv("bolt_torque_readings.csv")
    torque_series = {
        "labels": [r["time"] for r in reading_rows],
        "bolt1": [_num(r["bolt1_torque_nm"]) for r in reading_rows],
        "bolt2": [_num(r["bolt2_torque_nm"]) for r in reading_rows],
    }
    angle_series = {
        "labels": [r["time"] for r in reading_rows],
        "bolt1": [_num(r["bolt1_angle_deg"]) for r in reading_rows],
        "bolt2": [_num(r["bolt2_angle_deg"]) for r in reading_rows],
    }

    prediction = {row["key"]: row["value"] for row in _read_csv("bolt_torque_prediction.csv")}
    prediction["anomaly_score"] = _num(prediction.get("anomaly_score", 0))
    prediction["target_torque_nm"] = _num(prediction.get("target_torque_nm", 0))
    prediction["tolerance_nm"] = _num(prediction.get("tolerance_nm", 0))
    prediction["good_parts_5m"] = _num(prediction.get("good_parts_5m", 0), int)
    prediction["total_parts_5m"] = _num(prediction.get("total_parts_5m", 0), int)

    factors = [
        {"factor": r["factor"], "percent": _num(r["percent"])}
        for r in _read_csv("bolt_torque_prediction_factors.csv")
    ]

    latest_bolt1 = torque_series["bolt1"][-1] if torque_series["bolt1"] else 0
    latest_bolt2 = torque_series["bolt2"][-1] if torque_series["bolt2"] else 0

    return {
        "torque_series": torque_series,
        "angle_series": angle_series,
        "prediction": prediction,
        "factors": factors,
        "latest": {"bolt1_torque": latest_bolt1, "bolt2_torque": latest_bolt2},
    }


def line_list_data() -> dict[str, Any]:
    hourly_rows = _read_csv("line_hourly_production.csv")
    hourly_labels = [r["time"] for r in hourly_rows]

    lines = []
    for row in _read_csv("line_overview.csv"):
        key = row["line_key"]
        lines.append({
            "key": key,
            "label": row["line_label"],
            "current_count": _num(row["current_count"], int),
            "gauge_max": _num(row["gauge_max"], int),
            "hourly": {
                "labels": hourly_labels,
                "values": [_num(r[key], int) for r in hourly_rows],
            },
        })

    defect_rows = {r["key"]: r["value"] for r in _read_csv("inspection_defects.csv")}
    defects = {
        "label": defect_rows.get("label", "検査不良数"),
        "value": _num(defect_rows.get("value", 0), int),
        "max": _num(defect_rows.get("max", 20), int),
    }

    return {"lines": lines, "defects": defects}


def machine_learning_data() -> dict[str, Any]:
    series_rows = _read_csv("anomaly_detection_series.csv")
    anomaly_series = {
        "labels": [r["timestamp"] for r in series_rows],
        "date_labels": [r["date_label"] for r in series_rows],
        "get_value": [_num(r["get_value"]) for r in series_rows],
        "anomaly_score": [_num(r["anomaly_score"]) for r in series_rows],
    }

    summary_rows = {r["key"]: r["value"] for r in _read_csv("anomaly_summary.csv")}
    summary = {
        "state": summary_rows.get("state", "正常"),
        "anomaly_pct": _num(summary_rows.get("anomaly_pct", 0)),
        "normal_pct": _num(summary_rows.get("normal_pct", 0)),
        "threshold": _num(summary_rows.get("threshold", 8)),
    }

    history = [
        {
            "created_at": r["created_at"],
            "algorithm": r["algorithm"],
            "mean": r["param_mean"],
            "variance": r["param_variance"],
        }
        for r in _read_csv("model_training_history.csv")
    ]

    trend_rows = _read_csv("model_parameter_trend.csv")
    trend = {
        "labels": [r["date"] for r in trend_rows],
        "mean": [_num(r["mean"]) for r in trend_rows],
        "variance": [_num(r["variance"]) for r in trend_rows],
    }

    return {"anomaly_series": anomaly_series, "summary": summary, "history": history, "trend": trend}
