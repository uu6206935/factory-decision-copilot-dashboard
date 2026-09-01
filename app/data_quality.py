from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from .schema import ROLE_REQUIRED, choose_role_tables_multi, load_profile_frame, scan_tables

def run_data_quality(data_dir: Path) -> dict:
    profiles, warnings = scan_tables(data_dir)
    grouped = choose_role_tables_multi(profiles)
    checks=[]
    for role, req in ROLE_REQUIRED.items():
        ps=grouped.get(role, [])
        checks.append({"check": f"role:{role}", "status": "pass" if ps else "skip", "detail": f"{len(ps)} table(s) detected" if ps else "optional dataset not present; dependent modules are disabled"})
        for prof in ps:
            df=load_profile_frame(data_dir, prof)
            missing=[c for c in req if c not in df.columns]
            checks.append({"check": f"required_columns:{prof.label}", "status":"pass" if not missing else "fail", "detail":"ok" if not missing else f"missing {missing}"})
            for c in req & set(df.columns):
                ratio=float(df[c].isna().mean()) if len(df) else 1.0
                checks.append({"check":f"null_rate:{prof.label}:{c}", "status":"pass" if ratio < 0.05 else ("warn" if ratio < 0.25 else "fail"), "detail":f"{ratio*100:.1f}% null"})
    status="pass" if not any(x["status"]=="fail" for x in checks) else "fail"
    available_roles=[role for role, ps in grouped.items() if ps]
    return {"status": status, "checks": checks, "warnings": warnings, "summary": dict(Counter(x["status"] for x in checks)), "available_roles": available_roles, "adaptive_mode": True}
