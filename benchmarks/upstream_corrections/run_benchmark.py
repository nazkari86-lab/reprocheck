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


def _raw_evidence_value(path: Path, key: str) -> float:
    values: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        payload = json.loads(line)
        if key in payload:
            values.append(float(payload[key]))
    if not values:
        raise ValueError(f"raw evidence key is missing: {path.name}/{key}")
    return values[-1]


def run(output: Path) -> dict[str, Any]:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    discovery_path = ROOT / "discovery_snapshot.json"
    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    cases: list[dict[str, Any]] = []
    for correction in manifest["corrections"]:
        before_path = (
            ROOT / "sources" / f"{correction['id']}.before{Path(correction['path']).suffix}"
        )
        after_path = ROOT / "sources" / f"{correction['id']}.after{Path(correction['path']).suffix}"
        source_paths = [before_path, after_path]
        evidence_descriptor = correction.get("raw_evidence")
        evidence_suffix = evidence_descriptor.get("suffix", ".jsonl") if evidence_descriptor else ""
        evidence_path = ROOT / "sources" / f"{correction['id']}.evidence{evidence_suffix}"
        if evidence_descriptor:
            source_paths.append(evidence_path)
        integrity = all(
            _sha256(path) == lock["files"][path.name]["sha256"] for path in source_paths
        )
        before_text = before_path.read_text(encoding="utf-8")
        after_text = after_path.read_text(encoding="utf-8")
        change_results: list[dict[str, Any]] = []
        for change in correction["changes"]:
            count = int(change["count"])
            old_before = before_text.count(change["before"])
            old_after = after_text.count(change["before"])
            new_before = before_text.count(change["after"])
            new_after = after_text.count(change["after"])
            before_claims = _matching_claims(before_text, change["before"], change["before_claim"])
            after_claims = _matching_claims(after_text, change["after"], change["after_claim"])
            change_results.append(
                {
                    "selected_records": count,
                    "before_only_count": old_before,
                    "after_only_count": new_after,
                    "before_claims_extracted": len(before_claims),
                    "after_claims_extracted": len(after_claims),
                    "passed": (
                        old_before == count
                        and old_after == 0
                        and new_before == 0
                        and new_after == count
                        and len(before_claims) == count
                        and len(after_claims) == count
                    ),
                }
            )
        affected = sum(change["selected_records"] for change in change_results)
        parser_detected = all(change["passed"] for change in change_results)
        evidence_verified: bool | None = None
        evidence_value: float | None = None
        if evidence_descriptor:
            if evidence_descriptor.get("format", "jsonl") == "claim":
                evidence_claims = _matching_claims(
                    evidence_path.read_text(encoding="utf-8"),
                    evidence_descriptor["snippet"],
                    evidence_descriptor["claim"],
                )
                if len(evidence_claims) != 1:
                    raise ValueError(
                        f"raw evidence claim count is {len(evidence_claims)}: {evidence_path.name}"
                    )
                evidence_value = float(evidence_claims[0].value)
            else:
                evidence_value = _raw_evidence_value(evidence_path, evidence_descriptor["json_key"])
            expected_value = float(evidence_descriptor["expected_value"])
            corrected_claim_value = float(
                evidence_descriptor.get("corrected_claim_value", expected_value)
            )
            tolerance = float(evidence_descriptor.get("tolerance", 1e-12))
            corrected_values = {
                float(change["after_claim"]["value"])
                for change in correction["changes"]
                if "value" in change["after_claim"]
            }
            evidence_verified = (
                abs(evidence_value - expected_value) <= tolerance
                and corrected_claim_value in corrected_values
                and abs(evidence_value - corrected_claim_value) <= tolerance
            )
        passed = integrity and parser_detected and evidence_verified is not False
        cases.append(
            {
                "id": correction["id"],
                "repository": correction["repository"],
                "pull_request": correction["pull_request"],
                "kind": correction["kind"],
                "affected_records": affected,
                "source_integrity": integrity,
                "changes": change_results,
                "reprocheck_parser_detected": parser_detected,
                "raw_evidence_value": evidence_value,
                "raw_evidence_verified": evidence_verified,
                "passed": passed,
            }
        )
    result = {
        "schema_version": "reprocheck.upstream-corrections-result.v1",
        "manifest_sha256": _sha256(ROOT / "manifest.json"),
        "discovery_snapshot_sha256": _sha256(discovery_path),
        "discovery_cohort": {
            "results": len(discovery["results"]),
            "included": sum(item["decision"] == "include" for item in discovery["results"]),
            "excluded": sum(item["decision"] == "exclude" for item in discovery["results"]),
        },
        "independent_corrections": len(cases),
        "repositories": len({case["repository"] for case in cases}),
        "organizations": len({case["repository"].split("/", 1)[0] for case in cases}),
        "selected_claims": sum(case["affected_records"] for case in cases),
        "affected_records": sum(case["affected_records"] for case in cases),
        "verified_corrections": sum(case["passed"] for case in cases),
        "source_integrity_rate": sum(case["source_integrity"] for case in cases) / len(cases),
        "parser_detection_rate": sum(case["reprocheck_parser_detected"] for case in cases)
        / len(cases),
        "raw_evidence_cases": sum(case["raw_evidence_verified"] is not None for case in cases),
        "raw_evidence_verified": sum(case["raw_evidence_verified"] is True for case in cases),
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
        f"{result['selected_claims']} selected corrected claims"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
