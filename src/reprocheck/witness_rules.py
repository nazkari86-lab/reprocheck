from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


EdgeKey = tuple[str, str, str]


@dataclass(frozen=True)
class RuleContext:
    source: dict[str, Any]
    finding_index: int
    nodes: dict[str, dict[str, Any]]
    edges: tuple[dict[str, Any], ...]
    artifact_dir: Path | None

    @property
    def finding_id(self) -> str:
        return f"finding:{self.finding_index}"

    @property
    def finding(self) -> dict[str, Any]:
        return self.nodes[self.finding_id]


@dataclass(frozen=True)
class WitnessCandidate:
    node_ids: tuple[str, ...]
    edge_keys: tuple[EdgeKey, ...]
    rule_inputs: dict[str, Any]


@dataclass(frozen=True)
class WitnessRule:
    finding_code: str
    verifier_rule: str
    requires_artifacts: bool
    enumerate_candidates: Callable[[RuleContext], list[WitnessCandidate]]
    semantic_errors: Callable[[dict[str, Any]], list[str]]


def get_witness_rule(finding_code: str) -> WitnessRule:
    try:
        return WITNESS_RULES[finding_code]
    except KeyError as error:
        supported = ", ".join(sorted(WITNESS_RULES))
        raise ValueError(
            f"unsupported minimal-witness finding code: {finding_code}; supported: {supported}"
        ) from error


def enumerate_mismatch_candidates(context: RuleContext) -> list[WitnessCandidate]:
    finding_attributes = _attributes(context.finding, "finding")
    assert finding_attributes is not None
    source_claim = _source_claim(context.source, finding_attributes)
    tolerance = _finite_number(source_claim.get("tolerance"), "claim tolerance")
    observed = _finite_number(source_claim.get("observed"), "observed metric")
    candidates: list[WitnessCandidate] = []
    for claim_id in _predecessors(context.edges, context.finding_id, "raises"):
        claim = context.nodes.get(claim_id)
        if claim is None or claim.get("kind") != "claim":
            continue
        for metric_id, report_id in itertools.product(
            _predecessors(context.edges, claim_id, "contradicts"),
            _predecessors(context.edges, claim_id, "contains"),
        ):
            metric = context.nodes.get(metric_id)
            report = context.nodes.get(report_id)
            if metric is None or report is None or metric.get("kind") != "metric":
                continue
            metric_attributes = _attributes(metric, "metric", strict=False)
            report_attributes = _attributes(report, "report", strict=False)
            if not metric_attributes or not report_attributes:
                continue
            if report.get("kind") != "artifact" or report_attributes.get("role") != "report":
                continue
            value = metric_attributes.get("value")
            if not _same_number(value, observed):
                continue
            for source_id in sorted(
                set(_predecessors(context.edges, metric_id, "reports"))
                | set(_predecessors(context.edges, metric_id, "recomputes"))
            ):
                source = context.nodes.get(source_id)
                if source is None or source.get("kind") != "artifact":
                    continue
                source_relation = _one_relation(
                    context.edges, source_id, metric_id, {"reports", "recomputes"}
                )
                if source_relation is None:
                    continue
                candidates.append(
                    _candidate(
                        {context.finding_id, claim_id, metric_id, report_id, source_id},
                        {
                            (claim_id, context.finding_id, "raises"),
                            (metric_id, claim_id, "contradicts"),
                            (report_id, claim_id, "contains"),
                            (source_id, metric_id, source_relation),
                        },
                        {"tolerance": tolerance, "observed": observed},
                    )
                )
    return candidates


