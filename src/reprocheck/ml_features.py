from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Mapping


_TOKEN = re.compile(r"<num>|[^\W_]+(?:[.][^\W_]+)?", re.UNICODE)
_NUMBER = re.compile(r"(?<!\w)[+\-−]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+\-−]?\d+)?%?")


def normalize_ml_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().replace("−", "-")
    normalized = _NUMBER.sub(" <num> ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def sparse_text_features(value: str) -> Counter[str]:
    normalized = normalize_ml_text(value)
    tokens = _TOKEN.findall(normalized)
    features: Counter[str] = Counter()
    for token in tokens:
        features[f"w1:{token}"] += 1
    for index in range(len(tokens) - 1):
        features[f"w2:{tokens[index]}_{tokens[index + 1]}"] += 1
    compact = f" {normalized} "
    for size in (3, 4, 5):
        for index in range(max(0, len(compact) - size + 1)):
            features[f"c{size}:{compact[index : index + size]}"] += 1
    return features


def tfidf_vector(
    value: str,
    vocabulary: Mapping[str, int],
    inverse_document_frequency: tuple[float, ...],
) -> dict[int, float]:
    counts = sparse_text_features(value)
    weighted = {
        vocabulary[name]: (1 + math.log(count)) * inverse_document_frequency[vocabulary[name]]
        for name, count in counts.items()
        if name in vocabulary
    }
    norm = math.sqrt(sum(item * item for item in weighted.values()))
    if norm:
        return {index: item / norm for index, item in weighted.items()}
    return {}
