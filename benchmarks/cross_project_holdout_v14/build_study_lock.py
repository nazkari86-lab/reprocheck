from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    fixed = [
        "registration.json",
        "protocol.md",
        "retrieve.py",
        "evaluate.py",
        "verify_registration.py",
        "build_labels.py",
        "labels.json",
        "frames.json",
        "sample.json",
        "../cross_project_holdout_v13/metric-policy.json",
        "../cross_project_holdout_v13/retrieve.py",
        "../cross_project_holdout_v13/evaluate.py",
        "../../src/reprocheck/claims.py",
        "../../src/reprocheck/metric_names.py",
    ]
    generated = [
        str(path.relative_to(ROOT))
        for directory in (ROOT / "raw", ROOT / "sources")
        for path in sorted(directory.iterdir())
        if path.is_file()
    ]
    files = fixed + generated
    lock = {
        "schema_version": "reprocheck.cross-project-study-lock.v14",
        "status": "sources_and_labels_frozen_before_evaluation",
        "extractor_commit": "f7fe35a20d55fa48ab35c388645557ac4804efaa",
        "extractor_version": "0.27.0",
        "reviewed_documents": 47,
        "eligible_documents": 25,
        "selected_claims": 218,
        "immutable_files": {relative: digest(ROOT / relative) for relative in files},
    }
    (ROOT / "study.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
