"""Smoke-test the adaptive analyzer against deliberately incomplete datasets."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from tempfile import TemporaryDirectory
import pandas as pd

from app.analysis import analyze
from app.capabilities import detect_capabilities


def csv(path, rows): pd.DataFrame(rows).to_csv(path,index=False,encoding="utf-8-sig")

cases = {
    "quality_only": lambda d: csv(d/"品質.csv", [{"車両番号":"A1","判定":"OK"},{"車両番号":"A2","判定":"NG"}]),
    "sensor_only": lambda d: csv(d/"設備ログ.csv", [{"設備番号":"E1","日時":f"2026-08-24 09:{i:02d}:00","電流値":100+(20 if i>14 else 0)} for i in range(20)]),
    "process_only": lambda d: csv(d/"工程履歴.csv", [{"車両番号":"A1","設備番号":"E1"},{"車両番号":"A1","設備番号":"E2"}]),
    "maintenance_only": lambda d: csv(d/"保全.csv", [{"設備番号":"E1","故障":"摩耗"},{"設備番号":"E1","故障":"摩耗"}]),
    "parts_only": lambda d: csv(d/"部品.csv", [{"車両番号":"A1","部品ロット":"L1"}]),
    "docs_only": lambda d: (d/"手順書.md").write_text("異常時は設備を確認する。",encoding="utf-8"),
}

for name, build in cases.items():
    with TemporaryDirectory() as td:
        d=Path(td); build(d)
        caps=detect_capabilities(d)
        result=analyze("利用可能なデータを分析して", d)
        print(name, "active=", caps["active_modules"], "mode=", result.mode, "candidates=", len(result.candidates))
