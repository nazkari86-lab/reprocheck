from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "upstream_discovery_v8" / "collect_details_graphql.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("reprocheck_v8_graphql", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
