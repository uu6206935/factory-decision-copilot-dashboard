# Vision AI setup

## What works immediately

The sample camera `cam-body-03` points at `sample_data/vision_demo_line.png`. It uses the built-in deterministic demo detector, so the complete event pipeline can be demonstrated with no external model download.

Open:

```text
http://127.0.0.1:8000/vision
```

and press **1フレーム解析**. The visible red defect generates a critical event and an annotated snapshot. Investigating `QV-017` afterwards incorporates that event into the root-cause evidence for `EQ-R03`.

## Run a camera continuously

```bash
python scripts/run_vision_worker.py --camera cam-body-03 --interval 2
```

For one frame only:

```bash
python scripts/run_vision_worker.py --camera cam-body-03 --once
```

The worker is intentionally separate from the web process so camera failure or slow inference does not block the UI/API. `docker-compose.enterprise.yml` also contains an optional `vision` profile.

```bash
docker compose -f docker-compose.enterprise.yml --profile vision up --build
```

## Webcam

In `config/cameras.json`:

```json
{
  "id": "cam-line-01",
  "name": "Line 1 camera",
  "equipment_id": "EQ-R03",
  "source": "webcam://0",
  "target_id": null,
  "enabled": true,
  "detector": {
    "type": "yolox_onnx",
    "model": "models/yolox_factory.onnx",
    "input_size": [640, 640],
    "class_names": ["part", "defect", "tool"],
    "score_threshold": 0.35,
    "nms_threshold": 0.45,
    "tracking": true
  },
  "rules": [
    {"id":"visible-defect","type":"forbidden_class","class_name":"defect","severity":"critical","message":"外観欠陥候補"}
  ]
}
```

## RTSP / IP camera

Set `source` to the approved RTSP URI, for example:

```text
rtsp://camera-host/approved-stream
```

For production, do not keep credentials in `cameras.json`. Inject secrets through the deployment secret store or resolve a camera ID to a credentialed URL at runtime.

## YOLOX model setup

YOLOX is Apache-2.0. Model weights are not bundled in this product. Two bootstrap scripts are included for a connected development machine:

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_yolox_model_windows.ps1
```

Linux/macOS:

```bash
./scripts/setup_yolox_model_linux.sh
```

They clone the upstream YOLOX project, download the official YOLOX-S checkpoint and use the upstream ONNX export command to create:

```text
models/yolox_factory.onnx
```

The COCO checkpoint is useful to validate the plumbing only. **A factory defect model must be trained on customer-approved, representative images and factory-specific classes.**

## Custom classes

Typical manufacturing classes might be:

```text
part
missing_clip
wrong_connector
surface_defect
weld_spatter
worker
hand
tool
```

Do not force every defect into YOLO. If a defect has many visual forms and few labels, use a known-good anomaly detector (Anomalib/PatchCore/EfficientAD) and send its anomaly event into the same evidence store.

## Human review / active learning

The system queues:

- ambiguous detections (currently 0.25–0.65 confidence), and
- all critical/high events.

Export examples:

```python
from pathlib import Path
from integrations.label_studio_hook import export_tasks
from integrations.cvat_hook import export_manifest

export_tasks(Path("runtime/label_studio_tasks.json"))
export_manifest(Path("runtime/cvat_manifest.json"))
```

The resulting corrected labels should pass through a training/evaluation/model-promotion process before production deployment.

## License note

The default proprietary-product path is YOLOX + OpenCV / ONNX Runtime / OpenVINO because their licenses are permissive. The optional Ultralytics adapter is deliberately not a default dependency because the open-source Ultralytics repository is AGPL-3.0; use it only under terms appropriate to the customer deployment.

## Anomalib unknown-defect sidecar

An optional sidecar is included at `integrations/anomalib_sidecar.py`. After exporting an Anomalib model to OpenVINO, run for example:

```bash
ANOMALIB_MODEL_BIN=/models/visual_defect/model.bin \
uvicorn integrations.anomalib_sidecar:app --host 127.0.0.1 --port 8010
```

Then use the disabled `cam-anomaly-template` in `config/cameras.json` as a starting point. The sidecar returns an image-level anomaly score plus an approximate anomaly-map bounding box when available. The main application turns that into the `visual_anomaly` class and uses the normal rule/event/evidence path.
