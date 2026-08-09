from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from reprocheck.audit import run_audit
from reprocheck.version import __version__


ROOT = Path(__file__).resolve().parents[2]
TABULAR = ROOT / "benchmarks/external/sklearn-tabular"
YOLO = ROOT / "benchmarks/external/yolo26n-coco8"
Mutation = Callable[[Path], None]


def run(output: Path | None = None) -> dict[str, Any]:
    _verify_manifest(TABULAR)
    _verify_manifest(YOLO)
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="reprocheck-real-corruptions-") as directory:
        root = Path(directory)
        cases.extend(
            [
                _case(root, "iris_clean", "iris", None, None),
                _case(root, "diabetes_clean", "diabetes", None, None),
                _case(root, "yolo_clean", "yolo", None, None),
                _case(
                    root,
                    "iris_report_claim",
                    "iris",
                    _mutate_iris_report,
                    "claim_metric_mismatch",
                ),
                _case(
                    root,
                    "iris_predictions",
                    "iris",
                    _mutate_iris_predictions,
                    "metric_evidence_conflict",
                ),
                _case(
                    root,
                    "iris_split_overlap",
                    "iris",
                    _mutate_iris_split,
                    "exact_split_overlap",
                ),
                _case(
                    root,
                    "iris_supplied_metric",
                    "iris",
                    _mutate_iris_metric,
                    "metric_evidence_conflict",
                ),
                _case(
                    root,
                    "diabetes_report_claim",
                    "diabetes",
                    _mutate_diabetes_report,
                    "claim_metric_mismatch",
                ),
                _case(
                    root,
                    "diabetes_predictions",
                    "diabetes",
                    _mutate_diabetes_predictions,
                    "metric_evidence_conflict",
                ),
                _case(
                    root,
                    "yolo_report_claim",
                    "yolo",
                    _mutate_yolo_report,
                    "claim_metric_mismatch",
                ),
                _case(
                    root,
                    "yolo_detections",
                    "yolo",
                    _mutate_yolo_detections,
                    "metric_evidence_conflict",
                ),
            ]
        )

    corruptions = [case for case in cases if case["expected_code"]]
    controls = [case for case in cases if not case["expected_code"]]
    result = {
        "schema": "reprocheck.real-corruptions-result.v1",
        "tool_version": __version__,
        "cases": cases,
        "summary": {
            "corruptions": len(corruptions),
            "negative_controls": len(controls),
            "corruption_detection_sensitivity": sum(case["passed"] for case in corruptions)
            / len(corruptions),
            "negative_control_specificity": sum(case["passed"] for case in controls)
            / len(controls),
            "unexpected_finding_count": sum(len(case["unexpected_codes"]) for case in cases),
        },
        "scientific_boundary": (
            "Real source-derived artifacts with controlled mutations; mutation selection and "
            "labels are author-designed development evidence, not a natural corruption sample."
        ),
    }
    if output:
        _write_json(output, result)
    return result


def _case(
    root: Path,
    case_id: str,
    domain: str,
    mutation: Mutation | None,
    expected_code: str | None,
) -> dict[str, Any]:
    source = YOLO if domain == "yolo" else TABULAR
    case_root = root / case_id
    shutil.copytree(source, case_root)
    if mutation:
        mutation(case_root)
    audit = _audit(case_root, domain)
    actual_codes = [finding["code"] for finding in audit.findings]
    expected_codes = [expected_code] if expected_code else []
    return {
        "id": case_id,
        "domain": domain,
        "expected_code": expected_code,
        "actual_codes": actual_codes,
        "unexpected_codes": sorted(set(actual_codes) - set(expected_codes)),
        "passed": expected_code in actual_codes if expected_code else not actual_codes,
    }


def _audit(root: Path, domain: str):
    if domain == "iris":
        return run_audit(
            report_path=root / "iris_report.md",
            metrics_path=root / "official_metrics.json",
            metrics_selector="iris",
            predictions_path=root / "iris_predictions.csv",
            train_path=root / "iris_train.csv",
            test_path=root / "iris_test.csv",
            label_column="target",
            identity_columns=["sample_id"],
            average="macro",
            tolerance=1e-9,
        )
    if domain == "diabetes":
        return run_audit(
            report_path=root / "diabetes_report.md",
            metrics_path=root / "official_metrics.json",
            metrics_selector="diabetes",
            predictions_path=root / "diabetes_predictions.csv",
            prediction_task="regression",
            train_path=root / "diabetes_train.csv",
            test_path=root / "diabetes_test.csv",
            label_column="target",
            identity_columns=["sample_id"],
            tolerance=1e-9,
        )
    return run_audit(
        report_path=root / "report.md",
        metrics_path=root / "official_metrics_flat.json",
        detections_path=root / "coco8_detections.json",
        tolerance=0.001,
    )


def _mutate_iris_report(root: Path) -> None:
    path = root / "iris_report.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("Accuracy: 0.933333333333", "Accuracy: 0.5"),
        encoding="utf-8",
    )


def _mutate_diabetes_report(root: Path) -> None:
    path = root / "diabetes_report.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("RMSE: 54.244807679520", "RMSE: 10.000000000000"),
        encoding="utf-8",
    )


def _mutate_yolo_report(root: Path) -> None:
    path = root / "report.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("mAP50: 0.906494", "mAP50: 0.100000"),
        encoding="utf-8",
    )


def _mutate_iris_predictions(root: Path) -> None:
    _mutate_prediction(root / "iris_predictions.csv", classification=True)


def _mutate_diabetes_predictions(root: Path) -> None:
    _mutate_prediction(root / "diabetes_predictions.csv", classification=False)


def _mutate_prediction(path: Path, *, classification: bool) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0])
    if classification:
        rows[0]["y_pred"] = "0" if rows[0]["y_pred"] != "0" else "1"
    else:
        rows[0]["y_pred"] = str(float(rows[0]["y_pred"]) + 100.0)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _mutate_iris_split(root: Path) -> None:
    train = (root / "iris_train.csv").read_text(encoding="utf-8").splitlines()
    test = (root / "iris_test.csv").read_text(encoding="utf-8").splitlines()
    test[1] = train[1]
    (root / "iris_test.csv").write_text("\n".join(test) + "\n", encoding="utf-8")


def _mutate_iris_metric(root: Path) -> None:
    path = root / "official_metrics.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["iris"]["accuracy"] = 0.5
    _write_json(path, payload)


def _mutate_yolo_detections(root: Path) -> None:
    path = root / "coco8_detections.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["images"][0]["predictions"] = []
    _write_json(path, payload)


def _verify_manifest(root: Path) -> None:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for descriptor in manifest["files"]:
        path = root / descriptor["file"]
        if path.stat().st_size != descriptor["size_bytes"] or _sha256(path) != descriptor["sha256"]:
            raise ValueError(f"source manifest mismatch: {path}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/real-corruptions.json"))
    args = parser.parse_args()
    benchmark = run(args.output)
    print(json.dumps(benchmark["summary"], sort_keys=True))
