# GitHub feature research for Factory Decision Copilot

Checked for the **1.2.0-ai-modules-rc1** line.  This file separates three questions that are easy to mix up:

1. Is the idea useful in a factory?
2. Is the upstream project technically mature enough to learn from or integrate?
3. Is its open-source license comfortable for a proprietary commercial distribution?

The last answer is not legal advice. Re-check exact tags, transitive packages, model weights and enterprise terms before a customer release.

## Decision matrix

| Area | Repository | License checked | Product decision | How it maps into this project |
|---|---|---:|---|---|
| Object detection | `Megvii-BaseDetection/YOLOX` | Apache-2.0 | **Integrated adapter / preferred YOLO family path** | Camera/webcam/video/RTSP detection. The OpenCV ONNX adapter follows YOLOX preprocessing, decode and NMS logic. |
| Object detection | `ultralytics/ultralytics` | AGPL-3.0 OSS path | **Not a default proprietary dependency** | Optional adapter only. Use a suitable Ultralytics commercial license or legal approval if selected by a customer. |
| CV utilities / tracking | `roboflow/supervision` | MIT | **Optional integration** | ByteTrack, zones, counting, tracking IDs, annotation helpers. |
| Unknown visual defect detection | `open-edge-platform/anomalib` | Apache-2.0 | **Recommended sidecar** | PatchCore/EfficientAD/etc. for defects that are easier to describe as “different from normal” than as labelled YOLO classes. Automotive inspection datasets are relevant to the use case. |
| OCR | `PaddlePaddle/PaddleOCR` | Apache-2.0 | **Optional integration** | Read labels, serial numbers, lot codes and process cards. Built-in QR works without this dependency. |
| CV runtime | `opencv/opencv` | Apache-2.0 | **Core** | Camera capture, RTSP/video, QR decode, drawing and default YOLOX ONNX execution through DNN. |
| Model runtime | `microsoft/onnxruntime` | MIT | **Optional production runtime** | Provider-based CPU/GPU inference and a clean deployment contract for ONNX models. |
| Edge acceleration | `openvinotoolkit/openvino` | Apache-2.0 | **Optional production runtime** | Intel CPU/iGPU/NPU acceleration; particularly attractive for on-prem factory PCs. |
| Streaming anomaly | `online-ml/river` | BSD-3-Clause | **Optional integration** | Half-Space Trees for online equipment anomaly scoring as telemetry arrives. |
| Outlier ensemble | `yzhao062/pyod` | BSD-2-Clause | **Optional integration** | Batch / multivariate outlier models for sensor or quality feature tables. |
| Maintenance / production optimization | `google/or-tools` | Apache-2.0 | **Optional integration with built-in fallback** | CP-SAT maintenance scheduling. Current product falls back to an interpretable greedy schedule if OR-Tools is absent. |
| Causal inference | `py-why/dowhy` | MIT | **Optional guarded integration** | For validated causal DAGs / experiments. Never relabel ordinary correlation as causal evidence. |
| Data/model drift | `evidentlyai/evidently` | Apache-2.0 | **Optional integration + built-in drift checks** | Rich drift reports; product ships PSI / median / scale drift checks without requiring it. |
| Embedded analytics | `duckdb/duckdb` | MIT | **Recommended for larger file estates** | Query CSV/Parquet directly and reduce pandas memory pressure when data volumes grow. |
| Time-series storage | `apache/iotdb` | Apache-2.0 | **External connector candidate** | Persistent high-volume equipment telemetry instead of flat CSV logs. |
| Forecasting / temporal ML | `sktime/sktime` | BSD-3-Clause | **Optional future integration** | Remaining useful life / quality trends / maintenance forecasting once a validated target exists. |
| Image annotation | `HumanSignal/label-studio` | Apache-2.0 | **External active-learning loop** | Send low-confidence / critical snapshots for human labeling and retraining. Export hook is included. |
| Image/video annotation | `cvat-ai/cvat` | MIT | **External active-learning loop** | Alternative industrial CV annotation UI. Manifest export hook is included. |
| Process mining | `process-intelligence-solutions/pm4py` | AGPL-3.0 | **Not bundled by default** | Product includes its own basic path/variant/bottleneck analysis. Use PM4Py separately only if its license model fits the deployment. |
| Industrial HMI | `frangoteam/FUXA` | MIT | Architecture/UI reference | OPC-UA/MQTT/PLC/HMI patterns; useful if a customer wants a SCADA-style visualization layer. |
| IoT platform | `thingsboard/thingsboard` | Apache-2.0 | Architecture / external platform candidate | Device registry, telemetry and rule-engine patterns. |
| Labelled vision model lifecycle | `HumanSignal/label-studio`, `cvat-ai/cvat` | Apache-2.0 / MIT | **Supported workflow** | Review queue -> label -> train -> evaluate -> promote model -> redeploy. |

