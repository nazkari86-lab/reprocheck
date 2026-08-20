from __future__ import annotations

import json
import importlib.util
from pathlib import Path

import pytest

from reprocheck.evidence_trial import (
    canonical_digest,
    load_trial_protocol,
    lock_trial_gold,
    prepare_trial_review,
    register_evidence_trial,
    score_evidence_trial,
    validate_trial_sample,
    verify_evidence_trial_registration,
)


def _dump(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _protocol_payload(minimum: dict | None = None) -> dict:
    return {
        "schema_version": "reprocheck.evidence-trial-protocol.v1",
        "title": "Evidence Trial",
        "research_question": "Does recomputation improve contradiction detection?",
        "hypotheses": {"h1": "Raw recomputation improves recall."},
        "arms": ["report_only", "supplied_metrics", "raw_recomputation"],
        "minimum_information": minimum
        or {
            "repository_owners": 2,
            "claims": 5,
            "contradicted_claims": 1,
            "not_verifiable_claims": 1,
            "supported_evidence_claims": 1,
        },
        "source_frame": {"unit": "claim", "selection": "deterministic"},
        "annotation": {"reviewers": 2, "labels": 3},
        "primary_outcomes": ["contradiction_recall", "false_accusation_rate"],
        "secondary_outcomes": ["macro_f1"],
        "analysis": {"bootstrap_unit": "repository_owner", "seed": 19},
        "success_gate": {
            "minimum_contradiction_recall_delta": 0.1,
            "maximum_false_accusation_rate": 0.05,
        },
        "scientific_boundary": "One preregistered external claim sample; no universal claim.",
    }


def _protocol(path: Path, minimum: dict | None = None) -> Path:
    return _dump(path, _protocol_payload(minimum))


def _claims() -> list[dict]:
    statuses = ["contradicted", "supported", "not_verifiable", "supported", "supported"]
    strata = [
        "natural_correction",
        "natural_supported_control",
        "natural_not_verifiable",
        "unchanged_negative_control",
        "controlled_mutation",
    ]
    rows = []
    for index, (status, stratum) in enumerate(zip(statuses, strata, strict=True), start=1):
        rows.append(
            {
                "claim_id": f"claim-{index}",
                "owner": "owner-a" if index < 3 else "owner-b",
                "repository": f"repo-{index}",
                "url": f"https://example.org/repo-{index}/file",
                "commit": f"{index:x}" * 40,
                "path": f"results/{index}.json",
                "sha256": f"{index:x}" * 64,
                "block": {"start": index, "end": index},
                "stratum": stratum,
                "evidence_tier": "raw_recomputation" if index != 3 else "report_only",
                "gold_status": status,
                "gold_rationale": "fixture",
            }
        )
    return rows


def _sample(path: Path) -> Path:
    return _dump(
        path,
        {"schema_version": "reprocheck.evidence-trial-sample.v1", "claims": _claims()},
    )


def _registration(tmp_path: Path, protocol: Path) -> tuple[Path, dict[str, Path]]:
    artifacts = {}
    for name in ("evaluator", "acquisition", "source_config", "analysis", "exclusions"):
        artifacts[name] = tmp_path / name
        artifacts[name].write_text(name, encoding="utf-8")
    output = tmp_path / "registration.json"
    register_evidence_trial(protocol=protocol, output=output, **artifacts)
    return output, artifacts


def test_trial_protocol_is_strict_and_rejects_placeholders(tmp_path: Path):
    path = _protocol(tmp_path / "protocol.json")
    assert load_trial_protocol(path)["minimum_information"]["repository_owners"] == 2
    payload = _protocol_payload()
    payload["title"] = "UNRESOLVED"
    _dump(path, payload)
    with pytest.raises(ValueError, match="placeholder"):
        load_trial_protocol(path)
    payload = _protocol_payload()
    payload.pop("hypotheses")
    _dump(path, payload)
    with pytest.raises(ValueError, match="required property"):
        load_trial_protocol(path)


def test_registration_is_immutable_and_detects_every_artifact_tamper(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(tmp_path, protocol)
    assert verify_evidence_trial_registration(registration, protocol=protocol, **artifacts) == []
    with pytest.raises(ValueError, match="immutable"):
        register_evidence_trial(protocol=protocol, output=registration, **artifacts)
    artifacts["analysis"].write_text("changed", encoding="utf-8")
    assert "analysis checksum or size does not match" in verify_evidence_trial_registration(
        registration, protocol=protocol, **artifacts
    )


def test_sample_gate_uses_natural_claims_and_fails_closed(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    sample = _sample(tmp_path / "sample.json")
    result = validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})
    assert result["status"] == "insufficient_sample"
    assert result["counts"]["claims"] == 4
    with pytest.raises(ValueError, match="excluded owner"):
        validate_trial_sample(sample, protocol, exclusions={"owners": ["owner-a"], "files": []})


def _review(path: Path, reviewer: str, statuses: list[str]) -> Path:
    return _dump(
        path,
        {
            "schema_version": "reprocheck.evidence-trial-review.v1",
            "reviewer_id": reviewer,
            "independent": True,
            "reviews": [
                {"claim_id": f"claim-{index}", "status": status}
                for index, status in enumerate(statuses, start=1)
            ],
        },
    )


def test_blinded_packet_and_adjudicated_gold_lock(tmp_path: Path):
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    manifest = prepare_trial_review(sample, review_dir)
    packet = json.loads((review_dir / "public" / "packet.json").read_text())
    assert manifest["reviewers_completed"] == 0
    assert all("gold_status" not in item for item in packet["claims"])
    statuses = [item["gold_status"] for item in _claims()]
    first = _review(tmp_path / "r1.json", "r1", statuses)
    second_statuses = statuses.copy()
    second_statuses[0] = "supported"
    second = _review(tmp_path / "r2.json", "r2", second_statuses)
    with pytest.raises(ValueError, match="adjudication"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")
    adjudication = _dump(
        tmp_path / "adjudication.json",
        {"adjudications": [{"claim_id": "claim-1", "status": "contradicted"}]},
    )
    locked = lock_trial_gold(review_dir, [first, second], adjudication, tmp_path / "gold.json")
    assert locked["reviewer_count"] == 2
    assert locked["adjudication_complete"] is True


def _arm(path: Path, name: str, statuses: list[str]) -> Path:
    return _dump(
        path,
        {
            "schema_version": "reprocheck.evidence-trial-arm.v1",
            "arm": name,
            "predictions": [
                {"claim_id": f"claim-{index}", "status": status}
                for index, status in enumerate(statuses, start=1)
            ],
        },
    )


def test_trial_scoring_is_deterministic_and_separates_controlled_mutations(tmp_path: Path):
    protocol = _protocol(
        tmp_path / "protocol.json",
        {
            "repository_owners": 2,
            "claims": 4,
            "contradicted_claims": 1,
            "not_verifiable_claims": 1,
            "supported_evidence_claims": 1,
        },
    )
    registration, _ = _registration(tmp_path, protocol)
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    prepare_trial_review(sample, review_dir)
    statuses = [item["gold_status"] for item in _claims()]
    first = _review(tmp_path / "r1.json", "r1", statuses)
    second = _review(tmp_path / "r2.json", "r2", statuses)
    gold = tmp_path / "gold.json"
    lock_trial_gold(review_dir, [first, second], None, gold)
    report = ["supported", "supported", "supported", "supported", "supported"]
    supplied = ["supported", "supported", "not_verifiable", "supported", "supported"]
    arms = {
        "report_only": _arm(tmp_path / "report.json", "report_only", report),
        "supplied_metrics": _arm(tmp_path / "supplied.json", "supplied_metrics", supplied),
        "raw_recomputation": _arm(tmp_path / "raw.json", "raw_recomputation", statuses),
    }
    first_result = score_evidence_trial(
        gold_path=gold,
        arm_paths=arms,
        protocol_path=protocol,
        registration_path=registration,
        bootstrap_samples=200,
    )
    second_result = score_evidence_trial(
        gold_path=gold,
        arm_paths=arms,
        protocol_path=protocol,
        registration_path=registration,
        bootstrap_samples=200,
    )
    assert canonical_digest(first_result) == canonical_digest(second_result)
    assert first_result["arms"]["raw_recomputation"]["contradiction_recall"] == 1.0
    assert first_result["arms"]["report_only"]["contradiction_recall"] == 0.0
    assert first_result["controlled_mutation"]["claims"] == 1


def test_v19_protocol_and_exclusions_reconstruct_from_prior_samples():
    root = Path("benchmarks/evidence_trial_v19")
    protocol = load_trial_protocol(root / "protocol.json")
    assert protocol["minimum_information"]["claims"] == 150
    exclusions = json.loads((root / "exclusions.json").read_text(encoding="utf-8"))
    expected_owners = set()
    expected_files = set()
    for relative in exclusions["generated_from"]:
        path = Path(relative)
        if path.name != "sample.json":
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for sample in payload.get("samples", []):
            repository = sample["repository"]
            owner = sample.get("owner", repository.split("/", 1)[0])
            expected_owners.add(owner.casefold())
            if sample.get("path"):
                expected_files.add(f"{owner}:{repository}:{sample['path']}")
    assert {owner.casefold() for owner in exclusions["owners"]} == expected_owners
    assert set(exclusions["files"]) == expected_files
    assert exclusions["union_sha256"] == canonical_digest(exclusions, blank_field="union_sha256")


def test_v19_acquisition_resume_is_deterministic_without_network(tmp_path: Path):
    path = Path("benchmarks/evidence_trial_v19/acquire.py")
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_acquire", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = {
        "limits": {"per_response_bytes": 100, "global_bytes": 200},
        "events": [
            {"event_id": "b", "url": "https://example.org/b"},
            {"event_id": "a", "url": "https://example.org/a"},
        ],
    }
    first = module.acquire(config, tmp_path / "first", lambda url: url.encode())
    second = module.acquire(config, tmp_path / "second", lambda url: url.encode())
    assert first.read_bytes() == second.read_bytes()
    assert module.acquire(config, tmp_path / "first", lambda url: url.encode()) == first
