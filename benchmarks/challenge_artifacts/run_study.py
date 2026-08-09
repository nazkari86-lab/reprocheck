from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from importlib.metadata import distribution
from pathlib import Path
from typing import Any

from reprocheck import claims as claim_extraction
from reprocheck.documents import extract_document_text
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "source_manifest.json"
ANNOTATIONS = ROOT / "annotations.json"
POSTHOC_REVIEW = ROOT / "posthoc_label_review.json"
SOURCES = ROOT / "sources"
_ALIASES = {
    "map50_95": "ap",
    "map50": "ap50",
    "map75": "ap75",
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path.name}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_installed_evaluator(artifact: Path, expected_version: str) -> dict[str, str]:
    artifact = artifact.resolve()
    digest = _sha256(artifact)
    if __version__ != expected_version:
        raise ValueError(
            f"installed ReproCheck version is {__version__}, expected {expected_version}"
        )
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


def _verify_corpus(manifest: dict[str, Any], annotations: dict[str, Any]) -> list[dict[str, Any]]:
    entries = {
        entry["local_path"]: entry
        for entry in manifest.get("entries", [])
        if entry.get("kind") == "artifact"
    }
    items = annotations.get("artifacts")
    if not isinstance(items, list) or not items:
        raise ValueError("challenge annotations must contain artifacts")
    paths = [item.get("local_path") for item in items]
    if len(paths) != len(set(paths)) or set(entries) != set(paths):
        raise ValueError("challenge manifest and annotations disagree")
    for item in items:
        local_path = item["local_path"]
        source = (SOURCES / local_path).resolve()
        if not source.is_relative_to(SOURCES.resolve()) or not source.is_file():
            raise ValueError(f"unsafe or missing challenge source: {local_path}")
        entry = entries[local_path]
        if source.stat().st_size != entry["size_bytes"] or _sha256(source) != entry["sha256"]:
            raise ValueError(f"challenge source checksum mismatch: {local_path}")
        if entry["sha256"] != item.get("source_sha256"):
            raise ValueError(f"challenge annotation checksum mismatch: {local_path}")
    return items


def _extract_table_claims(text: str) -> tuple[list[Any], str]:
    public_extractor = getattr(claim_extraction, "extract_table_claims", None)
    if public_extractor is not None:
        return list(public_extractor(text)), "public_extract_table_claims"

    # ReproCheck 0.5 predates the public table-only API. Its frozen private
    # Markdown parser provides the same evaluation scope for compatibility.
    markdown_extractor = getattr(claim_extraction, "_extract_markdown_table_claims", None)
    if markdown_extractor is None:
        raise ValueError("installed evaluator has no compatible table claim extractor")
    claims = list(markdown_extractor(text.splitlines()))
    html_extractor = getattr(claim_extraction, "_extract_html_table_claims", None)
    if html_extractor is not None:
        claims.extend(html_extractor(text))
    claims.sort(key=lambda claim: claim.line)
    return claims, "v0.5_private_table_compatibility"


def _challenge_metric(metric: str, declared: set[str]) -> str | None:
    canonical = _ALIASES.get(metric, metric)
    return canonical if canonical in declared else None


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


def run(artifact: Path, expected_version: str, output: Path, phase: str) -> dict[str, Any]:
    evaluator = _verify_installed_evaluator(artifact, expected_version)
    manifest = _load_object(MANIFEST)
    annotations = _load_object(ANNOTATIONS)
    posthoc_review = _load_object(POSTHOC_REVIEW)
    items = _verify_corpus(manifest, annotations)
    declared = {claim["metric"] for item in items for claim in item.get("expected_claims", [])}
    records = []
    extractor_names: set[str] = set()
    for item in items:
        path = SOURCES / item["local_path"]
        expected = [(claim["metric"], float(claim["value"])) for claim in item["expected_claims"]]
        extracted = []
        table_claims, extractor_name = _extract_table_claims(extract_document_text(path))
        extractor_names.add(extractor_name)
        for claim in table_claims:
            metric = _challenge_metric(claim.metric, declared)
            if metric is not None:
                extracted.append((metric, claim.value))
        case = {
            "repository": item["repository"],
            "local_path": item["local_path"],
            "expected_claims": len(expected),
            "extracted_scoped_claims": len(extracted),
            **_match(expected, extracted),
        }
        records.append({"case": case, "expected": expected, "actual": extracted})
    if len(extractor_names) != 1:
        raise ValueError("challenge evaluation used inconsistent claim extractors")
    extractor_name = next(iter(extractor_names))
    cases = [record["case"] for record in records]
    claim_cases = [case for case in cases if case["expected_claims"]]
    by_repository = {
        repository: _aggregate(repository_cases)
        for repository, repository_cases in _group(cases, "repository").items()
    }
    by_metric_cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for metric in sorted(declared):
        for record in records:
            expected = [claim for claim in record["expected"] if claim[0] == metric]
            actual = [claim for claim in record["actual"] if claim[0] == metric]
            if not expected and not actual:
                continue
            by_metric_cases[metric].append(_match(expected, actual))
    repository_commits = {
        entry["repository"]: entry["commit"]
        for entry in manifest.get("entries", [])
        if entry.get("kind") == "artifact"
    }
    result = {
        "schema": "reprocheck.challenge-study.v2",
        "phase": phase,
        "evaluator": evaluator,
        "evaluation_protocol": {
            "prediction_scope": "Markdown and HTML table claims only",
            "extractor": extractor_name,
            "metric_scope": sorted(declared),
            "matching": "multiset metric and value matching",
            "absolute_tolerance": 1e-9,
            "posthoc_review_excluded_from_primary_metrics": True,
        },
        "corpus": {
            "artifacts": len(cases),
            "claim_bearing_artifacts": len(claim_cases),
            "annotated_claims": sum(case["expected_claims"] for case in cases),
            "repositories": len(by_repository),
            "repository_commits": dict(sorted(repository_commits.items())),
            "source_manifest_sha256": _sha256(MANIFEST),
            "annotations_sha256": _sha256(ANNOTATIONS),
            "posthoc_label_review_sha256": _sha256(POSTHOC_REVIEW),
            "annotation_scope": annotations.get("scope"),
            "annotation_reviewers": annotations.get("reviewers"),
            "limitations": annotations.get("limitations", []),
        },
        "summary": {
            **_aggregate(cases),
            "claim_artifact_exact_rate": sum(case["exact"] for case in claim_cases)
            / len(claim_cases),
        },
        "by_repository": by_repository,
        "by_metric": {
            metric: _aggregate(metric_cases)
            for metric, metric_cases in sorted(by_metric_cases.items())
        },
        "posthoc_label_review": {
            "cases": len(posthoc_review.get("cases", [])),
            "created_after_evaluator_output_inspection": posthoc_review.get(
                "created_after_evaluator_output_inspection"
            ),
            "interpretation": posthoc_review.get("interpretation"),
            "primary_metrics_modified": False,
        },
        "cases": cases,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def _group(cases: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case[key]].append(case)
    return dict(sorted(grouped.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run the frozen challenge corpus")
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument(
        "--phase",
        required=True,
        choices=["frozen_evaluator_replay", "development_after_challenge_inspection"],
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.evaluator_artifact, args.expected_version, args.output, args.phase)
    except (OSError, UnicodeDecodeError, ValueError) as error:
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
