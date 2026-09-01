from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import numpy as np
import pandas as pd

from .capabilities import detect_capabilities
from .models import AnalysisResult, Candidate, Evidence
from .process_intelligence import process_snapshot
from .predictive_ai import threshold_forecast
from .schema import choose_role_tables_multi, load_role_frame, scan_tables
from .sensor_ai import equipment_health


def _html(df: pd.DataFrame, limit: int = 20) -> str:
    if df.empty:
        return ""
    shown = df.head(limit).copy()
    for c in shown.columns:
        if pd.api.types.is_float_dtype(shown[c]):
            shown[c] = shown[c].map(lambda x: f"{x:.3f}" if pd.notna(x) else "")
    return shown.to_html(index=False, classes="table", border=0)


def _is_ng(value) -> bool:
    s = str(value).strip().upper().replace(" ", "")
    return s in {"NG", "NOK", "FAIL", "FAILED", "FALSE", "不合格", "異常", "不良", "×", "0"}


def _frames(data_dir: Path) -> tuple[dict[str, pd.DataFrame], dict[str, str], list[str]]:
    profiles, warnings = scan_tables(data_dir)
    grouped = choose_role_tables_multi(profiles)
    frames: dict[str, pd.DataFrame] = {}
    labels: dict[str, str] = {}
    for role, ps in grouped.items():
        if not ps:
            continue
        df = load_role_frame(data_dir, ps)
        if not df.empty:
            frames[role] = df
            labels[role] = ps[0].label
    return frames, labels, warnings


def _quality_candidates(df: pd.DataFrame, question: str) -> tuple[list[Candidate], list[str], dict[str, str], str | None, str | None]:
    q = df.copy()
    if "vehicle_id" in q.columns:
        q["vehicle_id"] = q["vehicle_id"].astype(str).str.strip().str.upper().str.replace("_", "-", regex=False)
    q["is_ng"] = q["result"].map(_is_ng).astype(int) if "result" in q.columns else 0
    vehicle = None
    if "vehicle_id" in q.columns:
        qnorm = question.upper().replace("_", "-")
        for vid in sorted(q["vehicle_id"].dropna().astype(str).unique(), key=len, reverse=True):
            if vid and vid in qnorm:
                vehicle = vid; break
    if not vehicle:
        m = re.search(r"(?:QV|TEST|VEH|VIN)[-_]?[A-Z0-9-]+", question, re.I)
        vehicle = m.group(0).upper().replace("_", "-") if m else None

    summary = [f"品質データ {len(q)}行を単独分析します。工程履歴が無いため設備原因との関連付けは行いません。"]
    defect_type = None
    if vehicle and "vehicle_id" in q.columns:
        rows = q[q["vehicle_id"] == vehicle]
        if not rows.empty:
            r = rows.iloc[-1]
            defect_type = str(r.get("defect_type")) if pd.notna(r.get("defect_type")) else None
            summary.append(f"対象 {vehicle}: 判定={r.get('result', '不明')}" + (f" / 不具合={defect_type}" if defect_type else ""))

    group_col = next((c for c in ["defect_type", "inspection_item", "process"] if c in q.columns and q[c].notna().any()), None)
    candidates: list[Candidate] = []
    tables: dict[str, str] = {}
    baseline = float(q["is_ng"].mean()) if len(q) else 0.0
    summary.append(f"全体NG率 {baseline*100:.1f}%")
    if group_col:
        stats = q.groupby(group_col, dropna=False).agg(records=("is_ng", "size"), ng_count=("is_ng", "sum"), ng_rate=("is_ng", "mean")).reset_index()
        total_ng = max(float(stats["ng_count"].sum()), 1.0)
        stats["ng_share"] = stats["ng_count"] / total_ng
        stats["priority"] = np.clip(stats["ng_rate"] * 0.6 + stats["ng_share"] * 0.4, 0, 1)
        stats = stats.sort_values(["priority", "ng_count"], ascending=False)
        disp = stats.copy(); disp["ng_rate"] *= 100; disp["ng_share"] *= 100
        tables["品質傾向"] = _html(disp.rename(columns={"ng_rate":"NG率[%]", "ng_share":"NG構成比[%]", "priority":"優先度"}))
        src = ", ".join(sorted(set(q.get("_source_file", pd.Series(dtype=str)).dropna().astype(str)))) or "quality"
        for _, r in stats.head(6).iterrows():
            label = str(r[group_col])
            score = float(r["priority"])
            candidates.append(Candidate(
                f"品質傾向: {label}", score, "quality_trend",
                [Evidence("quality_trend", f"{group_col}={label}: NG率 {float(r['ng_rate'])*100:.1f}% / NG {int(r['ng_count'])}件 / 全{int(r['records'])}件", src, score)],
                [f"{label}の発生時刻・製品属性・検査条件を追加で層別化", "工程履歴が追加されたら設備・工程との関連を自動分析"],
            ))
    if not candidates and len(q):
        src = ", ".join(sorted(set(q.get("_source_file", pd.Series(dtype=str)).dropna().astype(str)))) or "quality"
        candidates.append(Candidate("品質全体: NG発生状況", float(np.clip(baseline, 0.05, 0.95)), "quality_trend", [Evidence("quality_summary", f"全体NG率 {baseline*100:.1f}% / NG {int(q['is_ng'].sum())}件 / 全{len(q)}件", src, float(np.clip(baseline,0,1)))], ["不具合種別・検査項目・日時列を追加すると層別分析が自動で深くなります", "工程履歴追加時は設備との品質関連を算出します"]))
        tables["品質全体"] = _html(pd.DataFrame([{"records":len(q),"ng_count":int(q['is_ng'].sum()),"ng_rate_pct":baseline*100}]))
    return candidates, summary, tables, vehicle, defect_type



