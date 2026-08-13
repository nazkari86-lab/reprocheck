from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


RESULT_REFRESH_RANKS = {
    4,
    11,
    12,
    13,
    21,
    32,
    36,
    38,
    40,
    41,
    43,
    44,
    45,
    46,
    47,
    48,
    50,
    51,
    52,
    55,
    57,
    59,
    60,
    77,
    80,
    82,
    89,
    98,
    129,
    139,
    143,
    144,
}
NEW_RESULT_RANKS = {2, 8, 26, 31, 33, 35, 42, 49, 53, 54, 56, 58}
REMOVAL_WITHOUT_REPLACEMENT_RANKS = {10, 37, 39, 85, 89, 122}
NON_NUMERIC_CORRECTION_RANKS = {91, 95, 96, 101, 104, 111, 113, 116}

SPECIAL_REASONS = {
    1: "dashboard_visibility_fix_without_corrected_claim_pair",
    3: "metric_storage_fix_without_corrected_published_claim_pair",
    6: "benchmark_harness_reliability_fix_without_claim_pair",
    9: "benchmark_calculation_code_fix_without_published_claim_pair",
    14: "job_submission_documentation_without_result_correction",
    15: "review_packaging_feature_without_result_correction",
    18: "benchmark_recording_code_fix_without_published_claim_pair",
    20: "benchmark_row_deduplication_without_published_claim_pair",
    22: "benchmark_integrity_code_changes_without_immutable_old_new_claim_pair",
    25: "publication_pipeline_fix_without_corrected_numeric_pair",
    27: "branch_metadata_fix_without_numeric_result_correction",
    28: "first_valid_results_added_after_harness_bug_fix_without_prior_valid_pair",
    30: "implementation_change_without_corrected_report_claim",
    34: "old_and_new_numbers_measure_different_store_implementations",
    38: "new_real_s3_measurement_after_implementation_fix",
    67: "comparison_set_expanded_from_six_to_eight_systems",
    69: "stale_contract_recovery_feature_not_numeric_claim_correction",
    76: "benchmark_ticket_lifecycle_fix_not_numeric_claim_correction",
    87: "stale_state_rejection_fix_without_corrected_result_pair",
    97: "implementation_optimization_and_baseline_fix_without_published_pair",
    105: "mathematical_notebook_correction_not_benchmark_result_claim",
    107: "benchmark_dependency_import_fix_without_result_pair",
    112: "benchmark_argument_validation_without_result_pair",
    118: "performance_implementation_change_without_corrected_claim_pair",
    119: "schedule_optimization_without_corrected_published_pair",
    121: "codegen_correctness_fix_not_benchmark_claim_correction",
    123: "ci_threshold_policy_change_without_result_correction",
    124: "integration_test_setup_fix_without_result_correction",
    125: "evaluation_scorer_behavior_change_without_published_result_pair",
    128: "query_correctness_fix_not_benchmark_claim_correction",
    132: "benchmark_label_aggregation_fix_without_published_numeric_pair",
    135: "evaluation_assembly_and_sorting_fix_without_published_pair",
    138: "numerical_contract_repair_without_same_setting_result_pair",
    145: "new_regression_benchmark_without_prior_numeric_claim",
    148: "database_correctness_bug_not_benchmark_result_claim",
}


def reason_for(rank: int) -> str:
    if rank in SPECIAL_REASONS:
        return SPECIAL_REASONS[rank]
    if rank in RESULT_REFRESH_RANKS:
        return "result_refresh_after_code_data_version_or_configuration_change"
    if rank in NEW_RESULT_RANKS:
        return "new_benchmark_claims_without_preexisting_numeric_pair"
    if rank in REMOVAL_WITHOUT_REPLACEMENT_RANKS:
        return "incorrect_or_stale_claim_removed_without_corrected_numeric_value"
    if rank in NON_NUMERIC_CORRECTION_RANKS:
        return "benchmark_related_typo_or_label_fix_not_numeric_result_claim"
    return "no_corrected_preexisting_human_readable_numeric_claim_pair"


