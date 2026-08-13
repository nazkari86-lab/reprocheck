from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from reprocheck.claims import extract_claims


ROOT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _matching_claims(text: str, snippet: str, expected: dict[str, Any]) -> list[Any]:
    return [
        claim
        for claim in extract_claims(text)
        if snippet.strip() in claim.raw_text
        and claim.metric == expected["metric"]
        and ("value" not in expected or abs(claim.value - float(expected["value"])) < 1e-12)
    ]


def run(output: Path) -> dict[str, Any]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for correction in manifest["corrections"]:
        before_path = (
            ROOT / "sources" / f"{correction['id']}.before{Path(correction['path']).suffix}"
        )
        after_path = ROOT / "sources" / f"{correction['id']}.after{Path(correction['path']).suffix}"
        integrity = all(
            _sha256(path) == lock["files"][path.name]["sha256"]
            for path in (before_path, after_path)
        )
        before_text = before_path.read_text(encoding="utf-8")
        after_text = after_path.read_text(encoding="utf-8")
        affected = int(correction["affected_records"])
        old_before = before_text.count(correction["before"])
        old_after = after_text.count(correction["before"])
        new_before = before_text.count(correction["after"])
        new_after = after_text.count(correction["after"])
        before_claims = _matching_claims(
            before_text, correction["before"], correction["expected_before_claim"]
        )
        after_claims = _matching_claims(
            after_text, correction["after"], correction["expected_after_claim"]
        )
        parser_detected = len(before_claims) == affected and len(after_claims) == affected
        passed = (
            integrity
            and old_before == affected
            and old_after == 0
            and new_before == 0
            and new_after == affected
            and parser_detected
        )
        cases.append(
            {
                "id": correction["id"],
                "repository": correction["repository"],
                "pull_request": correction["pull_request"],
                "kind": correction["kind"],
                "affected_records": affected,
                "source_integrity": integrity,
                "before_only_count": old_before,
                "after_only_count": new_after,
                "before_claims_extracted": len(before_claims),
                "after_claims_extracted": len(after_claims),
                "reprocheck_parser_detected": parser_detected,
                "passed": passed,
            }
        )
    result = {
        "schema_version": "reprocheck.upstream-corrections-result.v1",
        "manifest_sha256": _sha256(ROOT / "manifest.json"),
        "independent_corrections": len(cases),
        "affected_records": sum(case["affected_records"] for case in cases),
        "verified_corrections": sum(case["passed"] for case in cases),
        "source_integrity_rate": sum(case["source_integrity"] for case in cases) / len(cases),
        "parser_detection_rate": sum(case["reprocheck_parser_detected"] for case in cases)
        / len(cases),
        "verification_rate": sum(case["passed"] for case in cases) / len(cases),
        "cases": cases,
        "scientific_boundary": manifest["scientific_boundary"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="verify frozen natural upstream corrections")
    parser.add_argument("--output", type=Path, default=Path("outputs/upstream-corrections.json"))
    args = parser.parse_args()
    result = run(args.output)
    if result["verification_rate"] != 1.0 or result["source_integrity_rate"] != 1.0:
        print("FAIL: upstream correction corpus did not verify")
        return 1
    print(
        f"PASS: {result['verified_corrections']}/{result['independent_corrections']} independent corrections; "
        f"{result['affected_records']} affected records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