def enumerate_metric_conflict_candidates(context: RuleContext) -> list[WitnessCandidate]:
    finding = _attributes(context.finding, "finding")
    assert finding is not None
    metric_name = finding.get("metric")
    sources = finding.get("sources")
    values = finding.get("values")
    if not isinstance(metric_name, str) or not metric_name:
        raise ValueError("metric conflict finding has no metric name")
    if (
        not isinstance(sources, list)
        or not isinstance(values, list)
        or len(sources) != 2
        or len(values) != 2
        or not all(isinstance(source, str) for source in sources)
    ):
        raise ValueError("metric conflict finding must bind exactly two sources and values")
    source_values = sorted(
        (
            str(source),
            _finite_number(value, f"metric conflict value for {source}"),
        )
        for source, value in zip(sources, values, strict=True)
    )
    if source_values[0][0] == source_values[1][0]:
        raise ValueError("metric conflict finding sources must be distinct")
    tolerance = _audit_tolerance(context)
    if abs(source_values[0][1] - source_values[1][1]) <= tolerance:
        raise ValueError("metric conflict values do not exceed audit tolerance")

    metric_ids = [
        node_id
        for node_id in _predecessors(context.edges, context.finding_id, "flags")
        if context.nodes.get(node_id, {}).get("kind") == "metric"
    ]
    candidates: list[WitnessCandidate] = []
    for left_id, right_id in itertools.combinations(metric_ids, 2):
        left = _attributes(context.nodes[left_id], "metric", strict=False)
        right = _attributes(context.nodes[right_id], "metric", strict=False)
        if not left or not right:
            continue
        if left.get("name") != metric_name or right.get("name") != metric_name:
            continue
        observed_pairs = sorted(
            (
                str(attributes.get("source")),
                _finite_number(attributes.get("value"), "metric observation"),
            )
            for attributes in (left, right)
        )
        if observed_pairs != source_values:
            continue
        bindings: list[list[tuple[str, str]]] = []
        for metric_id, attributes in ((left_id, left), (right_id, right)):
            source_name = attributes["source"]
            available: list[tuple[str, str]] = []
            for artifact_id in sorted(
                set(_predecessors(context.edges, metric_id, "reports"))
                | set(_predecessors(context.edges, metric_id, "recomputes"))
            ):
                artifact = context.nodes.get(artifact_id)
                artifact_attributes = (
                    _attributes(artifact, "artifact", strict=False) if artifact else None
                )
                if not artifact_attributes or artifact_attributes.get("filename") != source_name:
                    continue
                relation = _one_relation(
                    context.edges, artifact_id, metric_id, {"reports", "recomputes"}
                )
                if relation:
                    available.append((artifact_id, relation))
            bindings.append(available)
        for left_binding, right_binding in itertools.product(*bindings):
            left_artifact, left_relation = left_binding
            right_artifact, right_relation = right_binding
            if left_artifact == right_artifact:
                continue
            candidates.append(
                _candidate(
                    {
                        context.finding_id,
                        left_id,
                        right_id,
                        left_artifact,
                        right_artifact,
                    },
                    {
                        (left_id, context.finding_id, "flags"),
                        (right_id, context.finding_id, "flags"),
                        (left_artifact, left_id, left_relation),
                        (right_artifact, right_id, right_relation),
                    },
                    {
                        "metric": metric_name,
                        "source_values": [
                            {"source": source, "value": value} for source, value in source_values
                        ],
                        "tolerance": tolerance,
                    },
                )
            )
    return candidates


def enumerate_exact_overlap_candidates(context: RuleContext) -> list[WitnessCandidate]:
    if context.artifact_dir is None:
        raise ValueError("artifact-dir is required for exact_split_overlap witness")
    finding = _attributes(context.finding, "finding")
    assert finding is not None
    expected_overlap, expected_test_rows = _parse_overlap_message(finding.get("message"))
    identity_columns = _identity_columns(context)
    flagged = _predecessors(context.edges, context.finding_id, "flags")
    train_ids = _artifacts_with_role(context, flagged, "train")
    test_ids = _artifacts_with_role(context, flagged, "test")
    candidates: list[WitnessCandidate] = []
    for train_id, test_id in itertools.product(train_ids, test_ids):
        if train_id == test_id:
            continue
        train_path = _artifact_path(context, train_id)
        test_path = _artifact_path(context, test_id)
        overlap = recompute_exact_overlap(train_path, test_path, identity_columns)
        if overlap["exact_overlap_test_rows"] != expected_overlap:
            continue
        if overlap["test_rows"] != expected_test_rows:
            continue
        candidates.append(
            _candidate(
                {context.finding_id, train_id, test_id},
                {
                    (train_id, context.finding_id, "flags"),
                    (test_id, context.finding_id, "flags"),
                },
                {"identity_columns": identity_columns, **overlap},
            )
        )
    return candidates


def recompute_exact_overlap(
    train_path: Path, test_path: Path, identity_columns: list[str]
) -> dict[str, Any]:
    train_rows, train_fields = _read_csv(train_path)
    test_rows, test_fields = _read_csv(test_path)
    if not identity_columns:
        raise ValueError("exact overlap witness requires declared identity columns")
    missing = [
        column
        for column in identity_columns
        if column not in train_fields or column not in test_fields
    ]
    if missing:
        raise ValueError("identity columns missing from one split: " + ", ".join(missing))
    train_hashes = {_row_fingerprint(row, identity_columns) for row in train_rows}
    overlapping = [
        _row_fingerprint(row, identity_columns)
        for row in test_rows
        if _row_fingerprint(row, identity_columns) in train_hashes
    ]
    if not overlapping:
        raise ValueError("bound train/test artifacts have no exact overlap")
    return {
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "exact_overlap_test_rows": len(overlapping),
        "overlap_identity_sha256": sorted(set(overlapping)),
    }


