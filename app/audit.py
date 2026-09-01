from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def append_audit(runtime_dir: Path, payload: dict) -> None:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
    with (runtime_dir / "audit.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
