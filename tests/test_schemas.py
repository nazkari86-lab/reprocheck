import json
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from reprocheck.audit import run_audit


def _schema(name: str) -> dict:
    resource = files("reprocheck").joinpath("schemas", name)
    return json.loads(resource.read_text(encoding="utf-8"))


def test_generated_audit_matches_published_schema(tmp_path: Path):
    report = tmp_path / "report.md"
    predictions = tmp_path / "predictions.csv"
    report.write_text("Accuracy: 100%", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n1,1\n", encoding="utf-8")
    result = run_audit(report_path=report, predictions_path=predictions)
    schema = _schema("audit-report-v1.2.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.to_dict())


def test_audit_schema_rejects_malformed_nested_audits(tmp_path: Path):
    report = tmp_path / "report.md"
    report.write_text("No metric claim.", encoding="utf-8")
    payload = run_audit(report_path=report).to_dict()
    validator = Draft202012Validator(_schema("audit-report-v1.2.schema.json"))

    payload["leakage"] = {"exact_overlap_rate": 2}
    with pytest.raises(ValidationError):
        validator.validate(payload)

    payload["leakage"] = None
    payload["notebook"] = {"code_cells": -1}
    with pytest.raises(ValidationError):
        validator.validate(payload)


def test_detection_contract_schema_accepts_minimal_evidence():
    payload = {
        "evaluation": {
            "ap_method": "coco_101_mean",
            "matching_method": "confidence_greedy",
        },
        "images": [
            {
                "id": "one",
                "ground_truth": [{"class_id": 0, "bbox": [0, 0, 10, 10]}],
                "predictions": [
                    {
                        "class_id": 0,
                        "confidence": 0.9,
                        "bbox": [0, 0, 10, 10],
                    }
                ],
            }
        ],
    }
    schema = _schema("detections-v1.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