def _quality_parts_candidates(quality: pd.DataFrame, parts: pd.DataFrame) -> tuple[list[Candidate], dict[str, str]]:
    if not {"vehicle_id", "result"}.issubset(quality.columns) or not {"vehicle_id", "part_lot"}.issubset(parts.columns):
        return [], {}
    q=quality.copy(); p=parts.copy()
    q["vehicle_id"]=q["vehicle_id"].astype(str).str.strip().str.upper().str.replace("_","-",regex=False)
    p["vehicle_id"]=p["vehicle_id"].astype(str).str.strip().str.upper().str.replace("_","-",regex=False)
    q["is_ng"]=q["result"].map(_is_ng).astype(int)
    q=q[["vehicle_id","is_ng"]].drop_duplicates("vehicle_id",keep="last")
    exp=p[["vehicle_id","part_lot"]].dropna().drop_duplicates()
    merged=exp.merge(q,on="vehicle_id",how="inner")
    if merged.empty: return [], {}
    baseline=float(q["is_ng"].mean()) if len(q) else 0.0
    st=merged.groupby("part_lot").agg(vehicles=("vehicle_id","nunique"),ng_count=("is_ng","sum"),ng_rate=("is_ng","mean")).reset_index()
    st["lift"]=np.where(baseline>0,st["ng_rate"]/baseline,0.0)
    st["association"]=np.clip((st["ng_rate"]-baseline).clip(lower=0)/max(0.05,1-baseline)*np.minimum(1.0,st["vehicles"]/8.0),0,1)
    st=st.sort_values(["association","ng_rate","vehicles"],ascending=False)
    src=", ".join(sorted(set(p.get("_source_file",pd.Series(dtype=str)).dropna().astype(str)))) or "parts"
    candidates=[]
    for _,r in st.head(5).iterrows():
        score=float(r["association"])*0.82
        candidates.append(Candidate(f"部品ロット {r['part_lot']}: 品質偏り候補",score,"part_lot",[Evidence("lot_association",f"NG率 {float(r['ng_rate'])*100:.1f}% / 全体 {baseline*100:.1f}% / lift {float(r['lift']):.2f}x / {int(r['vehicles'])}製品",src,score)],["同一検査項目で別ロットと比較","受入・材料・寸法のロット情報を確認"]))
    disp=st.copy(); disp["ng_rate"]*=100
    return candidates,{"部品ロット別 品質関連":_html(disp)}

