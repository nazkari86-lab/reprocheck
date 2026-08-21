from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_annotation_ui import write_annotation_ui


parser = argparse.ArgumentParser()
parser.add_argument("--packet", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
write_annotation_ui(args.packet, args.output)
print(args.output)
