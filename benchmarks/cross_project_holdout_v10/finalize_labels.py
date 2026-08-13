from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def claim(metric: str, value: float, line: int, snippet: str, **context: str) -> dict[str, Any]:
    return {"metric": metric, "value": value, "line": line, "snippet": snippet, "context": context}


CLAIMS: dict[int, list[dict[str, Any]]] = {
    2: [
        claim("runtime_seconds", 0.832, 58, "| 1 | 0.832s | 1.267s |", system="c-logger", threads="1"),
        claim("runtime_seconds", 1.267, 58, "| 1 | 0.832s | 1.267s |", system="glog", threads="1"),
        claim("runtime_seconds", 1.386, 59, "| 10 | 1.386s | 1.183s |", system="c-logger", threads="10"),
        claim("runtime_seconds", 1.183, 59, "| 10 | 1.386s | 1.183s |", system="glog", threads="10"),
    ],
    3: [
        claim("optimal_throughput_ratio", 0.685, 80, "NanoFlow achieves 68.5% of optimal throughput"),
        claim("speedup", 1.91, 80, "provides 1.91× throughput boost"),
        claim("optimal_throughput_ratio", 0.59, 80, "achieving 59% to 72% of optimal throughput", bound="lower"),
        claim("optimal_throughput_ratio", 0.72, 80, "achieving 59% to 72% of optimal throughput", bound="upper"),
    ],
    6: [
        claim("artifact_size_kb", 0, 32, "| javascript | 0 | 84 | 8 |", system="javascript"),
        claim("avg_latency_seconds", 0.084, 32, "| javascript | 0 | 84 | 8 |", system="javascript"),
        claim("latency_stdev_seconds", 0.008, 32, "| javascript | 0 | 84 | 8 |", system="javascript"),
        claim("artifact_size_kb", 20, 33, "| simple replace, wee_alloc | 20 | 127 | 26 |", system="simple replace wee_alloc"),
        claim("avg_latency_seconds", 0.127, 33, "| simple replace, wee_alloc | 20 | 127 | 26 |", system="simple replace wee_alloc"),
        claim("latency_stdev_seconds", 0.026, 33, "| simple replace, wee_alloc | 20 | 127 | 26 |", system="simple replace wee_alloc"),
        claim("artifact_size_kb", 25, 34, "| simple replace, no wee_alloc | 25 | 133 | 30 |", system="simple replace no wee_alloc"),
        claim("avg_latency_seconds", 0.133, 34, "| simple replace, no wee_alloc | 25 | 133 | 30 |", system="simple replace no wee_alloc"),
        claim("latency_stdev_seconds", 0.030, 34, "| simple replace, no wee_alloc | 25 | 133 | 30 |", system="simple replace no wee_alloc"),
        claim("artifact_size_kb", 193, 35, "| regex, wee_alloc, default-features off | 193 | 540 | 235 |", system="regex minimal"),
        claim("avg_latency_seconds", 0.540, 35, "| regex, wee_alloc, default-features off | 193 | 540 | 235 |", system="regex minimal"),
        claim("latency_stdev_seconds", 0.235, 35, "| regex, wee_alloc, default-features off | 193 | 540 | 235 |", system="regex minimal"),
    ],
    9: [
        claim("processed_token_count", 6788, 161, "processed 6788 tokens with 3818 phrases", split="dev"),
        claim("phrase_count", 3818, 161, "processed 6788 tokens with 3818 phrases", split="dev"),
        claim("found_phrase_count", 3798, 161, "found: 3798 phrases", split="dev"),
        claim("correct_phrase_count", 3384, 161, "correct: 3384", split="dev"),
        claim("accuracy", 0.9128, 163, "accuracy: 91.28%", split="dev"),
        claim("precision", 0.8910, 163, "precision: 89.10%", split="dev"),
        claim("recall", 0.8863, 163, "recall: 88.63%", split="dev"),
        claim("f1", 0.8887, 163, "FB1: 88.87", split="dev"),
        claim("precision", 0.8910, 165, "precision: 89.10%", split="dev_detail"),
        claim("recall", 0.8863, 165, "recall: 88.63%", split="dev_detail"),
        claim("f1", 0.8887, 165, "FB1: 88.87", split="dev_detail"),
        claim("found_phrase_count", 3798, 165, "FB1: 88.87 3798", split="dev_detail"),
    ],
    10: [
        claim("precision", 0.96, 46, "Random Forest showed superior precision (96%)", system="Random Forest"),
        claim("precision", 0.70, 46, "Decision Tree (70%)", system="Decision Tree"),
        claim("precision", 0.97, 46, "XGBoost (97%)", system="XGBoost"),
        claim("accuracy", 1.0, 47, "similar overall accuracy (~100%)", system="models", approximate="true"),
    ],
    11: [claim("f1", 0.5869, 166, "best F1 score achieved on testing set of 173 images: 0.5869", system="Model 1")],
    12: [
        claim("artifact_size_mb", 3.2, 11, "requiring only 3.2MB"),
        claim("f1_improvement", 0.505, 11, "improves the classical F1 score by 50.5%"),
        claim("aff_f1_improvement", 0.078, 11, "Aff-F1 score by 7.8%"),
        claim("auc_improvement", 0.100, 11, "AUC by 10.0%"),
    ],
    14: [
        claim("runtime_seconds", 0.00018, 199, "0.18ms, 0 B", system="ModiBuff", operation="NoOp"),
        claim("memory_bytes", 0, 199, "0.18ms, 0 B", system="ModiBuff", operation="NoOp"),
        claim("runtime_seconds", 0.00026, 199, "0.26ms, 0 B", system="ModiBuff", operation="Apply InitDmg"),
        claim("memory_bytes", 0, 199, "0.26ms, 0 B", system="ModiBuff", operation="Apply InitDmg"),
        claim("runtime_seconds", 0.00044, 199, "0.44ms, 0 B", system="ModiBuff", operation="Apply InitStackDmg"),
        claim("memory_bytes", 0, 199, "0.44ms, 0 B", system="ModiBuff", operation="Apply InitStackDmg"),
        claim("runtime_seconds", 0.00101, 199, "1.01ms, 0 B", system="ModiBuff", operation="Apply Multi instance DoT"),
        claim("memory_bytes", 0, 199, "1.01ms, 0 B", system="ModiBuff", operation="Apply Multi instance DoT"),
        claim("runtime_seconds", 0.00102, 200, "1.02ms, 0 GC", system="ModiBuffEcs", operation="Apply InitDmg"),
        claim("allocation_count", 0, 200, "1.02ms, 0 GC", system="ModiBuffEcs", operation="Apply InitDmg"),
        claim("runtime_seconds", 0.0214, 201, "21.4ms, 24 GC", system="Old", operation="Apply InitDmg"),
        claim("allocation_count", 24, 201, "21.4ms, 24 GC", system="Old", operation="Apply InitDmg"),
    ],
    15: [
        claim("max_batch_size", 7, 47, "maximum batch size is 7", system="naive"),
        claim("oom_batch_size", 8, 47, "I get an OOM with 8", system="naive"),
        claim("memory_mb", 7403.52, 52, "Fragmented Memory: 7.23 GB", system="naive"),
        claim("fragmentation_ratio", 0.2846, 52, "Fragmented Memory: 7.23 GB (28.46%)", system="naive"),
        claim("fragmentation_ratio", 0.01, 60, "decreases fragmentation to <1%", system="paged", comparator="lt"),
        claim("speedup", 7, 60, "increases maximum batch size by 7X", system="paged"),
        claim("max_batch_size", 49, 62, "python llama3-paged.py 49", system="paged"),
        claim("memory_mb", 143.36, 65, "Fragmented Memory: 0.14 GB", system="paged"),
        claim("fragmentation_ratio", 0.0057, 65, "Fragmented Memory: 0.14 GB (0.57%)", system="paged"),
    ],
    17: [
        claim("avg_latency_seconds", 0.00094, 104, "Latency 0.94ms 2.47ms 206.34ms 99.64%", system="Titan"),
        claim("latency_stdev_seconds", 0.00247, 104, "Latency 0.94ms 2.47ms 206.34ms 99.64%", system="Titan"),
        claim("max_latency_seconds", 0.20634, 104, "Latency 0.94ms 2.47ms 206.34ms 99.64%", system="Titan"),
        claim("within_stdev_ratio", 0.9964, 104, "Latency 0.94ms 2.47ms 206.34ms 99.64%", system="Titan"),
        claim("requests_per_second", 19590, 105, "Req/Sec 19.59k 1.53k 22.74k 75.00%", system="Titan", statistic="avg"),
        claim("requests_per_second", 1530, 105, "Req/Sec 19.59k 1.53k 22.74k 75.00%", system="Titan", statistic="stdev"),
        claim("requests_per_second", 22740, 105, "Req/Sec 19.59k 1.53k 22.74k 75.00%", system="Titan", statistic="max"),
        claim("within_stdev_ratio", 0.75, 105, "Req/Sec 19.59k 1.53k 22.74k 75.00%", system="Titan"),
        claim("request_count", 780113, 106, "780113 requests in 10.03s, 826.55MB read", system="Titan"),
        claim("runtime_seconds", 10.03, 106, "780113 requests in 10.03s, 826.55MB read", system="Titan"),
        claim("data_read_mb", 826.55, 106, "780113 requests in 10.03s, 826.55MB read", system="Titan"),
        claim("requests_per_second", 77770.10, 107, "Requests/sec: 77770.10", system="Titan"),
    ],
    18: [
        claim("avg_latency_seconds", 0.009747, 96, "Thread calibration: mean lat.: 9747 usec", thread="1"),
        claim("sampling_interval_seconds", 0.021, 96, "rate sampling interval: 21 msec", thread="1"),
        claim("avg_latency_seconds", 0.009631, 97, "Thread calibration: mean lat.: 9631 usec", thread="2"),
        claim("sampling_interval_seconds", 0.021, 97, "rate sampling interval: 21 msec", thread="2"),
        claim("avg_latency_seconds", 0.00646, 99, "Latency 6.46ms 1.93ms 12.34ms 67.66%"),
        claim("latency_stdev_seconds", 0.00193, 99, "Latency 6.46ms 1.93ms 12.34ms 67.66%"),
        claim("max_latency_seconds", 0.01234, 99, "Latency 6.46ms 1.93ms 12.34ms 67.66%"),
        claim("within_stdev_ratio", 0.6766, 99, "Latency 6.46ms 1.93ms 12.34ms 67.66%"),
        claim("requests_per_second", 1050, 100, "Req/Sec 1.05k 1.12k 2.50k 64.84%", statistic="avg"),
        claim("requests_per_second", 1120, 100, "Req/Sec 1.05k 1.12k 2.50k 64.84%", statistic="stdev"),
        claim("requests_per_second", 2500, 100, "Req/Sec 1.05k 1.12k 2.50k 64.84%", statistic="max"),
        claim("within_stdev_ratio", 0.6484, 100, "Req/Sec 1.05k 1.12k 2.50k 64.84%"),
    ],
    20: [
        claim("tokens_per_second_gpu", 9731, 30, "Qwen3-0.6B | 2048 | 2 | - | 9,731", row="1"),
        claim("tflops_per_second_gpu", 57.6, 30, "57.6 | 22.5% | 22.2 GB", row="1"),
        claim("mfu", 0.225, 30, "57.6 | 22.5% | 22.2 GB", row="1"),
        claim("memory_mb", 22732.8, 30, "22.2 GB", row="1"),
        claim("tokens_per_second_gpu", 9834, 31, "Qwen3-0.6B | 8192 | 1 | Yes | 9,834", row="2"),
        claim("tflops_per_second_gpu", 99.8, 31, "99.8 | 39.0% | 21.4 GB", row="2"),
        claim("mfu", 0.390, 31, "99.8 | 39.0% | 21.4 GB", row="2"),
        claim("memory_mb", 21913.6, 31, "21.4 GB", row="2"),
        claim("tokens_per_second_gpu", 9079, 32, "Qwen3-0.6B | 16384 | 1 | Yes | 9,079", row="3"),
        claim("tflops_per_second_gpu", 143.3, 32, "143.3 | 56.0% | 39.2 GB", row="3"),
        claim("mfu", 0.560, 32, "143.3 | 56.0% | 39.2 GB", row="3"),
        claim("memory_mb", 40140.8, 32, "39.2 GB", row="3"),
    ],
    24: [
        claim("assertion_count", 1, 62, "All tests passed (1 assertions in 1 test case)"),
        claim("test_count", 1, 62, "All tests passed (1 assertions in 1 test case)"),
    ],
    28: [
        claim("bleu_2", 0.061, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("bleu_4", 0.027, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("rouge_l_1", 0.204, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("rouge_l_2", 0.087, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("rouge_l", 0.186, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("meteor", 0.114, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("text2mol", 0.057, 69, "Transformer | 0.061 | 0.027 | 0.204 | 0.087 | 0.186 | 0.114 | 0.057", system="Transformer"),
        claim("bleu_2", 0.103, 70, "GPT-3.5-turbo (zero_shot) | 0.103 | 0.050 | 0.261 | 0.088 | 0.204", system="GPT-3.5 zero-shot"),
        claim("bleu_4", 0.050, 70, "GPT-3.5-turbo (zero_shot) | 0.103 | 0.050 | 0.261 | 0.088 | 0.204", system="GPT-3.5 zero-shot"),
        claim("rouge_l_1", 0.261, 70, "GPT-3.5-turbo (zero_shot) | 0.103 | 0.050 | 0.261 | 0.088 | 0.204", system="GPT-3.5 zero-shot"),
        claim("rouge_l_2", 0.088, 70, "GPT-3.5-turbo (zero_shot) | 0.103 | 0.050 | 0.261 | 0.088 | 0.204", system="GPT-3.5 zero-shot"),
        claim("rouge_l", 0.204, 70, "GPT-3.5-turbo (zero_shot) | 0.103 | 0.050 | 0.261 | 0.088 | 0.204", system="GPT-3.5 zero-shot"),
    ],
    31: [
        claim("bleu_improvement", 1.12, 4, "improvements of 112% in BLEU scores"),
        claim("rouge_l_improvement", 0.217, 4, "21.7% in ROUGE-L scores"),
        claim("bleu_stdev", 3.72, 4, "standard deviations of 3.72 and 0.00075", metric_scope="BLEU"),
        claim("rouge_l_stdev", 0.00075, 4, "standard deviations of 3.72 and 0.00075", metric_scope="ROUGE-L"),
        claim("weighted_f1_decline", 0.13, 4, "Weighted F1 scores showed an expected decline of 13%"),
    ],
    32: [
        *[claim(metric, value, line, snippet, system=system) for line, system, values, snippet in [
            (89, "OpenSearch-SQL", [38.89, 4.76, 24.00, 23.87], "OpenSearch-SQL | 38.89 | 4.76 | 24.00 | 23.87"),
            (91, "TableLLaMA", [35.01, 32.70, 40.39, 26.71], "TableLLaMA | 35.01 | 32.70 | 40.39 | 26.71"),
            (92, "TableLLM", [62.40, 9.13, 7.84, 2.93], "TableLLM | 62.40 | 9.13 | 7.84 | 2.93"),
        ] for metric, value in zip(["wikitq_accuracy", "temptabqa_accuracy", "sstqa_accuracy", "sstqa_rouge_l"], [v / 100 for v in values])]
    ],
    33: [
        claim("iou", 0.90, 149, "| IoU | 0.90 |", system="U-Net"),
        claim("dice", 0.95, 150, "| Dice | 0.95 |", system="U-Net"),
        claim("precision", 0.92, 151, "| Precision | 0.92 |", system="U-Net"),
        claim("recall", 0.97, 152, "| Recall | 0.97 |", system="U-Net"),
        claim("auroc", 0.99, 153, "| ROC AUC | 0.99 |", system="U-Net"),
    ],
    34: [
        claim("precision", 0.974872, 178, "Precision: 0.974872", split="test"),
        claim("recall", 0.982158, 179, "Recall: 0.982158", split="test"),
        claim("f1", 0.978501, 180, "F1 Score: 0.978501", split="test"),
        claim("specificity", 0.991546, 181, "Specificity: 0.991546", split="test"),
        claim("auroc", 0.986852, 182, "AUC: 0.986852", split="test"),
        claim("iou", 0.957907, 183, "IoU: 0.957907", split="test"),
        claim("dice", 0.978501, 184, "Dice Coefficient: 0.978501", split="test"),
    ],
    35: [
        claim("auroc", 0.9515, 28, "95.15% image-level AU-ROC", level="image"),
        claim("pro", 0.9293, 28, "92.93% pixel-level PRO", level="pixel"),
    ],
    38: [
        *[claim(metric, value, line, snippet, system=system) for line, system, values, snippet in [
            (60, "ColQwen2.5", [0.630, 0.666, 0.717, 0.766, 0.573], "ColQwen2.5 | 0.630 | 0.666 | 0.717 | 0.766 | 0.573"),
            (61, "ColGemma3", [0.626, 0.660, 0.709, 0.767, 0.564], "ColGemma3 | 0.626 | 0.660 | 0.709 | 0.767 | 0.564"),
            (62, "ColQwen2", [0.624, 0.657], "ColQwen2 | 0.624 | 0.657"),
        ] for metric, value in zip(["ndcg_5", "ndcg_10", "mrr", "recall_10", "map_10"], values)]
    ],
}


INELIGIBLE = {
    1: "no empirical numeric result in sampled README",
    4: "reproduction instructions but no numeric result in sampled README",
    5: "results are only linked externally",
    7: "reproduction repository description without numeric result",
    8: "results are images or external links without human-readable numeric claims",
    13: "benchmark roadmap without numeric result",
    16: "metric definitions without observed values",
    19: "README explicitly states the benchmark is missing",
    21: "educational reference values, not repository evaluation results",
    22: "benchmark instructions without observed values",
    23: "test tooling documentation without an observed numeric result region",
    25: "evaluation instructions without observed numeric results",
    26: "feature and configuration counts, not observed evaluation outcomes",
    27: "results are external notebook/paper only",
    29: "results are qualitative images without human-readable numeric claims",
    30: "configuration values and architecture description only",
    36: "experiment code without committed observed numeric results",
    37: "evaluation capabilities without committed observed numeric results",
}


def main() -> int:
    sample = json.loads((ROOT / "sample.json").read_text())
    labels: list[dict[str, Any]] = []
    eligible_seen = 0
    for item in sample["samples"]:
        rank = item["sample_rank"]
        base = {"rank": rank, "repository": item["repository"], "path": item["path"]}
        if rank in CLAIMS:
            eligible_seen += 1
            labels.append({**base, "review_status": "reviewed", "eligible": True, "claims": CLAIMS[rank]})
        elif rank in INELIGIBLE:
            labels.append({**base, "review_status": "reviewed", "eligible": False, "reason": INELIGIBLE[rank]})
        elif eligible_seen >= 20:
            labels.append({**base, "review_status": "not_reviewed_target_reached", "eligible": None})
        else:
            raise RuntimeError(f"missing sequential eligibility decision for rank {rank}")
    if eligible_seen != 20:
        raise RuntimeError(f"expected 20 eligible documents, got {eligible_seen}")
    output = {
        "schema_version": "reprocheck.cross-project-labels.v10",
        "annotation_without_extractor": True,
        "sequential_stop_rank": 38,
        "eligible_documents": eligible_seen,
        "selected_claims": sum(len(claims) for claims in CLAIMS.values()),
        "labels": labels,
    }
    (ROOT / "labels.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"eligible_documents": eligible_seen, "selected_claims": output["selected_claims"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
