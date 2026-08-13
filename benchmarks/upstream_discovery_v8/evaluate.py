from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "upstream_discovery_v5" / "evaluate.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", default="zero-shot-frozen-0.23.0")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("reprocheck_v5_evaluate", BASE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    result = module.evaluate(args.output, args.phase)
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]
    result["schema_version"] = "reprocheck.upstream-discovery-result.v8"
    result["breadth"] = {
        "repositories": len({case["repository"] for case in cases}),
        "independent_repository_owners": len(
            {case["repository"].split("/", 1)[0] for case in cases}
        ),
        "source_formats": sorted(
            {Path(path).suffix.casefold().lstrip(".") for case in cases for path in case["files"]}
        ),
        "source_structures": ["markdown_prose", "markdown_table"],
        "metric_families": sorted(
            {claim["metric"] for case in cases for claim in case["claims"]}
        ),
    }
    result["scientific_boundary"] = (
        "The deterministic one-owner sample estimates visibility only in 40 frozen, "
        "query-conditioned GitHub correction frames. It is not a population estimate. "
        "All 994 sampled pull requests were labeled before the frozen parser's first run; "
        "any later development score is post-inspection evidence and cannot replace this result."
    )
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if result["source_integrity"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
