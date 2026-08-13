import pytest

from reprocheck import extract_claims as public_extract_claims
from reprocheck import extract_table_claims as public_extract_table_claims
from reprocheck.claims import check_claims, extract_claims, extract_table_claims
from reprocheck.metric_names import metric_family


def test_extracts_russian_and_english_metrics():
    claims = extract_claims("Точность: 94%\nF1 = 0,91\nprecision score: 88%")
    assert [(claim.metric, round(claim.value, 12)) for claim in claims] == [
        ("accuracy", 0.94),
        ("f1", 0.91),
        ("precision", 0.88),
    ]


def test_claim_extractors_are_part_of_the_public_package_api():
    assert public_extract_claims is extract_claims
    assert public_extract_table_claims is extract_table_claims


def test_unknown_public_attribute_fails_normally():
    import reprocheck

    try:
        getattr(reprocheck, "missing_public_api")
    except AttributeError as error:
        assert "missing_public_api" in str(error)
    else:
        raise AssertionError("unknown package attribute must raise AttributeError")


def test_checks_claims_with_tolerance():
    claims = extract_claims("accuracy = 90%\nrecall: 0.7")
    checks = check_claims(claims, {"accuracy": 0.902}, tolerance=0.005)
    assert checks[0].status == "supported"
    assert checks[1].status == "no_evidence"

    recomputed = check_claims(
        claims[:1],
        {"accuracy": 0.902},
        tolerance=0.005,
        evidence_levels={"accuracy": "recomputed"},
    )
    assert recomputed[0].status == "verified"


def test_extracts_detection_map_claims():
    claims = extract_claims("mAP50-95: 0.41, mAP50 = 62%, mAP75 0.38")
    assert [(claim.metric, round(claim.value, 12)) for claim in claims] == [
        ("map50_95", 0.41),
        ("map50", 0.62),
        ("map75", 0.38),
    ]


def test_does_not_treat_nms_iou_as_quality_claim():
    claims = extract_claims("mAP50: 0.9; NMS IoU=0.7")
    assert [(claim.metric, claim.value) for claim in claims] == [("map50", 0.9)]


def test_extracts_negative_and_scientific_regression_values():
    claims = extract_claims("R2: -2.5\nRMSE = 1.2e-3")
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("r2", -2.5),
        ("rmse", 0.0012),
    ]


def test_extracts_probability_metric_claims_with_correct_display_units():
    claims = extract_claims("AUROC: 91%\nAUPRC: 0.87\nlog loss: 0.23\nBrier score: 0.08")
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("auroc", 0.91),
        ("auprc", 0.87),
        ("log_loss", 0.23),
        ("brier_score", 0.08),
    ]
    checks = check_claims(claims, {}, tolerance=0.01)
    assert [check.display_kind for check in checks] == [
        "percentage",
        "percentage",
        "scalar",
        "percentage",
    ]


def test_extracts_metrics_from_markdown_tables_and_html_headers():
    text = """| Model | mAP<sup>val<br>50-95</sup> | rmse<sup>NYU</sup> | acc<br><sup>top1</sup> | acc<br><sup>top5</sup> |
| --- | ---: | ---: | ---: | ---: |
| YOLO26n | 40.9 | 0.414 | 71.4 | 90.1 |
| YOLO26s | 48.6 | 0.399 | 76.0 | 92.9 |
"""
    claims = extract_claims(text)
    assert [(claim.metric, round(claim.value, 12), claim.line) for claim in claims] == [
        ("map50_95", 0.409, 3),
        ("rmse", 0.414, 3),
        ("top1_accuracy", 0.714, 3),
        ("top5_accuracy", 0.901, 3),
        ("map50_95", 0.486, 4),
        ("rmse", 0.399, 4),
        ("top1_accuracy", 0.76, 4),
        ("top5_accuracy", 0.929, 4),
    ]
    assert claims[0].context == {"model": "YOLO26n"}
    assert claims[-1].context == {"model": "YOLO26s"}


def test_structured_claim_context_scopes_selected_evidence():
    claims = extract_table_claims(
        """| Model | Accuracy |
| --- | ---: |
| baseline | 81% |
| proposed | 92% |
"""
    )

    checks = check_claims(
        claims,
        {"accuracy": 0.92},
        tolerance=0.001,
        evidence_contexts={"accuracy": {"model": "proposed"}},
    )

    assert claims[0].context == {"model": "baseline"}
    assert claims[1].context == {"model": "proposed"}
    assert [check.status for check in checks] == ["no_evidence", "supported"]


def test_extracts_standalone_topk_table_headers_but_not_topk_error():
    text = """| Model | top1 | top5 | Top-1 (%) | Top-5 (%) | Top-1 error | Top-5 err |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| classifier | 81.2 | 95.4 | 82.1 | 96.0 | 17.9 | 4.0 |
"""
    assert [(claim.metric, round(claim.value, 12)) for claim in extract_table_claims(text)] == [
        ("top1_accuracy", 0.812),
        ("top5_accuracy", 0.954),
        ("top1_accuracy", 0.821),
        ("top5_accuracy", 0.96),
    ]


