from __future__ import annotations

from fastapi.testclient import TestClient

import app.approval_center as approval
from app.lineage import build_lineage
from app.main import app
from app.platform import catalog_payload, get_state


def test_approval_store_supports_four_states_and_history(tmp_path, monkeypatch):
    monkeypatch.setattr(approval, "APPROVAL_STORE", tmp_path / "approval_center.json")
    item = "schema::検査.xlsx::::号口"
    approval.record_decision(item, "held", "engineer-a", note="要確認")
    approval.record_decision(item, "approved", "engineer-b", details={"canonical": "vehicle_id"})
    store = approval.load_store()
    assert store["items"][item]["status"] == "approved"
    assert store["items"][item]["actor"] == "engineer-b"
    history = approval.recent_history(10)
    assert history[0]["to_status"] == "approved"
    assert history[1]["to_status"] == "held"


def test_approval_center_builds_schema_role_and_join_items(tmp_path, monkeypatch):
    monkeypatch.setattr(approval, "APPROVAL_STORE", tmp_path / "approval_center.json")
    catalog = {
        "tables": [{
            "source": "検査.xlsx", "sheet": "Sheet1", "table_key": "検査.xlsx::Sheet1", "role": "quality", "role_score": .94,
            "compatible_roles": ["quality"],
            "column_profiles": [{"raw": "号口", "canonical": "vehicle_id", "confidence": .97, "status": "auto", "examples": ["A01"], "reasons": ["ID pattern"]}],
        }],
        "joins": [{"id": "a|b|vehicle_id|equi_join", "label": "製品ID", "key": "vehicle_id", "left": "a", "right": "b", "confidence": .92, "status": "review", "reason": "same id"}],
    }
    center = approval.build_center(catalog)
    types = {x["type"] for x in center["items"]}
    assert {"schema", "role", "join"}.issubset(types)
    assert center["counts"]["pending"] == 3


def test_lineage_has_five_layers_and_analysis_nodes(tmp_path, monkeypatch):
    monkeypatch.setattr(approval, "APPROVAL_STORE", tmp_path / "approval_center.json")
    catalog = catalog_payload()
    graph = build_lineage(catalog, get_state().capabilities)
    assert [x["label"] for x in graph["layers"]] == ["ファイル", "テーブル", "意味付けされた列", "結合", "分析"]
    assert any(n["kind"] == "module" for n in graph["nodes"])
    assert any(n["kind"] == "column" for n in graph["nodes"])
    assert graph["summary"]["nodes"] == len(graph["nodes"])


def test_approval_center_page_was_removed():
    # The dedicated "承認センター" screen/nav item was intentionally removed
    # (2026-09 dashboard redesign). The underlying governance module
    # (approval_center.py, tested above) still backs the inline schema/join
    # review UI on /onboarding and /data-map.
    client = TestClient(app)
    assert client.get("/approvals").status_code == 404
    assert client.get("/api/v1/approvals").status_code == 404


def test_data_map_page_renders():
    client = TestClient(app)
    m = client.get("/data-map")
    assert m.status_code == 200
    assert "工場データの「つながり」を一枚で見る" in m.text
    assert "lineageData" in m.text


def test_lineage_api_renders():
    client = TestClient(app)
    l = client.get("/api/v1/lineage")
    assert l.status_code == 200
    body = l.json()
    assert "nodes" in body and "edges" in body and "summary" in body
