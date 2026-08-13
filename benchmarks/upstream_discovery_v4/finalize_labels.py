from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
EVALUATOR_COMMIT = "4b1ffdf633723c2672449aa15198d259f80b7568"


def source_name(case_id: str, path: str, phase: str) -> str:
    suffix = Path(path).suffix or ".txt"
    return f"{case_id}--{path.replace('/', '__')}.{phase}{suffix}"


def claim(
    case_id: str,
    file: str,
    before_snippet: str,
    after_snippet: str,
    metric: str,
    before_value: float,
    after_value: float,
) -> dict[str, object]:
    before = (ROOT / "sources" / source_name(case_id, file, "before")).read_text(encoding="utf-8")
    after = (ROOT / "sources" / source_name(case_id, file, "after")).read_text(encoding="utf-8")
    assert before.count(before_snippet) == 1, (case_id, file, before_snippet)
    assert after.count(after_snippet) == 1, (case_id, file, after_snippet)
    return {
        "file": file,
        "before_snippet": before_snippet,
        "after_snippet": after_snippet,
        "metric": metric,
        "before_value": before_value,
        "after_value": after_value,
    }


def popoto_claims() -> list[dict[str, object]]:
    case_id = "popoto-locomo-gold-blind-scoring"
    file = "docs/benchmarks.md"
    values = {
        "recall_1": ("Recall@1", 0.2986, 0.2981),
        "recall_5": ("Recall@5", 0.5534, 0.5302),
        "recall_10": ("Recall@10", 0.6400, 0.6017),
        "mrr": ("MRR", 0.4124, 0.4005),
    }
    return [
        claim(
            case_id, file, f"| {label} | {old:.4f} |", f"| {label} | {new:.4f} |", metric, old, new
        )
        for metric, (label, old, new) in values.items()
    ]


def ddharmon_claims() -> list[dict[str, object]]:
    case_id = "ddharmon-authoritative-metric-sync"
    file = "docs/methods.md"
    return [
        claim(
            case_id,
            file,
            "| **Hybrid retrieve** | `BM25` (lexical, over rich CDE text) ⊕ dense centroid cosine, fused by **Reciprocal Rank Fusion**; top-k=20 | The candidate generator. Hybrid beats dense at every k (recall@5 0.447 → 0.632 on the CDEMapper gold); a dense-rich control confirmed the gain is real lexical signal. Reusable in `ddharmon.matching` (`BM25`, `hybrid_topk`). |",
            "| **Hybrid retrieve** | `BM25` (lexical, over rich CDE text) ⊕ dense centroid cosine, fused by **Reciprocal Rank Fusion**; top-k=20 | The candidate generator. Hybrid beats dense on the CDEMapper gold (recall@5 0.674); a dense-rich control confirmed the gain is real lexical signal. Reusable in `ddharmon.matching` (`BM25`, `hybrid_topk`). |",
            "recall_5",
            0.632,
            0.674,
        ),
        claim(
            case_id,
            file,
            "| **CDEMapper** | Are we matching the **right CDE**? | Yale CDE-Mapping-Tool (494 field→CDE) | hybrid retrieval recall@5 0.632; fused assignment (in-backbone) 0.521 |",
            "| **CDEMapper** | Are we matching the **right CDE**? | Yale CDE-Mapping-Tool (494 field→CDE) | hybrid retrieval recall@5 0.674; fused assignment (in-backbone) 0.521 |",
            "recall_5",
            0.632,
            0.674,
        ),
        claim(
            case_id,
            file,
            "| **PhenX** | Do same-concept vars from **different cohorts** co-cluster? | PhenX↔dbGaP crosswalk | embedding separability Δ0.536; clustering's edge is diffuse (motivates assignment-first) |",
            "| **PhenX** | Do same-concept vars from **different cohorts** co-cluster? | PhenX↔dbGaP crosswalk | embedding separability Δ0.611; clustering's edge is diffuse (motivates assignment-first) |",
            "separability_delta",
            0.536,
            0.611,
        ),
    ]


