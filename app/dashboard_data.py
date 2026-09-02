from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import ROOT, DEEPSEEK_SEND_STRUCTURED_EVIDENCE
from .deepseek import available as deepseek_available, chat as deepseek_chat, DeepSeekError

DASHBOARD_DATA_DIR = ROOT / "dashboard_data"


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


def _ccr_delta(tier: str, delta: str) -> dict[str, str]:
    up = delta.strip().startswith("+")
    arrow = "↑" if up else "↓"
    # "good"/"critical" tiers are rate-type (higher = better); "neutral" tiers
    # are count-type (lower = better), so the same arrow direction flips meaning.
    favorable = up if tier in {"good", "critical"} else not up
    return {"text": delta, "arrow": arrow, "cls": "good" if favorable else "bad"}


def quality_ccr_data() -> dict[str, Any]:
    meta = {r["key"]: r["value"] for r in _read_csv("quality_ccr_meta.csv")}

    kpis = []
    for r in _read_csv("quality_ccr_kpis.csv"):
        kpis.append({
            "key": r["key"], "label": r["label"], "value": r["value"], "unit": r["unit"],
            "day_delta": _ccr_delta(r["tier"], r["day_delta"]),
            "week_delta": _ccr_delta(r["tier"], r["week_delta"]),
            "tier": r["tier"],
        })

    rework_rate_rows = {r["key"]: r["value"] for r in _read_csv("quality_ccr_rework_rate.csv")}
    rework_rate = {
        "label": rework_rate_rows.get("label", ""),
        "value": rework_rate_rows.get("value", ""),
        "rework_total": rework_rate_rows.get("rework_total", ""),
        "production_total": rework_rate_rows.get("production_total", ""),
    }

    worst_rework = [
        {"rank": r["rank"], "process": r["process"], "count": r["count"], "day_delta": _ccr_delta("neutral", r["day_delta"]), "flag": r["flag"]}
        for r in _read_csv("quality_worst_rework.csv")
    ]
    worst_calls = [
        {"rank": r["rank"], "process": r["process"], "count": r["count"], "day_delta": _ccr_delta("neutral", r["day_delta"]), "flag": r["flag"]}
        for r in _read_csv("quality_worst_calls.csv")
    ]

    trend_rows = _read_csv("quality_rework_trend.csv")
    trend = {
        "labels": [r["date"] for r in trend_rows],
        "red": [_num(r["red"], int) for r in trend_rows],
        "yellow": [_num(r["yellow"], int) for r in trend_rows],
        "blue": [_num(r["blue"], int) for r in trend_rows],
    }

    suggestions = [{"color": r["color"], "text": r["text"]} for r in _read_csv("quality_ai_suggestions.csv")]

    return {
        "meta": meta,
        "kpis": kpis,
        "rework_rate": rework_rate,
        "worst_rework": worst_rework,
        "worst_calls": worst_calls,
        "trend": trend,
        "suggestions": suggestions,
    }


