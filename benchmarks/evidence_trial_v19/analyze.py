from __future__ import annotations

import argparse
import json
from pathlib import Path

from reprocheck.evidence_trial import score_evidence_trial


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = json.loads(args.frozen_inputs.read_text(encoding="utf-8"))
    root = args.frozen_inputs.parent
    score_evidence_trial(
        gold_path=root / payload["gold"],
        arm_paths={name: root / path for name, path in payload["arms"].items()},
        protocol_path=root / payload["protocol"],
        registration_path=root / payload["registration"],
        output=args.output,
        bootstrap_samples=payload["bootstrap_samples"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
