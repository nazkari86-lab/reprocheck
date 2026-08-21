import io
import json
import stat
import time
from typing import Any
import zipfile

from fastapi.testclient import TestClient

from reprocheck import web
from reprocheck.web import app


client = TestClient(app)


def _wait_for_job(job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        payload = client.get(f"/api/audit/jobs/{job_id}").json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.02)
    raise AssertionError("audit job did not finish")


def _zip_project(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    return buffer.getvalue()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ml_status_explains_optional_non_verdict_role():
    response = client.get("/api/ml/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["languages"] == ["en", "ru", "kk"]
    assert payload["actions"] == ["verify", "review", "abstain"]
    assert payload["final_verdict_by_ml"] is False

    page = client.get("/")
    assert "Машина ищет. Доказательства решают." in page.text
    assert "Интерактивный граф доказательств" in page.text


def test_demo_endpoint_exposes_real_traceable_audit():
    response = client.post("/api/demo")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_review"
    assert {artifact["filename"] for artifact in payload["artifacts"]} == {
        "research_report.md",
        "model_predictions.csv",
        "train_split.csv",
        "test_split.csv",
    }
    assert {claim["status"] for claim in payload["claims"]} == {"verified", "mismatch"}
    assert payload["leakage"]["exact_overlap_test_rows"] == 1
    assert any(item["code"] == "exact_split_overlap" for item in payload["findings"])
    relations = {edge["relation"] for edge in payload["evidence_graph"]["edges"]}
    assert {"contains", "recomputes", "supports", "contradicts", "flags"} <= relations

    envelope = client.post("/api/demo?envelope=true").json()
    assert envelope["guide"]["derived_from_certificate_sha256"] == payload["certificate_sha256"]


def test_audit_endpoint():
    response = client.post(
        "/api/audit",
        files={
            "report": ("report.md", b"Accuracy: 50%", "text/markdown"),
            "predictions": (
                "predictions.csv",
                b"y_true,y_pred\n0,0\n1,0\n",
                "text/csv",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "passed"
    assert len(response.json()["certificate_sha256"]) == 64
    assert len(response.json()["evidence_graph"]["graph_sha256"]) == 64
    assert response.json()["evidence_graph"]["nodes"]


def test_project_folder_job_uses_manifest_and_real_progress():
    manifest = {
        "schema_version": "reprocheck.project.v1",
        "experiments": [
            {
                "id": "web-folder",
                "report": "research_findings.md",
                "predictions": "raw_predictions.csv",
                "average": "macro",
                "tolerance": 0.02,
                "artifacts": {"model_card": "model-card.md"},
            }
        ],
    }
    response = client.post(
        "/api/audit/jobs",
        files=[
            ("report", ("", b"", "application/octet-stream")),
            (
                "project_files",
                ("science/reprocheck.json", json.dumps(manifest).encode(), "application/json"),
            ),
            (
                "project_files",
                ("science/research_findings.md", b"Accuracy: 51%", "text/markdown"),
            ),
            (
                "project_files",
                ("science/model-card.md", b"# Frozen model", "text/markdown"),
            ),
            (
                "project_files",
                (
                    "science/raw_predictions.csv",
                    b"y_true,y_pred\n0,0\n1,0\n",
                    "text/csv",
                ),
            ),
        ],
    )

    assert response.status_code == 202
    completed = _wait_for_job(response.json()["job_id"])
    assert completed["status"] == "completed"
    assert completed["result"]["status"] == "passed"
    assert completed["result"]["parameters"]["average"] == "macro"
    assert completed["result"]["parameters"]["tolerance"] == 0.02
    assert any(
        item["role"] == "model_card" and item["filename"] == "model-card.md"
        for item in completed["result"]["artifacts"]
    )
    assert {item["filename"] for item in completed["result"]["artifacts"]} >= {
        "research_findings.md",
        "raw_predictions.csv",
    }
    assert [(stage["stage"], stage["state"]) for stage in completed["stages"]] == [
        ("files", "completed"),
        ("claims", "completed"),
        ("evidence", "completed"),
        ("matching", "completed"),
        ("certificate", "completed"),
    ]
    assert all(stage["duration_ms"] >= 0 for stage in completed["stages"])
    files_stage = completed["stages"][0]
    assert files_stage["inference_source"] == "reprocheck.json"
    assert files_stage["experiment_id"] == "web-folder"
    assert files_stage["experiment_count"] == 1
    assert files_stage["input_file_count"] == 4
    assert files_stage["upload_mode"] == "folder"
    assert {item["source"] for item in files_stage["files"]} >= {
        "reprocheck.json",
        "project_artifact",
    }


def test_project_zip_runs_the_same_real_audit_workflow():
    manifest = {
        "schema_version": "reprocheck.project.v1",
        "experiments": [
            {"id": "zip-project", "report": "report.md", "predictions": "predictions.csv"}
        ],
    }
    archive = _zip_project(
        {
            "project/reprocheck.json": json.dumps(manifest).encode(),
            "project/report.md": b"Accuracy: 100%",
            "project/predictions.csv": b"y_true,y_pred\n1,1\n",
            "__MACOSX/._report.md": b"ignored",
            "project/.DS_Store": b"ignored",
        }
    )

    response = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("science.zip", archive, "application/zip")},
    )

    assert response.status_code == 202
    completed = _wait_for_job(response.json()["job_id"])
    assert completed["status"] == "completed"
    assert completed["result"]["status"] == "passed"
    files_stage = completed["stages"][0]
    assert files_stage["upload_mode"] == "archive"
    assert files_stage["input_file_count"] == 3
    assert files_stage["experiment_id"] == "zip-project"
    assert (
        completed["guide"]["derived_from_certificate_sha256"]
        == completed["result"]["certificate_sha256"]
    )


def test_project_zip_rejects_unsafe_or_ambiguous_archives():
    traversal = _zip_project({"project/../report.md": b"Accuracy: 100%"})
    response = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("unsafe.zip", traversal, "application/zip")},
    )
    assert response.status_code == 400
    assert "небезопасный путь" in response.json()["detail"]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        link = zipfile.ZipInfo("project/report.md")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "target.md")
    symlink = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("symlink.zip", buffer.getvalue(), "application/zip")},
    )
    assert symlink.status_code == 400
    assert "Символическая ссылка" in symlink.json()["detail"]

    corrupt = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("broken.zip", b"not a zip", "application/zip")},
    )
    assert corrupt.status_code == 422

    ambiguous = client.post(
        "/api/audit/jobs",
        files=[
            ("project_files", ("project/report.md", b"Accuracy: 100%", "text/markdown")),
            (
                "project_archive",
                ("project.zip", _zip_project({"report.md": b"x"}), "application/zip"),
            ),
        ],
    )
    assert ambiguous.status_code == 400
    assert "не оба варианта" in ambiguous.json()["detail"]


