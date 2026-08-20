import hashlib
import json
import shutil
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from reprocheck.study import (
    _artifact_annotations,
    _format_json_claims,
    _format_table_claims,
    _load_object,
    _manifest_artifacts,
    _mutate_metric,
    _mutation_study,
    _mutation_variants,
    _quantile,
    _repository_commits,
    _swap_metrics,
    run_real_artifact_study,
    study_passed,
    validate_study_result,
)


PROJECT_ROOT = Path(__file__).parents[1]
CORPUS = PROJECT_ROOT / "benchmarks" / "real_artifacts"


def test_real_artifact_study_fails_closed_on_incomplete_historical_labels(tmp_path: Path):
    output = tmp_path / "study.json"
    result = run_real_artifact_study(
        CORPUS,
        output,
        repeats=1,
        bootstrap_samples=200,
    )
    assert not study_passed(result)
    assert result["corpus"] == {
        "artifacts": 60,
        "repositories": 3,
        "repository_commits": {
            "monai_model_zoo": "b9e4d04bb2a073110bde9e5c05c9690241e938b6",
            "tensorflow_docs": "35e0922e059d7bc6d515a83e03a7494f0640c314",
            "transformers": "e8ea728a3eeeb903e77c7d1bd29267c80a1be71f",
        },
        "source_manifest_sha256": hashlib.sha256(
            (CORPUS / "source_manifest.json").read_bytes()
        ).hexdigest(),
        "annotations_sha256": hashlib.sha256(
            (CORPUS / "annotations.json").read_bytes()
        ).hexdigest(),
        "annotated_claims": 40,
        "claim_bearing_artifacts": 24,
        "notebooks": 7,
        "reviewers": {
            "internal_reviewers": 1,
            "independent_external_reviewers": 0,
            "adjudication": False,
        },
        "limitations": [
            "MONAI eval_metrics labels are rule-derived from explicit JSON fields.",
            "Narrative and Transformers labels have one internal reviewer only.",
            "TensorFlow labels are static risk indicators, not proven methodological defects.",
        ],
    }
    assert result["reprocheck"]["tp"] == 40
    assert result["reprocheck"]["fp"] == 58
    assert result["reprocheck"]["fn"] == 0
    assert result["reprocheck"]["precision"] == pytest.approx(40 / 98)
    assert result["naive_inline_baseline"]["recall"] == 0.2
    assert result["format_aware_baseline"]["recall"] == 1.0
    assert result["paired_claim_recall_delta"]["paired_bootstrap_95"][0] > 0
    assert result["paired_claim_recall_delta_vs_format_aware"] == {
        "mean_artifact_recall_delta": 0.0,
        "paired_bootstrap_95": [0.0, 0.0],
        "bootstrap_samples": 200,
        "seed": 2026,
    }
    assert result["mutation_detection"]["cases"] == 130
    assert result["mutation_detection"]["defect_cases"] == 67
    assert result["mutation_detection"]["negative_control_cases"] == 63
    assert result["mutation_detection"]["reprocheck"]["defect_detection_rate"] == 1.0
    assert result["mutation_detection"]["reprocheck"]["negative_control_correct_rate"] == 1.0
    assert result["mutation_detection"]["format_aware_baseline"]["defect_detection_rate"] == 1.0
    assert (
        result["mutation_detection"]["format_aware_baseline"]["negative_control_correct_rate"]
        == 1.0
    )
    assert result["mutation_detection"]["naive_inline_baseline"]["defects_detected"] == 8
    assert output.is_file()

    schema = json.loads(
        files("reprocheck")
        .joinpath("schemas/real-study-v2.schema.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result)

    malformed = json.loads(json.dumps(result))
    malformed["mutation_detection"].pop("defect_cases")
    with pytest.raises(ValueError, match="invalid real-artifact study result"):
        validate_study_result(malformed)
    with pytest.raises(ValueError, match="unsupported real-artifact study schema"):
        validate_study_result({"schema_version": "unknown"})


def test_real_artifact_study_fails_closed_on_invalid_controls_and_tampering(tmp_path: Path):
    with pytest.raises(ValueError, match="must be positive"):
        run_real_artifact_study(CORPUS, repeats=0)
    with pytest.raises(ValueError, match="must be positive"):
        run_real_artifact_study(CORPUS, bootstrap_samples=0)

    copied = tmp_path / "corpus"
    shutil.copytree(CORPUS, copied)
    annotations = json.loads((copied / "annotations.json").read_text(encoding="utf-8"))
    source = copied / "sources" / annotations["artifacts"][0]["local_path"]
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_real_artifact_study(copied, repeats=1, bootstrap_samples=10)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("{", "cannot read real-artifact file"),
        ("[]", "must be a JSON object"),
    ],
)
def test_study_json_loader_rejects_malformed_roots(tmp_path: Path, payload: str, message: str):
    path = tmp_path / "invalid.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        _load_object(path)


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        ({}, "must declare repositories"),
        ({"repositories": [None]}, "entry must be an object"),
        ({"repositories": [{"id": "", "commit": "0" * 40}]}, "must declare an id"),
        ({"repositories": [{"id": "repo", "commit": "main"}]}, "invalid commit"),
        (
            {
                "repositories": [
                    {"id": "repo", "commit": "0" * 40},
                    {"id": "repo", "commit": "1" * 40},
                ]
            },
            "duplicate real-artifact repository",
        ),
    ],
)
def test_study_rejects_unpinned_or_ambiguous_repository_metadata(
    manifest: dict[str, object], message: str
):
    with pytest.raises(ValueError, match=message):
        _repository_commits(manifest)


