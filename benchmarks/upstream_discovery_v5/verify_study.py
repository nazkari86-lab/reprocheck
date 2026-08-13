from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    lock = json.loads((ROOT / "results.lock.json").read_text(encoding="utf-8"))
    frozen = ROOT / lock["result"]
    assert sha256(frozen) == lock["sha256"]
    for key, filename in (
        ("protocol_sha256", "protocol.md"),
        ("sample_sha256", "sample.json"),
        ("labels_sha256", "labels.json"),
        ("cases_sha256", "cases.json"),
        ("sources_lock_sha256", "sources.lock.json"),
    ):
        assert sha256(ROOT / filename) == lock[key]
    zero = json.loads(frozen.read_text(encoding="utf-8"))
    development = json.loads(
        (ROOT / "results" / "development-current.json").read_text(encoding="utf-8")
    )
    assert zero["phase"] == "zero-shot-frozen-0.21.0"
    assert (zero["visible_cases"], zero["eligible_cases"]) == (0, 11)
    assert (zero["visible_claims"], zero["selected_claims"]) == (0, 34)
    assert development["phase"] == "development-post-inspection"
    assert development["source_integrity"]
    assert (development["visible_cases"], development["eligible_cases"]) == (11, 11)
    assert (development["visible_claims"], development["selected_claims"]) == (34, 34)
    print("PASS: v5 lock valid; zero-shot 0/11, 0/34; development 11/11, 34/34")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
