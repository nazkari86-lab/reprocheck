from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

from .audit import run_audit
from .witness import build_witness_payload, verify_witness_file


CASES = (
    ("M01", "claim_metric_mismatch", "reported"),
    ("M02", "claim_metric_mismatch", "recomputed"),
    ("M03", "claim_metric_mismatch", "multi_source"),
    ("M04", "claim_metric_mismatch", "extra_findings"),
    ("C01", "metric_evidence_conflict", "accuracy"),
    ("C02", "metric_evidence_conflict", "precision"),
    ("C03", "metric_evidence_conflict", "recall"),
    ("C04", "metric_evidence_conflict", "f1"),
    ("S01", "exact_split_overlap", "one_overlap"),
    ("S02", "exact_split_overlap", "two_overlaps"),
    ("S03", "exact_split_overlap", "duplicate_test"),
    ("S04", "exact_split_overlap", "extra_notebook_finding"),
)


def run_witness_benchmark(output: Path | None = None, *, repeats: int = 25) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-witness-benchmark-") as directory:
        root = Path(directory)
        for case_id, rule, variant in CASES:
            case_root = root / case_id
            case_root.mkdir()
            source, finding_index = _build_case(case_root, rule, variant)
            graph = source["evidence_graph"]
            witness = build_witness_payload(source, finding_index, case_root)
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
            tamper_rejections = _tamper_rejections(witness, witness_path, certificate, case_root)
            one_hop_topology_complete = rule == "exact_split_overlap"
            cases.append(
                {
                    "id": case_id,
                    "rule": rule,
                    "variant": variant,
                    "representations": {
                        "full_graph": _size(full, valid=True),
                        "one_hop_neighborhood": _size(
                            neighborhood,
                            valid=one_hop_topology_complete,
                        ),
                        "exact_minimal_witness": _size(witness_view, valid=True),
                    },
                    "artifact_semantic_recomputation_required": rule == "exact_split_overlap",
                    "minimum_node_count": witness["minimality"]["minimum_node_count"],
                    "minimum_edge_count": witness["minimality"]["minimum_edge_count"],
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
        "schema_version": "reprocheck.witness-benchmark.v2",
        "design": {
            "type": "controlled_multi_rule_representation_benchmark",
            "primary_outcomes": ["node_count", "serialized_bytes"],
            "secondary_outcomes": ["verification_time", "tamper_rejection"],
            "scientific_boundary": (
                "Twelve author-designed controlled cases establish compactness and verifier "
                "behavior for three declared rules; they do not estimate natural defect "
                "prevalence or reviewer time savings."
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
        len(cases) == 12
        and {case.get("rule") for case in cases}
        == {"claim_metric_mismatch", "metric_evidence_conflict", "exact_split_overlap"}
        and all(case["representations"]["exact_minimal_witness"]["valid"] for case in cases)
        and all(
            case["representations"]["exact_minimal_witness"]["nodes"]
            < case["representations"]["full_graph"]["nodes"]
            for case in cases
        )
        and all(case["verification"]["tamper_cases_rejected"] == 4 for case in cases)
    )


def _build_case(root: Path, rule: str, variant: str) -> tuple[dict[str, Any], int]:
    if rule == "claim_metric_mismatch":
        return _mismatch_case(root, variant)
    if rule == "metric_evidence_conflict":
        return _conflict_case(root, variant)
    return _split_case(root, variant)


def _mismatch_case(root: Path, variant: str) -> tuple[dict[str, Any], int]:
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
    return source, _finding_index(source, "claim_metric_mismatch", 0)


def _conflict_case(root: Path, metric_name: str) -> tuple[dict[str, Any], int]:
    report = root / "report.md"
    metrics = root / "metrics.json"
    predictions = root / "predictions.csv"
    report.write_text(
        "Accuracy: 90%\nPrecision: 90%\nRecall: 90%\nF1: 90%\n",
        encoding="utf-8",
    )
    metrics.write_text(
        json.dumps({"accuracy": 0.9, "precision": 0.9, "recall": 0.9, "f1": 0.9}),
        encoding="utf-8",
    )
    predictions.write_text("y_true,y_pred\n0,0\n1,0\n", encoding="utf-8")
    source = run_audit(
        report_path=report,
        metrics_path=metrics,
        predictions_path=predictions,
        average="macro",
    ).to_dict()
    indexes = [
        index
        for index, finding in enumerate(source["findings"])
        if finding["code"] == "metric_evidence_conflict" and finding["metric"] == metric_name
    ]
    if len(indexes) != 1:
        raise ValueError(f"controlled metric conflict did not resolve once: {metric_name}")
    return source, indexes[0]


def _split_case(root: Path, variant: str) -> tuple[dict[str, Any], int]:
    report = root / "report.md"
    train = root / "train.csv"
    test = root / "test.csv"
    notebook = root / "analysis.ipynb"
    report.write_text("No numerical claim.\n", encoding="utf-8")
    train.write_text("id,text\n1,one\n2,two\n3,three\n", encoding="utf-8")
    if variant == "one_overlap":
        test.write_text("id,text\n1,new-one\n4,four\n", encoding="utf-8")
    elif variant == "two_overlaps":
        test.write_text("id,text\n1,new-one\n2,new-two\n4,four\n", encoding="utf-8")
    elif variant == "duplicate_test":
        test.write_text("id,text\n1,new-one\n1,again\n4,four\n", encoding="utf-8")
    else:
        test.write_text("id,text\n1,new-one\n4,four\n", encoding="utf-8")
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
    kwargs: dict[str, Any] = {
        "report_path": report,
        "train_path": train,
        "test_path": test,
        "identity_columns": ["id"],
    }
    if variant == "extra_notebook_finding":
        kwargs["notebook_path"] = notebook
    source = run_audit(**kwargs).to_dict()
    return source, _finding_index(source, "exact_split_overlap", 0)


def _finding_index(source: dict[str, Any], code: str, occurrence: int) -> int:
    indexes = [index for index, finding in enumerate(source["findings"]) if finding["code"] == code]
    if occurrence >= len(indexes):
        raise ValueError(f"controlled case did not produce finding: {code}")
    return indexes[occurrence]


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


def _tamper_rejections(
    witness: dict[str, Any], witness_path: Path, certificate: Path, artifact_dir: Path
) -> int:
    from .witness import witness_digest

    variants = []
    payload = json.loads(json.dumps(witness))
    if payload["finding_code"] == "claim_metric_mismatch":
        payload["rule_inputs"]["observed"] += 0.01
    elif payload["finding_code"] == "metric_evidence_conflict":
        payload["rule_inputs"]["source_values"][0]["value"] += 0.01
    else:
        payload["rule_inputs"]["exact_overlap_test_rows"] += 1
    payload["witness_sha256"] = witness_digest(payload)
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
        rejected += bool(verify_witness_file(witness_path, certificate, artifact_dir))
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
    by_rule: dict[str, dict[str, Any]] = {}
    for rule in sorted({str(case["rule"]) for case in cases}):
        selected = [case for case in cases if case["rule"] == rule]
        rule_full_nodes = sum(item["representations"]["full_graph"]["nodes"] for item in selected)
        rule_witness_nodes = sum(
            item["representations"]["exact_minimal_witness"]["nodes"] for item in selected
        )
        by_rule[rule] = {
            "cases": len(selected),
            "node_reduction": 1 - rule_witness_nodes / rule_full_nodes,
            "tamper_rejection_rate": sum(
                item["verification"]["tamper_cases_rejected"] for item in selected
            )
            / sum(item["verification"]["tamper_cases_total"] for item in selected),
        }
    return {
        "case_count": len(cases),
        "node_reduction": 1 - witness_nodes / full_nodes,
        "serialized_byte_reduction": 1 - witness_bytes / full_bytes,
        "one_hop_topology_complete_cases": sum(
            case["representations"]["one_hop_neighborhood"]["valid"] for case in cases
        ),
        "artifact_semantic_recomputation_cases": sum(
            case["artifact_semantic_recomputation_required"] for case in cases
        ),
        "tamper_rejection_rate": sum(
            case["verification"]["tamper_cases_rejected"] for case in cases
        )
        / sum(case["verification"]["tamper_cases_total"] for case in cases),
        "by_rule": by_rule,
    }
