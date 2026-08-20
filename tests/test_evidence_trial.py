from __future__ import annotations

import json
import importlib.util
import base64
import hashlib
from pathlib import Path

import pytest

from reprocheck.evidence_trial import (
    build_trial_sample,
    canonical_digest,
    load_trial_protocol,
    lock_trial_gold,
    prepare_trial_review,
    register_evidence_trial,
    score_evidence_trial,
    score_certificate_track,
    validate_trial_sample,
    verify_evidence_trial_registration,
)
from reprocheck.audit import run_audit
from reprocheck.witness import build_witness_file


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


def _candidate_enrollment(tmp_path: Path) -> tuple[Path, Path, Path]:
    source = tmp_path / "sources" / "candidate-001.txt"
    source.parent.mkdir(parents=True)
    source.write_text("Accuracy: 90%\n", encoding="utf-8")
    source_bytes = source.read_bytes()
    manifest = {
        "schema_version": "reprocheck.evidence-trial-candidates.v1",
        "status": "acquired_unreviewed",
        "config_sha256": "c" * 64,
        "completed_event_ids": ["search-01"],
        "frame_count": 1,
        "candidate_count": 1,
        "independent_owner_count": 1,
        "owner_cap": 1,
        "frames": [{"event_id": "search-01"}],
        "response_descriptors": [],
        "candidates": [
            {
                "candidate_id": "candidate-001",
                "frame": "search-01",
                "owner": "new-owner",
                "repository": "new-owner/repo",
                "default_branch": "main",
                "path": "RESULTS.md",
                "commit": "a" * 40,
                "blob_sha": "b" * 40,
                "indexed_blob_sha": "d" * 40,
                "immutable_url": "https://github.com/new-owner/repo/blob/" + "a" * 40 + "/RESULTS.md",
                "api_url": "https://api.github.com/repos/new-owner/repo/contents/RESULTS.md?ref=" + "a" * 40,
                "source_file": "sources/candidate-001.txt",
                "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "source_bytes": len(source_bytes),
                "selection_digest": "e" * 64,
            }
        ],
        "candidate_manifest_sha256": "",
    }
    manifest["candidate_manifest_sha256"] = canonical_digest(
        manifest, blank_field="candidate_manifest_sha256"
    )
    manifest_path = _dump(tmp_path / "candidates.json", manifest)
    enrollment = {
        "schema_version": "reprocheck.evidence-trial-enrollment.v1",
        "curator_id": "independent-curator-1",
        "independent_from_evaluator": True,
        "candidate_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "claims": [
            {
                "claim_id": "claim-001",
                "candidate_id": "candidate-001",
                "block": {"start": 1, "end": 1},
                "claim_text": "Accuracy: 90%",
                "declared_metric": "accuracy",
                "declared_value": 0.9,
                "stratum": "natural_unadjudicated",
                "evidence_tier": "report_only",
            }
        ],
    }
    enrollment_path = _dump(tmp_path / "enrollment.json", enrollment)
    return manifest_path, enrollment_path, source


def test_build_trial_sample_binds_source_only_enrollment(tmp_path: Path):
    manifest, enrollment, _ = _candidate_enrollment(tmp_path)
    output = tmp_path / "sample.json"
    result = build_trial_sample(manifest, enrollment, output)
    assert result["claims"][0]["stratum"] == "natural_unadjudicated"
    assert "gold_status" not in result["claims"][0]
    assert result["sample_sha256"] == canonical_digest(result, blank_field="sample_sha256")
    with pytest.raises(ValueError, match="immutable"):
        build_trial_sample(manifest, enrollment, output)


def test_build_trial_sample_rejects_tampering_and_unknown_candidates(tmp_path: Path):
    manifest, enrollment, source = _candidate_enrollment(tmp_path)
    source.write_text("Accuracy: 99%\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source bytes"):
        build_trial_sample(manifest, enrollment, tmp_path / "tampered.json")
    source.write_text("Accuracy: 90%\n", encoding="utf-8")
    payload = json.loads(enrollment.read_text(encoding="utf-8"))
    payload["claims"][0]["candidate_id"] = "candidate-999"
    _dump(enrollment, payload)
    with pytest.raises(ValueError, match="unknown candidate"):
        build_trial_sample(manifest, enrollment, tmp_path / "unknown.json")


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