def nutrunner_detail_data() -> dict[str, Any]:
    meta = {r["key"]: r["value"] for r in _read_csv("nutrunner_meta.csv")}
    alert_info = {r["key"]: r["value"] for r in _read_csv("nutrunner_alert_info.csv")}
    structure = [{"stage": r["stage"], "state": r["state"]} for r in _read_csv("nutrunner_structure.csv")]

    sensor_rows = _read_csv("nutrunner_sensors.csv")
    sensors = {
        "labels": [r["time"] for r in sensor_rows],
        "anomaly_score": [_num(r["anomaly_score"]) for r in sensor_rows],
        "torque": [_num(r["torque"]) for r in sensor_rows],
        "rotation": [_num(r["rotation"]) for r in sensor_rows],
        "motor_current": [_num(r["motor_current"]) for r in sensor_rows],
        "temperature": [_num(r["temperature"]) for r in sensor_rows],
    }
    alert_marker_rows = {r["key"]: r["value"] for r in _read_csv("nutrunner_alert_marker.csv")}
    alert_marker = {"index": _num(alert_marker_rows.get("index", 0), int), "label": alert_marker_rows.get("label", "")}

    score_mini_rows = _read_csv("nutrunner_score_mini.csv")
    score_mini = {"labels": [r["time"] for r in score_mini_rows], "values": [_num(r["value"]) for r in score_mini_rows]}
    latest_score = score_mini["values"][-1] if score_mini["values"] else 0

    score_7day_rows = _read_csv("nutrunner_score_7day.csv")
    score_7day = {"labels": [r["date"] for r in score_7day_rows], "values": [_num(r["value"]) for r in score_7day_rows]}

    recon_rows = _read_csv("nutrunner_reconstruction.csv")
    reconstruction = {"labels": [r["time"] for r in recon_rows], "values": [_num(r["value"]) for r in recon_rows]}
    recon_threshold_rows = {r["key"]: r["value"] for r in _read_csv("nutrunner_reconstruction_threshold.csv")}
    reconstruction["threshold"] = _num(recon_threshold_rows.get("threshold", 0.35))

    dist_rows = _read_csv("nutrunner_distribution.csv")
    distribution = {"buckets": [_num(r["bucket"], int) for r in dist_rows], "frequency": [_num(r["frequency"], int) for r in dist_rows]}
    dist_marker_rows = {r["key"]: r["value"] for r in _read_csv("nutrunner_distribution_marker.csv")}
    distribution["marker"] = {"value": _num(dist_marker_rows.get("value", 0), int), "label": dist_marker_rows.get("label", "")}

    chat = [{"sender": r["sender"], "time": r["time"], "kind": r["kind"], "text": r["text"]} for r in _read_csv("nutrunner_ai_chat.csv")]

    return {
        "meta": meta,
        "alert_info": alert_info,
        "structure": structure,
        "sensors": sensors,
        "alert_marker": alert_marker,
        "score_mini": score_mini,
        "latest_score": latest_score,
        "score_7day": score_7day,
        "reconstruction": reconstruction,
        "distribution": distribution,
        "chat": chat,
    }


def _nutrunner_context_text(nr: dict[str, Any]) -> str:
    """Compact Japanese-language summary of every nutrunner_*.csv table,
    used as grounding context for the AI assistant chat. Kept as a distilled
    summary (not the raw 49-row time series) so it stays cheap to send and
    the model can't cherry-pick unrepresentative individual points."""
    meta, alert = nr["meta"], nr["alert_info"]
    structure_lines = "\n".join(f"- {s['stage']}: {'異常' if s['state']=='critical' else '注意' if s['state']=='warning' else '正常'}" for s in nr["structure"])

    sensors = nr["sensors"]
    def trend(key: str, unit: str = "") -> str:
        vals = sensors[key]
        return f"開始{vals[0]}{unit}→現在{vals[-1]}{unit}（最小{min(vals)}{unit}／最大{max(vals)}{unit}）"

    recon = nr["reconstruction"]
    recon_max = max(recon["values"])
    recon_max_time = recon["labels"][recon["values"].index(recon_max)]

    week = nr["score_7day"]
    week_text = "、".join(f"{d}: {v}" for d, v in zip(week["labels"], week["values"]))

    return f"""【設備】{meta.get('equipment_name')}（{meta.get('tag')}）／{meta.get('area_line')}
【現在時刻】{meta.get('report_datetime')}

【異常スコア】現在値 {nr['latest_score']}/100（閾値70）、判定: {alert.get('latest_alert_level')}
【最新アラート】検出時刻 {alert.get('latest_alert_time')}、判定 {alert.get('alert_verdict')}、検知継続 {alert.get('detection_streak')}
【モデル】{alert.get('model_name')}（学習データ期間 {alert.get('training_period')}）

【設備構成の状態】
{structure_lines}

【直近24時間（05/18 10:30〜05/19 10:30）のセンサー推移】
- 異常スコア: {trend('anomaly_score')}
- 締め付けトルク: {trend('torque')}
- 回転数: {trend('rotation')}
- モーター電流: {trend('motor_current')}
- 温度: {trend('temperature')}

【再構成誤差（Autoencoder出力）】閾値 {recon['threshold']}、直近24時間の最大値 {recon_max}（{recon_max_time} 発生）

【過去7日間の異常スコア推移】{week_text}"""


