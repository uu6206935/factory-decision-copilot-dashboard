from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .decision import compare_stop_vs_continue
from .models import AnalysisResult, Candidate, Evidence
from .schema import choose_role_tables_multi, load_role_frame, scan_tables

SENSOR_COLS = ["current_a", "temperature_c", "vibration_mm_s", "pressure_mpa", "torque_nm"]


def _norm_id(value) -> str:
    return str(value).strip().upper().replace("_", "-")


def _is_ng(value) -> bool:
    s = str(value).strip().upper().replace(" ", "")
    return s in {"NG", "NOK", "FAIL", "FAILED", "FALSE", "不合格", "異常", "不良", "×", "0"}


def _to_dt(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _extract_vehicle(question: str, quality: pd.DataFrame | None) -> str | None:
    if quality is not None and "vehicle_id" in quality.columns:
        known = [_norm_id(v) for v in quality["vehicle_id"].dropna().astype(str).unique()]
        qnorm = _norm_id(question)
        # longest first prevents partial IDs from winning
        for vid in sorted(known, key=len, reverse=True):
            if vid and vid in qnorm:
                return vid
    m = re.search(r"(?:QV|TEST|VEH|VIN)[-_]?[A-Z0-9-]+", question, re.IGNORECASE)
    return _norm_id(m.group(0)) if m else None


def _html(df: pd.DataFrame, limit: int = 12) -> str:
    if df.empty:
        return ""
    shown = df.head(limit).copy()
    for c in shown.columns:
        if pd.api.types.is_float_dtype(shown[c]):
            shown[c] = shown[c].map(lambda x: f"{x:.3f}" if pd.notna(x) else "")
    return shown.to_html(index=False, classes="table", border=0)


def _normalize_frames(data_dir: Path):
    profiles, warnings = scan_tables(data_dir)
    chosen_multi = choose_role_tables_multi(profiles)
    frames = {role: load_role_frame(data_dir, role_profiles) for role, role_profiles in chosen_multi.items() if role_profiles}
    chosen = {role: role_profiles[0] for role, role_profiles in chosen_multi.items() if role_profiles}

    q = frames.get("quality")
    if q is not None and not q.empty:
        q = q.copy()
        q["vehicle_id"] = q["vehicle_id"].map(_norm_id)
        q["is_ng"] = q["result"].map(_is_ng).astype(int)
        if "timestamp" in q.columns:
            q["timestamp"] = _to_dt(q["timestamp"])
        frames["quality"] = q

    p = frames.get("process")
    if p is not None and not p.empty:
        p = p.copy()
        p["vehicle_id"] = p["vehicle_id"].map(_norm_id)
        p["equipment_id"] = p["equipment_id"].astype(str).str.strip()
        for c in ["start_time", "end_time", "timestamp"]:
            if c in p.columns:
                p[c] = _to_dt(p[c])
        frames["process"] = p

    e = frames.get("equipment_logs")
    if e is not None and not e.empty:
        e = e.copy()
        e["equipment_id"] = e["equipment_id"].astype(str).str.strip()
        if "timestamp" in e.columns:
            e["timestamp"] = _to_dt(e["timestamp"])
        for c in SENSOR_COLS:
            if c in e.columns:
                e[c] = pd.to_numeric(e[c], errors="coerce")
        frames["equipment_logs"] = e

    m = frames.get("maintenance")
    if m is not None and not m.empty:
        m = m.copy()
        m["equipment_id"] = m["equipment_id"].astype(str).str.strip()
        if "timestamp" in m.columns:
            m["timestamp"] = _to_dt(m["timestamp"])
        frames["maintenance"] = m

    parts = frames.get("parts")
    if parts is not None and not parts.empty:
        parts = parts.copy()
        parts["vehicle_id"] = parts["vehicle_id"].map(_norm_id)
        frames["parts"] = parts

    return frames, profiles, chosen, warnings


def _equipment_stats(process: pd.DataFrame, quality: pd.DataFrame) -> pd.DataFrame:
    if process.empty or quality.empty:
        return pd.DataFrame()
    q = quality[["vehicle_id", "is_ng"]].drop_duplicates("vehicle_id", keep="last")
    merged = process[["vehicle_id", "equipment_id"]].drop_duplicates().merge(q, on="vehicle_id", how="left")
    merged["is_ng"] = merged["is_ng"].fillna(0)
    baseline = float(q["is_ng"].mean()) if len(q) else 0.0
    out = merged.groupby("equipment_id", as_index=False).agg(
        vehicles=("vehicle_id", "nunique"),
        ng_count=("is_ng", "sum"),
        ng_rate=("is_ng", "mean"),
    )
    out["baseline_ng_rate"] = baseline
    out["lift"] = np.where(baseline > 0, out["ng_rate"] / baseline, 0.0)
    # Support-weighted suspicion: a 100% NG rate on 1 unit should not dominate.
    out["association_score"] = np.clip(
        (out["ng_rate"] - baseline).clip(lower=0) / max(0.05, 1 - baseline) * np.minimum(1.0, out["vehicles"] / 8.0),
        0,
        1,
    )
    return out.sort_values(["association_score", "ng_rate", "vehicles"], ascending=False)


def _event_time(process_rows: pd.DataFrame, equipment: str) -> pd.Timestamp | None:
    rows = process_rows[process_rows["equipment_id"].astype(str) == str(equipment)]
    if rows.empty:
        return None
    for c in ["end_time", "start_time", "timestamp"]:
        if c in rows.columns:
            vals = rows[c].dropna()
            if not vals.empty:
                return pd.Timestamp(vals.iloc[-1])
    return None


def _sensor_anomaly(logs: pd.DataFrame | None, equipment: str, event_time: pd.Timestamp | None) -> tuple[float, list[Evidence]]:
    if logs is None or logs.empty or "equipment_id" not in logs.columns:
        return 0.0, []
    sub = logs[logs["equipment_id"].astype(str) == str(equipment)].copy()
    if sub.empty:
        return 0.0, []
    if "timestamp" in sub.columns:
        sub = sub.sort_values("timestamp")
    evidence: list[Evidence] = []
    sensor_scores: list[float] = []

    for col in [c for c in SENSOR_COLS if c in sub.columns]:
        s = sub[[col] + (["timestamp"] if "timestamp" in sub.columns else [])].dropna(subset=[col]).copy()
        if len(s) < 5:
            continue
        if event_time is not None and "timestamp" in s.columns and s["timestamp"].notna().any():
            target = s[(s["timestamp"] >= event_time - pd.Timedelta(minutes=5)) & (s["timestamp"] <= event_time + pd.Timedelta(minutes=10))]
            baseline = s[s["timestamp"] < event_time - pd.Timedelta(minutes=7)].tail(40)
            if target.empty:
                target = s[s["timestamp"] <= event_time].tail(2)
            if len(baseline) < 4:
                baseline = s[s["timestamp"] < event_time].head(max(4, len(s) - len(target)))
        else:
            target = s.tail(max(1, min(3, len(s) // 4)))
            baseline = s.iloc[:-len(target)]
        if len(baseline) < 4:
            continue

        base_vals = baseline[col].astype(float)
        target_val = float(target[col].astype(float).mean())
        median = float(base_vals.median())
        mad = float((base_vals - median).abs().median())
        robust_sigma = 1.4826 * mad
        std = float(base_vals.std(ddof=0))
        scale = robust_sigma if robust_sigma > 1e-9 else (std if std > 1e-9 else 1.0)
        z = abs(target_val - median) / scale
        score = min(1.0, z / 4.0)
        sensor_scores.append(score)
        pct = ((target_val - median) / median * 100.0) if abs(median) > 1e-9 else 0.0
        if abs(pct) >= 4 or z >= 2:
            src = ", ".join(sorted(set(sub.get("_source_file", pd.Series(dtype=str)).dropna().astype(str).tolist()))) or "equipment_logs"
            evidence.append(Evidence(
                kind="sensor",
                text=f"{equipment} {col}: 対象時点 {target_val:.2f} / 通常中央値 {median:.2f} ({pct:+.1f}%, robust-z={z:.1f})",
                source=src,
                strength=score,
            ))
    return (float(np.mean(sensor_scores)) if sensor_scores else 0.0), evidence


def _latest_maintenance(maintenance: pd.DataFrame | None, equipment: str) -> list[Evidence]:
    if maintenance is None or maintenance.empty or "equipment_id" not in maintenance.columns:
        return []
    rows = maintenance[maintenance["equipment_id"].astype(str) == str(equipment)].copy()
    if rows.empty:
        return []
    if "timestamp" in rows.columns:
        rows = rows.sort_values("timestamp")
    r = rows.iloc[-1]
    issue = str(r.get("issue", "保全履歴あり"))
    action = str(r.get("action", ""))
    src = ", ".join(sorted(set(rows.get("_source_file", pd.Series(dtype=str)).dropna().astype(str).tolist()))) or "maintenance"
    return [Evidence("maintenance", f"過去保全: {issue} / 対応: {action}", src, 0.55)]


def _lot_stats(process: pd.DataFrame, quality: pd.DataFrame, parts: pd.DataFrame | None) -> pd.DataFrame:
    if parts is not None and not parts.empty and {"vehicle_id", "part_lot"}.issubset(parts.columns):
        exposure = parts[["vehicle_id", "part_lot"]].dropna().drop_duplicates()
    elif "part_lot" in process.columns:
        exposure = process[["vehicle_id", "part_lot"]].dropna().drop_duplicates()
    else:
        return pd.DataFrame()
    q = quality[["vehicle_id", "is_ng"]].drop_duplicates("vehicle_id", keep="last")
    merged = exposure.merge(q, on="vehicle_id", how="left")
    baseline = float(q["is_ng"].mean()) if len(q) else 0.0
    out = merged.groupby("part_lot", as_index=False).agg(vehicles=("vehicle_id", "nunique"), ng_count=("is_ng", "sum"), ng_rate=("is_ng", "mean"))
    out["baseline_ng_rate"] = baseline
    out["lift"] = np.where(baseline > 0, out["ng_rate"] / baseline, 0.0)
    out["association_score"] = np.clip((out["ng_rate"] - baseline).clip(lower=0) / max(0.05, 1 - baseline) * np.minimum(1.0, out["vehicles"] / 8.0), 0, 1)
    return out.sort_values(["association_score", "ng_rate"], ascending=False)


def _target_lots(vehicle: str | None, process: pd.DataFrame, parts: pd.DataFrame | None) -> list[str]:
    if not vehicle:
        return []
    vals: list[str] = []
    if parts is not None and not parts.empty and {"vehicle_id", "part_lot"}.issubset(parts.columns):
        vals.extend(parts.loc[parts["vehicle_id"] == vehicle, "part_lot"].dropna().astype(str).tolist())
    if "part_lot" in process.columns:
        vals.extend(process.loc[process["vehicle_id"] == vehicle, "part_lot"].dropna().astype(str).tolist())
    return list(dict.fromkeys(vals))


def _candidate_label_from_maintenance(equipment: str, maint_evidence: list[Evidence]) -> str:
    if maint_evidence:
        text = maint_evidence[0].text
        issue = text.split("過去保全:", 1)[-1].split("/ 対応:", 1)[0].strip()
        if issue and issue != "保全履歴あり":
            return f"{equipment}: {issue}の再発・関連"
    return f"{equipment}: 設備状態または工程条件の変動"


def analyze(question: str, data_dir: Path) -> AnalysisResult:
    frames, profiles, chosen, scan_warnings = _normalize_frames(data_dir)
    quality = frames.get("quality", pd.DataFrame())
    process = frames.get("process", pd.DataFrame())
    logs = frames.get("equipment_logs")
    maintenance = frames.get("maintenance")
    parts = frames.get("parts")

    data_roles = {role: profile.label for role, profile in chosen.items()}
    if quality.empty or process.empty:
        from .standalone_analysis import analyze_available
        return analyze_available(question, data_dir)

    vehicle = _extract_vehicle(question, quality)
    baseline_ng = float(quality["is_ng"].mean()) if len(quality) else 0.0
    summary = [f"自動認識したデータ: {', '.join(f'{k}={v}' for k, v in data_roles.items())}"]
    defect_type = None
    target_process = pd.DataFrame()

    if vehicle:
        qrows = quality[quality["vehicle_id"] == vehicle]
        if not qrows.empty:
            qrow = qrows.iloc[-1]
            defect_type = str(qrow.get("defect_type", "")) if "defect_type" in qrows.columns and pd.notna(qrow.get("defect_type")) else None
            summary.append(f"対象 {vehicle}: 判定={qrow.get('result', '不明')}" + (f" / 不具合={defect_type}" if defect_type else ""))
        else:
            summary.append(f"対象 {vehicle} の品質レコードは見つかりませんでした。")
        target_process = process[process["vehicle_id"] == vehicle].copy()
        if not target_process.empty:
            summary.append("通過設備: " + ", ".join(target_process["equipment_id"].astype(str).drop_duplicates().tolist()))
    else:
        summary.append("車両/製品ID指定なし: 全体データから疑わしい設備をランキングします。")

    eq_stats = _equipment_stats(process, quality)
    lot_stats = _lot_stats(process, quality, parts)
    tables: dict[str, str] = {}
    if not eq_stats.empty:
        display = eq_stats[["equipment_id", "vehicles", "ng_count", "ng_rate", "baseline_ng_rate", "lift", "association_score"]].copy()
        display["ng_rate"] *= 100
        display["baseline_ng_rate"] *= 100
        display = display.rename(columns={"ng_rate": "NG率[%]", "baseline_ng_rate": "全体NG率[%]", "association_score": "関連度"})
        tables["設備別 品質関連"] = _html(display)
    if not lot_stats.empty:
        d = lot_stats[["part_lot", "vehicles", "ng_count", "ng_rate", "lift", "association_score"]].copy()
        d["ng_rate"] *= 100
        d = d.rename(columns={"ng_rate": "NG率[%]", "association_score": "関連度"})
        tables["部品ロット別 品質関連"] = _html(d)

    candidates: list[Candidate] = []
    eq_lookup = eq_stats.set_index("equipment_id") if not eq_stats.empty else pd.DataFrame()
    if vehicle and not target_process.empty:
        equipment_list = target_process["equipment_id"].astype(str).drop_duplicates().tolist()
    else:
        equipment_list = eq_stats.head(6)["equipment_id"].astype(str).tolist() if not eq_stats.empty else []

    for eq in equipment_list:
        assoc = 0.0
        ng_rate = baseline_ng
        evidence: list[Evidence] = []
        if not eq_stats.empty and eq in eq_lookup.index:
            r = eq_lookup.loc[eq]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            assoc = float(r["association_score"])
            ng_rate = float(r["ng_rate"])
            proc_src = ", ".join(sorted(set(process.loc[process["equipment_id"].astype(str)==str(eq), "_source_file"].dropna().astype(str).tolist()))) if "_source_file" in process.columns else "process"
            qual_src = ", ".join(sorted(set(quality["_source_file"].dropna().astype(str).tolist()))) if "_source_file" in quality.columns else "quality"
            evidence.append(Evidence(
                "quality_association",
                f"{eq}通過品: NG率 {ng_rate*100:.1f}% ({int(r['ng_count'])}/{int(r['vehicles'])})、全体 {baseline_ng*100:.1f}%、lift {float(r['lift']):.2f}x",
                f"{qual_src} + {proc_src}",
                assoc,
            ))
        event_time = _event_time(target_process, eq) if vehicle and not target_process.empty else None
        sensor_score, sensor_evidence = _sensor_anomaly(logs, eq, event_time)
        evidence.extend(sensor_evidence)
        maint_evidence = _latest_maintenance(maintenance, eq)
        evidence.extend(maint_evidence)

        maint_score = 0.18 if maint_evidence else 0.0
        # Weighted priority, not probability.
        score = min(0.99, assoc * 0.52 + sensor_score * 0.38 + maint_score)
        checks = [f"{eq}の対象時刻前後の設備状態・設定値を現物/原ログで確認"]
        if sensor_evidence:
            checks.append("変動が大きいセンサ項目について基準値・校正・消耗品状態を確認")
        if maint_evidence:
            checks.append("過去保全と同じ現象が再現しているか点検し、対策後の品質を再確認")
        candidates.append(Candidate(_candidate_label_from_maintenance(eq, maint_evidence), score, "equipment", evidence, checks))

    target_lots = _target_lots(vehicle, process, parts)
    if not vehicle and not lot_stats.empty:
        target_lots = lot_stats.head(3)["part_lot"].astype(str).tolist()
    if not lot_stats.empty:
        llookup = lot_stats.set_index("part_lot")
        for lot in target_lots:
            if lot not in llookup.index:
                continue
            r = llookup.loc[lot]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            assoc = float(r["association_score"])
            # Keep lot hypothesis in the race, but don't let tiny samples dominate.
            score = min(0.92, assoc * 0.78)
            part_src = ", ".join(sorted(set(parts["_source_file"].dropna().astype(str).tolist()))) if parts is not None and not parts.empty and "_source_file" in parts.columns else "parts/process"
            qual_src = ", ".join(sorted(set(quality["_source_file"].dropna().astype(str).tolist()))) if "_source_file" in quality.columns else "quality"
            ev = [Evidence("lot_association", f"ロット {lot}: NG率 {float(r['ng_rate'])*100:.1f}% ({int(r['ng_count'])}/{int(r['vehicles'])}) / lift {float(r['lift']):.2f}x", f"{part_src} + {qual_src}", assoc)]
            candidates.append(Candidate(f"部品ロット {lot} のばらつき", score, "part_lot", ev, [f"{lot}と別ロットで同一検査項目の分布を比較", "受入/寸法/材料証明などのロット情報を確認"]))

    candidates.sort(key=lambda c: c.score, reverse=True)
    candidates = candidates[:6]

    scenarios = []
    top_eq = next((c for c in candidates if c.category == "equipment"), None)
    if top_eq and not eq_stats.empty:
        # recover equipment id from label prefix
        eq = top_eq.label.split(":", 1)[0]
        if eq in eq_lookup.index:
            r = eq_lookup.loc[eq]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            scenarios = compare_stop_vs_continue(float(r["ng_rate"]), baseline_ng)

    graph_nodes: list[dict] = []
    graph_edges: list[tuple[str, str]] = []
    root = vehicle or "FACTORY"
    graph_nodes.append({"id": root, "label": root, "kind": "target"})
    for c in candidates[:4]:
        cid = c.label
        graph_nodes.append({"id": cid, "label": c.label, "kind": c.category, "score": c.score})
        graph_edges.append((root, cid))
        for i, ev in enumerate(c.evidence[:2]):
            eid = f"{cid}::e{i}"
            graph_nodes.append({"id": eid, "label": ev.text, "kind": "evidence"})
            graph_edges.append((cid, eid))

    if candidates:
        summary.append(f"最優先確認候補: {candidates[0].label}（優先度指標 {candidates[0].score*100:.0f}/100。真因確率ではありません）")
    else:
        summary.append("十分な関連付け情報がなく、原因候補を算出できませんでした。")
    if scan_warnings:
        summary.append("一部ファイル読込警告あり: " + " / ".join(scan_warnings[:2]))

    return AnalysisResult(
        title="品質トラブル原因探索 + 意思決定支援",
        vehicle_id=vehicle,
        defect_type=defect_type,
        summary=summary,
        candidates=candidates,
        scenarios=scenarios,
        tables=tables,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        data_roles=data_roles,
        mode="root_cause",
        active_modules=["root_cause"] + [x for x, ok in [("sensor_monitoring", logs is not None and not logs.empty), ("maintenance_intelligence", maintenance is not None and not maintenance.empty), ("quality_lot", parts is not None and not parts.empty)] if ok],
        missing_for_deeper=[],
    )
