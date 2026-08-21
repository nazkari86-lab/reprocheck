from __future__ import annotations

import argparse
import json
from pathlib import Path

from reprocheck.ml_annotation_packet import compare_annotation_reviews
from reprocheck.ml_contracts import canonical_contract_json


parser = argparse.ArgumentParser()
parser.add_argument("--reviewer-a", type=Path, required=True)
parser.add_argument("--reviewer-b", type=Path, required=True)
parser.add_argument("--mapping", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise SystemExit("comparison output already exists")
result = compare_annotation_reviews(
    json.loads(args.reviewer_a.read_text(encoding="utf-8")),
    json.loads(args.reviewer_b.read_text(encoding="utf-8")),
    json.loads(args.mapping.read_text(encoding="utf-8")),
)
args.output.write_text(canonical_contract_json(result) + "\n", encoding="utf-8")
print(
    f"blocks={result['block_count']} agreement={result['exact_agreement']:.4f} "
    f"disagreements={result['disagreement_count']}"
)
