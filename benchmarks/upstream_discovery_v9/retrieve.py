from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V8 = ROOT.parent / "upstream_discovery_v8" / "retrieve.py"


def main() -> int:
    spec = importlib.util.spec_from_file_location("reprocheck_v8_retrieve", V8)
    assert spec is not None and spec.loader is not None
    v8 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v8)
    base_spec = importlib.util.spec_from_file_location("reprocheck_v5_retrieve", v8.V5)
    assert base_spec is not None and base_spec.loader is not None
    module = importlib.util.module_from_spec(base_spec)
    base_spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.SEED = "reprocheck-upstream-v9"
    module.EVALUATOR_COMMIT = "2eff4e8"
    module.EVALUATOR_VERSION = "0.24.0"
    module.SELECTED_PER_FRAME = 25
    module.QUERIES = [query.replace(module.BASE, "").strip() + " " + module.BASE for query in _queries(module.BASE)]
    original_prior_exposure = module._prior_exposure

    def prior_exposure():
        exposed = original_prior_exposure()
        for version in ("v5", "v6", "v7", "v8"):
            module._add_frames(exposed, ROOT.parent / f"upstream_discovery_{version}" / "frames.json")
        return exposed

    module._prior_exposure = prior_exposure
    print(module.json.dumps(module.retrieve(), sort_keys=True))
    return 0


def _queries(base: str) -> list[str]:
    return [
        f'"update benchmark" README {base}', f'"update benchmarks" README {base}',
        f'"benchmark numbers" README {base}', f'"benchmark metrics" README {base}',
        f'"benchmark table" README fix {base}', f'"benchmark table" docs fix {base}',
        f'"benchmark results" README correction {base}', f'"benchmark results" docs correction {base}',
        f'"performance numbers" README update {base}', f'"performance metrics" README update {base}',
        f'"latency numbers" README update {base}', f'"throughput numbers" README update {base}',
        f'"memory numbers" README update {base}', f'"accuracy numbers" README update {base}',
        f'"precision numbers" README update {base}', f'"recall numbers" README update {base}',
        f'"F1 score" README correct {base}', f'"mAP" README correct benchmark {base}',
        f'"test count" README update {base}', f'"tests" README "was incorrect" {base}',
        f'"outdated numbers" README benchmark {base}', f'"stale numbers" README benchmark {base}',
        f'"wrong numbers" README benchmark {base}', f'"incorrect numbers" README benchmark {base}',
        f'"fix typo" README benchmark {base}', f'"correct typo" README benchmark {base}',
        f'"regenerate benchmarks" docs {base}', f'"rerun benchmarks" README {base}',
        f'"re-ran benchmarks" README {base}', f'"fresh benchmark results" README {base}',
        f'"actual benchmark" README correction {base}', f'"reported results" README fix {base}',
        f'"reported metrics" README fix {base}', f'"documentation values" benchmark fix {base}',
        f'"documentation numbers" benchmark fix {base}', f'"sync README" benchmark {base}',
        f'"sync docs" benchmark results {base}', f'"results table" README corrected {base}',
        f'"results table" docs updated benchmark {base}', f'"measurement results" README corrected {base}',
    ]


if __name__ == "__main__":
    raise SystemExit(main())
