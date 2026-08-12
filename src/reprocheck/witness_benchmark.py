from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from .audit import run_audit
from .witness import build_witness_payload, verify_witness_file


def run_witness_benchmark(output: Path | None = None, *, repeats: int = 25) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-witness-benchmark-") as directory:
        root = Path(directory)
        for case_id, variant in (
            ("W01", "reported"),
            ("W02", "recomputed"),
            ("W03", "multi_source"),
            ("W04", "extra_findings"),
        ):
            case_root = root / case_id
            case_root.mkdir()
            source, finding_index = _build_case(case_root, variant)
            graph = source["evidence_graph"]
            witness = build_witness_payload(source, finding_index)
            full = {"nodes": graph["nodes"], "edges": graph["edges"]}
            neighborhood = _one_hop(graph, f"finding:{finding_index}")
            witness_view = {"nodes": witness["nodes"], "edges": witness["edges"]}
            certificate = case_root / "certificate.json"
            witness_path = case_root / "witness.json"
            certificate.write_text(json.dumps(source), encoding="utf-8")
            witness_path.write_text(json.dumps(witness), encoding="utf-8")
            durations = []
            for _ in range(repeats):
                started = time.perf_counter_ns()
                assert verify_witness_file(witness_path, certificate, case_root) == []
                durations.append(time.perf_counter_ns() - started)
            tamper_rejections = _tamper_rejections(witness, witness_path, certificate)
            cases.append(
                {
                    "id": case_id,
                    "variant": variant,
                    "representations": {
                        "full_graph": _size(full, valid=True),
                        "one_hop_neighborhood": _size(
                            neighborhood,
                            valid=_source_grounded(neighborhood, finding_index),
                        ),
                        "exact_minimal_witness": _size(witness_view, valid=True),
                    },
                    "minimum_node_count": witness["minimality"]["minimum_node_count"],
                    "candidate_groundings_checked": witness["minimality"][
                        "candidate_groundings_checked"
                    ],
                    "verification": {
                        "repeats": repeats,
                        "median_ns": sorted(durations)[len(durations) // 2],
                        "tamper_cases_rejected": tamper_rejections,
                        "tamper_cases_total": 4,
                    },
                }
            )
    result = {
        "schema_version": "reprocheck.witness-benchmark.v1",
        "design": {
            "type": "controlled_representation_benchmark",
            "primary_outcomes": ["node_count", "serialized_bytes"],
            "secondary_outcomes": ["verification_time", "tamper_rejection"],
            "scientific_boundary": (
                "Author-designed controlled cases establish compactness and verifier behavior "
                "under the declared witness rule; they do not estimate reviewer time savings."
            ),
        },
        "cases": cases,
        "summary": _summary(cases),
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def witness_benchmark_passed(result: dict[str, Any]) -> bool:
    cases = result.get("cases", [])
    return bool(
        len(cases) == 4
        and all(case["minimum_node_count"] == 5 for case in cases)
        and all(case["representations"]["exact_minimal_witness"]["valid"] for case in cases)
        and all(not case["representations"]["one_hop_neighborhood"]["valid"] for case in cases)
        and all(
            case["representations"]["exact_minimal_witness"]["nodes"]
            < case["representations"]["full_graph"]["nodes"]
            for case in cases
        )
        and all(case["verification"]["tamper_cases_rejected"] == 4 for case in cases)
    )


def _build_case(root: Path, variant: str) -> tuple[dict[str, Any], int]:
    report = root / "report.md"
    metrics = root / "metrics.json"
    predictions = root / "predictions.csv"
    train = root / "train.csv"
    test = root / "test.csv"
    notebook = root / "analysis.ipynb"
    report.write_text("Accuracy: 80%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,1\n", encoding="utf-8")
    train.write_text("id,text,label\n1,same,0\n", encoding="utf-8")
    test.write_text("id,text,label\n1,same,0\n", encoding="utf-8")
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "metadata": {},
                        "outputs": [],
                        "source": ["model.fit(X_test)"],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    kwargs: dict[str, Any] = {"report_path": report, "metrics_path": metrics}
    if variant in {"recomputed", "multi_source", "extra_findings"}:
        kwargs["predictions_path"] = predictions
    if variant == "multi_source":
        metrics.write_text('{"accuracy": 0.7}\n', encoding="utf-8")
    if variant == "extra_findings":
        kwargs.update(
            train_path=train,
            test_path=test,
            label_column="label",
            identity_columns=["id"],
            notebook_path=notebook,
        )
    source = run_audit(**kwargs).to_dict()
    finding_index = next(
        index
        for index, finding in enumerate(source["findings"])
        if finding["code"] == "claim_metric_mismatch"
    )
    return source, finding_index


def _one_hop(graph: dict[str, Any], finding_id: str) -> dict[str, list[dict[str, Any]]]:
    edges = [
        edge
        for edge in graph["edges"]
        if edge["source"] == finding_id or edge["target"] == finding_id
    ]
    ids = {finding_id} | {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
    return {
        "nodes": [node for node in graph["nodes"] if node["id"] in ids],
        "edges": edges,
    }


def _source_grounded(view: dict[str, list[dict[str, Any]]], finding_index: int) -> bool:
    kinds = [node["kind"] for node in view["nodes"]]
    relations = {edge["relation"] for edge in view["edges"]}
    return bool(
        f"finding:{finding_index}" in {node["id"] for node in view["nodes"]}
        and kinds.count("claim") == 1
        and kinds.count("metric") == 1
        and kinds.count("artifact") >= 1
        and {"raises", "contradicts", "contains"} <= relations
        and bool({"reports", "recomputes"} & relations)
    )


def _tamper_rejections(witness: dict[str, Any], witness_path: Path, certificate: Path) -> int:
    from .witness import witness_digest

    variants = []
    payload = json.loads(json.dumps(witness))
    payload["rule_inputs"]["observed"] += 0.01
    variants.append(payload)
    payload = json.loads(json.dumps(witness))
    payload["nodes"][0]["label"] += " tampered"
    payload["witness_sha256"] = witness_digest(payload)
    variants.append(payload)
    payload = json.loads(json.dumps(witness))
    payload["edges"][0]["relation"] = "supports"
    payload["witness_sha256"] = witness_digest(payload)
    variants.append(payload)
    payload = json.loads(json.dumps(witness))
    payload["minimality"]["minimum_node_count"] += 1
    payload["witness_sha256"] = witness_digest(payload)
    variants.append(payload)
    rejected = 0
    for payload in variants:
        witness_path.write_text(json.dumps(payload), encoding="utf-8")
        rejected += bool(verify_witness_file(witness_path, certificate))
    witness_path.write_text(json.dumps(witness), encoding="utf-8")
    return rejected


def _size(view: dict[str, list[dict[str, Any]]], *, valid: bool) -> dict[str, Any]:
    return {
        "nodes": len(view["nodes"]),
        "edges": len(view["edges"]),
        "serialized_bytes": len(
            json.dumps(view, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ),
        "valid": valid,
    }


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    full_nodes = sum(case["representations"]["full_graph"]["nodes"] for case in cases)
    witness_nodes = sum(case["representations"]["exact_minimal_witness"]["nodes"] for case in cases)
    full_bytes = sum(case["representations"]["full_graph"]["serialized_bytes"] for case in cases)
    witness_bytes = sum(
        case["representations"]["exact_minimal_witness"]["serialized_bytes"] for case in cases
    )
    return {
        "case_count": len(cases),
        "node_reduction": 1 - witness_nodes / full_nodes,
        "serialized_byte_reduction": 1 - witness_bytes / full_bytes,
        "one_hop_valid_cases": sum(
            case["representations"]["one_hop_neighborhood"]["valid"] for case in cases
        ),
        "tamper_rejection_rate": sum(
            case["verification"]["tamper_cases_rejected"] for case in cases
        )
        / sum(case["verification"]["tamper_cases_total"] for case in cases),
    }
