from __future__ import annotations

import argparse
from pathlib import Path

from reprocheck.ml_registration import register_ml_protocol


ROOT = Path(__file__).resolve().parent
FROZEN = [
    ROOT / name
    for name in (
        "protocol.json", "source-frame.json", "exclusions.json", "protocol.md",
        "annotation-guide.md", "model-card.md", "split.py", "train.py", "calibrate.py",
        "evaluate.py", "acquire.py", "annotate.py", "register.py", "verify-registration.py",
        "schema/registration-v1.schema.json"
    )
]

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
result = register_ml_protocol(ROOT, FROZEN, args.output)
print(result["registration_sha256"])
