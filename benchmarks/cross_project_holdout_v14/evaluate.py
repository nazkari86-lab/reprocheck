from __future__ import annotations

import json
from pathlib import Path

from benchmarks.cross_project_holdout_v13 import evaluate as engine


ROOT = Path(__file__).resolve().parent


def main() -> int:
    engine.ROOT = ROOT
    code = engine.main()
    output = ROOT / "results" / "zero-shot-0.27.0.json"
    result = json.loads(output.read_text(encoding="utf-8"))
    result["schema_version"] = "reprocheck.cross-project-zero-shot-result.v14"
    result["phase"] = "zero-shot-v14-frozen-0.27.0"
    result["scientific_boundary"] = (
        "First and only evaluation of the preregistered v14 sources and labels "
        "with the frozen 0.27.0 extractor."
    )
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
