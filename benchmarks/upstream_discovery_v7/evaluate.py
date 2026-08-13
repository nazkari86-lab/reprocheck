from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "upstream_discovery_v5" / "evaluate.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", default="zero-shot-frozen-0.22.0")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("reprocheck_v5_evaluate", BASE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    result = module.evaluate(args.output, args.phase)
    return 0 if result["source_integrity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