def test_sample_gate_separates_enrollment_from_post_gold_information(tmp_path: Path):
    protocol = _protocol(
        tmp_path / "protocol.json",
        {
            "repository_owners": 2,
            "claims": 4,
            "contradicted_claims": 2,
            "not_verifiable_claims": 2,
            "supported_evidence_claims": 2,
        },
    )
    claims = _claims()
    for claim in claims:
        claim.pop("gold_status", None)
        claim.pop("gold_rationale", None)
    sample = _dump(
        tmp_path / "sample.json",
        {"schema_version": "reprocheck.evidence-trial-sample.v1", "claims": claims},
    )
    result = validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})
    assert result["status"] == "eligible_for_blinded_review"
    assert result["gold_status_available"] is False
    assert result["information_shortfalls"] == {}


def _review(path: Path, reviewer: str, statuses: list[str], packet: Path) -> Path:
    return _dump(
        path,
        {
            "schema_version": "reprocheck.evidence-trial-review.v1",
            "reviewer_id": reviewer,
            "independent": True,
            "packet_sha256": hashlib.sha256(packet.read_bytes()).hexdigest(),
            "reviews": [
                {
                    "claim_id": f"claim-{index}",
                    "status": status,
                    "rationale": f"review evidence for claim {index}",
                    "evidence_refs": [f"source:line-{index}"],
                }
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
    assert not (review_dir / "private").exists()
    statuses = [item["gold_status"] for item in _claims()]
    packet_path = review_dir / "public" / "packet.json"
    first = _review(tmp_path / "r1.json", "r1", statuses, packet_path)
    second_statuses = statuses.copy()
    second_statuses[0] = "supported"
    second = _review(tmp_path / "r2.json", "r2", second_statuses, packet_path)
    with pytest.raises(ValueError, match="adjudication"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")
    adjudication = _dump(
        tmp_path / "adjudication.json",
        {
            "adjudications": [
                {
                    "claim_id": "claim-1",
                    "status": "contradicted",
                    "rationale": "raw metric conflicts with report",
                    "evidence_refs": ["metrics.json:accuracy"],
                }
            ]
        },
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
    packet_path = review_dir / "public" / "packet.json"
    first = _review(tmp_path / "r1.json", "r1", statuses, packet_path)
    second = _review(tmp_path / "r2.json", "r2", statuses, packet_path)
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
    search_url = "https://api.example.org/search"
    repository_url = "https://api.example.org/repos/new-owner/repo"
    commit_url = f"{repository_url}/commits/main"
    content_url = f"{repository_url}/contents/RESULTS.md?ref={'a' * 40}"
    config = {
        "schema_version": "reprocheck.evidence-trial-source-config.v2",
        "salt": "fixture",
        "limits": {
            "per_response_bytes": 10_000,
            "global_bytes": 100_000,
            "maximum_source_bytes": 1_000,
            "timeout_seconds": 1,
        },
        "selection": {"selected_per_frame": 1, "maximum_candidates": 1, "owner_cap": 1},
        "events": [{"event_id": "search-01", "url": search_url}],
    }
    responses = {
        search_url: json.dumps(
            {
                "total_count": 1,
                "items": [
                    {
                        "path": "RESULTS.md",
                        "sha": "b" * 40,
                        "repository": {
                            "full_name": "new-owner/repo",
                            "url": repository_url,
                            "default_branch": "main",
                        },
                    }
                ],
            }
        ).encode(),
        repository_url: json.dumps({"default_branch": "main"}).encode(),
        commit_url: json.dumps({"sha": "a" * 40}).encode(),
        content_url: json.dumps(
            {
                "sha": "c" * 40,
                "content": base64.b64encode(b"Accuracy: 90%\n").decode()[:8]
                + "\n"
                + base64.b64encode(b"Accuracy: 90%\n").decode()[8:],
            }
        ).encode(),
    }
    calls: list[str] = []

    def fetch(url: str) -> bytes:
        calls.append(url)
        return responses[url]

    first = module.acquire(config, tmp_path / "first", fetch)
    assert len(calls) == 4
    assert module.acquire(config, tmp_path / "first", fetch) == first
    assert len(calls) == 4
    second = module.acquire(config, tmp_path / "second", fetch)
    assert first.read_bytes() == second.read_bytes()
    manifest = json.loads(first.read_text(encoding="utf-8"))
    assert manifest["candidate_count"] == 1
    assert manifest["independent_owner_count"] == 1
    assert manifest["candidates"][0]["commit"] == "a" * 40
    assert manifest["candidates"][0]["source_sha256"]


def test_v19_acquisition_preserves_failure_and_reuses_frozen_search(tmp_path: Path):
    path = Path("benchmarks/evidence_trial_v19/acquire.py")
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_failure", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    search_url = "https://api.example.org/search"
    repository_url = "https://api.example.org/repos/new-owner/repo"
    config = {
        "schema_version": "reprocheck.evidence-trial-source-config.v2",
        "salt": "fixture",
        "limits": {
            "per_response_bytes": 10_000,
            "global_bytes": 100_000,
            "maximum_source_bytes": 1_000,
            "timeout_seconds": 1,
        },
        "selection": {"selected_per_frame": 1, "maximum_candidates": 1, "owner_cap": 1},
        "events": [{"event_id": "search-01", "url": search_url}],
    }
    search = json.dumps(
        {
            "total_count": 1,
            "items": [
                {
                    "path": "RESULTS.md",
                    "sha": "b" * 40,
                    "repository": {
                        "full_name": "new-owner/repo",
                        "url": repository_url,
                        "default_branch": "main",
                    },
                }
            ],
        }
    ).encode()
    search_calls = 0

    def fail_after_search(url: str) -> bytes:
        nonlocal search_calls
        if url == search_url:
            search_calls += 1
            return search
        raise RuntimeError("fixture outage")

    with pytest.raises(RuntimeError, match="fixture outage"):
        module.acquire(config, tmp_path / "failed", fail_after_search)
    failure = json.loads(
        (tmp_path / "failed" / "failures" / "failure-001.json").read_text(encoding="utf-8")
    )
    assert failure["error_type"] == "RuntimeError"
    assert failure["retry_permitted"] is True
    with pytest.raises(RuntimeError, match="fixture outage"):
        module.acquire(config, tmp_path / "failed", fail_after_search)
    assert search_calls == 1
    assert (tmp_path / "failed" / "failures" / "failure-002.json").is_file()


def test_v19_transport_validation_rejects_truncation_and_malformed_json():
    path = Path("benchmarks/evidence_trial_v19/acquire.py")
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_transport", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._validate_transport_json(b'{"ok":true}', 100, "11")
    with pytest.raises(ValueError, match="shorter"):
        module._validate_transport_json(b'{"ok":true}', 100, "12")
    with pytest.raises(ValueError, match="complete UTF-8 JSON"):
        module._validate_transport_json(b'{"cut":', 100)
    with pytest.raises(ValueError, match="must be an object"):
        module._validate_transport_json(b"[]", 100)


def _certificate_track_cases(tmp_path: Path) -> list[dict]:
    cases = []
    tamper_classes = [
        "node",
        "edge",
        "numeric_value",
        "artifact_byte",
        "context",
        "tolerance",
        "mandatory_relation",
        "non_minimal",
        "cross_case_swap",
    ]
    for index in range(2):
        root = tmp_path / f"case-{index}"
        root.mkdir()
        report = root / "report.md"
        metrics = root / "metrics.json"
        certificate = root / "certificate.json"
        witness = root / "witness.json"
        report.write_text(f"Accuracy: {80 + index}%\n", encoding="utf-8")
        metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
        audit = run_audit(report_path=report, metrics_path=metrics)
        certificate.write_text(json.dumps(audit.to_dict()), encoding="utf-8")
        build_witness_file(certificate, 0, witness, root)
        tampered = root / "tampered.json"
        payload = json.loads(witness.read_text(encoding="utf-8"))
        payload["rule_inputs"]["observed"] = 0.1
        tampered.write_text(json.dumps(payload), encoding="utf-8")
        cases.append(
            {
                "case_id": f"case-{index}",
                "certificate": str(certificate),
                "certificate_sha256": hashlib.sha256(certificate.read_bytes()).hexdigest(),
                "witness": str(witness),
                "artifact_dir": str(root),
                "certificate_verdict": "contradicted",
                "witness_verdict": "contradicted",
                "tampered": [
                    {"path": str(tampered), "kind": "witness", "tamper_class": name}
                    for name in (tamper_classes if index == 0 else [])
                ],
            }
        )
    return cases


def test_certificate_track_binds_verdicts_and_all_registered_tamper_classes(tmp_path: Path):
    result = score_certificate_track(_certificate_track_cases(tmp_path))
    assert result["verdict_preservation_rate"] == 1.0
    assert result["tamper_rejection_rate"] == 1.0
    assert set(result["tamper_by_class"]) == {
        "node",
        "edge",
        "numeric_value",
        "artifact_byte",
        "context",
        "tolerance",
        "mandatory_relation",
        "non_minimal",
        "cross_case_swap",
    }


def test_certificate_track_rejects_cross_case_witness_swap(tmp_path: Path):
    cases = _certificate_track_cases(tmp_path)
    cases[0]["witness"], cases[1]["witness"] = cases[1]["witness"], cases[0]["witness"]
    with pytest.raises(ValueError, match="binding"):
        score_certificate_track(cases)
