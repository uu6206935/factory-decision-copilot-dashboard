from pathlib import Path

import pandas as pd

import app.schema as schema
from app.schema import discover_join_candidates, scan_tables, save_schema_review


def test_unknown_japanese_factory_headers_are_understood(tmp_path, monkeypatch):
    monkeypatch.setattr(schema, "SCHEMA_MEMORY", tmp_path / "schema_memory.json")
    df = pd.DataFrame({
        "号口": ["A0001", "A0002", "A0003", "A0004"],
        "実績年月日": ["2026/08/25 08:00", "2026/08/25 08:01", "2026/08/25 08:02", "2026/08/25 08:03"],
        "工程コード": ["WLD10"] * 4,
        "号機": ["03", "03", "04", "03"],
        "結果区分": ["OK", "NG", "OK", "NG"],
        "実測": [4.8, 5.2, 4.9, 5.3],
        "上規格": [5.0] * 4,
        "下規格": [4.5] * 4,
    })
    df.to_excel(tmp_path / "未知フォーマット.xlsx", index=False)
    profiles, warnings = scan_tables(tmp_path)
    assert not warnings
    p = profiles[0]
    assert p.mapping["号口"] == "vehicle_id"
    assert p.mapping["号機"] == "equipment_id"
    assert p.mapping["結果区分"] == "result"
    assert p.mapping["実測"] == "value"
    assert p.mapping["上規格"] == "upper_limit"
    assert p.mapping["下規格"] == "lower_limit"
    assert p.inferred_role == "quality"
    assert "process" in p.compatible_roles
    assert "equipment_logs" not in p.compatible_roles  # no actual sensor signal


def test_join_discovery_uses_semantic_ids_and_value_overlap(tmp_path, monkeypatch):
    monkeypatch.setattr(schema, "SCHEMA_MEMORY", tmp_path / "schema_memory.json")
    pd.DataFrame({
        "号口": ["A001", "A002", "A003"],
        "結果区分": ["OK", "NG", "OK"],
        "号機": ["M01", "M02", "M01"],
    }).to_excel(tmp_path / "検査.xlsx", index=False)
    pd.DataFrame({
        "設備番号": ["M01", "M02", "M01"],
        "日時": ["2026-08-25 08:00", "2026-08-25 08:01", "2026-08-25 08:02"],
        "電流値": [100.0, 122.0, 101.0],
    }).to_csv(tmp_path / "設備ログ.csv", index=False, encoding="utf-8-sig")
    profiles, _ = scan_tables(tmp_path)
    joins = discover_join_candidates(tmp_path, profiles)
    eq = [j for j in joins if j["key"] == "equipment_id"]
    assert eq
    assert eq[0]["confidence"] >= 0.8


def test_schema_review_is_learned_for_next_table(tmp_path, monkeypatch):
    monkeypatch.setattr(schema, "SCHEMA_MEMORY", tmp_path / "schema_memory.json")
    pd.DataFrame({"謎の識別子": ["X001", "X002"], "結果区分": ["OK", "NG"]}).to_excel(tmp_path / "a.xlsx", index=False)
    profiles, _ = scan_tables(tmp_path)
    table_key = profiles[0].table_key
    save_schema_review(table_key, {"謎の識別子": "vehicle_id", "結果区分": "result"}, role="quality", learn=True)
    pd.DataFrame({"謎の識別子": ["Y001", "Y002"], "結果区分": ["OK", "OK"]}).to_excel(tmp_path / "b.xlsx", index=False)
    profiles, _ = scan_tables(tmp_path)
    b = next(p for p in profiles if p.source == "b.xlsx")
    assert b.mapping["謎の識別子"] == "vehicle_id"
    col = next(c for c in b.column_profiles if c["raw"] == "謎の識別子")
    assert col["status"] == "learned"
    assert col["confidence"] == 1.0


def test_onboarding_page_renders():
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    r = client.get("/onboarding")
    assert r.status_code == 200
    assert "Excelを置くだけで、AIがデータ仕様を理解" in r.text
    assert "AIによる列意味推定" in r.text
