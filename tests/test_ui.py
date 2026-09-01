from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_product_ui_pages_render():
    for path, marker in [
        ("/", "元町工場"),
        ("/investigate", "品質トラブル原因調査"),
        ("/data", "データカタログ"),
        ("/cases-ui", "調査ケース履歴"),
        ("/engineering", "システムと外部連携"),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert marker in response.text


def test_investigation_product_ui():
    response = client.post("/ask", data={"question": "QV-017の品質NGの原因候補を調べて。停止と継続も比較して"})
    assert response.status_code == 200
    assert "原因候補ランキング" in response.text
    assert "EQ-R03" in response.text
    assert "停止 / 継続の比較" in response.text
