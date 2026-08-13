from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).parents[1] / "benchmarks" / "cross_project_holdout_v14"


def test_v14_frozen_zero_shot_result_remains_immutable():
    result = ROOT / "results" / "zero-shot-0.27.0.json"
    assert hashlib.sha256(result.read_bytes()).hexdigest() == (
        "757a7a0cd09a8b3aec24bdcac676e684a21812c6f7c2c9647bab8841d8814489"
    )
