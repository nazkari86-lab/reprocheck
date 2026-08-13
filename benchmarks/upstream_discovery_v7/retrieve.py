from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V5 = ROOT.parent / "upstream_discovery_v5" / "retrieve.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("reprocheck_v5_retrieve", V5)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.SEED = "reprocheck-upstream-v7"
    module.EVALUATOR_COMMIT = "901352b"
    module.EVALUATOR_VERSION = "0.22.0"
    module.SELECTED_PER_FRAME = 20
    module.QUERIES = [
        f'"README benchmark" "out of sync" {module.BASE}',
        f'"stale benchmark" README {module.BASE}',
        f'"correct benchmark table" {module.BASE}',
        f'"benchmark results" "outdated" documentation {module.BASE}',
        f'"update README" "benchmark results" {module.BASE}',
        f'"reported score" "incorrect" README {module.BASE}',
        f'"benchmark table" "corrected" README {module.BASE}',
        f'"documentation" "wrong benchmark" {module.BASE}',
    ]
    original_prior_exposure = module._prior_exposure

    def prior_exposure():
        exposed = original_prior_exposure()
        module._add_frames(exposed, ROOT.parent / "upstream_discovery_v5" / "frames.json")
        module._add_frames(exposed, ROOT.parent / "upstream_discovery_v6" / "frames.json")
        return exposed

    module._prior_exposure = prior_exposure
    print(module.json.dumps(module.retrieve(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
