from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "benchmarks/cross_project_holdout_v15/results/zero-shot-0.28.0.json"


def test_v15_zero_shot_result_is_frozen_and_negative() -> None:
    assert hashlib.sha256(RESULT.read_bytes()).hexdigest() == (
        "eb7d3ea149673c5c46d5ce896dac305c0a3ae8456c5144f3c86e97dbb44c6b84"
    )
    result = json.loads(RESULT.read_text())
    assert result["eligible_documents"] == 30
    assert result["gold_claims"] == 220
    assert result["true_positive"] == 145
    assert result["predicted_claims"] == 224
    assert result["exact_documents"] == 8
    assert result["success"] is False
