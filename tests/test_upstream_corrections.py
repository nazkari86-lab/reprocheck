from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "benchmarks" / "upstream_corrections" / "run_benchmark.py"
    spec = importlib.util.spec_from_file_location("upstream_corrections_benchmark", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_upstream_corrections_are_real_and_parser_visible(tmp_path: Path) -> None:
    result = _module().run(tmp_path / "result.json")

    assert result["independent_corrections"] == 3
    assert result["affected_records"] == 14
    assert result["verified_corrections"] == 3
    assert result["source_integrity_rate"] == 1.0
    assert result["parser_detection_rate"] == 1.0
    assert result["verification_rate"] == 1.0
    assert all(case["passed"] for case in result["cases"])
