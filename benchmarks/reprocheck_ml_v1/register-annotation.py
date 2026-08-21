from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import register_ml_protocol


ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "benchmarks/reprocheck_ml_v1/annotation-sampling-v1.json",
    "benchmarks/reprocheck_ml_v1/annotation-guide.md",
    "benchmarks/reprocheck_ml_v1/prepare-annotation.py",
    "benchmarks/reprocheck_ml_v1/register-annotation.py",
    "benchmarks/reprocheck_ml_v1/data/materialized-development-v1/corpus.json",
    "benchmarks/reprocheck_ml_v1/data/materialized-development-v1/materialization.json",
    "src/reprocheck/ml_annotation_packet.py",
    "src/reprocheck/ml_extraction.py",
    "src/reprocheck/ml_registration.py",
]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = register_ml_protocol(ROOT, [ROOT / name for name in FILES], args.output)
print(result["registration_sha256"])
