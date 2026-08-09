from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import re
import statistics
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Callable
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .audit import run_audit
from .claims import extract_claims
from .documents import extract_document_text
from .evidence import load_metrics
from .metric_names import is_unit_interval_metric, scoped_metric_name
from .models import Claim
from .notebook import audit_notebook


_BASELINE_RE = re.compile(
    r"(?<![\w])(?P<metric>accuracy|precision|recall|f1(?:[-_ ]score)?|"
    r"dice(?: score)?|iou|rmse|mae|r2|r²)(?![\w])\s*"
    r"(?:=|:|of|at)?\s*(?P<value>[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*"
    r"(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_BASELINE_ALIASES = {
    "f1-score": "f1",
    "f1 score": "f1",
    "f1_score": "f1",
    "dice score": "dice",
    "r²": "r2",
}
_FORMAT_INLINE_RE = re.compile(
    r"(?<![\w])(?P<metric>accuracy|acc|precision|recall|f1(?:[-_ ]score)?|"
    r"dice(?: score)?|iou|mean[_ ]iou|miou|rmse|mae|r2|r²)(?![\w])\s*"
    r"(?:=|:|of|at)?\s*(?P<value>[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*"
    r"(?P<percent>%)?",
    flags=re.IGNORECASE,
)
_FORMAT_ALIASES = {
    **_BASELINE_ALIASES,
    "acc": "accuracy",
    "mean iou": "miou",
    "mean_iou": "miou",
}
_FORMAT_UNIT_METRICS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "dice",
    "iou",
    "miou",
}
_FORMAT_DIRECT_ALIASES = {
    "accuracy": "accuracy",
    "acc": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "f1_score": "f1",
    "dice": "dice",
    "mean_iou": "miou",
    "miou": "miou",
    "iou": "iou",
    "rmse": "rmse",
    "mae": "mae",
    "r2": "r2",
}
_FORMAT_FAMILY_WORDS = {
    "accuracy",
    "acc",
    "precision",
    "recall",
    "f1",
    "dice",
    "iou",
    "map",
    "rmse",
    "mae",
    "r2",
}


