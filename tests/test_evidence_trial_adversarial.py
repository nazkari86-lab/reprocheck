from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from reprocheck.evidence_trial import (
    _load_predictions,
    _owner_bootstrap_delta,
    _quantile,
    _recall,
    _score_arm,
    build_trial_sample,
    canonical_digest,
    lock_trial_gold,
    prepare_trial_review,
    score_certificate_track,
    score_evidence_trial,
    validate_trial_sample,
    verify_evidence_trial_registration,
)

from test_evidence_trial import (
    _arm,
    _candidate_enrollment,
    _certificate_track_cases,
    _claims,
    _dump,
    _protocol,
    _registration,
    _review,
    _sample,
)


def _rewrite(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _gold_pipeline(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, _ = _registration(tmp_path, protocol)
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    prepare_trial_review(sample, review_dir)
    statuses = [item["gold_status"] for item in _claims()]
    packet = review_dir / "public" / "packet.json"
    first = _review(tmp_path / "r1.json", "r1", statuses, packet)
    second = _review(tmp_path / "r2.json", "r2", statuses, packet)
    gold = tmp_path / "gold.json"
    lock_trial_gold(review_dir, [first, second], None, gold)
    arms = {
        name: _arm(tmp_path / f"{name}.json", name, statuses)
        for name in ("report_only", "supplied_metrics", "raw_recomputation")
    }
    return protocol, registration, gold, arms


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "bad", "unsupported"),
        ("status", "retrieved", "registered_not_retrieved"),
        ("source_contents_inspected_after_registration", True, "not pristine"),
    ],
)
def test_registration_verifier_rejects_state_tampering(
    tmp_path: Path, field: str, value, message: str
):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(tmp_path, protocol)
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload[field] = value
    payload["registration_sha256"] = canonical_digest(payload, blank_field="registration_sha256")
    _rewrite(registration, payload)
    assert any(
        message in error
        for error in verify_evidence_trial_registration(
            registration, protocol=protocol, **artifacts
        )
    )


def test_registration_verifier_reports_malformed_and_missing_inputs(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(tmp_path, protocol)
    registration.write_text("[]\n", encoding="utf-8")
    assert (
        "JSON object"
        in verify_evidence_trial_registration(registration, protocol=protocol, **artifacts)[0]
    )
    registration, artifacts = _registration(
        tmp_path / "second", _protocol(tmp_path / "second/p.json")
    )
    artifacts["evaluator"].unlink()
    errors = verify_evidence_trial_registration(
        registration, protocol=tmp_path / "second/p.json", **artifacts
    )
    assert any("registered evaluator is missing" in error for error in errors)


def test_registration_verifier_reports_all_descriptor_corruption(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(tmp_path, protocol)
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload["protocol"] = {}
    payload["artifacts"] = []
    payload["registration_sha256"] = canonical_digest(payload, blank_field="registration_sha256")
    _rewrite(registration, payload)
    errors = verify_evidence_trial_registration(registration, protocol=protocol, **artifacts)
    assert "protocol checksum or size does not match" in errors
    assert "registration artifacts must be an object" in errors


def test_registration_verifier_reports_checksum_and_missing_protocol(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(tmp_path, protocol)
    payload = json.loads(registration.read_text(encoding="utf-8"))
    payload["registration_sha256"] = "0" * 64
    _rewrite(registration, payload)
    assert any(
        "checksum" in error
        for error in verify_evidence_trial_registration(
            registration, protocol=protocol, **artifacts
        )
    )
    protocol.unlink()
    assert (
        "cannot be read"
        in verify_evidence_trial_registration(registration, protocol=protocol, **artifacts)[0]
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "object"),
        ({"owners": [1], "files": []}, "owners"),
        ({"owners": [], "files": [1]}, "files"),
    ],
)
def test_sample_gate_rejects_invalid_exclusion_objects(tmp_path: Path, payload, message: str):
    with pytest.raises(ValueError, match=message):
        validate_trial_sample(
            _sample(tmp_path / "sample.json"),
            _protocol(tmp_path / "protocol.json"),
            exclusions=payload,
        )


def test_sample_gate_rejects_invalid_exclusion_file_lock(tmp_path: Path):
    sample = _sample(tmp_path / "sample.json")
    protocol = _protocol(tmp_path / "protocol.json")
    exclusions = _dump(tmp_path / "exclusions.json", {"owners": [], "files": []})
    with pytest.raises(ValueError, match="unsupported"):
        validate_trial_sample(sample, protocol, exclusions=exclusions)
    payload = {
        "schema_version": "reprocheck.evidence-trial-exclusions.v1",
        "owners": [],
        "files": [],
        "union_sha256": "0" * 64,
    }
    _rewrite(exclusions, payload)
    with pytest.raises(ValueError, match="digest"):
        validate_trial_sample(sample, protocol, exclusions=exclusions)


def test_sample_gate_rejects_file_duplicate_and_checksum_tamper(tmp_path: Path):
    protocol = _protocol(tmp_path / "protocol.json")
    sample = _sample(tmp_path / "sample.json")
    identity = "owner-a:repo-1:results/1.json"
    with pytest.raises(ValueError, match="excluded file"):
        validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": [identity]})
    payload = json.loads(sample.read_text(encoding="utf-8"))
    payload["claims"][1]["claim_id"] = payload["claims"][0]["claim_id"]
    _rewrite(sample, payload)
    with pytest.raises(ValueError, match="unique"):
        validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})
    payload["claims"][1]["claim_id"] = "claim-2"
    payload["sample_sha256"] = "0" * 64
    _rewrite(sample, payload)
    with pytest.raises(ValueError, match="checksum"):
        validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})


