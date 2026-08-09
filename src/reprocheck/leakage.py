from __future__ import annotations

import csv
import difflib
import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .models import LeakageAudit


NEAR_METHODS = {"token_jaccard", "hybrid_lexical_v1", "ordered_tokens_v1"}


@dataclass(frozen=True)
class TextMatch:
    test_index: int
    train_index: int
    similarity: float


@dataclass(frozen=True)
class TextMatchSearch:
    matches: tuple[TextMatch, ...]
    exhaustive_pairs: int
    candidate_pairs: int
    scored_pairs: int


def text_similarity(left: str, right: str, method: str = "hybrid_lexical_v1") -> float:
    if method not in NEAR_METHODS:
        raise ValueError(f"unsupported near-duplicate method: {method}")
    left_ordered = _ordered_tokens(left)
    right_ordered = _ordered_tokens(right)
    return _text_similarity(
        set(left_ordered),
        set(right_ordered),
        _character_ngrams(left) if method == "hybrid_lexical_v1" else set(),
        _character_ngrams(right) if method == "hybrid_lexical_v1" else set(),
        method,
        left_ordered=left_ordered,
        right_ordered=right_ordered,
    )


def find_text_matches(
    train_texts: list[str],
    test_texts: list[str],
    *,
    threshold: float = 0.8,
    method: str = "hybrid_lexical_v1",
    excluded_test_indexes: set[int] | None = None,
) -> TextMatchSearch:
    if not 0 <= threshold <= 1:
        raise ValueError("near threshold must be between 0 and 1")
    if method not in NEAR_METHODS:
        raise ValueError(f"unsupported near-duplicate method: {method}")

    excluded = excluded_test_indexes or set()
    if any(index < 0 or index >= len(test_texts) for index in excluded):
        raise ValueError("excluded test index is out of range")

    train_ordered = [_ordered_tokens(text) for text in train_texts]
    train_tokens = [set(tokens) for tokens in train_ordered]
    train_ngrams = (
        [_character_ngrams(text) for text in train_texts]
        if method == "hybrid_lexical_v1"
        else [set() for _ in train_texts]
    )
    token_index: dict[str, set[int]] = {}
    ngram_index: dict[str, set[int]] = {}
    for train_index, tokens in enumerate(train_tokens):
        for token in tokens:
            token_index.setdefault(token, set()).add(train_index)
        for ngram in train_ngrams[train_index]:
            ngram_index.setdefault(ngram, set()).add(train_index)

    matches: list[TextMatch] = []
    exhaustive_pairs = 0
    candidate_pairs = 0
    scored_pairs = 0
    for test_index, text in enumerate(test_texts):
        if test_index in excluded:
            continue
        ordered = _ordered_tokens(text)
        tokens = set(ordered)
        ngrams = _character_ngrams(text) if method == "hybrid_lexical_v1" else set()
        if threshold > 0 and not tokens and not ngrams:
            continue
        exhaustive_pairs += len(train_texts)
        candidates: set[int] = set(range(len(train_texts))) if threshold == 0 else set()
        if threshold > 0:
            for token in tokens:
                candidates.update(token_index.get(token, ()))
            for ngram in ngrams:
                candidates.update(ngram_index.get(ngram, ()))
        candidate_pairs += len(candidates)

        best_index = -1
        best_score = 0.0
        for train_index in sorted(candidates):
            if (
                _similarity_upper_bound(
                    tokens,
                    train_tokens[train_index],
                    ngrams,
                    train_ngrams[train_index],
                    method,
                    left_ordered_size=len(ordered),
                    right_ordered_size=len(train_ordered[train_index]),
                )
                < threshold
            ):
                continue
            scored_pairs += 1
            score = _text_similarity(
                tokens,
                train_tokens[train_index],
                ngrams,
                train_ngrams[train_index],
                method,
                left_ordered=ordered,
                right_ordered=train_ordered[train_index],
            )
            if best_index == -1 or score > best_score:
                best_score = score
                best_index = train_index
        if best_score >= threshold:
            matches.append(TextMatch(test_index, best_index, best_score))

    return TextMatchSearch(tuple(matches), exhaustive_pairs, candidate_pairs, scored_pairs)