def run_real_artifact_study(
    corpus_root: Path,
    output: Path | None = None,
    *,
    repeats: int = 3,
    bootstrap_samples: int = 5_000,
) -> dict[str, Any]:
    if repeats < 1 or bootstrap_samples < 1:
        raise ValueError("study repeats and bootstrap samples must be positive")
    corpus_root = corpus_root.resolve()
    sources = corpus_root / "sources"
    manifest_path = corpus_root / "source_manifest.json"
    annotations_path = corpus_root / "annotations.json"
    manifest = _load_object(manifest_path)
    annotations = _load_object(annotations_path)
    repository_commits = _repository_commits(manifest)
    manifest_entries = _manifest_artifacts(manifest)
    annotation_items = _artifact_annotations(annotations)
    if set(repository_commits) != {item["repository"] for item in manifest_entries.values()}:
        raise ValueError("real-artifact repository metadata and artifact entries disagree")
    if set(manifest_entries) != {item["local_path"] for item in annotation_items}:
        raise ValueError("real-artifact manifest and annotations cover different files")
    for annotation in annotation_items:
        manifest_entry = manifest_entries[annotation["local_path"]]
        if annotation["repository"] != manifest_entry["repository"]:
            raise ValueError("real-artifact manifest and annotation repositories disagree")

    cases = []
    for annotation in annotation_items:
        local_path = annotation["local_path"]
        path = _safe_source_path(sources, local_path)
        _verify_source(path, manifest_entries[local_path], annotation)
        durations = []
        actual_claims: list[Claim] = []
        notebook_codes: list[str] | None = None
        text = ""
        for _ in range(repeats):
            started = time.perf_counter_ns()
            text = extract_document_text(path)
            actual_claims = extract_claims(text)
            if annotation["expected_notebook_finding_codes"] is not None:
                notebook_codes = [item["code"] for item in audit_notebook(path).findings]
            durations.append((time.perf_counter_ns() - started) / 1_000_000)
        expected = [
            (item["metric"], float(item["value"])) for item in annotation["expected_claims"]
        ]
        actual = [(claim.metric, claim.value) for claim in actual_claims]
        baseline = _naive_claims(text)
        format_aware = _format_aware_claims(path, text)
        repro_stats = _match_claims(expected, actual)
        baseline_stats = _match_claims(expected, baseline)
        format_aware_stats = _match_claims(expected, format_aware)
        expected_codes = annotation["expected_notebook_finding_codes"]
        notebook_exact = expected_codes is None or Counter(expected_codes) == Counter(
            notebook_codes
        )
        cases.append(
            {
                "repository": annotation["repository"],
                "local_path": local_path,
                "annotation_method": annotation["annotation_method"],
                "expected_claims": len(expected),
                "reprocheck": repro_stats,
                "baseline": baseline_stats,
                "format_aware": format_aware_stats,
                "expected_notebook_finding_codes": expected_codes,
                "actual_notebook_finding_codes": notebook_codes,
                "notebook_exact": notebook_exact,
                "latency_ms": statistics.median(durations),
                "exact": repro_stats["fp"] == 0 and repro_stats["fn"] == 0 and notebook_exact,
            }
        )

    repro_summary = _aggregate(cases, "reprocheck")
    baseline_summary = _aggregate(cases, "baseline")
    format_aware_summary = _aggregate(cases, "format_aware")
    notebook_cases = [case for case in cases if case["expected_notebook_finding_codes"] is not None]
    claim_cases = [case for case in cases if case["expected_claims"]]
    if not claim_cases:
        raise ValueError("real-artifact study requires at least one annotated claim")
    mutation = _mutation_study(corpus_root, annotation_items)
    paired_delta = _paired_recall_delta(claim_cases, "baseline", bootstrap_samples)
    format_aware_delta = _paired_recall_delta(claim_cases, "format_aware", bootstrap_samples)
    result = {
        "schema_version": "2.0",
        "corpus": {
            "artifacts": len(cases),
            "repositories": len({case["repository"] for case in cases}),
            "repository_commits": repository_commits,
            "source_manifest_sha256": _sha256_file(manifest_path),
            "annotations_sha256": _sha256_file(annotations_path),
            "annotated_claims": sum(case["expected_claims"] for case in cases),
            "claim_bearing_artifacts": len(claim_cases),
            "notebooks": len(notebook_cases),
            "reviewers": annotations.get("reviewers"),
            "limitations": annotations.get("limitations", []),
        },
        "reprocheck": {
            **repro_summary,
            "artifact_exact_rate": sum(case["exact"] for case in cases) / len(cases),
            "claim_artifact_exact_rate": sum(case["exact"] for case in claim_cases)
            / len(claim_cases),
            "notebook_annotation_agreement": (
                sum(case["notebook_exact"] for case in notebook_cases) / len(notebook_cases)
                if notebook_cases
                else 1.0
            ),
        },
        "naive_inline_baseline": baseline_summary,
        "format_aware_baseline": format_aware_summary,
        "paired_claim_recall_delta": paired_delta,
        "paired_claim_recall_delta_vs_format_aware": format_aware_delta,
        "mutation_detection": mutation,
        "latency_ms": {
            "median": statistics.median(case["latency_ms"] for case in cases),
            "p95": _quantile([case["latency_ms"] for case in cases], 0.95),
            "max": max(case["latency_ms"] for case in cases),
            "repeats_per_artifact": repeats,
        },
        "by_repository": {
            repository: {
                "artifacts": len(repository_cases),
                "reprocheck": _aggregate(repository_cases, "reprocheck"),
                "naive_inline_baseline": _aggregate(repository_cases, "baseline"),
                "format_aware_baseline": _aggregate(repository_cases, "format_aware"),
            }
            for repository, repository_cases in _group_cases(cases).items()
        },
        "cases": cases,
    }
    validate_study_result(result)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def validate_study_result(result: dict[str, Any]) -> None:
    schema_names = {"2.0": "real-study-v2.schema.json"}
    schema_version = result.get("schema_version")
    schema_name = schema_names.get(schema_version) if isinstance(schema_version, str) else None
    if schema_name is None:
        raise ValueError("unsupported real-artifact study schema version")
    schema = json.loads(files("reprocheck").joinpath("schemas", schema_name).read_text("utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(result), key=lambda item: list(item.path)
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "root"
        raise ValueError(f"invalid real-artifact study result at {location}: {errors[0].message}")


def study_passed(result: dict[str, Any]) -> bool:
    return bool(
        result["reprocheck"]["precision"] == 1.0
        and result["reprocheck"]["recall"] == 1.0
        and result["reprocheck"]["artifact_exact_rate"] == 1.0
        and result["reprocheck"]["notebook_annotation_agreement"] == 1.0
        and result["mutation_detection"]["reprocheck"]["defect_detection_rate"] == 1.0
        and result["mutation_detection"]["reprocheck"]["negative_control_correct_rate"] == 1.0
    )


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read real-artifact file {path.name}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"real-artifact file must be a JSON object: {path.name}")
    return payload


def _repository_commits(manifest: dict[str, Any]) -> dict[str, str]:
    repositories = manifest.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("real-artifact manifest must declare repositories")
    commits: dict[str, str] = {}
    for item in repositories:
        if not isinstance(item, dict):
            raise ValueError("real-artifact repository entry must be an object")
        repository = item.get("id")
        commit = item.get("commit")
        if not isinstance(repository, str) or not repository:
            raise ValueError("real-artifact repository entry must declare an id")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError(f"real-artifact repository {repository} has an invalid commit")
        if repository in commits:
            raise ValueError(f"duplicate real-artifact repository: {repository}")
        commits[repository] = commit
    return dict(sorted(commits.items()))


def _manifest_artifacts(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("real-artifact manifest must contain an entries array")
    artifacts: dict[str, dict[str, Any]] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("real-artifact manifest entry must be an object")
        if item.get("kind") != "artifact":
            continue
        local_path = item.get("local_path")
        repository = item.get("repository")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        if not isinstance(local_path, str) or not local_path:
            raise ValueError("real-artifact manifest entry must declare a local_path")
        if not isinstance(repository, str) or not repository:
            raise ValueError(f"real-artifact manifest entry has no repository: {local_path}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"real-artifact manifest entry has an invalid size: {local_path}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"real-artifact manifest entry has an invalid sha256: {local_path}")
        if local_path in artifacts:
            raise ValueError(f"duplicate real-artifact manifest path: {local_path}")
        artifacts[local_path] = item
    if not artifacts:
        raise ValueError("real-artifact manifest contains no artifacts")
    return artifacts


def _artifact_annotations(annotations: dict[str, Any]) -> list[dict[str, Any]]:
    items = annotations.get("artifacts")
    if not isinstance(items, list):
        raise ValueError("real-artifact annotations must contain an artifacts array")
    normalized: list[dict[str, Any]] = []
    paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("real-artifact annotation must be an object")
        local_path = item.get("local_path")
        if not isinstance(local_path, str) or not local_path:
            raise ValueError("real-artifact annotation must declare a local_path")
        if local_path in paths:
            raise ValueError(f"duplicate real-artifact annotation path: {local_path}")
        if not isinstance(item.get("repository"), str) or not item["repository"]:
            raise ValueError(f"real-artifact annotation has no repository: {local_path}")
        if not isinstance(item.get("expected_claims"), list):
            raise ValueError(f"real-artifact annotation has invalid expected_claims: {local_path}")
        paths.add(local_path)
        normalized.append(item)
    if not normalized:
        raise ValueError("real-artifact annotations contain no artifacts")
    return normalized


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_source_path(sources: Path, local_path: str) -> Path:
    path = (sources / local_path).resolve()
    if not path.is_relative_to(sources.resolve()) or not path.is_file():
        raise ValueError(f"unsafe or missing real-artifact source: {local_path}")
    return path


def _verify_source(path: Path, manifest: dict[str, Any], annotation: dict[str, Any]) -> None:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if len(payload) != manifest.get("size_bytes") or digest != manifest.get("sha256"):
        raise ValueError(f"real-artifact source checksum mismatch: {path.name}")
    if digest != annotation.get("source_sha256"):
        raise ValueError(f"real-artifact annotation checksum mismatch: {path.name}")


def _naive_claims(text: str) -> list[tuple[str, float]]:
    claims = []
    for match in _BASELINE_RE.finditer(text):
        raw_metric = match.group("metric").casefold()
        metric = _BASELINE_ALIASES.get(raw_metric, raw_metric)
        value = float(match.group("value").replace(",", "."))
        if match.group("percent") or (is_unit_interval_metric(metric) and 1 < value <= 100):
            value /= 100
        claims.append((metric, value))
    return claims


def _format_aware_claims(path: Path, text: str) -> list[tuple[str, float]]:
    if path.suffix.casefold() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        claims = _format_json_claims(payload)
        claims.extend(
            claim for string in _json_strings(payload) for claim in _format_inline_claims(string)
        )
        return claims
    claims = _format_inline_claims(text)
    if path.suffix.casefold() in {".md", ".txt", ".rst"}:
        claims.extend(_format_table_claims(text))
    return claims


def _format_inline_claims(text: str) -> list[tuple[str, float]]:
    claims = []
    for match in _FORMAT_INLINE_RE.finditer(text):
        raw_metric = match.group("metric").casefold()
        metric = _FORMAT_ALIASES.get(raw_metric, raw_metric)
        value = float(match.group("value").replace(",", "."))
        if match.group("percent") or (metric in _FORMAT_UNIT_METRICS and 1 < value <= 100):
            value /= 100
        claims.append((metric, value))
    return claims


def _format_json_claims(payload: object) -> list[tuple[str, float]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("eval_metrics"), dict):
        return []
    claims: list[tuple[str, float]] = []

    def visit(value: object, path: tuple[object, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, (*path, key))
            return
        if isinstance(value, bool):
            return
        metric = _format_metric_from_path(path)
        if metric is None:
            return
        try:
            numeric = float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return
        if 1 < numeric <= 100:
            numeric /= 100
        claims.append((metric, numeric))

    visit(payload["eval_metrics"])
    return claims


def _json_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in _json_strings(child)]
    if isinstance(value, list):
        return [text for child in value for text in _json_strings(child)]
    return []


def _format_metric_from_path(parts: tuple[object, ...]) -> str | None:
    normalized = tuple(
        re.sub(r"[^\w²]+", "_", str(part).strip().casefold()).strip("_") for part in parts
    )
    for index, part in enumerate(normalized):
        if part in _FORMAT_DIRECT_ALIASES or set(part.split("_")) & _FORMAT_FAMILY_WORDS:
            scoped = "_".join(normalized[index:])
            return _FORMAT_DIRECT_ALIASES.get(scoped, scoped)
    return None


def _format_table_claims(text: str) -> list[tuple[str, float]]:
    lines = text.splitlines()
    claims: list[tuple[str, float]] = []
    for index in range(len(lines) - 2):
        headers = _format_table_row(lines[index])
        separators = _format_table_row(lines[index + 1])
        if (
            not headers
            or not separators
            or not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in separators)
        ):
            continue
        metrics = [_format_table_metric(header) for header in headers]
        row = index + 2
        while row < len(lines):
            cells = _format_table_row(lines[row])
            if not cells:
                break
            for column, metric in enumerate(metrics):
                if metric is None or column >= len(cells):
                    continue
                match = re.fullmatch(
                    r"\s*(?P<value>[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+))\s*(?P<percent>%)?\s*",
                    cells[column],
                )
                if match is None:
                    continue
                value = float(match.group("value").replace(",", "."))
                if match.group("percent") or (metric in _FORMAT_UNIT_METRICS and 1 < value <= 100):
                    value /= 100
                claims.append((metric, value))
            row += 1
    return claims


def _format_table_row(line: str) -> list[str] | None:
    if "|" not in line:
        return None
    stripped = line.strip().strip("|")
    cells = [cell.strip() for cell in stripped.split("|")]
    return cells if len(cells) >= 2 else None


def _format_table_metric(header: str) -> str | None:
    plain = re.sub(r"<[^>]+>", " ", header)
    plain = re.sub(r"!?\[([^]]*)\]\([^)]*\)", r"\1", plain)
    normalized = re.sub(r"[^\w²]+", "_", plain.casefold()).strip("_")
    words = set(normalized.split("_"))
    for alias, metric in _FORMAT_DIRECT_ALIASES.items():
        if alias in normalized or set(alias.split("_")) <= words:
            return metric
    return None


def _match_claims(
    expected: list[tuple[str, float]], actual: list[tuple[str, float]], tolerance: float = 1e-9
) -> dict[str, Any]:
    remaining = list(expected)
    true_positives = 0
    for metric, value in actual:
        match_index = next(
            (
                index
                for index, (expected_metric, expected_value) in enumerate(remaining)
                if metric == expected_metric and abs(value - expected_value) <= tolerance
            ),
            None,
        )
        if match_index is not None:
            true_positives += 1
            remaining.pop(match_index)
    return {
        "tp": true_positives,
        "fp": len(actual) - true_positives,
        "fn": len(remaining),
        "exact": len(actual) == true_positives and not remaining,
    }


def _aggregate(cases: list[dict[str, Any]], key: str) -> dict[str, Any]:
    tp = sum(case[key]["tp"] for case in cases)
    fp = sum(case[key]["fp"] for case in cases)
    fn = sum(case[key]["fn"] for case in cases)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "precision_wilson_95": _wilson(tp, tp + fp),
        "recall": recall,
        "recall_wilson_95": _wilson(tp, tp + fn),
        "artifact_exact_rate": sum(case[key]["exact"] for case in cases) / len(cases),
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


def _paired_recall_delta(
    cases: list[dict[str, Any]], baseline_key: str, samples: int
) -> dict[str, Any]:
    deltas = [
        case["reprocheck"]["tp"] / case["expected_claims"]
        - case[baseline_key]["tp"] / case["expected_claims"]
        for case in cases
    ]
    observed = statistics.mean(deltas)
    generator = random.Random(2026)
    bootstrapped = sorted(
        statistics.mean(generator.choice(deltas) for _ in deltas) for _ in range(samples)
    )
    return {
        "mean_artifact_recall_delta": observed,
        "paired_bootstrap_95": [
            _quantile(bootstrapped, 0.025),
            _quantile(bootstrapped, 0.975),
        ],
        "bootstrap_samples": samples,
        "seed": 2026,
    }


def _mutation_study(corpus_root: Path, annotations: list[dict[str, Any]]) -> dict[str, Any]:
    tolerance = 0.005
    detector_names = ("reprocheck", "naive_inline", "format_aware")
    totals = {
        name: {"defect_cases": 0, "defects_detected": 0, "control_cases": 0, "controls_correct": 0}
        for name in detector_names
    }
    by_mutation: dict[str, dict[str, Any]] = {}
    case_index = 0
    with tempfile.TemporaryDirectory(prefix="reprocheck-real-mutations-") as directory:
        mutation_root = Path(directory)
        for annotation in annotations:
            rule_claims = [
                claim
                for claim in annotation["expected_claims"]
                if claim["review"] == "rule_derived"
            ]
            if annotation["repository"] != "monai_model_zoo" or not rule_claims:
                continue
            source = corpus_root / "sources" / annotation["local_path"]
            payload = json.loads(source.read_text(encoding="utf-8"))
            observed = load_metrics(source, selector="eval_metrics")
            for mutation in _mutation_variants(payload, rule_claims, source.name):
                report = mutation_root / f"case-{case_index}.json"
                report.write_text(
                    json.dumps(mutation["payload"], ensure_ascii=False), encoding="utf-8"
                )
                text = extract_document_text(report)
                audit = run_audit(
                    report_path=report,
                    metrics_path=source,
                    metrics_selector="eval_metrics",
                    tolerance=tolerance,
                )
                signals = mutation["signal_metrics"]
                expected_detection = mutation["expected_detection"]
                outcomes = {
                    "reprocheck": _audit_mutation_outcome(
                        audit.claims, signals, expected_detection
                    ),
                    "naive_inline": _claim_mutation_outcome(
                        _naive_claims(text), observed, signals, expected_detection, tolerance
                    ),
                    "format_aware": _claim_mutation_outcome(
                        _format_aware_claims(report, text),
                        observed,
                        signals,
                        expected_detection,
                        tolerance,
                    ),
                }
                mutation_summary = by_mutation.setdefault(
                    mutation["name"],
                    {
                        "cases": 0,
                        "expected_detection": expected_detection,
                        **{f"{name}_correct": 0 for name in detector_names},
                    },
                )
                mutation_summary["cases"] += 1
                for detector, correct in outcomes.items():
                    mutation_summary[f"{detector}_correct"] += int(correct)
                    category = "defect" if expected_detection else "control"
                    totals[detector][f"{category}_cases"] += 1
                    totals[detector][
                        "defects_detected" if expected_detection else "controls_correct"
                    ] += int(correct)
                case_index += 1
    for summary in by_mutation.values():
        for detector in detector_names:
            summary[f"{detector}_correct_rate"] = summary[f"{detector}_correct"] / summary["cases"]
    detector_summaries = {}
    for detector, counts in totals.items():
        detector_summaries[detector] = {
            **counts,
            "defect_detection_rate": counts["defects_detected"] / counts["defect_cases"],
            "negative_control_correct_rate": counts["controls_correct"] / counts["control_cases"],
            "negative_control_false_alarms_or_omissions": counts["control_cases"]
            - counts["controls_correct"],
        }
    return {
        "cases": case_index,
        "defect_cases": detector_summaries["reprocheck"]["defect_cases"],
        "negative_control_cases": detector_summaries["reprocheck"]["control_cases"],
        "tolerance": tolerance,
        "reprocheck": detector_summaries["reprocheck"],
        "naive_inline_baseline": detector_summaries["naive_inline"],
        "format_aware_baseline": detector_summaries["format_aware"],
        "by_mutation": dict(sorted(by_mutation.items())),
    }


def _mutation_variants(
    payload: dict[str, Any], rule_claims: list[dict[str, Any]], source_name: str
) -> list[dict[str, Any]]:
    target = (rule_claims[0]["metric"], float(rule_claims[0]["value"]))
    variants = [
        _changed_variant(
            payload, target, "large_value_shift", True, lambda value: _shift(value, 0.2)
        ),
        _changed_variant(
            payload, target, "outside_tolerance", True, lambda value: _shift(value, 0.006)
        ),
        _changed_variant(
            payload, target, "within_tolerance", False, lambda value: _shift(value, 0.004)
        ),
        _changed_variant(
            payload,
            target,
            "equivalent_percentage_scale",
            False,
            lambda value: value,
            raw_transform=lambda raw, normalized: normalized if raw > 1 else normalized * 100,
        ),
        _changed_variant(
            payload,
            target,
            "equivalent_numeric_string",
            False,
            lambda value: value,
            raw_transform=lambda raw, normalized: str(raw),
        ),
    ]
    inserted = copy.deepcopy(payload)
    eval_metrics = inserted.get("eval_metrics")
    if not isinstance(eval_metrics, dict):
        raise ValueError(f"cannot insert mutation target in {source_name}")
    injected_metric = "injected_accuracy"
    if injected_metric in eval_metrics:
        raise ValueError(f"mutation key already exists in {source_name}")
    eval_metrics[injected_metric] = 0.123
    variants.append(
        {
            "name": "unsupported_metric_insertion",
            "payload": inserted,
            "expected_detection": True,
            "signal_metrics": [injected_metric],
        }
    )
    distinct_claims = []
    for claim in rule_claims:
        candidate = (claim["metric"], float(claim["value"]))
        if not distinct_claims or abs(candidate[1] - distinct_claims[0][1]) > 0.005:
            distinct_claims.append(candidate)
        if len(distinct_claims) == 2:
            swapped = copy.deepcopy(payload)
            if not _swap_metrics(swapped.get("eval_metrics", {}), *distinct_claims):
                raise ValueError(f"cannot swap mutation targets in {source_name}")
            variants.append(
                {
                    "name": "swapped_metric_values",
                    "payload": swapped,
                    "expected_detection": True,
                    "signal_metrics": [item[0] for item in distinct_claims],
                }
            )
            break
    return variants


def _changed_variant(
    payload: dict[str, Any],
    target: tuple[str, float],
    name: str,
    expected_detection: bool,
    normalized_transform: Callable[[float], float],
    *,
    raw_transform: Callable[[float, float], object] | None = None,
) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    located = _metric_location(mutated.get("eval_metrics", {}), target)
    if located is None:
        raise ValueError("cannot locate mutation target")
    container, key, raw, normalized = located
    changed = normalized_transform(normalized)
    container[key] = (
        raw_transform(raw, changed)
        if raw_transform is not None
        else changed * 100
        if raw > 1
        else changed
    )
    return {
        "name": name,
        "payload": mutated,
        "expected_detection": expected_detection,
        "signal_metrics": [target[0]],
    }


def _shift(value: float, amount: float) -> float:
    return value + amount if value + amount <= 1 else value - amount


def _audit_mutation_outcome(
    checks: list[Any], signal_metrics: list[str], expected_detection: bool
) -> bool:
    relevant = [check for check in checks if check.claim.metric in signal_metrics]
    detected = any(check.status in {"mismatch", "no_evidence"} for check in relevant)
    if expected_detection:
        return detected
    preserved = all(
        any(check.claim.metric == metric and check.status == "supported" for check in relevant)
        for metric in signal_metrics
    )
    return not detected and preserved


def _claim_mutation_outcome(
    claims: list[tuple[str, float]],
    observed: dict[str, float],
    signal_metrics: list[str],
    expected_detection: bool,
    tolerance: float,
) -> bool:
    relevant = [(metric, value) for metric, value in claims if metric in signal_metrics]
    detected = any(
        metric not in observed or abs(value - observed[metric]) > tolerance
        for metric, value in relevant
    )
    if expected_detection:
        return detected
    preserved = all(
        expected in observed
        and any(
            metric == expected and abs(value - observed[expected]) <= tolerance
            for metric, value in relevant
        )
        for expected in signal_metrics
    )
    return not detected and preserved


def _mutate_metric(value: object, target: tuple[str, float], path: tuple[object, ...] = ()) -> bool:
    located = _metric_location(value, target, path)
    if located is None:
        return False
    container, key, raw, normalized = located
    changed = _shift(normalized, 0.2)
    container[key] = changed * 100 if raw > 1 else changed
    return True


def _metric_location(
    value: object, target: tuple[str, float], path: tuple[object, ...] = ()
) -> tuple[dict[Any, Any], object, float, float] | None:
    if not isinstance(value, dict):
        return None
    for key, child in value.items():
        child_path = (*path, key)
        if isinstance(child, dict):
            located = _metric_location(child, target, child_path)
            if located is not None:
                return located
            continue
        if not isinstance(child, (int, float)) or isinstance(child, bool):
            continue
        metric = scoped_metric_name(child_path)
        raw = float(child)
        normalized = raw
        if is_unit_interval_metric(metric or "") and 1 < normalized <= 100:
            normalized /= 100
        if metric == target[0] and abs(normalized - target[1]) <= 1e-9:
            return value, key, raw, normalized
    return None


def _swap_metrics(value: object, first: tuple[str, float], second: tuple[str, float]) -> bool:
    first_location = _metric_location(value, first)
    second_location = _metric_location(value, second)
    if first_location is None or second_location is None:
        return False
    first_container, first_key, first_raw, first_normalized = first_location
    second_container, second_key, second_raw, second_normalized = second_location
    first_container[first_key] = second_normalized * 100 if first_raw > 1 else second_normalized
    second_container[second_key] = first_normalized * 100 if second_raw > 1 else first_normalized
    return True


def _group_cases(cases: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["repository"]].append(case)
    return dict(sorted(grouped.items()))


def _quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    left = math.floor(position)
    right = math.ceil(position)
    if left == right:
        return ordered[left]
    return ordered[left] + (ordered[right] - ordered[left]) * (position - left)
