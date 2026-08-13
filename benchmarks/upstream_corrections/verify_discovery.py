from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def verify() -> dict[str, int]:
    snapshot = json.loads((ROOT / "discovery_snapshot.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    results = snapshot["results"]
    case_ids = {case["id"] for case in manifest["corrections"]}
    included = [result for result in results if result["decision"] == "include"]

    assert snapshot["returned_results"] == len(results)
    assert [result["rank"] for result in results] == list(range(1, len(results) + 1))
    assert len({(result["repository"], result["pull_request"]) for result in results}) == len(
        results
    )
    assert all(result["decision"] in {"include", "exclude"} for result in results)
    assert all(result.get("reason") for result in results if result["decision"] == "exclude")
    assert all(result.get("case_id") in case_ids for result in included)
    assert len({result["case_id"] for result in included}) == len(included)
    return {
        "results": len(results),
        "included": len(included),
        "excluded": len(results) - len(included),
    }


def main() -> int:
    summary = verify()
    print(
        f"PASS: discovery snapshot results={summary['results']} "
        f"included={summary['included']} excluded={summary['excluded']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
