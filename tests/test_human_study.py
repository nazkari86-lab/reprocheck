import json
import stat

from reprocheck.human_study import (
    _descriptor,
    _digest,
    issue_human_study_packet,
    prepare_human_study_master,
    score_human_study,
    verify_human_study_master,
    verify_human_study_public_lock,
)


def _protocol(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "title": "test",
                "design": "crossover",
                "primary_endpoint": "accuracy",
                "secondary_endpoints": [],
                "minimum_participants": 12,
                "approvals_required_before_distribution": True,
                "consent_required": True,
                "analysis_plan": {},
                "scientific_boundary": "controlled",
            }
        ),
        encoding="utf-8",
    )


def test_human_study_prepares_issues_and_scores_without_fake_completion(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    packet_dir = tmp_path / "packet"
    _protocol(protocol)
    manifest = prepare_human_study_master(protocol, master)
    assert manifest["status"] == "prepared_not_approved_not_executed"
    assert manifest["participants_completed"] == 0
    assert verify_human_study_master(master, protocol) == []
    private_paths = [master / "private", *(master / "private").rglob("*")]
    assert all(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0 for path in private_paths)

    packet = issue_human_study_packet(master, "P001", "SRC-2026-001", packet_dir)
    conditions = [item["condition"] for item in packet["assignments"]]
    assert conditions.count("manual") == 4
    assert conditions.count("assisted") == 4
    manual = next(item for item in packet["assignments"] if item["condition"] == "manual")
    assisted = next(item for item in packet["assignments"] if item["condition"] == "assisted")
    assert "audit.json" not in manual["available_files"]
    assert "audit.json" in assisted["available_files"]

    response_path = packet_dir / "response-template.json"
    response = json.loads(response_path.read_text())
    gold = json.loads((master / "private" / "PRIVATE-gold.json").read_text())
    verdicts = {item["case_id"]: item["accepted_verdict"] for item in gold["cases"]}
    response["consent_confirmed"] = True
    response["independent_review_confirmed"] = True
    for answer in response["responses"]:
        answer.update(
            verdict=verdicts[answer["case_id"]],
            duration_seconds=20,
            confidence=4,
            rationale="completed independently",
        )
    response_path.write_text(json.dumps(response), encoding="utf-8")

    result = score_human_study(master, [response_path], tmp_path / "result.json")
    assert result["status"] == "descriptive_only"
    assert result["participant_count"] == 1
    assert result["conditions"]["manual"]["accuracy"] == 1.0
    assert result["conditions"]["assisted"]["accuracy"] == 1.0


def test_public_human_study_lock_verifies_without_private_gold(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)
    (master / "private").rename(tmp_path / "private-hidden")

    assert verify_human_study_public_lock(master, protocol) == []
    assert "private gold" in verify_human_study_master(master, protocol)[0]

    protocol.write_text(protocol.read_text() + "\n", encoding="utf-8")
    assert "human-study protocol checksum or size does not match" in (
        verify_human_study_public_lock(master, protocol)
    )


def test_human_study_refuses_distribution_without_approval_and_unconsented_data(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)

    existing = tmp_path / "existing"
    existing.mkdir()
    try:
        issue_human_study_packet(master, "P000", "SRC-1", existing)
    except ValueError as error:
        assert "already exists" in str(error)
    else:
        raise AssertionError("packet overwrite must fail")
    try:
        issue_human_study_packet(master, "bad code", "SRC-1", tmp_path / "bad-code")
    except ValueError as error:
        assert "participant code" in str(error)
    else:
        raise AssertionError("invalid participant code must fail")

    try:
        issue_human_study_packet(master, "P001", "", tmp_path / "packet")
    except ValueError as error:
        assert "approval" in str(error)
    else:
        raise AssertionError("packet distribution must require approval")

    packet_dir = tmp_path / "approved"
    issue_human_study_packet(master, "P001", "SRC-1", packet_dir)
    try:
        score_human_study(master, [packet_dir / "response-template.json"], tmp_path / "result.json")
    except ValueError as error:
        assert "consent" in str(error)
    else:
        raise AssertionError("unconsented response must fail")

    try:
        score_human_study(master, [], tmp_path / "empty-result.json")
    except ValueError as error:
        assert "at least one" in str(error)
    else:
        raise AssertionError("empty response list must fail")


def test_human_study_master_detects_case_tampering(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)
    report = master / "private" / "cases" / "P1A" / "report.md"
    report.write_text("Accuracy: 1%\n", encoding="utf-8")

    errors = verify_human_study_master(master, protocol)
    assert any("artifact checksum or size mismatch" in error for error in errors)


def test_human_study_master_rejects_public_private_gold(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)
    gold = master / "private" / "PRIVATE-gold.json"
    gold.chmod(0o644)

    errors = verify_human_study_master(master, protocol)
    assert any("accessible by group or other" in error for error in errors)


def test_human_study_score_rejects_packet_or_condition_tampering(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    packet_dir = tmp_path / "packet"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)
    issue_human_study_packet(master, "P001", "SRC-1", packet_dir)
    response_path = packet_dir / "response-template.json"
    response = json.loads(response_path.read_text())
    response["consent_confirmed"] = True
    response["independent_review_confirmed"] = True
    for answer in response["responses"]:
        answer.update(verdict="clean", duration_seconds=10, confidence=3)
    response["responses"][0]["condition"] = (
        "assisted" if response["responses"][0]["condition"] == "manual" else "manual"
    )
    response_path.write_text(json.dumps(response), encoding="utf-8")

    try:
        score_human_study(master, [response_path], tmp_path / "result.json")
    except ValueError as error:
        assert "condition differs" in str(error)
    else:
        raise AssertionError("condition tampering must fail")


def test_human_study_master_and_protocol_fail_closed_branches(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)
    manifest_path = master / "master.json"
    original_manifest = json.loads(manifest_path.read_text())

    payload = dict(original_manifest)
    payload.update(schema_version="bad", status="bad", participants_completed=1)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_human_study_master(master)
    assert "unsupported human-study master schema" in errors
    assert "human-study master has an unexpected status" in errors
    assert "unexecuted human-study master cannot claim completed participants" in errors
    assert "human-study master checksum does not match its payload" in errors

    manifest_path.write_text(json.dumps(original_manifest), encoding="utf-8")
    bad_protocol = tmp_path / "bad-protocol.json"
    bad_protocol.write_text("{}", encoding="utf-8")
    assert any(
        "protocol is missing" in error for error in verify_human_study_master(master, bad_protocol)
    )
    protocol.write_text(protocol.read_text() + " ", encoding="utf-8")
    assert "human-study protocol checksum or size does not match" in verify_human_study_master(
        master, protocol
    )

    gold_path = master / "private" / "PRIVATE-gold.json"
    gold = json.loads(gold_path.read_text())
    gold["cases"] = "bad"
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    manifest = json.loads(manifest_path.read_text())
    manifest["gold"] = _descriptor(gold_path)
    manifest["master_sha256"] = _digest(manifest, "master_sha256")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    assert "human-study case count does not match private gold" in verify_human_study_master(master)


def test_human_study_response_validation_branches(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    packet_dir = tmp_path / "packet"
    _protocol(protocol)
    prepare_human_study_master(protocol, master)
    issue_human_study_packet(master, "P001", "SRC-1", packet_dir)
    response_path = packet_dir / "response-template.json"
    base_response = json.loads(response_path.read_text())
    base_packet = json.loads((packet_dir / "packet.json").read_text())
    base_response["consent_confirmed"] = True
    base_response["independent_review_confirmed"] = True
    for answer in base_response["responses"]:
        answer.update(verdict="clean", duration_seconds=10, confidence=3)

    def rejected(
        response_mutation=None,
        packet_mutation=None,
        *,
        reseal_packet=False,
        rebind_response=False,
    ):
        response = json.loads(json.dumps(base_response))
        packet = json.loads(json.dumps(base_packet))
        if response_mutation:
            response_mutation(response)
        if packet_mutation:
            packet_mutation(packet)
        if reseal_packet:
            packet["packet_sha256"] = _digest(packet, "packet_sha256")
        if rebind_response:
            response["packet_sha256"] = packet["packet_sha256"]
        response_path.write_text(json.dumps(response), encoding="utf-8")
        (packet_dir / "packet.json").write_text(json.dumps(packet), encoding="utf-8")
        try:
            score_human_study(master, [response_path], tmp_path / "never.json")
        except ValueError as error:
            return str(error)
        raise AssertionError("invalid response must fail")

    assert "participant codes" in rejected(lambda item: item.update(participant_code=""))
    assert "unsupported response schema" in rejected(lambda item: item.update(schema_version="bad"))
    assert "consent" in rejected(lambda item: item.update(consent_confirmed=False))
    assert "independent" in rejected(lambda item: item.update(independent_review_confirmed=False))
    assert "packet schema" in rejected(None, lambda item: item.update(schema_version="bad"))
    assert "packet checksum" in rejected(None, lambda item: item.update(counterbalance_arm=9))
    assert "packet identity" in rejected(
        None,
        lambda item: item.update(participant_code="P999"),
        reseal_packet=True,
        rebind_response=True,
    )
    assert "not bound" in rejected(lambda item: item.update(packet_sha256="0" * 64))
    assert "approval reference" in rejected(lambda item: item.update(approval_reference="OTHER"))
    assert "assignments" in rejected(
        None,
        lambda item: item.update(assignments="bad"),
        reseal_packet=True,
        rebind_response=True,
    )
    assert "incomplete" in rejected(lambda item: item.update(responses=[]))
    assert "malformed answer" in rejected(lambda item: item["responses"].__setitem__(0, "bad"))
    assert "unknown or duplicate" in rejected(
        lambda item: item["responses"][0].update(case_id="UNKNOWN")
    )
    assert "invalid condition or verdict" in rejected(
        lambda item: item["responses"][0].update(verdict="maybe")
    )
    assert "invalid duration" in rejected(
        lambda item: item["responses"][0].update(duration_seconds=0)
    )
    assert "invalid confidence" in rejected(lambda item: item["responses"][0].update(confidence=9))
