from __future__ import annotations

import math

import pytest

from reprocheck.ml_extraction import (
    ScoredSpan,
    decode_scored_claim,
    enumerate_numeric_spans,
    score_tuple_predictions,
)


def test_numeric_spans_preserve_exact_source_and_normalize_percent() -> None:
    text = "Accuracy was 94.5%, while loss was 1,25 and count 1,200."
    spans = enumerate_numeric_spans(text)
    assert [(item.raw_text, item.value, item.unit) for item in spans] == [
        ("94.5%", 0.945, "percent"),
        ("1,25", 1.25, "scalar"),
        ("1,200", 1200.0, "scalar"),
    ]
    assert all(text[item.start : item.end] == item.raw_text for item in spans)


def test_constrained_decoder_builds_only_source_bound_tuple() -> None:
    text = "Model Alpha reached accuracy 94% on the hidden test split."
    numbers = enumerate_numeric_spans(text)
    claim = decode_scored_claim(
        claim_id="claim-1",
        source_text=text,
        numeric_span=numbers[0],
        metric_spans=[ScoredSpan("accuracy", 20, 28, 0.98)],
        context_spans={
            "model": [ScoredSpan("Alpha", 6, 11, 0.92)],
            "split": [ScoredSpan("test", 47, 51, 0.95)],
        },
        minimum_score=0.8,
    )
    assert claim is not None
    assert claim.metric == "accuracy"
    assert claim.value == 0.94
    assert claim.context == {"model": "Alpha", "split": "test"}
    assert claim.value_text == "94%"


def test_decoder_abstains_without_supported_metric_or_sufficient_score() -> None:
    text = "Score was 0.91."
    number = enumerate_numeric_spans(text)[0]
    assert (
        decode_scored_claim(
            claim_id="c",
            source_text=text,
            numeric_span=number,
            metric_spans=[ScoredSpan("unknown_metric", 0, 5, 0.99)],
            context_spans={},
        )
        is None
    )
    assert (
        decode_scored_claim(
            claim_id="c",
            source_text=text,
            numeric_span=number,
            metric_spans=[ScoredSpan("f1", 0, 5, 0.2)],
            context_spans={},
            minimum_score=0.8,
        )
        is None
    )


def test_scored_span_validation_errors() -> None:
    with pytest.raises(ValueError, match="span"):
        ScoredSpan("accuracy", -1, 4, 0.9)
    with pytest.raises(ValueError, match="between 0 and 1"):
        ScoredSpan("accuracy", 0, 4, math.nan)
    with pytest.raises(ValueError, match="non-empty"):
        ScoredSpan("", 0, 4, 0.9)


def test_decoder_rejects_span_that_does_not_bind_declared_text() -> None:
    text = "Accuracy: 0.9"
    number = enumerate_numeric_spans(text)[0]
    with pytest.raises(ValueError, match="does not bind"):
        decode_scored_claim(
            claim_id="c",
            source_text=text,
            numeric_span=number,
            metric_spans=[ScoredSpan("f1", 0, 8, 0.9, source_text="F1")],
            context_spans={},
        )


def test_tuple_scoring_reports_exact_and_field_level_results() -> None:
    expected = [
        {"claim_id": "a", "metric": "accuracy", "value": 0.9, "context": {"split": "test"}},
        {"claim_id": "b", "metric": "f1", "value": 0.8, "context": {}},
    ]
    predicted = [
        {"claim_id": "a", "metric": "accuracy", "value": 0.9, "context": {"split": "test"}},
        {"claim_id": "b", "metric": "precision", "value": 0.8, "context": {}},
    ]
    result = score_tuple_predictions(expected, predicted)
    assert result["exact_match"] == 0.5
    assert result["field_accuracy"]["metric"] == 0.5
    assert result["field_accuracy"]["value"] == 1.0
