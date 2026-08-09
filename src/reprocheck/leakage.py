from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from .models import LeakageAudit


def audit_csv_splits(
    train_path: Path,
    test_path: Path,
    *,
    label_column: str | None = None,
    group_column: str | None = None,
    identity_columns: list[str] | None = None,
    text_column: str | None = None,
    near_threshold: float = 0.9,
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
    *,
    excluded_test_indexes: set[int],
    example_limit: int,
) -> tuple[int, list[dict[str, object]]]:
    train_tokens = [_tokens(row[text_column]) for row in train_rows]
    index: dict[str, set[int]] = {}
    for row_index, tokens in enumerate(train_tokens):
        for token in tokens:
            index.setdefault(token, set()).add(row_index)

    matches: list[dict[str, object]] = []
    match_count = 0
    for test_index, row in enumerate(test_rows):
        if test_index in excluded_test_indexes:
            continue
        tokens = _tokens(row[text_column])
        if not tokens:
            continue
        candidates = set().union(*(index.get(token, set()) for token in tokens))
        best_index = -1
        best_score = 0.0
        for train_index in candidates:
            union = tokens | train_tokens[train_index]
            score = len(tokens & train_tokens[train_index]) / len(union) if union else 0.0
            if score > best_score:
                best_score = score
                best_index = train_index
        if best_score >= threshold:
            match_count += 1
            if len(matches) < example_limit:
                matches.append(
                    {
                        "test_value": row[text_column],
                        "train_value": train_rows[best_index][text_column],
                        "similarity": round(best_score, 6),
                    }
                )
    return match_count, matches


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"\w+", _normalize(value), flags=re.UNICODE))