def test_extracts_openmmlab_two_dash_table_separators():
    text = """| model | top1 acc | top5 acc |
| :--: | :--: | :--: |
| SlowOnly | 72.97 | 90.88 |
"""
    assert [(claim.metric, round(claim.value, 12)) for claim in extract_claims(text)] == [
        ("top1_accuracy", 0.7297),
        ("top5_accuracy", 0.9088),
    ]


def test_extracts_coco_summary_metrics_without_misreading_iou_parameters():
    text = """ Average Precision  (AP) @[ IoU=0.50:0.95 | area=   all | maxDets=100 ] = 0.352
 Average Precision  (AP) @[ IoU=0.50      | area=   all | maxDets=100 ] = 0.681
 Average Precision  (AP) @[ IoU=0.75      | area=   all | maxDets=100 ] = 0.292
 Average Precision  (AP) @[ IoU=0.50:0.95 | area= small | maxDets=100 ] = 0.168
 Average Recall     (AR) @[ IoU=0.50:0.95 | area=   all | maxDets=100 ] = 0.501
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("map50_95", 0.352),
        ("map50", 0.681),
        ("map75", 0.292),
        ("ar", 0.501),
    ]


def test_extracts_real_benchmark_duration_claims_and_normalizes_units():
    text = """Processing time: 8 seconds
The benchmark measured HyperIndex completing the test in 1 minute, 143x faster.
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("runtime_seconds", 8.0),
        ("runtime_seconds", 60.0),
        ("speedup", 143.0),
    ]


def test_extracts_markdown_wrapped_metrics_without_losing_raw_text():
    claims = extract_claims("Precision: **95.7%**")
    assert [(claim.metric, round(claim.value, 6), claim.raw_text) for claim in claims] == [
        ("precision", 0.957, "Precision: **95.7%**")
    ]


def test_extracts_postfix_speedup_and_speedup_range():
    claims = extract_claims("35% speedup\nTurboQuant beats FAISS by 16–24%")
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("speedup", 0.35),
        ("speedup_range_low", 0.16),
        ("speedup_range_high", 0.24),
    ]


def test_extracts_row_labeled_rates_and_ratios():
    text = """| | compiled replay | agent |
|---|---|---|
| success rate | 95% (19/20) | 100% (20/20) |
| recall | 1 of 2 | 2 of 2 |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("success_rate", 0.95, {"system": "compiled replay"}),
        ("success_rate", 1.0, {"system": "agent"}),
        ("recall", 0.5, {"system": "compiled replay"}),
        ("recall", 1.0, {"system": "agent"}),
    ]


def test_extracts_latency_score_alias_and_provider_context():
    text = """| Provider | Avg latency | Latency score |
|---|---|---|
| remote | 2.4s | 2.8s |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("avg_latency_seconds", 2.4, {"system": "remote"}),
        ("latency_score_seconds", 2.4, {"system": "remote"}),
        ("latency_score_seconds", 2.8, {"system": "remote"}),
    ]


def test_extracts_memory_comparison_and_normalizes_units():
    claims = extract_claims("It cuts resident memory to about 130 MB from about 1 GB.")
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("memory_mb", 130.0, {"system": "native UI"}),
        ("memory_mb", 1024.0, {"system": "webview UI"}),
    ]


def test_extracts_scaled_throughput_with_system_context():
    text = """| Serialization Type | Throughput (ops/s) |
|---|---|
| JSON | 12.5K |
| Binary | 1.2M |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("throughput_ops_per_second", 12_500.0, {"system": "JSON"}),
        ("throughput_ops_per_second", 1_200_000.0, {"system": "Binary"}),
    ]


def test_extracts_embedded_duration_from_comparison_table():
    text = """| Solver | baseline | SSIK |
|---|---|---|
| search (cold) | failed | 18.2 ms (compiled) |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        (
            "runtime_seconds",
            0.0182,
            {"system": "search", "implementation": "ssik"},
        )
    ]


def test_extracts_numeric_tsv_columns_with_row_context():
    text = "word\twrong_coverage\nexample\t0.42\nother\t0.55\n"
    claims = extract_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("wrong_coverage", 0.42, {"word": "example"}),
        ("wrong_coverage", 0.55, {"word": "other"}),
    ]


def test_extracts_both_values_from_fitness_score_comparison():
    claims = extract_claims("fitness score improved from 0.426 to 0.553")
    assert [(c.metric, c.value) for c in claims] == [("score", 0.426), ("score", 0.553)]


def test_extracts_scores_from_old_new_benchmark_table():
    text = """| Benchmark | Old | New | Tokens |
|---|---|---|---|
| LoCoMo | 71.4 | **92.5** | 7.0K |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("score", 71.4, {"system": "LoCoMo"}),
        ("score", 92.5, {"system": "LoCoMo"}),
    ]


def test_extracts_mean_latency_table_header_in_seconds():
    text = """| Precision | Mean Latency | Accuracy (mAP50) |
