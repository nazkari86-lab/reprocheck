from __future__ import annotations

import hashlib
import json
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .audit import run_audit
from .certificate import digest_payload, verify_certificate_file
from .claims import check_claims, extract_claims
from .documents import extract_document_text
from .evidence import load_metric_evidence
from .metric_names import is_unit_interval_metric
from .version import __version__


SYSTEMS = (
    "report_text_only",
    "claim_plus_supplied_metrics",
    "artifact_aware_audit",
    "graph_certified_audit",
)


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    family: str
    defect_present: bool
    variant: str


@dataclass
class CaseFiles:
    report: Path
    metrics: Path | None
    predictions: Path | None
    train: Path | None
    test: Path | None
    notebook: Path | None
    certificate: Path


def run_evidence_ablation(output: Path | None = None) -> dict[str, Any]:
    """Compare four evidence layers on the same deterministic case matrix."""
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-evidence-ablation-") as directory:
        root = Path(directory)
        for spec in _case_specs():
            files = _build_case(root / spec.case_id, spec)
            detections = _evaluate_systems(files)
            cases.append(
                {
                    "id": spec.case_id,
                    "family": spec.family,
                    "defect_present": spec.defect_present,
                    "systems": {
                        system: {
                            "detected": detections[system][0],
                            "correct": detections[system][0] == spec.defect_present,
                            "signals": detections[system][1],
                        }
                        for system in SYSTEMS
                    },
                }
            )

    summaries = {system: _system_summary(cases, system) for system in SYSTEMS}
    result = {
        "schema_version": "1.0",
        "tool_version": __version__,
        "design": {
            "type": "controlled_information_ablation",
            "systems_in_order": list(SYSTEMS),
            "primary_outcome": "case-level defect detection correctness",
            "paired_test": "exact two-sided McNemar on correctness",
            "scientific_boundary": (
                "Deterministic controlled cases isolate information-layer capability; "
                "they are not an independent blind estimate of real-world prevalence or accuracy."
            ),
        },
        "case_counts": {
            "total": len(cases),
            "defects": sum(case["defect_present"] for case in cases),
            "negative_controls": sum(not case["defect_present"] for case in cases),
            "families": len({case["family"] for case in cases}),
        },
        "systems": summaries,
        "pairwise_mcnemar": _pairwise_tests(cases),
        "cases": cases,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def ablation_passed(result: dict[str, Any]) -> bool:
    systems = result.get("systems", {})
    sensitivities = [systems.get(system, {}).get("sensitivity") for system in SYSTEMS]
    monotonic = all(
        isinstance(value, (int, float)) for value in sensitivities
    ) and sensitivities == sorted(sensitivities)
    return bool(
        result.get("case_counts")
        == {"total": 19, "defects": 12, "negative_controls": 7, "families": 13}
        and monotonic
        and all(systems.get(system, {}).get("false_positives") == 0 for system in SYSTEMS)
        and systems.get("graph_certified_audit", {}).get("balanced_accuracy") == 1.0
        and systems.get("graph_certified_audit", {}).get("family_coverage_rate") == 1.0
    )


def _case_specs() -> list[CaseSpec]:
    return [
        CaseSpec("D01", "claim_validity", True, "out_of_range"),
        CaseSpec("D02", "claim_evidence", True, "claim_metric_mismatch"),
        CaseSpec("D03", "recomputation", True, "forged_metrics"),
        CaseSpec("D04", "split_integrity", True, "exact_overlap"),
        CaseSpec("D05", "split_integrity", True, "normalized_overlap"),
        CaseSpec("D06", "split_integrity", True, "group_overlap"),
        CaseSpec("D07", "notebook_dataflow", True, "fit_on_test"),
        CaseSpec("D08", "claim_evidence", True, "missing_metrics"),
        CaseSpec("D09", "graph_integrity", True, "graph_node_tamper"),
        CaseSpec("D10", "graph_integrity", True, "graph_endpoint_tamper"),
        CaseSpec("D11", "graph_integrity", True, "graph_cycle"),
        CaseSpec("D12", "notebook_dataflow", True, "fit_transform_on_test"),
        CaseSpec("C01", "clean_reported", False, "clean_reported"),
        CaseSpec("C02", "clean_recomputed", False, "clean_recomputed"),
        CaseSpec("C03", "clean_tolerance", False, "within_tolerance"),
        CaseSpec("C04", "clean_representation", False, "percentage_scale"),
        CaseSpec("C05", "clean_split", False, "disjoint_splits"),
        CaseSpec("C06", "clean_notebook", False, "seeded_notebook"),
        CaseSpec("C07", "clean_graph", False, "intact_graph"),
    ]


def _build_case(root: Path, spec: CaseSpec) -> CaseFiles:
    root.mkdir(parents=True)
    report = root / "report.md"
    metrics = root / "metrics.json"
    predictions = root / "predictions.csv"
    train = root / "train.csv"
    test = root / "test.csv"
    notebook = root / "analysis.ipynb"
    certificate = root / "certificate.json"

    report.write_text("Accuracy: 100%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 1.0}\n', encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,1\n", encoding="utf-8")
    train.write_text("id,group,text,label\n1,a,alpha sample,0\n", encoding="utf-8")
    test.write_text("id,group,text,label\n2,b,beta sample,1\n", encoding="utf-8")
    _write_notebook(notebook, "import numpy as np\nnp.random.seed(2026)\n")

    variant = spec.variant
    use_metrics = variant not in {"missing_metrics"}
    use_predictions = variant in {
        "forged_metrics",
        "clean_recomputed",
        "percentage_scale",
    }
    use_splits = variant in {
        "exact_overlap",
        "normalized_overlap",
        "group_overlap",
        "disjoint_splits",
    }
    use_notebook = variant in {"fit_on_test", "fit_transform_on_test", "seeded_notebook"}

    if variant == "out_of_range":
        report.write_text("Accuracy: 140%\n", encoding="utf-8")
    elif variant == "claim_metric_mismatch":
        report.write_text("Accuracy: 80%\n", encoding="utf-8")
    elif variant == "forged_metrics":
        report.write_text("Accuracy: 50%\n", encoding="utf-8")
        metrics.write_text('{"accuracy": 0.5}\n', encoding="utf-8")
    elif variant == "exact_overlap":
        test.write_text("id,group,text,label\n1,a,alpha sample,0\n", encoding="utf-8")
    elif variant == "normalized_overlap":
        test.write_text("id,group,text,label\n2,b,  ALPHA   SAMPLE  ,1\n", encoding="utf-8")
    elif variant == "group_overlap":
        test.write_text("id,group,text,label\n2,a,beta sample,1\n", encoding="utf-8")
    elif variant == "fit_on_test":
        _write_notebook(
            notebook,
            "from sklearn.preprocessing import StandardScaler\n"
            "import numpy as np\nnp.random.seed(2026)\n"
            "scaler = StandardScaler()\nscaler.fit(X_test)\n",
        )
    elif variant == "fit_transform_on_test":
        _write_notebook(
            notebook,
            "from sklearn.preprocessing import StandardScaler\n"
            "import numpy as np\nnp.random.seed(2026)\n"
            "scaler = StandardScaler()\nscaler.fit_transform(test_data)\n",
        )
    elif variant == "within_tolerance":
        report.write_text("Accuracy: 99.6%\n", encoding="utf-8")
    elif variant == "percentage_scale":
        metrics.write_text('{"accuracy": 100}\n', encoding="utf-8")

    audit = run_audit(
        report_path=report,
        notebook_path=notebook if use_notebook else None,
        metrics_path=metrics if use_metrics else None,
        predictions_path=predictions if use_predictions else None,
        train_path=train if use_splits else None,
        test_path=test if use_splits else None,
        label_column="label" if use_splits else None,
        group_column="group" if use_splits else None,
        identity_columns=["id"] if use_splits else None,
        text_column="text" if use_splits else None,
    )
    certificate.write_text(
        json.dumps(audit.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if variant.startswith("graph_"):
        _tamper_graph_certificate(certificate, variant)

    return CaseFiles(
        report=report,
        metrics=metrics if use_metrics else None,
        predictions=predictions if use_predictions else None,
        train=train if use_splits else None,
        test=test if use_splits else None,
        notebook=notebook if use_notebook else None,
        certificate=certificate,
    )


def _evaluate_systems(files: CaseFiles) -> dict[str, tuple[bool, list[str]]]:
    text = extract_document_text(files.report)
    claims = extract_claims(text)
    text_signals = [
        "unit_interval_out_of_range"
        for claim in claims
        if is_unit_interval_metric(claim.metric) and not 0 <= claim.value <= 1
    ]

    evidence = load_metric_evidence(files.metrics) if files.metrics else {}
    checks = check_claims(
        claims,
        {name: item.value for name, item in evidence.items()},
        0.005,
        evidence_levels={name: item.evidence_level for name, item in evidence.items()},
        evidence_contexts={name: item.context for name, item in evidence.items()},
    )
    supplied_signals = sorted(
        {
            f"claim_{check.status}"
            for check in checks
            if check.status not in {"supported", "verified"}
        }
        | set(text_signals)
    )

    audit = run_audit(
        report_path=files.report,
        notebook_path=files.notebook,
        metrics_path=files.metrics,
        predictions_path=files.predictions,
        train_path=files.train,
        test_path=files.test,
        label_column="label" if files.train else None,
        group_column="group" if files.train else None,
        identity_columns=["id"] if files.train else None,
        text_column="text" if files.train else None,
    )
    artifact_signals = sorted({str(item["code"]) for item in audit.findings} | set(text_signals))
    graph_errors = verify_certificate_file(files.certificate)
    graph_signals = sorted(set(artifact_signals) | {f"certificate:{item}" for item in graph_errors})
    return {
        "report_text_only": (bool(text_signals), text_signals),
        "claim_plus_supplied_metrics": (bool(supplied_signals), supplied_signals),
        "artifact_aware_audit": (bool(artifact_signals), artifact_signals),
        "graph_certified_audit": (bool(graph_signals), graph_signals),
    }


def _system_summary(cases: list[dict[str, Any]], system: str) -> dict[str, Any]:
    true_positives = sum(
        case["defect_present"] and case["systems"][system]["detected"] for case in cases
    )
    false_negatives = sum(
        case["defect_present"] and not case["systems"][system]["detected"] for case in cases
    )
    false_positives = sum(
        not case["defect_present"] and case["systems"][system]["detected"] for case in cases
    )
    true_negatives = sum(
        not case["defect_present"] and not case["systems"][system]["detected"] for case in cases
    )
    sensitivity = true_positives / (true_positives + false_negatives)
    specificity = true_negatives / (true_negatives + false_positives)
    defect_families = sorted({case["family"] for case in cases if case["defect_present"]})
    by_family = {
        family: {
            "detected": sum(
                case["systems"][system]["detected"]
                for case in cases
                if case["defect_present"] and case["family"] == family
            ),
            "cases": sum(case["defect_present"] and case["family"] == family for case in cases),
        }
        for family in defect_families
    }
    covered = sum(item["detected"] == item["cases"] for item in by_family.values())
    return {
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "false_positives": false_positives,
        "true_negatives": true_negatives,
        "sensitivity": sensitivity,
        "sensitivity_wilson_95": _wilson(true_positives, true_positives + false_negatives),
        "specificity": specificity,
        "specificity_wilson_95": _wilson(true_negatives, true_negatives + false_positives),
        "balanced_accuracy": (sensitivity + specificity) / 2,
        "family_coverage_rate": covered / len(defect_families),
        "by_defect_family": by_family,
    }


def _pairwise_tests(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparisons = []
    for first, second in zip(SYSTEMS, SYSTEMS[1:]):
        first_only = sum(
            case["systems"][first]["correct"] and not case["systems"][second]["correct"]
            for case in cases
        )
        second_only = sum(
            case["systems"][second]["correct"] and not case["systems"][first]["correct"]
            for case in cases
        )
        comparisons.append(
            {
                "first": first,
                "second": second,
                "first_only_correct": first_only,
                "second_only_correct": second_only,
                "discordant": first_only + second_only,
                "exact_two_sided_p": _exact_mcnemar(first_only, second_only),
            }
        )
    return comparisons


def _exact_mcnemar(first_only: int, second_only: int) -> float:
    discordant = first_only + second_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(first_only, second_only) + 1))
    return min(1.0, 2 * tail / (2**discordant))


def _wilson(successes: int, total: int, z: float = 1.96) -> list[float]:
    if total == 0:
        return [1.0, 1.0]
    proportion = successes / total
    denominator = 1 + z**2 / total
    center = (proportion + z**2 / (2 * total)) / denominator
    margin = (
        z * math.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2)) / denominator
    )
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _write_notebook(path: Path, source: str) -> None:
    path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "metadata": {},
                        "outputs": [],
                        "source": source.splitlines(keepends=True),
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )


def _tamper_graph_certificate(path: Path, variant: str) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    graph = payload["evidence_graph"]
    if variant == "graph_node_tamper":
        graph["nodes"][0]["label"] = "tampered experiment"
    elif variant == "graph_endpoint_tamper":
        graph["edges"][0]["target"] = "missing:0"
    elif variant == "graph_cycle":
        edge = {"source": "experiment:0", "target": "artifact:0", "relation": "flags"}
        edge["digest_sha256"] = _canonical_digest(edge)
        graph["edges"].append(edge)
        graph["graph_sha256"] = _canonical_digest(
            {key: value for key, value in graph.items() if key != "graph_sha256"}
        )
    else:
        raise ValueError(f"unsupported graph tamper variant: {variant}")
    payload["certificate_sha256"] = digest_payload(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
