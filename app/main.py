from __future__ import annotations

from pathlib import Path
import json
import re
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config import APP_NAME, APP_VERSION, AUTH_MODE, DATA_DIR, LLM_MODE, VECTOR_BACKEND, FILE_ALLOWLIST, MAX_FILE_MB, RUNTIME_DIR, DEEPSEEK_MODEL
from .capabilities import preferred_prompt
from .database import init_db, log_audit, recent_audit, recent_cases, recent_review_items, recent_vision_events
from .metrics import INGEST_COUNT
from .platform import catalog_payload, get_state, rebuild
from .security import UserContext, current_user, require_role
from .schema import ALIASES, DISPLAY_LABELS, ROLE_REQUIRED, save_join_review, save_schema_review
from .service import run_analysis
from .dashboard_data import production_dashboard_data, equipment_monitor_data, bolt_torque_data, line_list_data, machine_learning_data
from .ai_modules import intelligence_snapshot, module_status
from .process_intelligence import process_snapshot
from .sensor_ai import equipment_health
from .optimization import plan_from_health
from .drift_ai import drift_snapshot
from .acoustic_ai import snapshot as acoustic_snapshot
from .predictive_ai import threshold_forecast
from .vision import analyze_image_bytes, capture_once, load_cameras, vision_dashboard
from .vision.service import VISION_DIR
from .deepseek import status as deepseek_status
from .approval_center import decorate_catalog
from .lineage import build_lineage
from .markdown_utils import render_markdown
from .i18n import ja_role, ja_status, ja_mode, ja_semantic_type, ja_dtype, ja_join_mode, ja_kind, ja_signal, ja_data_quality_key, ja_reason, ja_term, ja_terms, ja_mapping

init_db()

BASE_DIR = Path(__file__).resolve().parent
LAST_INGEST_ANALYSIS = RUNTIME_DIR / "last_ingest_analysis.json"


def _last_ingest_analysis():
    if not LAST_INGEST_ANALYSIS.exists():
        return None
    try:
        return json.loads(LAST_INGEST_ANALYSIS.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_upload_name(name: str) -> str:
    base = Path(name or "upload.bin").name
    stem = re.sub(r"[^0-9A-Za-zぁ-んァ-ヶ一-龠ー._ -]+", "_", Path(base).stem).strip(" ._") or "upload"
    suffix = Path(base).suffix.lower()
    return stem[:100] + suffix


def _governed_catalog() -> dict:
    return decorate_catalog(catalog_payload())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    rebuild(save=True)
    yield

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="製造品質の根拠ベース原因調査・意思決定支援",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/runtime-assets", StaticFiles(directory=str(VISION_DIR)), name="runtime-assets")

@app.middleware("http")
async def disable_ui_cache(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path.startswith("/runtime-assets/"):
        # Static assets are cache-busted via an explicit ?v= query param on every
        # reference (see base.html), so they are safe to cache aggressively.
        # This is what makes page-to-page navigation feel instant: without it the
        # browser re-downloads the full CSS/JS bundle on every single screen.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path in {"/", "/investigate", "/onboarding", "/equipment", "/equipment/bolt-torque", "/equipment/lines", "/equipment/machine-learning", "/intelligence", "/data-map"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters.update({
    "markdown": render_markdown,
    "ja_role": ja_role,
    "ja_status": ja_status,
    "ja_mode": ja_mode,
    "ja_semantic_type": ja_semantic_type,
    "ja_dtype": ja_dtype,
    "ja_join_mode": ja_join_mode,
    "ja_kind": ja_kind,
    "ja_signal": ja_signal,
    "ja_data_quality_key": ja_data_quality_key,
    "ja_reason": ja_reason,
    "ja_term": ja_term,
    "ja_terms": ja_terms,
    "ja_mapping": ja_mapping,
})


