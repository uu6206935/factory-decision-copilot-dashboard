from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_dashboard_and_api():
    r = client.post("/ask", data={"question": "QV-017の品質NGの原因候補を調べて"})
    assert r.status_code == 200
    assert "EQ-R03" in r.text

    r2 = client.post("/api/analyze", json={"question": "QV-017の品質NGの原因候補を調べて"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["candidates"][0]["label"].startswith("EQ-R03")