def metric_claims() -> list[dict[str, object]]:
    before = {
        "map@1": 0.142,
        "map@10": 0.216,
        "map@3": 0.159,
        "map@4": 0.170,
        "map@5": 0.182,
        "mrr@1": 0.142,
        "mrr@10": 0.249,
        "mrr@3": 0.192,
        "mrr@4": 0.204,
        "mrr@5": 0.217,
        "ndcg@1": 0.142,
        "ndcg@10": 0.329,
        "ndcg@3": 0.209,
        "ndcg@4": 0.229,
        "ndcg@5": 0.254,
        "precision@1": 0.142,
        "precision@10": 0.072,
        "precision@3": 0.090,
        "precision@4": 0.082,
        "precision@5": 0.080,
        "recall@1": 0.114,
        "recall@10": 0.548,
        "recall@3": 0.212,
        "recall@4": 0.255,
        "recall@5": 0.312,
        "u_ndcg@2": 0.088,
        "u_ndcg@4": 0.120,
        "u_ndcg@6": 0.155,
        "u_recall@2": 0.169,
        "u_recall@4": 0.255,
        "u_recall@6": 0.357,
    }
    after = {
        "map@1": 0.151,
        "map@10": 0.236,
        "map@3": 0.175,
        "map@4": 0.187,
        "map@5": 0.199,
        "mrr@1": 0.151,
        "mrr@10": 0.265,
        "mrr@3": 0.206,
        "mrr@4": 0.221,
        "mrr@5": 0.233,
        "ndcg@1": 0.151,
        "ndcg@10": 0.352,
        "ndcg@3": 0.225,
        "ndcg@4": 0.250,
        "ndcg@5": 0.273,
        "precision@1": 0.151,
        "precision@10": 0.077,
        "precision@3": 0.100,
        "precision@4": 0.092,
        "precision@5": 0.087,
        "recall@1": 0.123,
        "recall@10": 0.589,
        "recall@3": 0.238,
        "recall@4": 0.285,
        "recall@5": 0.340,
        "u_ndcg@2": 0.095,
        "u_ndcg@4": 0.133,
        "u_ndcg@6": 0.168,
        "u_recall@2": 0.184,
        "u_recall@4": 0.285,
        "u_recall@6": 0.386,
    }
    constant = {
        "map@1": 0.378,
        "map@10": 0.478,
        "map@3": 0.426,
        "map@4": 0.443,
        "map@5": 0.453,
        "mrr@1": 0.378,
        "mrr@10": 0.514,
        "mrr@3": 0.474,
        "mrr@4": 0.488,
        "mrr@5": 0.496,
        "ndcg@1": 0.378,
        "ndcg@10": 0.585,
        "ndcg@3": 0.505,
        "ndcg@4": 0.528,
        "ndcg@5": 0.545,
        "precision@1": 0.378,
        "precision@10": 0.101,
        "precision@3": 0.215,
        "precision@4": 0.184,
        "precision@5": 0.159,
        "recall@1": 0.327,
        "recall@10": 0.785,
        "recall@3": 0.535,
        "recall@4": 0.595,
        "recall@5": 0.637,
        "u_ndcg@2": 0.227,
        "u_ndcg@4": 0.284,
        "u_ndcg@6": 0.314,
        "u_recall@2": 0.444,
        "u_recall@4": 0.595,
        "u_recall@6": 0.684,
    }
    claims = []
    for name in before:
        metric = name.replace("@", "_")
        claims.append(
            {
                "file": "benchmarks/esmemeval/results.md",
                "before_snippet": f"| {name} | {constant[name]:.3f} | {before[name]:.3f} |",
                "after_snippet": f"| {name} | {constant[name]:.3f} | {after[name]:.3f} |",
                "metric": metric,
                "before_value": before[name],
                "after_value": after[name],
            }
        )
    return claims


def main() -> int:
    details = json.loads((ROOT / "details.json").read_text(encoding="utf-8"))["details"]
    by_rank = {item["sample_rank"]: item for item in details}
    assert set(by_rank) == set(range(1, 151))
    eligible = {
        24: (
            "emotional-memory-esmemeval-correction",
            "same_intended_x2_evaluation_corrected_after_harness_bug",
        ),
        106: (
            "llmcompare-opus5-swebench",
            "same_model_and_swebench_metric_catalog_value_corrected",
        ),
    }
    labels = []
    for rank in range(1, 151):
        item = by_rank[rank]
        label: dict[str, object] = {
            "rank": rank,
            "repository": item["repository"],
            "pull_request": item["pull_request"],
            "eligible": rank in eligible,
            "reason": eligible[rank][1] if rank in eligible else reason_for(rank),
        }
        if rank in eligible:
            label["case_id"] = eligible[rank][0]
        labels.append(label)
    label_payload = {
        "schema_version": "reprocheck.upstream-discovery-labels.v1",
        "eligibility_blinded_to_parser_output": True,
        "sample_size": 150,
        "labels": labels,
        "scientific_boundary": (
            "Eligibility was assigned from immutable GitHub metadata and diffs without "
            "running either ReproCheck 0.19.0 or the development parser."
        ),
    }
    case24 = by_rank[24]
    case106 = by_rank[106]
    cases = {
        "schema_version": "reprocheck.upstream-discovery-cases.v1",
        "evaluator_commit": "7e5a6c087fc6f5e5df14ccde1c8436049c39c5b7",
        "cases": [
            {
                "id": "emotional-memory-esmemeval-correction",
                "repository": case24["repository"],
                "pull_request": case24["pull_request"],
                "parent_commit": case24["merge_parent_sha"],
                "merge_commit": case24["merge_commit_sha"],
                "files": ["benchmarks/esmemeval/results.md"],
                "claims": metric_claims(),
            },
            {
                "id": "llmcompare-opus5-swebench",
                "repository": case106["repository"],
                "pull_request": case106["pull_request"],
                "parent_commit": case106["merge_parent_sha"],
                "merge_commit": case106["merge_commit_sha"],
                "files": ["data/models.json"],
                "claims": [
                    {
                        "file": "data/models.json",
                        "before_snippet": '"swebench": 80,',
                        "after_snippet": '"swebench": 96,',
                        "metric": "swebench",
                        "before_value": 80.0,
                        "after_value": 96.0,
                    }
                ],
            },
        ],
    }
    (ROOT / "labels.json").write_text(
        json.dumps(label_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: labeled 150 sampled PRs; froze 2 eligible cases and 32 claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