def _manifest_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "kind": "artifact",
        "local_path": "repo/report.json",
        "repository": "repo",
        "size_bytes": 1,
        "sha256": "0" * 64,
    }
    entry.update(overrides)
    return entry


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        ({}, "entries array"),
        ({"entries": [None]}, "entry must be an object"),
        ({"entries": []}, "contains no artifacts"),
        ({"entries": [_manifest_entry(local_path="")]}, "declare a local_path"),
        ({"entries": [_manifest_entry(repository="")]}, "has no repository"),
        ({"entries": [_manifest_entry(size_bytes=True)]}, "invalid size"),
        ({"entries": [_manifest_entry(sha256="bad")]}, "invalid sha256"),
        (
            {"entries": [_manifest_entry(), _manifest_entry()]},
            "duplicate real-artifact manifest path",
        ),
    ],
)
def test_study_rejects_malformed_or_duplicate_manifest_artifacts(
    manifest: dict[str, object], message: str
):
    with pytest.raises(ValueError, match=message):
        _manifest_artifacts(manifest)


def _annotation(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "local_path": "repo/report.json",
        "repository": "repo",
        "expected_claims": [],
    }
    item.update(overrides)
    return item


@pytest.mark.parametrize(
    ("annotations", "message"),
    [
        ({}, "artifacts array"),
        ({"artifacts": [None]}, "annotation must be an object"),
        ({"artifacts": []}, "contain no artifacts"),
        ({"artifacts": [_annotation(local_path="")]}, "declare a local_path"),
        ({"artifacts": [_annotation(repository="")]}, "has no repository"),
        ({"artifacts": [_annotation(expected_claims=None)]}, "invalid expected_claims"),
        (
            {"artifacts": [_annotation(), _annotation()]},
            "duplicate real-artifact annotation path",
        ),
    ],
)
def test_study_rejects_malformed_or_duplicate_annotations(
    annotations: dict[str, object], message: str
):
    with pytest.raises(ValueError, match=message):
        _artifact_annotations(annotations)