def mismatch_semantic_errors(witness: dict[str, Any]) -> list[str]:
    nodes, edges, errors = _witness_parts(witness)
    if errors:
        return errors
    finding_id = f"finding:{witness.get('finding_index')}"
    claims = _nodes_of_kind(nodes, "claim")
    metrics = _nodes_of_kind(nodes, "metric")
    artifacts = _nodes_of_kind(nodes, "artifact")
    if (
        set(_nodes_of_kind(nodes, "finding")) != {finding_id}
        or len(claims) != 1
        or len(metrics) != 1
    ):
        return ["mismatch witness must contain exactly one finding, claim, and metric"]
    claim_id, metric_id = claims[0], metrics[0]
    finding = _attributes(nodes[finding_id], "finding", strict=False) or {}
    claim = _attributes(nodes[claim_id], "claim", strict=False) or {}
    metric = _attributes(nodes[metric_id], "metric", strict=False) or {}
    if finding.get("code") != "claim_metric_mismatch":
        errors.append("witness finding code is not claim_metric_mismatch")
    required = {
        (claim_id, finding_id, "raises"),
        (metric_id, claim_id, "contradicts"),
    }
    if not required <= edges:
        errors.append("mismatch witness is missing required contradiction relations")
    report_ids = [
        node_id
        for node_id in artifacts
        if (node_id, claim_id, "contains") in edges
        and (_attributes(nodes[node_id], "artifact", strict=False) or {}).get("role") == "report"
    ]
    source_ids = [
        node_id
        for node_id in artifacts
        if (node_id, metric_id, "reports") in edges or (node_id, metric_id, "recomputes") in edges
    ]
    if len(report_ids) != 1 or len(source_ids) != 1:
        errors.append("mismatch witness must bind one report and one metric source artifact")
    inputs = witness.get("rule_inputs")
    if not isinstance(inputs, dict):
        return errors + ["witness rule inputs must be an object"]
    try:
        tolerance = _finite_number(inputs.get("tolerance"), "claim tolerance")
        observed = _finite_number(inputs.get("observed"), "observed metric")
        claimed = _finite_number(claim.get("value"), "claimed metric")
        measured = _finite_number(metric.get("value"), "metric observation")
    except ValueError as error:
        return errors + [str(error)]
    if claim.get("metric") != metric.get("name"):
        errors.append("claim and metric names differ")
    if not math.isclose(measured, observed, rel_tol=0.0, abs_tol=1e-12):
        errors.append("witness metric does not match the finding's observed value")
    if abs(claimed - measured) <= tolerance:
        errors.append("witness values do not exceed the declared mismatch tolerance")
    return errors


def metric_conflict_semantic_errors(witness: dict[str, Any]) -> list[str]:
    nodes, edges, errors = _witness_parts(witness)
    if errors:
        return errors
    finding_id = f"finding:{witness.get('finding_index')}"
    metrics = _nodes_of_kind(nodes, "metric")
    artifacts = _nodes_of_kind(nodes, "artifact")
    if set(_nodes_of_kind(nodes, "finding")) != {finding_id} or len(metrics) != 2:
        return ["metric conflict witness must contain one finding and two metrics"]
    if len(artifacts) != 2:
        errors.append("metric conflict witness must contain two source artifacts")
    finding = _attributes(nodes[finding_id], "finding", strict=False) or {}
    if finding.get("code") != "metric_evidence_conflict":
        errors.append("witness finding code is not metric_evidence_conflict")
    inputs = witness.get("rule_inputs")
    if not isinstance(inputs, dict) or not isinstance(inputs.get("source_values"), list):
        return errors + ["metric conflict rule inputs are malformed"]
    observed: list[tuple[str, float]] = []
    for metric_id in metrics:
        metric = _attributes(nodes[metric_id], "metric", strict=False) or {}
        if (metric_id, finding_id, "flags") not in edges:
            errors.append("metric conflict witness is missing metric-to-finding flags relation")
        source_ids = [
            artifact_id
            for artifact_id in artifacts
            if (artifact_id, metric_id, "reports") in edges
            or (artifact_id, metric_id, "recomputes") in edges
        ]
        if len(source_ids) != 1:
            errors.append("each conflicting metric must bind exactly one source artifact")
        try:
            observed.append(
                (str(metric.get("source")), _finite_number(metric.get("value"), "metric value"))
            )
        except ValueError as error:
            errors.append(str(error))
    try:
        declared = sorted(
            (
                str(item["source"]),
                _finite_number(item["value"], "declared metric conflict value"),
            )
            for item in inputs["source_values"]
            if isinstance(item, dict)
        )
        tolerance = _finite_number(inputs.get("tolerance"), "audit tolerance")
    except (KeyError, ValueError) as error:
        return errors + [str(error)]
    if sorted(observed) != declared or len(declared) != 2:
        errors.append("metric conflict observations differ from canonical rule inputs")
    if len(declared) == 2 and abs(declared[0][1] - declared[1][1]) <= tolerance:
        errors.append("metric conflict values do not exceed audit tolerance")
    if any(
        (_attributes(nodes[item], "metric", strict=False) or {}).get("name") != inputs.get("metric")
        for item in metrics
    ):
        errors.append("metric conflict witness metric names differ")
    return errors


