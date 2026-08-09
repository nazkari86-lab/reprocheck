from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from importlib.metadata import distribution
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parent
BASE_RUNNER = ROOT / "run_zero_shot.py"
PRIMARY_RESULT = ROOT / "results" / "zero-shot-v0.7.json"
WHEEL_SHA256 = "c08925b2c955452c59dfe2c8f0838afb2e90b300207e990ce00041f5502733a3"
PRIMARY_RESULT_SHA256 = "74c7547eee265a19c8ee2d0269f384583dddb96228d4c53eef5022e1654a1b57"
BASE_RUNNER_SHA256 = "bbcc19e39f9308cca694f3ba3d79e36c611261d7fb2f6d8fbed880e0aaa25e04"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_base_runner() -> ModuleType:
    if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
        raise ValueError("frozen v0.7 runner changed")
    spec = importlib.util.spec_from_file_location("reprocheck_v07_frozen_runner", BASE_RUNNER)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load frozen v0.7 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _development_evaluator(module: ModuleType, wheel: Path) -> dict[str, str]:
    wheel = wheel.resolve()
    if module.__version__ != "0.8.0" or _sha256(wheel) != WHEEL_SHA256:
        raise ValueError("installed or supplied evaluator differs from frozen v0.8")
    direct_url_raw = distribution("reprocheck").read_text("direct_url.json")
    if direct_url_raw is None:
        raise ValueError("installed evaluator has no direct_url.json provenance")
    installed_hash = json.loads(direct_url_raw).get("archive_info", {}).get("hash")
    if installed_hash != f"sha256={WHEEL_SHA256}":
        raise ValueError("installed evaluator archive differs from supplied v0.8 wheel")
    return {
        "version": "0.8.0",
        "filename": wheel.name,
        "sha256": WHEEL_SHA256,
        "installed_archive_hash": installed_hash,
    }


def run(wheel: Path, output: Path) -> dict[str, Any]:
    if _sha256(PRIMARY_RESULT) != PRIMARY_RESULT_SHA256:
        raise ValueError("immutable v0.7 primary result changed")
    module = _load_base_runner()
    module.EVALUATOR_SHA256 = WHEEL_SHA256
    module._verify_evaluator = lambda supplied: _development_evaluator(module, supplied)
    result = module.run(wheel, output)
    result["schema"] = "reprocheck.cross-domain-holdout-development-study.v1"
    result["phase"] = "development_after_v0.7_holdout_inspection"
    result["zero_shot"] = False
    result["protocol"]["post_holdout_development"] = True
    result["corpus"]["primary_v0.7_result_sha256"] = PRIMARY_RESULT_SHA256
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="run post-holdout v0.8 development evaluation")
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.evaluator_artifact, args.output)
    except (KeyError, OSError, UnicodeDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    summary = result["summary"]
    print(
        f"version=0.8.0 zero_shot=false tp={summary['tp']} fp={summary['fp']} "
        f"fn={summary['fn']} precision={summary['precision']:.1%} recall={summary['recall']:.1%}"
    )
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
