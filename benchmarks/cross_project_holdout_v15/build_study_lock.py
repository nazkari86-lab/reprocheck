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
        "supported-ontology.json",
        "retrieve.py",
        "evaluate.py",
        "verify_registration.py",
        "build_labels.py",
        "labels.json",
        "frames.json",
        "sample.json",
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
        "schema_version": "reprocheck.cross-project-study-lock.v15",
        "status": "sources_and_labels_frozen_before_evaluation",
        "extractor_commit": "76614583ae8676ba6ed309b43ca8865e707d8c4e",
        "extractor_version": "0.28.0",
        "reviewed_documents": 37,
        "eligible_documents": 30,
        "selected_claims": 220,
        "immutable_files": {relative: digest(ROOT / relative) for relative in files},
    }
    (ROOT / "study.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