def lore_claims() -> list[dict[str, object]]:
    case_id = "lore-esbuild-ground-truth-correction"
    file = "docs/benchmark-results.md"
    rows: list[tuple[str, str, list[float], str, list[float]]] = [
        (
            "success_rate",
            "**Success rate**",
            [81.8, 92.6, 10.8],
            "**Success rate**",
            [89.2, 94.9, 5.6],
        ),
        (
            "partial_rate",
            "**Partial rate**",
            [17.4, 7.4, -10.0],
            "**Partial rate**",
            [7.2, 4.1, -3.1],
        ),
        ("fail_rate", "**Fail rate**", [0.8, 0.0, -0.8], "**Fail rate**", [3.6, 1.0, -2.6]),
        ("correctness", "**Correctness**", [85.1, 86.0, 1.0], "**Correctness**", [87.3, 90.8, 3.5]),
        (
            "answer_coverage",
            "**Answer coverage**",
            [86.9, 88.9, 2.0],
            "**Answer coverage**",
            [89.0, 92.0, 3.0],
        ),
    ]
    claims: list[dict[str, object]] = []
    for metric, before_label, old, after_label, new in rows:
        before = f"| {before_label} | {old[0]:.1f}% | {old[1]:.1f}% | "
        after = f"| {after_label} | {new[0]:.1f}% | {new[1]:.1f}% | "
        before_line = next(
            line
            for line in (ROOT / "sources" / source_name(case_id, file, "before"))
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith(before)
        )
        after_line = next(
            line
            for line in (ROOT / "sources" / source_name(case_id, file, "after"))
            .read_text(encoding="utf-8")
            .splitlines()
            if line.startswith(after)
        )
        for index, suffix in enumerate(("control", "lore", "delta_pp")):
            before_value = old[index] / 100 if index < 2 else old[index]
            after_value = new[index] / 100 if index < 2 else new[index]
            claims.append(
                claim(
                    case_id,
                    file,
                    before_line,
                    after_line,
                    f"{metric}_{suffix}",
                    before_value,
                    after_value,
                )
            )
    numeric_rows = [
        (
            "mean_tool_calls",
            "| **Mean tool calls** | 28.0 | 16.7 | **-11.3 (−40.5%)** |",
            "| **Mean tool calls** | 30.7 | 18.4 | **-12.3 (−40.2%)** |",
            [28.0, 16.7, -11.3, -40.5],
            [30.7, 18.4, -12.3, -40.2],
            ("control", "lore", "delta", "delta_percent"),
        ),
        (
            "mean_tokens",
            "| **Mean tokens** | 8,023 | 5,660 | **-2,363 (−29.5%)** |",
            "| **Mean tokens** | 8,952 | 6,182 | **-2,771 (−30.9%)** |",
            [8023.0, 5660.0, -2363.0, -29.5],
            [8952.0, 6182.0, -2771.0, -30.9],
            ("control", "lore", "delta", "delta_percent"),
        ),
        (
            "mean_wall_time_seconds",
            "| **Mean wall time** | 103.2s | 98.5s | -4.7s (−4.6%) |",
            "| **Mean wall time** | 110.3s | 101.7s | -8.6s (−7.8%) |",
            [103.2, 98.5, -4.7, -4.6],
            [110.3, 101.7, -8.6, -7.8],
            ("control", "lore", "delta", "delta_percent"),
        ),
    ]
    for metric, before, after, old, new, suffixes in numeric_rows:
        for suffix, before_value, after_value in zip(suffixes, old, new, strict=True):
            claims.append(
                claim(
                    case_id,
                    file,
                    before,
                    after,
                    f"{metric}_{suffix}",
                    before_value,
                    after_value,
                )
            )
    return claims


def sekiban_claims() -> list[dict[str, object]]:
    case_id = "sekiban-rss-log-correction"
    file = "docs/benchmark-results.md"
    rows = [
        (
            "| C# Native | `completed` | `2004.1` | `236.7` | `91.0` | `1586.5` | `597.6 s` | `~2626.4 MB` | `0` |",
            "| C# Native (Postgres) | `completed` | `2004.1` | `236.7` | `91.0` | `1586.5` | `597.6 s` | `~1637.2 MB` | `0` |",
            "csharp_native_peak_rss_mb",
            2626.4,
            1637.2,
        ),
        (
            "| MoonBit WASM | `completed` | `1460.5` | `556.8` | `214.1` | `164.5` | `340.9 s` | `~1961.6 MB` | `0` |",
            "| MoonBit WASM | `completed` | `1460.5` | `556.8` | `214.1` | `164.5` | `340.9 s` | `~1301.6 MB` | `0` |",
            "moonbit_wasm_peak_rss_mb",
            1961.6,
            1301.6,
        ),
        (
            "| Go WASM | `completed` | `1547.8` | `520.1` | `200.0` | `335.8` | `388.5 s` | `~2502.4 MB` | `0` |",
            "| Go WASM | `completed` | `1547.8` | `520.1` | `200.0` | `335.8` | `388.5 s` | `~2514.2 MB` | `0` |",
            "go_wasm_peak_rss_mb",
            2502.4,
            2514.2,
        ),
    ]
    return [
        claim(case_id, file, before, after, metric, old, new)
        for before, after, metric, old, new in rows
    ]


