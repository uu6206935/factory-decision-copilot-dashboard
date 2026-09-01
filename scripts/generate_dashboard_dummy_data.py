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
OUT = ROOT / "sample_data" / "dashboard"
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

print("done")
