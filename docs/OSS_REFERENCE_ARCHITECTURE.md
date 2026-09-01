# OSS Reference Architecture

The commercial value should live in manufacturing semantics and investigation workflow, not in reimplementing infrastructure.

| Need | Reference OSS | How this project uses / mirrors it |
|---|---|---|
| Industrial visual anomaly detection | open-edge-platform/anomalib | optional image-anomaly hook; Apache-2.0 reference |
| Vector retrieval | qdrant/qdrant | optional Qdrant backend; Apache-2.0 |
| Model lifecycle / lineage | mlflow/mlflow | recommended enterprise model registry integration; Apache-2.0 |
| IAM / SSO | keycloak/keycloak | OIDC token verification hook and example realm |
| Telemetry | prometheus/prometheus | /metrics endpoint and example scrape config |
| Distributed tracing | open-telemetry/opentelemetry-python | optional enterprise dependency / future instrumentation |
| Industrial flows | node-red/node-red | optional integration flow for shop-floor orchestration |
| HMI / SCADA concepts | frangoteam/FUXA | UI and connector reference; no FUXA code bundled |
| Industrial IoT platform concepts | thingsboard/thingsboard | device/telemetry integration reference; no code bundled |
| RAG + predictive-maintenance integration | zervakisai/smart-factory-rag | architecture reference; MIT at time checked |
| Edge anomaly patterns | validatedpatterns/edge-anomaly-detection | deployment-pattern reference |

Before commercial redistribution, run a dependency/license scan against the exact versions actually shipped. Do not rely only on this document.
