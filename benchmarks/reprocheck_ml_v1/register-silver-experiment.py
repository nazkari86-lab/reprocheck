from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import register_ml_protocol


ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "benchmarks/reprocheck_ml_v1/silver-experiment-v1.json",
    "benchmarks/reprocheck_ml_v1/run-silver-experiment.py",
    "benchmarks/reprocheck_ml_v1/data/materialized-development-v1/corpus.json",
    "benchmarks/reprocheck_ml_v1/data/annotation-packets-v1/coordinator-mapping.json",
    "src/reprocheck/ml_silver_experiment.py",
    "src/reprocheck/ml_baselines.py",
    "src/reprocheck/ml_features.py",
    "src/reprocheck/ml_split.py",
]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = register_ml_protocol(ROOT, [ROOT / name for name in FILES], args.output)
print(result["registration_sha256"])
