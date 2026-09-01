# Factory Decision Copilot Enterprise — 日本語UI・Markdown表示版

品質・工程・設備・部品・保全などの分散データをつなぎ、品質トラブルを監査可能な調査ケースへ変換する製造業向け意思決定支援プラットフォームです。

**現在のビルド: v1.7.4-japanese-markdown-rc1**

**This is an enterprise-grade prototype / release candidate.** It is designed to be close to a paid-pilot starting point, not to imply production certification.

## DeepSeek V4 Flash — single LLM layer

All LLM-capable semantic reasoning is routed through **`deepseek-v4-flash` only**: schema inference, JOIN reasoning, retrieval-query expansion, RAG answers, evidence-grounded investigation explanation and post-ingest automatic analysis. Numerical statistics, Vision and optimization remain specialist engines rather than being replaced by an LLM.

This private build has DeepSeek V4 Flash configured in embedded FULL mode. The API key is stored in `.env.local` inside the package, and sample values, document text and structured evidence are enabled for DeepSeek calls.


## Zero-config Excel / CSV onboarding

The main onboarding experience is now `/onboarding`. Drop in an unfamiliar Excel/CSV and the system profiles headers, sample values, types and distributions, then infers canonical manufacturing semantics with confidence and reasoning.

Examples: `号口 -> vehicle_id`, `号機 -> equipment_id`, `結果区分 -> result`, `実測 -> value`. A single sheet can be treated as multiple compatible roles when it contains quality + process + equipment information.

The system then proposes JOINs across files, persists user-approved corrections as local schema memory, refreshes the Capability Registry and automatically runs the best currently available analysis. See `docs/ZERO_CONFIG_DATA_ONBOARDING.md`.

The local semantic engine remains the deterministic base. When a DeepSeek key is configured, DeepSeek V4 Flash augments low-confidence semantics and JOIN reasoning. Raw sample values are sent in this private FULL build.

## Adaptive data architecture

You no longer need a complete quality + process dataset to use the product. The application auto-detects what data is present and switches modules on/off independently.

Examples:

- equipment logs only -> equipment anomaly / drift / threshold forecast
- camera only -> Vision inspection
- quality only -> quality trend analysis
- process only -> bottleneck / deviation analysis
- maintenance only -> recurring issue analysis
- PDF / Word / Markdown only -> local RAG assistant
- quality + parts -> lot-quality association without process history
- quality + process -> full root-cause investigation and decision support

See `docs/ADAPTIVE_DATA_MODES.md` and `GET /api/v1/capabilities`.

## What is different from a normal RAG chatbot?

A chatbot only retrieves documents. This system first performs deterministic / statistical work:

1. identifies a product/vehicle and its quality result;
2. traces which equipment/processes it passed;
3. calculates equipment-to-NG associations;
4. checks sensor deviations around the event;
5. compares part lots;
6. retrieves maintenance history and troubleshooting documents;
7. ranks investigation hypotheses with explicit evidence;
8. compares simple stop-vs-continue scenarios;
9. optionally asks an approved internal LLM to explain the evidence;
10. stores the case and audit trail.

Scores are **investigation priority indicators, not root-cause probabilities**.

## Out-of-the-box demo

The included sample data deliberately uses mixed formats and inconsistent labels:

- Japanese Excel quality results
- CSV process traceability
- CSV sensor logs
- separate CSV part-lot data
- separate Excel maintenance history
- Markdown troubleshooting document
- text prior-incident report

The application auto-maps these to canonical concepts such as `vehicle_id`, `equipment_id`, `result`, `temperature_c`, etc.

### Windows

Double-click:

```text
setup_and_run_windows.bat
```

その後 `http://127.0.0.1:8174` を開いてください。

### macOS / Linux

```bash
./setup_and_run_mac_linux.sh
```

