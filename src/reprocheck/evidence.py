from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .metric_names import (
    canonical_metric,
    is_nonnegative_metric,
    is_unit_interval_metric,
    metric_family,
    scoped_metric_name,
)
from .models import MetricObservation


AVERAGING_MODES = {"auto", "binary", "macro", "weighted"}
PREDICTION_TASKS = {"classification", "regression"}


def load_metric_evidence(path: Path, selector: str | None = None) -> dict[str, MetricObservation]:
    context: dict[str, str] = {}
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        selected = _select_json(payload, selector) if selector else payload
        if not isinstance(selected, dict):
            raise ValueError("selected metrics JSON value must be an object")
        values = _clean_metrics(selected)
    else:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            if not reader.fieldnames:
                raise ValueError("metrics CSV must contain a header")
            if len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError("metrics CSV contains duplicate column names")
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                raise ValueError("metrics CSV contains a malformed row")
            if {"metric", "value"}.issubset(reader.fieldnames):
                if any(
                    row.get("metric") in {None, ""} or row.get("value") in {None, ""}
                    for row in rows
                ):
                    raise ValueError("metrics CSV contains an empty metric or value")
                values = _clean_metric_items((row["metric"], row["value"]) for row in rows)
            else:
                selected_row = _select_csv_row(rows, list(reader.fieldnames), selector)
                values = _clean_metrics(selected_row)
                context = _csv_selector_context(selector)
    if not values:
        raise ValueError("selected evidence contains no numeric metrics")
    method = "provided" if selector is None else f"provided; selector={selector}"
    return {
        name: MetricObservation(value=value, source=path.name, method=method, context=context)
        for name, value in values.items()
    }


def load_metrics(path: Path, selector: str | None = None) -> dict[str, float]:
    return {
        name: item.value for name, item in load_metric_evidence(path, selector=selector).items()
    }