## What was actually implemented in this release

### 1. Vision inspection pipeline

```text
USB / RTSP / video / uploaded image
          │
          ▼
 OpenCV capture / decode
          │
          ├─ YOLOX ONNX object/defect detection
          ├─ demo detector (works with zero model download)
          ├─ optional Ultralytics adapter (license-sensitive)
          └─ Anomalib sidecar contract for unknown defects
          │
          ▼
 optional ByteTrack / QR / PaddleOCR
          │
          ▼
 rules: forbidden / required / count limits
          │
          ▼
 snapshot + event + human-review queue
          │
          ▼
 Factory Decision Copilot root-cause evidence
```

The point is not to make a separate “camera AI demo”.  If `CAM-BODY-03` sees a visible defect and the affected product passed `EQ-R03`, that visual event becomes another evidence item on the `EQ-R03` root-cause candidate.

### 2. Streaming / sensor intelligence

The built-in module calculates robust operating-point deviations per equipment. River's `HalfSpaceTrees` is exposed as an optional online extension. PyOD is a future / optional multivariate ensemble path.

### 3. Process intelligence without PM4Py lock-in

The product calculates:

- product/vehicle process sequences;
- most common process path;
- variant frequency;
- deviations from the modal path;
- median / p90 cycle time by equipment;
- bottleneck ranking.

This deliberately avoids forcing an AGPL process-mining dependency into the proprietary core.

### 4. Maintenance optimization

Health scores become maintenance tasks. If OR-Tools is installed, CP-SAT minimizes risk-weighted maintenance start times subject to technician capacity. Otherwise a deterministic greedy fallback is used.

### 5. Data drift monitoring

The built-in implementation compares the historical baseline to recent telemetry using:

- Population Stability Index (PSI);
- median shift;
- variance / scale shift.

Evidently can later render richer customer-facing drift reports without changing the root application.

### 6. Acoustic condition monitoring

The release contains a no-network DSP baseline and synthetic sample WAV files. It extracts:

- RMS energy;
- crest factor;
- spectral centroid;
- dominant frequency;
- high-frequency energy ratio.

The interface is intentionally model-agnostic. A DCASE/MIMII-style autoencoder can replace the scoring layer after enough customer machine audio is collected.

### 7. Human-in-the-loop loop

Low-confidence detections and critical vision events are placed into the review queue. Export hooks for Label Studio and CVAT are included so corrected labels can be used to retrain the detector.

## High-value additions that should come next

### A. Visual unknown-defect sidecar (Anomalib)
Highest value after YOLOX for quality inspection. YOLO answers “is a known class present?”, while PatchCore/EfficientAD-style systems answer “does this look unlike known-good parts?”. In manufacturing, both are useful and complementary.

### B. Model registry + shadow deployment
Promote a candidate model only after it passes a test set. Run old/new models in parallel (“shadow”) and compare false rejects/escapes before switching production. Existing MLflow hook is the natural control point.

### C. Data/vision drift alarms
Camera angle, lighting, part finish, supplier changes and sensor recalibration can silently degrade AI. Persist feature distributions and alert before accuracy collapses.

### D. Thermal camera evidence
Treat thermal frames as another evidence source: hotspot location, max temperature, delta to baseline. It fits the same `VisionEvent -> Evidence` contract.

### E. Acoustic autoencoder
Learn each machine's normal sound, score reconstruction/embedding distance, and combine it with vibration/current/temperature. This can surface bearing or pneumatic anomalies before visual quality fails.

### F. MES/QMS/SCADA connectors
Move from “folder drop” to read-only connectors for the customer’s real systems. Keep a canonical semantic layer so every connector maps into the same product/vehicle/equipment/time/lot entities.

### G. Closed-loop recommendation approval
AI proposes checks, but a responsible engineer accepts/rejects them. Store the outcome and feed it back into hypothesis ranking. Do not allow autonomous equipment control from an LLM response.

## Commercial architecture rule

Use OSS for commodity plumbing and keep product value in:

- manufacturing semantic mapping;
- cross-source traceability;
- evidence fusion;
- root-cause prioritization;
- investigation workflow;
- auditability;
- customer-specific connectors / rules.

That is the layer a factory is paying for; a pile of open-source dashboards or models by itself is not a differentiated product.
