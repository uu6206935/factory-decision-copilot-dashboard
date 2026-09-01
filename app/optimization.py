from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class MaintenanceTask:
    equipment_id: str
    duration_min: int
    risk_score: float
    earliest_min: int = 0
    latest_min: int = 480


@dataclass
class ScheduledTask:
    equipment_id: str
    start_min: int
    end_min: int
    risk_score: float
    solver: str


def _greedy(tasks: list[MaintenanceTask], horizon_min: int, technicians: int) -> list[ScheduledTask]:
    lanes = [0 for _ in range(max(1, technicians))]
    out: list[ScheduledTask] = []
    for t in sorted(tasks, key=lambda x: x.risk_score, reverse=True):
        lane = min(range(len(lanes)), key=lambda i: lanes[i])
        start = max(int(t.earliest_min), lanes[lane])
        end = min(horizon_min, start + int(t.duration_min))
        if end <= start or start > t.latest_min:
            continue
        out.append(ScheduledTask(t.equipment_id, start, end, t.risk_score, "greedy-fallback"))
        lanes[lane] = end
    return out


def schedule_maintenance(tasks: list[MaintenanceTask], horizon_min: int = 480, technicians: int = 1) -> list[ScheduledTask]:
    """Risk-weighted maintenance scheduling with optional OR-Tools CP-SAT."""
    try:
        from ortools.sat.python import cp_model  # type: ignore
    except Exception:
        return _greedy(tasks, horizon_min, technicians)
    if not tasks:
        return []
    model = cp_model.CpModel()
    starts, ends, intervals = [], [], []
    for i, t in enumerate(tasks):
        start = model.new_int_var(max(0, t.earliest_min), min(horizon_min, t.latest_min), f"s{i}")
        end = model.new_int_var(0, horizon_min, f"e{i}")
        interval = model.new_interval_var(start, t.duration_min, end, f"iv{i}")
        starts.append(start); ends.append(end); intervals.append(interval)
    if technicians <= 1:
        model.add_no_overlap(intervals)
    else:
        demands = [1] * len(intervals)
        model.add_cumulative(intervals, demands, technicians)
    # High risk should be scheduled earlier. Integerize score for CP-SAT.
    model.minimize(sum(int(max(1, t.risk_score * 1000)) * starts[i] for i, t in enumerate(tasks)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 2.0
    status = solver.solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return _greedy(tasks, horizon_min, technicians)
    out = [ScheduledTask(t.equipment_id, solver.value(starts[i]), solver.value(ends[i]), t.risk_score, "ortools-cp-sat") for i, t in enumerate(tasks)]
    return sorted(out, key=lambda x: x.start_min)


def plan_from_health(health_rows: list[dict[str, Any]], horizon_min: int = 480, technicians: int = 1) -> dict:
    tasks = []
    for row in health_rows:
        risk = float(row.get("risk_score", 0))
        if risk < 0.20:
            continue
        duration = 20 if risk < 0.4 else 35 if risk < 0.7 else 50
        tasks.append(MaintenanceTask(str(row["equipment_id"]), duration, risk))
    scheduled = schedule_maintenance(tasks, horizon_min, technicians)
    return {"horizon_min": horizon_min, "technicians": technicians, "items": [asdict(x) for x in scheduled], "solver": scheduled[0].solver if scheduled else "none"}