def _sensor_candidates(data_dir: Path) -> tuple[list[Candidate], list[str], dict[str, str]]:
    health = equipment_health(data_dir)
    candidates: list[Candidate] = []
    summary = [f"設備ログから {len(health)}設備を単独監視します。品質データが無くても異常兆候の順位付けは可能です。"]
    rows = []
    forecast = threshold_forecast(data_dir)
    forecast_by_eq: dict[str, list[dict]] = {}
    for x in forecast.get("items", []): forecast_by_eq.setdefault(str(x["equipment_id"]), []).append(x)
    for h in health[:8]:
        sigs = sorted(h.signals, key=lambda s: s.anomaly_score, reverse=True)
        evidence = [Evidence("sensor", f"{s.name}: recent={s.latest:.3f} / baseline={s.baseline_median:.3f} / shift={s.shift_pct:+.1f}% / robust-z={s.robust_z:.1f}", ", ".join(h.source_files), s.anomaly_score) for s in sigs[:3] if s.latest is not None and s.baseline_median is not None]
        frows = [x for x in forecast_by_eq.get(h.equipment_id, []) if x.get("minutes_to_limit") is not None]
        if frows:
            f = min(frows, key=lambda x: float(x["minutes_to_limit"]))
            evidence.append(Evidence("predictive", f"{f['signal']} は現在トレンド継続時に約{float(f['minutes_to_limit']):.0f}分で異常帯へ到達", "threshold_forecast", 0.55))
        candidates.append(Candidate(f"{h.equipment_id}: 設備状態の異常兆候", float(h.risk_score), "equipment", evidence, ["上位異常信号の原ログ・校正・設定値を確認", "保全履歴が追加されたら過去故障との再発関係を自動照合"]))
        rows.append({"equipment_id": h.equipment_id, "risk_score": h.risk_score, "state": h.state, "top_signal": sigs[0].name if sigs else ""})
    tables = {"設備ヘルス": _html(pd.DataFrame(rows))} if rows else {}
    return candidates, summary, tables


def _process_candidates(data_dir: Path, question: str) -> tuple[list[Candidate], list[str], dict[str, str]]:
    snap = process_snapshot(data_dir)
    if not snap.get("available"):
        return [], ["工程データを認識しましたが分析可能な列が不足しています。"], {}
    summary = [f"工程履歴 {snap.get('case_count', 0)}製品を単独分析します。品質結果が無くても工程variant・逸脱・ボトルネックは分析できます。"]
    if snap.get("modal_path"): summary.append("最頻工程: " + snap["modal_path"])
    candidates: list[Candidate] = []
    bottlenecks = snap.get("bottlenecks", [])
    max_p90 = max([float(x.get("p90", 0)) for x in bottlenecks] or [1.0])
    for b in bottlenecks[:6]:
        score = float(np.clip(float(b.get("p90", 0)) / max(max_p90, 1e-9), 0, 1))
        candidates.append(Candidate(f"{b['equipment_id']}: サイクルタイム・ボトルネック候補", score, "process_bottleneck", [Evidence("process_cycle", f"median {b.get('median')} min / p90 {b.get('p90')} min / samples {int(b.get('count',0))}", "process history", score)], ["段取り・待ち・設備停止をサイクル時間へ分解", "品質データ追加時は遅延と品質NGの関連も確認"]))
    for d in snap.get("deviations", [])[:3]:
        candidates.append(Candidate(f"{d['target_id']}: 工程順序逸脱", 0.55, "process_deviation", [Evidence("process_variant", f"実績 {d['path']} / 標準候補 {d['expected']}", "process history", 0.55)], ["例外工程が正規運用か、手戻り・リワークかを確認"]))
    if not candidates:
        for v in snap.get("variants", [])[:4]:
            share=float(v.get("share",0)); candidates.append(Candidate(f"工程variant: {v.get('path','')}", max(0.15,1-share) if len(snap.get('variants',[]))>1 else 0.2, "process_variant", [Evidence("process_variant", f"{int(v.get('count',0))}件 / 構成比 {share*100:.1f}%", "process history", 0.3)], ["開始/終了時刻を追加するとボトルネック分析が有効になります"]))
    tables = {"工程ボトルネック": _html(pd.DataFrame(bottlenecks)), "工程variant": _html(pd.DataFrame(snap.get("variants", [])))}
    return candidates, summary, tables


