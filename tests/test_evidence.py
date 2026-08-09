from pathlib import Path

import pytest

from reprocheck.evidence import (
    load_metric_evidence,
    load_metrics,
    metric_evidence_from_predictions,
    metrics_from_predictions,
)


def test_binary_metrics_are_recomputed(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred\n0,0\n0,1\n1,1\n1,1\n", encoding="utf-8")
    metrics = metrics_from_predictions(path, positive_label="1")
    assert metrics["accuracy"] == 0.75
    assert metrics["precision"] == 2 / 3
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 0.8
    assert metrics["hard_dice"] == 0.8
    assert metrics["hard_iou"] == 2 / 3


def test_auto_average_does_not_guess_binary_positive_label(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred\ncat,cat\ncat,dog\ndog,dog\n", encoding="utf-8")

    evidence = metric_evidence_from_predictions(path)

    assert evidence["f1"].method == "macro; labels=2"
    assert "hard_dice" not in evidence
    with pytest.raises(ValueError, match="explicit positive label"):
        metric_evidence_from_predictions(path, average="binary")


def test_multiclass_macro_metrics_and_accuracy_interval(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text(
        "y_true,y_pred\nA,A\nA,B\nB,B\nB,B\nC,C\nC,A\n",
        encoding="utf-8",
    )
    evidence = metric_evidence_from_predictions(path, average="macro")
    assert evidence["accuracy"].value == 4 / 6
    assert evidence["accuracy"].ci_low is not None
    assert evidence["accuracy"].ci_high is not None
    assert evidence["accuracy"].ci_low < evidence["accuracy"].value
    assert evidence["accuracy"].ci_high > evidence["accuracy"].value
    assert evidence["f1"].method == "macro; labels=3"


def test_binary_positive_label_is_explicit(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred\ncat,cat\ndog,cat\ndog,dog\n", encoding="utf-8")
    metrics = metric_evidence_from_predictions(path, positive_label="cat", average="binary")
    assert metrics["precision"].value == 0.5
    assert metrics["recall"].value == 1.0
    assert "positive_label=cat" in metrics["f1"].method


def test_selects_segmentation_metrics_from_wide_csv(tmp_path: Path):
    path = tmp_path / "metrics.csv"
    path.write_text(
        "experiment,hard_dice,hard_iou,note\n"
        "baseline,0.80,0.67,old\n"
        "compact,0.9036145,0.824176,current\n",
        encoding="utf-8",
    )
    evidence = load_metric_evidence(path, selector="experiment=compact")
    assert evidence["hard_dice"].value == 0.9036145
    assert evidence["hard_iou"].value == 0.824176
    assert "selector=experiment=compact" in evidence["hard_dice"].method


def test_selects_nested_json_metrics(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text(
        '{"variants":{"single_pass":{"test_metrics":{"hard_dice":0.9,"assd":12.5}}}}',
        encoding="utf-8",
    )
    evidence = load_metric_evidence(path, selector="variants.single_pass.test_metrics")
    assert evidence["hard_dice"].value == 0.9
    assert evidence["assd"].value == 12.5


def test_rejects_duplicate_normalized_metrics(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text('{"f1": 0.8, "f1_score": 0.8}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate metric"):
        load_metric_evidence(path)


def test_rejects_duplicate_csv_headers(tmp_path: Path):
    path = tmp_path / "metrics.csv"
    path.write_text("metric,value,value\naccuracy,0.9,0.8\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate column"):
        load_metric_evidence(path)


def test_regression_metrics_are_recomputed(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred\n1,1\n2,3\n3,2\n", encoding="utf-8")
    evidence = metric_evidence_from_predictions(path, task="regression")
    assert evidence["mae"].value == pytest.approx(2 / 3)
    assert evidence["rmse"].value == pytest.approx((2 / 3) ** 0.5)
    assert evidence["r2"].value == 0.0
    assert all(item.evidence_level == "recomputed" for item in evidence.values())


def test_binary_probability_metrics_are_recomputed(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text(
        "y_true,y_pred,y_score\n1,1,0.9\n0,1,0.8\n1,1,0.7\n0,0,0.1\n",
        encoding="utf-8",
    )

    evidence = metric_evidence_from_predictions(path, positive_label="1")

    assert evidence["auroc"].value == 0.75
    assert evidence["auprc"].value == pytest.approx(5 / 6)
    assert evidence["brier_score"].value == pytest.approx(0.1875)
    assert evidence["log_loss"].value == pytest.approx(0.5442084719221214)
    assert "positive_label=1" in evidence["auroc"].method


def test_probability_metrics_fail_closed_on_ambiguous_or_invalid_scores(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred,y_score\n0,0,0.1\n1,1,0.9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="explicit positive label"):
        metric_evidence_from_predictions(path)

    path.write_text("y_true,y_pred,y_score\n0,0,0.1\n1,1,1.2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="between 0 and 1"):
        metric_evidence_from_predictions(path, positive_label="1")

    path.write_text("y_true,y_pred,y_score\n1,1,0.8\n1,1,0.9\n", encoding="utf-8")
    with pytest.raises(ValueError, match="both positive and negative"):
        metric_evidence_from_predictions(path, positive_label="1")


def test_r2_can_be_negative_but_error_metrics_cannot(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text('{"r2": -2.5}', encoding="utf-8")
    assert load_metric_evidence(path)["r2"].value == -2.5
    path.write_text('{"rmse": -1}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-negative"):
        load_metric_evidence(path)


def test_prediction_contract_rejects_invalid_modes_and_rows(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("actual,predicted\n1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="y_true,y_pred"):
        metric_evidence_from_predictions(path)

    path.write_text("y_true,y_pred\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        metric_evidence_from_predictions(path)

    path.write_text("y_true,y_pred\nA,A\nB,B\nC,C\n", encoding="utf-8")
    with pytest.raises(ValueError, match="binary averaging"):
        metric_evidence_from_predictions(path, average="binary")
    with pytest.raises(ValueError, match="positive label"):
        metric_evidence_from_predictions(path, positive_label="missing")
    with pytest.raises(ValueError, match="average must be"):
        metric_evidence_from_predictions(path, average="invalid")
    with pytest.raises(ValueError, match="prediction task"):
        metric_evidence_from_predictions(path, task="invalid")


def test_regression_rejects_nonfinite_and_handles_constant_target(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred\nA,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="finite numbers"):
        metric_evidence_from_predictions(path, task="regression")
    path.write_text("y_true,y_pred\n1,nan\n", encoding="utf-8")
    with pytest.raises(ValueError, match="finite numbers"):
        metric_evidence_from_predictions(path, task="regression")

    path.write_text("y_true,y_pred\n2,2\n2,2\n", encoding="utf-8")
    assert metric_evidence_from_predictions(path, task="regression")["r2"].value == 1.0
    path.write_text("y_true,y_pred\n2,1\n2,1\n", encoding="utf-8")
    assert metric_evidence_from_predictions(path, task="regression")["r2"].value == 0.0


def test_metric_selectors_fail_closed(tmp_path: Path):
    path = tmp_path / "metrics.csv"
    path.write_text("experiment,accuracy\na,0.9\nb,0.8\n", encoding="utf-8")
    with pytest.raises(ValueError, match="needs --metrics-selector"):
        load_metric_evidence(path)
    with pytest.raises(ValueError, match="column=value"):
        load_metric_evidence(path, selector="experiment")
    with pytest.raises(ValueError, match="column is absent"):
        load_metric_evidence(path, selector="missing=a")
    with pytest.raises(ValueError, match="matched 0"):
        load_metric_evidence(path, selector="experiment=c")

    nested = tmp_path / "metrics.json"
    nested.write_text('{"runs": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON selector"):
        load_metric_evidence(nested, selector="runs.bad")


def test_metric_evidence_contract_edges(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text('{"accuracy": 95}', encoding="utf-8")
    assert load_metrics(path) == {"accuracy": 0.95}

    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be an object"):
        load_metric_evidence(path)

    path.write_text('{"note": "not numeric"}', encoding="utf-8")
    with pytest.raises(ValueError, match="no numeric metrics"):
        load_metric_evidence(path)

    path.write_text('{"accuracy": NaN}', encoding="utf-8")
    with pytest.raises(ValueError, match="must be finite"):
        load_metric_evidence(path)

    path.write_text('{"accuracy": -0.1}', encoding="utf-8")
    with pytest.raises(ValueError, match="between 0 and 1"):
        load_metric_evidence(path)

    path.write_text('{"r2": 1.1}', encoding="utf-8")
    with pytest.raises(ValueError, match="no greater than 1"):
        load_metric_evidence(path)


def test_metric_csv_contract_edges(tmp_path: Path):
    path = tmp_path / "metrics.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="contain a header"):
        load_metric_evidence(path)

    path.write_text("metric,value\naccuracy\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed row"):
        load_metric_evidence(path)

    path.write_text("metric,value\naccuracy,\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty metric or value"):
        load_metric_evidence(path)

    path.write_text("experiment,accuracy\nonly,0.8\n", encoding="utf-8")
    assert load_metric_evidence(path)["accuracy"].value == 0.8


def test_json_selectors_support_list_indexes_and_reject_missing_keys(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text('{"runs": [{"accuracy": 0.9}]}', encoding="utf-8")
    assert load_metric_evidence(path, selector="runs.0")["accuracy"].value == 0.9
    with pytest.raises(ValueError, match="invalid JSON selector"):
        load_metric_evidence(path, selector="missing.value")


def test_prediction_csv_rejects_duplicate_headers_and_malformed_rows(tmp_path: Path):
    path = tmp_path / "predictions.csv"
    path.write_text("y_true,y_pred,y_pred\n1,1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate column"):
        metric_evidence_from_predictions(path)

    path.write_text("y_true,y_pred\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed row"):
        metric_evidence_from_predictions(path)


def test_scoped_metric_ids_inherit_family_validation(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text('{"fold1_accuracy": 95, "val_mean_dice_tc": 85.59}', encoding="utf-8")
    evidence = load_metric_evidence(path)
    assert evidence["fold1_accuracy"].value == 0.95
    assert evidence["val_mean_dice_tc"].value == pytest.approx(0.8559)

    path.write_text('{"fold1_rmse": -1}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-negative"):
        load_metric_evidence(path)


def test_nested_metric_object_is_flattened_without_losing_scope(tmp_path: Path):
    path = tmp_path / "metrics.json"
    path.write_text(
        '{"eval_metrics":{"mean_dice":{"central gland":0.88,"peripheral zone":0.75}}}',
        encoding="utf-8",
    )
    evidence = load_metric_evidence(path, selector="eval_metrics")
    assert {name: item.value for name, item in evidence.items()} == {
        "mean_dice_central_gland": 0.88,
        "mean_dice_peripheral_zone": 0.75,
    }
