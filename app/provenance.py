from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .config import FILE_ALLOWLIST, MAX_FILE_MB
from .text_utils import repair_utf8_as_cp932

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def build_file_catalog(data_dir: Path) -> list[dict]:
    out=[]
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in FILE_ALLOWLIST:
            continue
        st=path.stat(); mb=st.st_size/(1024*1024)
        item={"relative_path": repair_utf8_as_cp932(str(path.relative_to(data_dir))), "extension": path.suffix.lower(), "size_bytes": st.st_size, "size_mb": round(mb,3), "modified_at": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(), "allowed": mb <= MAX_FILE_MB}
        item["sha256"] = sha256_file(path) if item["allowed"] else None
        out.append(item)
    return out
