from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .audit import run_audit
from .version import __version__
from .witness import build_witness_file, verify_witness_file, witness_digest
from .witness_rules import WITNESS_RULES


ROOT = Path(__file__).resolve().parents[2]


def run_witness_source_benchmark(protocol: Path, output: Path | None = None) -> dict[str, Any]:
    payload = _load_object(protocol, "witness source protocol")
    _validate_protocol(payload)
    _verify_source_manifests(payload)
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-witness-source-") as directory:
        temporary_root = Path(directory)
        for descriptor in payload["cases"]:
            case_root = temporary_root / descriptor["id"]
            source_root = ROOT / payload["source_roots"][descriptor["domain"]]
            shutil.copytree(source_root, case_root)
            if descriptor["evidence_stratum"] == "controlled_mutation":
                _mutate(case_root, descriptor)
            audit = _audit(case_root, descriptor["domain"])
            certificate = case_root / "certificate.json"
            certificate.write_text(
                json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            cases.append(_evaluate_case(case_root, certificate, audit, descriptor))
    result = {
        "schema_version": "reprocheck.witness-source-benchmark.v1",
        "tool_version": __version__,
        "protocol_sha256": _sha256(protocol),
        "cases": cases,
        "summary": _summary(cases),
        "scientific_boundary": payload["scientific_boundary"],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def witness_source_benchmark_passed(result: dict[str, Any]) -> bool:
    summary = result.get("summary", {})
    return bool(
        summary.get("case_count") == 30
        and summary.get("controlled_mutation_cases") == 27
        and summary.get("negative_control_cases") == 3
        and summary.get("natural_cases") == 0
        and summary.get("expected_witness_construction_rate") == 1.0
        and summary.get("independent_verification_rate") == 1.0
        and summary.get("negative_control_specificity") == 1.0
        and summary.get("tamper_rejection_rate") == 1.0
    )


def deterministic_projection(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": result["schema_version"],
        "protocol_sha256": result["protocol_sha256"],
        "cases": [
            {
                key: case[key]
                for key in (
                    "id",
                    "domain",
                    "evidence_stratum",
                    "expected_rule",
                    "actual_supported_findings",
                    "witness_nodes",
                    "witness_edges",
                    "constructed",
                    "verified",
                    "tamper_rejected",
                    "passed",
                )
            }
            for case in result["cases"]
        ],
        "summary": result["summary"],
        "scientific_boundary": result["scientific_boundary"],
    }


def _evaluate_case(
    root: Path,
    certificate: Path,
    audit: dict[str, Any],
    descriptor: dict[str, Any],
) -> dict[str, Any]:
    supported = [
        (index, finding)
        for index, finding in enumerate(audit["findings"])
        if finding.get("code") in WITNESS_RULES
        and (
            descriptor["rule"] != "metric_evidence_conflict"
            or finding.get("metric") == descriptor["target"]
        )
    ]
    actual_codes = [finding["code"] for _, finding in supported]
    expected_rule = descriptor["rule"]
    if expected_rule is None:
        return {
            "id": descriptor["id"],
            "domain": descriptor["domain"],
            "evidence_stratum": descriptor["evidence_stratum"],
            "expected_rule": None,
            "actual_supported_findings": actual_codes,
            "witness_nodes": 0,
            "witness_edges": 0,
            "constructed": False,
            "verified": False,
            "tamper_rejected": False,
            "passed": not supported,
        }
    matching = [
        (index, finding) for index, finding in supported if finding["code"] == expected_rule
    ]
    if len(matching) != 1:
        return {
            "id": descriptor["id"],
            "domain": descriptor["domain"],
            "evidence_stratum": descriptor["evidence_stratum"],
            "expected_rule": expected_rule,
            "actual_supported_findings": actual_codes,
            "witness_nodes": 0,
            "witness_edges": 0,
            "constructed": False,
            "verified": False,
            "tamper_rejected": False,
            "passed": False,
        }
    finding_index = matching[0][0]
    witness_path = root / "witness.json"
    witness = build_witness_file(certificate, finding_index, witness_path, root)
    verified = not verify_witness_file(witness_path, certificate, root)
    tampered = json.loads(json.dumps(witness))
    tampered["minimality"]["minimum_node_count"] += 1
    tampered["witness_sha256"] = witness_digest(tampered)
    witness_path.write_text(json.dumps(tampered), encoding="utf-8")
    tamper_rejected = bool(verify_witness_file(witness_path, certificate, root))
    return {
        "id": descriptor["id"],
        "domain": descriptor["domain"],
        "evidence_stratum": descriptor["evidence_stratum"],
        "expected_rule": expected_rule,
        "actual_supported_findings": actual_codes,
        "witness_nodes": len(witness["nodes"]),
        "witness_edges": len(witness["edges"]),
        "constructed": True,
        "verified": verified,
        "tamper_rejected": tamper_rejected,
        "passed": verified and tamper_rejected,
    }


def _audit(root: Path, domain: str) -> dict[str, Any]:
    if domain == "iris":
        return run_audit(
            report_path=root / "iris_report.md",
            metrics_path=root / "official_metrics.json",
            metrics_selector="iris",
            predictions_path=root / "iris_predictions.csv",
            train_path=root / "iris_train.csv",
            test_path=root / "iris_test.csv",
            label_column="target",
            identity_columns=["sample_id"],
            average="macro",
            tolerance=1e-9,
        ).to_dict()
    if domain == "diabetes":
        return run_audit(
            report_path=root / "diabetes_report.md",
            metrics_path=root / "official_metrics.json",
            metrics_selector="diabetes",
            predictions_path=root / "diabetes_predictions.csv",
            prediction_task="regression",
            train_path=root / "diabetes_train.csv",
            test_path=root / "diabetes_test.csv",
            label_column="target",
            identity_columns=["sample_id"],
            tolerance=1e-9,
        ).to_dict()
    return run_audit(
        report_path=root / "report.md",
        metrics_path=root / "official_metrics_flat.json",
        detections_path=root / "coco8_detections.json",
        tolerance=0.001,
    ).to_dict()


def _mutate(root: Path, descriptor: dict[str, Any]) -> None:
    rule = descriptor["rule"]
    domain = descriptor["domain"]
    target = descriptor["target"]
    variant = int(descriptor["variant"])
    if rule == "claim_metric_mismatch":
        _mutate_report(root, domain, str(target), variant)
    elif rule == "metric_evidence_conflict":
        _mutate_metric_source(root, domain, str(target), variant)
    elif rule == "exact_split_overlap":
        _mutate_split(root, domain, variant)
    else:
        raise ValueError(f"unsupported source benchmark mutation rule: {rule}")


def _mutate_report(root: Path, domain: str, metric: str, variant: int) -> None:
    path = root / ("report.md" if domain == "yolo" else f"{domain}_report.md")
    text = path.read_text(encoding="utf-8")
    replacements = {
        "accuracy": (r"Accuracy: [0-9.]+", f"Accuracy: 0.{variant}"),
        "precision": (r"Precision: [0-9.]+", f"Precision: 0.{variant}"),
        "recall": (r"Recall: [0-9.]+", f"Recall: 0.{variant}"),
        "mae": (r"MAE: [0-9.]+", f"MAE: {variant}.0"),
        "rmse": (r"RMSE: [0-9.]+", f"RMSE: {variant}.0"),
        "r2": (r"R2: [0-9.]+", f"R2: 0.{variant}"),
        "map50_95": (r"mAP50-95: [0-9.]+", f"mAP50-95: 0.{variant}"),
        "map50": (r"mAP50: [0-9.]+", f"mAP50: 0.{variant}"),
        "map75": (r"mAP75: [0-9.]+", f"mAP75: 0.{variant}"),
    }
    pattern, replacement = replacements[metric]
    mutated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise ValueError(f"report mutation did not resolve once: {domain}/{metric}")
    path.write_text(mutated, encoding="utf-8")


def _mutate_metric_source(root: Path, domain: str, metric: str, variant: int) -> None:
    path = root / ("official_metrics_flat.json" if domain == "yolo" else "official_metrics.json")
    payload = _load_object(path, "metric source")
    target = payload if domain == "yolo" else payload[domain]
    if not isinstance(target, dict) or metric not in target:
        raise ValueError(f"metric source mutation target is missing: {domain}/{metric}")
    if metric in {"mae", "rmse"}:
        target[metric] = float(variant)
    elif metric == "r2":
        target[metric] = -0.1 * variant
    else:
        target[metric] = 0.01 * variant
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _mutate_split(root: Path, domain: str, variant: int) -> None:
    train_path = root / f"{domain}_train.csv"
    test_path = root / f"{domain}_test.csv"
    with train_path.open(newline="", encoding="utf-8") as handle:
        train_rows = list(csv.DictReader(handle))
    with test_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        test_rows = list(reader)
    test_rows[variant - 1] = {field: train_rows[variant - 1][field] for field in fields}
    with test_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(test_rows)


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    mutations = [case for case in cases if case["evidence_stratum"] == "controlled_mutation"]
    controls = [case for case in cases if case["evidence_stratum"] == "negative_control"]
    natural = [case for case in cases if case["evidence_stratum"] == "natural"]
    by_rule: dict[str, dict[str, Any]] = {}
    for rule in sorted({str(case["expected_rule"]) for case in mutations}):
        selected = [case for case in mutations if case["expected_rule"] == rule]
        by_rule[rule] = {
            "cases": len(selected),
            "mean_witness_nodes": sum(case["witness_nodes"] for case in selected) / len(selected),
            "mean_witness_edges": sum(case["witness_edges"] for case in selected) / len(selected),
            "verification_rate": sum(case["verified"] for case in selected) / len(selected),
        }
    return {
        "case_count": len(cases),
        "controlled_mutation_cases": len(mutations),
        "negative_control_cases": len(controls),
        "natural_cases": len(natural),
        "expected_witness_construction_rate": sum(case["constructed"] for case in mutations)
        / len(mutations),
        "independent_verification_rate": sum(case["verified"] for case in mutations)
        / len(mutations),
        "negative_control_specificity": sum(case["passed"] for case in controls) / len(controls),
        "tamper_rejection_rate": sum(case["tamper_rejected"] for case in mutations)
        / len(mutations),
        "by_rule": by_rule,
    }


def _validate_protocol(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "reprocheck.witness-source-protocol.v1":
        raise ValueError("unsupported witness source protocol schema")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 30:
        raise ValueError("witness source protocol must contain exactly 30 cases")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != 30 or len(set(ids)) != 30:
        raise ValueError("witness source protocol case ids must be unique")
    strata = [case.get("evidence_stratum") for case in cases]
    if "natural" in strata:
        raise ValueError("protocol cannot prelabel a case as natural without observed evidence")
    if strata.count("controlled_mutation") != 27 or strata.count("negative_control") != 3:
        raise ValueError("witness source protocol must preserve 27 mutations and 3 controls")


def _verify_source_manifests(protocol: dict[str, Any]) -> None:
    for relative in sorted(set(protocol["source_roots"].values())):
        root = ROOT / relative
        manifest = _load_object(root / "manifest.json", "source manifest")
        for descriptor in manifest["files"]:
            path = root / descriptor["file"]
            if (
                path.stat().st_size != descriptor["size_bytes"]
                or _sha256(path) != descriptor["sha256"]
            ):
                raise ValueError(f"source manifest mismatch: {path}")


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
