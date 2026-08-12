from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .certificate import verify_certificate_file
from .witness_rules import RuleContext, get_witness_rule


WITNESS_SCHEMA_VERSION = "reprocheck.witness.v1"
WITNESS_RULE = "claim_metric_mismatch.source_grounded.v1"
WITNESS_SCHEMA_VERSION_V2 = "reprocheck.witness.v2"


def build_witness_file(
    certificate: Path,
    finding_index: int,
    output: Path,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
    errors = verify_certificate_file(certificate, artifact_dir)
    if errors:
        raise ValueError("source certificate is invalid: " + "; ".join(errors))
    payload = _load_object(certificate, "source certificate")
    witness = build_witness_payload(payload, finding_index, artifact_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(witness, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return witness


def build_witness_payload(
    source: dict[str, Any], finding_index: int, artifact_dir: Path | None = None
) -> dict[str, Any]:
    graph = source.get("evidence_graph")
    if not isinstance(graph, dict):
        raise ValueError("source certificate has no evidence graph")
    nodes = _objects_by_id(graph.get("nodes"))
    edges = tuple(_object_list(graph.get("edges"), "evidence graph edges"))
    finding_id = f"finding:{finding_index}"
    finding = nodes.get(finding_id)
    if finding is None:
        raise ValueError(f"finding index does not exist: {finding_index}")
    attributes = finding.get("attributes")
    if not isinstance(attributes, dict) or not isinstance(attributes.get("code"), str):
        raise ValueError("finding has no valid code")
    finding_code = attributes["code"]
    rule = get_witness_rule(finding_code)
    if rule.requires_artifacts and artifact_dir is None:
        raise ValueError(f"artifact-dir is required for {finding_code} witness")
    context = RuleContext(source, finding_index, nodes, edges, artifact_dir)
    candidates = rule.enumerate_candidates(context)
    if not candidates:
        raise ValueError(f"no source-grounded witness exists for {finding_code} finding")
    candidates.sort(
        key=lambda candidate: (
            len(candidate.node_ids),
            len(candidate.edge_keys),
            candidate.node_ids,
            candidate.edge_keys,
            json.dumps(candidate.rule_inputs, sort_keys=True, separators=(",", ":")),
        )
    )
    selected = candidates[0]
    edge_by_key = {
        (str(edge.get("source")), str(edge.get("target")), str(edge.get("relation"))): edge
        for edge in edges
    }
    try:
        selected_edges = [edge_by_key[key] for key in selected.edge_keys]
    except KeyError as error:
        raise ValueError(f"witness candidate references a missing graph edge: {error}") from error
    witness = {
        "schema_version": WITNESS_SCHEMA_VERSION_V2,
        "tool_version": source.get("tool_version"),
        "source_certificate_sha256": source.get("certificate_sha256"),
        "source_graph_sha256": graph.get("graph_sha256"),
        "finding_index": finding_index,
        "finding_code": finding_code,
        "verifier_rule": rule.verifier_rule,
        "rule_inputs": selected.rule_inputs,
        "nodes": [nodes[node_id] for node_id in selected.node_ids],
        "edges": selected_edges,
        "minimality": {
            "method": "complete typed-grounding enumeration",
            "candidate_groundings_checked": len(candidates),
            "minimum_node_count": len(selected.node_ids),
            "minimum_edge_count": len(selected.edge_keys),
            "tie_break": "node count, edge count, lexicographic node ids and edge keys",
            "scope": rule.verifier_rule,
        },
        "witness_sha256": "",
    }
    semantic_errors = rule.semantic_errors(witness)
    if semantic_errors:
        raise ValueError("constructed witness violates its rule: " + "; ".join(semantic_errors))
    witness["witness_sha256"] = witness_digest(witness)
    return witness


def _build_v1_mismatch_payload(source: dict[str, Any], finding_index: int) -> dict[str, Any]:
    witness = build_witness_payload(source, finding_index)
    if witness.get("finding_code") != "claim_metric_mismatch":
        raise ValueError("only claim_metric_mismatch findings have a v1 minimal witness")
    witness["schema_version"] = WITNESS_SCHEMA_VERSION
    witness["verifier_rule"] = WITNESS_RULE
    witness["minimality"]["tie_break"] = "lexicographic node ids"
    witness["minimality"]["scope"] = WITNESS_RULE
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
        if witness.get("schema_version") == WITNESS_SCHEMA_VERSION:
            rebuilt = _build_v1_mismatch_payload(source, int(witness["finding_index"]))
        else:
            rebuilt = build_witness_payload(
                source,
                int(witness["finding_index"]),
                artifact_dir,
            )
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
    if witness.get("schema_version") == WITNESS_SCHEMA_VERSION_V2:
        return _validate_v2_witness_shape(witness)
    return _validate_v1_witness_shape(witness)


def _validate_v1_witness_shape(witness: dict[str, Any]) -> list[str]:
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


def _validate_v2_witness_shape(witness: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if witness.get("schema_version") != WITNESS_SCHEMA_VERSION_V2:
        errors.append("unsupported witness schema version")
    finding_code = witness.get("finding_code")
    if not isinstance(finding_code, str):
        errors.append("witness finding code must be a string")
        return errors
    try:
        rule = get_witness_rule(finding_code)
    except ValueError as error:
        return errors + [str(error)]
    if witness.get("verifier_rule") != rule.verifier_rule:
        errors.append("unsupported witness verifier rule")
    nodes = witness.get("nodes")
    edges = witness.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return errors + ["witness nodes and edges must be arrays"]
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            errors.append(f"malformed witness node at index {index}")
            continue
        node_id = node["id"]
        if node_id in node_ids:
            errors.append(f"duplicate witness node id: {node_id}")
        node_ids.add(node_id)
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
    minimality = witness.get("minimality")
    if not isinstance(minimality, dict):
        errors.append("witness minimality must be an object")
    else:
        if minimality.get("minimum_node_count") != len(nodes):
            errors.append("witness minimality node count is inconsistent")
        if minimality.get("minimum_edge_count") != len(edges):
            errors.append("witness minimality edge count is inconsistent")
        if minimality.get("scope") != rule.verifier_rule:
            errors.append("witness minimality scope differs from verifier rule")
    errors.extend(rule.semantic_errors(witness))
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
