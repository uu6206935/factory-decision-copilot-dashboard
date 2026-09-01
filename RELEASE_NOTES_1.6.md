# 1.6.0 Approval Center & Data Lineage RC1

## Governance workflow
- Unified Approval Center for schema columns, inferred table roles, and JOIN candidates.
- Four states: pending, approved, held, rejected.
- Per-item actions plus bulk approve/hold/reject.
- Optional reviewer comments.
- Actor, UTC timestamp, before/after state and details persist in `runtime/approval_center.json`.
- Decisions are also written to the existing audit database.
- Approved schema decisions synchronize to Schema Memory and learned aliases.
- Rejected schema mappings are explicitly set unused; reset removes the explicit mapping and learned alias.
- Approved JOINs synchronize to accepted JOIN memory; hold/reject removes operational acceptance.

## Data Lineage Map
- Interactive five-layer graph: File → Table → Semantic Column → JOIN → Analysis Module.
- Node/edge selection detail panel.
- Search, kind/status filters, zoom and fit controls.
- Governance colors for approved/pending/held/rejected and active/waiting modules.
- File/table details include related approval history.

## APIs
- `GET /api/v1/approvals`
- `POST /api/v1/approval-action`
- `GET /api/v1/lineage`

## Compatibility
- DeepSeek V4 Flash FULL Embedded behavior is retained.
- Existing onboarding, analysis, vision, intelligence, data, cases and engineering routes remain available.
