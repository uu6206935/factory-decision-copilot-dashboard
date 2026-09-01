# API

- `GET /healthz` liveness
- `GET /readyz` readiness / index status
- `GET /metrics` Prometheus metrics
- `GET /api/v1/capabilities` auto-detected data signals and enabled/disabled module registry
- `GET /api/v1/catalog` file, schema and provenance catalog
- `GET /api/v1/data-quality` ingestion quality gate
- `POST /api/v1/ingest/scan` rescan local data directory
- `POST /api/v1/analyze` adaptive analysis: routes to root-cause, quality-only, sensor-only, process-only, maintenance-only, parts-only or RAG depending on available data
- `GET /api/v1/cases` recent cases
- `GET /api/v1/audit` recent audit events (admin)

Example:

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H 'Content-Type: application/json' \
  -d '{"question":"QV-017の品質NG原因候補を調べて","use_llm":false}'
```

When `AUTH_MODE=api_key`, also send `X-API-Key`.

## Vision AI

### `GET /api/v1/vision/cameras`
Returns configured camera sources and detector configuration.

### `POST /api/v1/vision/capture/{camera_id}`
Reads one frame from an image/webcam/video/RTSP source, runs detection/tracking/OCR/rules, persists snapshots/events and returns the result.

### `POST /api/v1/vision/analyze-image/{camera_id}`
Multipart image upload into the same pipeline.

### `GET /api/v1/vision/events`
Recent persisted vision events.

### `GET /api/v1/vision/review-queue`
Low-confidence/critical frames waiting for human review.

## Process / equipment intelligence

### `GET /api/v1/intelligence/modules`
Availability and status of built-in/optional AI modules.

### `GET /api/v1/intelligence/sensor-health`
Per-equipment sensor health and interpretable signal deviations.

### `GET /api/v1/intelligence/process?target_id=QV-017`
Process path, variants, deviations and bottleneck statistics.

### `GET /api/v1/intelligence/maintenance-plan?technicians=1`
Risk-weighted maintenance schedule. Uses OR-Tools when installed and a deterministic fallback otherwise.

### `GET /api/v1/intelligence/drift`
Recent-vs-baseline equipment data drift using PSI and location/scale changes.

### `GET /api/v1/intelligence/acoustic`
Offline synthetic machine-sound demonstration of the acoustic condition-monitoring contract.

### `GET /api/v1/intelligence/predictive?horizon_min=480`
Interpretable trend-to-abnormal-band forecast. This endpoint intentionally does **not** claim failure probability or remaining useful life without labelled failure data.
