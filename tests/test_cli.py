import json
from pathlib import Path

import uvicorn

from reprocheck.cli import main


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
