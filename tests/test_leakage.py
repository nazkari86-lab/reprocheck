from pathlib import Path

import pytest

from reprocheck.leakage import audit_csv_splits


def test_detects_exact_normalized_and_group_overlap(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text(
        "id,patient,text,label\n1,p1,North School,A\n2,p2,Central Park,B\n", encoding="utf-8"
    )
    test.write_text(
        "id,patient,text,label\n1,p1,North School,A\n2,p3,  CENTRAL  PARK ,B\n", encoding="utf-8"
    )
    result = audit_csv_splits(
        train,
        test,
        label_column="label",
        group_column="patient",
        identity_columns=["text"],
    )
    assert result.exact_overlap_test_rows == 1
    assert result.normalized_overlap_test_rows == 2
    assert result.overlapping_groups == ["p1"]


def test_detects_heuristic_near_text_overlap(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text("id,text,label\n1,red brick school in almaty,A\n", encoding="utf-8")
    test.write_text("id,text,label\n2,red brick school located in almaty,A\n", encoding="utf-8")
    result = audit_csv_splits(
        train,
        test,
        label_column="label",
        identity_columns=["id"],
        text_column="text",
        near_threshold=0.8,
    )
    assert result.near_overlap_test_rows == 1
    assert result.near_overlap_examples[0]["similarity"] == pytest.approx(5 / 6, abs=1e-6)


def test_group_overlap_is_normalized(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text("id,patient,label\n1, Patient-A ,A\n", encoding="utf-8")
    test.write_text("id,patient,label\n2,patient-a,B\n", encoding="utf-8")
    result = audit_csv_splits(
        train,
        test,
        label_column="label",
        group_column="patient",
        identity_columns=["id"],
    )
    assert result.overlapping_groups == ["patient-a"]


def test_rejects_empty_and_malformed_splits(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text("id,label\n", encoding="utf-8")
    test.write_text("id,label\n1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="split is empty"):
        audit_csv_splits(train, test, label_column="label")

    train.write_text("id,id,label\n1,1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate headers"):
        audit_csv_splits(train, test, label_column="label")


def test_rejects_invalid_split_contracts(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text("label\nA\n", encoding="utf-8")
    test.write_text("label\nB\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no common identity columns"):
        audit_csv_splits(train, test, label_column="label")

    train.write_text("id,label\n1,A\n", encoding="utf-8")
    test.write_text("id,label\n2,B\n", encoding="utf-8")
    with pytest.raises(ValueError, match="identity columns missing"):
        audit_csv_splits(train, test, identity_columns=["missing"])
    with pytest.raises(ValueError, match="group column is missing"):
        audit_csv_splits(train, test, group_column="patient")
    with pytest.raises(ValueError, match="text column is missing"):
        audit_csv_splits(train, test, text_column="text")
    with pytest.raises(ValueError, match="near threshold"):
        audit_csv_splits(train, test, near_threshold=1.1)


def test_rejects_header_and_row_corruption(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    test.write_text("id,label\n2,B\n", encoding="utf-8")

    train.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="no header"):
        audit_csv_splits(train, test)

    train.write_text(",label\n1,A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty header"):
        audit_csv_splits(train, test)

    train.write_text("id,label\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed row"):
        audit_csv_splits(train, test)


def test_near_overlap_skips_exact_and_empty_text(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text("id,text,label\n1,red brick school,A\n", encoding="utf-8")
    test.write_text(
        "id,text,label\n1,red brick school,A\n2,,B\n",
        encoding="utf-8",
    )
    result = audit_csv_splits(
        train,
        test,
        identity_columns=["id"],
        text_column="text",
        near_threshold=0.5,
    )
    assert result.exact_overlap_test_rows == 1
    assert result.near_overlap_test_rows == 0
