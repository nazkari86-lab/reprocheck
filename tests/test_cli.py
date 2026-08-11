import json
from pathlib import Path

import uvicorn
import pytest

from reprocheck.audit import run_audit
from reprocheck.certificate import digest_payload
from reprocheck.cli import main


def test_cli_prints_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == "reprocheck 0.16.0\n"


def test_cli_audit_writes_json_and_html(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    model = tmp_path / "model.bin"
    output = tmp_path / "audit.json"
    html = tmp_path / "audit.html"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    model.write_bytes(b"model")

    code = main(
        [
            "audit",
            "--report",
            str(report),
            "--predictions",
            str(predictions),
            "--artifact",
            f"model={model}",
            "--output",
            str(output),
            "--html",
            str(html),
        ]
    )
    assert code == 0
    assert json.loads(output.read_text())["status"] == "passed"
    assert "ПРОЙДЕНО" in html.read_text(encoding="utf-8")


def test_cli_exit_codes_for_review_and_bad_input(tmp_path: Path, capsys):
    report = tmp_path / "report.md"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    review_output = tmp_path / "review.json"
    assert main(["audit", "--report", str(report), "--output", str(review_output)]) == 1

    missing = tmp_path / "missing.csv"
    assert (
        main(
            [
                "audit",
                "--report",
                str(report),
                "--predictions",
                str(missing),
            ]
        )
        == 2
    )
    assert "ERROR:" in capsys.readouterr().err


def test_cli_selects_hybrid_near_duplicate_method(tmp_path: Path):
    report = tmp_path / "report.md"
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    output = tmp_path / "near.json"
    report.write_text("No numerical metric is claimed.", encoding="utf-8")
    train.write_text("id,text\n1,classification accuracy on validation dataset\n", encoding="utf-8")
    test.write_text(
        "id,text\n2,clasification accuracy on the validation data set\n", encoding="utf-8"
    )
    assert (
        main(
            [
                "audit",
                "--report",
                str(report),
                "--train",
                str(train),
                "--test",
                str(test),
                "--identity-columns",
                "id",
                "--text-column",
                "text",
                "--near-method",
                "hybrid_lexical_v1",
                "--near-threshold",
                "0.8",
                "--output",
                str(output),
            ]
        )
        == 1
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["leakage"]["near_overlap_test_rows"] == 1
    assert payload["parameters"]["near_method"] == "hybrid_lexical_v1"


def test_cli_verify_detects_artifact_tampering(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    certificate = tmp_path / "audit.json"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    assert (
        main(
            [
                "audit",
                "--report",
                str(report),
                "--predictions",
                str(predictions),
                "--output",
                str(certificate),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "verify",
                "--certificate",
                str(certificate),
                "--artifact-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    report.write_text("Accuracy: 0%", encoding="utf-8")
    assert (
        main(
            [
                "verify",
                "--certificate",
                str(certificate),
                "--artifact-dir",
                str(tmp_path),
            ]
        )
        == 1
    )


def test_cli_exports_verified_evidence_graph(tmp_path: Path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    certificate = tmp_path / "audit.json"
    graph = tmp_path / "audit.mmd"
    report.write_text("Accuracy: 90%", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}', encoding="utf-8")
    assert (
        main(
            [
                "audit",
                "--report",
                str(report),
                "--metrics",
                str(metrics),
                "--output",
                str(certificate),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "graph",
                "--certificate",
                str(certificate),
                "--output",
                str(graph),
            ]
        )
        == 0
    )
    assert "flowchart LR" in graph.read_text(encoding="utf-8")
    assert "supports" in graph.read_text(encoding="utf-8")

    graph_json = tmp_path / "graph.json"
    assert (
        main(
            [
                "graph",
                "--certificate",
                str(certificate),
                "--format",
                "json",
                "--output",
                str(graph_json),
            ]
        )
        == 0
    )
    assert json.loads(graph_json.read_text())["schema_version"] == "1.0"


def test_cli_graph_rejects_invalid_or_legacy_certificate(tmp_path: Path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    assert main(["graph", "--certificate", str(invalid)]) == 1

    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    legacy = tmp_path / "legacy.json"
    report.write_text("Accuracy: 90%", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}', encoding="utf-8")
    audit = run_audit(report_path=report, metrics_path=metrics)
    payload = audit.to_dict()
    payload["evidence_graph"] = None
    payload["certificate_sha256"] = digest_payload(payload)
    legacy.write_text(json.dumps(payload), encoding="utf-8")

    assert main(["graph", "--certificate", str(legacy)]) == 2


def test_cli_demo_benchmark_and_serve_dispatch(tmp_path: Path, monkeypatch):
    assert main(["demo", "--output-dir", str(tmp_path / "demo")]) == 0
    assert main(["benchmark", "--output", str(tmp_path / "benchmark.json")]) == 0

    called = {}

    def fake_run(app, *, host, port, reload):
        called.update(app=app, host=host, port=port, reload=reload)

    monkeypatch.setattr(uvicorn, "run", fake_run)
    assert main(["serve", "--host", "0.0.0.0", "--port", "9000"]) == 0
    assert called == {
        "app": "reprocheck.web:app",
        "host": "0.0.0.0",
        "port": 9000,
        "reload": False,
    }


def test_cli_runs_real_artifact_study(tmp_path: Path):
    corpus = Path(__file__).parents[1] / "benchmarks" / "real_artifacts"
    output = tmp_path / "study.json"
    assert (
        main(
            [
                "study",
                "--corpus",
                str(corpus),
                "--output",
                str(output),
                "--repeats",
                "1",
                "--bootstrap-samples",
                "20",
            ]
        )
        == 0
    )
    assert json.loads(output.read_text(encoding="utf-8"))["corpus"]["artifacts"] == 60
