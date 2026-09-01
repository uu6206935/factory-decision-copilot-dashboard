"""Optional Anomalib/OpenVINO inference sidecar.

Install optional dependencies first, then set ANOMALIB_MODEL_BIN to an exported
OpenVINO .bin model.  The main application can configure a camera detector as
`anomalib_http` pointing to this service.

Upstream API pattern follows Anomalib's Apache-2.0 OpenVINOInferencer example.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, UploadFile

MODEL_BIN = os.getenv("ANOMALIB_MODEL_BIN", "")
app = FastAPI(title="Factory Copilot Anomalib Sidecar")
_inferencer = None


def inferencer():
    global _inferencer
    if _inferencer is None:
        if not MODEL_BIN:
            raise RuntimeError("ANOMALIB_MODEL_BIN is not configured")
        from anomalib.deploy import OpenVINOInferencer  # type: ignore
        _inferencer = OpenVINOInferencer(path=MODEL_BIN)
    return _inferencer


def _scalar(x, default=0.0):
    if x is None:
        return default
    try:
        if hasattr(x, "detach"):
            x = x.detach().cpu().numpy()
        a = np.asarray(x)
        return float(a.reshape(-1)[0])
    except Exception:
        return float(x)


def _bbox_from_map(anomaly_map) -> list[int] | None:
    if anomaly_map is None:
        return None
    try:
        if hasattr(anomaly_map, "detach"):
            anomaly_map = anomaly_map.detach().cpu().numpy()
        a = np.asarray(anomaly_map).squeeze()
        if a.ndim != 2 or a.size == 0:
            return None
        threshold = max(float(np.quantile(a, 0.985)), float(a.mean() + 2.0 * a.std()))
        ys, xs = np.where(a >= threshold)
        if len(xs) < 2:
            return None
        return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    except Exception:
        return None


@app.get("/healthz")
def healthz():
    return {"ok": bool(MODEL_BIN), "model": MODEL_BIN}


@app.post("/infer")
async def infer(image: UploadFile = File(...)):
    data = await image.read()
    suffix = Path(image.filename or "frame.jpg").suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        path = f.name
    try:
        predictions = inferencer().predict(image=path)
        pred = next(iter(predictions)) if hasattr(predictions, "__iter__") else predictions
        score = _scalar(getattr(pred, "pred_score", None), 0.0)
        label = int(round(_scalar(getattr(pred, "pred_label", None), 1 if score >= 0.5 else 0)))
        return {
            "anomaly_score": score,
            "pred_label": label,
            "bbox": _bbox_from_map(getattr(pred, "anomaly_map", None)),
        }
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
