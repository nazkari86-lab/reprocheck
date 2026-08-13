from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def claim(line: int, metric: str, value: float) -> dict[str, Any]:
    return {"line": line, "metric": metric, "value": value}


def eligible(
    rank: int, reason: str, block: tuple[int, int], claims: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "rank": rank,
        "eligible": True,
        "reason": reason,
        "block_lines": list(block),
        "claims": claims,
    }


def excluded(rank: int, reason: str) -> dict[str, Any]:
    return {"rank": rank, "eligible": False, "reason": reason, "claims": []}


CASES = [
    excluded(1, "first benchmark table contains more than twenty outcome claims"),
    eligible(
        2,
        "first result table contains eight performance outcomes",
        (11, 15),
        [
            claim(13, "requests_per_second", 31272),
            claim(13, "latency_ms", 3.20),
            claim(13, "performance_change_percent", 120),
            claim(14, "requests_per_second", 20840),
            claim(14, "latency_ms", 4.80),
            claim(14, "performance_change_percent", 47),
            claim(15, "requests_per_second", 14207),
            claim(15, "latency_ms", 7.04),
        ],
    ),
    excluded(3, "first result table contains thirty quantitative outcomes"),
    eligible(
        4,
        "first result table contains three measured render times",
        (15, 19),
        [
            claim(17, "runtime_ms", 17.94),
            claim(18, "runtime_ms", 8.35),
            claim(19, "runtime_ms", 1.91),
        ],
    ),
    eligible(
        5,
        "first confirmed-result table contains twenty outcomes",
        (14, 21),
        [
            claim(16, "baseline_column_count", 107),
            claim(16, "optimized_column_count", 74),
            claim(16, "column_reduction", -33),
            claim(16, "column_reduction_percent", 31),
            claim(17, "baseline_memory_mb", 577.5),
            claim(17, "optimized_memory_mb", 228.1),
            claim(17, "memory_reduction_mb", -349.4),
            claim(17, "memory_reduction_percent", 61),
            claim(18, "baseline_runtime_seconds", 0.145),
            claim(18, "optimized_runtime_seconds", 0.041),
            claim(18, "speedup", 3.5),
            claim(19, "baseline_runtime_seconds", 0.671),
            claim(19, "optimized_runtime_seconds", 0.412),
            claim(19, "speedup", 1.6),
            claim(20, "baseline_runtime_seconds", 0.129),
            claim(20, "optimized_runtime_seconds", 0.051),
            claim(20, "speedup", 2.5),
            claim(21, "baseline_runtime_seconds", 1.895),
            claim(21, "optimized_runtime_seconds", 0.512),
            claim(21, "speedup", 3.7),
        ],
    ),
    eligible(
        6,
        "executive-summary block contains four outcomes",
        (9, 13),
        [
            claim(10, "speedup_percent", 47),
            claim(11, "relative_performance_percent", 109),
            claim(12, "relative_performance_percent", 80),
            claim(13, "tokens_per_second", 13.49),
        ],
    ),
    eligible(
        7,
        "first accuracy table contains sixteen outcome values",
        (5, 11),
        [
            claim(7, "strict_match_accuracy", 0.8582),
            claim(7, "flexible_extract_accuracy", 0.8582),
            claim(8, "strict_match_accuracy", 0.8537),
            claim(8, "flexible_extract_accuracy", 0.8544),
            claim(8, "strict_delta_percentage_points", -0.45),
            claim(8, "flexible_delta_percentage_points", -0.38),
            claim(9, "strict_match_accuracy", 0.7945),
            claim(9, "flexible_extract_accuracy", 0.7945),
            claim(10, "strict_match_accuracy", 0.0197),
            claim(10, "flexible_extract_accuracy", 0.1061),
            claim(10, "strict_delta_percentage_points", -77.48),
            claim(10, "flexible_delta_percentage_points", -68.84),
            claim(11, "strict_match_accuracy", 0.7938),
            claim(11, "flexible_extract_accuracy", 0.7930),
            claim(11, "strict_delta_percentage_points", -0.07),
            claim(11, "flexible_delta_percentage_points", -0.15),
        ],
    ),
    eligible(
        8,
        "first evidence paragraph contains six scored outcomes",
        (11, 17),
        [
            claim(14, "holistic_score", 8.255),
            claim(14, "mobile_score", 8.595),
            claim(15, "holistic_score", 8.185),
            claim(15, "mobile_score", 8.645),
            claim(17, "holistic_score", 7.58),
            claim(17, "mobile_score", 7.46),
        ],
    ),
    eligible(
        9,
        "first performance table contains twelve outcomes",
        (5, 10),
        [
            claim(7, "accuracy", 0.6518),
            claim(7, "avg_response_tokens", 4315.8),
            claim(7, "avg_response_chars", 12096.0),
            claim(8, "accuracy", 0.8686),
            claim(8, "avg_response_tokens", 2944.8),
            claim(8, "avg_response_chars", 8141.1),
            claim(9, "accuracy", 0.8834),
            claim(9, "avg_response_tokens", 2849.3),
            claim(9, "avg_response_chars", 7886.6),
            claim(10, "accuracy", 0.8438),
            claim(10, "avg_response_tokens", 3198.8),
            claim(10, "avg_response_chars", 8822.7),
        ],
    ),
    eligible(
        10,
        "executive summary contains accuracy, successful-answer, and completion outcomes",
        (10, 15),
        [
            claim(11, "accuracy", 0.8189),
            claim(15, "successful_answer_count", 42),
            claim(15, "completion_rate", 1.0),
        ],
    ),
    eligible(
        11,
        "first result table contains six mean keyword-count outcomes",
        (17, 24),
        [
            claim(19, "mean_keyword_count", 4.43),
            claim(20, "mean_keyword_count", 1.31),
            claim(21, "mean_keyword_count", 18.00),
            claim(22, "mean_keyword_count", 4.37),
            claim(23, "mean_keyword_count", 1.73),
            claim(24, "mean_keyword_count", 2.51),
        ],
    ),
    eligible(
        12,
        "first validation table contains twelve active metric outcomes",
        (24, 29),
        [
            claim(26, "retrieval", 1.0),
            claim(26, "lifecycle", 1.0),
            claim(27, "retrieval", 1.0),
            claim(27, "lifecycle", 1.0),
            claim(27, "scope_accuracy", 1.0),
            claim(28, "retrieval", 1.0),
            claim(28, "lifecycle", 1.0),
            claim(28, "scope_accuracy", 1.0),
            claim(28, "qa", 1.0),
            claim(29, "retrieval", 1.0),
            claim(29, "lifecycle", 1.0),
            claim(29, "scope_accuracy", 1.0),
        ],
    ),
    eligible(
        13,
        "first empirical history table contains four open-time outcomes",
        (21, 25),
        [
            claim(23, "cold_open_ms", 55),
            claim(24, "cold_open_seconds", 1.1),
            claim(25, "cold_open_seconds", 1.1),
            claim(25, "warm_open_ms", 26),
        ],
    ),
    excluded(14, "first summary table contains more than twenty outcomes"),
    eligible(
        15,
        "first summary table contains twelve relative-performance outcomes",
        (7, 13),
        [
            claim(9, "performance_change_percent", -43),
            claim(9, "performance_change_percent", -13),
            claim(10, "performance_change_percent", -40),
            claim(10, "overhead_percent", 2),
            claim(10, "overhead_percent", 5),
            claim(11, "performance_change_percent", -25),
            claim(11, "overhead_percent", 2),
            claim(11, "overhead_percent", 5),
            claim(12, "performance_change_percent", -46),
            claim(12, "overhead_percent", 2),
            claim(12, "overhead_percent", 5),
            claim(13, "performance_change_percent", 9),
        ],
    ),
    excluded(16, "resource guide defines metrics but reports no empirical result block"),
    eligible(
        17,
        "first console-result block contains five resource outcomes",
        (11, 18),
        [
            claim(13, "user_time_seconds", 3.83),
            claim(14, "system_time_seconds", 0.48),
            claim(15, "cpu_percent", 540),
            claim(16, "elapsed_time_seconds", 0.80),
            claim(17, "memory_kb", 485672),
        ],
    ),
    eligible(
        18,
        "first type-distribution result table contains eighteen outcomes",
        (55, 62),
        [
            claim(57, "zero_count_ratio", 0.143),
            claim(57, "p25", 1.25),
            claim(57, "median", 3),
            claim(58, "zero_count_ratio", 0.286),
            claim(58, "p25", 0.25),
            claim(58, "median", 2),
            claim(59, "zero_count_ratio", 0.357),
            claim(59, "p25", 0),
            claim(59, "median", 1),
            claim(60, "zero_count_ratio", 0.643),
            claim(60, "p25", 0),
            claim(60, "median", 0),
            claim(61, "zero_count_ratio", 0.643),
            claim(61, "p25", 0),
            claim(61, "median", 0),
            claim(62, "zero_score_ratio", 0),
            claim(62, "p25", 40),
            claim(62, "median", 60),
        ],
    ),
    excluded(19, "generated API type documentation contains no empirical outcomes"),
    excluded(20, "implementation report lists checks but no quantitative result block"),
    eligible(
        21,
        "first accelerator table contains nine cycle and speed outcomes",
        (7, 11),
        [
            claim(9, "cpu_cycles", 11070),
            claim(9, "accelerator_cycles", 1100),
            claim(9, "speedup", 10.0),
            claim(10, "cpu_cycles", 84780),
            claim(10, "accelerator_cycles", 8235),
            claim(10, "speedup", 10.30),
            claim(11, "cpu_cycles", 766232),
            claim(11, "accelerator_cycles", 69490),
            claim(11, "speedup", 11.02),
        ],
    ),
    excluded(22, "generated API reference defines a result type but contains no measured result"),
    eligible(
        23,
        "first calibration table contains eight accuracy outcomes",
        (11, 20),
        [
            claim(13, "accuracy", 1.0),
            claim(14, "accuracy", 1.0),
            claim(15, "accuracy", 1.0),
            claim(16, "accuracy", 1.0),
            claim(17, "accuracy", 1.0),
            claim(18, "accuracy", 1.0),
            claim(19, "accuracy", 1.0),
            claim(20, "accuracy", 0.917),
        ],
    ),
    eligible(
        24,
        "first game-level table contains twenty confusion and performance outcomes",
        (12, 15),
        [
            claim(14, "true_positive", 15863),
            claim(14, "true_negative", 396),
            claim(14, "false_positive_1", 142),
            claim(14, "false_positive_2", 17),
            claim(14, "false_negative", 775),
            claim(14, "accuracy", 0.946),
            claim(14, "precision", 0.990),
            claim(14, "recall", 0.957),
            claim(14, "f1", 0.973),
            claim(14, "frames_per_second", 156.9),
            claim(15, "true_positive", 15973),
            claim(15, "true_negative", 389),
            claim(15, "false_positive_1", 167),
            claim(15, "false_positive_2", 24),
            claim(15, "false_negative", 640),
            claim(15, "accuracy", 0.952),
            claim(15, "precision", 0.988),
            claim(15, "recall", 0.961),
            claim(15, "f1", 0.975),
            claim(15, "frames_per_second", 155.7),
        ],
    ),
    eligible(
        25,
        "first wrk console block contains thirteen performance outcomes",
        (7, 12),
        [
            claim(8, "latency_ms", 92.21),
            claim(8, "latency_stdev_ms", 66.06),
            claim(8, "max_latency_ms", 708.65),
            claim(8, "latency_within_stdev_ratio", 0.8061),
            claim(9, "requests_per_second", 386.64),
            claim(9, "requests_per_second_stdev", 48.25),
            claim(9, "max_requests_per_second", 570.0),
            claim(9, "requests_within_stdev_ratio", 0.7207),
            claim(10, "request_count", 138365),
            claim(10, "runtime_seconds", 30.03),
            claim(10, "data_read_mb", 7.92),
            claim(11, "requests_per_second", 4606.98),
            claim(12, "transfer_kb_per_second", 269.94),
        ],
    ),
    excluded(26, "personal notes contain plans and links but no empirical result block"),
    eligible(
        27,
        "result list contains six exact-match, win, delta, and range outcomes",
        (6, 12),
        [
            claim(7, "exact_match_count", 2),
            claim(9, "win_count", 11),
            claim(10, "mean_delta_ms", -0.0006),
            claim(10, "mean_delta_percent", -0.17),
            claim(11, "min_delta_percent", -0.59),
            claim(11, "max_delta_percent", 0.39),
        ],
    ),
    excluded(28, "first detailed benchmark block contains more than twenty outcomes"),
    excluded(29, "first BenchmarkDotNet result table contains more than twenty outcomes"),
    excluded(30, "first OCR leaderboard table contains more than twenty outcomes"),
    eligible(
        31,
        "first inline result table contains nine relative-performance endpoints",
        (253, 259),
        [
            claim(255, "speedup", 0.01),
            claim(255, "speedup", 0.2),
            claim(256, "speedup", 0.1),
            claim(256, "speedup", 0.5),
            claim(257, "speedup", 0.1),
            claim(257, "speedup", 0.3),
            claim(258, "speedup", 0.2),
            claim(258, "speedup", 0.5),
            claim(259, "speedup", 0.2),
        ],
    ),
    excluded(
        32, "benchmark index provides commands and external links but no textual result block"
    ),
    excluded(33, "first benchmark table contains more than twenty outcomes"),
    eligible(
        34,
        "first LLM-latency table contains four latency outcomes",
        (16, 22),
        [
            claim(19, "mean_latency_ms", 5519.4),
            claim(20, "p50_latency_ms", 4200.5),
            claim(21, "p95_latency_ms", 14470.2),
            claim(22, "p99_latency_ms", 49487.6),
        ],
    ),
    excluded(35, "first headline prose block contains more than twenty quantitative outcomes"),
    eligible(
        36,
        "first graphics-performance block contains three FPS outcomes",
        (3, 11),
        [
            claim(5, "frames_per_second", 9000),
            claim(9, "frames_per_second", 14000),
            claim(11, "frames_per_second", 22000),
        ],
    ),
    excluded(37, "experiment plan contains methodology but no measured results"),
    excluded(38, "experiment index links to external results without textual outcome block"),
    excluded(39, "reproduction instructions contain no textual empirical outcomes"),
    excluded(40, "command notebook contains configurations but no textual result block"),
    excluded(
        41,
        "experiment inventory reports configurations and run lengths rather than outcome metrics",
    ),
    excluded(42, "first downstream validation table contains more than twenty outcomes"),
    excluded(43, "coursework instructions contain no completed empirical results"),
    eligible(
        44,
        "executive summary contains six evaluation outcomes",
        (3, 7),
        [
            claim(7, "gold_hit_count", 76),
            claim(7, "gold_span_recall", 0.6609),
            claim(7, "baseline_gold_span_recall", 0.6435),
            claim(7, "summary_pass_count", 50),
            claim(7, "completed_contract_count", 50),
            claim(7, "alignment_rate", 0.9565),
        ],
    ),
    eligible(
        45,
        "first result summary contains three model-size and latency outcomes",
        (35, 38),
        [
            claim(38, "parameter_count", 95000),
            claim(38, "flops", 10560000),
            claim(38, "latency_ms", 1.0),
        ],
    ),
    excluded(46, "first totals table contains more than twenty outcomes"),
    eligible(
        47,
        "first result table contains eight validation-loss outcomes",
        (43, 46),
        [
            claim(45, "adamw_validation_loss", 3.135),
            claim(45, "adamw_validation_loss_stdev", 0.023),
            claim(45, "kenian_validation_loss", 3.067),
            claim(45, "kenian_validation_loss_stdev", 0.013),
            claim(46, "adamw_validation_loss", 3.182),
            claim(46, "adamw_validation_loss_stdev", 0.003),
            claim(46, "kenian_validation_loss", 3.212),
            claim(46, "kenian_validation_loss_stdev", 0.006),
        ],
    ),
]


def main() -> None:
    samples = {
        item["sample_rank"]: item
        for item in json.loads((ROOT / "sample.json").read_text())["samples"]
    }
    labels = []
    for case in CASES:
        item = samples[case["rank"]]
        labels.append(
            {**case, "repository": item["repository"], "source_file": item["source_file"]}
        )
    document = {
        "schema_version": "reprocheck.cross-project-labels.v14",
        "annotation_mode": "manual-source-only-no-extractor-output",
        "review_order": "ascending sample rank",
        "stop_rule": "first 25 eligible documents",
        "reviewed_documents": len(labels),
        "eligible_documents": sum(case["eligible"] for case in labels),
        "labels": labels,
    }
    (ROOT / "labels.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
