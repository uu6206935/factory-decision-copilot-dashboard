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

print("done")