def test_real_artifact_study_rejects_annotation_structure_and_unsafe_paths(tmp_path: Path):
    copied = tmp_path / "corpus"
    shutil.copytree(CORPUS, copied)
    annotation_path = copied / "annotations.json"
    manifest_path = copied / "source_manifest.json"
    annotations = json.loads(annotation_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    invalid = {**annotations, "artifacts": {}}
    annotation_path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(ValueError, match="artifacts array"):
        run_real_artifact_study(copied, repeats=1, bootstrap_samples=1)

    mismatched = {**annotations, "artifacts": annotations["artifacts"][:-1]}
    annotation_path.write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(ValueError, match="cover different files"):
        run_real_artifact_study(copied, repeats=1, bootstrap_samples=1)

    unsafe_annotations = json.loads(json.dumps(annotations))
    unsafe_manifest = json.loads(json.dumps(manifest))
    original_path = unsafe_annotations["artifacts"][0]["local_path"]
    unsafe_annotations["artifacts"][0]["local_path"] = "../outside.json"
    manifest_entry = next(
        item for item in unsafe_manifest["entries"] if item.get("local_path") == original_path
    )
    manifest_entry["local_path"] = "../outside.json"
    annotation_path.write_text(json.dumps(unsafe_annotations), encoding="utf-8")
    manifest_path.write_text(json.dumps(unsafe_manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="unsafe or missing"):
        run_real_artifact_study(copied, repeats=1, bootstrap_samples=1)

    bad_digest = json.loads(json.dumps(annotations))
    bad_digest["artifacts"][0]["source_sha256"] = "0" * 64
    annotation_path.write_text(json.dumps(bad_digest), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="annotation checksum mismatch"):
        run_real_artifact_study(copied, repeats=1, bootstrap_samples=1)


def test_metric_mutation_handles_nested_nonmetrics_and_percentage_scale():
    assert not _mutate_metric([], ("accuracy", 0.95))

    percentage = {"metadata": {"note": "reported"}, "accuracy": 95, "enabled": True}
    assert _mutate_metric(percentage, ("accuracy", 0.95))
    assert percentage["accuracy"] == pytest.approx(75.0)

    bounded = {"accuracy": 0.4}
    assert _mutate_metric(bounded, ("accuracy", 0.4))
    assert bounded["accuracy"] == pytest.approx(0.6)

    assert not _mutate_metric({"metadata": {"note": "none"}}, ("dice", 0.8))
    assert _quantile([3.0], 0.95) == 3.0


def test_format_aware_reference_handles_tables_and_rejects_non_numeric_json_leaves():
    assert _format_json_claims(
        {
            "eval_metrics": {
                "enabled": True,
                "dice": "not-a-number",
                "accuracy": "95",
            }
        }
    ) == [("accuracy", 0.95)]
    assert _format_table_claims("| Accuracy | Note |\n| ---: | --- |\n| 95% | unavailable |\n") == [
        ("accuracy", 0.95)
    ]


def test_mutation_variant_builder_rejects_colliding_or_missing_swap_targets():
    claim = {"metric": "accuracy", "value": 0.9, "review": "rule_derived"}
    with pytest.raises(ValueError, match="mutation key already exists"):
        _mutation_variants(
            {"eval_metrics": {"accuracy": 0.9, "injected_accuracy": 0.1}},
            [claim],
            "collision.json",
        )

    missing_second = {"metric": "dice", "value": 0.7, "review": "rule_derived"}
    with pytest.raises(ValueError, match="cannot swap mutation targets"):
        _mutation_variants(
            {"eval_metrics": {"accuracy": 0.9}},
            [claim, missing_second],
            "missing.json",
        )
    assert not _swap_metrics({}, ("accuracy", 0.9), ("dice", 0.7))


def test_mutation_study_rejects_an_annotation_target_absent_from_source(tmp_path: Path):
    local_path = "models/example/configs/metadata.json"
    source = tmp_path / "sources" / local_path
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({"eval_metrics": {"accuracy": 0.9}}), encoding="utf-8")
    annotations = [
        {
            "repository": "monai_model_zoo",
            "local_path": local_path,
            "expected_claims": [{"metric": "dice", "value": 0.8, "review": "rule_derived"}],
        }
    ]

    with pytest.raises(ValueError, match="cannot locate mutation target"):
        _mutation_study(tmp_path, annotations)
