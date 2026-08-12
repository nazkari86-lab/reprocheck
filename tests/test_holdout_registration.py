import json

from reprocheck.holdout_registration import (
    _load_protocol,
    register_external_holdout,
    verify_external_holdout_registration,
)


def _protocol(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "title": "test",
                "research_question": "test?",
                "evaluator_version": "1",
                "source_pools": [
                    {
                        "repository": f"https://github.com/example/repo-{index}",
                        "commit": str(index) * 40,
                    }
                    for index in range(1, 4)
                ],
                "selection": {},
                "primary_endpoints": {},
                "annotation": {},
                "stopping_rule": "one run",
                "analysis_plan": {},
                "scientific_boundary": "bounded",
            }
        ),
        encoding="utf-8",
    )


def test_external_holdout_registration_is_immutable_and_verifiable(tmp_path):
    protocol = tmp_path / "protocol.json"
    evaluator = tmp_path / "evaluator.whl"
    registration = tmp_path / "registration.json"
    _protocol(protocol)
    evaluator.write_bytes(b"frozen evaluator")

    payload = register_external_holdout(protocol, evaluator, registration)

    assert payload["status"] == "registered_not_executed"
    assert payload["external_reviewers_completed"] == 0
    assert verify_external_holdout_registration(registration, protocol, evaluator) == []
    try:
        register_external_holdout(protocol, evaluator, registration)
    except ValueError as error:
        assert "immutable" in str(error)
    else:
        raise AssertionError("registration overwrite must fail")


def test_external_holdout_registration_detects_tampering_and_placeholders(tmp_path):
    protocol = tmp_path / "protocol.json"
    evaluator = tmp_path / "evaluator.whl"
    registration = tmp_path / "registration.json"
    _protocol(protocol)
    evaluator.write_bytes(b"frozen evaluator")
    register_external_holdout(protocol, evaluator, registration)

    evaluator.write_bytes(b"changed")
    assert "registered evaluator checksum or size does not match" in (
        verify_external_holdout_registration(registration, protocol, evaluator)
    )

    _protocol(protocol)
    payload = json.loads(protocol.read_text())
    payload["title"] = "TODO"
    protocol.write_text(json.dumps(payload), encoding="utf-8")
    try:
        register_external_holdout(protocol, evaluator, tmp_path / "other.json")
    except ValueError as error:
        assert "placeholder" in str(error)
    else:
        raise AssertionError("unresolved protocol must fail")


def test_holdout_protocol_and_registration_fail_closed_branches(tmp_path):
    protocol = tmp_path / "protocol.json"
    evaluator = tmp_path / "evaluator.whl"
    registration = tmp_path / "registration.json"
    _protocol(protocol)
    evaluator.write_bytes(b"evaluator")

    try:
        register_external_holdout(protocol, tmp_path / "missing.whl", registration)
    except ValueError as error:
        assert "does not exist" in str(error)
    else:
        raise AssertionError("missing evaluator must fail")

    base = json.loads(protocol.read_text())
    mutations = [
        ({key: value for key, value in base.items() if key != "title"}, "missing"),
        ({**base, "source_pools": []}, "at least three"),
        ({**base, "source_pools": [1, 2, 3]}, "must be an object"),
        (
            {
                **base,
                "source_pools": [{**item, "commit": "BAD"} for item in base["source_pools"]],
            },
            "40-character commit",
        ),
        (
            {
                **base,
                "source_pools": [
                    {**item, "repository": "https://example.com/repo"}
                    for item in base["source_pools"]
                ],
            },
            "GitHub repository",
        ),
    ]
    for payload, expected in mutations:
        protocol.write_text(json.dumps(payload), encoding="utf-8")
        try:
            _load_protocol(protocol)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError("invalid protocol must fail")

    protocol.write_text("[]", encoding="utf-8")
    missing_registration = tmp_path / "missing.json"
    missing_registration.write_text("{}", encoding="utf-8")
    assert (
        "must be a JSON object"
        in verify_external_holdout_registration(missing_registration, protocol, evaluator)[0]
    )

    _protocol(protocol)
    payload = register_external_holdout(protocol, evaluator, registration)
    protocol.write_text(protocol.read_text() + " ", encoding="utf-8")
    assert "registered protocol checksum or size does not match" in (
        verify_external_holdout_registration(registration, protocol, evaluator)
    )
    _protocol(protocol)
    payload.update(
        schema_version="bad",
        status="executed",
        external_reviewers_completed=2,
        source_contents_inspected_after_registration=True,
    )
    registration.write_text(json.dumps(payload), encoding="utf-8")
    evaluator.unlink()
    errors = verify_external_holdout_registration(registration, protocol, evaluator)
    assert "unsupported external holdout registration schema" in errors
    assert "registration must remain registered_not_executed before evaluation" in errors
    assert "unexecuted registration cannot claim completed external reviewers" in errors
    assert "registration source-inspection state is not pristine" in errors
    assert "registration checksum does not match its payload" in errors
    assert any("registered evaluator is missing" in error for error in errors)

    registration.write_text("not json", encoding="utf-8")
    assert (
        "registration cannot be read"
        in verify_external_holdout_registration(registration, protocol, evaluator)[0]
    )
