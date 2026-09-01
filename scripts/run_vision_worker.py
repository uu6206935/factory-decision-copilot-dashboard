#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2

from app.config import ROOT
from app.vision.service import _source_value, analyze_frame, load_cameras, read_frame

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def _is_image_source(source: str) -> bool:
    src = _source_value(source)
    return isinstance(src, str) and Path(src).exists() and Path(src).suffix.lower() in IMAGE_EXT


def main() -> int:
    p = argparse.ArgumentParser(description="Factory Decision Copilot camera worker")
    p.add_argument("--camera", action="append", help="camera id; repeatable. default: all enabled cameras")
    p.add_argument("--interval", type=float, default=0.25, help="minimum seconds between analysis cycles")
    p.add_argument("--once", action="store_true", help="capture one frame and exit")
    p.add_argument("--every-n-frames", type=int, default=1, help="analyze every Nth frame for live sources")
    args = p.parse_args()
    wanted = set(args.camera or [])
    cameras = [c for c in load_cameras() if c.enabled and (not wanted or c.id in wanted)]
    if not cameras:
        print("No enabled matching cameras")
        return 2

    captures: dict[str, cv2.VideoCapture] = {}
    frame_no: dict[str, int] = {}
    try:
        for cam in cameras:
            if not _is_image_source(cam.source):
                cap = cv2.VideoCapture(_source_value(cam.source))
                captures[cam.id] = cap
                frame_no[cam.id] = 0
        while True:
            cycle_start = time.perf_counter()
            for cam in cameras:
                try:
                    if _is_image_source(cam.source):
                        frame = read_frame(cam.source)
                    else:
                        cap = captures[cam.id]
                        ok, frame = cap.read()
                        if not ok or frame is None:
                            cap.release()
                            time.sleep(0.2)
                            cap = cv2.VideoCapture(_source_value(cam.source))
                            captures[cam.id] = cap
                            ok, frame = cap.read()
                            if not ok or frame is None:
                                raise RuntimeError("camera frame unavailable")
                        frame_no[cam.id] += 1
                        if frame_no[cam.id] % max(1, args.every_n_frames) != 0:
                            continue
                    result = analyze_frame(cam, frame, actor="vision-worker")
                    print(f"{datetime.now().isoformat(timespec='seconds')} {cam.id}: detections={len(result.detections)} events={len(result.events)} latency_ms={result.latency_ms:.1f}")
                except Exception as exc:
                    print(f"{datetime.now().isoformat(timespec='seconds')} {cam.id}: ERROR {exc}")
            if args.once:
                break
            elapsed = time.perf_counter() - cycle_start
            time.sleep(max(0.0, max(0.05, args.interval) - elapsed))
    finally:
        for cap in captures.values():
            cap.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