### Manual

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```


## Product UI

The browser UI is split by user intent rather than by backend component:

- `/` — **Operations Center**: top risks, equipment status, evidence and recent cases for supervisors/operators.
- `/investigate` — **Investigation Workspace**: natural-language investigation, ranked hypotheses, evidence chain, analysis tables and decision scenarios.
- `/cases-ui` — **Case History**: auditable record of prior investigations.
- `/onboarding` — **AI Data Onboarding**: drag/drop, schema discovery, review, JOIN discovery, automatic capability activation.
- `/data` — **Data Platform**: file catalog, SHA-256 provenance, schema mapping and data-quality gate.
- `/engineering` — **Engineering Console**: runtime configuration, health/metrics endpoints and integration surfaces.

The UI information architecture was reviewed against permissively licensed dashboard projects including Tabler / Tabler Starter and AdminLTE, plus industrial operations patterns from FUXA and ThingsBoard. The shipped browser UI is self-contained and does not require a public CDN, so the local/offline demo remains functional. See `THIRD_PARTY.md`.

## Enterprise stack

```bash
docker compose -f docker-compose.enterprise.yml up --build
```

This starts an example stack with:

- application API/UI
- PostgreSQL for cases/audit
- Qdrant retrieval backend
- Prometheus metrics
- Keycloak example IdP

The compose file keeps `AUTH_MODE=off` for a frictionless local demo. For a customer installation, put the UI behind the corporate SSO/reverse proxy and enable OIDC for API calls.

## Main APIs

- `/api/v1/schema-intelligence`
- `/api/v1/joins`
- `/api/v1/deepseek/status`
- `/api/v1/capabilities`
- `/api/v1/catalog`
- `/api/v1/data-quality`
- `/api/v1/ingest/scan`
- `/api/v1/analyze`
- `/api/v1/cases`
- `/api/v1/audit`
- `/metrics`
- `/healthz`, `/readyz`

See `docs/API.md`.

## Security defaults

- This private build includes an embedded DeepSeek API key and starts with DeepSeek V4 Flash FULL mode enabled. If the embedded configuration is removed, the application can still fall back to local analysis.
- Local analysis works without internet.
- このFULL埋め込み版では、サンプル値・文書本文・構造化根拠のDeepSeek送信が有効です。実データ利用時は所属組織の外部AI利用ルールに従ってください。
- Email/phone-like patterns are redacted before enabled LLM calls.
- File hashes are recorded in the catalog.
- API-key and OIDC RBAC hooks are included.
- Investigation and audit records are persisted.

Do not upload customer confidential data to an unapproved external AI service.

## Architecture inspiration

The project deliberately builds on established OSS patterns instead of re-inventing infrastructure: Anomalib, Qdrant, MLflow, Keycloak, Prometheus/OpenTelemetry, Node-RED, FUXA, ThingsBoard and other industrial-data projects. See `docs/OSS_REFERENCE_ARCHITECTURE.md` and `THIRD_PARTY.md`.

## Commercialization

The core differentiator should be customer-specific manufacturing semantics and workflow:

- automatic schema mapping across messy factory files;
- product/vehicle traceability graph;
- evidence-grounded root-cause investigation ranking;
- reusable adapters for QMS/MES/SCADA/PLM;
- human-in-the-loop investigation and approval.

Before selling as a production system, complete the checklist in `docs/COMMERCIALIZATION_CHECKLIST.md`.

## AI Modules 1.2

This build adds an integrated manufacturing-AI layer rather than a collection of isolated demos.

- `/vision` — camera / image inspection, snapshots, events and review queue.
- `/intelligence` — equipment health, process variants, maintenance optimization, drift and acoustic condition monitoring.
- YOLOX ONNX is the preferred permissively licensed YOLO-family integration path.
- Visual events are automatically fused into the same evidence graph used by root-cause investigation.
- Optional extensions include Supervision/ByteTrack, Anomalib, PaddleOCR, River, PyOD, OR-Tools, DoWhy, Evidently, OpenVINO, DuckDB, Label Studio and CVAT.

The included synthetic data contains a camera defect and machine-sound anomaly, so both UI paths can be demonstrated offline.

See:

- `docs/GITHUB_FEATURE_RESEARCH.md`
- `docs/VISION_AI_SETUP.md`
- `docs/AI_MODULES_ROADMAP.md`

For a full optional AI environment:

```bash
pip install -r requirements-ai.txt
```

The core demo intentionally remains smaller and does not require all optional AI packages.


## v1.6 Approval Center & Data Lineage

- `/approvals`: AI提案を1画面に集約。列意味・データ種別・JOINを **承認 / 修正 / 保留 / 却下** できます。
- 一括承認 / 一括保留 / 一括却下に対応。
- 各判断は actor、UTC timestamp、変更前後、コメントを `runtime/approval_center.json` と監査DBへ記録します。
- Schema承認はSchema Memoryへ、JOIN承認はaccepted JOINへ同期。却下した列は明示的に未使用として保存します。
- `/data-map`: **FILES → TABLES → SEMANTIC COLUMNS → JOINS → ANALYSIS** の5レイヤーLineageをインタラクティブ表示。
- ノード/エッジを選択すると、信頼度、サンプル、根拠、承認者、承認日時、関連分析を確認できます。
- `/api/v1/approvals`, `/api/v1/approval-action`, `/api/v1/lineage` を追加。
- DeepSeek V4 Flash FULL Embedded設定はv1.5系から維持しています。
