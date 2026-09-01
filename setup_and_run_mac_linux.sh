#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export FDC_PORT=8174
echo "Factory Decision Copilot v1.7.4 起動URL -> http://127.0.0.1:8174"
python run_demo.py
