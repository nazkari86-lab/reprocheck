from __future__ import annotations

import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13 import retrieve as engine


ROOT = Path(__file__).resolve().parent
BASE_PRIOR = engine.prior_repositories_and_owners
SEED = "reprocheck-cross-project-v17-explicit-metric-blocks"
QUERIES = [
    '"Precision" "Recall" "F1" filename:RESULTS.md extension:md',
    '"Accuracy" "Precision" "Recall" filename:RESULTS.md extension:md',
    '"mAP" "Precision" "Recall" filename:RESULTS.md extension:md',
    '"RMSE" "MAE" filename:RESULTS.md extension:md',
    '"P95 Latency" "Throughput" filename:RESULTS.md extension:md',
    '"Precision" "Recall" "F1" filename:BENCHMARK.md extension:md',
    '"Accuracy" "F1" filename:BENCHMARK.md extension:md',
    '"P95" "Latency" filename:BENCHMARK.md extension:md',
    '"Throughput" "requests" filename:BENCHMARK.md extension:md',
    '"Precision" "Recall" "F1" filename:EXPERIMENTS.md extension:md',
    '"Accuracy" "F1" filename:EXPERIMENTS.md extension:md',
    '"BLEU" "ROUGE" filename:EXPERIMENTS.md extension:md',
    '"RMSE" "MAE" filename:EXPERIMENTS.md extension:md',
    '"Precision" "Recall" "F1" filename:METRICS.md extension:md',
    '"Accuracy" "mAP" filename:METRICS.md extension:md',
    '"Latency" "Throughput" filename:METRICS.md extension:md',
    '"Precision" "Recall" "F1" path:results extension:md',
    '"Accuracy" "F1" path:results extension:md',
    '"RMSE" "MAE" path:results extension:md',
    '"P95" "Latency" path:results extension:md',
    '"Precision" "Recall" "F1" path:evaluation extension:md',
    '"mAP50" "mAP50-95" path:evaluation extension:md',
    '"AUROC" "AUPRC" path:evaluation extension:md',
    '"Accuracy" "F1" path:benchmark extension:md',
    '"Precision" "Recall" path:benchmark extension:md',
    '"Throughput" "Latency" path:benchmark extension:md',
    '"precision" "recall" "f1-score" filename:results.txt extension:txt',
    '"accuracy" "f1" filename:results.txt extension:txt',
    '"p95 latency" filename:results.txt extension:txt',
    '"throughput" "success rate" filename:results.txt extension:txt',
]


def prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories, owners = BASE_PRIOR()
    for version in (13, 14, 15, 16):
        root = ROOT.parent / f"cross_project_holdout_v{version}"
        for name in ("frames.json", "sample.json"):
            path = root / name
            if path.exists():
                engine.record_repositories(json.loads(path.read_text()), repositories)
    return repositories, owners | {repository.split("/", 1)[0] for repository in repositories}


def main() -> dict[str, object]:
    engine.ROOT = ROOT
    engine.SEED = SEED
    engine.QUERIES = QUERIES
    engine.SELECTED_PER_FRAME = 3
    engine.EVALUATOR_COMMIT = "00e14dd2d8b646dd12ed77e5833e891fb3ca634b"
    engine.EVALUATOR_VERSION = "0.29.0"
    engine.prior_repositories_and_owners = prior_repositories_and_owners
    result = engine.retrieve()
    for name, schema in (
        ("frames.json", "reprocheck.cross-project-frames.v17"),
        ("sample.json", "reprocheck.cross-project-sample.v17"),
    ):
        path = ROOT / name
        payload = json.loads(path.read_text())
        payload["schema_version"] = schema
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
