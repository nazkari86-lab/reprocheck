from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import verify_ml_registration

parser = argparse.ArgumentParser()
parser.add_argument("registration", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
errors = verify_ml_registration(root, args.registration)
for error in errors:
    print(f"FAIL: {error}")
raise SystemExit(1 if errors else 0)
