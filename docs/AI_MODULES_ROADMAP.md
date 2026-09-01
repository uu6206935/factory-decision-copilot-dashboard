# AI modules roadmap

## Shipped in 1.2.0-ai-modules-rc1

### Vision AI
- image, webcam, video and RTSP capture
- YOLOX ONNX adapter
- zero-download demo detector
- rule engine
- QR decode
- optional PaddleOCR
- optional ByteTrack through Supervision
- snapshot/event persistence
- human review queue
- direct root-cause evidence fusion
- continuous camera worker

### Sensor AI
- robust-z operating-point anomaly score
- recent-vs-baseline shifts
- optional River streaming anomaly detector
- PyOD extension point

### Process intelligence
- process variants
- modal route
- route deviations
- equipment cycle-time median/p90
- bottleneck ranking

### Optimization
- risk-weighted maintenance plan
- OR-Tools CP-SAT when available
- deterministic fallback without OR-Tools

### Data/model drift
- PSI
- median shift
- scale shift
- optional Evidently extension

### Acoustic AI
- WAV condition-monitoring demo
- RMS
- crest factor
- spectral centroid
- dominant frequency
- high-band ratio
- baseline comparison and risk score

### Active learning
- low-confidence/critical review queue
- Label Studio task export
- CVAT manifest export

## Next implementation tier

### 1. Anomalib inference service
Train on known-good images, return anomaly score + segmentation heatmap, and persist the heatmap as evidence. The web app already has the event/evidence model needed for this.

### 2. Thermal inspection
Input: radiometric/thermal images or exported temperature matrices. Output: hotspot area, max temperature, delta against reference part, and a visual overlay.

### 3. Remaining useful life
Requires labeled failure/maintenance history. Candidate architecture: feature store -> sktime / LightGBM / survival model -> calibrated RUL interval -> maintenance optimizer.

### 4. Quality prediction before final inspection
Use process conditions, part lot, supplier, environmental and equipment-state features to estimate defect risk before the product reaches final inspection. Always show feature/evidence provenance and measure calibration.

### 5. Data drift + AI model drift service
Persist daily windows. Alert on input shift, confidence shift and disagreement with human inspection. Optional Evidently reports can become an engineering page.

### 6. Large-scale local analytics
Switch flat-file analysis to DuckDB for CSV/Parquet estates, and to Apache IoTDB/TimescaleDB when telemetry becomes continuous and high-volume.

### 7. Digital twin / what-if simulation
Combine process capacity, queues and downtime with OR-Tools/discrete-event simulation. Example question: “If EQ-R03 is stopped for 35 minutes now, which jobs should be rerouted and what is the expected WIP impact?”

### 8. Controlled action workflow
Recommendations can create a work order or approval request, but execution should remain behind an authenticated human approval or a deterministic safety controller. An LLM should not directly actuate production equipment.
