from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

from .models import ClaimCheck, EvidenceEdge, EvidenceGraph, EvidenceNode, MetricObservation


GRAPH_SCHEMA_VERSION = "1.0"
_SPLIT_FINDINGS = {
    "exact_split_overlap",
    "normalized_split_overlap",
    "group_split_overlap",
    "near_text_split_overlap",
}
_NOTEBOOK_FINDINGS = {
    "fit_on_test_data",
    "fit_transform_on_test_data",
    "fit_on_test_dataflow",
    "non_monotonic_execution_order",
    "duplicate_execution_count",
    "missing_random_seed",
}


def build_evidence_graph(
    *,
    tool_version: str,
    status: str,
    artifacts: Iterable[Any],
    claims: list[ClaimCheck],
    metric_evidence: Mapping[str, MetricObservation],
    metric_observations: Iterable[tuple[str, MetricObservation]],
    findings: list[dict[str, object]],
    parameters: dict[str, Any],
) -> EvidenceGraph:
    nodes: list[EvidenceNode] = []
    edges: list[EvidenceEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()

    def add_node(node_id: str, kind: str, label: str, attributes: dict[str, Any]) -> None:
        payload = {"id": node_id, "kind": kind, "label": label, "attributes": attributes}
        nodes.append(EvidenceNode(**payload, digest_sha256=_digest(payload)))

    def add_edge(source: str, target: str, relation: str) -> None:
        key = (source, target, relation)
        if key in edge_keys:
            return
        edge_keys.add(key)
        payload = {"source": source, "target": target, "relation": relation}
        edges.append(EvidenceEdge(**payload, digest_sha256=_digest(payload)))

    add_node(
        "experiment:0",
        "experiment",
        "ReproCheck audit",
        {"status": status, "tool_version": tool_version, "parameters": parameters},
    )

    artifacts_by_filename: dict[str, list[str]] = {}
    artifacts_by_role: dict[str, list[str]] = {}
    for index, artifact in enumerate(artifacts):
        node_id = f"artifact:{index}"
        artifacts_by_filename.setdefault(artifact.filename, []).append(node_id)
        artifacts_by_role.setdefault(artifact.role, []).append(node_id)
        add_node(
            node_id,
            "artifact",
            f"{artifact.role}: {artifact.filename}",
            {
                "role": artifact.role,
                "filename": artifact.filename,
                "content_sha256": artifact.sha256,
                "size_bytes": artifact.size_bytes,
            },
        )
        add_edge(node_id, "experiment:0", "input_to")

    contexts = sorted(
        {(key, value) for check in claims for key, value in check.claim.context.items()}
        | {
            (key, value)
            for observation in metric_evidence.values()
            for key, value in observation.context.items()
        }
    )
    context_ids: dict[tuple[str, str], str] = {}
    for index, (key, value) in enumerate(contexts):
        node_id = f"context:{index}"
        context_ids[(key, value)] = node_id
        add_node(node_id, "context", f"{key}={value}", {"key": key, "value": value})
        add_edge(node_id, "experiment:0", "scopes")

    raw_observations = list(metric_observations or metric_evidence.items())
    ordered_observations = sorted(
        raw_observations,
        key=lambda item: (
            item[0],
            item[1].source,
            item[1].method,
            item[1].value,
            item[1].evidence_level,
            sorted(item[1].context.items()),
        ),
    )
    metric_nodes: dict[str, list[tuple[str, MetricObservation]]] = {}
    for index, (name, observation) in enumerate(ordered_observations):
        node_id = f"metric:{index}"
        metric_nodes.setdefault(name, []).append((node_id, observation))
        add_node(
            node_id,
            "metric",
            f"{name}={observation.value:.8g}",
            {
                "name": name,
                "value": observation.value,
                "source": observation.source,
                "method": observation.method,
                "sample_count": observation.sample_count,
                "evidence_level": observation.evidence_level,
                "context": observation.context,
            },
        )
        relation = "recomputes" if observation.evidence_level == "recomputed" else "reports"
        for artifact_id in artifacts_by_filename.get(observation.source, []):
            add_edge(artifact_id, node_id, relation)
        for item in observation.context.items():
            add_edge(context_ids[item], node_id, "qualifies")

    claim_ids: list[str] = []
    report_ids = artifacts_by_role.get("report", [])
    for index, check in enumerate(claims):
        node_id = f"claim:{index}"
        claim_ids.append(node_id)
        add_node(
            node_id,
            "claim",
            f"{check.claim.metric}={check.claim.value:.8g}",
            {
                "metric": check.claim.metric,
                "value": check.claim.value,
                "line": check.claim.line,
                "raw_text": check.claim.raw_text,
                "context": check.claim.context,
                "status": check.status,
                "observed": check.observed,
                "evidence_level": check.evidence_level,
            },
        )
        for artifact_id in report_ids:
            add_edge(artifact_id, node_id, "contains")
        for item in check.claim.context.items():
            add_edge(context_ids[item], node_id, "qualifies")
        if check.status != "no_evidence":
            for metric_id, observation in metric_nodes.get(check.claim.metric, []):
                if not _contexts_compatible(check.claim.context, observation.context):
                    continue
                relation = (
                    "supports"
                    if abs(check.claim.value - observation.value) <= check.tolerance
                    else "contradicts"
                )
                add_edge(metric_id, node_id, relation)

    for index, finding in enumerate(findings):
        node_id = f"finding:{index}"
        add_node(
            node_id,
            "finding",
            str(finding.get("code", "finding")),
            dict(finding),
        )
        add_edge("experiment:0", node_id, "reports_finding")
        line = finding.get("line")
        if isinstance(line, int):
            for claim_id, check in zip(claim_ids, claims):
                if check.claim.line == line:
                    add_edge(claim_id, node_id, "raises")
        code = finding.get("code")
        if code in _SPLIT_FINDINGS:
            for role in ("train", "test"):
                for artifact_id in artifacts_by_role.get(role, []):
                    add_edge(artifact_id, node_id, "flags")
        if code in _NOTEBOOK_FINDINGS:
            for artifact_id in artifacts_by_role.get("notebook", report_ids):
                add_edge(artifact_id, node_id, "flags")
        sources = finding.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, str):
                    for artifact_id in artifacts_by_filename.get(source, []):
                        add_edge(artifact_id, node_id, "flags")
            metric = finding.get("metric")
            if isinstance(metric, str):
                for metric_id, observation in metric_nodes.get(metric, []):
                    if observation.source in sources:
                        add_edge(metric_id, node_id, "flags")

    graph_payload = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "root_id": "experiment:0",
        "nodes": [node.to_dict() for node in nodes],
        "edges": [edge.to_dict() for edge in edges],
    }
    return EvidenceGraph(
        **graph_payload,
        graph_sha256=_digest(graph_payload),
    )


