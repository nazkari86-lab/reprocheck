from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    raw = json.loads((ROOT / "raw_evidence_verification.json").read_text(encoding="utf-8"))
    zero_path = ROOT / "results" / "zero-shot-0.20.0.json"
    zero = json.loads(zero_path.read_text(encoding="utf-8"))
    result_lock = json.loads((ROOT / "results.lock.json").read_text(encoding="utf-8"))
    assert labels["eligibility_blinded_to_parser_output"] is True
    assert labels["sample_size"] == sample["sample_size"] == 250
    assert len(labels["labels"]) == 250
    assert [label["rank"] for label in labels["labels"]] == list(range(1, 251))
    assert len(cases["cases"]) == 6
    assert sum(len(case["claims"]) for case in cases["cases"]) == 96
    assert raw["uses_reprocheck_parser"] is False
    assert raw["summary"] == {
        "agreement_rate": 1.0,
        "cases_verified": 3,
        "cases_with_raw_evidence": 3,
    }
    assert sha256(zero_path) == result_lock["zero_shot_result"]["sha256"]
    assert (
        sha256(ROOT / result_lock["frozen_evaluator_wheel"]["path"])
        == result_lock["frozen_evaluator_wheel"]["sha256"]
    )
    assert zero["runtime_evaluator_version"] == "0.20.0"
    assert zero["eligible_cases"] == 6 and zero["visible_cases"] == 0
    assert zero["selected_claims"] == 96 and zero["visible_claims"] == 3
    development_path = ROOT / "results" / "development-current.json"
    development_lock_path = ROOT / "development.lock.json"
    if development_lock_path.exists():
        development = json.loads(development_path.read_text(encoding="utf-8"))
        development_lock = json.loads(development_lock_path.read_text(encoding="utf-8"))
        assert sha256(development_path) == development_lock["development_result"]["sha256"]
        assert development["runtime_evaluator_version"] == "0.21.0"
        assert development["eligible_cases"] == development["visible_cases"] == 6
        assert development["selected_claims"] == development["visible_claims"] == 93
        assert development["originally_selected_claims"] == 96
        assert development["adjudicated_invalid_claims"] == 3
        assert development["independently_frozen_raw_evidence_cases"] == 3
        assert development["raw_evidence_agreement_rate"] == 1.0
        assert (
            development["development_implementation_commit"]
            == development_lock["implementation_commit"]
        )
    print("PASS: v4 sample=250 eligible=6 zero-shot=0/6 cases, 3/96 claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