def test_project_zip_enforces_type_and_compressed_size(monkeypatch):
    archive = _zip_project({"report.md": b"Accuracy: 100%"})

    wrong_type = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("project.tar", archive, "application/x-tar")},
    )
    assert wrong_type.status_code == 415

    monkeypatch.setattr(web, "MAX_PROJECT_ARCHIVE_BYTES", len(archive) - 1)
    too_large = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("project.zip", archive, "application/zip")},
    )
    assert too_large.status_code == 413
    assert "ZIP проекта превышает" in too_large.json()["detail"]


def test_project_zip_enforces_entry_and_unpacked_limits(monkeypatch):
    three_files = _zip_project({"a.txt": b"a", "b.txt": b"b", "report.md": b"Accuracy: 1%"})
    monkeypatch.setattr(web, "MAX_PROJECT_FILES", 1)
    too_many_entries = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("project.zip", three_files, "application/zip")},
    )
    assert too_many_entries.status_code == 413
    assert "слишком много записей" in too_many_entries.json()["detail"]

    two_files = _zip_project({"a.txt": b"a", "report.md": b"Accuracy: 1%"})
    too_many_files = client.post(
        "/api/audit/jobs",
        files={"project_archive": ("project.zip", two_files, "application/zip")},
    )
    assert too_many_files.status_code == 413
    assert "В ZIP больше" in too_many_files.json()["detail"]

    monkeypatch.setattr(web, "MAX_PROJECT_FILES", 300)
    monkeypatch.setattr(web, "MAX_PROJECT_UPLOAD_BYTES", 5)
    unpacked_too_large = client.post(
        "/api/audit/jobs",
        files={
            "project_archive": (
                "project.zip",
                _zip_project({"report.md": b"Accuracy: 100%"}),
                "application/zip",
            )
        },
    )
    assert unpacked_too_large.status_code == 413
    assert "Распакованный проект превышает" in unpacked_too_large.json()["detail"]


