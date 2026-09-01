#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
THIRD="$ROOT/third_party_build"
YOLOX="$THIRD/YOLOX"
MODELS="$ROOT/models"
mkdir -p "$THIRD" "$MODELS"
if [ ! -d "$YOLOX/.git" ]; then
  git clone --depth 1 https://github.com/Megvii-BaseDetection/YOLOX.git "$YOLOX"
fi
cd "$YOLOX"
python -m pip install -v -e .
python -m pip install onnx onnxsim
if [ ! -f yolox_s.pth ]; then
  python - <<'PY'
import urllib.request
urllib.request.urlretrieve('https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.pth','yolox_s.pth')
PY
fi
python tools/export_onnx.py -n yolox-s -c yolox_s.pth --output-name "$MODELS/yolox_factory.onnx"
echo "Created $MODELS/yolox_factory.onnx"