def nutrunner_ai_ask(question: str) -> dict[str, Any]:
    if not deepseek_available():
        return {"ok": False, "error": "DeepSeek APIが設定されていません。.env.local に DEEPSEEK_API_KEY を設定すると回答できるようになります。"}

    nr = nutrunner_detail_data()
    context = _nutrunner_context_text(nr) if DEEPSEEK_SEND_STRUCTURED_EVIDENCE else "[設備データの送信は設定で無効化されています]"
    user_prompt = f"以下は監視対象設備の実データです。この情報だけを根拠に、質問に日本語で答えてください。\n\n{context}\n\n【質問】\n{question}"
    try:
        answer = deepseek_chat(
            system=(
                "あなたは製造設備の異常検知AIアシスタントです。渡された設備の実データだけを根拠に回答し、"
                "データにない数値や原因を創作しないでください。箇条書きを使ってもよいですが、"
                "レポートのような長文にはせず、チャットの返信として自然な分量（数行〜十数行程度）にまとめてください。"
                "回答はプレーンテキストで返し、Markdown記法（見出しの # や太字の **）は一切使わないでください。"
            ),
            user=user_prompt,
            thinking=False,
            reasoning_effort="low",
            max_tokens=1000,
            temperature=0.2,
        )
        return {"ok": True, "answer": answer}
    except DeepSeekError as exc:
        return {"ok": False, "error": f"DeepSeekへの問い合わせに失敗しました（{exc}）"}


def anomaly_dashboard_data() -> dict[str, Any]:
    meta = {r["key"]: r["value"] for r in _read_csv("anomaly_dashboard_meta.csv")}
    summary = [{"tier": r["tier"], "label": r["label"], "count": r["count"], "link_label": r["link_label"]} for r in _read_csv("anomaly_dashboard_summary.csv")]

    areas: dict[str, dict[str, Any]] = {}
    for r in _read_csv("anomaly_dashboard_map.csv"):
        area = areas.setdefault(r["area"], {"area_label": r["area_label"], "equipment": []})
        area["equipment"].append({"eq_id": r["eq_id"], "icon": r["icon"], "state": r["state"]})
    map_areas = [areas[k] for k in sorted(areas.keys())]

    alerts = [{"time": r["time"], "eq_id": r["eq_id"], "eq_name": r["eq_name"], "level": r["level"], "content": r["content"]} for r in _read_csv("anomaly_dashboard_alerts.csv")]

    trend_series_rows = _read_csv("anomaly_dashboard_trend_series.csv")
    series_by_eq: dict[str, dict[str, list]] = {}
    for r in trend_series_rows:
        s = series_by_eq.setdefault(r["eq_id"], {"labels": [], "values": []})
        s["labels"].append(r["time"])
        s["values"].append(_num(r["value"]))

    trend_cards = []
    for r in _read_csv("anomaly_dashboard_trend.csv"):
        trend_cards.append({
            "eq_id": r["eq_id"], "eq_name": r["eq_name"], "risk": r["risk"], "score": _num(r["score"], int),
            "series": series_by_eq.get(r["eq_id"], {"labels": [], "values": []}),
        })

    top_alerts = [{"rank": r["rank"], "eq_id": r["eq_id"], "eq_name": r["eq_name"], "score": r["score"], "trend": r["trend"]} for r in _read_csv("anomaly_dashboard_top_alerts.csv")]
    details = {r["eq_id"]: r["text"] for r in _read_csv("anomaly_dashboard_ai_details.csv")}
    actions = {r["eq_id"]: r["text"] for r in _read_csv("anomaly_dashboard_ai_actions.csv")}
    predictions = [{"eq_id": r["eq_id"], "eq_name": r["eq_name"], "probability": r["probability"]} for r in _read_csv("anomaly_dashboard_ai_predictions.csv")]
    quick_actions = [r["label"] for r in _read_csv("anomaly_dashboard_quick_actions.csv")]

    return {
        "meta": meta,
        "summary": summary,
        "map_areas": map_areas,
        "alerts": alerts,
        "trend_cards": trend_cards,
        "top_alerts": top_alerts,
        "details": details,
        "actions": actions,
        "predictions": predictions,
        "quick_actions": quick_actions,
    }