def _maintenance_candidates(df: pd.DataFrame) -> tuple[list[Candidate], list[str], dict[str, str]]:
    m = df.copy()
    if "timestamp" in m.columns: m["timestamp"] = pd.to_datetime(m["timestamp"], errors="coerce")
    if "equipment_id" not in m.columns:
        return [], ["保全履歴はありますが設備IDを特定できません。"], {}
    summary = [f"保全履歴 {len(m)}件を単独分析します。設備ログが無くても頻出・再発傾向を整理できます。"]
    rows=[]; candidates=[]
    grouped=m.groupby("equipment_id")
    max_count=max([len(g) for _,g in grouped] or [1])
    for eq,g in grouped:
        count=len(g); issues=[str(x) for x in g.get("issue", pd.Series(dtype=str)).dropna().tolist()]
        common=Counter(issues).most_common(1)[0][0] if issues else "保全イベント"
        recurrence=Counter(issues).most_common(1)[0][1] if issues else count
        score=float(np.clip(0.25 + 0.45*count/max_count + 0.30*recurrence/max(count,1),0,0.95))
        latest=g.sort_values("timestamp").iloc[-1] if "timestamp" in g.columns and g["timestamp"].notna().any() else g.iloc[-1]
        src=", ".join(sorted(set(g.get("_source_file", pd.Series(dtype=str)).dropna().astype(str)))) or "maintenance"
        evidence=[Evidence("maintenance", f"保全 {count}件 / 最頻現象 {common} ({recurrence}件) / 直近 {latest.get('issue', common)}", src, score)]
        candidates.append(Candidate(f"{eq}: {common}の再発確認", score, "maintenance", evidence, ["直近対策後に同現象が再発していないか確認", "設備ログ追加時は保全前後のセンサ変化を自動比較"]))
        rows.append({"equipment_id":eq,"events":count,"most_common_issue":common,"repeat_count":recurrence,"priority":score})
    candidates.sort(key=lambda c:c.score, reverse=True)
    return candidates[:8], summary, {"保全履歴サマリー":_html(pd.DataFrame(rows).sort_values("priority",ascending=False))}