|---|---|---|
| FP16 | 51.82 ms | 0.7791 |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value) for c in claims] == [
        ("avg_latency_seconds", 0.05182),
        ("latency_score_seconds", 0.05182),
        ("map50", 0.7791),
    ]


def test_extracts_total_and_language_test_counts():
    claims = extract_claims("~19,170 tests: 5,954 TypeScript + 13,216 Python")
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("test_count", 19170.0, {"scope": "total"}),
        ("test_count", 5954.0, {"scope": "TypeScript"}),
        ("test_count", 13216.0, {"scope": "Python"}),
    ]


def test_test_count_does_not_treat_version_tail_as_count():
    claims = extract_claims("PyTorch 2.12.0, Python 3.14.5; max_det=300, seed=0.")

    assert not [claim for claim in claims if claim.metric == "test_count"]


def test_extracts_wrapped_total_passed_and_multilingual_test_counts():
    text = """Measured baseline: 4,321 passing unit
tests in 88 files.
All tests run with JUnit. There are 57 in total.
pytest: 612 passed, 3 skipped.
현재 144개 자동 테스트를 실행합니다.
"""
    assert [(c.metric, c.value, c.context) for c in extract_claims(text)] == [
        ("test_count", 4321.0, {"scope": "total"}),
        ("test_count", 57.0, {"scope": "total"}),
        ("test_count", 612.0, {"scope": "total"}),
        ("test_count", 144.0, {"scope": "total"}),
    ]


def test_extracts_unit_test_qualifier_and_vram_peak():
    claims = extract_claims(
        "The suite has 206 unit tests. Peak of ~11.5 GB GPU VRAM during model loading."
    )
    assert [(c.metric, c.value) for c in claims] == [
        ("test_count", 206.0),
        ("memory_mb", 11776.0),
    ]


def test_extracts_abbreviated_ranked_headers_and_duration_speed_header():
    text = """| Adapter | P@5 | R@5 | Recall speed |
|---|---:|---:|---:|
| hybrid | 0.31 | 0.84 | ~42ms |
"""
    assert [(c.metric, c.value) for c in extract_table_claims(text)] == [
        ("precision_5", 0.31),
        ("recall_5", 0.84),
        ("runtime_seconds", 0.042),
    ]


def test_extracts_machine_metric_and_test_count_rows():
    text = """| Metric | Value |
|---|---:|
| Hub ratio (`hub_pct`) | 8.4% |
| Dead code (`dead_code_pct`) | 3.1% |
| Tests | 712 |
"""
    assert [(c.metric, c.value) for c in extract_table_claims(text)] == [
        ("hub_pct", 0.084),
        ("dead_code_pct", 0.031),
        ("test_count", 712.0),
    ]


def test_extracts_artifact_size_comparison_without_calling_it_memory():
    claims = extract_claims("Smaller hashfile (**39.7 vs 70.9 MiB** on the tree)")
    assert [(c.metric, c.value) for c in claims] == [
        ("artifact_size_mb", 39.7),
        ("artifact_size_mb", 70.9),
    ]


def test_extracts_counts_and_artifact_sizes_inside_table_cells():
    text = """| Evidence | Details |
|---|---|
| Verification | 19,170 tests: 13,216 Python |
| Storage | Smaller hashfile (39.7 vs 70.9 MiB on the tree) |
"""
    claims = extract_table_claims(text)
    assert [(c.metric, c.value, c.context) for c in claims] == [
        ("test_count", 19170.0, {"scope": "total"}),
        ("test_count", 13216.0, {"scope": "Python"}),
        ("artifact_size_mb", 39.7, {"system": "reported artifact"}),
        ("artifact_size_mb", 70.9, {"system": "baseline artifact"}),
    ]


def test_normalizes_subsecond_prose_durations_and_rejects_invalid_time_cells():
    text = """Processing time: 250 milliseconds
Processing time: 40 us
| Model | Runtime |
| --- | ---: |
| broken | unavailable |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("runtime_seconds", 0.25),
        ("runtime_seconds", 0.00004),
    ]


def test_extracts_scoped_benchmark_times_and_speedup_from_tables():
    text = """| Model | Sign Time | Verify Time | Speedup |
| --- | ---: | ---: | ---: |
| small | 1.4s | 0.7s | 3.94x |
| large | 1m1s | 57s | 1.10x |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("sign_time_seconds", 1.4),
        ("verify_time_seconds", 0.7),
        ("speedup", 3.94),
        ("sign_time_seconds", 61.0),
        ("verify_time_seconds", 57.0),
        ("speedup", 1.1),
    ]


def test_extracts_cached_and_uncached_sync_times_without_unit_confusion():
    text = """| Benchmarks | Sync time (w/o cache) | Sync time (w/ cache) |
| --- | ---: | ---: |
| Ponder | 31.1s | 18.2s |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("sync_time_without_cache_seconds", 31.1),
        ("sync_time_with_cache_seconds", 18.2),
    ]


def test_extracts_compound_metric_table_cells():
    text = """| Method | AUROC/AUPRC/Acc |
