from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_annotation_packet import write_annotation_packets


parser = argparse.ArgumentParser()
parser.add_argument("--corpus", type=Path, required=True)
parser.add_argument("--sources-root", type=Path, required=True)
parser.add_argument("--output-dir", type=Path, required=True)
parser.add_argument("--seed", type=int, default=20260821)
args = parser.parse_args()
result = write_annotation_packets(args.corpus, args.sources_root, args.output_dir, seed=args.seed)
print(
    f"blocks={result['blocks']} candidates={result['candidates']} "
    f"sampled_negatives={result['sampled_negatives']}"
)
