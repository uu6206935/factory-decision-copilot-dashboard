from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Evidence:
    kind: str
    text: str
    source: str | None = None
    strength: float = 0.5


@dataclass
class Candidate:
    label: str
    score: float
    category: str
    evidence: list[Evidence] = field(default_factory=list)
    recommended_checks: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    name: str
    production_loss_units: float
    expected_defects: float
    expected_quality_loss_index: float
    note: str


@dataclass
class AnalysisResult:
    title: str
    vehicle_id: str | None
    defect_type: str | None
    summary: list[str]
    candidates: list[Candidate]
    scenarios: list[Scenario]
    tables: dict[str, str]
    graph_nodes: list[dict]
    graph_edges: list[tuple[str, str]]
    data_roles: dict[str, str]
    mode: str = "root_cause"
    active_modules: list[str] = field(default_factory=list)
    missing_for_deeper: list[str] = field(default_factory=list)