| --- | --- |
| Deterministic | 0.972/0.782/0.922 |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("auroc", 0.972),
        ("auprc", 0.782),
        ("accuracy", 0.922),
    ]


def test_extracts_waymo_level_scoped_metrics():
    text = """| Model | mAP@L1 | mAPH@L1 | mAP@L2 | mAPH@L2 |
| --- | ---: | ---: | ---: | ---: |
| SECOND | 65.3 | 61.7 | 58.9 | 55.7 |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("map_l1", 0.653),
        ("maph_l1", 0.617),
        ("map_l2", 0.589),
        ("maph_l2", 0.557),
    ]


def test_extracts_standalone_topk_headers_from_html():
    text = """<table>
<tr><th>Model</th><th>top1</th><th>Top-5 (%)</th></tr>
<tr><td>classifier</td><td>80</td><td>95</td></tr>
</table>"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [
        ("top1_accuracy", 0.8),
        ("top5_accuracy", 0.95),
    ]


def test_extracts_row_labeled_retrieval_metrics_from_markdown_tables():
    text = """| Metric | baseline | proposed |
|---|---|---|
| map@1 | 0.378 | 0.151 |
| mrr@10 | 0.514 | 0.265 |
| ndcg@4 | 0.528 | 0.250 |
| precision@5 | 0.159 | 0.087 |
| recall@10 | 0.785 | 0.589 |
| u_ndcg@4 | 0.284 | 0.133 |
| u_recall@6 | 0.684 | 0.386 |
"""
    claims = extract_table_claims(text)
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("map_1", 0.378),
        ("map_1", 0.151),
        ("mrr_10", 0.514),
        ("mrr_10", 0.265),
        ("ndcg_4", 0.528),
        ("ndcg_4", 0.250),
        ("precision_5", 0.159),
        ("precision_5", 0.087),
        ("recall_10", 0.785),
        ("recall_10", 0.589),
        ("u_ndcg_4", 0.284),
        ("u_ndcg_4", 0.133),
        ("u_recall_6", 0.684),
        ("u_recall_6", 0.386),
    ]
    assert claims[0].context == {"system": "baseline"}
    assert claims[1].context == {"system": "proposed"}


def test_row_labeled_metrics_require_explicit_metric_header_and_known_family():
    text = """| Name | baseline | proposed |
|---|---|---|
| ndcg@4 | 0.2 | 0.3 |

| Metric | baseline | proposed |
|---|---|---|
| learning_rate@4 | 0.2 | 0.3 |
"""
    assert extract_table_claims(text) == []


def test_extracts_multilingual_row_labeled_metrics_with_system_context():
    text = """| Метрика | FTS (BM25) | Vector | Hybrid | Delta |
|---|---:|---:|---:|---:|
| MRR | 0.619 | 0.750 | 0.754 | +0.135 |
| MAR@10 | 0.467 | 1.133 | 1.044 | +0.577 |
| Avg Latency (s) | 0.559 | 2.208 | 2.270 | +1.711 |
"""
    claims = extract_table_claims(text)
    assert ("mrr", 0.619, {"system": "FTS (BM25)"}) in [
        (claim.metric, claim.value, claim.context) for claim in claims
    ]
    assert ("mar_10", 1.133, {"system": "Vector"}) in [
        (claim.metric, claim.value, claim.context) for claim in claims
    ]
    assert ("avg_latency_seconds", 2.27, {"system": "Hybrid"}) in [
        (claim.metric, claim.value, claim.context) for claim in claims
    ]


def test_extracts_rate_and_efficiency_rows_without_losing_sign_or_thousands():
    text = """| Metric | Control | Lore-enabled | Delta |
|---|---:|---:|---:|
| Fail rate | 3.6% | 1.0% | -2.6pp |
| Mean tokens | 8,952 | 6,182 | -2,771 (−30.9%) |
"""
    claims = extract_table_claims(text)
    observed = [(claim.metric, claim.value, claim.context) for claim in claims]
    fail_delta = next(
        value
        for metric, value, context in observed
        if metric == "fail_rate" and context == {"system": "Delta"}
    )
    assert fail_delta == pytest.approx(-0.026)
    assert ("mean_tokens", 8952.0, {"system": "Control"}) in observed
    assert ("mean_tokens", -2771.0, {"system": "Delta"}) in observed
    assert ("mean_tokens_delta_percent", -30.9, {"system": "Delta"}) in observed


def test_extracts_ranked_prose_arrow_target_and_separability():
    claims = extract_claims(
        "Hybrid improves recall@5 0.447 → 0.632. Embedding separability Δ0.611."
    )
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("recall_5", 0.447),
        ("recall_5", 0.632),
        ("separability_delta", 0.611),
    ]