def test_project_zip_rejects_casefold_duplicates_and_oversized_member(monkeypatch):
    duplicate = client.post(
        "/api/audit/jobs",
        files={
            "project_archive": (
                "project.zip",
                _zip_project({"project/report.md": b"one", "project/REPORT.md": b"two"}),
                "application/zip",
            )
        },
    )
    assert duplicate.status_code == 400
    assert "Повторяющийся файл в ZIP" in duplicate.json()["detail"]

    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 5)
    oversized = client.post(
        "/api/audit/jobs",
        files={
            "project_archive": (
                "project.zip",
                _zip_project({"report.md": b"Accuracy: 100%"}),
                "application/zip",
            )
        },
    )
    assert oversized.status_code == 413
    assert "Файл report.md превышает" in oversized.json()["detail"]


def test_project_folder_job_requires_a_detectable_report():
    response = client.post(
        "/api/audit/jobs",
        files=[("project_files", ("project/source.py", b"print('ok')", "text/x-python"))],
    )

    assert response.status_code == 422
    assert "не найден научный отчёт" in response.json()["detail"]


def test_project_folder_job_rejects_invalid_or_incomplete_manifest():
    invalid = client.post(
        "/api/audit/jobs",
        files=[
            (
                "project_files",
                ("project/reprocheck.json", b'{"experiments": []}', "application/json"),
            )
        ],
    )
    assert invalid.status_code == 422
    assert "schema violation" in invalid.json()["detail"]

    missing = client.post(
        "/api/audit/jobs",
        files=[
            (
                "project_files",
                (
                    "project/reprocheck.json",
                    json.dumps(
                        {
                            "schema_version": "reprocheck.project.v1",
                            "experiments": [{"id": "missing", "report": "absent.md"}],
                        }
                    ).encode(),
                    "application/json",
                ),
            )
        ],
    )
    assert missing.status_code == 422
    assert "manifest artifact is absent" in missing.json()["detail"]


def test_job_api_rejects_missing_jobs_partial_splits_and_unsafe_paths():
    assert client.get("/api/audit/jobs/not-a-job").status_code == 404

    partial = client.post(
        "/api/audit/jobs",
        files={
            "report": ("report.md", b"Accuracy: 100%", "text/markdown"),
            "train": ("train.csv", b"id,label\n1,1\n", "text/csv"),
        },
    )
    assert partial.status_code == 400
    assert "Train и test" in partial.json()["detail"]

    unsafe = client.post(
        "/api/audit/jobs",
        files=[("project_files", ("project/../report.md", b"Accuracy: 100%", "text/markdown"))],
    )
    assert unsafe.status_code == 400
    assert "небезопасный путь" in unsafe.json()["detail"]

    duplicate = client.post(
        "/api/audit/jobs",
        files=[
            ("project_files", ("project/report.md", b"Accuracy: 100%", "text/markdown")),
            ("project_files", ("project/report.md", b"Accuracy: 50%", "text/markdown")),
        ],
    )
    assert duplicate.status_code == 400
    assert "Повторяющийся файл" in duplicate.json()["detail"]
    assert web._split_columns("id, text, ") == ["id", "text"]


def test_project_folder_enforces_file_count_and_byte_limits(monkeypatch):
    monkeypatch.setattr(web, "MAX_PROJECT_FILES", 1)
    too_many = client.post(
        "/api/audit/jobs",
        files=[
            ("project_files", ("project/report.md", b"Accuracy: 100%", "text/markdown")),
            ("project_files", ("project/data.txt", b"data", "text/plain")),
        ],
    )
    assert too_many.status_code == 413
    assert "В папке больше" in too_many.json()["detail"]

    monkeypatch.setattr(web, "MAX_PROJECT_FILES", 300)
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 5)
    oversized_file = client.post(
        "/api/audit/jobs",
        files=[("project_files", ("project/report.md", b"Accuracy: 100%", "text/markdown"))],
    )
    assert oversized_file.status_code == 413
    assert "Файл project/report.md превышает" in oversized_file.json()["detail"]

    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 100)
    monkeypatch.setattr(web, "MAX_PROJECT_UPLOAD_BYTES", 5)
    oversized_folder = client.post(
        "/api/audit/jobs",
        files=[("project_files", ("project/report.md", b"Accuracy: 100%", "text/markdown"))],
    )
    assert oversized_folder.status_code == 413
    assert "Папка проекта превышает" in oversized_folder.json()["detail"]