def verify_evidence_graph(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["evidence graph must be an object"]
    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["evidence graph nodes and edges must be arrays"]
    errors: list[str] = []
    node_ids: set[str] = set()
    node_kinds: dict[str, object] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if isinstance(node_id, str):
            if node_id in node_ids:
                errors.append(f"duplicate evidence graph node id: {node_id}")
            node_ids.add(node_id)
            node_kinds[node_id] = node.get("kind")
        expected = node.get("digest_sha256")
        canonical = {key: value for key, value in node.items() if key != "digest_sha256"}
        if expected != _digest(canonical):
            errors.append(f"evidence graph node digest mismatch at index {index}")
    edge_keys: set[tuple[object, object, object]] = set()
    valid_edges: list[tuple[str, str]] = []
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            continue
        expected = edge.get("digest_sha256")
        canonical = {key: value for key, value in edge.items() if key != "digest_sha256"}
        if expected != _digest(canonical):
            errors.append(f"evidence graph edge digest mismatch at index {index}")
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            errors.append(f"evidence graph edge references an unknown node at index {index}")
        else:
            source = str(edge["source"])
            target = str(edge["target"])
            valid_edges.append((source, target))
        edge_key = (edge.get("source"), edge.get("target"), edge.get("relation"))
        if edge_key in edge_keys:
            errors.append(f"duplicate evidence graph edge at index {index}")
        edge_keys.add(edge_key)
    root_id = payload.get("root_id")
    if root_id not in node_ids:
        errors.append("evidence graph root references an unknown node")
    elif node_kinds.get(str(root_id)) != "experiment":
        errors.append("evidence graph root must be an experiment node")
    if isinstance(root_id, str) and root_id in node_ids:
        errors.extend(_structural_errors(node_ids, valid_edges, root_id))
    expected_graph = payload.get("graph_sha256")
    canonical_graph = {key: value for key, value in payload.items() if key != "graph_sha256"}
    if expected_graph != _digest(canonical_graph):
        errors.append("evidence graph digest does not match its payload")
    return errors


def _structural_errors(node_ids: set[str], edges: list[tuple[str, str]], root_id: str) -> list[str]:
    undirected = {node_id: set() for node_id in node_ids}
    outgoing = {node_id: set() for node_id in node_ids}
    indegree = dict.fromkeys(node_ids, 0)
    for source, target in edges:
        undirected[source].add(target)
        undirected[target].add(source)
        if target not in outgoing[source]:
            outgoing[source].add(target)
            indegree[target] += 1

    connected = {root_id}
    frontier = [root_id]
    while frontier:
        current = frontier.pop()
        for neighbor in undirected[current] - connected:
            connected.add(neighbor)
            frontier.append(neighbor)

    errors = []
    if connected != node_ids:
        errors.append("evidence graph contains nodes disconnected from its root")

    ready = [node_id for node_id, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        current = ready.pop()
        visited += 1
        for target in outgoing[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if visited != len(node_ids):
        errors.append("evidence graph contains a directed cycle")
    return errors


def render_mermaid(graph: Mapping[str, Any]) -> str:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_names: dict[str, str] = {}
    lines = ["flowchart LR"]
    if isinstance(nodes, list):
        for index, node in enumerate(nodes):
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                continue
            name = f"n{index}"
            node_names[node["id"]] = name
            label = _mermaid_text(str(node.get("label", node["id"])))
            lines.append(f'  {name}["{label}"]')
    if isinstance(edges, list):
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = node_names.get(str(edge.get("source")))
            target = node_names.get(str(edge.get("target")))
            if source and target:
                relation = _mermaid_text(str(edge.get("relation", "links")))
                lines.append(f"  {source} -->|{relation}| {target}")
    return "\n".join(lines) + "\n"


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _contexts_compatible(claim: dict[str, str], evidence: dict[str, str]) -> bool:
    shared = set(claim) & set(evidence)
    return not shared or all(
        claim[key].strip().casefold() == evidence[key].strip().casefold() for key in shared
    )


def _mermaid_text(value: str) -> str:
    return re.sub(r"[\r\n]+", " ", value).replace('"', "'").replace("|", "/")
