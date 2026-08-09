import json
import random
from pathlib import Path

import pytest

from reprocheck.certificate import digest_payload
from reprocheck.detection import detection_evidence
from reprocheck.evidence import metric_evidence_from_predictions


def test_perfect_multiclass_metrics_are_permutation_invariant(tmp_path: Path):
    labels = ["a", "b", "c"] * 20
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text(
        "y_true,y_pred\n" + "".join(f"{label},{label}\n" for label in labels),
        encoding="utf-8",
    )
    random.Random(42).shuffle(labels)
    second.write_text(
        "y_true,y_pred\n" + "".join(f"{label},{label}\n" for label in labels),
        encoding="utf-8",
    )
    first_metrics = metric_evidence_from_predictions(first, average="macro")
    second_metrics = metric_evidence_from_predictions(second, average="macro")
    assert {name: item.value for name, item in first_metrics.items()} == {
        name: item.value for name, item in second_metrics.items()
    }
    assert all(item.value == 1.0 for item in first_metrics.values())


def test_low_confidence_false_positive_after_full_recall_does_not_change_ap(
    tmp_path: Path,
):
    base = {
        "images": [
            {
                "id": "one",
                "ground_truth": [{"class_id": 0, "bbox": [0, 0, 10, 10]}],
                "predictions": [{"class_id": 0, "confidence": 0.9, "bbox": [0, 0, 10, 10]}],
            }
        ]
    }
    clean = tmp_path / "clean.json"
    noisy = tmp_path / "noisy.json"
    clean.write_text(json.dumps(base), encoding="utf-8")
    base["images"][0]["predictions"].append(
        {"class_id": 0, "confidence": 0.01, "bbox": [20, 20, 30, 30]}
    )
    noisy.write_text(json.dumps(base), encoding="utf-8")
    assert detection_evidence(clean)["map50_95"].value == pytest.approx(
        detection_evidence(noisy)["map50_95"].value
    )


def test_certificate_digest_is_key_order_independent_but_payload_sensitive():
    first = {"status": "passed", "created_at": "one", "findings": []}
    reordered = {"findings": [], "created_at": "two", "status": "passed"}
    changed = {"findings": ["tampered"], "created_at": "two", "status": "passed"}
    assert digest_payload(first) == digest_payload(reordered)
    assert digest_payload(first) != digest_payload(changed)
