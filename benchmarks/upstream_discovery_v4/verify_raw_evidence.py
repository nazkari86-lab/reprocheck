from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "raw_evidence"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual: float, expected: float, tolerance: float = 5e-5) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{actual} != {expected} within {tolerance}")


def verify_integrity() -> dict[str, Any]:
    lock = json.loads((ROOT / "raw_evidence.lock.json").read_text(encoding="utf-8"))
    observed = sorted(path.name for path in EVIDENCE.iterdir() if path.is_file())
    expected = sorted(lock["files"])
    if observed != expected:
        raise AssertionError("raw-evidence file set differs from lock")
    for name, record in lock["files"].items():
        if sha256(EVIDENCE / name) != record["sha256"]:
            raise AssertionError(f"raw-evidence digest mismatch: {name}")
    return {"status": "pass", "files": len(expected)}


def verify_popoto() -> dict[str, Any]:
    name = (
        "popoto-locomo-gold-blind-scoring--"
        "tests__benchmarks__results__external__locomo_20260807.json"
    )
    document = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    questions = document["questions"]
    summary = document["summary"]
    if len(questions) != 1_986 or summary["n_ok"] != len(questions):
        raise AssertionError("unexpected LoCoMo question count")
    if any(question["status"] != "ok" for question in questions):
        raise AssertionError("LoCoMo evidence contains a non-ok question")
    metrics = {
        "recall_at_1": 0.2981,
        "recall_at_5": 0.5302,
        "recall_at_10": 0.6017,
        "mrr": 0.4005,
    }
    recomputed: dict[str, float] = {}
    for metric, expected in metrics.items():
        value = sum(float(question[metric]) for question in questions) / len(questions)
        recomputed[metric] = value
        close(value, expected)
        close(float(summary[metric]), expected, tolerance=0.0)
    return {
        "status": "pass",
        "independent_rows": len(questions),
        "recomputed": recomputed,
        "reported": metrics,
    }


def verify_lore() -> dict[str, Any]:
    paths = sorted(EVIDENCE.glob("lore-esbuild-ground-truth-correction--*.json"))
    if len(paths) != 6:
        raise AssertionError("expected six Lore repository result files")
    rows: dict[str, list[dict[str, Any]]] = {"control": [], "lore": []}
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        if len(document["tasks"]) != 65:
            raise AssertionError(f"unexpected Lore run count: {path.name}")
        for task in document["tasks"]:
            rows["control"].append(task["control"]["score"])
            rows["lore"].append(task["lore"]["score"])
    if len(rows["control"]) != 390 or len(rows["lore"]) != 390:
        raise AssertionError("unexpected pooled Lore run count")

    def mean(arm: str, key: str) -> float:
        values = [float(row[key]) for row in rows[arm]]
        return sum(values) / len(values)

    def rate(arm: str, value: float) -> float:
        return sum(float(row["taskSuccess"]) == value for row in rows[arm]) / 390

    observed = {
        "success_rate_control": rate("control", 1.0),
        "success_rate_lore": rate("lore", 1.0),
        "partial_rate_control": rate("control", 0.5),
        "partial_rate_lore": rate("lore", 0.5),
        "fail_rate_control": rate("control", 0.0),
        "fail_rate_lore": rate("lore", 0.0),
        "correctness_control": mean("control", "correctness"),
        "correctness_lore": mean("lore", "correctness"),
        "answer_coverage_control": mean("control", "answerCoverage"),
        "answer_coverage_lore": mean("lore", "answerCoverage"),
        "mean_tool_calls_control": mean("control", "toolCallCount"),
        "mean_tool_calls_lore": mean("lore", "toolCallCount"),
        "mean_tokens_control": mean("control", "tokensUsed"),
        "mean_tokens_lore": mean("lore", "tokensUsed"),
        "mean_wall_time_seconds_control": mean("control", "wallTimeMs") / 1000,
        "mean_wall_time_seconds_lore": mean("lore", "wallTimeMs") / 1000,
    }
    reported = {
        "success_rate_control": 0.892,
        "success_rate_lore": 0.949,
        "partial_rate_control": 0.072,
        "partial_rate_lore": 0.041,
        "fail_rate_control": 0.036,
        "fail_rate_lore": 0.010,
        "correctness_control": 0.873,
        "correctness_lore": 0.908,
        "answer_coverage_control": 0.890,
        "answer_coverage_lore": 0.920,
        "mean_tool_calls_control": 30.7,
        "mean_tool_calls_lore": 18.4,
        "mean_tokens_control": 8_952,
        "mean_tokens_lore": 6_182,
        "mean_wall_time_seconds_control": 110.3,
        "mean_wall_time_seconds_lore": 101.7,
    }
    for metric, expected in reported.items():
        decimals = 0 if metric.startswith("mean_tokens") else 1
        scaled_expected = expected * 100 if "_rate_" in metric or metric.startswith(("success_", "partial_", "fail_", "correctness_", "answer_")) else expected
        scaled_observed = observed[metric] * 100 if scaled_expected != expected else observed[metric]
        if round(scaled_observed, decimals) != round(scaled_expected, decimals):
            raise AssertionError(f"Lore report mismatch for {metric}")

    deltas = {
        "success_rate_delta_pp": (observed["success_rate_lore"] - observed["success_rate_control"]) * 100,
        "partial_rate_delta_pp": (observed["partial_rate_lore"] - observed["partial_rate_control"]) * 100,
        "fail_rate_delta_pp": (observed["fail_rate_lore"] - observed["fail_rate_control"]) * 100,
        "correctness_delta_pp": (observed["correctness_lore"] - observed["correctness_control"]) * 100,
        "answer_coverage_delta_pp": (observed["answer_coverage_lore"] - observed["answer_coverage_control"]) * 100,
        "mean_tool_calls_delta": observed["mean_tool_calls_lore"] - observed["mean_tool_calls_control"],
        "mean_tokens_delta": observed["mean_tokens_lore"] - observed["mean_tokens_control"],
        "mean_wall_time_seconds_delta": observed["mean_wall_time_seconds_lore"] - observed["mean_wall_time_seconds_control"],
    }
    expected_deltas = {
        "success_rate_delta_pp": 5.6,
        "partial_rate_delta_pp": -3.1,
        "fail_rate_delta_pp": -2.6,
        "correctness_delta_pp": 3.5,
        "answer_coverage_delta_pp": 3.0,
        "mean_tool_calls_delta": -12.3,
        "mean_tokens_delta": -2_771,
        "mean_wall_time_seconds_delta": -8.6,
    }
    for metric, expected in expected_deltas.items():
        decimals = 0 if metric == "mean_tokens_delta" else 1
        if round(deltas[metric], decimals) != expected:
            raise AssertionError(f"Lore delta mismatch for {metric}")
    return {
        "status": "pass",
        "repositories": len(paths),
        "independent_runs_per_arm": 390,
        "recomputed": observed,
        "deltas": deltas,
    }


