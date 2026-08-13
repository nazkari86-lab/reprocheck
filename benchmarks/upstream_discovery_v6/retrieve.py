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
    module.SEED = "reprocheck-upstream-v6"
    module.EVALUATOR_COMMIT = "5fdb6a6"
    module.EVALUATOR_VERSION = "0.22.0"
    module.SELECTED_PER_FRAME = 15
    module.QUERIES = [
        f'"benchmark numbers were" corrected {module.BASE}',
        f'"fix reported metrics" {module.BASE}',
        f'"results table" "was incorrect" {module.BASE}',
        f'"correct benchmark data" {module.BASE}',
        f'"wrong latency numbers" {module.BASE}',
        f'"metrics were calculated incorrectly" {module.BASE}',
    ]
    original_prior_exposure = module._prior_exposure

    def prior_exposure():
        exposed = original_prior_exposure()
        module._add_frames(exposed, ROOT.parent / "upstream_discovery_v5" / "frames.json")
        return exposed

    module._prior_exposure = prior_exposure
    print(module.json.dumps(module.retrieve(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
