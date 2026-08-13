from __future__ import annotations

import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13 import retrieve as engine


ROOT = Path(__file__).resolve().parent
BASE_PRIOR = engine.prior_repositories_and_owners
SEED = "reprocheck-cross-project-v16-portable-results"
QUERIES = [
    '"accuracy" filename:RESULTS.md extension:md',
    '"precision" "recall" filename:RESULTS.md extension:md',
    '"latency" filename:RESULTS.md extension:md',
    '"throughput" filename:RESULTS.md extension:md',
    '"accuracy" filename:BENCHMARK.md extension:md',
    '"latency" filename:BENCHMARK.md extension:md',
    '"throughput" filename:BENCHMARK.md extension:md',
    '"accuracy" filename:PERFORMANCE.md extension:md',
    '"runtime" filename:PERFORMANCE.md extension:md',
    '"precision" "recall" filename:PERFORMANCE.md extension:md',
    '"accuracy" filename:METRICS.md extension:md',
    '"F1" filename:METRICS.md extension:md',
    '"latency" filename:METRICS.md extension:md',
    '"accuracy" filename:EXPERIMENTS.md extension:md',
    '"RMSE" filename:EXPERIMENTS.md extension:md',
    '"runtime" filename:EXPERIMENTS.md extension:md',
    '"accuracy" path:benchmark extension:md',
    '"precision" "recall" path:benchmark extension:md',
    '"latency" "throughput" path:benchmark extension:md',
    '"accuracy" path:results extension:md',
    '"F1" path:results extension:md',
    '"runtime" path:results extension:md',
    '"accuracy" path:evaluation extension:md',
    '"mAP" "IoU" path:evaluation extension:md',
    '"BLEU" "ROUGE" path:evaluation extension:md',
    '"accuracy" filename:results.txt extension:txt',
    '"latency" filename:results.txt extension:txt',
    '"throughput" filename:results.txt extension:txt',
    '"benchmark" filename:metrics.txt extension:txt',
    '"runtime" filename:metrics.txt extension:txt',
]


def prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories, owners = BASE_PRIOR()
    for version in (13, 14, 15):
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
        ("frames.json", "reprocheck.cross-project-frames.v16"),
        ("sample.json", "reprocheck.cross-project-sample.v16"),
    ):
        path = ROOT / name
        payload = json.loads(path.read_text())
        payload["schema_version"] = schema
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
