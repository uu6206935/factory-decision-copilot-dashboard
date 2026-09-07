"""Generate dummy CSV datasets that back the Smart Factory dashboard screens.

Deterministic (seeded) so the demo looks identical on every run/restart.
Run: python scripts/generate_dashboard_dummy_data.py
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard_data"
OUT.mkdir(parents=True, exist_ok=True)

rng = random.Random(20261002)


def write_csv(name: str, header: list[str], rows: list[list]) -> None:
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {path.relative_to(ROOT)} ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# 1) production_kpis.csv - factory + line level KPI snapshot (home dashboard)
# ---------------------------------------------------------------------------
write_csv(
    "production_kpis.csv",
    ["line_key", "line_label", "oee_pct", "availability_pct", "achievement_pct", "quality_pct", "plan_qty", "actual_qty"],
    [
        ["all", "工場全体", 82, 95, 89, 96, 153000, 152000],
        ["line1", "ライン1", 81, 92, 92, 96, 3800, 37500],
        ["line2", "ライン2", 62, 76, 85, 96, 3700, 35000],
        ["line3", "ライン3", 88, 97, 94, 97, 3900, 38200],
        ["line4", "ライン4", 74, 88, 79, 95, 3600, 33800],
    ],
)

# ---------------------------------------------------------------------------
# 2) oee_trend.csv - all-equipment OEE trend across the day (line chart)
# ---------------------------------------------------------------------------
rows = []
bases = {"line1": 84, "line2": 78, "line3": 88, "line4": 81, "all": 87}
walk = {k: 0.0 for k in bases}
for step in range(73):  # 00:00 .. 24:00 every 20min
    hh = (step * 20) // 60
    mm = (step * 20) % 60
    ts = f"{hh:02d}:{mm:02d}"
    row = [ts]
    for key, base in bases.items():
        walk[key] += rng.uniform(-4.5, 4.5)
        walk[key] *= 0.72
        seasonal = 4 * math.sin(step / 7.0 + hash(key) % 5)
        val = base + walk[key] + seasonal
        val = max(68, min(97, val))
        row.append(round(val, 1))
    rows.append(row)
write_csv("oee_trend.csv", ["time", "line1", "line2", "line3", "line4", "all"], rows)

# ---------------------------------------------------------------------------
# 3) production_progress.csv - hourly stacked production (left axis, small
#    scale) plus a whole-factory cumulative actual/target pace (right axis,
#    large scale) that tracks the 152,000 / 153,000 daily totals from the
#    KPI cards. The cumulative line dips under target early, then overtakes
#    it mid-shift before settling just under plan by the end of the day.
# ---------------------------------------------------------------------------
rows = []
cum = 0
PLAN_TOTAL = 153000
ACTUAL_TOTAL = 152000
for hour in range(24):
    l1 = max(0, int(rng.gauss(16, 4)))
    l2 = max(0, int(rng.gauss(11, 4)))
    l3 = max(0, int(rng.gauss(17, 4)))
    l4 = max(0, int(rng.gauss(9, 4)))

    frac = (hour + 1) / 24
    # Slight S-curve so the pace looks like a real shift ramp-up rather than
    # a perfectly straight line.
    pace = 0.5 - 0.5 * math.cos(math.pi * frac)
    target = round(PLAN_TOTAL * frac)
    actual_pace = pace + 0.05 * math.sin(frac * math.pi * 2.2)
    cum = round(ACTUAL_TOTAL * min(1.0, max(0.0, actual_pace)))
    rows.append([hour, l1, l2, l3, l4, cum, target])
rows[-1][5] = ACTUAL_TOTAL
rows[-1][6] = PLAN_TOTAL
write_csv("production_progress.csv", ["hour", "line1", "line2", "line3", "line4", "cumulative_actual", "target"], rows)

# ---------------------------------------------------------------------------
# 4) equipment_gauges.csv - single-equipment overview gauges (設備 screen)
# ---------------------------------------------------------------------------
write_csv(
    "equipment_gauges.csv",
    ["metric_key", "metric_label", "value", "min", "max", "unit"],
    [
        ["rotation_speed", "回転速度", 77.9, 0, 150, "RPM"],
        ["flow_rate", "流量", 28, 0, 100, "L/min"],
    ],
)

write_csv(
    "equipment_status.csv",
    ["key", "value"],
    [
        ["equipment_name", "組立ライン 溶接ユニット #3"],
        ["device_state", "正常"],
        ["error_code", "なし"],
        ["today_count", 1443],
        ["month_count", 3767],
    ],
)

# ---------------------------------------------------------------------------
# 5) equipment_status_timeline.csv - today's run/stop status per device (gantt)
# ---------------------------------------------------------------------------
STATES = ["稼働", "段取り替え", "メンテナンス", "設備停止", "その他"]
WEIGHTS = [0.62, 0.14, 0.10, 0.09, 0.05]
timeline_rows = []
for device in ["装置A", "装置B", "装置C", "装置D"]:
    t = 8 * 60  # start 08:00
    end = 20 * 60
    while t < end:
        state = rng.choices(STATES, weights=WEIGHTS, k=1)[0]
        dur = rng.choice([15, 20, 25, 30, 45, 60]) if state == "稼働" else rng.choice([10, 15, 20])
        dur = min(dur, end - t)
        sh, sm = divmod(t, 60)
        eh, em = divmod(t + dur, 60)
        timeline_rows.append([device, f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}", state])
        t += dur
write_csv("equipment_status_timeline.csv", ["device", "start", "end", "state"], timeline_rows)

# ---------------------------------------------------------------------------
# 6) stop_reason_breakdown.csv - pie chart
# ---------------------------------------------------------------------------
write_csv(
    "stop_reason_breakdown.csv",
    ["reason", "percent"],
    [
        ["段取り替え", 43.1],
        ["メンテナンス", 29.6],
        ["設備停止", 16.2],
        ["材料不足", 7.9],
        ["治具不良", 3.2],
    ],
)

# ---------------------------------------------------------------------------
# 7) uptime_downtime_monthly.csv - stacked bar Jan..Dec
# ---------------------------------------------------------------------------
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
rows = []
for i, m in enumerate(months):
    scale = 1.0 if i < 9 else 0.32
    running = max(4, int(rng.gauss(78, 10) * scale))
    changeover = max(1, int(rng.gauss(14, 3) * scale))
    maint = max(1, int(rng.gauss(10, 3) * scale))
    stop = max(1, int(rng.gauss(9, 3) * scale))
    other = max(1, int(rng.gauss(5, 2) * scale))
    rows.append([m, running, changeover, maint, stop, other])
write_csv("uptime_downtime_monthly.csv", ["month", "稼働", "段取り替え", "メンテナンス", "設備停止", "その他"], rows)

# ---------------------------------------------------------------------------
# 8) stop_reason_pareto.csv - pareto bar + cumulative % line
# ---------------------------------------------------------------------------
write_csv(
    "stop_reason_pareto.csv",
    ["reason", "minutes", "cum_pct"],
    [
        ["段取り替え", 42, 42],
        ["メンテナンス", 28, 70],
        ["設備停止", 15, 85],
        ["材料不足", 8, 93],
        ["治具不良", 3, 100],
    ],
)

# ---------------------------------------------------------------------------
# 9) bolt_torque_readings.csv - two time series (torque / angle) per bolt joint
# ---------------------------------------------------------------------------
rows = []
t0_min = 14 * 60 + 13
n_points = 19
b1_torque, b2_torque = 45.0, 44.5
b1_angle, b2_angle = 34.0, 7.0
for i in range(n_points):
    minute = t0_min + (i * 15) // 60
    sec = (i * 15) % 60
    hh, mm = divmod(minute, 60)
    ts = f"{hh:02d}:{mm:02d}:{sec:02d}"
    b1_torque += rng.uniform(-0.5, 0.5)
    b2_torque += rng.uniform(-0.5, 0.5)
    b1_angle += rng.uniform(-1.2, 1.2)
    b2_angle += rng.uniform(-0.8, 0.8)
    # Bolt 2 drifts out of tolerance in the last third -> the anomaly the AI flags.
    if i > n_points * 0.6:
        b2_torque += rng.uniform(0.4, 1.4)
    rows.append([
        ts,
        round(max(38, min(58, b1_torque)), 2),
        round(max(38, min(62, b2_torque)), 2),
        round(max(20, min(45, b1_angle)), 2),
        round(max(2, min(20, b2_angle)), 2),
    ])
write_csv("bolt_torque_readings.csv", ["time", "bolt1_torque_nm", "bolt2_torque_nm", "bolt1_angle_deg", "bolt2_angle_deg"], rows)

# ---------------------------------------------------------------------------
# 10) bolt_torque_prediction.csv - AI anomaly summary
# ---------------------------------------------------------------------------
write_csv(
    "bolt_torque_prediction.csv",
    ["key", "value"],
    [
        ["equipment_name", "ボルト締め付けユニット 1-1"],
        ["station_id", "BT-1100"],
        ["line", "元町工場 ライン1"],
        ["run_state", "Running"],
        ["prediction", "ANOMALY_DETECTED"],
        ["anomaly_score", 0.50],
        ["target_torque_nm", 45.0],
        ["tolerance_nm", 3.0],
        ["good_parts_5m", 6],
        ["total_parts_5m", 8],
    ],
)

write_csv(
    "bolt_torque_prediction_factors.csv",
    ["factor", "percent"],
    [
        ["ボルト2 締め付けトルク", 31],
        ["ボルト1 回転角度", 19],
        ["ボルト1 締め付けトルク", 24],
        ["ボルト2 回転角度", 26],
    ],
)

# ---------------------------------------------------------------------------
# 11) line_overview.csv / line_hourly_production.csv / inspection_defects.csv
#     - "ライン一覧" screen (per-line current count gauge + hourly bar chart)
# ---------------------------------------------------------------------------
write_csv(
    "line_overview.csv",
    ["line_key", "line_label", "current_count", "gauge_max"],
    [
        ["prod001", "PROD001 生産数", 59, 300],
        ["prod002", "PROD002 生産数", 138, 300],
        ["prod003", "PROD003 生産数", 152, 300],
    ],
)

# Night shift near-idle, day shift (08:00-16:00) is the main production block,
# with one extra tall bar right at the end of the window - matches the
# reference dashboard's hourly shape.
DAY_SHAPE = [0.06, 0.02, 0, 0, 0, 0, 0, 0.08, 0.55, 0.9, 0.95, 0.85, 0.8, 0.9, 0.97, 0.35, 0.55, 1.0]
HOURS = ["20:00", "21:00", "22:00", "23:00", "00:00", "01:00", "02:00", "03:00",
         "04:00", "05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00"]
LINE_PEAKS = {"prod001": 100, "prod002": 250, "prod003": 300}
rows = []
for i, hour in enumerate(HOURS):
    row = [hour]
    for line_key, peak in LINE_PEAKS.items():
        base = DAY_SHAPE[i] * peak
        noise = rng.uniform(-0.04, 0.04) * peak
        row.append(max(0, round(base + noise)))
    rows.append(row)
write_csv("line_hourly_production.csv", ["time", "prod001", "prod002", "prod003"], rows)

write_csv(
    "inspection_defects.csv",
    ["key", "value"],
    [["label", "検査不良数"], ["value", 4], ["max", 20]],
)

# ---------------------------------------------------------------------------
# 12) anomaly_detection_series.csv / anomaly_summary.csv - "機械学習" screen,
#     top half (現在の状態 / 異常・正常の割合 / 異常検知結果)
# ---------------------------------------------------------------------------
GET_PEAKS = [10.5, 13.5, 9.0, 11.0, 10.5, 9.5, 8.0, 10.0, 19.0, 15.0, 11.5, 13.5, 11.5, 9.5]
SCORE_PEAKS = [1.5, 2.0, 1.2, 1.8, 1.6, 1.3, 1.0, 1.5, 9.5, 6.0, 1.8, 2.2, 1.7, 1.3]
THRESHOLD = 8.0
rows = []
anomalous = 0
total = 0
STEPS_PER_DAY = 24
for day in range(14):
    date_label = f"5/{day + 1}"
    for step in range(STEPS_PER_DAY):
        frac = step / STEPS_PER_DAY
        # Smooth single-hump-per-day shape (raised-cosine), floor near the
        # day boundaries, with a touch of high-frequency jitter on top so
        # it reads as a real sensor trace rather than a clean sine wave.
        hump = (0.5 - 0.5 * math.cos(2 * math.pi * frac)) ** 1.6
        jitter = math.sin(frac * 37 + day) * 0.06 + rng.uniform(-0.05, 0.05)
        get_val = 1.0 + GET_PEAKS[day] * hump * (1 + jitter)
        score_val = 0.3 + SCORE_PEAKS[day] * hump * (1 + jitter)
        get_val = max(0.2, get_val)
        score_val = max(0.1, score_val)
        hh = int(step * 24 / STEPS_PER_DAY)
        mm = int((step * 24 / STEPS_PER_DAY - hh) * 60)
        ts = f"{date_label} {hh:02d}:{mm:02d}"
        rows.append([ts, date_label, round(get_val, 2), round(score_val, 2)])
        total += 1
        if score_val >= THRESHOLD:
            anomalous += 1
write_csv("anomaly_detection_series.csv", ["timestamp", "date_label", "get_value", "anomaly_score"], rows)

anomaly_pct = round(100 * anomalous / total, 2)
write_csv(
    "anomaly_summary.csv",
    ["key", "value"],
    [
        ["state", "正常"],
        ["anomaly_pct", anomaly_pct],
        ["normal_pct", round(100 - anomaly_pct, 2)],
        ["threshold", THRESHOLD],
    ],
)

# ---------------------------------------------------------------------------
# 13) model_training_history.csv / model_parameter_trend.csv - "機械学習"
#     screen, bottom half (モデル学習履歴 / パラメータの推移)
# ---------------------------------------------------------------------------
mean_by_date = {
    "5/5": 8.72, "5/6": 8.65, "5/7": 8.55, "5/8": 8.48, "5/9": 8.62,
    "5/10": 9.06, "5/11": 9.50, "5/12": 9.66, "5/13": 9.91, "5/14": 10.18,
}
variance_by_date = {
    "5/5": 12.30, "5/6": 11.85, "5/7": 11.20, "5/8": 10.95, "5/9": 10.80,
    "5/10": 13.45, "5/11": 14.48, "5/12": 13.64, "5/13": 14.22, "5/14": 14.07,
}
rows = []
for date in sorted(mean_by_date, key=lambda d: -int(d.split("/")[1])):
    created = f"2021-05-{int(date.split('/')[1]):02d} 00:00:20"
    rows.append([created, "hotelling", f"{mean_by_date[date]:.2f}", f"{variance_by_date[date]:.2f}"])
write_csv("model_training_history.csv", ["created_at", "algorithm", "param_mean", "param_variance"], rows)

trend_dates = ["5/2", "5/3", "5/4", "5/5", "5/6", "5/7", "5/8", "5/9", "5/10", "5/11", "5/12", "5/13", "5/14"]
trend_mean = [8.82, 8.78, 8.75, 8.72, 8.65, 8.55, 8.48, 8.62, 9.06, 9.50, 9.66, 9.91, 10.18]
trend_variance = [15.80, 15.10, 14.30, 12.30, 11.85, 11.20, 10.95, 10.80, 13.45, 14.48, 13.64, 14.22, 14.07]
write_csv(
    "model_parameter_trend.csv",
    ["date", "mean", "variance"],
    [[d, m, v] for d, m, v in zip(trend_dates, trend_mean, trend_variance)],
)

# ---------------------------------------------------------------------------
# 14) 品質 > 品質状況 (Quality CCR dashboard, 高岡電池工場 LINE #1)
# ---------------------------------------------------------------------------
write_csv(
    "quality_ccr_meta.csv",
    ["key", "value"],
    [
        ["factory_name", "高岡電池工場"],
        ["line_name", "LINE #1"],
        ["report_date", "2025/05/28"],
        ["shift", "白直"],
        ["setting_change", "ON"],
    ],
)

write_csv(
    "quality_ccr_kpis.csv",
    ["key", "label", "value", "unit", "day_delta", "week_delta", "tier"],
    [
        ["w_yield", "W 直行率", "98.1", "%", "+0.2", "+0.3", "good"],
        ["t_yield", "T 直行率", "99.8", "%", "+0.1", "+0.2", "good"],
        ["k_yield", "K 直行率", "94.3", "%", "-0.6", "-1.2", "critical"],
        ["downstream_leak", "後工程流出数", "5", "件", "-2", "-3", "neutral"],
    ],
)
write_csv(
    "quality_ccr_rework_rate.csv",
    ["key", "value"],
    [
        ["label", "台当たり手直し件数"],
        ["value", "1.88"],
        ["rework_total", "1,193"],
        ["production_total", "63,486"],
    ],
)

write_csv(
    "quality_worst_rework.csv",
    ["rank", "process", "count", "day_delta", "flag"],
    [
        [1, "XX塗布工程", 23, "+4", "critical"],
        [2, "●●巻付け工程", 21, "+1", "critical"],
        [3, "XX組立工程", 14, "-2", "none"],
    ],
)
write_csv(
    "quality_worst_calls.csv",
    ["rank", "process", "count", "day_delta", "flag"],
    [
        [1, "XX巻付け工程", 23, "+1", "critical"],
        [2, "▲▲巻付け工程", 18, "+3", "warn"],
        [3, "■■巻付け工程", 10, "-2", "none"],
    ],
)

write_csv(
    "quality_rework_trend.csv",
    ["date", "red", "yellow", "blue"],
    [
        ["5/24", 26, 18, 11],
        ["5/25", 24, 18, 12],
        ["5/26", 25, 19, 13],
        ["5/27", 19, 20, 16],
        ["5/28(本日)", 23, 21, 14],
    ],
)

write_csv(
    "quality_ai_suggestions.csv",
    ["color", "text"],
    [
        ["red", "●●巻付け工程で5/27以降急激な悪化を確認。段取り変更・材料ロット・設備設定変更履歴の確認を推奨します。"],
        ["yellow", "XX塗布工程の手直し件数が増加して高止まりしています。塗布条件の再確認と治具保全の実施を推奨します。"],
        ["blue", "後工程流出数が前日比で増加しています。人工直での受入チェック基準の見直しと、W工程の限界管理の強化を推奨します。"],
    ],
)


# ---------------------------------------------------------------------------
# 15) 設備監視 > ナットランナーPU-01 (equipment anomaly-detail screen, AI chat)
# ---------------------------------------------------------------------------
write_csv(
    "nutrunner_meta.csv",
    ["key", "value"],
    [
        ["equipment_name", "ナットランナー PU-01"],
        ["tag", "重要設備"],
        ["area_line", "エリア / 製造ライン1"],
        ["report_datetime", "2025/05/19 10:30:00"],
        ["auto_refresh", "ON"],
        ["alert_badge", "1"],
        ["alert_count", "3"],
        ["user_role", "管理者"],
    ],
)

write_csv(
    "nutrunner_alert_info.csv",
    ["key", "value"],
    [
        ["latest_alert_level", "高異常"],
        ["latest_alert_time", "2025/05/19 09:55"],
        ["alert_verdict", "異常（AI）"],
        ["detection_streak", "3日"],
        ["model_name", "Autoencoder v2.1"],
        ["training_period", "2025/01/01〜2025/04/30"],
    ],
)

write_csv(
    "nutrunner_structure.csv",
    ["stage", "state"],
    [
        ["モーター", "normal"],
        ["ギアボックス", "normal"],
        ["トルクセンサー", "critical"],
        ["ソケット", "normal"],
    ],
)

# 24h @ 30min resolution, 05/18 10:30 -> 05/19 10:30 (49 points)
N = 49
STEP_MIN = 30
BASE_DATE = ["05/18"] * 28 + ["05/19"] * 21  # date rolls over at step 28 (00:00)
nr_labels = []
for i in range(N):
    total_min = i * STEP_MIN
    day = "05/18" if total_min < 28 * 30 else "05/19"
    hh = (10 + total_min // 60) % 24
    mm = (30 + total_min) % 60
    nr_labels.append(f"{day} {hh:02d}:{mm:02d}")

nr_score, nr_torque, nr_rot, nr_current, nr_temp = [], [], [], [], []
for i in range(N):
    frac = i / (N - 1)
    accelerate = max(0, frac - 0.78) / 0.22  # sharper rise after ~05/19 06:30
    score = 20 + 45 * frac + 25 * (accelerate ** 1.3) + rng.uniform(-3, 3)
    nr_score.append(round(max(5, min(100, score)), 1))
    nr_torque.append(round(38 + 34 * frac + 18 * (accelerate ** 1.2) + rng.uniform(-4, 4), 1))
    nr_rot.append(round(55 + 6 * math.sin(frac * 9) + rng.uniform(-3, 3), 1))
    nr_current.append(round(30 + 16 * frac + rng.uniform(-3, 3), 1))
    nr_temp.append(round(64 + 8 * math.sin(frac * 6 + 1) + rng.uniform(-3, 3), 1))
nr_score[-1] = 85.0  # pin the current reading to match the reference screen exactly
write_csv(
    "nutrunner_sensors.csv",
    ["time", "anomaly_score", "torque", "rotation", "motor_current", "temperature"],
    [[nr_labels[i], nr_score[i], nr_torque[i], nr_rot[i], nr_current[i], nr_temp[i]] for i in range(N)],
)
write_csv("nutrunner_alert_marker.csv", ["key", "value"], [["index", 47], ["label", "アラート発生 09:55"]])

# Mini top-left score trend (same window, coarser)
write_csv(
    "nutrunner_score_mini.csv",
    ["time", "value"],
    [[nr_labels[i], nr_score[i]] for i in range(0, N, 3)],
)

# 7-day trend embedded in the AI chat bubble
week_dates = ["05/13", "05/14", "05/15", "05/16", "05/17", "05/18", "05/19"]
week_scores = [24, 27, 30, 34, 41, 55, 78]
write_csv("nutrunner_score_7day.csv", ["date", "value"], [[d, v] for d, v in zip(week_dates, week_scores)])

# Reconstruction error (Autoencoder output)
recon = []
for i in range(N):
    frac = i / (N - 1)
    v = 0.22 + 0.08 * math.sin(frac * 14) + rng.uniform(-0.05, 0.05)
    if 10 <= i <= 13:
        v += (0.75 if i in (11, 12) else 0.35)  # one sharp spike near 05/18 22:30-00:30
    v += 0.12 * max(0, frac - 0.75)  # gentle upward drift near the end
    recon.append(round(max(0.02, v), 3))
write_csv("nutrunner_reconstruction.csv", ["time", "value"], [[nr_labels[i], recon[i]] for i in range(N)])
write_csv("nutrunner_reconstruction_threshold.csv", ["key", "value"], [["threshold", 0.35]])

# Score distribution (past 7 days), bucketed 0-100 in steps of 5, roughly bell
# shaped around 40-45 with a long right tail out to the current value of 85.
buckets = list(range(0, 100, 5))
peak = 42
dist = []
for b in buckets:
    d = abs(b - peak) / 11.0
    freq = round(32 * math.exp(-d * d) + rng.uniform(-1.5, 1.5))
    dist.append(max(0, freq))
dist[buckets.index(85)] = max(dist[buckets.index(85)], 2)
write_csv("nutrunner_distribution.csv", ["bucket", "frequency"], [[b, f] for b, f in zip(buckets, dist)])
write_csv("nutrunner_distribution_marker.csv", ["key", "value"], [["value", 85], ["label", "現在値 85"]])

write_csv(
    "nutrunner_ai_chat.csv",
    ["sender", "time", "kind", "text"],
    [
        ["user", "10:28", "text", "この装置の異常のトレンドを教えてください。"],
        ["ai", "10:28", "text",
         "過去7日間の異常スコアは徐々に上昇傾向にあり、特に05/19 6:30以降にスコアが上昇しています。"
         "これは締め付けトルクのばらつき増加と、ソケット摩耗の進行を原因と考えられます。"],
        ["ai", "10:28", "chart", "過去7日間の異常スコア推移"],
        ["user", "10:29", "text", "なぜ異常スコアが高いのかを詳しく分析してください。"],
        ["ai", "10:29", "text",
         "異常スコアが高い主な要因は以下の通りです：\n"
         "・締め付けトルクのばらつき増加\n"
         "　05/16以降、目標トルクに対する誤差が徐々に拡大しており、ソケット摩耗や軸ずれの可能性があります。\n"
         "・モーター電流の増加\n"
         "　負荷の上昇や抵抗の増加が影響し、電流値が上昇しています。\n"
         "・再構成誤差の増加\n"
         "　Autoencoderモデルがパターンから大きく乖離しており、異常と判定されるデータが多くなっています。\n"
         "これらの要因を総合的に判断し、異常スコアが高くなっています。"],
    ],
)


# ---------------------------------------------------------------------------
# 16) 異常兆候 > 異常兆候検知 (facility-wide anomaly dashboard, floor map,
#     alert table, trend cards, AI assistant)
# ---------------------------------------------------------------------------
write_csv(
    "anomaly_dashboard_meta.csv",
    ["key", "value"],
    [
        ["title", "異常兆候検知ダッシュボード"],
        ["report_datetime", "2025/06/19 10:30:00"],
        ["auto_refresh", "On"],
        ["alert_badge", "3"],
    ],
)

write_csv(
    "anomaly_dashboard_summary.csv",
    ["tier", "label", "count", "link_label"],
    [
        ["critical", "異常の高確度あり", 3, "即時要注意"],
        ["warning", "注意（監視強化）", 7, "詳細を表示"],
        ["normal", "正常", 18, "詳細を表示"],
        ["offline", "停止中", 2, "詳細を表示"],
    ],
)

write_csv(
    "anomaly_dashboard_map.csv",
    ["area", "area_label", "eq_id", "icon", "state"],
    [
        ["A", "エリアA：組立ライン", "A-01", "robot", "warning"],
        ["A", "エリアA：組立ライン", "A-02", "robot", "critical"],
        ["A", "エリアA：組立ライン", "A-03", "machine", "normal"],
        ["A", "エリアA：組立ライン", "A-04", "scanner", "offline"],
        ["B", "エリアB：加工ライン", "B-01", "gear", "critical"],
        ["B", "エリアB：加工ライン", "B-02", "conveyor", "normal"],
        ["B", "エリアB：加工ライン", "B-03", "gear", "critical"],
        ["B", "エリアB：加工ライン", "B-04", "robot", "warning"],
        ["B", "エリアB：加工ライン", "B-05", "conveyor", "normal"],
        ["C", "エリアC：検査・梱包ライン", "C-01", "gear", "normal"],
        ["C", "エリアC：検査・梱包ライン", "C-02", "robot", "warning"],
        ["C", "エリアC：検査・梱包ライン", "C-03", "box", "normal"],
        ["C", "エリアC：検査・梱包ライン", "C-04", "box", "normal"],
        ["C", "エリアC：検査・梱包ライン", "C-05", "scanner", "normal"],
    ],
)

write_csv(
    "anomaly_dashboard_alerts.csv",
    ["time", "eq_id", "eq_name", "level", "content"],
    [
        ["10:25", "A-02", "組立ロボット2号機", "重大", "モーター温度異常上昇"],
        ["10:18", "B-01", "NC旋盤1号機", "重大", "主軸振動の異常検知"],
        ["10:12", "A-01", "組立ロボット1号機", "警告", "過負荷閾値超過の注意喚起"],
        ["09:38", "B-02", "マシニングセンタ1号機", "警告", "工具摩耗の可能性"],
        ["09:45", "C-02", "検査装置2号機", "注意", "センサー検出値変動"],
    ],
)

write_csv(
    "anomaly_dashboard_trend.csv",
    ["eq_id", "eq_name", "risk", "score"],
    [
        ["A-02", "組立ロボット2号機", "高リスク", 87],
        ["B-03", "NC旋盤3号機", "高リスク", 78],
        ["A-01", "組立ロボット1号機", "中リスク", 62],
        ["C-02", "検査装置2号機", "低リスク", 34],
    ],
)

TREND_PEAKS = {"A-02": 87, "B-03": 78, "A-01": 62, "C-02": 34}
TREND_START = {"A-02": 30, "B-03": 28, "A-01": 38, "C-02": 30}
trend_rows = []
for eq_id, peak in TREND_PEAKS.items():
    start = TREND_START[eq_id]
    for i in range(N):  # reuse the 49-point 06/18 10:30 -> 06/19 10:30 window shape
        frac = i / (N - 1)
        v = start + (peak - start) * (frac ** 1.4) + rng.uniform(-4, 4)
        trend_rows.append([eq_id, nr_labels[i].replace("05/18", "06/18").replace("05/19", "06/19"), round(max(2, v), 1)])
trend_rows_last = {}
for row in trend_rows:
    trend_rows_last[row[0]] = row
for eq_id, peak in TREND_PEAKS.items():
    trend_rows_last[eq_id][2] = float(peak)  # pin the final point to the headline score
write_csv("anomaly_dashboard_trend_series.csv", ["eq_id", "time", "value"], trend_rows)

write_csv(
    "anomaly_dashboard_top_alerts.csv",
    ["rank", "eq_id", "eq_name", "score", "trend"],
    [
        [1, "A-02", "組立ロボット2号機", 87, "上昇傾向"],
        [2, "B-01", "NC旋盤1号機", 78, "上昇傾向"],
        [3, "A-01", "組立ロボット1号機", 62, "上昇傾向"],
    ],
)
write_csv(
    "anomaly_dashboard_ai_details.csv",
    ["eq_id", "text"],
    [
        ["A-02", "モーター温度が基準値を超過しており、スコアが上昇しています。"],
        ["B-01", "主軸振動の異常が継続しており、故障リスクが高まっています。"],
        ["A-01", "過負荷閾値超過が継続中のため注意が必要です。"],
    ],
)
write_csv(
    "anomaly_dashboard_ai_actions.csv",
    ["eq_id", "text"],
    [
        ["A-02", "モーターおよび電源系統の点検を実施"],
        ["B-01", "主軸の軸心と振動原因の特定を実施"],
        ["A-01", "運用負荷の軽減または休止を検討"],
    ],
)
write_csv(
    "anomaly_dashboard_ai_predictions.csv",
    ["eq_id", "eq_name", "probability"],
    [
        ["A-02", "組立ロボット2号機", 85],
        ["B-01", "NC旋盤1号機", 72],
        ["A-01", "組立ロボット1号機", 65],
    ],
)
write_csv(
    "anomaly_dashboard_quick_actions.csv",
    ["label"],
    [["主要設備のリスクランキング"], ["エリア別の傾向分析"], ["特定の設備を詳しく分析（例：B-01について）"]],
)


# ---------------------------------------------------------------------------
# 17) 設定 > オートエンコーダー設定 (Autoencoder model configuration screen)
# ---------------------------------------------------------------------------
write_csv(
    "autoencoder_meta.csv",
    ["key", "value"],
    [
        ["breadcrumb", "設備一覧 › ポンプユニット PU-01 › モデル設定（Autoencoder）"],
        ["title", "Autoencoder モデル設定"],
        ["subtitle", "ポンプユニット PU-01"],
        ["report_datetime", "2025/05/19 10:30:00"],
        ["auto_refresh", "ON"],
        ["alert_badge", "2"],
    ],
)

write_csv(
    "autoencoder_tabs.csv",
    ["label", "active"],
    [
        ["モデル構成・学習", "1"],
        ["データ設定", ""],
        ["しきい値設定", ""],
        ["学習・評価履歴", ""],
    ],
)

# section / label / value / kind (text|select|toggle) / options (pipe separated)
write_csv(
    "autoencoder_fields.csv",
    ["section", "label", "value", "kind", "options"],
    [
        ["model", "入力次元数", "24", "text", ""],
        ["model", "潜在層の次元数（ボトルネック）", "8", "text", ""],
        ["model", "エンコーダ層構成", "64, 32", "text", ""],
        ["model", "デコーダ層構成", "32, 64", "text", ""],
        ["model", "活性化関数", "ReLU", "select", "ReLU|LeakyReLU|Tanh|Sigmoid|ELU"],
        ["model", "出力層の活性化関数", "Linear", "select", "Linear|Sigmoid|Tanh"],
        ["model", "正規化", "Batch Normalization", "select", "Batch Normalization|Layer Normalization|なし"],
        ["model", "正則化設定（ドロップアウトなど）", "", "select", "|Dropout 0.1|Dropout 0.2|L2 正則化"],
        ["training", "学習アルゴリズム", "Adam", "select", "Adam|SGD|RMSprop|AdamW"],
        ["training", "学習率 (Learning Rate)", "0.001", "text", ""],
        ["training", "バッチサイズ", "64", "text", ""],
        ["training", "エポック数", "100", "text", ""],
        ["training", "損失関数", "MSE（平均二乗誤差）", "select", "MSE（平均二乗誤差）|MAE（平均絶対誤差）|Huber"],
        ["training", "早期終了 (Early Stopping)", "ON", "toggle", ""],
        ["training", "パティエンス", "10", "text", ""],
        ["training", "検証データの分割比率", "0.2", "text", ""],
        ["training", "ランダムシード", "42", "text", ""],
        ["score", "スコア計算方法", "再構成誤差（MSE）", "select", "再構成誤差（MSE）|再構成誤差（MAE）|マハラノビス距離"],
        ["score", "スコアの統計方法", "平均", "select", "平均|最大|中央値|パーセンタイル"],
    ],
)

write_csv(
    "autoencoder_summary.csv",
    ["label", "value"],
    [
        ["モデル", "Autoencoder v2.1"],
        ["入力次元", "24"],
        ["潜在次元", "8"],
        ["学習率", "0.001（Adam）"],
        ["エポック数", "100"],
        ["バッチサイズ", "64"],
        ["損失関数", "MSE"],
        ["スコア計算", "再構成誤差（MSE）平均"],
    ],
)

# Neural-network diagram: one row per layer (node count + colour role)
write_csv(
    "autoencoder_network.csv",
    ["layer", "label", "nodes", "role"],
    [
        ["1", "入力層", 6, "plain"],
        ["2", "エンコーダ", 5, "encoder"],
        ["3", "", 3, "bottleneck"],
        ["4", "デコーダ", 5, "decoder"],
        ["5", "出力層", 6, "plain"],
    ],
)

write_csv(
    "autoencoder_ai_chat.csv",
    ["sender", "time", "text"],
    [
        ["ai", "10:30", "こんにちは！Autoencoderのハイパーパラメータについてご案内します。以下のデータを参考にご活用ください。"],
        ["user", "10:31", "現在の設定で問題はどのように改善できますか？"],
        ["ai", "10:31",
         "現在の設定は（潜在次元数: 8）は適切だと思いますが、さらなる改善のポイントをご提案します。\n"
         "・一般的に次元数は入力の1/2〜1/10が目安です\n"
         "・小さすぎると重要な情報が失われやすく、大きすぎると過学習になりやすいです\n"
         "・エポック数と早期終了を組み合わせて調整してください\n"
         "\n損失関数について\n"
         "・入力次元のスケールが異なる場合は正規化を活用すると効果的です\n"
         "・MSEは一般的で安定していますが、外れ値が多い場合は MAE も検討ください"],
        ["user", "10:32", "学習率はどうでしょうか？"],
        ["ai", "10:32",
         "Adamの場合、一般的には 0.001 がよく使われます。\n"
         "・学習が不安定な場合 → 小さくする（例: 0.0005）\n"
         "・学習が遅い場合 → 大きくする（例: 0.002）\n"
         "\n範囲 0.0001〜0.01 を目安に調整してください。"],
    ],
)


# ---------------------------------------------------------------------------
# 18) 保全 > 保全情報 (CCR maintenance-info screen reproducing the
#     高岡電池工場 CCRダッシュボード「保全情報」reference image 1:1, plus the
#     toggleable live AI chat panel)
# ---------------------------------------------------------------------------
write_csv("maintenance_meta.csv", ["key", "value"], [
    ["factory_name", "高岡電池工場"], ["title", "CCRダッシュボード"], ["subtitle", "保全情報"],
    ["line_name", "LINE #1"], ["report_date", "2026/05/28"], ["shift", "白直"],
    ["auto_refresh_label", "自動更新"], ["auto_refresh", "ON"],
])
write_csv("maintenance_kpis.csv", ["key", "label", "value", "unit", "day_delta", "week_delta", "tier"], [
    ["w_rate", "W 稼働率", "98.1", "%", "+0.2", "+0.3", "good"],
    ["t_rate", "T 稼働率", "99.8", "%", "+0.1", "+0.2", "good"],
    ["k_rate", "K 稼働率", "94.3", "%", "-0.6", "-1.2", "critical"],
    ["line_stop", "ライン停止時間", "5", "M", "-2", "-3", "neutral"],
])
write_csv("maintenance_rate.csv", ["key", "value"], [
    ["label", "台当り異常件数"], ["value", "1.88"], ["unit", "%"],
    ["rework_label", "手直し総数"], ["rework_total", "1,193"], ["rework_unit", "件"],
    ["production_label", "生産台数"], ["production_total", "63,486"], ["production_unit", "台"],
])
write_csv("maintenance_worst_anomaly.csv", ["rank", "process", "count", "day_delta", "flag"], [
    [1, "XX 巻付け工程", 23, "+1", "critical"],
    [2, "●● 巻付け工程", 21, "+1", "critical"],
    [3, "XX 組立工程", 14, "-2", "none"],
])
write_csv("maintenance_worst_stoptime.csv", ["rank", "process", "hours", "day_delta", "flag"], [
    [1, "XX 巻付け工程", 23, "+1", "critical"],
    [2, "▲▲ 巻付け工程", 15, "+3", "warn"],
    [3, "●● 巻付け工程", 10, "-2", "none"],
])
write_csv("maintenance_status_summary.csv", ["tier", "label", "count", "link_label"], [
    ["critical", "異常の兆候あり", 3, "詳細を見る"],
    ["warning", "注意（監視強化）", 7, "詳細を見る"],
    ["normal", "正常", 18, "詳細を見る"],
    ["offline", "停止中", 2, "詳細を見る"],
])
write_csv("maintenance_trend.csv", ["date", "total", "red", "yellow", "blue"], [
    ["5/24", 112, 25, 21, 14], ["5/25", 118, 25, 21, 14], ["5/26", 123, 25, 21, 15],
    ["5/27", 136, 24, 21, 14], ["5/28 (本日)", 142, 23, 21, 14],
])
write_csv("maintenance_trend_legend.csv", ["key", "label"], [
    ["total", "合計件数"], ["red", "XX 巻付け工程"], ["yellow", "●● 巻付け工程"], ["blue", "XX 組立工程"],
])
write_csv("maintenance_score_cards.csv", ["eq_id", "eq_name", "risk", "badge", "score"], [
    ["A-02", "巻取コート設備", "high", "異常スコア", 87],
    ["B-03", "化成設備", "high", "異常スコア", 78],
    ["A-01", "巻取ラミネート設備", "mid", "警戒スコア", 62],
    ["C-02", "組立検査設備", "low", "正常スコア", 34],
])
# 5-day, 2-hourly anomaly-score history per equipment (60 points), shaped so
# each card's sparkline reads like the reference: two rising/jagged "high"
# lines, one oscillating "mid" line, one flat noisy "low" line.
MAINT_PTS = 60
maint_score_rows = []
maint_shapes = {
    "A-02": (30.0, 87.0, 1.6, 9.0),
    "B-03": (38.0, 78.0, 1.2, 12.0),
    "A-01": (58.0, 62.0, 1.0, 11.0),
    "C-02": (32.0, 34.0, 1.0, 5.0),
}
for eq_id, (start, end, curve, noise) in maint_shapes.items():
    v = start
    for i in range(MAINT_PTS):
        frac = i / (MAINT_PTS - 1)
        target = start + (end - start) * (frac ** curve)
        # random walk pulled back toward the trend line (jagged, not smooth)
        v = v + (target - v) * 0.55 + rng.uniform(-noise, noise)
        v = min(98.0, max(3.0, v))
        day = 24 + (i * 2) // 24
        hour = (i * 2) % 24
        if i == MAINT_PTS - 1:
            v = end
        maint_score_rows.append([eq_id, f"05/{day:02d} {hour:02d}:00", round(v, 1)])
write_csv("maintenance_score_series.csv", ["eq_id", "time", "value"], maint_score_rows)
write_csv("maintenance_ai_tips.csv", ["color", "equipment", "occurred", "serial_no", "health_score", "comment"], [
    ["red", "XX 巻布工程設備", "5/27", "6", "E", "軸交換が必要です。"],
    ["yellow", "●● 巻付け工程設備", "5/27", "3", "D", "継続的な悪化傾向あり、要確認。"],
    ["blue", "XX 組付工程設備", "5/28", "2", "C", "予兆の兆候あり。"],
])
write_csv("maintenance_ai_chat.csv", ["sender", "time", "text"], [
    ["ai", "10:30", "こんにちは！保全情報についてご案内します。設備の異常兆候や停止時間について、気になる点があればお尋ねください。"],
    ["user", "10:31", "今もっとも優先して対応すべき設備はどれですか？"],
    ["ai", "10:31", "現在、XX 巻付け工程の異常件数と設備停止時間がともにワースト1位で、AI提案でもXX 巻布工程設備がHealthScore Eと最も深刻です。軸交換が必要な状態のため、最優先での対応を推奨します。次いで●● 巻付け工程設備（HealthScore D）も継続的な悪化傾向があるため、早めの確認をお勧めします。"],
])
# Mascot shown on 保全情報2 (こひにゃん): sits beside the AI toggle, clicking it
# opens the AI panel, and it doubles as the assistant's chat avatar.
write_csv("maintenance_mascot.csv", ["key", "value"], [
    ["name", "こひにゃん"],
    ["bubble", "ぼくこひにゃん！ぼくをクリックしたら、あなたのアシストをするよ！"],
    ["image", "/static/kohinyan.png"],
    ["avatar", "/static/kohinyan_avatar.png"],
])

# 保全情報2 専用: 主要設備の異常スコアトレンド。先頭カードはナットランナーPU-01 の
# １軸（source=pumpunit_axis1、起点は pumpunit_meta の mini_start）。grade は各カードの
# スコア横に表示する評価ランク。
# href = ページ遷移アイコンの飛び先（空なら従来のバッジ表示）
PU01_PAGE = "/monitoring/nut-runner-pu01-2"
write_csv("maintenance2_score_cards.csv", ["eq_id", "eq_name", "risk", "badge", "score", "grade", "source", "href"], [
    ["PU-01", "ナット締め付け設備", "high", "異常スコア", 85, "E", "pumpunit_axis1", PU01_PAGE],
    ["B-03", "化成設備", "high", "異常スコア", 78, "E", "", PU01_PAGE],
    ["A-01", "巻取ラミネート設備", "mid", "警戒スコア", 62, "D", "", PU01_PAGE],
    ["C-02", "組立検査設備", "low", "正常スコア", 34, "A", "", PU01_PAGE],
])
# 設備ステータスサマリーの「詳細を見る ›」を押したときに出る設備リスト（tier ごと）
write_csv("maintenance2_status_links.csv", ["tier", "label", "href"], [
    ["critical", "PU-01 ナット締め付け設備", PU01_PAGE],
    ["critical", "B-03 化成設備", ""],
    ["critical", "A-02 巻取コート設備", ""],
])

# ---------------------------------------------------------------------------
# 19) 生産状況 > 生産状況 (conveyor line-map production status screen,
#     reproducing the reference image 1:1 on a 1672×941 canvas; every
#     station / track / carry / indicator / KPI is data-driven from here)
# ---------------------------------------------------------------------------
write_csv("production_status_meta.csv", ["key", "value"], [
    ["current", "5"], ["target", "10"], ["target_relative", "50"],
    ["availability", "95"], ["planned_working_pct", "66"], ["planned_marker_pct", "50"],
    ["overtime_planned", "10"], ["overtime", "2,5"],
    ["errors", "2"], ["lack", "30"], ["failed", "5"],
    ["errors_bar_px", "6"], ["lack_bar_px", "97"], ["failed_bar_px", "45"],
    # every "Produced" counter starts at its CSV value and +1 every N seconds
    ["produced_interval_sec", "2"],
])
# x,y,w,h in canvas px; state green/red/grey; label_y/produced_y absolute;
# produced = initial counter value (blank = no "Produced" box; it then counts
# up by 1 every produced_interval_sec); car=1 draws the yellow vehicle tile.
write_csv("production_status_stations.csv", ["id", "label", "x", "y", "w", "h", "state", "label_y", "produced", "produced_y", "car"], [
    ["bs", "B/S", 95, 185, 65, 425, "green", 405, 152, 505, 0],
    ["mb_red", "M/B", 340, 345, 60, 430, "red", 535, 152, 635, 1],
    ["mb_green", "M/B", 668, 493, 58, 340, "green", 660, 152, 710, 0],
    ["ub", "U/B", 698, 312, 364, 60, "green", 324, 152, 342, 0],
    ["sim1", "S-IM-1", 908, 85, 210, 55, "green", 97, 152, 115, 0],
    ["sim2", "S-IM-2", 908, 150, 210, 55, "grey", 162, 152, 180, 0],
    ["sim1b", "", 1145, 85, 180, 55, "green", 0, "", 0, 0],
    ["sim2b", "", 1145, 150, 180, 55, "grey", 0, "", 0, 0],
    ["ff", "F/F", 1207, 320, 73, 160, "red", 348, 152, 430, 0],
    ["fb", "F/B", 1285, 435, 80, 78, "red", 462, "", 0, 0],
    ["ec", "E/C", 965, 512, 60, 123, "red", 537, 152, 605, 0],
    ["ec2", "E/C", 1027, 560, 79, 100, "red", 580, "", 0, 0],
    ["fsm", "F/SM", 1027, 660, 79, 40, "grey", 680, "", 0, 0],
    ["ur", "U/R", 883, 625, 60, 170, "red", 703, 152, 733, 0],
    ["ur2", "U/R", 957, 815, 90, 80, "grey", 835, "", 0, 0],
    ["cfrf", "C/F|R/F", 1083, 815, 90, 80, "red", 833, "", 0, 0],
    ["tall", "", 1262, 570, 56, 255, "green", 0, "", 0, 0],
])
# conveyor centre-lines (SVG path data) in FLOW order: each path starts where
# pallets enter it (the line starts top-left at B/S), so the stepped dash
# animation moves every pallet forward along the line
write_csv("production_status_tracks.csv", ["id", "d"], [
    ["left_loop", "M125,612 V650 A30,30 0 0 0 155,680 H205 A30,30 0 0 0 235,650 V237 A35,35 0 0 1 305,237 V340 A30,30 0 0 0 335,370 H352"],
    ["top_row", "M668,610 H535 A30,30 0 0 1 505,580 V150 A30,30 0 0 1 535,120 H908"],
    ["top_row2", "M640,120 A32.5,32.5 0 0 0 640,185 H908"],
    ["ub_left", "M668,610 H620 A30,30 0 0 1 590,580 V370 A30,30 0 0 1 620,340 H698"],
    ["ub_right", "M1062,340 H1207"],
    ["ub_down1", "M910,372 V625"],
    ["ub_down2", "M990,372 V512"],
    ["bottom_loop", "M370,775 V840 A30,30 0 0 0 400,870 H670 A30,30 0 0 0 700,840 V833"],
    # U/R (red) -> down, bend right, straight lane through U/R (grey) into C/F R/F
    ["ur_out", "M913,795 V825 A30,30 0 0 0 943,855 H1095"],
])
# carry labels: marker = badge (red circle count) | count (plain red number
# + small red square) | vehicle (yellow AGV) | bar (blue bar + white count)
write_csv("production_status_carries.csv", ["label", "x", "y", "marker", "count", "arrows_y", "arrow_dx"], [
    ["E/F Carry", 272, 143, "vehicle", "", 0, 0],
    ["S-MB-3Carry", 455, 297, "count", "2", 337, 22],
    ["S-IM-1 Carry", 760, 55, "badge", "0", 92, 19],
    ["S-MB-2Carry", 762, 205, "none", "", 240, 19],
    ["S-MB-1Carry", 640, 412, "badge", "0", 452, 19],
    ["S-MB-2Carry", 858, 448, "badge", "0", 486, 19],
    ["S-MB-2Carry", 1044, 448, "badge", "0", 486, 19],
    ["S-MB-3Carry", 492, 790, "badge", "0", 828, 19],
    ["E/F Carry", 1135, 275, "bar", "3", 0, 0],
])
# small status indicators: icon car | alert | m5 | m4, red count badge, optional text label
write_csv("production_status_indicators.csv", ["icon", "x", "y", "count", "count_style", "label", "label_x", "label_y"], [
    ["car", 30, 200, "0", "badge", "", 0, 0],
    ["alert", 30, 510, "0", "badge", "", 0, 0],
    ["m5", 22, 590, "0", "badge", "", 0, 0],
    ["car", 270, 380, "0", "badge", "", 0, 0],
    ["alert", 265, 640, "0", "badge", "", 0, 0],
    ["m4", 270, 745, "12", "count", "", 0, 0],
    ["car", 905, 55, "0", "badge", "", 0, 0],
    ["alert", 985, 55, "0", "badge", "", 0, 0],
    ["car", 1065, 55, "0", "badge", "", 0, 0],
    ["car", 905, 220, "0", "badge", "", 0, 0],
    ["alert", 985, 220, "0", "badge", "", 0, 0],
    ["car", 1065, 220, "0", "badge", "", 0, 0],
    ["car", 755, 287, "0", "badge", "", 0, 0],
    ["alert", 838, 287, "0", "badge", "", 0, 0],
    ["car", 985, 287, "0", "badge", "", 0, 0],
    ["car", 820, 385, "0", "badge", "", 0, 0],
    ["car", 1015, 385, "0", "badge", "", 0, 0],
    ["car", 740, 505, "0", "badge", "L/R", 748, 530],
    ["car", 590, 530, "0", "badge", "", 0, 0],
    ["car", 745, 605, "0", "badge", "B/R", 750, 636],
    ["car", 600, 640, "0", "badge", "", 0, 0],
    ["car", 745, 662, "0", "badge", "UP/R", 750, 691],
    ["alert", 595, 715, "0", "badge", "", 0, 0],
    ["car", 745, 810, "0", "badge", "IN/OUT", 750, 836],
    ["car", 600, 810, "0", "badge", "", 0, 0],
    ["alert", 870, 810, "0", "badge", "", 0, 0],
])
# thin connector lines (none: the U/R -> C/F link is a real conveyor lane now)
write_csv("production_status_lines.csv", ["x1", "y1", "x2", "y2"], [])
# ---------------------------------------------------------------------------
# 20) 設備監視 > ナットランナーPU-01（2）: Factory Guardian「設備詳細」画面
#     (ポンプユニット PU-01) を 1:1 で再現 — ラベル・系列・チャット文まで全部ここから
# ---------------------------------------------------------------------------
import math as _math
write_csv("pumpunit_meta.csv", ["key", "value"], [
    ["app_name", "Factory Guardian"], ["crumb1", "設備一覧"], ["crumb2", "設備詳細"],
    ["datetime", "2025/05/19  10:30:00"], ["auto_refresh", "自動更新 ON"], ["bell_count", "1"], ["user", "管理者"],
    ["equipment_name", "ナットランナーPU-01"], ["tag", "重要設備"], ["area_line", "エリアA / 製造ライン1"],
    ["active_tab", "概要"], ["period", "24時間"],
    ["structure_image", "/static/nutrunner_section.png"],
    ["mini_start", "05/19 00:00"],  # 左上グラフの起点（１軸系列をここから表示）
    ["history_link", "/history/t-mss"],  # 設備異常履歴の各行の外部リンクアイコンの飛び先（設備異常履歴 > T-MSS）
    ["score_note", "締め付け時間が増加傾向を示しています。\nまた、トルク時間勾配、締め付け角度にも\n関連する変化が示されています。"],  # 異常スコア欄のコメント
])
write_csv("pumpunit_nav.csv", ["label", "icon", "active", "badge"], [
    ["ダッシュボード", "home", 0, ""], ["設備監視", "monitor", 1, ""], ["アラート一覧", "bell", 0, "3"],
    ["設備一覧", "list", 0, ""], ["レポート", "report", 0, ""], ["設定", "gear", 0, ""],
])
write_csv("pumpunit_tabs.csv", ["label"], [["概要"], ["時系列分析"], ["閾値分析"], ["履歴"]])
write_csv("pumpunit_alert_info.csv", ["key", "value"], [
    ["latest_alert_level", "高異常"], ["latest_alert_time", "2025/05/19 09:55"], ["alert_verdict", "異常（AI）"],
    ["detection_streak", "3日"], ["model_name", "Autoencoder v2.1"], ["training_period", "2025/01/01\n〜2025/04/30"],
    ["threshold", "70"], ["latest_score", "85"], ["score_grade", "E"], ["recon_threshold", "0.35"],
])
write_csv("pumpunit_structure.csv", ["stage", "state"], [
    ["モーター", "normal"], ["ギヤ", "normal"], ["ソケット", "critical"],
])
write_csv("pumpunit_sensor_legend.csv", ["key", "label", "color", "axis"], [
    ["anomaly_score", "１軸", "#e5322d", "left"], ["discharge_pressure", "２軸", "#3b9dff", "left"],
    ["current_oc", "３軸", "#f5c400", "left"], ["motor_current", "４軸", "#5cc84a", "left"],
    ["temperature", "５軸", "#a45fe0", "left"],
])
PU_N = 97  # 15-minute samples, 05/18 10:30 -> 05/19 10:30
def pu_time(i):
    m = 10 * 60 + 30 + i * 15
    day = 18 + m // (24 * 60)
    m %= 24 * 60
    return f"05/{day:02d} {m // 60:02d}:{m % 60:02d}"
# １軸 (red) is the anomaly score; ２〜５軸 share the red line's starting value and
# stay in the same low band (never below 1, so nothing is clipped at the bottom).
pu_rows = []
pu_start = None
for i in range(PU_N):
    f = i / (PU_N - 1)
    if f < 0.78:
        score = 6 + rng.uniform(-3, 3)
    else:
        score = 6 + (f - 0.78) / 0.22 * 68 + rng.uniform(-9, 9)
    if i >= PU_N - 4:
        score = 78 + rng.uniform(0, 12)
    if i == PU_N - 1:
        score = 85.0
    score = round(max(1, min(98, score)), 1)
    if pu_start is None:
        pu_start = score
    def ax(drift, noise, first=(i == 0)):
        return pu_start if first else round(max(1.0, pu_start + drift + rng.uniform(-noise, noise)), 1)
    pu_rows.append([
        pu_time(i),
        score,
        ax(8 * f, 2.5),                                   # ２軸: slow rise
        ax(2 + 3 * _math.sin(f * 6.0), 2.0),               # ３軸: gentle wave
        ax(1 + 10 * max(0.0, f - 0.75) / 0.25, 2.0),       # ４軸: rises late, like the load
        ax(4 + 4 * _math.sin(f * 3.0 + 1.0), 2.5),         # ５軸: gentle wave
    ])
write_csv("pumpunit_sensors.csv", ["time", "anomaly_score", "discharge_pressure", "current_oc", "motor_current", "temperature"], pu_rows)
write_csv("pumpunit_alert_marker.csv", ["key", "value"], [["index", 84], ["label", "アラート発生 09:55"]])
pu_mini = []
for i in range(49):
    f = i / 48
    v = 30 + 55 * (f ** 1.3) + rng.uniform(-6, 6)
    pu_mini.append([pu_time(i * 2), round(85.0 if i == 48 else max(5, min(97, v)), 1)])
write_csv("pumpunit_score_mini.csv", ["time", "value"], pu_mini)
pu_week = []
for i in range(56):
    f = i / 55
    v = 25 + 60 * (f ** 1.6) + rng.uniform(-5, 5)
    pu_week.append([f"05/{13 + i // 8:02d}", round(85.0 if i == 55 else max(5, min(97, v)), 1)])
write_csv("pumpunit_score_7day.csv", ["date", "value"], pu_week)
pu_recon = []
for i in range(PU_N):
    v = 0.3 + rng.uniform(-0.13, 0.13)
    if i == 63:
        v = 0.92
    elif i in (18, 41, 77):
        v = 0.58 + rng.uniform(0, 0.08)
    pu_recon.append([pu_time(i), round(max(0.08, min(0.95, v)), 3)])
write_csv("pumpunit_reconstruction.csv", ["time", "value"], pu_recon)
pu_dist = []
for b in range(0, 100, 2):
    freq = 30 * _math.exp(-((b + 1 - 42) ** 2) / (2 * 13 ** 2)) + rng.uniform(-1.2, 1.2)
    pu_dist.append([b, int(round(max(0, freq)))])
write_csv("pumpunit_distribution.csv", ["bucket", "frequency"], pu_dist)
write_csv("pumpunit_distribution_marker.csv", ["key", "value"], [["value", 85], ["label", "現在値 85"]])
# 生データ: two point clouds (blue / orange) over the same 24h; both sink where the
# anomaly score rises (last ~20% of the window), like the reference scatter image.
pu_raw = []
for series, base, noise, outlier in (("blue", 0.62, 0.13, 0.06), ("orange", 0.55, 0.08, 0.02)):
    for i in range(180):
        x = i / 179 + rng.uniform(-0.004, 0.004)
        y = base + rng.uniform(-noise, noise)
        if rng.random() < outlier:
            y = base + rng.uniform(0.18, 0.32)
        if x > 0.80:
            y -= (x - 0.80) / 0.20 * 0.45
        pu_raw.append([series, round(min(0.97, max(0.04, x)), 4), round(min(0.97, max(0.04, y)), 4)])
write_csv("pumpunit_rawdata.csv", ["series", "x", "y"], pu_raw)
# newest first (the loader also sorts by date descending, so row order is not load-bearing)
write_csv("pumpunit_failure_history.csv", ["date", "cause", "action"], [
    ["2025/04/30", "ソケット先端のひび割れ", "ソケットの交換"],
    ["2024/12/02", "ソケットの変形・ダメージ", "ソケットの交換、芯出し調整"],
    ["2024/08/19", "ソケットのひび（打痕による）", "ソケットの交換、ボルト当たり面の確認"],
    ["2024/03/08", "ソケット内面の欠け", "ソケットの交換"],
    ["2023/10/21", "ソケット角部の摩耗・ダメージ", "ソケットの交換、締付トルク再設定"],
    ["2023/06/03", "ソケット先端のひび割れ", "ソケットの交換"],
    ["2023/02/15", "ソケットの破損", "ソケットの交換"],
    ["2022/11/14", "ソケット先端のひび割れ", "ソケットの交換"],
    ["2022/07/27", "ソケット角部の欠け", "ソケットの交換"],
    ["2022/03/09", "ソケット内面のクラック", "ソケットの交換、締付回数の見直し"],
    ["2021/12/20", "ソケットの破損", "ソケットの交換"],
    ["2021/09/06", "ソケットのひび（打痕による）", "ソケットの交換、ボルト当たり面の確認"],
    ["2021/05/18", "ソケットの摩耗・ダメージ", "ソケットの交換"],
    ["2021/01/25", "ソケット先端のひび割れ", "ソケットの交換"],
    ["2020/10/12", "ソケットの変形", "ソケットの交換、芯出し調整"],
    ["2020/06/29", "ソケット内面の欠け", "ソケットの交換"],
    ["2020/02/17", "ソケットのひび割れ", "ソケットの交換"],
    ["2019/11/04", "ソケット角部のダメージ", "ソケットの交換、締付トルク再設定"],
    ["2019/07/22", "ソケットの破損", "ソケットの交換"],
    ["2019/03/11", "ソケット先端のひび", "ソケットの交換"],
])
# 最新アラート情報パネルの 5 行（ナットランナー用）
write_csv("pumpunit_info_rows.csv", ["label", "value"], [
    ["設備ID", "ナットランナーPU-01"],
    ["締め付けID", "Y202505190002"],
    ["発生時刻", "2025-05-19-09:55:30"],
    ["軸番号", "１"],
    ["Health Score", "E"],
])
# 生データの縦軸の選択肢（先頭が初期表示）
write_csv("pumpunit_raw_axes.csv", ["key", "label", "unit", "max"], [
    ["angle", "締め付け角度", "deg", 180],
    ["torque", "トルク", "N·m", 100],
])
write_csv("pumpunit_ai_chat.csv", ["sender", "time", "kind", "text"], [
    ["user", "10:28", "text", "この装置の異常のトレンドを教えてください。"],
    ["ai", "10:28", "text", "過去7日間の異常スコアは徐々に上昇傾向にあり、特に05/19 6:30 以降にスコアが上昇しています。これは主に、吸込みフィルターの詰まりと流量低下を原因と考えられます。"],
    ["ai", "10:28", "chart", "過去7日間の異常スコア推移"],
    ["user", "10:29", "text", "なぜ異常スコアが高いのかを詳しく分析してください。"],
    ["ai", "10:29", "text", "異常スコアが高い主な要因は以下の通りです。\n・流量の低下（OC流量）\n　05/16以降、流量が徐々に低下しており、ポンプリングの効率低下の可能性があります。\n・モーター電流の増加\n　負荷の上昇や抵抗の増加が影響し、電流値が上昇しています。\n・再構成誤差の増加\n　Autoencoderモデルがパターンから大きく乖離しており、異常と判定されるデータが多くなっています。\nこれらの要因を総合的に判断し、異常スコアが高くなっています。"],
])
# ---------------------------------------------------------------------------
# 21) 設備異常履歴 > T-MSS: 1 件の異常履歴（2025/04/30 ソケット先端のひび割れ）の
#     詳細画面。見出し・日時・本文はすべてここから。
# ---------------------------------------------------------------------------
write_csv("tmss_history_detail.csv", ["key", "value"], [
    ["page_title", "設備異常履歴"],
    ["equipment_label", "設備名"], ["equipment_name", "ナットランナーPU-01"], ["status", "稼働中"],
    ["location_label", "設置場所"], ["location", "製造ライン1"],
    ["equipment_id_label", "設備ID"], ["equipment_id", "ナットランナーPU-01"],
    ["fastening_id_label", "締め付けID"], ["fastening_id", "2025-04-30-10:42:15"],
    ["issue_title", "不具合（詳細）"], ["issue_date_label", "発生日時"], ["issue_date", "2025/04/30 10:42"],
    ["issue_text", "締付け動作中に締付けトルクの立ち上がり不良と異常振動を検知し、異常アラーム（トルク異常）が発生。\nソケット先端部にひび割れがあり、ボルト頭部との嵌合が不安定で設定トルクに達しない状態。アラーム発生後は自動で停止する。"],
    ["cause_title", "原因（詳細）"], ["cause_date_label", "特定日時"], ["cause_date", "2025/04/30 13:20"],
    ["cause_text", "ソケット先端部の疲労によるひび割れ（打痕を起点としたクラックの進展）。\n締付け回数が交換目安を超えて使用されており、ボルト当たり面の偏摩耗も確認。"],
    ["action_title", "処置（詳細）"], ["action_date_label", "完了日時"], ["action_date", "2025/04/30 15:05"],
    ["action_text", "ソケットを新品に交換し、締付けトルク・角度の校正を実施。\n動作確認のうえ、正常に締付けができることを確認し、設備を復旧。\n再発防止として、締付け回数に基づくソケット交換周期を作業標準に追記。"],
])
# ---------------------------------------------------------------------------
# 22) 品質 > 品質状況2: 高岡電池工場 CCRダッシュボード（品質状況）の参考画像を 1:1 再現
# ---------------------------------------------------------------------------
write_csv("quality2_meta.csv", ["key", "value"], [
    ["factory_name", "高岡電池工場"], ["title", "CCRダッシュボード（品質状況）"],
    ["line_name", "LINE #1"], ["report_date", "2025/05/28"], ["shift", "白直"],
    ["auto_refresh_label", "自動更新"], ["auto_refresh", "ON"],
    ["todo_title", "車体部　ToDoリスト（5/28）"], ["bad_title", "T　当月廃品数詳細"], ["bad_col2_label", "廃品理由"],
    ["owner_self_label", "自"], ["owner_other_label", "他"],
    ["trend_y_labels", "0|20|40|60|80|100|120|130|140|160|180|200"],  # 参考画像の目盛り表記そのまま
    ["trend_y_max", "200"],
])
write_csv("quality2_kpis.csv", ["key", "prefix", "label", "value", "unit", "tier", "row1_label", "row1_value", "row2_label", "row2_value"], [
    ["k_rate", "K", "直行率", "94.3", "%", "critical", "前日", "94.9%", "前週", "95.5%"],
    ["w_defect", "W", "台当たり不具合件数", "1.05", "件/台", "good", "手直し総数", "119件", "", ""],
    ["t_bad", "T", "当月廃品数", "3", "件", "good", "前月廃品数", "11件", "", ""],
    ["k_defect", "K", "台当たり不具合件数", "1.88", "件/台", "good", "手直し総数", "122件", "", ""],
    ["outflow", "", "後工程流出数（当月）", "2", "件", "good", "前月", "1件", "", ""],
])
write_csv("quality2_worst_rework.csv", ["rank", "process", "count", "prev", "flag"], [
    [1, "XX 塗布工程", "23件", "19件", "critical"], [2, "●● 巻付け工程", "21件", "20件", "critical"], [3, "XX 組立工程", "14件", "16件", "none"],
])
write_csv("quality2_worst_calls.csv", ["rank", "process", "count", "prev", "flag"], [
    [1, "XX 巻付け工程", "23件", "22件", "critical"], [2, "▲▲ 巻付け工程", "18件", "15件", "warn"], [3, "■■ 巻付け工程", "10件", "12件", "none"],
])
# owner: 自 = 自工程起因（赤枠）, 他 = 他工程起因（緑枠）
write_csv("quality2_bad_products.csv", ["date", "reason", "owner"], [
    ["5/21", "塗布ムラによる膜厚不足", "自"],
    ["5/15", "受入部品の寸法不良", "他"],
    ["5/10", "巻付け位置ズレ", "自"],
])
# 車体部 ToDo: done_by / doing_by は担当者の姓（quality2_people.csv の surname）
write_csv("quality2_todo.csv", ["done_by", "doing_by", "task"], [
    ["鈴木", "", "XX 塗布工程の塗布条件（粘度・吐出量）の再確認"],
    ["", "佐藤", "●● 巻付け工程の段取り変更・材料ロット履歴の確認"],
    ["斉藤", "山田", "後工程流出品の受入チェック基準の見直し"],
    ["", "田中", "W工程 識別管理ルールの改訂と周知"],
    ["高橋", "", "XX 組立工程の手直し要因分析（5/24〜5/28）"],
])
write_csv("quality2_people.csv", ["surname", "given_name", "email", "presence", "bg", "fg"], [
    ["鈴木", "健太", "suzuki@dekirunet02.onmicrosoft.com", "available", "#c9d8f3", "#1b3a6b"],
    ["佐藤", "美咲", "sato@dekirunet02.onmicrosoft.com", "busy", "#f3c9d2", "#7a1c2e"],
    ["斉藤", "大輔", "saito@dekirunet02.onmicrosoft.com", "available", "#cfe8d4", "#1e5b2e"],
    ["山田", "由紀", "yamada@dekirunet02.onmicrosoft.com", "away", "#f3c9d2", "#7a1c2e"],
    ["田中", "翔", "tanaka@dekirunet02.onmicrosoft.com", "available", "#f7dcc4", "#7a3d12"],
    ["高橋", "恵", "takahashi@dekirunet02.onmicrosoft.com", "busy", "#e0d2f0", "#4a2a7a"],
])
write_csv("quality2_trend.csv", ["date", "total", "red", "yellow", "blue"], [
    ["5/24", 112, 26, 21, 12], ["5/25", 118, 24, 21, 12], ["5/26", 123, 25, 21, 12],
    ["5/27", 136, 24, 21, 12], ["5/28（本日）", 142, 23, 21, 14],
])
write_csv("quality2_trend_legend.csv", ["key", "label"], [
    ["total", "全体"], ["red", "XX 塗布工程"], ["yellow", "●● 巻付け工程"], ["blue", "XX 組立工程"],
])
write_csv("quality2_ai_tips.csv", ["color", "text"], [
    ["red", "●● 巻付け工程で 5/27以降急激な悪化を確認。段取り変更・材料ロット・設備設定変更履歴の確認を推奨します。"],
    ["yellow", "XX 塗布工程の手直し件数が継続して高止まりしています。塗布条件の再確認と設備保全の実施を推奨します。"],
    ["blue", "後工程流出数が前月比で増加しています。AI工程での受入チェック基準の見直しと、W工程の識別管理の強化を推奨します。"],
])
write_csv("quality2_ai_chat.csv", ["sender", "time", "text"], [
    ["ai", "10:30", "こんにちは！品質状況についてご案内します。直行率や手直し件数、後工程流出について、気になる点があればお尋ねください。"],
    ["user", "10:31", "今いちばん対策が必要な工程はどこですか？"],
    ["ai", "10:31", "手直し発生件数は XX 塗布工程が 23 件（前日 19 件）でワースト 1 位、●● 巻付け工程が 21 件で 2 位です。呼出回数でも XX 巻付け工程が 23 件で最多です。K 直行率も 94.3% と前日（94.9%）・前週（95.5%）から低下しているため、まず XX 塗布工程の塗布条件と設備保全の確認を優先することをお勧めします。"],
])
print("done")
