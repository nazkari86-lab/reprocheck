from __future__ import annotations

import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13 import retrieve as engine


ROOT = Path(__file__).resolve().parent
BASE_PRIOR = engine.prior_repositories_and_owners
SEED = "reprocheck-cross-project-v15-supported-ontology"
QUERIES = [
    '"accuracy" filename:EVALUATION_RESULTS.md extension:md',
    '"precision" "recall" filename:EVALUATION_RESULTS.md extension:md',
    '"latency" filename:EVALUATION_RESULTS.md extension:md',
    '"accuracy" filename:BENCHMARK_RESULTS.md extension:md',
    '"latency" "throughput" filename:BENCHMARK_RESULTS.md extension:md',
    '"runtime" filename:BENCHMARK_RESULTS.md extension:md',
    '"accuracy" filename:PERFORMANCE_RESULTS.md extension:md',
    '"F1" filename:PERFORMANCE_RESULTS.md extension:md',
    '"latency" filename:PERFORMANCE_RESULTS.md extension:md',
    '"accuracy" filename:EXPERIMENT_RESULTS.md extension:md',
    '"RMSE" filename:EXPERIMENT_RESULTS.md extension:md',
    '"runtime" filename:EXPERIMENT_RESULTS.md extension:md',
    '"accuracy" filename:RESULTS.txt extension:txt',
    '"precision" "recall" filename:RESULTS.txt extension:txt',
    '"latency" filename:RESULTS.txt extension:txt',
    '"benchmark" filename:BENCHMARK.txt extension:txt',
    '"runtime" filename:BENCHMARK.txt extension:txt',
    '"throughput" filename:BENCHMARK.txt extension:txt',
    '"accuracy" filename:REPORT.txt extension:txt',
    '"F1" filename:REPORT.txt extension:txt',
    '"runtime" filename:REPORT.txt extension:txt',
    '"accuracy" path:reports extension:md',
    '"precision" "recall" path:reports extension:md',
    '"latency" "throughput" path:reports extension:md',
    '"RMSE" "MAE" path:reports extension:md',
    '"mAP" "IoU" path:reports extension:md',
    '"BLEU" "ROUGE" path:reports extension:md',
    '"accuracy" path:performance extension:md',
    '"latency" path:performance extension:md',
    '"benchmark results" path:experiments extension:md',
]


def prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories, owners = BASE_PRIOR()
    for version in (13, 14):
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
    engine.EVALUATOR_COMMIT = "76614583ae8676ba6ed309b43ca8865e707d8c4e"
    engine.EVALUATOR_VERSION = "0.28.0"
    engine.prior_repositories_and_owners = prior_repositories_and_owners
    result = engine.retrieve()
    for name, schema in (
        ("frames.json", "reprocheck.cross-project-frames.v15"),
        ("sample.json", "reprocheck.cross-project-sample.v15"),
    ):
        path = ROOT / name
        payload = json.loads(path.read_text())
        payload["schema_version"] = schema
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
