from __future__ import annotations
import re

PATTERNS = [
    (re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I), "<EMAIL>"),
    (re.compile(r"(?<!\d)(?:\+?81[- ]?)?0\d{1,4}[- ]?\d{1,4}[- ]?\d{3,4}(?!\d)"), "<PHONE>"),
]

def redact(text: str) -> str:
    out=text
    for rx, repl in PATTERNS:
        out=rx.sub(repl, out)
    return out
