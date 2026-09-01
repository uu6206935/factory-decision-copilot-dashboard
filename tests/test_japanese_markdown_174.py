from fastapi.testclient import TestClient

from app.main import app
from app.markdown_utils import render_markdown


def test_copilot_markdown_renders_heading_bold_list_and_table():
    raw = r'''\## QV-017 品質NG 原因候補の調査結果

### 1) 観察事実
- 設備 \*\*EQ-R03\*\* で異常。

| 順位 | 仮説 | 優先度 |
|---|---|---|
| 1 | \*\*電極チップ摩耗\*\* | 90/100 |
'''
    html = str(render_markdown(raw))
    assert '<h2>QV-017 品質NG 原因候補の調査結果</h2>' in html
    assert '<strong>EQ-R03</strong>' in html
    assert '<ul>' in html and '<li>' in html
    assert '<table>' in html and '<th>順位</th>' in html
    assert '<strong>電極チップ摩耗</strong>' in html
    assert r'\##' not in html and r'\*\*' not in html


def test_copilot_markdown_sanitizes_html():
    html = str(render_markdown('## 見出し\n<script>alert(1)</script>\n**安全**'))
    assert '<script' not in html
    assert '<h2>見出し</h2>' in html
    assert '<strong>安全</strong>' in html


def test_major_pages_use_japanese_ui_labels():
    client = TestClient(app)
    forbidden = [
        'CURRENT COVERAGE', 'PROCESS INTELLIGENCE', 'SENSOR AI',
        'RELATION DISCOVERY', 'APPROVAL AUDIT TRAIL', 'COPILOT RESPONSE',
        '>ACTIVE<', '>WAITING<', '>DATA WAIT<', 'AI SCHEMA DISCOVERY',
    ]
    for path in ['/', '/equipment', '/equipment/bolt-torque', '/investigate', '/onboarding', '/data-map', '/intelligence', '/data', '/engineering']:
        r = client.get(path)
        assert r.status_code == 200
        for phrase in forbidden:
            assert phrase not in r.text, (path, phrase)


def test_intelligence_signal_names_are_localized_in_template():
    client = TestClient(app)
    r = client.get('/intelligence')
    assert r.status_code == 200
    assert '工程・設備AI' in r.text
    assert '工程分析AI' in r.text
    assert '設備センサAI' in r.text
