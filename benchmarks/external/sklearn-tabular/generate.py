from __future__ import annotations

import csv
import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import sklearn
from sklearn.datasets import load_diabetes, load_iris
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
RANDOM_STATE = 2026


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _classification_case() -> tuple[dict[str, float], dict[str, object]]:
    dataset = load_iris()
    indexes = np.arange(len(dataset.target))
    train_indexes, test_indexes = train_test_split(
        indexes,
        test_size=0.3,
        random_state=RANDOM_STATE,
        stratify=dataset.target,
    )
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, random_state=RANDOM_STATE),
    )
    model.fit(dataset.data[train_indexes], dataset.target[train_indexes])
    predictions = model.predict(dataset.data[test_indexes])
    truth = dataset.target[test_indexes]
    metrics = {
        "accuracy": float(accuracy_score(truth, predictions)),
        "precision": float(precision_score(truth, predictions, average="macro", zero_division=0)),
        "recall": float(recall_score(truth, predictions, average="macro", zero_division=0)),
        "f1": float(f1_score(truth, predictions, average="macro", zero_division=0)),
    }
    _write_csv(
        ROOT / "iris_predictions.csv",
        ["y_true", "y_pred"],
        [
            [int(actual), int(predicted)]
            for actual, predicted in zip(truth, predictions, strict=True)
        ],
    )
    _write_csv(
        ROOT / "iris_train.csv",
        ["sample_id", "target"],
        [[int(index), int(dataset.target[index])] for index in train_indexes],
    )
    _write_csv(
        ROOT / "iris_test.csv",
        ["sample_id", "target"],
        [[int(index), int(dataset.target[index])] for index in test_indexes],
    )
    (ROOT / "iris_report.md").write_text(
        "# Iris classification result\n\n"
        + "\n".join(f"{name.title()}: {value:.12f}" for name, value in metrics.items())
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "source": "sklearn.datasets.load_iris",
        "samples": int(dataset.data.shape[0]),
        "features": int(dataset.data.shape[1]),
        "data_sha256": _canonical_sha256(dataset.data.tolist()),
        "target_sha256": _canonical_sha256(dataset.target.tolist()),
        "split": {
            "test_size": 0.3,
            "random_state": RANDOM_STATE,
            "stratified": True,
            "train_samples": len(train_indexes),
            "test_samples": len(test_indexes),
        },
        "model": "StandardScaler + LogisticRegression(max_iter=2000)",
        "metric_average": "macro",
    }
    return metrics, metadata


def _regression_case() -> tuple[dict[str, float], dict[str, object]]:
    dataset = load_diabetes()
    indexes = np.arange(len(dataset.target))
    train_indexes, test_indexes = train_test_split(
        indexes,
        test_size=0.25,
        random_state=RANDOM_STATE,
    )
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(dataset.data[train_indexes], dataset.target[train_indexes])
    predictions = model.predict(dataset.data[test_indexes])
    truth = dataset.target[test_indexes]
    metrics = {
        "mae": float(mean_absolute_error(truth, predictions)),
        "rmse": float(mean_squared_error(truth, predictions) ** 0.5),
        "r2": float(r2_score(truth, predictions)),
    }
    _write_csv(
        ROOT / "diabetes_predictions.csv",
        ["y_true", "y_pred"],
        [
            [format(float(actual), ".17g"), format(float(predicted), ".17g")]
            for actual, predicted in zip(truth, predictions, strict=True)
        ],
    )
    _write_csv(
        ROOT / "diabetes_train.csv",
        ["sample_id", "target"],
        [[int(index), format(float(dataset.target[index]), ".17g")] for index in train_indexes],
    )
    _write_csv(
        ROOT / "diabetes_test.csv",
        ["sample_id", "target"],
        [[int(index), format(float(dataset.target[index]), ".17g")] for index in test_indexes],
    )
    (ROOT / "diabetes_report.md").write_text(
        "# Diabetes regression result\n\n"
        + "\n".join(f"{name.upper()}: {value:.12f}" for name, value in metrics.items())
        + "\n",
        encoding="utf-8",
    )
    metadata = {
        "source": "sklearn.datasets.load_diabetes",
        "samples": int(dataset.data.shape[0]),
        "features": int(dataset.data.shape[1]),
        "data_sha256": _canonical_sha256(dataset.data.tolist()),
        "target_sha256": _canonical_sha256(dataset.target.tolist()),
        "split": {
            "test_size": 0.25,
            "random_state": RANDOM_STATE,
            "stratified": False,
            "train_samples": len(train_indexes),
            "test_samples": len(test_indexes),
        },
        "model": "StandardScaler + Ridge(alpha=1.0)",
    }
    return metrics, metadata


def _file_manifest() -> list[dict[str, object]]:
    descriptors = []
    for path in sorted(ROOT.iterdir()):
        if not path.is_file() or path.name == "manifest.json":
            continue
        payload = path.read_bytes()
        descriptors.append(
            {
                "file": path.name,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return descriptors


def main() -> None:
    iris_metrics, iris_metadata = _classification_case()
    diabetes_metrics, diabetes_metadata = _regression_case()
    _write_json(
        ROOT / "official_metrics.json",
        {"iris": iris_metrics, "diabetes": diabetes_metrics},
    )
    _write_json(
        ROOT / "manifest.json",
        {
            "schema": "reprocheck.external-benchmark.v1",
            "scope": "deterministic tabular classification and regression smoke benchmark",
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scikit_learn": sklearn.__version__,
            },
            "datasets": {"iris": iris_metadata, "diabetes": diabetes_metadata},
            "files": _file_manifest(),
        },
    )


if __name__ == "__main__":
    main()
