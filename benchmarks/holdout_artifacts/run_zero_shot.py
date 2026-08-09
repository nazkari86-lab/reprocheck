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
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
ANNOTATIONS = ROOT / "annotations.json"
PREREGISTRATION = ROOT / "preregistration.json"
PREREGISTRATION_LOCK = ROOT / "preregistration.lock.json"
ANNOTATION_LOCK = ROOT / "annotation.lock.json"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_evaluator(artifact: Path) -> dict[str, str]:
    preregistration_lock = _load(PREREGISTRATION_LOCK)
    artifact = artifact.resolve()
    digest = _sha256(artifact)
    if __version__ != "0.6.0":
        raise ValueError(f"installed evaluator is {__version__}, expected 0.6.0")
    if digest != preregistration_lock["evaluator_sha256"]:
        raise ValueError("evaluator wheel differs from preregistration lock")
    dist = distribution("reprocheck")
    direct_url_raw = dist.read_text("direct_url.json")
    if direct_url_raw is None:
        raise ValueError("installed evaluator has no direct_url.json provenance")
    direct_url = json.loads(direct_url_raw)
    installed_hash = direct_url.get("archive_info", {}).get("hash")
    if installed_hash != f"sha256={digest}":
        raise ValueError("installed evaluator hash does not match supplied wheel")
    return {
        "version": __version__,
        "filename": artifact.name,
        "sha256": digest,
        "installed_archive_hash": installed_hash,
    }


def _verify_inputs() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    preregistration_lock = _load(PREREGISTRATION_LOCK)
    annotation_lock = _load(ANNOTATION_LOCK)
    manifest = _load(MANIFEST)
    annotations = _load(ANNOTATIONS)
    if _sha256(PREREGISTRATION) != preregistration_lock["preregistration_sha256"]:
        raise ValueError("preregistration changed after lock")
    if _sha256(MANIFEST) != annotation_lock["source_manifest_sha256"]:
        raise ValueError("source manifest changed after annotation lock")
    if _sha256(ANNOTATIONS) != annotation_lock["annotations_sha256"]:
        raise ValueError("annotations changed after annotation lock")
    entries = {
        entry["local_path"]: entry
        for entry in manifest.get("entries", [])
        if entry.get("kind") == "artifact"
    }
    artifacts = annotations.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != annotation_lock["artifacts"]:
        raise ValueError("annotation artifact count differs from lock")
    paths = [artifact.get("local_path") for artifact in artifacts]
    if len(paths) != len(set(paths)) or set(paths) != set(entries):
        raise ValueError("manifest and annotation paths disagree")
    for artifact in artifacts:
        path = SOURCES / artifact["local_path"]
        entry = entries[artifact["local_path"]]
        if not path.is_file() or _sha256(path) != entry["sha256"]:
            raise ValueError(f"source checksum mismatch: {artifact['local_path']}")
        if artifact["source_sha256"] != entry["sha256"]:
            raise ValueError(f"annotation source checksum mismatch: {artifact['local_path']}")
    return manifest, artifacts


def _canonical_metric(metric: str) -> str | None:
    if metric in {"ap", "map50_95"} or metric.endswith(("_ap", "_ap50_95")):
        return "ap"
    if metric in {"ap50", "map50"} or metric.endswith("_ap50"):
        return "ap50"
    if metric in {"ap75", "map75"} or metric.endswith("_ap75"):
        return "ap75"
    return None


def _match(
    expected: list[tuple[str, float]], actual: list[tuple[str, float]], tolerance: float = 1e-9
) -> dict[str, Any]:
    remaining = list(expected)
    true_positives = 0
    for metric, value in actual:
        index = next(
            (
                offset
                for offset, (expected_metric, expected_value) in enumerate(remaining)
                if metric == expected_metric and abs(value - expected_value) <= tolerance
            ),
            None,
        )
        if index is not None:
            true_positives += 1
            remaining.pop(index)
    return {
        "tp": true_positives,
        "fp": len(actual) - true_positives,
        "fn": len(remaining),
        "exact": len(actual) == true_positives and not remaining,
    }


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


def run(evaluator_artifact: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"zero-shot output already exists and cannot be overwritten: {output}")
    evaluator = _verify_evaluator(evaluator_artifact)
    manifest, artifacts = _verify_inputs()
    records = []
    for artifact in artifacts:
        path = SOURCES / artifact["local_path"]
        expected = [
            (claim["metric"], float(claim["value"])) for claim in artifact["expected_claims"]
        ]
        actual = []
        for claim in extract_table_claims(extract_document_text(path)):
            metric = _canonical_metric(claim.metric)
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
    by_repository: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        by_repository[case["repository"]].append(case)
    by_metric_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metric in ("ap", "ap50", "ap75"):
        for record in records:
            expected = [claim for claim in record["expected"] if claim[0] == metric]
            actual = [claim for claim in record["actual"] if claim[0] == metric]
            if expected or actual:
                by_metric_cases[metric].append(_match(expected, actual))
    repository_commits = {
        repository["id"]: repository["commit"] for repository in manifest["repositories"]
    }
    result = {
        "schema": "reprocheck.preregistered-holdout-study.v1",
        "phase": "preregistered_zero_shot",
        "evaluator": evaluator,
        "protocol": {
            "prediction_scope": "Markdown and HTML table claims only",
            "metric_scope": ["ap", "ap50", "ap75"],
            "matching": "multiset metric and value matching",
            "absolute_tolerance": 1e-9,
            "output_overwrite_forbidden": True,
        },
        "corpus": {
            "artifacts": len(cases),
            "claim_bearing_artifacts": len(claim_cases),
            "annotated_claims": sum(case["expected_claims"] for case in cases),
            "repositories": len(by_repository),
            "repository_commits": dict(sorted(repository_commits.items())),
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
            repository: _aggregate(repository_cases)
            for repository, repository_cases in sorted(by_repository.items())
        },
        "by_metric": {
            metric: _aggregate(metric_cases)
            for metric, metric_cases in sorted(by_metric_cases.items())
        },
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the preregistered v0.6 zero-shot holdout")
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.evaluator_artifact, args.output)
    except (KeyError, OSError, UnicodeDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    print(
        f"version={result['evaluator']['version']} "
        f"artifacts={result['corpus']['artifacts']} "
        f"claims={result['corpus']['annotated_claims']} "
        f"precision={result['summary']['precision']:.1%} "
        f"recall={result['summary']['recall']:.1%}"
    )
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
