import csv
import json
from pathlib import Path

import pytest

from reprocheck.audit import run_audit
from reprocheck.witness import build_witness_file, verify_witness_file, witness_digest
from reprocheck.witness_rules import recompute_exact_overlap


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _metric_conflict_certificate(root: Path) -> Path:
    report = root / "report.md"
    metrics = root / "metrics.json"
    predictions = root / "predictions.csv"
    certificate = root / "certificate.json"
    report.write_text("Accuracy: 90%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,0\n", encoding="utf-8")
    audit = run_audit(report_path=report, metrics_path=metrics, predictions_path=predictions)
    certificate.write_text(json.dumps(audit.to_dict()), encoding="utf-8")
    return certificate


def _split_certificate(root: Path) -> Path:
    report = root / "report.md"
    train = root / "train.csv"
    test = root / "test.csv"
    certificate = root / "certificate.json"
    report.write_text("No numerical claims.\n", encoding="utf-8")
    _write_csv(train, [{"id": "1", "text": "train"}, {"id": "2", "text": "other"}])
    _write_csv(test, [{"id": "1", "text": "changed"}, {"id": "3", "text": "new"}])
    audit = run_audit(
        report_path=report,
        train_path=train,
        test_path=test,
        identity_columns=["id"],
    )
    certificate.write_text(json.dumps(audit.to_dict()), encoding="utf-8")
    return certificate


def test_metric_conflict_builds_and_verifies_canonical_five_node_witness(tmp_path: Path):
    certificate = _metric_conflict_certificate(tmp_path)
    output = tmp_path / "witness.json"

    witness = build_witness_file(certificate, 0, output, tmp_path)

    assert witness["schema_version"] == "reprocheck.witness.v2"
    assert witness["finding_code"] == "metric_evidence_conflict"
    assert witness["minimality"]["minimum_node_count"] == 5
    assert witness["minimality"]["minimum_edge_count"] == 4
    assert verify_witness_file(output, certificate, tmp_path) == []


def test_exact_overlap_requires_and_recomputes_bound_artifacts(tmp_path: Path):
    certificate = _split_certificate(tmp_path)
    output = tmp_path / "witness.json"
    with pytest.raises(ValueError, match="artifact-dir"):
        build_witness_file(certificate, 0, output)

    witness = build_witness_file(certificate, 0, output, tmp_path)

    assert witness["finding_code"] == "exact_split_overlap"
    assert witness["minimality"]["minimum_node_count"] == 3
    assert witness["minimality"]["minimum_edge_count"] == 2
    assert witness["rule_inputs"]["exact_overlap_test_rows"] == 1
    assert len(witness["rule_inputs"]["overlap_identity_sha256"]) == 1
    assert verify_witness_file(output, certificate, tmp_path) == []


def test_exact_overlap_fails_if_csv_or_rule_inputs_change(tmp_path: Path):
    certificate = _split_certificate(tmp_path)
    output = tmp_path / "witness.json"
    witness = build_witness_file(certificate, 0, output, tmp_path)
    payload = json.loads(json.dumps(witness))
    payload["rule_inputs"]["exact_overlap_test_rows"] = 2
    payload["witness_sha256"] = witness_digest(payload)
    output.write_text(json.dumps(payload), encoding="utf-8")
    assert verify_witness_file(output, certificate, tmp_path)

    output.write_text(json.dumps(witness), encoding="utf-8")
    (tmp_path / "test.csv").write_text("id,text\n3,new\n", encoding="utf-8")
    errors = verify_witness_file(output, certificate, tmp_path)
    assert any("checksum or size mismatch" in error for error in errors)


def test_metric_conflict_is_order_independent_but_source_value_bound(tmp_path: Path):
    certificate = _metric_conflict_certificate(tmp_path)
    source = json.loads(certificate.read_text(encoding="utf-8"))
    finding = next(
        item for item in source["findings"] if item["code"] == "metric_evidence_conflict"
    )
    finding["sources"].reverse()
    finding["values"].reverse()
    graph_finding = next(
        node
        for node in source["evidence_graph"]["nodes"]
        if node["kind"] == "finding" and node["attributes"]["code"] == "metric_evidence_conflict"
    )
    graph_finding["attributes"]["sources"].reverse()
    graph_finding["attributes"]["values"].reverse()
    from reprocheck.certificate import digest_payload
    from reprocheck.evidence_graph import _digest

    graph_finding["digest_sha256"] = _digest(
        {key: value for key, value in graph_finding.items() if key != "digest_sha256"}
    )
    graph = source["evidence_graph"]
    graph["graph_sha256"] = _digest(
        {key: value for key, value in graph.items() if key != "graph_sha256"}
    )
    source["certificate_sha256"] = digest_payload(source)
    certificate.write_text(json.dumps(source), encoding="utf-8")

    output = tmp_path / "witness.json"
    witness = build_witness_file(certificate, 0, output, tmp_path)
    assert [item["source"] for item in witness["rule_inputs"]["source_values"]] == sorted(
        finding["sources"]
    )


def test_recompute_exact_overlap_preserves_duplicate_test_row_count(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    _write_csv(train, [{"id": "1"}])
    _write_csv(test, [{"id": "1"}, {"id": "1"}, {"id": "2"}])

    result = recompute_exact_overlap(train, test, ["id"])

    assert result["exact_overlap_test_rows"] == 2
    assert len(result["overlap_identity_sha256"]) == 1
