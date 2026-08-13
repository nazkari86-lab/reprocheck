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
    print("PASS: v3 frozen labels, 2 cases, 32 claims, and 4 immutable sources verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