def ctx(active_page: str = "dashboard", **kwargs):
    s = get_state()
    base = {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "auth_mode": AUTH_MODE,
        "vector_backend": s.retriever.backend,
        "llm_mode": LLM_MODE,
        "llm_model": DEEPSEEK_MODEL,
        "deepseek": deepseek_status(),
        "data_dir": str(DATA_DIR),
        "file_count": len(s.file_catalog),
        "table_count": len(s.profiles),
        "chunk_count": len(s.chunks),
        "warnings": s.warnings,
        "data_quality": s.data_quality,
        "capabilities": s.capabilities,
        "question": preferred_prompt(s.capabilities),
        "answer": None,
        "result": None,
        "case_id": None,
        "active_page": active_page,
        "canonical_fields": [(k, DISPLAY_LABELS.get(k, k)) for k in ALIASES],
        "role_options": list(ROLE_REQUIRED),
    }
    base.update(kwargs)
    return base


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="production_dashboard.html",
        context=ctx("dashboard", dashboard=production_dashboard_data()),
    )


@app.get("/equipment", response_class=HTMLResponse)
def equipment_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="equipment_monitor.html",
        context=ctx("equipment", equipment=equipment_monitor_data()),
    )


@app.get("/equipment/bolt-torque", response_class=HTMLResponse)
def equipment_bolt_torque_page(request: Request):
    data = bolt_torque_data()
    return templates.TemplateResponse(
        request=request,
        name="bolt_torque.html",
        context=ctx(
            "bolt_torque",
            prediction=data["prediction"],
            factors=data["factors"],
            torque_series=data["torque_series"],
            angle_series=data["angle_series"],
        ),
    )


@app.get("/equipment/lines", response_class=HTMLResponse)
def equipment_line_list_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="line_list.html",
        context=ctx("line_list", data=line_list_data()),
    )


@app.get("/equipment/machine-learning", response_class=HTMLResponse)
def equipment_machine_learning_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="machine_learning.html",
        context=ctx("machine_learning", ml=machine_learning_data()),
    )


@app.get("/coming-soon", response_class=HTMLResponse)
def coming_soon_page(request: Request):
    label = request.query_params.get("label") or "準備中の画面"
    return templates.TemplateResponse(
        request=request,
        name="coming_soon.html",
        context=ctx("coming_soon", label=label),
    )


@app.get("/investigate", response_class=HTMLResponse)
def investigate(request: Request):
    question = request.query_params.get("q") or preferred_prompt(get_state().capabilities)
    return templates.TemplateResponse(
        request=request,
        name="investigate.html",
        context=ctx("investigate", question=question),
    )


@app.post("/ask", response_class=HTMLResponse)
def ask(request: Request, question: str = Form(...), user: UserContext = Depends(current_user)):
    payload = run_analysis(question, actor=user.subject, use_llm=True)
    return templates.TemplateResponse(
        request=request,
        name="investigate.html",
        context=ctx(
            "investigate",
            question=question,
            answer=payload.get("answer"),
            result=payload,
            case_id=payload.get("case_id"),
        ),
    )


@app.get("/data", response_class=HTMLResponse)
def data_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="data.html",
        context=ctx("data", catalog=catalog_payload()),
    )


@app.get("/onboarding", response_class=HTMLResponse)
def onboarding_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context=ctx("onboarding", catalog=_governed_catalog(), auto_analysis=_last_ingest_analysis()),
    )