def test_extracts_transposed_metric_table_from_nearby_heading():
    text = """### MAR@5 by scenario

| Scenario | FTS | Vector | Hybrid |
|---|---:|---:|---:|
| UA→EN | 0.000 | 0.208 | 0.208 |
"""
    claims = extract_table_claims(text)
    assert [(claim.metric, claim.value, claim.context) for claim in claims] == [
        ("mar_5", 0.0, {"scenario": "UA→EN", "system": "FTS"}),
        ("mar_5", 0.208, {"scenario": "UA→EN", "system": "Vector"}),
        ("mar_5", 0.208, {"scenario": "UA→EN", "system": "Hybrid"}),
    ]


def test_extracts_multilevel_dataset_metric_table_with_percent_headers():
    text = """| Method | WikiTQ-ST | SSTQA | SSTQA |
|---|---:|---:|---:|
| | Accuracy (%) | Accuracy (%) | ROUGE-L (%) |
| baseline | 38.89 | 24.00 | 23.87 |
"""
    claims = extract_table_claims(text)
    assert [c.metric for c in claims] == ["wikitq_accuracy", "sstqa_accuracy", "sstqa_rouge_l"]
    assert [c.value for c in claims] == pytest.approx([0.3889, 0.24, 0.2387])


def test_extracts_units_declared_in_benchmark_table_headers():
    text = """| Model | Tokens/s/GPU | TFLOP/s/GPU | MFU | HBM/GPU |
|---|---:|---:|---:|---:|
| model-a | 9,731 | 57.6 | 22.5% | 22.2 GB |
"""
    assert [(c.metric, c.value) for c in extract_table_claims(text)] == [
        ("tokens_per_second_gpu", 9731.0),
        ("tflops_per_second_gpu", 57.6),
        ("mfu", 0.225),
        ("memory_mb", 22732.8),
    ]


def test_extracts_wrk_console_summary_as_structured_metrics():
    text = """    Latency 0.94ms 2.47ms 206.34ms 99.64%
    Req/Sec 19.59k 1.53k 22.74k 75.00%
780113 requests in 10.03s, 826.55MB read
Requests/sec: 77770.10
"""
    claims = {(c.line, c.metric, c.value) for c in extract_claims(text)}
    assert (1, "avg_latency_seconds", 0.00094) in claims
    assert (1, "max_latency_seconds", 0.20634) in claims
    assert (2, "requests_per_second", 19590.0) in claims
    assert (3, "request_count", 780113.0) in claims
    assert (3, "data_read_mb", 826.55) in claims
    assert (4, "requests_per_second", 77770.10) in claims


def test_extracts_general_improvement_and_memory_prose():
    text = (
        "The model requires only 3.2MB and improves the F1 score by 50.5%, "
        "the Aff-F1 score by 7.8%, and the AUC by 10.0%.\n"
        "It achieves 68.5% of optimal throughput and a 1.91x throughput boost.\n"
        "Fragmented Memory: 0.14 GB (0.57%)\n"
    )
    claims = {(c.metric, c.value) for c in extract_claims(text)}
    assert ("artifact_size_mb", 3.2) in claims
    assert ("f1_improvement", 0.505) in claims
    assert ("aff_f1_improvement", 0.078) in claims
    assert ("auc_improvement", 0.1) in claims
    assert ("optimal_throughput_ratio", 0.685) in claims
    assert ("speedup", 1.91) in claims
    assert ("memory_mb", 143.36) in claims
    assert any(
        metric == "fragmentation_ratio" and value == pytest.approx(0.0057)
        for metric, value in claims
    )


def test_extracts_general_result_variants_without_project_specific_rules():
    text = """The system retains 50% to 75% of optimal throughput.
BLEU improvement of 7%, while ROUGE-L decline of 8% and a decline of 9% in F1 scores.
The detector reached 95% image-level AUROC and 88% PRO.
Best Dice: 75%; precision is approximately (~92%).
The change decreased allocator fragmentation to <= 2%.
The maximum batch size is 32; the next run gets OOM with 64.
The patch increased the supported batch size by 4x.
120 assertions in 30 test cases.
processed 1000 tokens with 80 phrases; found: 70 phrases; correct: 65
FB1: 0.75 71
precision measurements were (91%) and (~93%).
mean lat.: 250 usec, rate sampling interval: 5 msec
BLEU and ROUGE-L have standard deviations of 1.2 and 2.3, respectively.
"""
    claims = [(claim.metric, claim.value) for claim in extract_claims(text)]
    expected = [
        ("optimal_throughput_ratio", 0.5),
        ("optimal_throughput_ratio", 0.75),
        ("bleu_improvement", 0.07),
        ("rouge_l_decline", 0.08),
        ("f1_decline", 0.09),
        ("auroc", 0.95),
        ("pro", 0.88),
        ("dice", 0.75),
        ("precision", 0.92),
        ("fragmentation_ratio", 0.02),
        ("max_batch_size", 32.0),
        ("oom_batch_size", 64.0),
        ("speedup", 4.0),
        ("assertion_count", 120.0),
        ("test_count", 30.0),
        ("processed_token_count", 1000.0),
        ("phrase_count", 80.0),
        ("found_phrase_count", 70.0),
        ("correct_phrase_count", 65.0),
        ("found_phrase_count", 71.0),
        ("avg_latency_seconds", 0.00025),
        ("sampling_interval_seconds", 0.005),
        ("bleu_stdev", 1.2),
        ("rouge_l_stdev", 2.3),
    ]
    for item in expected:
        assert any(
            metric == item[0] and value == pytest.approx(item[1]) for metric, value in claims
        )