def _parts_candidates(df: pd.DataFrame, question: str) -> tuple[list[Candidate], list[str], dict[str, str], str | None]:
    p=df.copy(); vehicle=None
    if "vehicle_id" in p.columns:
        p["vehicle_id"]=p["vehicle_id"].astype(str).str.strip().str.upper().str.replace("_","-",regex=False)
        q=question.upper().replace("_","-")
        for vid in sorted(p["vehicle_id"].dropna().unique(), key=len, reverse=True):
            if str(vid) in q: vehicle=str(vid); break
    summary=[f"部品ロットデータ {len(p)}行を単独でトレーサビリティ表示します。品質データが追加されればロット別NG率を自動比較できます。"]
    candidates=[]
    if vehicle and "vehicle_id" in p.columns:
        rows=p[p["vehicle_id"]==vehicle]
        lots=rows.get("part_lot",pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
        summary.append(f"対象 {vehicle} のロット: {', '.join(lots) if lots else '記録なし'}")
        for lot in lots[:6]:
            candidates.append(Candidate(f"部品ロット {lot}",0.35,"part_trace",[Evidence("part_trace",f"{vehicle} にロット {lot} が紐付いています。","parts",0.35)],["品質データ追加時に同ロットのNG率と他ロットを比較"]))
    elif "part_lot" in p.columns:
        counts=p["part_lot"].dropna().astype(str).value_counts()
        for lot,count in counts.head(5).items():
            candidates.append(Candidate(f"部品ロット {lot}",0.18,"part_trace",[Evidence("part_trace",f"{int(count)}レコードで使用されています。品質との良否関連は未評価です。","parts",0.18)],["製品IDで対象ロットを追跡", "品質データ追加時にロット別NG率を比較"]))
    tables={"部品ロット":_html(p[[c for c in ["vehicle_id","part_no","part_lot","timestamp"] if c in p.columns]].head(30))}
    return candidates,summary,tables,vehicle


def analyze_available(question: str, data_dir: Path) -> AnalysisResult:
    capabilities = detect_capabilities(data_dir)
    frames, labels, warnings = _frames(data_dir)
    signals = capabilities["signals"]
    qlow = question.lower()
    candidates: list[Candidate]=[]; summary=[]; tables={}; active=[]; vehicle=None; defect=None

    wants_sensor = any(k in qlow for k in ["設備","センサ","振動","温度","電流","異常"])
    wants_process = any(k in qlow for k in ["工程","ボトルネック","サイクル","滞留","逸脱"])
    wants_maint = any(k in qlow for k in ["保全","故障","修理","メンテ"])
    wants_quality = any(k in qlow for k in ["品質","ng","不良","不具合","検査"])
    wants_parts = any(k in qlow for k in ["部品","ロット","lot"])
    explicit = wants_sensor or wants_process or wants_maint or wants_quality or wants_parts

    if signals["quality"] and (wants_quality or not explicit):
        cs,ss,tt,v,d=_quality_candidates(frames["quality"],question); candidates+=cs; summary+=ss; tables.update(tt); vehicle=vehicle or v; defect=defect or d; active.append("quality_trends")
        if signals["parts"]:
            pcs, ptt = _quality_parts_candidates(frames["quality"], frames["parts"]); candidates += pcs; tables.update(ptt)
            if pcs: active.append("quality_lot")
    if signals["equipment_logs"] and (wants_sensor or not explicit):
        cs,ss,tt=_sensor_candidates(data_dir)
        if signals["maintenance"]:
            m=frames["maintenance"]
            for c in cs:
                eq=c.label.split(":",1)[0]
                rows=m[m["equipment_id"].astype(str)==str(eq)] if "equipment_id" in m.columns else pd.DataFrame()
                if not rows.empty:
                    r=rows.iloc[-1]; issue=str(r.get("issue","保全履歴あり")); src=", ".join(sorted(set(rows.get("_source_file",pd.Series(dtype=str)).dropna().astype(str)))) or "maintenance"
                    c.evidence.append(Evidence("maintenance",f"直近保全: {issue}",src,0.5)); c.score=min(0.99,c.score+0.06)
            if cs: active.append("maintenance_intelligence")
        candidates+=cs; summary+=ss; tables.update(tt); active.append("sensor_monitoring")
    if signals["process"] and (wants_process or not explicit):
        cs,ss,tt=_process_candidates(data_dir,question); candidates+=cs; summary+=ss; tables.update(tt); active.append("process_intelligence")
    if signals["maintenance"] and (wants_maint or not explicit):
        cs,ss,tt=_maintenance_candidates(frames["maintenance"]); candidates+=cs; summary+=ss; tables.update(tt); active.append("maintenance_intelligence")
    if signals["parts"] and (wants_parts or (not explicit and not candidates)):
        cs,ss,tt,v=_parts_candidates(frames["parts"],question); candidates+=cs; summary+=ss; tables.update(tt); vehicle=vehicle or v; active.append("part_traceability")

    candidates.sort(key=lambda c:c.score,reverse=True); candidates=candidates[:8]
    if signals["documents"]:
        active.append("rag_assistant")
        summary.append("文書検索も有効です。関連PDF/Word/Markdown/TXTをRAGで同時検索します。")
    if signals["vision"]:
        active.append("vision_inspection")
        summary.append("Vision AIは独立稼働可能です。カメライベントは設備ID/製品IDが一致すれば追加根拠になります。")
    if signals["acoustic"]:
        active.append("acoustic_monitoring")
        summary.append("設備音AIも利用可能です。音響結果は工程・品質データが無くても単独表示できます。")
    if not summary:
        summary=["分析可能な構造化データはまだありません。PDF等があればRAG、カメラ設定があればVisionを個別に利用できます。"]
    if warnings: summary.append("読込警告: "+" / ".join(warnings[:2]))

    if candidates:
        summary.append(f"現在あるデータだけでの最優先確認候補: {candidates[0].label}（{candidates[0].score*100:.0f}/100。異種モジュール間のスコアは参考指標です）")
    missing=[]
    if not signals["quality"]: missing.append("品質データ")
    if not signals["process"]: missing.append("工程履歴")
    title="利用可能データによる自動分析"
    if active==["rag_assistant"] or (not candidates and signals["documents"]): title="現場文書検索アシスタント"
    elif "sensor_monitoring" in active and len(active)<=3: title="設備異常監視モード"
    elif "quality_trends" in active and not signals["process"]: title="品質傾向分析モード"
    elif "process_intelligence" in active and not signals["quality"]: title="工程分析モード"

    return AnalysisResult(title=title, vehicle_id=vehicle, defect_type=defect, summary=summary, candidates=candidates, scenarios=[], tables=tables, graph_nodes=[], graph_edges=[], data_roles=labels, mode="adaptive", active_modules=list(dict.fromkeys(active)), missing_for_deeper=missing)
