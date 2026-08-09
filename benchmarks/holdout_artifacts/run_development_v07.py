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
ANNOTATIONS = ROOT / "posthoc_annotations-v0.7.json"
FROZEN_RESULT = ROOT / "results" / "zero-shot-v0.6.json"
EXPECTED = {
    "wheel": "8c182c3e2cdd41d47e296653950429d1d12cfc0837b63db565f19f2eb65a09ee",
    "manifest": "dcf58f8015401ce9d66bd3cc988a0c1e949df1df6e3b751eace9214755448ada",
    "annotations": "81b6519c34d6b34b73328e780566bc663c15ca7c100536c807648c2063faf306",
    "frozen_result": "f87ac0c5c10f00c289bd4046ea0f67d07f26d4a5aba3dab74fa8f54fe935d83f",
}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_inputs(wheel: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    wheel = wheel.resolve()
    for path, expected in (
        (wheel, EXPECTED["wheel"]),
        (MANIFEST, EXPECTED["manifest"]),
        (ANNOTATIONS, EXPECTED["annotations"]),
        (FROZEN_RESULT, EXPECTED["frozen_result"]),
    ):
        if _sha256(path) != expected:
            raise ValueError(f"development input checksum mismatch: {path}")
    if __version__ != "0.7.0":
        raise ValueError(f"installed evaluator is {__version__}, expected 0.7.0")
    direct_url_raw = distribution("reprocheck").read_text("direct_url.json")
    if direct_url_raw is None:
        raise ValueError("installed evaluator has no direct_url.json provenance")
    installed_hash = json.loads(direct_url_raw).get("archive_info", {}).get("hash")
    if installed_hash != f"sha256={EXPECTED['wheel']}":
        raise ValueError("installed evaluator does not match the frozen v0.7 wheel")

    manifest = _load(MANIFEST)
    annotations = _load(ANNOTATIONS)
    entries = {
        entry["local_path"]: entry for entry in manifest["entries"] if entry["kind"] == "artifact"
    }
    artifacts = annotations["artifacts"]
    if {item["local_path"] for item in artifacts} != set(entries):
        raise ValueError("post-hoc annotations and source manifest disagree")
    for artifact in artifacts:
        path = SOURCES / artifact["local_path"]
        if _sha256(path) != entries[artifact["local_path"]]["sha256"]:
            raise ValueError(f"source checksum mismatch: {artifact['local_path']}")
    evaluator = {
        "version": __version__,
        "filename": wheel.name,
        "sha256": EXPECTED["wheel"],
        "installed_archive_hash": installed_hash,
    }
    return manifest, artifacts, evaluator


def _canonical_metric(metric: str) -> str | None:
    if metric in {"ap", "map50_95"} or metric.endswith(("_ap", "_ap50_95")):
        return "ap"
    if metric in {"ap50", "map50"} or metric.endswith("_ap50"):
        return "ap50"
    if metric in {"ap75", "map75"} or metric.endswith("_ap75"):
        return "ap75"
    return None


def _match(expected: list[tuple[str, float]], actual: list[tuple[str, float]]) -> dict[str, Any]:
    remaining = list(expected)
    tp = 0
    for metric, value in actual:
        index = next(
            (
                offset
                for offset, (expected_metric, expected_value) in enumerate(remaining)
                if metric == expected_metric and abs(value - expected_value) <= 1e-9
            ),
            None,
        )
        if index is not None:
            tp += 1
            remaining.pop(index)
    return {
        "tp": tp,
        "fp": len(actual) - tp,
        "fn": len(remaining),
        "exact": not remaining and tp == len(actual),
    }


def _wilson(successes: int, total: int) -> list[float]:
    if total == 0:
        return [1.0, 1.0]
    z = 1.96
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


def run(wheel: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError(f"development output already exists: {output}")
    manifest, artifacts, evaluator = _verify_inputs(wheel)
    records = []
    for artifact in artifacts:
        expected = [
            (claim["metric"], float(claim["value"])) for claim in artifact["expected_claims"]
        ]
        actual = []
        path = SOURCES / artifact["local_path"]
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
    repositories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        repositories[case["repository"]].append(case)
    metric_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metric in ("ap", "ap50", "ap75"):
        for record in records:
            expected = [item for item in record["expected"] if item[0] == metric]
            actual = [item for item in record["actual"] if item[0] == metric]
            if expected or actual:
                metric_cases[metric].append(_match(expected, actual))
    result = {
        "schema": "reprocheck.holdout-development-study.v1",
        "phase": "development_after_v0.6_holdout_inspection",
        "zero_shot": False,
        "evaluator": evaluator,
        "protocol": {
            "prediction_scope": "Markdown and HTML table claims only",
            "metric_scope": ["ap", "ap50", "ap75"],
            "matching": "multiset metric and value matching",
            "absolute_tolerance": 1e-9,
            "posthoc_annotations": True,
        },
        "corpus": {
            "artifacts": len(cases),
            "claim_bearing_artifacts": len(claim_cases),
            "annotated_claims": sum(case["expected_claims"] for case in cases),
            "repositories": len(repositories),
            "repository_commits": {item["id"]: item["commit"] for item in manifest["repositories"]},
            "source_manifest_sha256": EXPECTED["manifest"],
            "posthoc_annotations_sha256": EXPECTED["annotations"],
            "primary_v0.6_result_sha256": EXPECTED["frozen_result"],
        },
        "summary": {
            **_aggregate(cases),
            "claim_artifact_exact_rate": sum(case["exact"] for case in claim_cases)
            / len(claim_cases),
        },
        "by_repository": {name: _aggregate(group) for name, group in sorted(repositories.items())},
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
    parser = argparse.ArgumentParser(description="run the post-holdout v0.7 development study")
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
        f"version=0.7.0 phase=development tp={summary['tp']} fp={summary['fp']} "
        f"fn={summary['fn']} precision={summary['precision']:.1%} recall={summary['recall']:.1%}"
    )
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