@app.post("/onboarding/upload")
async def onboarding_upload(files: list[UploadFile] = File(...), user: UserContext = Depends(require_role("engineer"))):
    target = DATA_DIR / "uploads"
    target.mkdir(parents=True, exist_ok=True)
    saved = []
    rejected = []
    for upload in files:
        name = _safe_upload_name(upload.filename or "upload.bin")
        suffix = Path(name).suffix.lower()
        if suffix not in FILE_ALLOWLIST:
            rejected.append({"file": name, "reason": "extension not allowed"})
            continue
        data = await upload.read()
        if len(data) > MAX_FILE_MB * 1024 * 1024:
            rejected.append({"file": name, "reason": f"larger than {MAX_FILE_MB}MB"})
            continue
        dest = target / name
        if dest.exists():
            dest = target / f"{dest.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{dest.suffix}"
        dest.write_bytes(data)
        saved.append(str(dest.relative_to(DATA_DIR)))
    state = rebuild(save=True)
    auto = None
    if state.capabilities.get("ready"):
        try:
            prompt = preferred_prompt(state.capabilities)
            auto = run_analysis(prompt, actor=user.subject, use_llm=True)
            LAST_INGEST_ANALYSIS.write_text(json.dumps(auto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        except Exception as exc:
            auto = {"error": str(exc)}
            LAST_INGEST_ANALYSIS.write_text(json.dumps(auto, ensure_ascii=False, indent=2), encoding="utf-8")
    log_audit(user.subject, "onboarding.upload", {"saved": saved, "rejected": rejected, "active_modules": state.capabilities.get("active_modules", [])})
    return RedirectResponse(url=f"/onboarding?uploaded={len(saved)}#discovery", status_code=303)


@app.post("/onboarding/schema-review")
async def onboarding_schema_review(request: Request, user: UserContext = Depends(require_role("engineer"))):
    form = await request.form()
    table_key = str(form.get("table_key") or "")
    role = str(form.get("role") or "") or None
    learn = str(form.get("learn") or "").lower() in {"1", "true", "on", "yes"}
    mapping = {}
    for key, value in form.multi_items():
        if not str(key).startswith("raw_"):
            continue
        idx = str(key).split("_", 1)[1]
        raw = str(value)
        canonical = str(form.get(f"canonical_{idx}") or "") or None
        mapping[raw] = canonical
    save_schema_review(table_key, mapping, role=role, learn=learn)
    state = rebuild(save=True)
    log_audit(user.subject, "schema.review", {"table_key": table_key, "mapping": mapping, "role": role, "learn": learn, "active_modules": state.capabilities.get("active_modules", [])})
    return RedirectResponse(url="/onboarding#schema", status_code=303)


@app.post("/onboarding/join-review")
async def onboarding_join_review(request: Request, user: UserContext = Depends(require_role("engineer"))):
    form = await request.form()
    join_id = str(form.get("join_id") or "")
    accepted = str(form.get("accepted") or "true").lower() in {"1", "true", "on", "yes"}
    save_join_review(join_id, accepted)
    rebuild(save=False)
    log_audit(user.subject, "join.review", {"join_id": join_id, "accepted": accepted})
    return RedirectResponse(url="/onboarding#joins", status_code=303)


@app.get("/data-map", response_class=HTMLResponse)
def data_map_page(request: Request):
    catalog = _governed_catalog()
    lineage = build_lineage(catalog, get_state().capabilities)
    return templates.TemplateResponse(
        request=request,
        name="data_map.html",
        context=ctx("data_map", catalog=catalog, lineage=lineage),
    )


@app.get("/cases-ui", response_class=HTMLResponse)
def cases_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="cases.html",
        context=ctx("cases", cases=recent_cases(100)),
    )


@app.get("/engineering", response_class=HTMLResponse)
def engineering_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="engineering.html",
        context=ctx("engineering"),
    )


@app.get("/vision", response_class=HTMLResponse)
def vision_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="vision.html",
        context=ctx("vision", vision=vision_dashboard(), review_items=recent_review_items(30)),
    )


@app.post("/vision/capture/{camera_id}")
def vision_capture_ui(camera_id: str, user: UserContext = Depends(require_role("engineer"))):
    result = capture_once(camera_id, actor=user.subject)
    log_audit(user.subject, "vision.capture", {"camera_id": camera_id, "events": len(result.events)}, "camera", camera_id)
    return RedirectResponse(url="/vision", status_code=303)


@app.get("/intelligence", response_class=HTMLResponse)
def intelligence_page(request: Request):
    target = request.query_params.get("target") or "QV-017"
    return templates.TemplateResponse(
        request=request,
        name="intelligence.html",
        context=ctx("intelligence", target_id=target, intelligence=intelligence_snapshot(target)),
    )


@app.post("/reload")
def reload_ui(user: UserContext = Depends(require_role("engineer"))):
    try:
        rebuild(save=True)
        INGEST_COUNT.labels(status="ok").inc()
        log_audit(user.subject, "ingest.reload", {"data_dir": str(DATA_DIR)})
    except Exception:
        INGEST_COUNT.labels(status="error").inc()
        raise
    return RedirectResponse(url="/data", status_code=303)


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": APP_VERSION}


