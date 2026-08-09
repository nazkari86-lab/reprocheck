from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
OUTPUT = ROOT / "annotations.json"

DIRECT_ALIASES = {
    "accuracy": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "f1_score": "f1",
    "dice": "dice",
    "mean_iou": "miou",
    "miou": "miou",
    "iou": "iou",
    "rmse": "rmse",
    "mae": "mae",
    "r2": "r2",
}
FAMILY_WORDS = ("accuracy", "precision", "recall", "f1", "dice", "iou", "map", "rmse", "mae", "r2")

NARRATIVE_MONAI_CLAIMS = {
    "monai_model_zoo/models/multi_organ_segmentation/configs/metadata.json": [
        {"metric": "dice", "value": 0.88, "origin": "description", "review": "manual"}
    ],
    "monai_model_zoo/models/pancreas_ct_dints_segmentation/configs/metadata.json": [
        {"metric": "dice", "value": 0.62, "origin": "description", "review": "manual"}
    ],
    "monai_model_zoo/models/pathology_nuclei_segmentation_classification/configs/metadata.json": [
        {"metric": "dice", "value": 0.83, "origin": "description", "review": "manual"}
    ],
}

TRANSFORMERS_CLAIMS = {
    "transformers/examples/pytorch/audio-classification/README.md": [
        {"metric": "accuracy", "value": 0.9706, "origin": "line 142", "review": "manual"},
        {"metric": "accuracy", "value": 0.9826, "origin": "line 143", "review": "manual"},
        {"metric": "accuracy", "value": 0.9819, "origin": "line 144", "review": "manual"},
        {"metric": "accuracy", "value": 0.9757, "origin": "line 145", "review": "manual"},
        {"metric": "accuracy", "value": 0.7945, "origin": "line 146", "review": "manual"},
    ],
    "transformers/examples/pytorch/question-answering/README.md": [
        {"metric": "f1", "value": 0.8852, "origin": "line 58", "review": "manual"}
    ],
    "transformers/examples/pytorch/text-classification/README.md": [
        {
            "metric": "accuracy",
            "value": 0.7093812375249501,
            "origin": "line 250",
            "review": "manual",
        }
    ],
}

TENSORFLOW_NOTEBOOK_LABELS = {
    "classification.ipynb": ["random_seed_not_detected"],
    "keras_tuner.ipynb": ["random_seed_not_detected", "unparsed_notebook_cells"],
    "overfit_and_underfit.ipynb": [
        "random_seed_not_detected",
        "unparsed_notebook_cells",
    ],
    "regression.ipynb": ["unparsed_notebook_cells"],
    "save_and_load.ipynb": ["random_seed_not_detected", "unparsed_notebook_cells"],
    "text_classification.ipynb": ["random_seed_not_detected"],
    "text_classification_with_hub.ipynb": [
        "random_seed_not_detected",
        "unparsed_notebook_cells",
    ],
}


def _normalized(value: object) -> str:
    return re.sub(r"[^\w²]+", "_", str(value).strip().casefold()).strip("_")


def _annotated_metric(parts: tuple[object, ...]) -> str | None:
    normalized_parts = tuple(_normalized(part) for part in parts)
    start = None
    for index, part in enumerate(normalized_parts):
        words = set(part.split("_"))
        if part in DIRECT_ALIASES or words.intersection(FAMILY_WORDS):
            start = index
            break
    if start is None:
        return None
    scoped = "_".join(normalized_parts[start:])
    return DIRECT_ALIASES.get(scoped, scoped)


def _metric_leaves(value: object, path: tuple[object, ...] = ()) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            claims.extend(_metric_leaves(child, (*path, key)))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        metric = _annotated_metric(path)
        if metric is not None:
            numeric = float(value)
            claims.append(
                {
                    "metric": metric,
                    "value": numeric / 100 if 1 < numeric <= 100 else numeric,
                    "origin": "eval_metrics." + ".".join(str(part) for part in path),
                    "review": "rule_derived",
                }
            )
    return claims


def build() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    artifacts = []
    for entry in manifest["entries"]:
        if entry["kind"] != "artifact":
            continue
        local_path = entry["local_path"]
        source = SOURCES / local_path
        claims: list[dict[str, Any]] = []
        notebook_codes: list[str] | None = None
        if entry["repository"] == "monai_model_zoo":
            payload = json.loads(source.read_text(encoding="utf-8"))
            claims = _metric_leaves(payload.get("eval_metrics", {}))
            claims.extend(NARRATIVE_MONAI_CLAIMS.get(local_path, []))
            annotation_method = "eval_metrics_rule_plus_full_file_manual_narrative_review"
        elif entry["repository"] == "transformers":
            claims = TRANSFORMERS_CLAIMS.get(local_path, [])
            annotation_method = "full_file_manual_supported_metric_review"
        else:
            notebook_codes = TENSORFLOW_NOTEBOOK_LABELS[source.name]
            annotation_method = "single_internal_static_risk_review"
        artifacts.append(
            {
                "repository": entry["repository"],
                "local_path": local_path,
                "source_sha256": entry["sha256"],
                "expected_claims": sorted(
                    claims,
                    key=lambda item: (item["metric"], item["value"], item["origin"]),
                ),
                "expected_notebook_finding_codes": notebook_codes,
                "annotation_method": annotation_method,
            }
        )
    result = {
        "schema": "reprocheck.real-artifact-annotations.v1",
        "scope": "all supported numerical claims in complete frozen files",
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
        "artifacts": sorted(artifacts, key=lambda item: item["local_path"]),
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build or verify frozen corpus annotations")
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace annotations.json instead of checking the checked-in file",
    )
    args = parser.parse_args(argv)
    result = build()
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(serialized, encoding="utf-8")
        action = "wrote"
    else:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != serialized:
            print("ERROR: annotations.json differs; review and run with --write")
            return 1
        action = "verified"
    print(
        f"{action} artifacts={len(result['artifacts'])} "
        f"claims={sum(len(item['expected_claims']) for item in result['artifacts'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
