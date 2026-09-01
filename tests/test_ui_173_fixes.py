from pathlib import Path

from app.text_utils import repair_utf8_as_cp932


def test_mojibake_filename_repair():
    assert repair_utf8_as_cp932("01_蜩∬ｳｪ讀懈渊邨先棡.xlsx") == "01_品質検査結果.xlsx"
    assert repair_utf8_as_cp932("03_險ｭ蛯吶そ繝ｳ繧ｵ繝ｭ繧ｰ.csv") == "03_設備センサログ.csv"
    assert repair_utf8_as_cp932("01_品質検査結果.xlsx") == "01_品質検査結果.xlsx"


def test_unique_light_css_asset_and_guard():
    root = Path(__file__).parents[1]
    base = (root / "app/templates/base.html").read_text(encoding="utf-8")
    css = (root / "app/static/product-warm-teal-174.css").read_text(encoding="utf-8")
    assert "product-warm-teal-174.css" in base
    assert ".content .coverage-grid > div" in css
    assert ".content .target-form input" in css
    assert ".content .approval-action-form input.text-input.readonly" in css
    assert ".content .modal-path" in css
    assert "background:#ffffff !important" in css


def test_schema_scan_repairs_mojibake_source_name(tmp_path):
    import pandas as pd
    from app.schema import scan_tables
    bad = "01_品質検査結果.xlsx".encode("utf-8").decode("cp932")
    pd.DataFrame({"号口":["QV-001"],"結果区分":["OK"]}).to_excel(tmp_path / bad, index=False)
    profiles, warnings = scan_tables(tmp_path)
    assert not warnings
    assert profiles
    assert all("蜩∬" not in p.source for p in profiles)
    assert any(p.source == "01_品質検査結果.xlsx" for p in profiles)


def test_ingest_repairs_mojibake_source_name(tmp_path):
    from app.ingest import load_chunks
    bad = "03_設備センサログ.csv".encode("utf-8").decode("cp932")
    (tmp_path / bad).write_text("設備番号,電流\nEQ-01,12.3\n", encoding="utf-8")
    chunks, warnings = load_chunks(tmp_path)
    assert not warnings
    assert chunks
    assert chunks[0].source == "03_設備センサログ.csv"


def test_file_catalog_repairs_mojibake_path(tmp_path):
    from app.provenance import build_file_catalog
    bad = "03_設備センサログ.csv".encode("utf-8").decode("cp932")
    (tmp_path / bad).write_text("設備番号,電流\nEQ-01,12.3\n", encoding="utf-8")
    rows = build_file_catalog(tmp_path)
    assert rows[0]["relative_path"] == "03_設備センサログ.csv"