@app.get("/readyz")
def readyz():
    s = get_state()
    return {
        "ready": bool(s.capabilities.get("ready")),
        "files": len(s.file_catalog),
        "tables": len(s.profiles),
        "chunks": len(s.chunks),
        "retrieval_backend": s.retriever.backend,
        "active_modules": s.capabilities.get("active_modules", []),
        "capabilities": s.capabilities,
    }


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/capabilities")
def api_capabilities(user: UserContext = Depends(require_role("viewer"))):
    """Return the auto-detected data signals and modules currently enabled."""
    return JSONResponse(get_state().capabilities)


@app.get("/api/v1/deepseek/status")
def api_deepseek_status(user: UserContext = Depends(require_role("viewer"))):
    """Return provider/model/data-policy status without ever returning the API key."""
    return JSONResponse(deepseek_status())


@app.get("/api/v1/schema-intelligence")
def api_schema_intelligence(user: UserContext = Depends(require_role("viewer"))):
    payload = catalog_payload()
    return {"summary": payload.get("schema_summary"), "tables": payload.get("tables"), "joins": payload.get("joins"), "capabilities": payload.get("capabilities")}


@app.get("/api/v1/joins")
def api_joins(user: UserContext = Depends(require_role("viewer"))):
    return {"items": get_state().joins}


@app.post("/api/v1/schema-review")
async def api_schema_review(request: Request, user: UserContext = Depends(require_role("engineer"))):
    body = await request.json()
    table_key = str(body.get("table_key") or "")
    mapping = body.get("mapping") or {}
    role = body.get("role")
    learn = bool(body.get("learn", True))
    save_schema_review(table_key, mapping, role=role, learn=learn)
    state = rebuild(save=True)
    log_audit(user.subject, "schema.review.api", {"table_key": table_key, "role": role, "learn": learn})
    return {"ok": True, "capabilities": state.capabilities, "catalog": catalog_payload()}


@app.post("/api/v1/join-review")
async def api_join_review(request: Request, user: UserContext = Depends(require_role("engineer"))):
    body = await request.json()
    join_id = str(body.get("join_id") or "")
    accepted = bool(body.get("accepted", True))
    save_join_review(join_id, accepted)
    state = rebuild(save=False)
    log_audit(user.subject, "join.review.api", {"join_id": join_id, "accepted": accepted})
    return {"ok": True, "joins": state.joins}


@app.get("/api/v1/lineage")
def api_lineage(user: UserContext = Depends(require_role("viewer"))):
    return build_lineage(_governed_catalog(), get_state().capabilities)


@app.get("/api/v1/catalog")
def api_catalog(user: UserContext = Depends(require_role("viewer"))):
    log_audit(user.subject, "catalog.read", {})
    return JSONResponse(catalog_payload())


@app.get("/api/v1/data-quality")
def api_data_quality(user: UserContext = Depends(require_role("viewer"))):
    return JSONResponse(get_state().data_quality)


@app.post("/api/v1/ingest/scan")
def api_ingest(user: UserContext = Depends(require_role("engineer"))):
    try:
        s = rebuild(save=True)
        INGEST_COUNT.labels(status="ok").inc()
        log_audit(
            user.subject,
            "ingest.scan",
            {"snapshot_id": s.snapshot_id, "files": len(s.file_catalog), "tables": len(s.profiles), "chunks": len(s.chunks)},
        )
        return {"ok": True, "snapshot_id": s.snapshot_id, "files": len(s.file_catalog), "tables": len(s.profiles), "chunks": len(s.chunks), "backend": s.retriever.backend}
    except Exception:
        INGEST_COUNT.labels(status="error").inc()
        raise


@app.post("/api/v1/analyze")
async def api_analyze(request: Request, user: UserContext = Depends(require_role("engineer"))):
    body = await request.json()
    question = str(body.get("question") or "品質異常の原因候補を調べて")
    return JSONResponse(run_analysis(question, actor=user.subject, use_llm=bool(body.get("use_llm", True))))


