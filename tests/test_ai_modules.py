from pathlib import Path

from fastapi.testclient import TestClient

from app.config import DATA_DIR, ROOT
from app.main import app
from app.optimization import MaintenanceTask, schedule_maintenance
from app.process_intelligence import process_snapshot
from app.sensor_ai import equipment_health
from app.service import run_analysis
from app.vision.service import SNAPSHOT_DIR, capture_once


def test_vision_demo_detects_defect_and_persists_snapshot():
    result = capture_once("cam-body-03", actor="pytest")
    assert any(d.class_name == "defect" for d in result.detections)
    assert result.events
    assert result.annotated_snapshot
    assert (SNAPSHOT_DIR / result.annotated_snapshot).exists()


def test_vision_is_merged_into_root_cause_evidence():
    capture_once("cam-body-03", actor="pytest")
    payload = run_analysis("QV-017の品質NGの原因候補を調べて", actor="pytest", use_llm=False)
    assert payload["vision_evidence"]
    candidates = payload["candidates"]
    eq = next(c for c in candidates if c["category"] == "equipment" and c["label"].startswith("EQ-R03:"))
    assert any(e["kind"] == "vision" for e in eq["evidence"])


def test_sensor_health_and_process_intelligence():
    health = equipment_health(DATA_DIR)
    assert health
    assert any(x.equipment_id == "EQ-R03" for x in health)
    proc = process_snapshot(DATA_DIR, "QV-017")
    assert proc["available"] is True
    assert proc["variants"]


def test_maintenance_scheduler_fallback_or_ortools():
    rows = schedule_maintenance([
        MaintenanceTask("EQ-A", 30, 0.9),
        MaintenanceTask("EQ-B", 20, 0.6),
    ], horizon_min=120, technicians=1)
    assert len(rows) == 2
    assert rows[0].start_min <= rows[1].start_min


def test_ai_module_pages_and_api():
    client = TestClient(app)
    assert client.get("/vision").status_code == 200
    assert client.get("/intelligence").status_code == 200
    assert client.get("/api/v1/intelligence/sensor-health").status_code == 200
    r = client.post("/api/v1/vision/capture/cam-body-03")
    assert r.status_code == 200
    assert r.json()["events"]


def test_drift_and_acoustic_modules():
    from app.acoustic_ai import demo_snapshot
    from app.drift_ai import drift_snapshot
    from app.config import DATA_DIR
    acoustic = demo_snapshot()
    assert acoustic["available"] is True
    assert acoustic["risk_score"] > 0.2
    assert acoustic["equipment_id"] == "EQ-R03"
    drift = drift_snapshot(DATA_DIR)
    assert "summary" in drift
    assert "signals" in drift


def test_intelligence_new_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/v1/intelligence/drift").status_code == 200
    r = c.get("/api/v1/intelligence/acoustic")
    assert r.status_code == 200
    assert r.json()["available"] is True


def test_zone_rule_detects_object_center():
    from app.vision.models import Detection, VisionRule
    from app.vision.rules import evaluate_rules
    d = Detection(2, "worker", 0.9, 10, 10, 30, 30)
    r = VisionRule(id="zone", type="zone_forbidden_class", class_name="worker", polygon=[[0,0],[100,0],[100,100],[0,100]], severity="critical")
    events = evaluate_rules([d], [r])
    assert events and events[0]["rule_id"] == "zone"


def test_predictive_threshold_forecast():
    from app.predictive_ai import threshold_forecast
    from app.config import DATA_DIR
    x = threshold_forecast(DATA_DIR)
    assert x["available"] is True
    assert x["items"]
    assert all("minutes_to_limit" in i for i in x["items"])
