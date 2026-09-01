# Enterprise Architecture

## Product boundary
Factory Decision Copilot is not a general-purpose chatbot. It orchestrates structured manufacturing data analysis, document retrieval, anomaly signals, provenance and human confirmation into an auditable investigation case.

## Logical flow
1. Ingest files / APIs / MQTT / OPC-UA.
2. Detect schemas and map heterogeneous column names to canonical manufacturing concepts.
3. Validate data quality before analysis.
4. Join product/vehicle traceability, equipment exposure, parts lots and quality outcomes.
5. Run quantitative association and sensor anomaly analysis.
6. Retrieve relevant manuals, maintenance history and prior incidents.
7. Rank investigation hypotheses with evidence; never label the score as causal probability.
8. Optionally call an approved internal OpenAI-compatible LLM for explanation only.
9. Persist case, audit trail and evidence sources.
10. Export through REST API for MES/QMS/BI integration.

## Deployment modes
- Laptop/PoC: SQLite + local TF-IDF, LLM off.
- Plant server: PostgreSQL + Qdrant, internal LLM optional.
- Enterprise: OIDC/Keycloak or corporate IdP, reverse proxy/TLS, centralized logging, model registry, backups and SIEM export.

## Trust controls
- External LLM is OFF by default.
- File hashes and source metadata are cataloged.
- API roles: viewer / engineer / admin.
- Every analysis is stored as a case.
- Audit events are append-only at application level.
- Data quality gates are exposed before analysis.
