from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.deepseek import available, chat, status

s = status()
print(f"Provider: {s['provider']}")
print(f"Model: {s['model']}")
print(f"Configured: {s['configured']}")
print(f"FULL sample values: {s['send_sample_values']}")
print(f"FULL document text: {s['send_document_text']}")
print(f"FULL structured evidence: {s['send_structured_evidence']}")
if not available():
    raise SystemExit("DeepSeek API key is not configured.")
answer = chat(
    system="You are a connectivity test. Follow the user's exact response instruction.",
    user="Reply exactly: OK",
    thinking=False,
    reasoning_effort="low",
    max_tokens=20,
    temperature=0.0,
)
print("API response:", answer)
if answer.strip().upper() != "OK":
    raise SystemExit("API connected, but exact-response check did not return OK.")
print("Connection test complete: PASS")
