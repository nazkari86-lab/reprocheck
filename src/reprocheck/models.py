from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Claim:
    metric: str
    value: float
    raw_text: str
    line: int
    context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ClaimCheck:
    claim: Claim
    status: Literal["verified", "supported", "mismatch", "no_evidence"]
    observed: float | None
    difference: float | None
    tolerance: float
    evidence_level: Literal["reported", "recomputed"] | None = None
    display_kind: Literal["percentage", "scalar"] = "scalar"


@dataclass(frozen=True)
class SourceArtifact:
    role: str
    filename: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class MetricObservation:
    value: float
    source: str
    method: str
    sample_count: int | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    evidence_level: Literal["reported", "recomputed"] = "reported"
    context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceNode:
    id: str
    kind: str
    label: str
    attributes: dict[str, Any]
    digest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceEdge:
    source: str
    target: str
    relation: str
    digest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceGraph:
    schema_version: str
    root_id: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    graph_sha256: str


@dataclass
class LeakageAudit:
    train_rows: int
    test_rows: int
    identity_columns: list[str]
    exact_overlap_test_rows: int
    normalized_overlap_test_rows: int
    exact_overlap_rate: float
    normalized_overlap_rate: float
    near_overlap_test_rows: int
    near_overlap_rate: float
    train_duplicate_rows: int
    test_duplicate_rows: int
    normalized_only_overlap_test_rows: int = 0
    normalized_only_overlap_rate: float = 0.0
    overlapping_group_count: int = 0
    group_column: str | None = None
    overlapping_groups: list[str] = field(default_factory=list)
    exact_overlap_examples: list[dict[str, str]] = field(default_factory=list)
    normalized_overlap_examples: list[dict[str, str]] = field(default_factory=list)
    near_overlap_examples: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class NotebookAudit:
    filename: str
    total_cells: int
    code_cells: int
    executed_code_cells: int
    has_random_seed: bool
    execution_order_monotonic: bool
    duplicate_execution_counts: list[int]
    findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AuditReport:
    schema_version: str
    tool_version: str
    created_at: str
    status: Literal["passed", "needs_review"]
    artifacts: list[SourceArtifact]
    claims: list[ClaimCheck]
    observed_metrics: dict[str, float]
    metric_evidence: dict[str, MetricObservation]
    leakage: LeakageAudit | None
    notebook: NotebookAudit | None
    findings: list[dict[str, Any]]
    parameters: dict[str, Any]
    evidence_graph: EvidenceGraph | None = None
    certificate_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