def audit_csv_splits(
    train_path: Path,
    test_path: Path,
    *,
    label_column: str | None = None,
    group_column: str | None = None,
    identity_columns: list[str] | None = None,
    text_column: str | None = None,
    near_threshold: float = 0.8,
    near_method: str = "hybrid_lexical_v1",
    example_limit: int = 5,
) -> LeakageAudit:
    train_rows, train_fields = _read_csv(train_path)
    test_rows, test_fields = _read_csv(test_path)
    common = [field for field in train_fields if field in test_fields]
    excluded = {column for column in (label_column, group_column) if column}
    selected = identity_columns or [field for field in common if field not in excluded]
    if not selected:
        raise ValueError("no common identity columns remain after exclusions")
    missing = [field for field in selected if field not in common]
    if missing:
        raise ValueError(f"identity columns missing from one split: {', '.join(missing)}")
    if group_column and group_column not in common:
        raise ValueError(f"group column is missing from one split: {group_column}")
    if text_column and text_column not in common:
        raise ValueError(f"text column is missing from one split: {text_column}")
    if not 0 <= near_threshold <= 1:
        raise ValueError("near threshold must be between 0 and 1")
    if near_method not in NEAR_METHODS:
        raise ValueError(f"unsupported near-duplicate method: {near_method}")

    train_exact = [_fingerprint(row, selected, normalize=False) for row in train_rows]
    test_exact = [_fingerprint(row, selected, normalize=False) for row in test_rows]
    train_normalized = [_fingerprint(row, selected, normalize=True) for row in train_rows]
    test_normalized = [_fingerprint(row, selected, normalize=True) for row in test_rows]
    train_exact_set = set(train_exact)
    train_normalized_set = set(train_normalized)

    exact_indexes = [index for index, value in enumerate(test_exact) if value in train_exact_set]
    normalized_indexes = [
        index for index, value in enumerate(test_normalized) if value in train_normalized_set
    ]
    train_duplicates = sum(count - 1 for count in Counter(train_exact).values() if count > 1)
    test_duplicates = sum(count - 1 for count in Counter(test_exact).values() if count > 1)

    overlapping_groups: list[str] = []
    if group_column:
        train_groups = {_normalize(row[group_column]) for row in train_rows if row[group_column]}
        test_groups = {_normalize(row[group_column]) for row in test_rows if row[group_column]}
        overlapping_groups = sorted(train_groups & test_groups)

    near_count, near_examples = (
        _find_near_text_overlap(
            train_rows,
            test_rows,
            text_column,
            near_threshold,
            near_method,
            excluded_test_indexes=set(normalized_indexes),
            example_limit=example_limit,
        )
        if text_column
        else (0, [])
    )

    test_count = len(test_rows)
    return LeakageAudit(
        train_rows=len(train_rows),
        test_rows=test_count,
        identity_columns=selected,
        exact_overlap_test_rows=len(exact_indexes),
        normalized_overlap_test_rows=len(normalized_indexes),
        exact_overlap_rate=len(exact_indexes) / test_count if test_count else 0.0,
        normalized_overlap_rate=len(normalized_indexes) / test_count if test_count else 0.0,
        near_overlap_test_rows=near_count,
        near_overlap_rate=near_count / test_count if test_count else 0.0,
        train_duplicate_rows=train_duplicates,
        test_duplicate_rows=test_duplicates,
        group_column=group_column,
        overlapping_groups=overlapping_groups[:100],
        exact_overlap_examples=[
            {field: test_rows[index][field] for field in selected}
            for index in exact_indexes[:example_limit]
        ],
        normalized_overlap_examples=[
            {field: test_rows[index][field] for field in selected}
            for index in normalized_indexes[:example_limit]
        ],
        near_overlap_examples=near_examples,
    )


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path.name}")
        if any(not field for field in reader.fieldnames):
            raise ValueError(f"CSV has an empty header: {path.name}")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"CSV has duplicate headers: {path.name}")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV has a malformed row at line {line_number}: {path.name}")
            rows.append({key: value or "" for key, value in row.items()})
    if not rows:
        raise ValueError(f"CSV split is empty: {path.name}")
    return rows, list(reader.fieldnames)


def _fingerprint(row: dict[str, str], columns: list[str], *, normalize: bool) -> str:
    values = [_normalize(row[column]) if normalize else row[column] for column in columns]
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", " ", value)


def _find_near_text_overlap(
    train_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    text_column: str,
    threshold: float,
    method: str,
    *,
    excluded_test_indexes: set[int],
    example_limit: int,
) -> tuple[int, list[dict[str, object]]]:
    search = find_text_matches(
        [row[text_column] for row in train_rows],
        [row[text_column] for row in test_rows],
        threshold=threshold,
        method=method,
        excluded_test_indexes=excluded_test_indexes,
    )
    examples = [
        {
            "test_value": test_rows[match.test_index][text_column],
            "train_value": train_rows[match.train_index][text_column],
            "similarity": round(match.similarity, 6),
        }
        for match in search.matches[:example_limit]
    ]
    return len(search.matches), examples


def _tokens(value: str) -> set[str]:
    return set(_ordered_tokens(value))


def _ordered_tokens(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\w+", _normalize(value), flags=re.UNICODE))


def _character_ngrams(value: str, size: int = 3) -> set[str]:
    normalized = re.sub(r"[^\w]+", " ", _normalize(value), flags=re.UNICODE).strip()
    if len(normalized) < size:
        return set()
    padded = f" {normalized} "
    return {padded[index : index + size] for index in range(len(padded) - size + 1)}


def _text_similarity(
    left_tokens: set[str],
    right_tokens: set[str],
    left_ngrams: set[str],
    right_ngrams: set[str],
    method: str,
    *,
    left_ordered: tuple[str, ...] = (),
    right_ordered: tuple[str, ...] = (),
) -> float:
    token_union = left_tokens | right_tokens
    token_jaccard = len(left_tokens & right_tokens) / len(token_union) if token_union else 0.0
    if method == "token_jaccard":
        return token_jaccard
    if method == "ordered_tokens_v1":
        return difflib.SequenceMatcher(None, left_ordered, right_ordered, autojunk=False).ratio()
    ngram_total = len(left_ngrams) + len(right_ngrams)
    ngram_dice = 2 * len(left_ngrams & right_ngrams) / ngram_total if ngram_total else 0.0
    return max(token_jaccard, ngram_dice)


def _similarity_upper_bound(
    left_tokens: set[str],
    right_tokens: set[str],
    left_ngrams: set[str],
    right_ngrams: set[str],
    method: str,
    *,
    left_ordered_size: int = 0,
    right_ordered_size: int = 0,
) -> float:
    token_maximum = _jaccard_size_upper_bound(len(left_tokens), len(right_tokens))
    if method == "token_jaccard":
        return token_maximum
    if method == "ordered_tokens_v1":
        return _dice_size_upper_bound(left_ordered_size, right_ordered_size)
    ngram_maximum = _dice_size_upper_bound(len(left_ngrams), len(right_ngrams))
    return max(token_maximum, ngram_maximum)


def _jaccard_size_upper_bound(left: int, right: int) -> float:
    return min(left, right) / max(left, right) if left and right else 0.0


def _dice_size_upper_bound(left: int, right: int) -> float:
    return 2 * min(left, right) / (left + right) if left and right else 0.0
