from __future__ import annotations

import html
import time
from dataclasses import asdict

from .analysis import analyze
from .config import DATA_DIR, REDACT_BEFORE_LLM
from .database import log_audit, save_case
from .llm import available as llm_available, rewrite_retrieval_query, synthesize
from .metrics import ANALYSIS_COUNT, ANALYSIS_LATENCY
from .models import Evidence
from .process_intelligence import process_snapshot
from .vision.service import evidence_for as vision_evidence_for
from .platform import get_state
from .redaction import redact



def enrich_with_multimodal_evidence(result):
    """Merge live vision and process-intelligence evidence into the ranked investigation."""
    equipment_ids = [c.label.split(":", 1)[0].strip() for c in result.candidates if c.category == "equipment"]
    vision_events = vision_evidence_for(result.vehicle_id, equipment_ids, limit=40)
    if vision_events:
        for ev in vision_events:
            eq = str(ev.get("equipment_id") or "")
            target = next((c for c in result.candidates if c.category == "equipment" and c.label.startswith(eq + ":")), None)
            if target is None:
                continue
            severity = str(ev.get("severity") or "warning").lower()
            strength = 0.90 if severity in {"critical", "high"} else 0.65
            target.evidence.append(Evidence(
                kind="vision",
                text=f"{ev.get('camera_id')}: {ev.get('message')}",
                source=f"vision_event#{ev.get('id')} / {ev.get('snapshot_path')}",
                strength=strength,
            ))
            target.score = min(0.99, target.score + (0.10 if strength >= 0.9 else 0.05))
            if "カメラ" not in " ".join(target.recommended_checks):
                target.recommended_checks.append("カメラ検知スナップショットと現物を照合し、誤検知/見逃しを確認")
        result.candidates.sort(key=lambda c: c.score, reverse=True)
        result.summary.append(f"画像/カメラ異常イベント {len(vision_events)}件を原因候補の根拠に統合しました。")
    proc = process_snapshot(DATA_DIR, result.vehicle_id)
    if proc.get("available") and result.vehicle_id:
        dev = next((x for x in proc.get("deviations", []) if str(x.get("target_id", "")).upper() == str(result.vehicle_id).upper()), None)
        if dev:
            result.summary.append("工程順序の逸脱候補あり: " + str(dev.get("path")))
    return vision_events, proc

def structured_as_text(result) -> str:
    lines=list(result.summary)
    for i,c in enumerate(result.candidates,1):
        lines.append(f"候補 {i}: {c.label}; 優先度={c.score:.3f}; 種別={c.category}")
        lines.extend(f"- 根拠: {e.text} [参照元={e.source}]" for e in c.evidence)
        lines.extend(f"- 確認: {x}" for x in c.recommended_checks)
    for s in result.scenarios:
        lines.append(f"シナリオ {s.name}: 生産ロス={s.production_loss_units:.2f}; 想定不良数={s.expected_defects:.2f}; 損失指標={s.expected_quality_loss_index:.2f}")
    return "\n".join(lines)

def local_synthesis(result, hits) -> str:
    if not result.candidates:
        if hits:
            lines=["【利用可能データでの回答】"]
            lines.extend(f"・{s}" for s in result.summary[:6])
            lines += ["", "【関連文書】"]
            for h in hits[:6]:
                excerpt=" ".join(str(h.text).split())[:420]
                lines.append(f"・{h.source} ({h.locator}) — {excerpt}")
            lines += ["", "※ 構造化データが無い場合は文書検索として動作します。品質・工程・設備ログ等を追加すると対応する分析モジュールが自動で有効になります。"]
            return "\n".join(lines)
        return "利用可能なデータから実行できる分析はありません。データカタログにファイルを追加すると、対応するモジュールだけが自動で有効になります。"
    top=result.candidates[0]
    lines=["【観察】", *[f"・{s}" for s in result.summary if not s.startswith("最優先")], "", "【優先して確認する仮説】", f"・{top.label}（優先度 {top.score*100:.0f}/100。確率ではありません）"]
    for ev in top.evidence[:6]:
        lines.append(f"  - {ev.text} / 参照元={ev.source or '不明'}")
    lines += ["", "【次に確認すること】"] + [f"・{x}" for x in top.recommended_checks]
    if result.scenarios:
        lines += ["", "【簡易シナリオ比較】"]
        lines += [f"・{s.name}: 生産ロス {s.production_loss_units:.1f}台 / 予想NG {s.expected_defects:.1f}台 — {s.note}" for s in result.scenarios]
    if hits:
        lines += ["", "【関連文書】"] + [f"・{h.source} ({h.locator}) 類似度={h.score:.3f}" for h in hits[:5]]
    lines += ["", "※ 優先度は調査順序の指標であり真因確率ではありません。真因確定には現物確認・測定・再現・対策後確認が必要です。"]
    return "\n".join(lines)