def test_extracts_batch_size_from_command_only_after_explanatory_context():
    text = """The experiment determines the maximum batch size.
Run the probe with:
python scripts/probe.py model 48
"""
    assert ("max_batch_size", 48.0) in [
        (claim.metric, claim.value) for claim in extract_claims(text)
    ]


def test_extracts_header_duration_units_and_embedded_allocations():
    text = """| System | Avg latency (us) | Max latency (ms) | Runtime (s) | Artifact size (KB) |
|---|---:|---:|---:|---:|
| alpha | 250 | 7.5 | 2 | 64 |

| Benchmark | Go implementation |
|---|---:|
| parser speed | 12 ms, 128 B, 2 GC |
"""
    claims = [(claim.metric, claim.value) for claim in extract_table_claims(text)]
    expected = [
        ("avg_latency_seconds", 0.00025),
        ("max_latency_seconds", 0.0075),
        ("runtime_seconds", 2.0),
        ("artifact_size_mb", 0.0625),
        ("memory_bytes", 128.0),
        ("allocation_count", 2.0),
    ]
    for item in expected:
        assert any(
            metric == item[0] and value == pytest.approx(item[1]) for metric, value in claims
        )


def test_extracts_peak_rss_and_embedded_feature_count_with_context():
    text = """| Runtime | Peak RSS |
|---|---:|
| C# Native | ~1637.2 MB |

| tool | auc_roc |
|---|---:|
| SESTRAV RF (31-feat) | 0.7255 |
"""
    claims = extract_table_claims(text)
    observed = [(claim.metric, claim.value, claim.context) for claim in claims]
    assert ("peak_rss_mb", 1637.2, {"system": "C# Native"}) in observed
    assert (
        "feature_count",
        31.0,
        {"model": "SESTRAV RF (31-feat)"},
    ) in observed


def test_extracts_ranked_header_and_metric_text_embedded_in_table_cell():
    text = """| Model | Recall@5 | Notes |
|---|---:|---|
| hybrid | 67.4% | recall@5 0.447 → 0.674; separability Δ0.611 |
"""
    claims = extract_table_claims(text)
    observed = [(claim.metric, claim.value, claim.context) for claim in claims]
    assert ("recall_5", 0.674, {"model": "hybrid"}) in observed
    assert ("recall_5", 0.447, {}) in observed
    assert ("recall_5", 0.674, {}) in observed
    assert ("separability_delta", 0.611, {}) in observed


def test_row_labeled_delta_can_extract_first_number_from_annotated_cell():
    text = """| Metric | Baseline | Delta |
|---|---:|---:|
| Mean tokens | 1000 | down 250 tokens |
"""
    claims = extract_table_claims(text)
    assert ("mean_tokens", 250.0, {"system": "Delta"}) in [
        (claim.metric, claim.value, claim.context) for claim in claims
    ]


def test_transposed_table_without_nearby_metric_is_not_invented():
    text = """| Scenario | FTS | Vector |
|---|---:|---:|
| UA→EN | n/a | 0.208 |
"""
    assert extract_table_claims(text) == []


def test_extracts_swebench_structured_score_without_probability_rescaling():
    claims = extract_claims('{"scores": {"swebench": 96}}')
    assert [(claim.metric, claim.value) for claim in claims] == [("swebench", 96.0)]


def test_normalizes_unmarked_percentage_scale_for_bounded_metrics():
    claims = extract_claims("Accuracy: 95\nRMSE: 42.5")
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("accuracy", 0.95),
        ("rmse", 42.5),
    ]


def test_preserves_scoped_json_metric_ids_and_rejects_parameter_keys():
    claims = extract_claims(
        "val_mean_dice_tc: 85.59\nvalidation_accuracy: 94.5\niou_threshold: 0.5"
    )
    assert [(claim.metric, round(claim.value, 4)) for claim in claims] == [
        ("val_mean_dice_tc", 0.8559),
        ("validation_accuracy", 0.945),
    ]


def test_extracts_structured_metric_names_with_evaluation_suffixes():
    claims = extract_claims("mIoU(ms+flip): 53.58")
    assert [(claim.metric, round(claim.value, 12)) for claim in claims] == [
        ("miou_ms_flip", 0.5358)
    ]


