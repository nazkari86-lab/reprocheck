import json
from pathlib import Path

import pytest

from reprocheck.detection import detection_evidence


def _write(path: Path, predictions: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "images": [
                    {
                        "id": "image-1",
                        "ground_truth": [{"class_id": 0, "bbox": [0, 0, 10, 10]}],
                        "predictions": predictions,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_perfect_detection_has_unit_map(tmp_path: Path):
    path = tmp_path / "detections.json"
    _write(path, [{"class_id": 0, "confidence": 0.9, "bbox": [0, 0, 10, 10]}])
    evidence = detection_evidence(path)
    assert evidence["map50_95"].value == 1.0
    assert evidence["map50"].value == 1.0
    assert evidence["map75"].value == 1.0


def test_high_confidence_false_positive_reduces_ap(tmp_path: Path):
    path = tmp_path / "detections.json"
    _write(
        path,
        [
            {"class_id": 0, "confidence": 0.95, "bbox": [20, 20, 30, 30]},
            {"class_id": 0, "confidence": 0.90, "bbox": [0, 0, 10, 10]},
        ],
    )
    evidence = detection_evidence(path)
    assert evidence["map50"].value == pytest.approx(0.5)


def test_rejects_invalid_bbox(tmp_path: Path):
    path = tmp_path / "detections.json"
    _write(path, [{"class_id": 0, "confidence": 0.9, "bbox": [10, 0, 0, 10]}])
    with pytest.raises(ValueError, match="positive width"):
        detection_evidence(path)


def test_rejects_missing_prediction_confidence(tmp_path: Path):
    path = tmp_path / "detections.json"
    _write(path, [{"class_id": 0, "bbox": [0, 0, 10, 10]}])
    with pytest.raises(ValueError, match="confidence must be numeric"):
        detection_evidence(path)


def test_ultralytics_trapezoid_convention_is_explicit(tmp_path: Path):
    path = tmp_path / "detections.json"
    path.write_text(
        json.dumps(
            {
                "evaluation": {"ap_method": "ultralytics_101_trapezoid"},
                "images": [
                    {
                        "id": "image-1",
                        "ground_truth": [{"class_id": 0, "bbox": [0, 0, 10, 10]}],
                        "predictions": [{"class_id": 0, "confidence": 0.9, "bbox": [0, 0, 10, 10]}],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    evidence = detection_evidence(path)
    assert evidence["map50"].value == pytest.approx(0.995)
    assert "ultralytics_101_trapezoid" in evidence["map50"].method


def test_ultralytics_matching_convention_is_exercised(tmp_path: Path):
    path = tmp_path / "detections.json"
    path.write_text(
        json.dumps(
            {
                "evaluation": {
                    "ap_method": "ultralytics_101_trapezoid",
                    "matching_method": "ultralytics_iou_greedy",
                },
                "images": [
                    {
                        "id": "image-1",
                        "ground_truth": [
                            {"class_id": 0, "bbox": [0, 0, 10, 10]},
                            {"class_id": 0, "bbox": [8, 0, 18, 10]},
                        ],
                        "predictions": [
                            {
                                "class_id": 0,
                                "confidence": 0.9,
                                "bbox": [0, 0, 10, 10],
                            },
                            {
                                "class_id": 0,
                                "confidence": 0.8,
                                "bbox": [8, 0, 18, 10],
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    evidence = detection_evidence(path)
    assert evidence["map50"].value == pytest.approx(0.995)
    assert "ultralytics_iou_greedy" in evidence["map50"].method


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "images array"),
        ({}, "images array"),
        ({"images": []}, "no images"),
        ({"images": ["bad"]}, "image must be an object"),
        (
            {
                "images": [
                    {"id": "same", "ground_truth": [], "predictions": []},
                    {"id": "same", "ground_truth": [], "predictions": []},
                ]
            },
            "unique",
        ),
        (
            {"evaluation": [], "images": [{"id": "x", "ground_truth": [], "predictions": []}]},
            "evaluation must be an object",
        ),
        (
            {
                "evaluation": {"ap_method": "unknown"},
                "images": [{"id": "x", "ground_truth": [], "predictions": []}],
            },
            "unsupported detection AP",
        ),
        (
            {
                "evaluation": {"matching_method": "unknown"},
                "images": [{"id": "x", "ground_truth": [], "predictions": []}],
            },
            "unsupported detection matching",
        ),
        (
            {"images": [{"id": "x", "ground_truth": [], "predictions": []}]},
            "no ground-truth",
        ),
    ],
)
def test_rejects_invalid_detection_containers(tmp_path: Path, payload, message):
    path = tmp_path / "detections.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        detection_evidence(path)


@pytest.mark.parametrize(
    ("box", "message"),
    [
        ("bad", "box must be an object"),
        ({"class_id": 0, "bbox": [0, 0, 1]}, "bbox must be"),
        ({"class_id": 0, "bbox": [0, 0, "bad", 1]}, "coordinates must be numeric"),
        ({"class_id": 0, "bbox": [0, 0, float("inf"), 1]}, "coordinates must be finite"),
        ({"bbox": [0, 0, 1, 1]}, "class_id"),
    ],
)
def test_rejects_invalid_ground_truth_boxes(tmp_path: Path, box, message):
    path = tmp_path / "detections.json"
    path.write_text(
        json.dumps({"images": [{"id": "x", "ground_truth": [box], "predictions": []}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        detection_evidence(path)


def test_rejects_out_of_range_confidence(tmp_path: Path):
    path = tmp_path / "detections.json"
    _write(path, [{"class_id": 0, "confidence": 1.1, "bbox": [0, 0, 10, 10]}])
    with pytest.raises(ValueError, match="between 0 and 1"):
        detection_evidence(path)
