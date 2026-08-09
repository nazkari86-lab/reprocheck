import copy
import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from reprocheck.certificate import digest_payload, verify_certificate_file
from reprocheck.cli import main


def _write_project(root: Path, *, include_review: bool = True) -> Path:
    inputs = root / "inputs"
    inputs.mkdir()
    (inputs / "pass-report.md").write_text("Accuracy: 100%", encoding="utf-8")
    (inputs / "pass-predictions.csv").write_text("y_true,y_pred\n1,1\n0,0\n", encoding="utf-8")
    experiments: list[dict[str, object]] = [
        {
            "id": "passing",
            "report": "inputs/pass-report.md",
            "predictions": "inputs/pass-predictions.csv",
        }
    ]
    if include_review:
        (inputs / "review-report.md").write_text("Accuracy: 100%", encoding="utf-8")
        (inputs / "review-predictions.csv").write_text(
            "y_true,y_pred\n1,0\n0,0\n", encoding="utf-8"
        )
        experiments.append(
            {
                "id": "needs-review",
                "report": "inputs/review-report.md",
                "predictions": "inputs/review-predictions.csv",
                "tolerance": 0.001,
            }
        )
    manifest = root / "reprocheck.json"
    manifest.write_text(
        json.dumps(
            {"schema_version": "reprocheck.project.v1", "experiments": experiments},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def test_batch_check_writes_and_verifies_linked_certificates(tmp_path: Path):
    manifest = _write_project(tmp_path)
    output = tmp_path / "audit-output"

    assert main(["check", str(manifest), "--output-dir", str(output), "--html"]) == 1
    batch_path = output / "batch-certificate.json"
    payload = json.loads(batch_path.read_text(encoding="utf-8"))
    schema = json.loads(
        files("reprocheck")
        .joinpath("schemas/batch-certificate-v1.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["status"] == "needs_review"
    assert [(item["id"], item["status"]) for item in payload["experiments"]] == [
        ("passing", "passed"),
        ("needs-review", "needs_review"),
    ]
    assert (output / "passing.audit.html").is_file()
    assert (output / "needs-review.audit.html").is_file()
    assert verify_certificate_file(batch_path, tmp_path) == []
    assert main(["verify", "--certificate", str(batch_path), "--artifact-dir", str(tmp_path)]) == 0

    predictions = tmp_path / "inputs" / "pass-predictions.csv"
    original_predictions = predictions.read_text(encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,0\n", encoding="utf-8")
    assert any(
        "artifact checksum" in error for error in verify_certificate_file(batch_path, tmp_path)
    )
    predictions.write_text(original_predictions, encoding="utf-8")

    child = output / "passing.audit.json"
    child_payload = json.loads(child.read_text(encoding="utf-8"))
    child_payload["status"] = "needs_review"
    child.write_text(json.dumps(child_payload), encoding="utf-8")
    assert any(
        "passing.audit.json" in error for error in verify_certificate_file(batch_path, tmp_path)
    )


def test_batch_check_passes_and_fails_closed_on_invalid_manifests(tmp_path: Path):
    manifest = _write_project(tmp_path, include_review=False)
    output = tmp_path / "passed"
    assert main(["check", str(manifest), "--output-dir", str(output)]) == 0
    assert verify_certificate_file(output / "batch-certificate.json", tmp_path) == []

    invalid_cases = [
        {
            "schema_version": "reprocheck.project.v1",
            "experiments": [{"id": "escape", "report": "../report.md"}],
        },
        {
            "schema_version": "reprocheck.project.v1",
            "experiments": [{"id": "unknown", "report": "report.md", "surprise": True}],
        },
        {
            "schema_version": "reprocheck.project.v1",
            "experiments": [
                {"id": "same", "report": "report.md"},
                {"id": "same", "report": "other.md"},
            ],
        },
        {
            "schema_version": "reprocheck.project.v1",
            "experiments": [
                {
                    "id": "reserved",
                    "report": "report.md",
                    "artifacts": {"metrics": "metrics.json"},
                }
            ],
        },
    ]
    for index, payload in enumerate(invalid_cases):
        path = tmp_path / f"invalid-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        assert main(["check", str(path), "--output-dir", str(tmp_path / f"bad-{index}")]) == 2


def test_batch_rejects_symlink_escape_and_leaves_no_partial_output(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("Accuracy: 100%", encoding="utf-8")
    (project / "outside-link.md").symlink_to(outside)
    symlink_manifest = project / "symlink.json"
    symlink_manifest.write_text(
        json.dumps(
            {
                "schema_version": "reprocheck.project.v1",
                "experiments": [{"id": "escape", "report": "outside-link.md"}],
            }
        ),
        encoding="utf-8",
    )
    assert main(["check", str(symlink_manifest), "--output-dir", str(project / "out")]) == 2
    assert not (project / "out").exists()

    report = project / "report.md"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    partial_manifest = project / "partial.json"
    partial_manifest.write_text(
        json.dumps(
            {
                "schema_version": "reprocheck.project.v1",
                "experiments": [
                    {"id": "valid-first", "report": "report.md"},
                    {"id": "missing-second", "report": "missing.md"},
                ],
            }
        ),
        encoding="utf-8",
    )
    partial_output = project / "partial-output"
    assert main(["check", str(partial_manifest), "--output-dir", str(partial_output)]) == 2
    assert not partial_output.exists()


def test_batch_verifier_fails_closed_on_linkage_and_structure_tampering(tmp_path: Path):
    manifest = _write_project(tmp_path, include_review=False)
    output = tmp_path / "output"
    assert main(["check", str(manifest), "--output-dir", str(output)]) == 0
    batch_path = output / "batch-certificate.json"
    child_path = output / "passing.audit.json"
    original_batch = json.loads(batch_path.read_text(encoding="utf-8"))
    original_child_text = child_path.read_text(encoding="utf-8")
    original_child = json.loads(original_child_text)

    def write_batch(payload: dict[str, Any]) -> list[str]:
        payload["certificate_sha256"] = digest_payload(payload)
        batch_path.write_text(json.dumps(payload), encoding="utf-8")
        return verify_certificate_file(batch_path, tmp_path)

    duplicate = copy.deepcopy(original_batch)
    duplicate_entry = copy.deepcopy(duplicate["experiments"][0])
    duplicate["experiments"].append(duplicate_entry)
    duplicate_errors = write_batch(duplicate)
    assert any("duplicate batch experiment" in error for error in duplicate_errors)
    assert any("duplicate child certificate" in error for error in duplicate_errors)

    wrong_summary = copy.deepcopy(original_batch)
    wrong_summary["status"] = "needs_review"
    wrong_summary["experiments"][0]["status"] = "needs_review"
    wrong_summary["experiments"][0]["findings"] = 7
    summary_errors = write_batch(wrong_summary)
    assert any("status mismatch" in error for error in summary_errors)
    assert any("finding count mismatch" in error for error in summary_errors)

    missing_child = copy.deepcopy(original_batch)
    child_path.rename(output / "passing.saved")
    assert any("child certificate is missing" in error for error in write_batch(missing_child))
    (output / "passing.saved").rename(child_path)

    child_path.write_text("not-json", encoding="utf-8")
    assert any("child certificate cannot be read" in error for error in write_batch(original_batch))
    child_path.write_text("[]", encoding="utf-8")
    assert any("child certificate must be" in error for error in write_batch(original_batch))
    child_path.write_text(original_child_text, encoding="utf-8")

    def write_linked_child(child: dict[str, Any]) -> list[str]:
        child["certificate_sha256"] = digest_payload(child)
        child_path.write_text(json.dumps(child), encoding="utf-8")
        batch = copy.deepcopy(original_batch)
        batch["experiments"][0]["certificate_sha256"] = child["certificate_sha256"]
        return write_batch(batch)

    missing_artifact = copy.deepcopy(original_child)
    missing_artifact["artifacts"] = [
        artifact for artifact in missing_artifact["artifacts"] if artifact["role"] != "predictions"
    ]
    assert any(
        "manifest artifact is absent" in error for error in write_linked_child(missing_artifact)
    )

    unknown_role = copy.deepcopy(original_child)
    unknown_role["artifacts"][1]["role"] = "unknown"
    assert any(
        "role is absent from manifest" in error for error in write_linked_child(unknown_role)
    )

    duplicate_role = copy.deepcopy(original_child)
    duplicate_role["artifacts"].append(copy.deepcopy(duplicate_role["artifacts"][0]))
    assert any("duplicate artifact role" in error for error in write_linked_child(duplicate_role))

    wrong_filename = copy.deepcopy(original_child)
    wrong_filename["artifacts"][0]["filename"] = "wrong.md"
    assert any(
        "artifact filename mismatch" in error for error in write_linked_child(wrong_filename)
    )
    child_path.write_text(original_child_text, encoding="utf-8")

    predictions = tmp_path / "inputs" / "pass-predictions.csv"
    predictions.rename(tmp_path / "inputs" / "saved-predictions.csv")
    assert any(
        "artifact is missing" in error for error in write_batch(copy.deepcopy(original_batch))
    )
    (tmp_path / "inputs" / "saved-predictions.csv").rename(predictions)

    malformed_schema = copy.deepcopy(original_batch)
    malformed_schema.pop("tool_version")
    malformed_schema["certificate_sha256"] = digest_payload(malformed_schema)
    batch_path.write_text(json.dumps(malformed_schema), encoding="utf-8")
    assert any(
        "batch certificate schema violation" in error
        for error in verify_certificate_file(batch_path)
    )

    noncanonical = copy.deepcopy(original_batch)
    noncanonical["manifest"]["size_bytes"] = float("nan")
    batch_path.write_text(json.dumps(noncanonical), encoding="utf-8")
    assert any("not canonicalizable" in error for error in verify_certificate_file(batch_path))


def test_batch_manifest_loader_rejects_malformed_json_roots(tmp_path: Path):
    for index, content in enumerate(("not-json", "[]")):
        manifest = tmp_path / f"malformed-{index}.json"
        manifest.write_text(content, encoding="utf-8")
        assert main(["check", str(manifest), "--output-dir", str(tmp_path / "out")]) == 2


def test_project_check_is_available_from_public_package_api():
    import reprocheck
    from reprocheck.batch import run_project_check

    assert reprocheck.run_project_check is run_project_check