def test_sample_gate_reaches_post_gold_statuses(tmp_path: Path):
    claims = _claims()
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
    sample = _dump(
        tmp_path / "sample.json",
        {"schema_version": "reprocheck.evidence-trial-sample.v1", "claims": claims},
    )
    assert (
        validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})["status"]
        == "insufficient_information"
    )
    protocol = _protocol(
        tmp_path / "eligible.json",
        {
            "repository_owners": 2,
            "claims": 4,
            "contradicted_claims": 1,
            "not_verifiable_claims": 1,
            "supported_evidence_claims": 1,
        },
    )
    assert (
        validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})["status"]
        == "eligible"
    )


def test_build_sample_rejects_manifest_and_enrollment_rebinding(tmp_path: Path):
    manifest, enrollment, _ = _candidate_enrollment(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["candidate_count"] = 2
    payload["candidate_manifest_sha256"] = canonical_digest(
        payload, blank_field="candidate_manifest_sha256"
    )
    _rewrite(manifest, payload)
    enrolled = json.loads(enrollment.read_text(encoding="utf-8"))
    enrolled["candidate_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _rewrite(enrollment, enrolled)
    with pytest.raises(ValueError, match="count"):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")
    payload["candidate_count"] = 1
    payload["candidate_manifest_sha256"] = canonical_digest(
        payload, blank_field="candidate_manifest_sha256"
    )
    _rewrite(manifest, payload)
    with pytest.raises(ValueError, match="different candidate manifest"):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")


def test_build_sample_rejects_duplicate_candidates_and_claims(tmp_path: Path):
    manifest, enrollment, _ = _candidate_enrollment(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    duplicate = {**payload["candidates"][0], "owner": "another-owner"}
    payload["candidates"].append(duplicate)
    payload["candidate_count"] = 2
    payload["independent_owner_count"] = 2
    payload["candidate_manifest_sha256"] = canonical_digest(
        payload, blank_field="candidate_manifest_sha256"
    )
    _rewrite(manifest, payload)
    enrolled = json.loads(enrollment.read_text(encoding="utf-8"))
    enrolled["candidate_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _rewrite(enrollment, enrolled)
    with pytest.raises(ValueError, match="candidate IDs"):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")
    payload["candidates"] = payload["candidates"][:1]
    payload["candidate_count"] = payload["independent_owner_count"] = 1
    payload["candidate_manifest_sha256"] = canonical_digest(
        payload, blank_field="candidate_manifest_sha256"
    )
    _rewrite(manifest, payload)
    enrolled["candidate_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    enrolled["claims"].append(dict(enrolled["claims"][0]))
    _rewrite(enrollment, enrolled)
    with pytest.raises(ValueError, match="claim IDs"):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("digest", "checksum"),
        ("owner", "one-candidate-per-owner"),
        ("frames", "frame count"),
    ],
)
def test_build_sample_rejects_candidate_manifest_invariants(
    tmp_path: Path, mutation: str, message: str
):
    manifest, enrollment, _ = _candidate_enrollment(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if mutation == "digest":
        payload["candidate_manifest_sha256"] = "0" * 64
    elif mutation == "owner":
        payload["independent_owner_count"] = 0
        payload["candidate_manifest_sha256"] = canonical_digest(
            payload, blank_field="candidate_manifest_sha256"
        )
    else:
        payload["frame_count"] = 2
        payload["candidate_manifest_sha256"] = canonical_digest(
            payload, blank_field="candidate_manifest_sha256"
        )
    _rewrite(manifest, payload)
    enrolled = json.loads(enrollment.read_text(encoding="utf-8"))
    enrolled["candidate_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _rewrite(enrollment, enrolled)
    with pytest.raises(ValueError, match=message):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")


def test_build_sample_rejects_non_utf8_source(tmp_path: Path):
    manifest, enrollment, source = _candidate_enrollment(tmp_path)
    source.write_bytes(b"\xff")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["candidates"][0]["source_sha256"] = hashlib.sha256(b"\xff").hexdigest()
    payload["candidates"][0]["source_bytes"] = 1
    payload["candidate_manifest_sha256"] = canonical_digest(
        payload, blank_field="candidate_manifest_sha256"
    )
    _rewrite(manifest, payload)
    enrolled = json.loads(enrollment.read_text(encoding="utf-8"))
    enrolled["candidate_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _rewrite(enrollment, enrolled)
    with pytest.raises(ValueError, match="not UTF-8"):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")


@pytest.mark.parametrize(
    ("block", "text", "message"),
    [
        ({"start": 2, "end": 2}, "Accuracy: 90%", "outside source"),
        ({"start": 1, "end": 1}, "Accuracy: 91%", "does not match"),
    ],
)
def test_build_sample_rejects_invalid_source_spans(
    tmp_path: Path, block: dict, text: str, message: str
):
    manifest, enrollment, _ = _candidate_enrollment(tmp_path)
    payload = json.loads(enrollment.read_text(encoding="utf-8"))
    payload["claims"][0]["block"] = block
    payload["claims"][0]["claim_text"] = text
    _rewrite(enrollment, payload)
    with pytest.raises(ValueError, match=message):
        build_trial_sample(manifest, enrollment, tmp_path / "sample.json")


def test_review_lock_rejects_packet_and_reviewer_identity_tampering(tmp_path: Path):
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    prepare_trial_review(sample, review_dir)
    with pytest.raises(ValueError, match="empty"):
        prepare_trial_review(sample, review_dir)
    packet = review_dir / "public" / "packet.json"
    statuses = [item["gold_status"] for item in _claims()]
    first = _review(tmp_path / "r1.json", "same", statuses, packet)
    second = _review(tmp_path / "r2.json", "same", statuses, packet)
    with pytest.raises(ValueError, match="distinct"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")
    payload = json.loads(second.read_text(encoding="utf-8"))
    payload["reviewer_id"] = "other"
    payload["packet_sha256"] = "0" * 64
    _rewrite(second, payload)
    with pytest.raises(ValueError, match="different blinded packet"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")
    with pytest.raises(ValueError, match="exactly two"):
        lock_trial_gold(review_dir, [first], None, tmp_path / "gold.json")


def test_review_lock_rejects_manifest_and_claim_set_tampering(tmp_path: Path):
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    prepare_trial_review(sample, review_dir)
    packet = review_dir / "public" / "packet.json"
    statuses = [item["gold_status"] for item in _claims()]
    first = _review(tmp_path / "r1.json", "r1", statuses, packet)
    second = _review(tmp_path / "r2.json", "r2", statuses, packet)
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["reviews"].pop()
    _rewrite(first, payload)
    with pytest.raises(ValueError, match="every claim"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")
    manifest = json.loads((review_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest["packet"] = {}
    _rewrite(review_dir / "manifest.json", manifest)
    with pytest.raises(ValueError, match="manifest"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")


def test_review_rejects_duplicate_claim_rows_and_sample_checksum(tmp_path: Path):
    sample = _sample(tmp_path / "sample.json")
    payload = json.loads(sample.read_text(encoding="utf-8"))
    payload["sample_sha256"] = "0" * 64
    _rewrite(sample, payload)
    with pytest.raises(ValueError, match="checksum"):
        prepare_trial_review(sample, tmp_path / "review")
    sample = _sample(tmp_path / "sample2.json")
    review_dir = tmp_path / "review2"
    prepare_trial_review(sample, review_dir)
    packet = review_dir / "public" / "packet.json"
    statuses = [item["gold_status"] for item in _claims()]
    first = _review(tmp_path / "r1.json", "r1", statuses, packet)
    second = _review(tmp_path / "r2.json", "r2", statuses, packet)
    review = json.loads(first.read_text(encoding="utf-8"))
    review["reviews"][1]["claim_id"] = review["reviews"][0]["claim_id"]
    _rewrite(first, review)
    with pytest.raises(ValueError, match="exactly once"):
        lock_trial_gold(review_dir, [first, second], None, tmp_path / "gold.json")


def test_adjudication_rejects_duplicate_and_extra_rows(tmp_path: Path):
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    prepare_trial_review(sample, review_dir)
    packet = review_dir / "public" / "packet.json"
    statuses = [item["gold_status"] for item in _claims()]
    first = _review(tmp_path / "r1.json", "r1", statuses, packet)
    changed = statuses.copy()
    changed[0] = "supported"
    second = _review(tmp_path / "r2.json", "r2", changed, packet)
    row = {
        "claim_id": "claim-1",
        "status": "contradicted",
        "rationale": "evidence",
        "evidence_refs": ["source:1"],
    }
    adjudication = _dump(tmp_path / "a.json", {"adjudications": [row, row]})
    with pytest.raises(ValueError, match="unique"):
        lock_trial_gold(review_dir, [first, second], adjudication, tmp_path / "gold.json")
    _rewrite(adjudication, {"adjudications": [row, {**row, "claim_id": "claim-2"}]})
    with pytest.raises(ValueError, match="only and every"):
        lock_trial_gold(review_dir, [first, second], adjudication, tmp_path / "gold.json")
    _rewrite(adjudication, {"adjudications": [{**row, "rationale": ""}]})
    with pytest.raises(ValueError, match="resolve every"):
        lock_trial_gold(review_dir, [first, second], adjudication, tmp_path / "gold.json")
    _rewrite(adjudication, {})
    with pytest.raises(ValueError, match="rows are missing"):
        lock_trial_gold(review_dir, [first, second], adjudication, tmp_path / "gold.json")


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("bootstrap", "positive"),
        ("arms", "three registered arms"),
        ("gold_checksum", "gold lock checksum"),
        ("adjudication", "adjudication-complete"),
        ("registration_checksum", "registration checksum"),
        ("prediction_ids", "exactly the gold claim IDs"),
    ],
)
def test_scoring_rejects_invalid_frozen_inputs(tmp_path: Path, target: str, message: str):
    protocol, registration, gold, arms = _gold_pipeline(tmp_path)
    samples = 20
    if target == "bootstrap":
        samples = 0
    elif target == "arms":
        arms.pop("report_only")
    elif target == "gold_checksum":
        payload = json.loads(gold.read_text(encoding="utf-8"))
        payload["raw_agreement"] = 0.5
        _rewrite(gold, payload)
    elif target == "adjudication":
        payload = json.loads(gold.read_text(encoding="utf-8"))
        payload["adjudication_complete"] = False
        payload["gold_sha256"] = canonical_digest(payload, blank_field="gold_sha256")
        _rewrite(gold, payload)
    elif target == "registration_checksum":
        payload = json.loads(registration.read_text(encoding="utf-8"))
        payload["status"] = "bad"
        _rewrite(registration, payload)
    else:
        payload = json.loads(arms["report_only"].read_text(encoding="utf-8"))
        payload["predictions"].pop()
        _rewrite(arms["report_only"], payload)
    with pytest.raises(ValueError, match=message):
        score_evidence_trial(
            gold_path=gold,
            arm_paths=arms,
            protocol_path=protocol,
            registration_path=registration,
            bootstrap_samples=samples,
        )


def test_scoring_rejects_protocol_gold_and_arm_structure_tampering(tmp_path: Path):
    protocol, registration, gold, arms = _gold_pipeline(tmp_path)
    protocol_payload = json.loads(protocol.read_text(encoding="utf-8"))
    protocol_payload["title"] = "Changed"
    _rewrite(protocol, protocol_payload)
    with pytest.raises(ValueError, match="protocol does not match"):
        score_evidence_trial(
            gold_path=gold,
            arm_paths=arms,
            protocol_path=protocol,
            registration_path=registration,
            bootstrap_samples=10,
        )


@pytest.mark.parametrize(
    ("claims", "message"),
    [({}, "array of objects"), ([{"claim_id": "x"}, {"claim_id": "x"}], "unique")],
)
def test_scoring_rejects_malformed_gold_claims(tmp_path: Path, claims, message: str):
    protocol, registration, gold, arms = _gold_pipeline(tmp_path)
    payload = json.loads(gold.read_text(encoding="utf-8"))
    payload["claims"] = claims
    payload["gold_sha256"] = canonical_digest(payload, blank_field="gold_sha256")
    _rewrite(gold, payload)
    with pytest.raises(ValueError, match=message):
        score_evidence_trial(
            gold_path=gold,
            arm_paths=arms,
            protocol_path=protocol,
            registration_path=registration,
            bootstrap_samples=10,
        )


def test_scoring_records_false_accusation_gate(tmp_path: Path):
    protocol, registration, gold, arms = _gold_pipeline(tmp_path)
    payload = json.loads(arms["raw_recomputation"].read_text(encoding="utf-8"))
    payload["predictions"][1]["status"] = "contradicted"
    _rewrite(arms["raw_recomputation"], payload)
    result = score_evidence_trial(
        gold_path=gold,
        arm_paths=arms,
        protocol_path=protocol,
        registration_path=registration,
        bootstrap_samples=10,
    )
    assert "false_accusation_rate" in result["primary_analysis"]["failed_gates"]
    protocol = _protocol(tmp_path / "protocol.json")
    registration, _ = _registration(tmp_path / "fresh", _protocol(tmp_path / "fresh/p.json"))
    with pytest.raises(ValueError, match="protocol does not match"):
        score_evidence_trial(
            gold_path=gold,
            arm_paths=arms,
            protocol_path=protocol,
            registration_path=registration,
            bootstrap_samples=10,
        )


def test_scoring_helpers_fail_closed_on_invalid_inputs(tmp_path: Path):
    with pytest.raises(ValueError, match="every gold claim"):
        _score_arm({"one": {"gold_status": "supported"}}, {})
    with pytest.raises(ValueError, match="invalid tri-state"):
        _score_arm({"one": {"gold_status": "supported"}}, {"one": "maybe"})
    assert _recall([], "report_only") == 0.0
    assert _owner_bootstrap_delta([], 2, 19) == [0.0, 0.0]
    assert _quantile([], 0.5) == 0.0
    assert _quantile([1.0], 0.5) == 1.0
    arm = _arm(tmp_path / "arm.json", "report_only", ["supported", "supported"])
    payload = json.loads(arm.read_text(encoding="utf-8"))
    payload["arm"] = "supplied_metrics"
    _rewrite(arm, payload)
    with pytest.raises(ValueError, match="declared arm"):
        _load_predictions(arm, "report_only")
    payload["arm"] = "report_only"
    payload["predictions"][1]["claim_id"] = payload["predictions"][0]["claim_id"]
    _rewrite(arm, payload)
    with pytest.raises(ValueError, match="unique"):
        _load_predictions(arm, "report_only")


def test_certificate_track_requires_registered_complete_tamper_set(tmp_path: Path):
    with pytest.raises(ValueError, match="at least one"):
        score_certificate_track([])
    fake = tmp_path / "fake.json"
    fake.write_text("{}", encoding="utf-8")
    case = {
        "case_id": "one",
        "certificate": str(fake),
        "certificate_sha256": hashlib.sha256(fake.read_bytes()).hexdigest(),
        "witness": str(fake),
        "artifact_dir": str(tmp_path),
        "certificate_verdict": "contradicted",
        "witness_verdict": "contradicted",
        "tampered": [],
    }
    with pytest.raises(ValueError, match="verification failed"):
        score_certificate_track([case])


def test_certificate_track_rejects_bad_case_registry(tmp_path: Path):
    cases = _certificate_track_cases(tmp_path)
    cases[1]["case_id"] = cases[0]["case_id"]
    with pytest.raises(ValueError, match="case IDs"):
        score_certificate_track(cases)
    (tmp_path / "digest").mkdir()
    cases = _certificate_track_cases(tmp_path / "digest")
    cases[0]["certificate_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="binding mismatch"):
        score_certificate_track(cases)
    (tmp_path / "class").mkdir()
    cases = _certificate_track_cases(tmp_path / "class")
    cases[0]["tampered"][0]["tamper_class"] = "unknown"
    with pytest.raises(ValueError, match="unregistered"):
        score_certificate_track(cases)
    (tmp_path / "missing").mkdir()
    cases = _certificate_track_cases(tmp_path / "missing")
    cases[0]["tampered"] = cases[0]["tampered"][:-1]
    with pytest.raises(ValueError, match="missing tamper classes"):
        score_certificate_track(cases)
