from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "upstream_discovery_v5" / "build_review_packet.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("reprocheck_v5_review", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    print(module.json.dumps(module.build(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
