from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

from .certificate import verify_certificate_file


WITNESS_SCHEMA_VERSION = "reprocheck.witness.v1"
WITNESS_RULE = "claim_metric_mismatch.source_grounded.v1"


def build_witness_file(certificate: Path, finding_index: int, output: Path) -> dict[str, Any]:
    errors = verify_certificate_file(certificate)
    if errors:
        raise ValueError("source certificate is invalid: " + "; ".join(errors))
    payload = _load_object(certificate, "source certificate")
    witness = build_witness_payload(payload, finding_index)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(witness, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return witness


def build_witness_payload(source: dict[str, Any], finding_index: int) -> dict[str, Any]:
    graph = source.get("evidence_graph")
    if not isinstance(graph, dict):
        raise ValueError("source certificate has no evidence graph")
    nodes = _objects_by_id(graph.get("nodes"))
    edges = _object_list(graph.get("edges"), "evidence graph edges")
    finding_id = f"finding:{finding_index}"
    finding = nodes.get(finding_id)
    if finding is None:
        raise ValueError(f"finding index does not exist: {finding_index}")
    attributes = finding.get("attributes")
    if not isinstance(attributes, dict) or attributes.get("code") != "claim_metric_mismatch":
        raise ValueError("only claim_metric_mismatch findings have a v1 minimal witness")

    source_claim = _source_claim(source, attributes)
    tolerance = _finite_number(source_claim.get("tolerance"), "claim tolerance")
    observed = _finite_number(source_claim.get("observed"), "observed metric")
    candidates: list[tuple[tuple[int, int, tuple[str, ...]], list[str], list[dict[str, Any]]]] = []

    claim_ids = _predecessors(edges, finding_id, "raises")
    for claim_id in claim_ids:
        claim = nodes.get(claim_id)
        if claim is None or claim.get("kind") != "claim":
            continue
        claim_attributes = claim.get("attributes")
        if not isinstance(claim_attributes, dict):
            continue
        metric_ids = _predecessors(edges, claim_id, "contradicts")
        report_ids = _predecessors(edges, claim_id, "contains")
        for metric_id, report_id in itertools.product(metric_ids, report_ids):
            metric = nodes.get(metric_id)
            report = nodes.get(report_id)
            if metric is None or report is None:
                continue
            metric_attributes = metric.get("attributes")
            report_attributes = report.get("attributes")
            if not isinstance(metric_attributes, dict) or not isinstance(report_attributes, dict):
                continue
            if report.get("kind") != "artifact" or report_attributes.get("role") != "report":
                continue
            metric_value = metric_attributes.get("value")
            if not isinstance(metric_value, (int, float)) or isinstance(metric_value, bool):
                continue
            if not math.isclose(float(metric_value), observed, rel_tol=0.0, abs_tol=1e-12):
                continue
            source_ids = sorted(
                set(_predecessors(edges, metric_id, "reports"))
                | set(_predecessors(edges, metric_id, "recomputes"))
            )
            for source_id in source_ids:
                source_artifact = nodes.get(source_id)
                if source_artifact is None or source_artifact.get("kind") != "artifact":
                    continue
                selected_ids = sorted({finding_id, claim_id, metric_id, report_id, source_id})
                selected_edges = _required_edges(
                    edges,
                    finding_id=finding_id,
                    claim_id=claim_id,
                    metric_id=metric_id,
                    report_id=report_id,
                    source_id=source_id,
                )
                if len(selected_edges) != 4:
                    continue
                key = (len(selected_ids), len(selected_edges), tuple(selected_ids))
                candidates.append((key, selected_ids, selected_edges))

    if not candidates:
        raise ValueError("no source-grounded mismatch witness exists for this finding")
    candidates.sort(key=lambda item: item[0])
    key, selected_ids, selected_edges = candidates[0]
    selected_nodes = [nodes[node_id] for node_id in selected_ids]
    witness = {
        "schema_version": WITNESS_SCHEMA_VERSION,
        "tool_version": source.get("tool_version"),
        "source_certificate_sha256": source.get("certificate_sha256"),
        "source_graph_sha256": graph.get("graph_sha256"),
        "finding_index": finding_index,
        "finding_code": "claim_metric_mismatch",
        "verifier_rule": WITNESS_RULE,
        "rule_inputs": {
            "tolerance": tolerance,
            "observed": observed,
        },
        "nodes": selected_nodes,
        "edges": selected_edges,
        "minimality": {
            "method": "complete typed-grounding enumeration",
            "candidate_groundings_checked": len(candidates),
            "minimum_node_count": key[0],
            "minimum_edge_count": key[1],
            "tie_break": "lexicographic node ids",
            "scope": WITNESS_RULE,
        },
        "witness_sha256": "",
    }
    witness["witness_sha256"] = witness_digest(witness)
    return witness


def verify_witness_file(
    witness_path: Path,
    certificate_path: Path,
    artifact_dir: Path | None = None,
) -> list[str]:
    try:
        witness = _load_object(witness_path, "witness")
        source = _load_object(certificate_path, "source certificate")
    except ValueError as error:
        return [str(error)]

    errors = verify_certificate_file(certificate_path, artifact_dir)
    expected_digest = witness.get("witness_sha256")
    try:
        actual_digest = witness_digest(witness)
    except (TypeError, ValueError) as error:
        return errors + [f"witness is not canonicalizable: {error}"]
    if expected_digest != actual_digest:
        errors.append("witness checksum does not match its payload")
    errors.extend(_validate_witness_shape(witness))
    if errors:
        return errors

    if witness.get("source_certificate_sha256") != source.get("certificate_sha256"):
        errors.append("witness references a different source certificate")
    graph = source.get("evidence_graph")
    if not isinstance(graph, dict) or witness.get("source_graph_sha256") != graph.get(
        "graph_sha256"
    ):
        errors.append("witness references a different source evidence graph")
    if errors:
        return errors

    try:
        rebuilt = build_witness_payload(source, int(witness["finding_index"]))
    except (TypeError, ValueError) as error:
        return [f"witness cannot be reproduced from source certificate: {error}"]
    if witness != rebuilt:
        errors.append("witness is not the canonical minimal witness for its source certificate")
    return errors


def witness_digest(payload: dict[str, Any]) -> str:
    canonical = dict(payload)
    canonical["witness_sha256"] = ""
    return _digest(canonical)


def _validate_witness_shape(witness: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if witness.get("schema_version") != WITNESS_SCHEMA_VERSION:
        errors.append("unsupported witness schema version")
    if witness.get("verifier_rule") != WITNESS_RULE:
        errors.append("unsupported witness verifier rule")
    nodes = witness.get("nodes")
    edges = witness.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return errors + ["witness nodes and edges must be arrays"]
    node_ids: set[str] = set()
    node_by_id: dict[str, dict[str, Any]] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            errors.append(f"malformed witness node at index {index}")
            continue
        node_id = node["id"]
        if node_id in node_ids:
            errors.append(f"duplicate witness node id: {node_id}")
        node_ids.add(node_id)
        node_by_id[node_id] = node
        canonical = {key: value for key, value in node.items() if key != "digest_sha256"}
        if node.get("digest_sha256") != _digest(canonical):
            errors.append(f"witness node digest mismatch at index {index}")
    edge_keys: set[tuple[object, object, object]] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append(f"malformed witness edge at index {index}")
            continue
        canonical = {key: value for key, value in edge.items() if key != "digest_sha256"}
        if edge.get("digest_sha256") != _digest(canonical):
            errors.append(f"witness edge digest mismatch at index {index}")
        key = (edge.get("source"), edge.get("target"), edge.get("relation"))
        if key in edge_keys:
            errors.append(f"duplicate witness edge at index {index}")
        edge_keys.add(key)
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            errors.append(f"witness edge references an unknown node at index {index}")
    errors.extend(_semantic_errors(witness, node_by_id, edge_keys))
    return errors


def _semantic_errors(
    witness: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: set[tuple[object, object, object]],
) -> list[str]:
    errors: list[str] = []
    finding_id = f"finding:{witness.get('finding_index')}"
    findings = [node_id for node_id, node in nodes.items() if node.get("kind") == "finding"]
    claims = [node_id for node_id, node in nodes.items() if node.get("kind") == "claim"]
    metrics = [node_id for node_id, node in nodes.items() if node.get("kind") == "metric"]
    artifacts = [node_id for node_id, node in nodes.items() if node.get("kind") == "artifact"]
    if findings != [finding_id] or len(claims) != 1 or len(metrics) != 1:
        return ["witness must contain exactly one finding, claim, and metric"]
    claim_id, metric_id = claims[0], metrics[0]
    finding_attributes = nodes[finding_id].get("attributes", {})
    claim_attributes = nodes[claim_id].get("attributes", {})
    metric_attributes = nodes[metric_id].get("attributes", {})
    if not all(
        isinstance(item, dict) for item in (finding_attributes, claim_attributes, metric_attributes)
    ):
        return ["witness semantic node attributes must be objects"]
    if finding_attributes.get("code") != "claim_metric_mismatch":
        errors.append("witness finding code is not claim_metric_mismatch")
    if (claim_id, finding_id, "raises") not in edges:
        errors.append("witness is missing the claim-to-finding relation")
    if (metric_id, claim_id, "contradicts") not in edges:
        errors.append("witness is missing the metric-to-claim contradiction")
    report_ids = [
        artifact_id
        for artifact_id in artifacts
        if (artifact_id, claim_id, "contains") in edges
        and isinstance(nodes[artifact_id].get("attributes"), dict)
        and nodes[artifact_id]["attributes"].get("role") == "report"
    ]
    source_ids = [
        artifact_id
        for artifact_id in artifacts
        if (artifact_id, metric_id, "reports") in edges
        or (artifact_id, metric_id, "recomputes") in edges
    ]
    if len(report_ids) != 1 or len(source_ids) != 1:
        errors.append("witness must ground claim and metric in exactly one source artifact each")
    rule_inputs = witness.get("rule_inputs")
    if not isinstance(rule_inputs, dict):
        errors.append("witness rule inputs must be an object")
        return errors
    try:
        tolerance = _finite_number(rule_inputs.get("tolerance"), "claim tolerance")
        observed = _finite_number(rule_inputs.get("observed"), "observed metric")
        claimed = _finite_number(claim_attributes.get("value"), "claimed metric")
        measured = _finite_number(metric_attributes.get("value"), "metric observation")
    except ValueError as error:
        errors.append(str(error))
        return errors
    if claim_attributes.get("metric") != metric_attributes.get("name"):
        errors.append("claim and metric names differ")
    if not math.isclose(measured, observed, rel_tol=0.0, abs_tol=1e-12):
        errors.append("witness metric does not match the finding's observed value")
    if abs(claimed - measured) <= tolerance:
        errors.append("witness values do not exceed the declared mismatch tolerance")
    minimality = witness.get("minimality")
    if not isinstance(minimality, dict) or minimality.get("minimum_node_count") != len(nodes):
        errors.append("witness minimality node count is inconsistent")
    if not isinstance(minimality, dict) or minimality.get("minimum_edge_count") != len(edges):
        errors.append("witness minimality edge count is inconsistent")
    return errors


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


def _required_edges(
    edges: list[dict[str, Any]],
    *,
    finding_id: str,
    claim_id: str,
    metric_id: str,
    report_id: str,
    source_id: str,
) -> list[dict[str, Any]]:
    required = {
        (claim_id, finding_id, "raises"),
        (metric_id, claim_id, "contradicts"),
        (report_id, claim_id, "contains"),
    }
    source_relations = {
        (source_id, metric_id, "reports"),
        (source_id, metric_id, "recomputes"),
    }
    selected = [
        edge
        for edge in edges
        if (edge.get("source"), edge.get("target"), edge.get("relation")) in required
        or (edge.get("source"), edge.get("target"), edge.get("relation")) in source_relations
    ]
    return sorted(
        selected,
        key=lambda edge: (
            str(edge.get("source")),
            str(edge.get("target")),
            str(edge.get("relation")),
        ),
    )


def _predecessors(edges: list[dict[str, Any]], target: str, relation: str) -> list[str]:
    return sorted(
        {
            str(edge["source"])
            for edge in edges
            if edge.get("target") == target
            and edge.get("relation") == relation
            and isinstance(edge.get("source"), str)
        }
    )


def _objects_by_id(value: object) -> dict[str, dict[str, Any]]:
    objects = _object_list(value, "evidence graph nodes")
    result: dict[str, dict[str, Any]] = {}
    for item in objects:
        node_id = item.get("id")
        if not isinstance(node_id, str):
            raise ValueError("evidence graph node id must be a string")
        result[node_id] = item
    return result


def _object_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be an array of objects")
    return value


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _finite_number(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
