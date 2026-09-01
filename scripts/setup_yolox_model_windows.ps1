# Bootstrap a permissively licensed YOLOX-S model and export it to ONNX.
# Requires Git, Python, and internet access. Run only in an approved setup environment.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Third = Join-Path $Root "third_party_build"
$YoloX = Join-Path $Third "YOLOX"
$Models = Join-Path $Root "models"
New-Item -ItemType Directory -Force -Path $Third,$Models | Out-Null
if (-not (Test-Path $YoloX)) {
  git clone --depth 1 https://github.com/Megvii-BaseDetection/YOLOX.git $YoloX
}
Push-Location $YoloX
python -m pip install -v -e .
python -m pip install onnx onnxsim
$Ckpt = Join-Path $YoloX "yolox_s.pth"
if (-not (Test-Path $Ckpt)) {
  Invoke-WebRequest -Uri "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.pth" -OutFile $Ckpt
}
python tools/export_onnx.py -n yolox-s -c $Ckpt --output-name (Join-Path $Models "yolox_factory.onnx")
Pop-Location
Write-Host "Created: $(Join-Path $Models 'yolox_factory.onnx')"
Write-Host "Edit config/cameras.json class_names for your custom factory model before production use."