def _anomaly_dashboard_context_text(ad: dict[str, Any]) -> str:
    """Compact Japanese-language summary of every anomaly_dashboard_*.csv
    table, used as grounding context for the facility-wide AI assistant."""
    summary_lines = "\n".join(f"- {s['label']}: {s['count']}台" for s in ad["summary"])

    map_lines = []
    for area in ad["map_areas"]:
        states = "、".join(f"{e['eq_id']}({'異常' if e['state']=='critical' else '注意' if e['state']=='warning' else '停止中' if e['state']=='offline' else '正常'})" for e in area["equipment"])
        map_lines.append(f"- {area['area_label']}: {states}")
    map_text = "\n".join(map_lines)

    alert_lines = "\n".join(f"- {a['time']} {a['eq_id']} {a['eq_name']}: {a['level']}「{a['content']}」" for a in ad["alerts"])

    trend_lines = "\n".join(f"- {c['eq_id']} {c['eq_name']}: 異常スコア{c['score']}/100（{c['risk']}）" for c in ad["trend_cards"])

    prediction_lines = "\n".join(f"- {p['eq_id']} {p['eq_name']}: 悪化確率{p['probability']}%" for p in ad["predictions"])

    return f"""【設備ステータスサマリー】
{summary_lines}

【設備配置マップ（エリア別の現在状態）】
{map_text}

【最新アラート】
{alert_lines}

【主要設備の異常スコアトレンド】
{trend_lines}

【今後24時間の悪化予測】
{prediction_lines}"""


def anomaly_dashboard_ai_ask(question: str) -> dict[str, Any]:
    if not deepseek_available():
        return {"ok": False, "error": "DeepSeek APIが設定されていません。.env.local に DEEPSEEK_API_KEY を設定すると回答できるようになります。"}

    ad = anomaly_dashboard_data()
    context = _anomaly_dashboard_context_text(ad) if DEEPSEEK_SEND_STRUCTURED_EVIDENCE else "[設備データの送信は設定で無効化されています]"
    user_prompt = f"以下は工場全体の設備監視の実データです。この情報だけを根拠に、質問に日本語で答えてください。\n\n{context}\n\n【質問】\n{question}"
    try:
        answer = deepseek_chat(
            system=(
                "あなたは工場全体の異常兆候検知AIアシスタントです。渡された設備の実データだけを根拠に回答し、"
                "データにない数値や設備名を創作しないでください。箇条書きを使ってもよいですが、"
                "レポートのような長文にはせず、チャットの返信として自然な分量（数行〜十数行程度）にまとめてください。"
                "回答はプレーンテキストで返し、Markdown記法（見出しの # や太字の **）は一切使わないでください。"
            ),
            user=user_prompt,
            thinking=False,
            reasoning_effort="low",
            max_tokens=1000,
            temperature=0.2,
        )
        return {"ok": True, "answer": answer}
    except DeepSeekError as exc:
        return {"ok": False, "error": f"DeepSeekへの問い合わせに失敗しました（{exc}）"}


