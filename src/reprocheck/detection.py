from __future__ import annotations

import json
import math
from collections import defaultdict
from bisect import bisect_right
from pathlib import Path
from typing import TypedDict

from .models import MetricObservation


IOU_THRESHOLDS = tuple(round(0.5 + index * 0.05, 2) for index in range(10))
AP_METHODS = {"coco_101_mean", "ultralytics_101_trapezoid"}
MATCHING_METHODS = {"confidence_greedy", "ultralytics_iou_greedy"}


class EvidenceBox(TypedDict):
    class_id: str
    bbox: list[float]
    confidence: float


class DetectionImage(TypedDict):
    id: str
    ground_truth: list[EvidenceBox]
    predictions: list[EvidenceBox]


def detection_evidence(path: Path) -> dict[str, MetricObservation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    images = _validate_payload(payload)
    evaluation = payload.get("evaluation", {})
    if not isinstance(evaluation, dict):
        raise ValueError("detection evaluation must be an object")
    ap_method = str(evaluation.get("ap_method", "coco_101_mean"))
    if ap_method not in AP_METHODS:
        raise ValueError(f"unsupported detection AP method: {ap_method}")
    matching_method = str(evaluation.get("matching_method", "confidence_greedy"))
    if matching_method not in MATCHING_METHODS:
        raise ValueError(f"unsupported detection matching method: {matching_method}")
    class_ids = sorted({item["class_id"] for image in images for item in image["ground_truth"]})
    if not class_ids:
        raise ValueError("detection evidence contains no ground-truth boxes")

    per_threshold = {
        threshold: _mean_ap(images, class_ids, threshold, ap_method, matching_method)
        for threshold in IOU_THRESHOLDS
    }
    values = {
        "map50_95": sum(per_threshold.values()) / len(per_threshold),
        "map50": per_threshold[0.5],
        "map75": per_threshold[0.75],
    }
    method = (
        "independent class-aware greedy matching; "
        f"matching={matching_method}; AP={ap_method}; IoU=0.50:0.05:0.95"
    )
    return {
        name: MetricObservation(
            value=value,
            source=path.name,
            method=method,
            sample_count=len(images),
            evidence_level="recomputed",
        )
        for name, value in values.items()
    }


def _validate_payload(payload: object) -> list[DetectionImage]:
    if not isinstance(payload, dict):
        raise ValueError("detection JSON must contain an images array")
    raw_images = payload.get("images")
    if not isinstance(raw_images, list):
        raise ValueError("detection JSON must contain an images array")
    images: list[DetectionImage] = []
    seen_ids: set[str] = set()
    for raw_image in raw_images:
        if not isinstance(raw_image, dict):
            raise ValueError("each detection image must be an object")
        image_id = str(raw_image.get("id", "")).strip()
        if not image_id or image_id in seen_ids:
            raise ValueError("detection image ids must be non-empty and unique")
        seen_ids.add(image_id)
        ground_truth = _validate_boxes(raw_image.get("ground_truth"), predictions=False)
        predictions = _validate_boxes(raw_image.get("predictions"), predictions=True)
        images.append(
            {
                "id": image_id,
                "ground_truth": ground_truth,
                "predictions": predictions,
            }
        )
    if not images:
        raise ValueError("detection evidence contains no images")
    return images


def _validate_boxes(value: object, *, predictions: bool) -> list[EvidenceBox]:
    if not isinstance(value, list):
        raise ValueError("ground_truth and predictions must be arrays")
    boxes: list[EvidenceBox] = []
    for raw_box in value:
        if not isinstance(raw_box, dict):
            raise ValueError("each box must be an object")
        bbox = raw_box.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError("each bbox must be [x1,y1,x2,y2]")
        try:
            coordinates = [float(item) for item in bbox]
        except (TypeError, ValueError) as error:
            raise ValueError("bbox coordinates must be numeric") from error
        if not all(math.isfinite(item) for item in coordinates):
            raise ValueError("bbox coordinates must be finite")
        if coordinates[2] <= coordinates[0] or coordinates[3] <= coordinates[1]:
            raise ValueError("bbox must have positive width and height")
        raw_class_id = raw_box.get("class_id")
        if raw_class_id is None or not str(raw_class_id).strip():
            raise ValueError("each box must contain a non-empty class_id")
        box = EvidenceBox(
            class_id=str(raw_class_id),
            bbox=coordinates,
            confidence=0.0,
        )
        if predictions:
            raw_confidence = raw_box.get("confidence")
            if raw_confidence is None:
                raise ValueError("prediction confidence must be numeric")
            try:
                confidence = float(raw_confidence)
            except (TypeError, ValueError) as error:
                raise ValueError("prediction confidence must be numeric") from error
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError("prediction confidence must be between 0 and 1")
            box["confidence"] = confidence
        boxes.append(box)
    return boxes


def _mean_ap(
    images: list[DetectionImage],
    class_ids: list[str],
    threshold: float,
    ap_method: str,
    matching_method: str,
) -> float:
    return sum(
        _class_ap(images, class_id, threshold, ap_method, matching_method) for class_id in class_ids
    ) / len(class_ids)


def _class_ap(
    images: list[DetectionImage],
    class_id: str,
    threshold: float,
    ap_method: str,
    matching_method: str,
) -> float:
    truth: dict[str, list[list[float]]] = defaultdict(list)
    predictions: list[tuple[float, str, int, list[float]]] = []
    for image in images:
        image_id = str(image["id"])
        for item in image["ground_truth"]:
            if item["class_id"] == class_id:
                truth[image_id].append(item["bbox"])
        class_prediction_index = 0
        for item in image["predictions"]:
            if item["class_id"] == class_id:
                predictions.append(
                    (
                        float(item["confidence"]),
                        image_id,
                        class_prediction_index,
                        item["bbox"],
                    )
                )
                class_prediction_index += 1

    truth_count = sum(len(items) for items in truth.values())
    predictions.sort(key=lambda item: item[0], reverse=True)
    if matching_method == "ultralytics_iou_greedy":
        matched_predictions = _ultralytics_matches(truth, predictions, threshold)
        true_positives = [
            int((image_id, local_index) in matched_predictions)
            for _, image_id, local_index, _ in predictions
        ]
        false_positives = [1 - value for value in true_positives]
        return _ap_from_flags(true_positives, false_positives, truth_count, ap_method)

    matched: dict[str, set[int]] = defaultdict(set)
    true_positives: list[int] = []
    false_positives: list[int] = []
    for _, image_id, _, predicted_box in predictions:
        candidates = [
            (index, _iou(predicted_box, actual_box))
            for index, actual_box in enumerate(truth[image_id])
            if index not in matched[image_id]
        ]
        best = max(candidates, key=lambda item: item[1], default=None)
        is_match = best is not None and best[1] >= threshold
        if best is not None and is_match:
            matched[image_id].add(best[0])
        true_positives.append(int(is_match))
        false_positives.append(int(not is_match))

    return _ap_from_flags(true_positives, false_positives, truth_count, ap_method)


def _ap_from_flags(
    true_positives: list[int],
    false_positives: list[int],
    truth_count: int,
    ap_method: str,
) -> float:

    cumulative_tp = _cumulative(true_positives)
    cumulative_fp = _cumulative(false_positives)
    recall = [value / truth_count for value in cumulative_tp]
    precision = [
        tp / (tp + fp) if tp + fp else 0.0
        for tp, fp in zip(cumulative_tp, cumulative_fp, strict=True)
    ]
    return _interpolated_ap(recall, precision, ap_method)


def _ultralytics_matches(
    truth: dict[str, list[list[float]]],
    predictions: list[tuple[float, str, int, list[float]]],
    threshold: float,
) -> set[tuple[str, int]]:
    by_image: dict[str, list[tuple[int, list[float]]]] = defaultdict(list)
    for _, image_id, local_index, box in predictions:
        by_image[image_id].append((local_index, box))

    matched: set[tuple[str, int]] = set()
    for image_id, image_predictions in by_image.items():
        candidates = [
            (truth_index, prediction_index, _iou(truth_box, prediction_box))
            for truth_index, truth_box in enumerate(truth[image_id])
            for prediction_index, prediction_box in image_predictions
        ]
        candidates = [item for item in candidates if item[2] >= threshold]
        candidates.sort(key=lambda item: item[2], reverse=True)
        unique_predictions: dict[int, tuple[int, int, float]] = {}
        for item in candidates:
            unique_predictions.setdefault(item[1], item)
        unique_truth: dict[int, tuple[int, int, float]] = {}
        for prediction_index in sorted(unique_predictions):
            item = unique_predictions[prediction_index]
            unique_truth.setdefault(item[0], item)
        for truth_index in sorted(unique_truth):
            matched.add((image_id, unique_truth[truth_index][1]))
    return matched


def _cumulative(values: list[int]) -> list[int]:
    total = 0
    result = []
    for value in values:
        total += value
        result.append(total)
    return result


def _interpolated_ap(recall: list[float], precision: list[float], ap_method: str) -> float:
    if not recall:
        return 0.0
    if ap_method == "coco_101_mean":
        return (
            sum(
                max((p for r, p in zip(recall, precision, strict=True) if r >= level), default=0.0)
                for level in (index / 100 for index in range(101))
            )
            / 101
        )

    modified_recall = [0.0, *recall, recall[-1], 1.0]
    modified_precision = [1.0, *precision, 0.0, 0.0]
    for index in range(len(modified_precision) - 2, -1, -1):
        modified_precision[index] = max(modified_precision[index], modified_precision[index + 1])
    interpolated = [
        _linear_interpolate(level, modified_recall, modified_precision)
        for level in (index / 100 for index in range(101))
    ]
    return sum((interpolated[index] + interpolated[index + 1]) * 0.005 for index in range(100))


def _linear_interpolate(value: float, xs: list[float], ys: list[float]) -> float:
    right = bisect_right(xs, value)
    if right == 0:
        return ys[0]
    if right >= len(xs):
        return ys[-1]
    left = right - 1
    span = xs[right] - xs[left]
    if span == 0:
        return ys[right]
    fraction = (value - xs[left]) / span
    return ys[left] + fraction * (ys[right] - ys[left])


def _iou(first: list[float], second: list[float]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    first_area = (first[2] - first[0]) * (first[3] - first[1])
    second_area = (second[2] - second[0]) * (second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0