def run_analysis(question: str, actor: str="local-demo", use_llm: bool=True) -> dict:
    t0=time.perf_counter()
    try:
        result=analyze(question, DATA_DIR)
        vision_events, process_info = enrich_with_multimodal_evidence(result)
        q=question+" "+(result.defect_type or "")
        if result.candidates:
            q += " "+result.candidates[0].label+" "+" ".join(e.text for e in result.candidates[0].evidence[:4])
        state=get_state()
        deepseek_query = None
        if use_llm and llm_available():
            try:
                base_q = redact(question) if REDACT_BEFORE_LLM else question
                context_hint = redact(structured_as_text(result)[:3500]) if REDACT_BEFORE_LLM else structured_as_text(result)[:3500]
                deepseek_query = rewrite_retrieval_query(base_q, context_hint)
            except Exception:
                deepseek_query = None
        search_q = (q + " " + deepseek_query).strip() if deepseek_query else q
        hits=state.retriever.search(search_q, top_k=8)
        local=local_synthesis(result,hits)
        answer=local
        llm_used=False
        llm_error=None
        if use_llm and llm_available():
            try:
                structured=structured_as_text(result)
                retrieved="\n\n".join(f"[{h.source} | {h.locator}]\n{h.text[:1800]}" for h in hits)
                qq=redact(question) if REDACT_BEFORE_LLM else question
                ss=redact(structured) if REDACT_BEFORE_LLM else structured
                rr=redact(retrieved) if REDACT_BEFORE_LLM else retrieved
                answer=synthesize(qq,ss,rr) or local
                llm_used=True
            except Exception as exc:
                llm_error=str(exc)
        payload=asdict(result)
        payload["retrieval"]=[{"score":h.score,"source":h.source,"locator":h.locator,"text":h.text[:1200]} for h in hits]
        payload["vision_evidence"] = vision_events
        payload["process_intelligence"] = process_info
        payload["answer"]=answer
        payload["local_summary"]=local
        payload["llm_used"]=llm_used
        payload["llm_provider"]="DeepSeek" if llm_used else None
        payload["llm_model"]="deepseek-v4-flash" if llm_used else None
        payload["retrieval_query_rewritten_by_llm"] = bool(deepseek_query)
        payload["llm_error"]=llm_error
        payload["retrieval_backend"]=state.retriever.backend
        payload["capabilities"] = state.capabilities
        top=result.candidates[0] if result.candidates else None
        case_id=save_case(actor, question, result.vehicle_id, top.label if top else None, top.score if top else None, payload)
        payload["case_id"]=case_id
        log_audit(actor,"analysis.created", {"question":question,"top_candidate":top.label if top else None,"top_score":top.score if top else None,"retrieved_sources":[h.source for h in hits]}, "case", str(case_id))
        ANALYSIS_COUNT.labels(status="ok").inc()
        return payload
    except Exception as exc:
        ANALYSIS_COUNT.labels(status="error").inc()
        log_audit(actor,"analysis.error",{"question":question,"error":str(exc)})
        raise
    finally:
        ANALYSIS_LATENCY.observe(time.perf_counter()-t0)
