from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FILES = [
    "README.md",
    "protocol.md",
    "registration.json",
    "retrieve.py",
    "collect_details.py",
    "collect_details_graphql.py",
    "resume_collect_details.py",
    "build_review_packet.py",
    "frames.json",
    "sample.json",
    "details.json.gz",
    "review_packet.json",
    "source_plan.json",
    "sources.lock.json",
    "labels.json",
    "cases.json",
    "evaluate.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(missing)
    payload = {
        "schema_version": "reprocheck.upstream-discovery-study-lock.v8",
        "status": "labels-and-sources-frozen-before-evaluation",
        "extractor_commit": "6238f2c",
        "extractor_version": "0.23.0",
        "sha256": {name: sha256(ROOT / name) for name in FILES},
    }
    (ROOT / "study.lock.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: froze {len(FILES)} v8 study artifacts before evaluation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