def test_extracts_narrative_metric_phrasing():
    claims = extract_claims("The mean Dice score of 0.88; точность на уровне 94%.")
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("dice", 0.88),
        ("accuracy", 0.94),
    ]


def test_extracts_real_validator_methodology_counts():
    before = "Benchmarks run in single-node dev mode on a dedicated bare-metal host."
    after = "Benchmarks run two local validators in consensus on a dedicated host."

    assert [(claim.metric, claim.value) for claim in extract_claims(before)] == [
        ("validator_count", 1.0)
    ]
    assert [(claim.metric, claim.value) for claim in extract_claims(after)] == [
        ("validator_count", 2.0)
    ]
    assert [(claim.metric, claim.value) for claim in extract_claims("2 local validators")] == [
        ("validator_count", 2.0)
    ]


def test_extracts_real_json_measurement_keys_but_not_parameters():
    text = """{
  "spy_close": 754.95,
  "spy_return_pct": -0.765617,
  "inception_adjusted_close": 754.95,
  "return_pct": -0.765617,
  "threshold_pct": 20
}"""

    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("spy_close", 754.95),
        ("spy_return_pct", -0.765617),
        ("inception_adjusted_close", 754.95),
        ("return_pct", -0.765617),
    ]


def test_extracts_real_generic_scores_from_table_and_comparison_prose():
    text = """| Method | Score | Model |
| --- | ---: | --- |
| GEPA | 2.63598+ | gemini |

HELIX matched the best published result (2.635982 vs 2.63598+).
Target score >= 2.63598 to match the best published result.
"""

    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("score", 2.63598),
        ("score", 2.635982),
        ("score", 2.63598),
        ("score", 2.63598),
    ]


def test_generic_score_does_not_duplicate_named_metrics_or_plain_benchmark_numbers():
    text = """Brier score: 0.08
Precision score: 88%
The benchmark completed in 1 minute with seed 42.
"""

    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("brier_score", 0.08),
        ("precision", 0.88),
        ("runtime_seconds", 60.0),
    ]


def test_generic_structured_prediction_scores_are_not_report_metrics():
    text = "Segment: {'id': 0, 'label_id': 0, 'score': 0.946127}"

    assert extract_claims(text) == []


def test_extracts_map_variants_and_skips_non_numeric_table_cells():
    text = """| Model | mAP<sup>75</sup> | mAP<sup>50</sup> | mean IoU | Accuracy |
| --- | ---: | ---: | ---: | ---: |
| detector | 75 | 80 | 61 | n/a |
| short row | 72 |
"""
    claims = extract_claims(text)
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("map75", 0.75),
        ("map50", 0.8),
        ("miou", 0.61),
        ("map75", 0.72),
    ]


def test_scoped_map_metric_family_recognizes_threshold_suffixes():
    assert metric_family("validation map result 50 95") == "map50_95"
    assert metric_family("validation map result 75") == "map75"


def test_extracts_scoped_ap_ar_pq_from_markdown_result_tables():
    text = """| Model | train time | box AP | mask AP | AP50 | AR1000 | PQ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| detector | 0.21 | 38.2 | 34.7 | 75.36 | 58.0 | 41.3 |
"""
    claims = extract_claims(text)
    assert [(claim.metric, round(claim.value, 12)) for claim in claims] == [
        ("box_ap", 0.382),
        ("mask_ap", 0.347),
        ("ap50", 0.7536),
        ("ar", 0.58),
        ("pq", 0.413),
    ]


def test_excludes_size_specific_ap_columns_without_losing_threshold_ap():
    text = """| Model | AP test S | AP test M | AP test L | AP small | AP50 | AP75 | AP50-95 | box AP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| detector | 20 | 40 | 55 | 21 | 60 | 45 | 38 | 39 |
"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [
        ("ap50", 0.6),
        ("ap75", 0.45),
        ("map50_95", 0.38),
        ("box_ap", 0.39),
    ]


def test_excludes_size_specific_ap_columns_in_html_tables():
    text = """<table>
<tr><th>Model</th><th>AP medium</th><th>mask AP (L)</th><th>AP</th></tr>
<tr><td>detector</td><td>44</td><td>51</td><td>48</td></tr>
</table>"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [("ap", 0.48)]


def test_extracts_detectron_style_html_tables_with_orphan_header_cells():
    text = """<table><tbody>
<th>Name</th><th>box<br/>AP</th><th>mask AP</th><th>model id</th>
<tr><td>R50-FPN</td><td>37.9</td><td>34.6</td><td>137257794</td></tr>
</tbody></table>"""
    claims = extract_claims(text)
    assert [(claim.metric, round(claim.value, 12)) for claim in claims] == [
        ("box_ap", 0.379),
        ("mask_ap", 0.346),
    ]


def test_new_detection_metric_families_normalize_scoped_names():
    assert metric_family("box_ap") == "ap"
    assert metric_family("proposal_ar") == "ar"
    assert metric_family("panoptic quality") == "pq"


