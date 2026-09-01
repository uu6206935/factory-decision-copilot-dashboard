from __future__ import annotations

import json
from pathlib import Path


def test_deepseek_client_always_uses_flash(monkeypatch):
    import app.deepseek as ds

    captured = {}

    class Resp:
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "payload": json, "timeout": timeout})
        return Resp()

    monkeypatch.setattr(ds, "DEEPSEEK_ENABLED", True)
    monkeypatch.setattr(ds, "DEEPSEEK_API_KEY", "test-key-not-real")
    monkeypatch.setattr(ds.requests, "post", fake_post)

    text = ds.chat(system="system", user="user", thinking=False)
    assert text == "ok"
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert captured["url"].endswith("/chat/completions")
    assert "test-key-not-real" not in str(captured["payload"])


def test_deepseek_json_mode_uses_flash(monkeypatch):
    import app.deepseek as ds

    captured = {}

    class Resp:
        def raise_for_status(self):
            return None
        def json(self):
            return {"choices": [{"message": {"content": '{"columns": []}'}}]}

    def fake_post(url, headers, json, timeout):
        captured["payload"] = json
        return Resp()

    monkeypatch.setattr(ds, "DEEPSEEK_ENABLED", True)
    monkeypatch.setattr(ds, "DEEPSEEK_API_KEY", "test-key-not-real")
    monkeypatch.setattr(ds.requests, "post", fake_post)
    out = ds.json_chat(system="output json", user="json please")
    assert out == {"columns": []}
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert captured["payload"]["response_format"] == {"type": "json_object"}


def test_no_pro_or_retired_deepseek_model_in_application_source():
    root = Path(__file__).resolve().parents[1]
    targets = [root / "app", root / ".env.example"]
    text = ""
    for target in targets:
        if target.is_file():
            text += target.read_text(encoding="utf-8", errors="ignore")
        else:
            for p in target.rglob("*.py"):
                text += p.read_text(encoding="utf-8", errors="ignore")
    low = text.lower()
    assert "deepseek-v4-pro" not in low
    assert "deepseek-chat" not in low
    assert "deepseek-reasoner" not in low
    assert "deepseek-v4-flash" in low


def test_env_example_does_not_contain_secret_like_key():
    text = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    # Placeholder must be empty; never package a user key.
    line = next(x for x in text.splitlines() if x.startswith("DEEPSEEK_API_KEY="))
    assert line == "DEEPSEEK_API_KEY="
