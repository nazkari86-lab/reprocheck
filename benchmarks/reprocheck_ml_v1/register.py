from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import register_ml_protocol


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "benchmarks" / "reprocheck_ml_v1"
FROZEN = [
    BENCHMARK / name
    for name in (
        "protocol.json",
        "source-frame.json",
        "exclusions.json",
        "protocol.md",
        "annotation-guide.md",
        "model-card.md",
        "split.py",
        "train.py",
        "calibrate.py",
        "evaluate.py",
        "acquire.py",
        "annotate.py",
        "register.py",
        "verify-registration.py",
        "schema/registration-v1.schema.json",
    )
] + [
    ROOT / name
    for name in (
        "pyproject.toml",
        "uv.lock",
        "src/reprocheck/ml_acquisition.py",
        "src/reprocheck/ml_baselines.py",
        "src/reprocheck/ml_calibration.py",
        "src/reprocheck/ml_contracts.py",
        "src/reprocheck/ml_dataset.py",
        "src/reprocheck/ml_decision.py",
        "src/reprocheck/ml_evaluation.py",
        "src/reprocheck/ml_extraction.py",
        "src/reprocheck/ml_features.py",
        "src/reprocheck/ml_registration.py",
        "src/reprocheck/ml_reporting.py",
        "src/reprocheck/ml_retrieval.py",
        "src/reprocheck/ml_split.py",
        "src/reprocheck/ml_transformer.py",
    )
]

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = register_ml_protocol(ROOT, FROZEN, args.output)
print(result["registration_sha256"])
