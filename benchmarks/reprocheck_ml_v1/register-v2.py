from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import register_ml_protocol


ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "benchmarks/reprocheck_ml_v1/registration.json",
    "benchmarks/reprocheck_ml_v1/data/discovery-development.json",
    "benchmarks/reprocheck_ml_v1/amendment-001.md",
    "benchmarks/reprocheck_ml_v1/source-frame-v2.json",
    "benchmarks/reprocheck_ml_v1/acquire.py",
    "benchmarks/reprocheck_ml_v1/acquire-v2.py",
    "benchmarks/reprocheck_ml_v1/register-v2.py",
    "benchmarks/reprocheck_ml_v1/verify-registration-v2.py",
    "src/reprocheck/ml_acquisition.py",
    "src/reprocheck/ml_acquisition_v2.py",
    "src/reprocheck/ml_registration.py",
    "pyproject.toml",
    "uv.lock",
]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = register_ml_protocol(ROOT, [ROOT / name for name in FILES], args.output)
print(result["registration_sha256"])
