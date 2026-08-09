import json
from pathlib import Path

from reprocheck.audit import run_audit
from reprocheck.certificate import digest_payload, verify_certificate_file
from reprocheck.evidence_graph import render_mermaid, verify_evidence_graph


def _audit(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    report.write_text(
        "| Model | Accuracy |\n| --- | ---: |\n| proposed | 100% |\n",
        encoding="utf-8",
    )
    predictions.write_text("y_true,y_pred\nno,no\nyes,yes\n", encoding="utf-8")
    return run_audit(report_path=report, predictions_path=predictions)


def test_evidence_graph_traces_artifact_metric_and_claim(tmp_path: Path):
    first = _audit(tmp_path)
    second = _audit(tmp_path)
    assert first.evidence_graph is not None
    assert second.evidence_graph is not None
    assert first.evidence_graph.graph_sha256 == second.evidence_graph.graph_sha256
    assert verify_evidence_graph(first.evidence_graph.__dict__) == []

    relations = {
        (edge["source"], edge["relation"], edge["target"]) for edge in first.evidence_graph.edges
    }
    assert ("artifact:1", "recomputes", "metric:0") in relations
    assert ("metric:0", "supports", "claim:0") in relations
    assert ("artifact:0", "contains", "claim:0") in relations
    assert any(edge[1] == "qualifies" for edge in relations)


def test_evidence_graph_internal_digests_reject_self_consistent_tampering(tmp_path: Path):
    audit = _audit(tmp_path)
    certificate = tmp_path / "certificate.json"
    payload = audit.to_dict()
    payload["evidence_graph"]["nodes"][0]["label"] = "altered experiment"
    payload["certificate_sha256"] = digest_payload(payload)
    certificate.write_text(json.dumps(payload), encoding="utf-8")

    errors = verify_certificate_file(certificate)
    assert "evidence graph node digest mismatch at index 0" in errors
    assert "evidence graph digest does not match its payload" in errors


def test_evidence_graph_preserves_all_conflicting_metric_sources(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    predictions = tmp_path / "predictions.csv"
    report.write_text("Accuracy: 50%", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}', encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,0\n", encoding="utf-8")

    audit = run_audit(
        report_path=report,
        metrics_path=metrics,
        predictions_path=predictions,
    )
    assert audit.evidence_graph is not None
    metric_nodes = [
        node
        for node in audit.evidence_graph.nodes
        if node["kind"] == "metric" and node["attributes"]["name"] == "accuracy"
    ]
    assert [node["attributes"]["source"] for node in metric_nodes] == [
        "metrics.json",
        "predictions.csv",
    ]
    relations = {
        (edge["source"], edge["relation"], edge["target"]) for edge in audit.evidence_graph.edges
    }
    assert ("metric:0", "contradicts", "claim:0") in relations
    assert ("metric:1", "supports", "claim:0") in relations
    assert ("metric:0", "flags", "finding:0") in relations
    assert ("metric:1", "flags", "finding:0") in relations


def test_evidence_graph_preserves_contexts_from_every_metric_source(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.csv"
    predictions = tmp_path / "predictions.csv"
    report.write_text(
        "| Model | Accuracy |\n| --- | ---: |\n| proposed | 100% |\n",
        encoding="utf-8",
    )
    metrics.write_text(
        "model,accuracy\nbaseline,0.5\nproposed,1.0\n",
        encoding="utf-8",
    )
    predictions.write_text(
        "model,y_true,y_pred\nbaseline,0,1\nproposed,1,1\n",
        encoding="utf-8",
    )

    audit = run_audit(
        report_path=report,
        metrics_path=metrics,
        metrics_selector="model=baseline",
        predictions_path=predictions,
    )

    assert audit.evidence_graph is not None
    contexts = {
        (node["attributes"]["key"], node["attributes"]["value"])
        for node in audit.evidence_graph.nodes
        if node["kind"] == "context"
    }
    assert ("model", "baseline") in contexts
    assert ("model", "proposed") in contexts
    assert verify_evidence_graph(audit.evidence_graph.__dict__) == []


def test_mermaid_export_uses_safe_generated_identifiers(tmp_path: Path):
    audit = _audit(tmp_path)
    assert audit.evidence_graph is not None
    output = render_mermaid(audit.evidence_graph.__dict__)

    assert output.startswith("flowchart LR\n")
    assert 'n0["ReproCheck audit"]' in output
    assert "-->|supports|" in output
    assert "artifact:0[" not in output


def test_evidence_graph_rejects_duplicate_cycle_and_disconnected_node(tmp_path: Path):
    audit = _audit(tmp_path)
    assert audit.evidence_graph is not None
    payload = audit.evidence_graph.__dict__
    payload = json.loads(json.dumps(payload))
    payload["edges"].append(dict(payload["edges"][0]))
    payload["nodes"].append(
        {
            "id": "detached:0",
            "kind": "finding",
            "label": "detached",
            "attributes": {},
            "digest_sha256": "0" * 64,
        }
    )
    payload["edges"].append(
        {
            "source": "experiment:0",
            "target": "artifact:0",
            "relation": "flags",
            "digest_sha256": "0" * 64,
        }
    )

    errors = verify_evidence_graph(payload)
    assert any("duplicate evidence graph edge" in error for error in errors)
    assert "evidence graph contains nodes disconnected from its root" in errors
    assert "evidence graph contains a directed cycle" in errors


def test_evidence_graph_validation_fails_closed_on_malformed_structure(tmp_path: Path):
    assert verify_evidence_graph([]) == ["evidence graph must be an object"]
    assert verify_evidence_graph({"nodes": {}, "edges": []}) == [
        "evidence graph nodes and edges must be arrays"
    ]

    audit = _audit(tmp_path)
    assert audit.evidence_graph is not None
    payload = json.loads(json.dumps(audit.evidence_graph.__dict__))
    payload["nodes"].append(dict(payload["nodes"][0]))
    payload["edges"].append("not-an-edge")
    payload["edges"][0]["source"] = "missing:0"
    payload["root_id"] = "artifact:0"

    errors = verify_evidence_graph(payload)
    assert "duplicate evidence graph node id: experiment:0" in errors
    assert "evidence graph edge references an unknown node at index 0" in errors
    assert "evidence graph root must be an experiment node" in errors

    rendered = render_mermaid({"nodes": ["bad"], "edges": ["bad"]})
    assert rendered == "flowchart LR\n"
