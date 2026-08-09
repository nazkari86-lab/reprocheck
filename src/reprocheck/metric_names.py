from __future__ import annotations

import re


METRIC_ALIASES = {
    "accuracy": "accuracy",
    "acc": "accuracy",
    "точность": "accuracy",
    "precision": "precision",
    "точность класса": "precision",
    "recall": "recall",
    "полнота": "recall",
    "f1": "f1",
    "f1-score": "f1",
    "f1 score": "f1",
    "f1_score": "f1",
    "f-мера": "f1",
    "hard dice": "hard_dice",
    "hard_dice": "hard_dice",
    "dice score": "dice",
    "dice": "dice",
    "hard iou": "hard_iou",
    "hard_iou": "hard_iou",
    "intersection over union": "iou",
    "iou": "iou",
    "mean iou": "miou",
    "mean_iou": "miou",
    "miou": "miou",
    "boundary f1": "boundary_f1",
    "boundary_f1": "boundary_f1",
    "map50-95": "map50_95",
    "map50_95": "map50_95",
    "map 50-95": "map50_95",
    "map@0.50:0.95": "map50_95",
    "map50": "map50",
    "map 50": "map50",
    "map@0.50": "map50",
    "map75": "map75",
    "map 75": "map75",
    "map@0.75": "map75",
    "average precision": "ap",
    "ap": "ap",
    "ap50": "ap50",
    "ap 50": "ap50",
    "ap@0.50": "ap50",
    "ap75": "ap75",
    "ap 75": "ap75",
    "ap@0.75": "ap75",
    "average recall": "ar",
    "ar": "ar",
    "panoptic quality": "pq",
    "pq": "pq",
    "hausdorff95": "hausdorff95",
    "hausdorff 95": "hausdorff95",
    "assd": "assd",
    "rmse": "rmse",
    "mae": "mae",
    "mse": "mse",
    "mean squared error": "mse",
    "top-1 accuracy": "top1_accuracy",
    "top1 accuracy": "top1_accuracy",
    "top1_accuracy": "top1_accuracy",
    "top-5 accuracy": "top5_accuracy",
    "top5 accuracy": "top5_accuracy",
    "top5_accuracy": "top5_accuracy",
    "r²": "r2",
    "r2": "r2",
}

UNIT_INTERVAL_METRICS = {
    "accuracy",
    "precision",
    "recall",
    "f1",
    "hard_dice",
    "dice",
    "hard_iou",
    "iou",
    "miou",
    "boundary_f1",
    "map50_95",
    "map50",
    "map75",
    "ap",
    "ap50",
    "ap75",
    "ar",
    "pq",
    "top1_accuracy",
    "top5_accuracy",
}

NONNEGATIVE_METRICS = {"hausdorff95", "assd", "rmse", "mae", "mse"}

_CANONICAL_METRICS = set(METRIC_ALIASES.values())


def canonical_metric(name: object) -> str:
    raw = str(name).strip().casefold()
    if raw in METRIC_ALIASES:
        return METRIC_ALIASES[raw]
    normalized = re.sub(r"[^\w²]+", "_", raw, flags=re.UNICODE).strip("_")
    return METRIC_ALIASES.get(normalized, normalized)


def metric_family(name: object) -> str | None:
    canonical = canonical_metric(name)
    if canonical in _CANONICAL_METRICS:
        return canonical
    readable = re.sub(r"[^\w²]+", " ", canonical.replace("_", " "), flags=re.UNICODE).strip()
    if re.search(r"\bmap\b", readable):
        if re.search(r"\b50\s+95\b", readable):
            return "map50_95"
        if re.search(r"\b75\b", readable):
            return "map75"
        if re.search(r"\b50\b", readable):
            return "map50"
    for alias in sorted(METRIC_ALIASES, key=len, reverse=True):
        normalized_alias = re.sub(
            r"[^\w²]+", " ", alias.casefold().replace("_", " "), flags=re.UNICODE
        ).strip()
        if normalized_alias and re.search(rf"(?<!\w){re.escape(normalized_alias)}(?!\w)", readable):
            return METRIC_ALIASES[alias]
    return None


def is_unit_interval_metric(name: object) -> bool:
    return metric_family(name) in UNIT_INTERVAL_METRICS


def is_nonnegative_metric(name: object) -> bool:
    return metric_family(name) in NONNEGATIVE_METRICS


def scoped_metric_name(parts: list[object] | tuple[object, ...]) -> str | None:
    for index, part in enumerate(parts):
        if metric_family(part) is not None:
            return canonical_metric("_".join(str(value) for value in parts[index:]))
    return None
