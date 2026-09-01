from __future__ import annotations

"""Acoustic condition-monitoring primitives for machine sound.

This module deliberately starts with transparent DSP features so it can run on
an air-gapped factory PC.  A DCASE/MIMII-style autoencoder or other model can
later replace the scoring layer without changing the API contract.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import wave

import numpy as np

from .config import DATA_DIR, ROOT


@dataclass
class AcousticFeatures:
    path: str
    sample_rate: int
    duration_sec: float
    rms: float
    crest_factor: float
    spectral_centroid_hz: float
    dominant_frequency_hz: float
    high_band_ratio: float

    def as_dict(self) -> dict:
        return asdict(self)


def _read_wav(path: Path) -> tuple[int, np.ndarray]:
    # stdlib WAV reader keeps the core product free from heavyweight audio deps.
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        channels = w.getnchannels()
        width = w.getsampwidth()
        frames = w.readframes(w.getnframes())
    dtype = {1: np.uint8, 2: np.int16, 4: np.int32}.get(width)
    if dtype is None:
        raise ValueError(f"unsupported WAV sample width: {width}")
    x = np.frombuffer(frames, dtype=dtype).astype(np.float64)
    if width == 1:
        x = (x - 128.0) / 128.0
    else:
        x /= float(2 ** (8 * width - 1))
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    return int(sr), x


def extract_features(path: Path) -> AcousticFeatures:
    sr, x = _read_wav(path)
    if len(x) == 0:
        raise ValueError("empty WAV")
    x = x - float(np.mean(x))
    rms = float(np.sqrt(np.mean(np.square(x))) + 1e-12)
    crest = float(np.max(np.abs(x)) / rms)
    window = np.hanning(len(x)) if len(x) > 2 else np.ones(len(x))
    spec = np.abs(np.fft.rfft(x * window))
    freq = np.fft.rfftfreq(len(x), 1.0 / sr)
    power = np.square(spec)
    denom = float(power.sum()) + 1e-12
    centroid = float((freq * power).sum() / denom)
    dominant = float(freq[int(np.argmax(power))]) if len(power) else 0.0
    high = float(power[freq >= min(1000.0, sr * 0.25)].sum() / denom)
    return AcousticFeatures(str(path), sr, len(x) / sr, rms, crest, centroid, dominant, high)


def compare_to_baseline(sample_path: Path, baseline_paths: list[Path]) -> dict:
    sample = extract_features(sample_path)
    base = [extract_features(p) for p in baseline_paths if p.exists()]
    if not base:
        return {"available": False, "sample": sample.as_dict(), "reason": "baseline missing"}
    keys = ["rms", "crest_factor", "spectral_centroid_hz", "dominant_frequency_hz", "high_band_ratio"]
    deviations = []
    for key in keys:
        vals = np.asarray([float(getattr(x, key)) for x in base], dtype=float)
        med = float(np.median(vals))
        mad = float(np.median(np.abs(vals - med)))
        scale = max(1.4826 * mad, float(np.std(vals)), max(abs(med) * 0.03, 1e-6))
        val = float(getattr(sample, key))
        z = abs(val - med) / scale
        deviations.append({"feature": key, "value": val, "baseline": med, "robust_z": float(z)})
    deviations.sort(key=lambda x: x["robust_z"], reverse=True)
    risk = float(np.clip(np.mean([min(1.0, d["robust_z"] / 4.0) for d in deviations[:3]]), 0, 1))
    state = "critical" if risk >= 0.70 else "warning" if risk >= 0.35 else "healthy"
    return {"available": True, "state": state, "risk_score": risk, "sample": sample.as_dict(), "deviations": deviations}


def snapshot(data_dir: Path = DATA_DIR) -> dict:
    """Auto-discover a small labelled acoustic dataset.

    Files containing normal/ok/good are used as the baseline. Files containing
    anomaly/abnormal/ng/fail are comparison samples. This keeps the module
    optional and lets an audio-only deployment run without quality/process data.
    """
    wavs = sorted(p for p in data_dir.rglob("*.wav") if p.is_file()) if data_dir.exists() else []
    normals = [p for p in wavs if any(k in p.name.lower() for k in ("normal", "ok", "good", "baseline"))]
    anomalies = [p for p in wavs if any(k in p.name.lower() for k in ("anomaly", "abnormal", "ng", "fail", "fault"))]
    if not normals and len(wavs) >= 3:
        normals = wavs[:-1]
    sample = anomalies[0] if anomalies else (wavs[-1] if len(wavs) >= 2 else None)
    if sample is None or not normals:
        return {"available": False, "reason": "need baseline WAV files and a comparison WAV", "wav_count": len(wavs)}
    normals = [p for p in normals if p != sample]
    if not normals:
        return {"available": False, "reason": "baseline missing", "wav_count": len(wavs)}
    result = compare_to_baseline(sample, normals)
    result["equipment_id"] = sample.parent.name if sample.parent != data_dir else "AUDIO-SOURCE"
    try:
        result["source"] = str(sample.relative_to(ROOT))
    except Exception:
        result["source"] = str(sample)
    result["baseline_count"] = len(normals)
    return result


def demo_snapshot() -> dict:
    result = snapshot(DATA_DIR)
    if result.get("available"):
        result["equipment_id"] = "EQ-R03"
    return result