def exact_overlap_semantic_errors(witness: dict[str, Any]) -> list[str]:
    nodes, edges, errors = _witness_parts(witness)
    if errors:
        return errors
    finding_id = f"finding:{witness.get('finding_index')}"
    artifacts = _nodes_of_kind(nodes, "artifact")
    if set(_nodes_of_kind(nodes, "finding")) != {finding_id} or len(artifacts) != 2:
        return ["exact overlap witness must contain one finding and two artifacts"]
    roles = sorted(
        str((_attributes(nodes[node_id], "artifact", strict=False) or {}).get("role"))
        for node_id in artifacts
    )
    if roles != ["test", "train"]:
        errors.append("exact overlap witness must bind one train and one test artifact")
    if any((node_id, finding_id, "flags") not in edges for node_id in artifacts):
        errors.append("exact overlap witness is missing artifact-to-finding flags relations")
    inputs = witness.get("rule_inputs")
    if not isinstance(inputs, dict):
        return errors + ["exact overlap rule inputs must be an object"]
    columns = inputs.get("identity_columns")
    hashes = inputs.get("overlap_identity_sha256")
    if (
        not isinstance(columns, list)
        or not columns
        or not all(isinstance(item, str) for item in columns)
    ):
        errors.append("exact overlap identity columns are malformed")
    if (
        not isinstance(hashes, list)
        or not hashes
        or hashes != sorted(set(hashes))
        or not all(re.fullmatch(r"[0-9a-f]{64}", str(item)) for item in hashes)
    ):
        errors.append("exact overlap identity hashes are malformed")
    overlap = inputs.get("exact_overlap_test_rows")
    test_rows = inputs.get("test_rows")
    if not isinstance(overlap, int) or isinstance(overlap, bool) or overlap < 1:
        errors.append("exact overlap row count is malformed")
    if not isinstance(test_rows, int) or isinstance(test_rows, bool):
        errors.append("exact overlap test row count is malformed")
    elif isinstance(overlap, int) and not isinstance(overlap, bool) and test_rows < overlap:
        errors.append("exact overlap test row count is malformed")
    return errors


def _candidate(
    node_ids: set[str], edge_keys: set[EdgeKey], rule_inputs: dict[str, Any]
) -> WitnessCandidate:
    return WitnessCandidate(
        tuple(sorted(node_ids)),
        tuple(sorted(edge_keys)),
        rule_inputs,
    )


def _attributes(
    node: dict[str, Any] | None, label: str, *, strict: bool = True
) -> dict[str, Any] | None:
    attributes = node.get("attributes") if isinstance(node, dict) else None
    if isinstance(attributes, dict):
        return attributes
    if strict:
        raise ValueError(f"{label} attributes must be an object")
    return None


