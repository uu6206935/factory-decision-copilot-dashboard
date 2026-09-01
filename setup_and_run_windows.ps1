Set-Location $PSScriptRoot
$env:FDC_PORT = "8174"
if (-not (Test-Path ".venv")) { py -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Start-Job { Start-Sleep -Seconds 3; Start-Process "http://127.0.0.1:8174/investigate" } | Out-Null
Write-Host "Factory Decision Copilot v1.7.4 起動URL -> http://127.0.0.1:8174"
python run_demo.py