@app.get("/api/v1/cases")
def api_cases(limit: int = 50, user: UserContext = Depends(require_role("viewer"))):
    return {"items": recent_cases(max(1, min(limit, 200)))}


@app.get("/api/v1/audit")
def api_audit(limit: int = 100, user: UserContext = Depends(require_role("admin"))):
    return {"items": recent_audit(max(1, min(limit, 500)))}


@app.get("/api/v1/vision/cameras")
def api_vision_cameras(user: UserContext = Depends(require_role("viewer"))):
    return {"items": [{"id": c.id, "name": c.name, "equipment_id": c.equipment_id, "source": c.source, "detector": c.detector, "enabled": c.enabled} for c in load_cameras()]}


@app.post("/api/v1/vision/capture/{camera_id}")
def api_vision_capture(camera_id: str, user: UserContext = Depends(require_role("engineer"))):
    result = capture_once(camera_id, actor=user.subject)
    log_audit(user.subject, "vision.capture", {"camera_id": camera_id, "events": len(result.events)}, "camera", camera_id)
    return result.as_dict()


@app.post("/api/v1/vision/analyze-image/{camera_id}")
async def api_vision_analyze_image(camera_id: str, image: UploadFile = File(...), user: UserContext = Depends(require_role("engineer"))):
    data = await image.read()
    if len(data) > 25 * 1024 * 1024:
        return JSONResponse({"error": "image too large"}, status_code=413)
    result = analyze_image_bytes(camera_id, data, actor=user.subject)
    log_audit(user.subject, "vision.upload_analyze", {"camera_id": camera_id, "filename": image.filename, "events": len(result.events)}, "camera", camera_id)
    return result.as_dict()


@app.get("/api/v1/vision/events")
def api_vision_events(limit: int = 100, user: UserContext = Depends(require_role("viewer"))):
    return {"items": recent_vision_events(max(1, min(limit, 500)))}


@app.get("/api/v1/vision/review-queue")
def api_vision_review(limit: int = 100, user: UserContext = Depends(require_role("engineer"))):
    return {"items": recent_review_items(max(1, min(limit, 500)))}


@app.get("/api/v1/intelligence/modules")
def api_modules(user: UserContext = Depends(require_role("viewer"))):
    return module_status()


@app.get("/api/v1/intelligence/sensor-health")
def api_sensor_health(user: UserContext = Depends(require_role("viewer"))):
    return {"items": [x.as_dict() for x in equipment_health(DATA_DIR)]}


@app.get("/api/v1/intelligence/process")
def api_process(target_id: str | None = None, user: UserContext = Depends(require_role("viewer"))):
    return process_snapshot(DATA_DIR, target_id)


@app.get("/api/v1/intelligence/maintenance-plan")
def api_maintenance_plan(technicians: int = 1, user: UserContext = Depends(require_role("engineer"))):
    health = [x.as_dict() for x in equipment_health(DATA_DIR)]
    return plan_from_health(health, technicians=max(1, min(technicians, 20)))


@app.get("/api/v1/intelligence/drift")
def api_drift(user: UserContext = Depends(require_role("viewer"))):
    return drift_snapshot(DATA_DIR)


@app.get("/api/v1/intelligence/acoustic")
def api_acoustic(user: UserContext = Depends(require_role("viewer"))):
    return acoustic_snapshot(DATA_DIR)


@app.get("/api/v1/intelligence/predictive")
def api_predictive(horizon_min: int = 480, user: UserContext = Depends(require_role("viewer"))):
    return threshold_forecast(DATA_DIR, horizon_min=max(30, min(horizon_min, 10080)))


# compatibility endpoints for the original demo
@app.get("/schema")
def legacy_schema(user: UserContext = Depends(require_role("viewer"))):
    return JSONResponse(catalog_payload())


@app.get("/health")
def legacy_health():
    payload = readyz()
    payload["ok"] = True
    return payload


@app.post("/api/analyze")
async def legacy_analyze(request: Request, user: UserContext = Depends(require_role("engineer"))):
    return await api_analyze(request, user)