def test_table_only_extraction_excludes_narrative_claims():
    text = """The model reaches AP 42.0 in the paper abstract.

| Model | box AP |
| --- | ---: |
| detector | 38.2 |
"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [
        ("box_ap", 0.382)
    ]


def test_preserves_equal_claims_from_distinct_metric_columns():
    text = """| Model | COCO mAP | Official COCO mAP |
| --- | ---: | ---: |
| detector | 44.9 | 44.9 |
"""
    claims = extract_claims(text)
    assert [(claim.metric, claim.value) for claim in claims] == [
        ("ap", 0.449),
        ("ap", 0.449),
    ]


def test_skips_ambiguous_multi_number_table_cells():
    text = """| Model | box AP | mask AP |
| --- | ---: | ---: |
| detector | 40.8 (+3.4) | 38.2 |
"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [
        ("mask_ap", 0.382)
    ]


def test_markdown_table_parser_preserves_escaped_pipes():
    text = """| Model | box AP | Download |
| --- | ---: | --- |
| detector | 38.2 | [model](model.pth) \\| [log](log.json) |
"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [
        ("box_ap", 0.382)
    ]


def test_spelled_out_detection_metrics_preserve_scope():
    text = """| Model | bbox detection Average Precision | segmentation Average Precision |
| --- | ---: | ---: |
| detector | 0.599 | 0.584 |
"""
    assert [(claim.metric, claim.value) for claim in extract_table_claims(text)] == [
        ("box_ap", 0.599),
        ("mask_ap", 0.584),
    ]


def test_complete_extraction_does_not_parse_table_headers_as_narrative_claims():
    text = """The abstract reports AP 42.0.

| Model | AR 1000 | box AP |
| --- | ---: | ---: |
| detector | 58.0 | 38.2 |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("ap", 0.42),
        ("ar", 0.58),
        ("box_ap", 0.382),
    ]


def test_html_table_mask_preserves_narrative_line_numbers_and_surrounding_text():
    text = """AP 42.0
<table><tr><th>AR 1000</th></tr><tr><td>58.0</td></tr></table>
PQ 41.3
"""
    assert [(claim.metric, claim.value, claim.line) for claim in extract_claims(text)] == [
        ("ap", 0.42, 1),
        ("ar", 0.58, 2),
        ("pq", 0.413, 3),
    ]


def test_portable_result_table_handles_abbreviated_metrics_and_fps():
    text = """| Model | Acc. | Prec. | Rec. | F1 | Speed |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 94.6% | 99.0% | 95.7% | 97.3% | 156.9 FPS |
"""
    assert [(claim.metric, round(claim.value, 6)) for claim in extract_claims(text)] == [
        ("accuracy", 0.946),
        ("precision", 0.99),
        ("recall", 0.957),
        ("f1", 0.973),
        ("frames_per_second", 156.9),
    ]


def test_portable_row_metric_table_normalizes_milliseconds_to_seconds():
    text = """| metric | value |
| --- | ---: |
| mean_ms | 5519.4 |
| p50_ms | 4200.5 |
| p95_ms | 14470.2 |
| p99_ms | 49487.6 |
"""
    assert [(claim.metric, round(claim.value, 6)) for claim in extract_claims(text)] == [
        ("avg_latency_seconds", 5.5194),
        ("p50_latency_seconds", 4.2005),
        ("p95_latency_seconds", 14.4702),
        ("p99_latency_seconds", 49.4876),
    ]


def test_portable_time_console_and_scaled_fps_are_visible():
    text = """no driver: 9k FPS
User time (seconds): 3.83
System time (seconds): 0.48
Percent of CPU this job got: 540%
Elapsed (wall clock) time (h:mm:ss or m:ss): 0:00.80
Maximum resident set size (kbytes): 485672
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("frames_per_second", 9000),
        ("user_time_seconds", 3.83),
        ("system_time_seconds", 0.48),
        ("cpu_percent", 540),
        ("elapsed_time_seconds", 0.8),
        ("memory_kb", 485672),
    ]


def test_expected_duration_column_is_not_reported_as_an_outcome():
    text = """| Test | Measured Time | Expected |
| --- | ---: | ---: |
| render | 17.94ms | <=100ms |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("runtime_seconds", 0.01794),
    ]


def test_validation_loss_table_preserves_mean_and_standard_deviation():
    text = """| Benchmark | AdamW validation loss | Kenian validation loss |
| --- | ---: | ---: |
| vision | 3.135 ± 0.023 | 3.067 ± 0.013 |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("validation_loss", 3.135),
        ("validation_loss_stdev", 0.023),
        ("validation_loss", 3.067),
        ("validation_loss_stdev", 0.013),
    ]


def test_portable_latency_does_not_duplicate_specialized_latency():
    text = """| Metric | Threshold | Achieved | Status |
|---|---:|---:|---|
| Latency (GPU) | — | 28 ms | — |
"""
    assert [(claim.metric, claim.value) for claim in extract_claims(text)] == [
        ("avg_latency_seconds", 0.028),
    ]
