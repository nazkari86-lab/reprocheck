from pathlib import Path
import random

import pytest

from reprocheck.leakage import (
    _character_ngrams,
    _find_near_text_overlap,
    _similarity_upper_bound,
    _text_similarity,
    _tokens,
    audit_csv_splits,
    find_text_matches,
    text_similarity,
)


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
        near_method="token_jaccard",
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
    with pytest.raises(ValueError, match="unsupported near-duplicate method"):
        audit_csv_splits(train, test, near_method="unknown")


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


def test_hybrid_near_overlap_detects_typos_that_token_jaccard_misses(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text(
        "id,text,label\n1,classification accuracy on validation dataset,A\n"
        "2,river temperature sensor calibration,B\n",
        encoding="utf-8",
    )
    test.write_text(
        "id,text,label\n3,clasification accuracy on the validation data set,A\n"
        "4,urban traffic congestion forecast,B\n",
        encoding="utf-8",
    )
    legacy = audit_csv_splits(
        train,
        test,
        identity_columns=["id"],
        text_column="text",
        near_threshold=0.8,
        near_method="token_jaccard",
    )
    hybrid = audit_csv_splits(
        train,
        test,
        identity_columns=["id"],
        text_column="text",
        near_threshold=0.8,
        near_method="hybrid_lexical_v1",
    )
    assert legacy.near_overlap_test_rows == 0
    assert hybrid.near_overlap_test_rows == 1
    assert hybrid.near_overlap_examples[0]["similarity"] >= 0.8
    assert hybrid.near_overlap_examples[0]["test_value"].startswith("clasification")


def test_near_overlap_tie_break_is_stable(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text(
        "id,text\n1,alpha beta gamma\n2,gamma beta alpha\n",
        encoding="utf-8",
    )
    test.write_text("id,text\n3,alpha beta gamma delta\n", encoding="utf-8")
    result = audit_csv_splits(
        train,
        test,
        identity_columns=["id"],
        text_column="text",
        near_threshold=0.7,
        near_method="token_jaccard",
    )
    assert result.near_overlap_examples[0]["train_value"] == "alpha beta gamma"


def test_zero_near_threshold_considers_zero_similarity_pairs(tmp_path: Path):
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    train.write_text("id,text\n1,alpha\n", encoding="utf-8")
    test.write_text("id,text\n2,omega\n", encoding="utf-8")

    result = audit_csv_splits(
        train,
        test,
        identity_columns=["id"],
        text_column="text",
        near_threshold=0,
    )

    assert result.near_overlap_test_rows == 1
    assert result.near_overlap_examples == [
        {"test_value": "omega", "train_value": "alpha", "similarity": 0.0}
    ]


def test_public_text_similarity_api_and_validation():
    import reprocheck

    assert reprocheck.text_similarity is text_similarity
    assert text_similarity("data set accuracy", "dataset accuracy") > text_similarity(
        "data set accuracy", "river temperature"
    )
    with pytest.raises(ValueError, match="unsupported near-duplicate method"):
        text_similarity("a", "b", method="unknown")


def test_ordered_similarity_and_public_index_statistics():
    assert text_similarity(
        "alpha beta gamma delta",
        "alpha beta delta gamma",
        "ordered_tokens_v1",
    ) > text_similarity(
        "alpha beta gamma delta",
        "delta gamma beta alpha",
        "ordered_tokens_v1",
    )

    result = find_text_matches(
        ["alpha beta", "river sensor"],
        ["alpha beta", "unrelated words"],
        threshold=0.8,
        method="ordered_tokens_v1",
    )
    assert [(match.test_index, match.train_index) for match in result.matches] == [(0, 0)]
    assert result.exhaustive_pairs == 4
    assert result.candidate_pairs == 1
    assert result.scored_pairs == 1


def test_ordered_index_prunes_common_token_without_losing_match():
    result = find_text_matches(
        ["shared alpha beta", "shared river sensor", "shared model card"],
        ["shared alpha beta", "shared unrelated sample"],
        threshold=0.8,
        method="ordered_tokens_v1",
    )

    assert [(match.test_index, match.train_index) for match in result.matches] == [(0, 0)]
    assert result.exhaustive_pairs == 6
    assert result.candidate_pairs == 6
    assert result.scored_pairs == 1


def test_public_text_match_search_validates_contract():
    with pytest.raises(ValueError, match="near threshold"):
        find_text_matches([], [], threshold=-0.1)
    with pytest.raises(ValueError, match="unsupported near-duplicate method"):
        find_text_matches([], [], method="unknown")
    with pytest.raises(ValueError, match="out of range"):
        find_text_matches(["a"], ["b"], excluded_test_indexes={1})


def test_text_match_search_is_available_from_public_package_api():
    import reprocheck

    assert reprocheck.find_text_matches is find_text_matches
    assert reprocheck.TextMatch.__name__ == "TextMatch"
    assert reprocheck.TextMatchSearch.__name__ == "TextMatchSearch"


def test_similarity_size_upper_bound_is_safe_for_random_feature_sets():
    randomizer = random.Random(20260809)
    universe = [f"f{index}" for index in range(20)]
    for _ in range(1_000):
        token_left = set(randomizer.sample(universe, randomizer.randrange(11)))
        token_right = set(randomizer.sample(universe, randomizer.randrange(11)))
        ngram_left = set(randomizer.sample(universe, randomizer.randrange(11)))
        ngram_right = set(randomizer.sample(universe, randomizer.randrange(11)))
        for method in ("token_jaccard", "hybrid_lexical_v1"):
            score = _text_similarity(
                token_left,
                token_right,
                ngram_left,
                ngram_right,
                method,
            )
            upper_bound = _similarity_upper_bound(
                token_left,
                token_right,
                ngram_left,
                ngram_right,
                method,
            )
            assert upper_bound + 1e-12 >= score


def test_indexed_hybrid_join_matches_exhaustive_pairwise_evaluation():
    randomizer = random.Random(117)
    vocabulary = ["glacier", "river", "school", "sensor", "north", "field", "model"]

    def sentence() -> str:
        words = randomizer.sample(vocabulary, randomizer.randint(2, 6))
        if randomizer.random() < 0.4:
            position = randomizer.randrange(len(words))
            words[position] = words[position][:-1] + "x"
        return " ".join(words)

    train_rows = [{"text": sentence()} for _ in range(35)]
    test_rows = [{"text": sentence()} for _ in range(25)]
    threshold = 0.62
    indexed_count, _ = _find_near_text_overlap(
        train_rows,
        test_rows,
        "text",
        threshold,
        "hybrid_lexical_v1",
        excluded_test_indexes=set(),
        example_limit=5,
    )
    exhaustive_count = sum(
        any(
            text_similarity(test["text"], train["text"], "hybrid_lexical_v1") >= threshold
            for train in train_rows
        )
        for test in test_rows
    )
    assert indexed_count == exhaustive_count

    # Exercise the same feature construction used by indexed scoring explicitly.
    sample = train_rows[0]["text"]
    assert _tokens(sample)
    assert _character_ngrams(sample)


def test_indexed_ordered_join_matches_exhaustive_pairwise_evaluation():
    randomizer = random.Random(20260810)
    vocabulary = ["glacier", "river", "school", "sensor", "north", "field", "model"]
    train = [" ".join(randomizer.choices(vocabulary, k=5)) for _ in range(40)]
    test = [" ".join(randomizer.choices(vocabulary, k=5)) for _ in range(30)]
    threshold = 0.7

    indexed = find_text_matches(train, test, threshold=threshold, method="ordered_tokens_v1")
    exhaustive = []
    for test_index, test_text in enumerate(test):
        scores = [
            text_similarity(test_text, train_text, "ordered_tokens_v1") for train_text in train
        ]
        best = max(range(len(scores)), key=lambda index: (scores[index], -index))
        if scores[best] >= threshold:
            exhaustive.append((test_index, best, scores[best]))
    assert [
        (match.test_index, match.train_index, match.similarity) for match in indexed.matches
    ] == exhaustive
