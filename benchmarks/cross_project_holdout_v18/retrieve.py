from __future__ import annotations

import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13 import retrieve as engine


ROOT = Path(__file__).resolve().parent
BASE_PRIOR = engine.prior_repositories_and_owners
SEED = "reprocheck-cross-project-v18-single-metric-result-documents"
QUERIES = [
    '"accuracy" filename:RESULTS.md extension:md',
    '"precision" filename:RESULTS.md extension:md',
    '"recall" filename:RESULTS.md extension:md',
    '"f1" filename:RESULTS.md extension:md',
    '"rmse" filename:RESULTS.md extension:md',
    '"mae" filename:RESULTS.md extension:md',
    '"latency" filename:RESULTS.md extension:md',
    '"throughput" filename:RESULTS.md extension:md',
    '"accuracy" filename:BENCHMARK.md extension:md',
    '"precision" filename:BENCHMARK.md extension:md',
    '"recall" filename:BENCHMARK.md extension:md',
    '"f1" filename:BENCHMARK.md extension:md',
    '"latency" filename:BENCHMARK.md extension:md',
    '"throughput" filename:BENCHMARK.md extension:md',
    '"accuracy" filename:EXPERIMENTS.md extension:md',
    '"precision" filename:EXPERIMENTS.md extension:md',
    '"f1" filename:EXPERIMENTS.md extension:md',
    '"rmse" filename:EXPERIMENTS.md extension:md',
    '"accuracy" filename:METRICS.md extension:md',
    '"precision" filename:METRICS.md extension:md',
    '"f1" filename:METRICS.md extension:md',
    '"latency" filename:METRICS.md extension:md',
    '"accuracy" path:results extension:md',
    '"precision" path:results extension:md',
    '"f1" path:results extension:md',
    '"rmse" path:results extension:md',
    '"latency" path:benchmark extension:md',
    '"throughput" path:benchmark extension:md',
    '"accuracy" filename:results.txt extension:txt',
    '"precision" filename:results.txt extension:txt',
]


def prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories, owners = BASE_PRIOR()
    for version in (13, 14, 15, 16, 17):
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
        ("frames.json", "reprocheck.cross-project-frames.v18"),
        ("sample.json", "reprocheck.cross-project-sample.v18"),
    ):
        path = ROOT / name
        payload = json.loads(path.read_text())
        payload["schema_version"] = schema
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