def autoencoder_config_data() -> dict[str, Any]:
    meta = {r["key"]: r["value"] for r in _read_csv("autoencoder_meta.csv")}
    tabs = [{"label": r["label"], "active": bool(r["active"])} for r in _read_csv("autoencoder_tabs.csv")]

    sections: dict[str, list] = {"model": [], "training": [], "score": []}
    for r in _read_csv("autoencoder_fields.csv"):
        sections.setdefault(r["section"], []).append({
            "label": r["label"],
            "value": r["value"],
            "kind": r["kind"],
            "options": [o for o in r["options"].split("|")] if r["options"] else [],
        })

    summary = [{"label": r["label"], "value": r["value"]} for r in _read_csv("autoencoder_summary.csv")]

    # Neural-network diagram geometry, computed here so the template stays
    # markup-only: 5 evenly spaced layers, nodes vertically centred, plus the
    # fully-connected edges between neighbouring layers.
    raw_layers = [
        {"layer": _num(r["layer"], int), "label": r["label"], "nodes": _num(r["nodes"], int), "role": r["role"]}
        for r in _read_csv("autoencoder_network.csv")
    ]
    VB_W, VB_H, GAP_Y = 300.0, 150.0, 19.0
    network_layers = []
    for i, lay in enumerate(raw_layers):
        x = 26 + i * ((VB_W - 52) / max(1, len(raw_layers) - 1))
        n = lay["nodes"]
        top = (VB_H - 18) / 2 - ((n - 1) * GAP_Y) / 2 + 12
        network_layers.append({
            **lay,
            "x": round(x, 1),
            "r": 5.0 if lay["role"] == "bottleneck" else 6.0,
            "points": [{"cx": round(x, 1), "cy": round(top + j * GAP_Y, 1)} for j in range(n)],
        })
    network_edges = []
    for a, b in zip(network_layers, network_layers[1:]):
        for p in a["points"]:
            for q in b["points"]:
                network_edges.append({"x1": p["cx"], "y1": p["cy"], "x2": q["cx"], "y2": q["cy"]})
    network = {"layers": network_layers, "edges": network_edges}
    chat = [{"sender": r["sender"], "time": r["time"], "text": r["text"]} for r in _read_csv("autoencoder_ai_chat.csv")]

    return {
        "meta": meta,
        "tabs": tabs,
        "model_fields": sections.get("model", []),
        "training_fields": sections.get("training", []),
        "score_fields": sections.get("score", []),
        "summary": summary,
        "network": network,
        "chat": chat,
    }


def _autoencoder_context_text(ae: dict[str, Any]) -> str:
    """Compact summary of every autoencoder_*.csv table for the AI assistant."""
    def fields(key: str) -> str:
        return "\n".join(f"- {f['label']}: {f['value'] or '（未設定）'}" for f in ae[key])

    summary_lines = "\n".join(f"- {s['label']}: {s['value']}" for s in ae["summary"])
    return f"""【対象設備】{ae['meta'].get('subtitle')} / {ae['meta'].get('title')}

【モデル構成】
{fields('model_fields')}

【学習設定】
{fields('training_fields')}

【異常スコア設定】
{fields('score_fields')}

【現在の設定の概要】
{summary_lines}"""


def autoencoder_ai_ask(question: str) -> dict[str, Any]:
    if not deepseek_available():
        return {"ok": False, "error": "DeepSeek APIが設定されていません。.env.local に DEEPSEEK_API_KEY を設定すると回答できるようになります。"}

    ae = autoencoder_config_data()
    context = _autoencoder_context_text(ae) if DEEPSEEK_SEND_STRUCTURED_EVIDENCE else "[設定データの送信は設定で無効化されています]"
    user_prompt = f"以下はAutoencoder異常検知モデルの現在の設定値です。この設定を踏まえて、質問に日本語で答えてください。\n\n{context}\n\n【質問】\n{question}"
    try:
        answer = deepseek_chat(
            system=(
                "あなたはAutoencoderによる異常検知モデルのチューニングを支援するAIアシスタントです。"
                "渡された現在の設定値を踏まえて実務的な助言をしてください。設定値を偽らず、"
                "レポートのような長文にはせず、チャットの返信として自然な分量（数行〜十数行程度）で、"
                "箇条書きを使ってまとめてください。"
                "回答はプレーンテキストで返し、Markdown記法（見出しの # や太字の **）は一切使わないでください。"
            ),
            user=user_prompt,
            thinking=False,
            reasoning_effort="low",
            max_tokens=1000,
            temperature=0.2,
        )
        return {"ok": True, "answer": answer}
    except DeepSeekError as exc:
        return {"ok": False, "error": f"DeepSeekへの問い合わせに失敗しました（{exc}）"}
