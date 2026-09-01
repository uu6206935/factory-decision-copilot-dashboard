# Third-party / OSS references

No external repository source tree is vendored wholesale in this package. The product uses Python packages at install time and contains integration hooks / architecture patterns inspired by established OSS projects.

Projects reviewed while designing this release candidate include:

- `open-edge-platform/anomalib` — industrial anomaly detection — Apache-2.0 at time checked.
- `qdrant/qdrant` — vector database — Apache-2.0 at time checked.
- `mlflow/mlflow` — model tracking / registry — Apache-2.0 at time checked.
- `keycloak/keycloak` — identity and access management.
- `prometheus/prometheus` — metrics / monitoring.
- `open-telemetry/opentelemetry-python` — tracing/telemetry patterns.
- `node-red/node-red` — flow-based integration patterns.
- `frangoteam/FUXA` — industrial HMI/SCADA patterns.
- `thingsboard/thingsboard` — industrial IoT/device platform patterns.
- `zervakisai/smart-factory-rag` — manufacturing RAG + predictive maintenance architecture — MIT at time checked.
- `validatedpatterns/edge-anomaly-detection` — edge anomaly-deployment patterns.

For commercial shipping, generate an SBOM and verify the license of the exact dependency versions and container images included in your release. License status can change between repositories, branches, versions, and enterprise editions.


## UI references reviewed for this release

- `tabler/tabler` and `tabler/tabler-starter` — MIT. Reviewed and reused as a reference for the application shell, page-header/card hierarchy, responsive dashboard conventions, and dense enterprise information layout.
- `ColorlibHQ/AdminLTE` — MIT. Reviewed for admin sidebar, KPI-card, status and engineering-console patterns.
- `frangoteam/FUXA` — MIT. Reviewed for operator-first industrial HMI/SCADA information density and status presentation.
- `thingsboard/thingsboard` — Apache-2.0. Reviewed for device/data/operations separation and IoT operations navigation.

The shipped UI assets in `app/static/` are local to this project; no CDN is required at runtime. If exact third-party UI assets are later vendored, retain the corresponding license/NOTICE files and verify the exact version before commercial distribution.

## AI / vision references checked for 1.2.0

The following projects were reviewed for the AI modules. Exact version/tag licensing must be rechecked during release engineering.

- `Megvii-BaseDetection/YOLOX` — Apache-2.0. Portions of the preprocessing, output decode and NMS logic in `app/vision/yolox_onnx.py` are adapted from the upstream reference implementation. Preserve the upstream copyright/license notice when distributing that portion.
- `opencv/opencv` — Apache-2.0. Runtime camera/image processing and OpenCV DNN.
- `roboflow/supervision` — MIT. Optional ByteTrack / CV utilities.
- `open-edge-platform/anomalib` — Apache-2.0. Optional visual anomaly sidecar.
- `PaddlePaddle/PaddleOCR` — Apache-2.0. Optional OCR.
- `microsoft/onnxruntime` — MIT. Optional ONNX runtime.
- `openvinotoolkit/openvino` — Apache-2.0. Optional edge acceleration.
- `online-ml/river` — BSD-3-Clause. Optional streaming anomaly detection.
- `yzhao062/pyod` — BSD-2-Clause. Optional outlier algorithms.
- `google/or-tools` — Apache-2.0. Optional CP-SAT maintenance optimization.
- `py-why/dowhy` — MIT. Optional causal inference, only when causal assumptions are supplied and validated.
- `evidentlyai/evidently` — Apache-2.0. Optional data/model drift reports.
- `duckdb/duckdb` — MIT. Optional embedded analytics path.
- `apache/iotdb` — Apache-2.0. External time-series platform candidate.
- `sktime/sktime` — BSD-3-Clause. Optional forecasting/RUL candidate.
- `HumanSignal/label-studio` — Apache-2.0. External annotation/review tool.
- `cvat-ai/cvat` — MIT. External image/video annotation tool.

### Deliberately not bundled by default

- `ultralytics/ultralytics` — the open-source repository was AGPL-3.0 when checked. An optional adapter exists, but a proprietary commercial deployment must use terms appropriate to the deployment (for example an applicable commercial license) rather than silently treating the package as permissive.
- `process-intelligence-solutions/pm4py` — AGPL-3.0 when checked. This product ships a small built-in process-variant/bottleneck implementation instead of bundling PM4Py into the proprietary core.
