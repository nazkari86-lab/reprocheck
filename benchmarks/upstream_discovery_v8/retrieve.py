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
    module.SEED = "reprocheck-upstream-v8"
    module.EVALUATOR_COMMIT = "6238f2c"
    module.EVALUATOR_VERSION = "0.23.0"
    module.SELECTED_PER_FRAME = 25
    module.QUERIES = [
        f'"update benchmark" README {module.BASE}',
        f'"update benchmarks" README {module.BASE}',
        f'"benchmark numbers" README {module.BASE}',
        f'"benchmark metrics" README {module.BASE}',
        f'"benchmark table" README fix {module.BASE}',
        f'"benchmark table" docs fix {module.BASE}',
        f'"benchmark results" README correction {module.BASE}',
        f'"benchmark results" docs correction {module.BASE}',
        f'"performance numbers" README update {module.BASE}',
        f'"performance metrics" README update {module.BASE}',
        f'"latency numbers" README update {module.BASE}',
        f'"throughput numbers" README update {module.BASE}',
        f'"memory numbers" README update {module.BASE}',
        f'"accuracy numbers" README update {module.BASE}',
        f'"precision numbers" README update {module.BASE}',
        f'"recall numbers" README update {module.BASE}',
        f'"F1 score" README correct {module.BASE}',
        f'"mAP" README correct benchmark {module.BASE}',
        f'"test count" README update {module.BASE}',
        f'"tests" README "was incorrect" {module.BASE}',
        f'"outdated numbers" README benchmark {module.BASE}',
        f'"stale numbers" README benchmark {module.BASE}',
        f'"wrong numbers" README benchmark {module.BASE}',
        f'"incorrect numbers" README benchmark {module.BASE}',
        f'"fix typo" README benchmark {module.BASE}',
        f'"correct typo" README benchmark {module.BASE}',
        f'"regenerate benchmarks" docs {module.BASE}',
        f'"rerun benchmarks" README {module.BASE}',
        f'"re-ran benchmarks" README {module.BASE}',
        f'"fresh benchmark results" README {module.BASE}',
        f'"actual benchmark" README correction {module.BASE}',
        f'"reported results" README fix {module.BASE}',
        f'"reported metrics" README fix {module.BASE}',
        f'"documentation values" benchmark fix {module.BASE}',
        f'"documentation numbers" benchmark fix {module.BASE}',
        f'"sync README" benchmark {module.BASE}',
        f'"sync docs" benchmark results {module.BASE}',
        f'"results table" README corrected {module.BASE}',
        f'"results table" docs updated benchmark {module.BASE}',
        f'"measurement results" README corrected {module.BASE}',
    ]
    original_prior_exposure = module._prior_exposure

    def prior_exposure():
        exposed = original_prior_exposure()
        for version in ("v5", "v6", "v7"):
            module._add_frames(
                exposed, ROOT.parent / f"upstream_discovery_{version}" / "frames.json"
            )
        return exposed

    module._prior_exposure = prior_exposure
    print(module.json.dumps(module.retrieve(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
