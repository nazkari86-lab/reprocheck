from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import register_ml_protocol


ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "benchmarks/reprocheck_ml_v1/registration-v2.json",
    "benchmarks/reprocheck_ml_v1/data/discovery-development-v2.json",
    "benchmarks/reprocheck_ml_v1/materialization-rules-v1.json",
    "benchmarks/reprocheck_ml_v1/acquire.py",
    "benchmarks/reprocheck_ml_v1/materialize.py",
    "benchmarks/reprocheck_ml_v1/register-materialization.py",
    "benchmarks/reprocheck_ml_v1/verify-materialization-registration.py",
    "src/reprocheck/ml_contracts.py",
    "src/reprocheck/ml_materialization.py",
    "src/reprocheck/ml_registration.py",
]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = register_ml_protocol(ROOT, [ROOT / name for name in FILES], args.output)
print(result["registration_sha256"])
