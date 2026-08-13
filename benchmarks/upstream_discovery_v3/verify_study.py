from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_name(case_id: str, path: str, phase: str) -> str:
    suffix = Path(path).suffix or ".txt"
    return f"{case_id}--{path.replace('/', '__')}.{phase}{suffix}"


def main() -> int:
    labels = json.loads((ROOT / "labels.json").read_text(encoding="utf-8"))
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    assert labels["eligibility_blinded_to_parser_output"] is True
    assert labels["sample_size"] == sample["sample_size"] == 150
    assert len(labels["labels"]) == 150
    assert [label["rank"] for label in labels["labels"]] == list(range(1, 151))
    eligible = [label for label in labels["labels"] if label["eligible"]]
    assert {label["case_id"] for label in eligible} == {case["id"] for case in cases["cases"]}
    assert cases["evaluator_commit"] == "7e5a6c087fc6f5e5df14ccde1c8436049c39c5b7"
    expected_files: set[str] = set()
    claim_count = 0
    for case in cases["cases"]:
        for path in case["files"]:
            for phase in ("before", "after"):
                filename = source_name(case["id"], path, phase)
                expected_files.add(filename)
                source = ROOT / "sources" / filename
                assert source.is_file()
                assert sha256(source) == lock["files"][filename]["sha256"]
        for claim in case["claims"]:
            before = ROOT / "sources" / source_name(case["id"], claim["file"], "before")
            after = ROOT / "sources" / source_name(case["id"], claim["file"], "after")
            assert before.read_text(encoding="utf-8").count(claim["before_snippet"]) == 1
            assert after.read_text(encoding="utf-8").count(claim["after_snippet"]) == 1
            assert claim["before_value"] != claim["after_value"]
            claim_count += 1
    assert expected_files == set(lock["files"])
    assert len(eligible) == len(cases["cases"]) == 2
    assert claim_count == 32
    zero_path = ROOT / "results" / "zero-shot-0.19.0.json"
    zero = json.loads(zero_path.read_text(encoding="utf-8"))
    results_lock = json.loads((ROOT / "results.lock.json").read_text(encoding="utf-8"))
    assert sha256(zero_path) == results_lock["zero_shot_result"]["sha256"]
    assert (
        sha256(ROOT / results_lock["frozen_evaluator_wheel"]["path"])
        == results_lock["frozen_evaluator_wheel"]["sha256"]
    )
    assert zero["runtime_evaluator_version"] == "0.19.0"
    assert zero["eligible_cases"] == 2 and zero["visible_cases"] == 0
    assert zero["selected_claims"] == 32 and zero["visible_claims"] == 0
    assert zero["source_integrity"] is True
    development_path = ROOT / "results" / "development-current.json"
    development_lock_path = ROOT / "development.lock.json"
    if development_lock_path.exists():
        development = json.loads(development_path.read_text(encoding="utf-8"))
        development_lock = json.loads(development_lock_path.read_text(encoding="utf-8"))
        assert sha256(development_path) == development_lock["development_result"]["sha256"]
        assert development["runtime_evaluator_version"] == "0.20.0"
        assert development["eligible_cases"] == development["visible_cases"] == 2
        assert development["selected_claims"] == development["visible_claims"] == 32
        assert development["source_integrity"] is True
        assert development["protocol_sha256"] == zero["protocol_sha256"]
        assert development["sample_sha256"] == zero["sample_sha256"]
        assert development["labels_sha256"] == zero["labels_sha256"]
        assert development["cases_sha256"] == zero["cases_sha256"]
        assert development["sources_lock_sha256"] == zero["sources_lock_sha256"]
        assert (
            development["development_implementation_commit"]
            == development_lock["implementation_commit"]
        )
    print("PASS: v3 sample=150 eligible=2 zero-shot=0/2 cases, 0/32 claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
