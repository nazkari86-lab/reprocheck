import json
from pathlib import Path

from reprocheck.audit import run_audit
from reprocheck.witness import (
    _finite_number,
    _load_object,
    _object_list,
    _objects_by_id,
    _validate_witness_shape,
    build_witness_file,
    build_witness_payload,
    verify_witness_file,
    witness_digest,
)


def _mismatch_certificate(tmp_path: Path) -> tuple[Path, Path]:
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    certificate = tmp_path / "certificate.json"
    report.write_text("Accuracy: 80%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
    audit = run_audit(report_path=report, metrics_path=metrics)
    certificate.write_text(json.dumps(audit.to_dict()), encoding="utf-8")
    return certificate, tmp_path


def test_builds_and_verifies_canonical_minimal_mismatch_witness(tmp_path: Path):
    certificate, artifacts = _mismatch_certificate(tmp_path)
    output = tmp_path / "witness.json"

    witness = build_witness_file(certificate, 0, output)

    assert witness["schema_version"] == "reprocheck.witness.v1"
    assert witness["verifier_rule"] == "claim_metric_mismatch.source_grounded.v1"
    assert witness["minimality"]["minimum_node_count"] == 5
    assert witness["minimality"]["minimum_edge_count"] == 4
    assert {node["kind"] for node in witness["nodes"]} == {
        "artifact",
        "claim",
        "metric",
        "finding",
    }
    assert verify_witness_file(output, certificate, artifacts) == []


def test_witness_rejects_payload_node_edge_and_source_tampering(tmp_path: Path):
    certificate, _ = _mismatch_certificate(tmp_path)
    output = tmp_path / "witness.json"
    build_witness_file(certificate, 0, output)
    original = json.loads(output.read_text(encoding="utf-8"))

    payload = json.loads(json.dumps(original))
    payload["rule_inputs"]["observed"] = 0.8
    output.write_text(json.dumps(payload), encoding="utf-8")
    assert "witness checksum does not match its payload" in verify_witness_file(output, certificate)

    payload = json.loads(json.dumps(original))
    payload["nodes"][0]["label"] = "tampered"
    payload["witness_sha256"] = witness_digest(payload)
    output.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_witness_file(output, certificate)
    assert any("node digest mismatch" in error for error in errors)

    payload = json.loads(json.dumps(original))
    payload["edges"][0]["relation"] = "supports"
    payload["witness_sha256"] = witness_digest(payload)
    output.write_text(json.dumps(payload), encoding="utf-8")
    errors = verify_witness_file(output, certificate)
    assert any("edge digest mismatch" in error for error in errors)

    payload = json.loads(json.dumps(original))
    payload["source_certificate_sha256"] = "0" * 64
    payload["witness_sha256"] = witness_digest(payload)
    output.write_text(json.dumps(payload), encoding="utf-8")
    assert "witness references a different source certificate" in verify_witness_file(
        output, certificate
    )


def test_witness_fails_closed_for_unsupported_or_missing_finding(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    certificate = tmp_path / "certificate.json"
    report.write_text("Accuracy: 90%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
    certificate.write_text(
        json.dumps(run_audit(report_path=report, metrics_path=metrics).to_dict()),
        encoding="utf-8",
    )

    try:
        build_witness_file(certificate, 0, tmp_path / "witness.json")
    except ValueError as error:
        assert "finding index does not exist" in str(error)
    else:
        raise AssertionError("missing finding must fail closed")


def test_witness_selects_metric_that_matches_the_actual_observed_value(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    predictions = tmp_path / "predictions.csv"
    certificate = tmp_path / "certificate.json"
    output = tmp_path / "witness.json"
    report.write_text("Accuracy: 80%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.7}\n', encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,1\n", encoding="utf-8")
    audit = run_audit(
        report_path=report,
        metrics_path=metrics,
        predictions_path=predictions,
    )
    certificate.write_text(json.dumps(audit.to_dict()), encoding="utf-8")

    witness = build_witness_file(certificate, 1, output)

    metric = next(node for node in witness["nodes"] if node["kind"] == "metric")
    assert metric["attributes"]["value"] == 1.0
    assert metric["attributes"]["source"] == "predictions.csv"
    assert verify_witness_file(output, certificate, tmp_path) == []


def test_witness_shape_validation_rejects_malformed_and_semantically_invalid_payloads(
    tmp_path: Path,
):
    certificate, _ = _mismatch_certificate(tmp_path)
    output = tmp_path / "witness.json"
    base = build_witness_file(certificate, 0, output)

    payload = json.loads(json.dumps(base))
    payload.update(schema_version="bad", verifier_rule="bad", nodes={})
    errors = _validate_witness_shape(payload)
    assert "unsupported witness schema version" in errors
    assert "unsupported witness verifier rule" in errors
    assert "witness nodes and edges must be arrays" in errors

    payload = json.loads(json.dumps(base))
    payload["nodes"].append("bad")
    payload["nodes"].append(dict(payload["nodes"][0]))
    payload["edges"].append("bad")
    payload["edges"][0]["target"] = "missing"
    payload["edges"].append(dict(payload["edges"][0]))
    errors = _validate_witness_shape(payload)
    assert any("malformed witness node" in error for error in errors)
    assert any("duplicate witness node" in error for error in errors)
    assert any("malformed witness edge" in error for error in errors)
    assert any("duplicate witness edge" in error for error in errors)
    assert any("unknown node" in error for error in errors)

    def semantic_error(mutate, expected):
        payload = json.loads(json.dumps(base))
        mutate(payload)
        errors = _validate_witness_shape(payload)
        assert any(expected in error for error in errors), errors

    semantic_error(
        lambda item: item["nodes"].append({**item["nodes"][-1], "id": "metric:extra"}),
        "exactly one finding",
    )
    semantic_error(
        lambda item: next(node for node in item["nodes"] if node["kind"] == "claim").update(
            attributes="bad"
        ),
        "attributes must be objects",
    )
    semantic_error(
        lambda item: next(node for node in item["nodes"] if node["kind"] == "finding")[
            "attributes"
        ].update(code="other"),
        "finding code",
    )
    semantic_error(lambda item: item["edges"].pop(), "metric-to-claim contradiction")
    semantic_error(
        lambda item: item.update(
            edges=[edge for edge in item["edges"] if edge["relation"] != "raises"]
        ),
        "claim-to-finding",
    )
    semantic_error(
        lambda item: item.update(
            edges=[edge for edge in item["edges"] if edge["relation"] != "reports"]
        ),
        "source artifact",
    )
    semantic_error(lambda item: item.update(rule_inputs=[]), "rule inputs")
    semantic_error(
        lambda item: item["rule_inputs"].update(tolerance="bad"),
        "finite number",
    )
    semantic_error(
        lambda item: next(node for node in item["nodes"] if node["kind"] == "metric")[
            "attributes"
        ].update(name="f1"),
        "names differ",
    )
    semantic_error(lambda item: item["rule_inputs"].update(observed=0.1), "observed value")
    semantic_error(
        lambda item: next(node for node in item["nodes"] if node["kind"] == "metric")[
            "attributes"
        ].update(value=0.8),
        "mismatch tolerance",
    )
    semantic_error(
        lambda item: item["minimality"].update(minimum_node_count=99),
        "node count",
    )
    semantic_error(
        lambda item: item["minimality"].update(minimum_edge_count=99),
        "edge count",
    )


def test_witness_build_and_io_helpers_fail_closed(tmp_path: Path):
    certificate, _ = _mismatch_certificate(tmp_path)
    source = json.loads(certificate.read_text())

    for mutation, expected in (
        (lambda item: item.update(evidence_graph=None), "no evidence graph"),
        (
            lambda item: item["evidence_graph"]["nodes"].__setitem__(0, {"kind": "bad"}),
            "node id",
        ),
        (
            lambda item: item["evidence_graph"].update(edges=["bad"]),
            "array of objects",
        ),
        (
            lambda item: next(
                node for node in item["evidence_graph"]["nodes"] if node["id"] == "finding:0"
            )["attributes"].update(code="other"),
            "only claim_metric_mismatch",
        ),
        (
            lambda item: item.update(claims=[]),
            "exactly one mismatched source claim",
        ),
        (
            lambda item: next(
                node for node in item["evidence_graph"]["nodes"] if node["id"] == "claim:0"
            ).update(kind="bad"),
            "no source-grounded",
        ),
    ):
        payload = json.loads(json.dumps(source))
        mutation(payload)
        try:
            build_witness_payload(payload, 0)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError("malformed source must fail")

    assert _object_list([], "items") == []
    try:
        _objects_by_id([{"id": 1}])
    except ValueError as error:
        assert "node id" in str(error)
    else:
        raise AssertionError("non-string node id must fail")
    for value in (True, float("inf"), "1"):
        try:
            _finite_number(value, "value")
        except ValueError as error:
            assert "finite number" in str(error)
        else:
            raise AssertionError("invalid number must fail")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("[]", encoding="utf-8")
    try:
        _load_object(malformed, "payload")
    except ValueError as error:
        assert "JSON object" in str(error)
    else:
        raise AssertionError("non-object JSON must fail")
    malformed.write_text("not json", encoding="utf-8")
    assert "cannot be read" in verify_witness_file(malformed, certificate)[0]