def _source_claim(source: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
    line = finding.get("line")
    matches = []
    for check in source.get("claims", []):
        if not isinstance(check, dict) or check.get("status") != "mismatch":
            continue
        claim = check.get("claim")
        if isinstance(claim, dict) and claim.get("line") == line:
            matches.append(check)
    if len(matches) != 1:
        raise ValueError("finding does not resolve to exactly one mismatched source claim")
    return matches[0]


def _predecessors(edges: tuple[dict[str, Any], ...], target: str, relation: str) -> list[str]:
    return sorted(
        {
            str(edge["source"])
            for edge in edges
            if edge.get("target") == target
            and edge.get("relation") == relation
            and isinstance(edge.get("source"), str)
        }
    )


def _one_relation(
    edges: tuple[dict[str, Any], ...], source: str, target: str, relations: set[str]
) -> str | None:
    matches = sorted(
        str(edge["relation"])
        for edge in edges
        if edge.get("source") == source
        and edge.get("target") == target
        and edge.get("relation") in relations
    )
    return matches[0] if matches else None


def _audit_tolerance(context: RuleContext) -> float:
    experiment = context.nodes.get("experiment:0")
    attributes = _attributes(experiment, "experiment")
    assert attributes is not None
    parameters = attributes.get("parameters")
    if not isinstance(parameters, dict):
        raise ValueError("audit experiment parameters must be an object")
    return _finite_number(parameters.get("tolerance"), "audit tolerance")


def _identity_columns(context: RuleContext) -> list[str]:
    experiment = context.nodes.get("experiment:0")
    attributes = _attributes(experiment, "experiment")
    assert attributes is not None
    parameters = attributes.get("parameters")
    columns = parameters.get("identity_columns") if isinstance(parameters, dict) else None
    if (
        not isinstance(columns, list)
        or not columns
        or not all(isinstance(item, str) and item for item in columns)
    ):
        raise ValueError("exact overlap witness requires declared non-empty identity columns")
    return list(columns)


def _artifacts_with_role(context: RuleContext, node_ids: list[str], role: str) -> list[str]:
    return [
        node_id
        for node_id in node_ids
        if context.nodes.get(node_id, {}).get("kind") == "artifact"
        and (_attributes(context.nodes[node_id], "artifact", strict=False) or {}).get("role")
        == role
    ]


def _artifact_path(context: RuleContext, artifact_id: str) -> Path:
    assert context.artifact_dir is not None
    attributes = _attributes(context.nodes[artifact_id], "artifact")
    assert attributes is not None
    filename = attributes.get("filename")
    role = attributes.get("role")
    if not isinstance(filename, str) or not isinstance(role, str):
        raise ValueError("artifact binding is malformed")
    root = context.artifact_dir.resolve()
    candidates = [root / filename, root / role / filename]
    matches = [path for path in candidates if path.is_file()]
    if len(matches) != 1:
        raise ValueError(f"artifact binding must resolve exactly once: {role}/{filename}")
    return matches[0]


def _parse_overlap_message(value: object) -> tuple[int, int]:
    if not isinstance(value, str):
        raise ValueError("exact overlap finding message is malformed")
    match = re.fullmatch(r"(\d+)/(\d+) test rows also occur in train\.", value)
    if not match:
        raise ValueError("exact overlap finding message is not canonical")
    return int(match.group(1)), int(match.group(2))


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or any(not field for field in reader.fieldnames):
            raise ValueError(f"CSV has an invalid header: {path.name}")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"CSV has duplicate headers: {path.name}")
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV has a malformed row at line {line_number}: {path.name}")
            rows.append({key: value or "" for key, value in row.items()})
    if not rows:
        raise ValueError(f"CSV split is empty: {path.name}")
    return rows, list(reader.fieldnames)


def _row_fingerprint(row: dict[str, str], columns: list[str]) -> str:
    payload = json.dumps(
        [row[column] for column in columns], ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _witness_parts(
    witness: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[EdgeKey], list[str]]:
    raw_nodes = witness.get("nodes")
    raw_edges = witness.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        return {}, set(), ["witness nodes and edges must be arrays"]
    nodes = {
        str(node.get("id")): node
        for node in raw_nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    edges = {
        (str(edge.get("source")), str(edge.get("target")), str(edge.get("relation")))
        for edge in raw_edges
        if isinstance(edge, dict)
    }
    return nodes, edges, []


def _nodes_of_kind(nodes: dict[str, dict[str, Any]], kind: str) -> list[str]:
    return sorted(node_id for node_id, node in nodes.items() if node.get("kind") == kind)


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _same_number(value: object, expected: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-12)
    )


WITNESS_RULES = {
    rule.finding_code: rule
    for rule in (
        WitnessRule(
            "claim_metric_mismatch",
            "claim_metric_mismatch.source_grounded.v2",
            False,
            enumerate_mismatch_candidates,
            mismatch_semantic_errors,
        ),
        WitnessRule(
            "metric_evidence_conflict",
            "metric_evidence_conflict.source_grounded.v1",
            False,
            enumerate_metric_conflict_candidates,
            metric_conflict_semantic_errors,
        ),
        WitnessRule(
            "exact_split_overlap",
            "exact_split_overlap.artifact_recomputed.v1",
            True,
            enumerate_exact_overlap_candidates,
            exact_overlap_semantic_errors,
        ),
    )
}
