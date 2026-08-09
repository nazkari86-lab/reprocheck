from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from importlib.metadata import distribution
from pathlib import Path
from typing import Any

from reprocheck.claims import extract_table_claims
from reprocheck.documents import extract_document_text
from reprocheck.metric_names import metric_family
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
ANNOTATIONS = ROOT / "annotations.json"
PREREGISTRATION = ROOT / "preregistration.json"
ANNOTATION_LOCK = ROOT / "annotation.lock.json"
EVALUATOR_SHA256 = "8c182c3e2cdd41d47e296653950429d1d12cfc0837b63db565f19f2eb65a09ee"
REGISTERED_METRICS = {
    "accuracy",
    "top1_accuracy",
    "top5_accuracy",
    "precision",
    "recall",
    "f1",
    "dice",
    "iou",
    "miou",
    "ap",
    "ap50",
    "ap75",
    "bleu",
    "wer",
    "cer",
    "rmse",
    "mae",
    "r2",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_evaluator(wheel: Path) -> dict[str, str]:
    wheel = wheel.resolve()
    if __version__ != "0.7.0" or _sha256(wheel) != EVALUATOR_SHA256:
        raise ValueError("installed or supplied evaluator differs from frozen v0.7")
    direct_url_raw = distribution("reprocheck").read_text("direct_url.json")
    if direct_url_raw is None:
        raise ValueError("installed evaluator has no direct_url.json provenance")
    installed_hash = json.loads(direct_url_raw).get("archive_info", {}).get("hash")
    if installed_hash != f"sha256={EVALUATOR_SHA256}":
        raise ValueError("installed evaluator archive differs from supplied wheel")
    return {
        "version": __version__,
        "filename": wheel.name,
        "sha256": EVALUATOR_SHA256,
        "installed_archive_hash": installed_hash,
    }


def _verify_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lock = _load(ANNOTATION_LOCK)
    manifest = _load(MANIFEST)
    annotations = _load(ANNOTATIONS)
    bindings = (
        (PREREGISTRATION, lock["preregistration_sha256"]),
        (MANIFEST, lock["source_manifest_sha256"]),
        (ANNOTATIONS, lock["annotations_sha256"]),
    )
    for path, expected in bindings:
        if _sha256(path) != expected:
            raise ValueError(f"locked evaluation input changed: {path}")
    artifacts = annotations["artifacts"]
    entries = {
        entry["local_path"]: entry for entry in manifest["entries"] if entry["kind"] == "artifact"
    }
    if len(artifacts) != lock["artifacts"] or {item["local_path"] for item in artifacts} != set(
        entries
    ):
        raise ValueError("annotation and source artifact sets disagree")
    for artifact in artifacts:
        path = SOURCES / artifact["local_path"]
        if _sha256(path) != entries[artifact["local_path"]]["sha256"]:
            raise ValueError(f"source checksum mismatch: {artifact['local_path']}")
    return manifest, artifacts


def _canonical(metric: str) -> str | None:
    if metric in {"map50_95", "ap50_95"} or metric.endswith("_ap50_95"):
        return "ap"
    if metric in {"map50", "ap50"} or metric.endswith("_ap50"):
        return "ap50"
    if metric in {"map75", "ap75"} or metric.endswith("_ap75"):
        return "ap75"
    if metric == "ap" or metric.endswith("_ap"):
        return "ap"
    family = metric_family(metric)
    return family if family in REGISTERED_METRICS else None


def _match(expected: list[tuple[str, float]], actual: list[tuple[str, float]]) -> dict[str, Any]:
    remaining = list(expected)
    tp = 0
    for metric, value in actual:
        hit = next(
            (
                index
                for index, (expected_metric, expected_value) in enumerate(remaining)
                if metric == expected_metric and abs(value - expected_value) <= 1e-9
            ),
            None,
        )
        if hit is not None:
            tp += 1
            remaining.pop(hit)
    return {
        "tp": tp,
        "fp": len(actual) - tp,
        "fn": len(remaining),
        "exact": tp == len(actual) and not remaining,
    }


def _wilson(successes: int, total: int) -> list[float]:
    if not total:
        return [1.0, 1.0]
    z = 1.96
    p = successes / total
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _aggregate(cases: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(case["tp"] for case in cases)
    fp = sum(case["fp"] for case in cases)
    fn = sum(case["fn"] for case in cases)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else 1.0,
        "precision_wilson_95": _wilson(tp, tp + fp),
        "recall": tp / (tp + fn) if tp + fn else 1.0,
        "recall_wilson_95": _wilson(tp, tp + fn),
        "artifact_exact_rate": sum(case["exact"] for case in cases) / len(cases),
    }


def run(wheel: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"zero-shot output already exists and cannot be overwritten: {output}")
    evaluator = _verify_evaluator(wheel)
    manifest, artifacts = _verify_inputs()
    records = []
    for artifact in artifacts:
        expected = [
            (claim["metric"], float(claim["value"])) for claim in artifact["expected_claims"]
        ]
        actual = []
        path = SOURCES / artifact["local_path"]
        for claim in extract_table_claims(extract_document_text(path)):
            metric = _canonical(claim.metric)
            if metric is not None:
                actual.append((metric, claim.value))
        case = {
            "repository": artifact["repository"],
            "local_path": artifact["local_path"],
            "expected_claims": len(expected),
            "extracted_scoped_claims": len(actual),
            **_match(expected, actual),
        }
        records.append({"case": case, "expected": expected, "actual": actual})
    cases = [record["case"] for record in records]
    claim_cases = [case for case in cases if case["expected_claims"]]
    repository_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        repository_cases[case["repository"]].append(case)
    metric_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metric in sorted(REGISTERED_METRICS):
        for record in records:
            expected = [item for item in record["expected"] if item[0] == metric]
            actual = [item for item in record["actual"] if item[0] == metric]
            if expected or actual:
                metric_cases[metric].append(_match(expected, actual))
    result = {
        "schema": "reprocheck.cross-domain-holdout-study.v1",
        "phase": "preregistered_v0.7_zero_shot",
        "zero_shot": True,
        "evaluator": evaluator,
        "protocol": {
            "prediction_scope": "Markdown and HTML table claims only",
            "metric_scope": sorted(REGISTERED_METRICS),
            "matching": "multiset metric and value matching",
            "absolute_tolerance": 1e-9,
            "output_overwrite_forbidden": True,
        },
        "corpus": {
            "artifacts": len(cases),
            "claim_bearing_artifacts": len(claim_cases),
            "annotated_claims": sum(case["expected_claims"] for case in cases),
            "repositories": len(repository_cases),
            "repository_commits": {
                repository["id"]: repository["commit"] for repository in manifest["repositories"]
            },
            "preregistration_sha256": _sha256(PREREGISTRATION),
            "source_manifest_sha256": _sha256(MANIFEST),
            "annotations_sha256": _sha256(ANNOTATIONS),
            "annotation_lock_sha256": _sha256(ANNOTATION_LOCK),
        },
        "summary": {
            **_aggregate(cases),
            "claim_artifact_exact_rate": sum(case["exact"] for case in claim_cases)
            / len(claim_cases),
        },
        "by_repository": {
            name: _aggregate(group) for name, group in sorted(repository_cases.items())
        },
        "by_metric": {name: _aggregate(group) for name, group in sorted(metric_cases.items())},
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the preregistered v0.7 cross-domain holdout")
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.evaluator_artifact, args.output)
    except (KeyError, OSError, UnicodeDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    summary = result["summary"]
    print(
        f"version=0.7.0 zero_shot=true artifacts={result['corpus']['artifacts']} "
        f"claims={result['corpus']['annotated_claims']} tp={summary['tp']} "
        f"fp={summary['fp']} fn={summary['fn']} precision={summary['precision']:.1%} "
        f"recall={summary['recall']:.1%}"
    )
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
