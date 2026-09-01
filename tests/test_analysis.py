from pathlib import Path

from app.analysis import analyze
from app.schema import choose_role_tables, scan_tables

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "sample_data"


def test_schema_auto_detects_mixed_files():
    profiles, warnings = scan_tables(DATA)
    chosen = choose_role_tables(profiles)
    assert not warnings
    assert {"quality", "process", "equipment_logs", "maintenance", "parts"}.issubset(chosen)
    assert chosen["quality"].source.endswith("品質検査結果.xlsx")
    assert "車両番号" in chosen["quality"].mapping
    assert chosen["quality"].mapping["車両番号"] == "vehicle_id"


def test_qv017_points_to_r03_and_not_lot():
    result = analyze("QV-017の品質NGの原因候補を調べて。停止と継続も比較して", DATA)
    assert result.vehicle_id == "QV-017"
    assert result.candidates
    assert result.candidates[0].label.startswith("EQ-R03")
    assert result.candidates[0].score > 0.75
    lot = next(c for c in result.candidates if c.category == "part_lot")
    assert lot.score < 0.2


def test_decision_scenarios_present():
    result = analyze("QV-017の品質NGの原因候補を調べて", DATA)
    assert len(result.scenarios) == 2
    continue_s, stop_s = result.scenarios
    assert continue_s.expected_defects > stop_s.expected_defects
    assert stop_s.production_loss_units > 0
