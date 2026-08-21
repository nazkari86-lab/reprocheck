from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from reprocheck.ml_contracts import canonical_contract_json
from reprocheck.ml_silver_experiment import build_silver_pairs, run_silver_experiment


parser = argparse.ArgumentParser()
parser.add_argument("--corpus", type=Path, required=True)
parser.add_argument("--mapping", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--seed", type=int, default=20260821)
parser.add_argument("--bootstrap-samples", type=int, default=1000)
args = parser.parse_args()
if args.output_dir.exists():
    raise SystemExit("silver experiment output already exists")
corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
rows, split = build_silver_pairs(corpus, mapping, seed=args.seed)
report, model = run_silver_experiment(
    rows,
    split,
    corpus_sha256=hashlib.sha256(canonical_contract_json(corpus).encode()).hexdigest(),
    seed=args.seed,
    bootstrap_samples=args.bootstrap_samples,
)
args.output_dir.mkdir(parents=True)
for name, value in (
    ("pairs.json", rows),
    ("split.json", split),
    ("model.json", model),
    ("report.json", report),
):
    (args.output_dir / name).write_text(canonical_contract_json(value) + "\n", encoding="utf-8")
print(
    f"pairs={len(rows)} owners={report['owner_count']} "
    f"test_f1={report['results']['full_pair']['test']['f1']:.4f} "
    f"test_auroc={report['results']['full_pair']['test']['auroc']:.4f}"
)
