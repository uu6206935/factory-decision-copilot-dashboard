from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    DEEPSEEK_SEND_SAMPLE_VALUES, DEEPSEEK_SEND_DOCUMENT_TEXT,
    DEEPSEEK_SEND_STRUCTURED_EVIDENCE, DEEPSEEK_SCHEMA_REASONING,
    DEEPSEEK_JOIN_REASONING, DEEPSEEK_QUERY_REWRITE, REDACT_BEFORE_LLM,
)
from app.deepseek import chat, json_chat


def ok(name: str, detail: str = "") -> None:
    print(f"[PASS] {name}" + (f" - {detail}" if detail else ""))


def fail(name: str, exc: Exception | str) -> None:
    print(f"[FAIL] {name} - {exc}")
    raise SystemExit(1)

print("Factory Decision Copilot / DeepSeek V4 Flash FULL diagnostics")
print("API key: configured" if DEEPSEEK_API_KEY else "API key: MISSING")
print("API key value is intentionally not printed.")
print(f"Base URL: {DEEPSEEK_BASE_URL}")
print(f"Model: {DEEPSEEK_MODEL}")
print("FULL flags:", {
    "sample_values": DEEPSEEK_SEND_SAMPLE_VALUES,
    "document_text": DEEPSEEK_SEND_DOCUMENT_TEXT,
    "structured_evidence": DEEPSEEK_SEND_STRUCTURED_EVIDENCE,
    "schema_reasoning": DEEPSEEK_SCHEMA_REASONING,
    "join_reasoning": DEEPSEEK_JOIN_REASONING,
    "query_rewrite": DEEPSEEK_QUERY_REWRITE,
    "redact_before_llm": REDACT_BEFORE_LLM,
})
if not DEEPSEEK_API_KEY:
    fail("embedded API key", "missing")
if DEEPSEEK_MODEL != "deepseek-v4-flash":
    fail("model lock", DEEPSEEK_MODEL)
if not all([DEEPSEEK_SEND_SAMPLE_VALUES, DEEPSEEK_SEND_DOCUMENT_TEXT, DEEPSEEK_SEND_STRUCTURED_EVIDENCE, DEEPSEEK_SCHEMA_REASONING, DEEPSEEK_JOIN_REASONING, DEEPSEEK_QUERY_REWRITE]):
    fail("FULL mode flags", "one or more FULL features are disabled")
if REDACT_BEFORE_LLM:
    fail("FULL mode redaction", "REDACT_BEFORE_LLM must be false in this private FULL build")
ok("embedded configuration", "Flash + FULL")

try:
    host = DEEPSEEK_BASE_URL.split('://', 1)[-1].split('/', 1)[0].split(':', 1)[0]
    ip = socket.gethostbyname(host)
    ok("DNS resolution", f"{host} -> {ip}")
except Exception as exc:
    fail("DNS resolution", exc)

headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
try:
    r = requests.get(f"{DEEPSEEK_BASE_URL}/models", headers=headers, timeout=30)
    r.raise_for_status()
    models = [str(x.get('id')) for x in r.json().get('data', [])]
    if DEEPSEEK_MODEL not in models:
        fail("GET /models", f"{DEEPSEEK_MODEL} not returned; got {models}")
    ok("GET /models + API key authorization", f"{DEEPSEEK_MODEL} available")
except Exception as exc:
    fail("GET /models + API key authorization", exc)

try:
    text = chat(
        system="Connectivity test. Obey exact output instruction.",
        user="Reply exactly: FLASH_OK",
        thinking=False,
        reasoning_effort="low",
        max_tokens=30,
        temperature=0.0,
    )
    if text.strip() != "FLASH_OK":
        fail("non-thinking chat", f"unexpected response: {text[:120]!r}")
    ok("non-thinking /chat/completions", "FLASH_OK")
except Exception as exc:
    fail("non-thinking /chat/completions", exc)

try:
    obj = json_chat(
        system="Return valid JSON only.",
        user='Return exactly this JSON object: {"status":"JSON_OK","number":7}',
        thinking=False,
        reasoning_effort="low",
        max_tokens=80,
    )
    if obj.get("status") != "JSON_OK" or obj.get("number") != 7:
        fail("JSON mode", obj)
    ok("JSON output mode", json.dumps(obj, ensure_ascii=False))
except Exception as exc:
    fail("JSON output mode", exc)

try:
    text = chat(
        system="Connectivity test. Give a very short final answer.",
        user="What is 2+3? Reply only with the number.",
        thinking=True,
        reasoning_effort="low",
        max_tokens=80,
        temperature=0.0,
    )
    if text.strip() != "5":
        fail("thinking mode", f"unexpected response: {text[:120]!r}")
    ok("thinking mode", "5")
except Exception as exc:
    fail("thinking mode", exc)

print("\nALL LIVE DEEPSEEK DIAGNOSTICS PASSED")