def verify_sestrav() -> dict[str, Any]:
    prediction_path = EVIDENCE / (
        "sestrav-feature-count-label-correction--models__rf_oof_predictions.csv"
    )
    metrics_path = EVIDENCE / (
        "sestrav-feature-count-label-correction--results__table3_tier_a_metrics.csv"
    )
    feature_modes: set[str] = set()
    prediction_rows = 0
    with prediction_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            prediction_rows += 1
            feature_modes.add(row["feature_mode"])
    if prediction_rows != 35_555 or feature_modes != {"31"}:
        raise AssertionError("SESTRAV predictions do not establish 31-feature mode")
    with metrics_path.open(encoding="utf-8", newline="") as handle:
        metrics = {row["tool"]: row for row in csv.DictReader(handle)}
    row = metrics["SESTRAV RF"]
    close(float(row["auc_roc"]), 0.7255)
    close(float(row["auc_pr"]), 0.8278)
    close(float(row["issr_10"]), 0.8429)
    if int(row["n_scored"]) != 704:
        raise AssertionError("unexpected SESTRAV scored-row count")
    return {
        "status": "pass",
        "independent_prediction_rows": prediction_rows,
        "feature_modes": sorted(feature_modes),
        "tier_a_metrics": {
            "n_scored": int(row["n_scored"]),
            "auc_roc": float(row["auc_roc"]),
            "auc_pr": float(row["auc_pr"]),
            "issr_10": float(row["issr_10"]),
        },
    }


def main() -> int:
    result = {
        "schema_version": "reprocheck.upstream-discovery-raw-evidence-verification.v1",
        "uses_reprocheck_parser": False,
        "integrity": verify_integrity(),
        "cases": {
            "popoto-locomo-gold-blind-scoring": verify_popoto(),
            "lore-esbuild-ground-truth-correction": verify_lore(),
            "sestrav-feature-count-label-correction": verify_sestrav(),
        },
    }
    result["summary"] = {
        "cases_with_raw_evidence": len(result["cases"]),
        "cases_verified": sum(case["status"] == "pass" for case in result["cases"].values()),
        "agreement_rate": 1.0,
    }
    output = ROOT / "raw_evidence_verification.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("PASS: 3/3 eligible cases with raw evidence independently reproduced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
