from __future__ import annotations

import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13 import retrieve as engine


ROOT = Path(__file__).resolve().parent
SEED = "reprocheck-cross-project-v14-result-files"
BASE_PRIOR = engine.prior_repositories_and_owners
QUERIES = [
    '"benchmark results" filename:RESULTS.md extension:md',
    '"performance results" filename:RESULTS.md extension:md',
    '"evaluation results" filename:RESULTS.md extension:md',
    '"accuracy" "F1" filename:RESULTS.md extension:md',
    '"latency" "throughput" filename:RESULTS.md extension:md',
    '"benchmark" filename:RESULT.md extension:md',
    '"performance" filename:RESULT.md extension:md',
    '"accuracy" filename:RESULT.md extension:md',
    '"latency" filename:RESULT.md extension:md',
    '"benchmark results" filename:BENCHMARKS.md extension:md',
    '"performance" filename:BENCHMARKS.md extension:md',
    '"latency" filename:BENCHMARKS.md extension:md',
    '"throughput" filename:BENCHMARKS.md extension:md',
    '"experimental results" filename:EXPERIMENTS.md extension:md',
    '"evaluation" filename:EXPERIMENTS.md extension:md',
    '"results" filename:REPORT.md extension:md',
    '"benchmark" filename:REPORT.md extension:md',
    '"accuracy" filename:REPORT.md extension:md',
    '"results" filename:METRICS.md extension:md',
    '"accuracy" filename:METRICS.md extension:md',
    '"latency" filename:METRICS.md extension:md',
    '"benchmark" path:results extension:md',
    '"evaluation" path:results extension:md',
    '"accuracy" path:results extension:md',
    '"latency" path:results extension:md',
    '"benchmark" path:benchmarks extension:md',
    '"performance results" path:benchmarks extension:md',
    '"requests/sec" path:benchmarks extension:md',
    '"accuracy" path:evaluation extension:md',
    '"evaluation metrics" path:evaluation extension:md',
]


def prior_repositories_and_owners() -> tuple[set[str], set[str]]:
    repositories, owners = BASE_PRIOR()
    for name in ("frames.json", "sample.json"):
        path = ROOT.parent / "cross_project_holdout_v13" / name
        if path.exists():
            engine.record_repositories(json.loads(path.read_text(encoding="utf-8")), repositories)
    return repositories, owners | {repository.split("/", 1)[0] for repository in repositories}


def main() -> dict[str, object]:
    engine.ROOT = ROOT
    engine.SEED = SEED
    engine.QUERIES = QUERIES
    engine.SELECTED_PER_FRAME = 3
    engine.EVALUATOR_COMMIT = "f7fe35a20d55fa48ab35c388645557ac4804efaa"
    engine.EVALUATOR_VERSION = "0.27.0"
    engine.prior_repositories_and_owners = prior_repositories_and_owners
    result = engine.retrieve()
    frames_path = ROOT / "frames.json"
    frames = json.loads(frames_path.read_text(encoding="utf-8"))
    frames["schema_version"] = "reprocheck.cross-project-frames.v14"
    frames_path.write_text(json.dumps(frames, indent=2, sort_keys=True) + "\n")
    sample_path = ROOT / "sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample["schema_version"] = "reprocheck.cross-project-sample.v14"
    sample_path.write_text(json.dumps(sample, indent=2, sort_keys=True) + "\n")
    return result


if __name__ == "__main__":
    print(json.dumps(main(), sort_keys=True))