def sestrav_claims() -> list[dict[str, object]]:
    case_id = "sestrav-feature-count-label-correction"
    file = "results/external_benchmark_comparison.md"
    return [
        claim(
            case_id,
            file,
            "| SESTRAV RF (30-feat) | 704 | 0.7255 | 0.8278 | 0.8429 | 0.8352 | 0.8429 | 0.1204 | 0.8764 | 0.8352 | 0.3000 | 0.8522 | 0.9788 | 0.9956 |",
            "| SESTRAV RF (31-feat) | 704 | 0.7255 | 0.8278 | 0.8429 | 0.8352 | 0.8429 | 0.1204 | 0.8764 | 0.8352 | 0.3000 | 0.8522 | 0.9788 | 0.9956 |",
            "feature_count",
            30.0,
            31.0,
        )
    ]


def power_table_claims(
    file: str,
    before_rows: dict[str, list[float]],
    after_rows: dict[str, list[float]],
    metrics: dict[str, str],
) -> list[dict[str, object]]:
    case_id = "power-path-parser-metric-correction"
    before_text = (ROOT / "sources" / source_name(case_id, file, "before")).read_text(
        encoding="utf-8"
    )
    after_text = (ROOT / "sources" / source_name(case_id, file, "after")).read_text(
        encoding="utf-8"
    )
    claims: list[dict[str, object]] = []
    for label, old_values in before_rows.items():
        new_values = after_rows[label]
        before_line = next(
            line for line in before_text.splitlines() if line.startswith(f"| {label} |")
        )
        after_line = next(
            line for line in after_text.splitlines() if line.startswith(f"| {label} |")
        )
        for system, old, new in zip(
            ("fts", "vector", "hybrid"), old_values, new_values, strict=True
        ):
            if old == new:
                continue
            claims.append(
                claim(
                    case_id,
                    file,
                    before_line,
                    after_line,
                    f"{metrics[label]}_{system}",
                    old,
                    new,
                )
            )
    return claims


def power_claims() -> list[dict[str, object]]:
    test2 = "docs/tests/P.O.W.E.R.2.0.3-TEST-2.md"
    labels2 = [
        "**MRR**",
        "**MAP@3**",
        "**MAP@5**",
        "**MAR@5**",
        "**MAR@10**",
        "**MnDCG@5**",
        "**MnDCG@10**",
        "**Avg Latency (s)**",
        "**P95 Latency (s)**",
    ]
    old2 = [
        [0.311, 0.377, 0.374],
        [0.311, 0.378, 0.378],
        [0.387, 0.520, 0.427],
        [0.567, 0.733, 0.611],
        [1.339, 1.622, 1.339],
        [0.189, 0.264, 0.294],
        [0.390, 0.510, 0.506],
        [16.141, 3.544, 4.194],
        [46.743, 8.727, 30.167],
    ]
    new2 = [
        [0.619, 0.750, 0.754],
        [0.422, 0.556, 0.489],
        [0.267, 0.467, 0.453],
        [0.367, 0.650, 0.633],
        [0.467, 1.133, 1.044],
        [0.419, 0.376, 0.491],
        [0.459, 0.517, 0.654],
        [0.559, 2.208, 2.270],
        [0.889, 5.878, 5.294],
    ]
    metrics2 = {
        "**MRR**": "mrr",
        "**MAP@3**": "map_3",
        "**MAP@5**": "map_5",
        "**MAR@5**": "mar_5",
        "**MAR@10**": "mar_10",
        "**MnDCG@5**": "mndcg_5",
        "**MnDCG@10**": "mndcg_10",
        "**Avg Latency (s)**": "avg_latency_seconds",
        "**P95 Latency (s)**": "p95_latency_seconds",
    }
    claims = power_table_claims(
        test2,
        dict(zip(labels2, old2, strict=True)),
        dict(zip(labels2, new2, strict=True)),
        metrics2,
    )

    test3 = "docs/tests/P.O.W.E.R.2.0.3-TEST-3.md"
    labels3 = [
        "**MRR**",
        "**MAP@5**",
        "**MAR@5**",
        "**MAR@10**",
        "**MnDCG@5**",
        "**MnDCG@10**",
        "**Avg Latency**",
        "**P95 Latency**",
    ]
    old3 = [
        [0.107, 0.168, 0.196],
        [0.090, 0.200, 0.190],
        [0.142, 0.300, 0.287],
        [0.250, 0.483, 0.617],
        [0.065, 0.166, 0.126],
        [0.093, 0.234, 0.261],
        [0.56, 2.57, 2.43],
        [0.79, 5.43, 5.58],
    ]
    new3 = [
        [0.204, 0.340, 0.385],
        [0.080, 0.210, 0.230],
        [0.138, 0.312, 0.358],
        [0.154, 0.554, 0.604],
        [0.082, 0.254, 0.256],
        [0.091, 0.326, 0.343],
        [0.56, 2.28, 2.49],
        [0.85, 5.49, 5.48],
    ]
    metrics3 = {
        **metrics2,
        "**Avg Latency**": "avg_latency_seconds",
        "**P95 Latency**": "p95_latency_seconds",
    }
    claims.extend(
        power_table_claims(
            test3,
            dict(zip(labels3, old3, strict=True)),
            dict(zip(labels3, new3, strict=True)),
            metrics3,
        )
    )
    language_labels = ["🇺🇦 UA→UA", "🇬🇧 EN→UA", "🇺🇦 UA→EN"]
    old_language = [[0.146, 0.250, 0.302], [0.417, 0.667, 0.500], [0.000, 0.000, 0.000]]
    new_language = [[0.115, 0.344, 0.396], [0.375, 0.500, 0.625], [0.000, 0.208, 0.208]]
    claims.extend(
        power_table_claims(
            test3,
            dict(zip(language_labels, old_language, strict=True)),
            dict(zip(language_labels, new_language, strict=True)),
            {label: f"language_recall_{index + 1}" for index, label in enumerate(language_labels)},
        )
    )
    return claims


