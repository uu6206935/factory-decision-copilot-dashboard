"""Optional MLflow logging adapter.

Install requirements-enterprise.txt and set MLFLOW_TRACKING_URI before using.
No MLflow dependency is required for the default laptop demo.
"""
from __future__ import annotations


def log_investigation_run(case_id: int, payload: dict) -> str | None:
    try:
        import mlflow
    except Exception:
        return None
    with mlflow.start_run(run_name=f"quality-case-{case_id}") as run:
        mlflow.log_param("target_id", payload.get("vehicle_id") or "")
        mlflow.log_param("defect_type", payload.get("defect_type") or "")
        candidates=payload.get("candidates") or []
        if candidates:
            mlflow.log_metric("top_investigation_priority", float(candidates[0].get("score",0)))
            mlflow.set_tag("top_candidate", candidates[0].get("label", ""))
        mlflow.set_tag("case_id", str(case_id))
        return run.info.run_id