def metric_evidence_from_predictions(
    path: Path,
    *,
    positive_label: str | None = None,
    average: str = "auto",
    task: str = "classification",
) -> dict[str, MetricObservation]:
    if task not in PREDICTION_TASKS:
        raise ValueError(f"prediction task must be one of: {', '.join(sorted(PREDICTION_TASKS))}")
    if average not in AVERAGING_MODES:
        raise ValueError(f"average must be one of: {', '.join(sorted(AVERAGING_MODES))}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"y_true", "y_pred"}.issubset(reader.fieldnames):
            raise ValueError("predictions CSV must contain y_true,y_pred columns")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("predictions CSV contains duplicate column names")
        rows = list(reader)
        if any(
            None in row or row.get("y_true") is None or row.get("y_pred") is None for row in rows
        ):
            raise ValueError("predictions CSV contains a malformed row")
        pairs = [(row["y_true"], row["y_pred"]) for row in rows]
    if not pairs:
        raise ValueError("predictions CSV is empty")
    if task == "regression":
        return _regression_evidence(path, pairs)

    labels = sorted({value for pair in pairs for value in pair})
    if positive_label is not None and positive_label not in labels:
        raise ValueError(f"positive label is absent from predictions: {positive_label}")
    resolved_average = average
    if resolved_average == "auto":
        resolved_average = "binary" if len(labels) == 2 and positive_label is not None else "macro"
    if resolved_average == "binary" and len(labels) != 2:
        raise ValueError("binary averaging requires exactly two labels")
    if resolved_average == "binary" and positive_label is None:
        raise ValueError("binary averaging requires an explicit positive label")

    sample_count = len(pairs)
    accuracy = sum(actual == predicted for actual, predicted in pairs) / sample_count
    ci_low, ci_high = _wilson_interval(accuracy, sample_count)
    observations = {
        "accuracy": MetricObservation(
            value=accuracy,
            source=path.name,
            method="exact from y_true/y_pred",
            sample_count=sample_count,
            ci_low=ci_low,
            ci_high=ci_high,
            evidence_level="recomputed",
        )
    }

    per_label = {label: _per_label_metrics(pairs, label) for label in labels}
    selected: str | None = None
    if resolved_average == "binary":
        assert positive_label is not None
        selected = positive_label
        values = per_label[selected]
        method = f"binary; positive_label={selected}"
    else:
        weights = (
            {label: per_label[label]["support"] / sample_count for label in labels}
            if resolved_average == "weighted"
            else {label: 1 / len(labels) for label in labels}
        )
        values = {
            metric: sum(per_label[label][metric] * weights[label] for label in labels)
            for metric in ("precision", "recall", "f1")
        }
        method = f"{resolved_average}; labels={len(labels)}"

    for metric in ("precision", "recall", "f1"):
        observations[metric] = MetricObservation(
            value=float(values[metric]),
            source=path.name,
            method=method,
            sample_count=sample_count,
            evidence_level="recomputed",
        )
    if resolved_average == "binary":
        assert selected is not None
        observations["hard_dice"] = MetricObservation(
            value=float(values["f1"]),
            source=path.name,
            method=f"binary overlap; positive_label={selected}",
            sample_count=sample_count,
            evidence_level="recomputed",
        )
        observations["hard_iou"] = MetricObservation(
            value=_safe_ratio(values["tp"], values["tp"] + values["fp"] + values["fn"]),
            source=path.name,
            method=f"binary overlap; positive_label={selected}",
            sample_count=sample_count,
            evidence_level="recomputed",
        )
    if "y_score" in (reader.fieldnames or []):
        if positive_label is None:
            raise ValueError("probability metrics require an explicit positive label")
        if len(labels) > 2:
            raise ValueError("probability metrics currently require binary labels")
        scores = _probability_scores(rows)
        observations.update(_probability_evidence(path, pairs, scores, positive_label))
    return observations


def metrics_from_predictions(
    path: Path,
    *,
    positive_label: str | None = None,
    average: str = "auto",
    task: str = "classification",
) -> dict[str, float]:
    return {
        name: item.value
        for name, item in metric_evidence_from_predictions(
            path, positive_label=positive_label, average=average, task=task
        ).items()
    }


def _per_label_metrics(pairs: list[tuple[str, str]], label: str) -> dict[str, float]:
    counts = Counter(
        "tp"
        if actual == label and predicted == label
        else "fp"
        if actual != label and predicted == label
        else "fn"
        if actual == label and predicted != label
        else "tn"
        for actual, predicted in pairs
    )
    precision = _safe_ratio(counts["tp"], counts["tp"] + counts["fp"])
    recall = _safe_ratio(counts["tp"], counts["tp"] + counts["fn"])
    return {
        "precision": precision,
        "recall": recall,
        "f1": _safe_ratio(2 * precision * recall, precision + recall),
        "support": float(counts["tp"] + counts["fn"]),
        "tp": float(counts["tp"]),
        "fp": float(counts["fp"]),
        "fn": float(counts["fn"]),
    }


def _regression_evidence(path: Path, pairs: list[tuple[str, str]]) -> dict[str, MetricObservation]:
    try:
        numeric = [(float(actual), float(predicted)) for actual, predicted in pairs]
    except ValueError as error:
        raise ValueError("regression predictions must be finite numbers") from error
    if not all(math.isfinite(value) for pair in numeric for value in pair):
        raise ValueError("regression predictions must be finite numbers")
    sample_count = len(numeric)
    absolute_errors = [abs(actual - predicted) for actual, predicted in numeric]
    squared_errors = [(actual - predicted) ** 2 for actual, predicted in numeric]
    mean_actual = sum(actual for actual, _ in numeric) / sample_count
    total_variance = sum((actual - mean_actual) ** 2 for actual, _ in numeric)
    residual = sum(squared_errors)
    r2 = 1 - residual / total_variance if total_variance else float(residual == 0)
    values = {
        "mae": sum(absolute_errors) / sample_count,
        "rmse": math.sqrt(residual / sample_count),
        "r2": r2,
    }
    return {
        name: MetricObservation(
            value=value,
            source=path.name,
            method="exact regression metric from numeric y_true/y_pred",
            sample_count=sample_count,
            evidence_level="recomputed",
        )
        for name, value in values.items()
    }


def _probability_scores(rows: list[dict[str, str]]) -> list[float]:
    try:
        scores = [float(row["y_score"]) for row in rows]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("y_score values must be finite probabilities") from error
    if not all(math.isfinite(score) and 0 <= score <= 1 for score in scores):
        raise ValueError("y_score values must be finite probabilities between 0 and 1")
    return scores


def _probability_evidence(
    path: Path,
    pairs: list[tuple[str, str]],
    scores: list[float],
    positive_label: str,
) -> dict[str, MetricObservation]:
    labels = [int(actual == positive_label) for actual, _ in pairs]
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if not positive_count or not negative_count:
        raise ValueError("probability metrics require both positive and negative y_true labels")

    positive_scores = [score for label, score in zip(labels, scores) if label]
    negative_scores = [score for label, score in zip(labels, scores) if not label]
    favourable_pairs = sum(
        positive > negative for positive in positive_scores for negative in negative_scores
    )
    tied_pairs = sum(
        positive == negative for positive in positive_scores for negative in negative_scores
    )
    auroc = (favourable_pairs + 0.5 * tied_pairs) / (positive_count * negative_count)

    ordered = sorted(zip(scores, labels), key=lambda item: item[0], reverse=True)
    true_positives = 0
    false_positives = 0
    previous_recall = 0.0
    auprc = 0.0
    index = 0
    while index < len(ordered):
        score = ordered[index][0]
        group_labels: list[int] = []
        while index < len(ordered) and ordered[index][0] == score:
            group_labels.append(ordered[index][1])
            index += 1
        true_positives += sum(group_labels)
        false_positives += len(group_labels) - sum(group_labels)
        recall = true_positives / positive_count
        precision = true_positives / (true_positives + false_positives)
        auprc += (recall - previous_recall) * precision
        previous_recall = recall

    epsilon = math.ulp(1.0)
    clipped = [min(1 - epsilon, max(epsilon, score)) for score in scores]
    log_loss = -sum(
        label * math.log(score) + (1 - label) * math.log(1 - score)
        for label, score in zip(labels, clipped)
    ) / len(labels)
    brier = sum((score - label) ** 2 for label, score in zip(labels, scores)) / len(labels)
    values = {
        "auroc": auroc,
        "auprc": auprc,
        "log_loss": log_loss,
        "brier_score": brier,
    }
    return {
        name: MetricObservation(
            value=value,
            source=path.name,
            method=(
                "exact binary probability metric from y_true/y_score; "
                f"positive_label={positive_label}; log_loss_clip=machine_epsilon"
            ),
            sample_count=len(labels),
            evidence_level="recomputed",
        )
        for name, value in values.items()
    }


def _wilson_interval(proportion: float, sample_count: int, z: float = 1.96) -> tuple[float, float]:
    denominator = 1 + z**2 / sample_count
    center = (proportion + z**2 / (2 * sample_count)) / denominator
    margin = (
        z
        * math.sqrt(proportion * (1 - proportion) / sample_count + z**2 / (4 * sample_count**2))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _safe_ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _clean_metrics(values: Mapping[Any, Any]) -> dict[str, float]:
    return _clean_metric_items(_flatten_metric_items(values))


def _flatten_metric_items(
    values: Mapping[Any, Any], prefix: tuple[object, ...] = ()
) -> Iterable[tuple[object, object]]:
    for raw_name, raw_value in values.items():
        path = (*prefix, raw_name)
        if isinstance(raw_value, Mapping):
            if prefix or metric_family(raw_name) is not None:
                yield from _flatten_metric_items(raw_value, path)
            continue
        yield scoped_metric_name(path) or canonical_metric(raw_name), raw_value


def _clean_metric_items(values: Iterable[tuple[object, object]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw_name, raw_value in values:
        name = canonical_metric(raw_name)
        try:
            value = float(str(raw_value).replace(",", "."))
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            raise ValueError(f"metric {name} must be finite")
        if is_unit_interval_metric(name) and 1 < value <= 100:
            value /= 100.0
        if is_unit_interval_metric(name) and not 0 <= value <= 1:
            raise ValueError(f"metric {name} must be between 0 and 1")
        if name == "r2" and value > 1:
            raise ValueError("metric r2 must be no greater than 1")
        if is_nonnegative_metric(name) and value < 0:
            raise ValueError(f"metric {name} must be non-negative")
        if name in result:
            raise ValueError(f"duplicate metric after normalization: {name}")
        result[name] = value
    return result


def _select_json(payload: object, selector: str) -> object:
    current = payload
    for part in selector.split("."):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as error:
                raise ValueError(f"invalid JSON selector: {selector}") from error
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ValueError(f"invalid JSON selector: {selector}")
    return current


def _select_csv_row(
    rows: list[dict[str, str]], fieldnames: Sequence[str], selector: str | None
) -> dict[str, str]:
    if selector is None:
        if len(rows) != 1:
            raise ValueError("wide metrics CSV needs --metrics-selector column=value")
        return rows[0]
    if "=" not in selector:
        raise ValueError("CSV metrics selector must use column=value")
    column, expected = (part.strip() for part in selector.split("=", 1))
    if column not in fieldnames:
        raise ValueError(f"metrics selector column is absent: {column}")
    matches = [row for row in rows if row.get(column) == expected]
    if len(matches) != 1:
        raise ValueError(f"metrics selector must match exactly one row; matched {len(matches)}")
    return matches[0]


def _csv_selector_context(selector: str | None) -> dict[str, str]:
    if selector is None or "=" not in selector:
        return {}
    column, value = (part.strip() for part in selector.split("=", 1))
    key = re.sub(r"[^\w]+", "_", column.casefold(), flags=re.UNICODE).strip("_")
    aliases = {"architecture": "model", "model_name": "model", "average": "averaging"}
    return {aliases.get(key, key): value}