def main() -> int:
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    by_rank = {item["sample_rank"]: item for item in details}
    builders = {
        17: (
            "popoto-locomo-gold-blind-scoring",
            "same_dataset_and_retrieval_outputs_scored_with_gold_blind_ranking",
            popoto_claims,
        ),
        31: (
            "ddharmon-authoritative-metric-sync",
            "stale_documented_metrics_corrected_to_committed_authoritative_evidence",
            ddharmon_claims,
        ),
        37: (
            "lore-esbuild-ground-truth-correction",
            "same_system_rerun_after_benchmark_ground_truth_correction",
            lore_claims,
        ),
        69: (
            "sekiban-rss-log-correction",
            "same_runs_rss_values_corrected_against_frozen_logs",
            sekiban_claims,
        ),
        119: (
            "sestrav-feature-count-label-correction",
            "same_certified_model_numeric_configuration_label_corrected",
            sestrav_claims,
        ),
        159: (
            "power-path-parser-metric-correction",
            "same_search_outputs_recomputed_with_correct_path_only_parser",
            power_claims,
        ),
    }
    labels = []
    cases = []
    for rank in range(1, 251):
        item = by_rank[rank]
        eligible = rank in builders
        label: dict[str, Any] = {
            "rank": rank,
            "repository": item["repository"],
            "pull_request": item["pull_request"],
            "eligible": eligible,
            "reason": builders[rank][1]
            if eligible
            else "no_eligible_like_for_like_numeric_claim_pair",
        }
        if eligible:
            case_id, _, build_claims = builders[rank]
            label["case_id"] = case_id
            plan = next(
                case
                for case in json.loads((ROOT / "source_plan.json").read_text())["cases"]
                if case["rank"] == rank
            )
            claims = build_claims()
            assert claims
            cases.append(
                {
                    "id": case_id,
                    "repository": item["repository"],
                    "pull_request": item["pull_request"],
                    "parent_commit": item["merge_parent_sha"],
                    "merge_commit": item["merge_commit_sha"],
                    "files": plan["files"],
                    "claims": claims,
                }
            )
        labels.append(label)
    label_payload = {
        "schema_version": "reprocheck.upstream-discovery-labels.v2",
        "eligibility_blinded_to_parser_output": True,
        "sample_size": len(labels),
        "labels": labels,
        "scientific_boundary": (
            "All 250 decisions were made from frozen GitHub metadata, merge-parent/merge diffs, "
            "and immutable source pairs without importing or executing ReproCheck. Repeated "
            "narrative and derived restatements were collapsed to each case's primary corrected "
            "claim surface."
        ),
    }
    case_payload = {
        "schema_version": "reprocheck.upstream-discovery-cases.v2",
        "evaluator_commit": EVALUATOR_COMMIT,
        "cases": cases,
    }
    (ROOT / "labels.json").write_text(
        json.dumps(label_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "cases.json").write_text(
        json.dumps(case_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"PASS: labeled {len(labels)} PRs; froze {len(cases)} eligible cases and "
        f"{sum(len(case['claims']) for case in cases)} primary claims"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