def test_project_folder_job_infers_roles_without_manifest():
    response = client.post(
        "/api/audit/jobs",
        files=[
            ("project_files", ("project/final_report.md", b"Accuracy: 100%", "text/markdown")),
            (
                "project_files",
                ("project/model_predictions.csv", b"y_true,y_pred\n1,1\n", "text/csv"),
            ),
        ],
    )

    assert response.status_code == 202
    completed = _wait_for_job(response.json()["job_id"])
    assert completed["status"] == "completed"
    assert completed["stages"][0]["inference_source"] == "filename_rules"
    assert [(item["role"], item["filename"]) for item in completed["stages"][0]["files"]] == [
        ("report", "final_report.md"),
        ("predictions", "model_predictions.csv"),
    ]


def test_audit_job_exposes_parser_failure():
    response = client.post(
        "/api/audit/jobs",
        files={
            "report": ("actual_report.md", b"Accuracy: 100%", "text/markdown"),
            "predictions": ("broken_predictions.csv", b"wrong,column\n1,1\n", "text/csv"),
        },
    )

    assert response.status_code == 202
    failed = _wait_for_job(response.json()["job_id"])
    assert failed["status"] == "failed"
    assert "y_true,y_pred" in failed["error"]


def test_regression_metrics_are_marked_scalar_and_web_uses_metadata():
    response = client.post(
        "/api/audit",
        data={"prediction_task": "regression"},
        files={
            "report": ("report.md", b"MAE: 2.5", "text/markdown"),
            "predictions": (
                "predictions.csv",
                b"y_true,y_pred\n0,2\n0,3\n",
                "text/csv",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["claims"][0]["display_kind"] == "scalar"

    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "formatMetric(claim.value, display_kind)" in script.text
    assert "percent(claim.value)" not in script.text


def test_web_exposes_interactive_evidence_explorer():
    page = client.get("/")
    script = client.get("/static/app.js")
    styles = client.get("/static/styles.css")

    assert page.status_code == script.status_code == styles.status_code == 200
    assert 'id="evidence-explorer"' in page.text
    assert 'id="evidence-svg"' in page.text
    assert 'id="node-inspector"' in page.text
    assert 'id="demo"' in page.text
    assert 'id="project-archive"' in page.text
    assert page.text.count('class="config-panel"') == 2
    assert "semanticNeighborhood" in script.text
    assert "MAX_VISIBLE_NODES" in script.text
    assert "roundedOrthogonalPath" in script.text
    assert "edge-group" in script.text
    assert "is-structural" in script.text
    assert "/api/audit/jobs" in script.text
    assert "startProjectLoading" in script.text
    assert "renderEvidencePassport" in script.text
    assert "refreshProjectPreview" in script.text
    assert "ФАКТИЧЕСКИЙ ХОД BACKEND" in script.text
    assert "EVIDENCE PASSPORT / БЕЗ AI SCORE" in script.text
    assert "prefers-reduced-motion" in styles.text


def test_audit_endpoint_rejects_malformed_detection():
    response = client.post(
        "/api/audit",
        files={
            "report": ("report.md", b"mAP50: 90%", "text/markdown"),
            "detections": (
                "detections.json",
                b'{"images":[{"id":"x","ground_truth":[],"predictions":['
                b'{"class_id":0,"bbox":[0,0,1,1]}]}]}',
                "application/json",
            ),
        },
    )
    assert response.status_code == 422
    assert "confidence must be numeric" in response.json()["detail"]


def test_upload_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(web, "MAX_UPLOAD_BYTES", 10)
    response = client.post(
        "/api/audit",
        files={"report": ("report.md", b"Accuracy: 100%", "text/markdown")},
    )
    assert response.status_code == 413


def test_web_forwards_hybrid_near_duplicate_configuration():
    response = client.post(
        "/api/audit",
        data={
            "identity_columns": "id",
            "text_column": "text",
            "near_method": "hybrid_lexical_v1",
            "near_threshold": "0.8",
        },
        files={
            "report": ("report.md", b"No metric claim.", "text/markdown"),
            "train": (
                "train.csv",
                b"id,text\n1,classification accuracy on validation dataset\n",
                "text/csv",
            ),
            "test": (
                "test.csv",
                b"id,text\n2,clasification accuracy on the validation data set\n",
                "text/csv",
            ),
        },
    )
    assert response.status_code == 200
    assert response.json()["parameters"]["near_method"] == "hybrid_lexical_v1"
    assert response.json()["leakage"]["near_overlap_test_rows"] == 1
