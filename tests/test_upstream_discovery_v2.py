from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "benchmarks" / "upstream_discovery_v2" / "verify_registration.py"
    spec = importlib.util.spec_from_file_location("upstream_discovery_v2_registration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prospective_registration_is_unretrieved_and_hash_locked() -> None:
    result = _module().verify()

    assert result["status"] == "registered_unretrieved"
    assert result["evaluator_commit"] == "2618cad2c54c1610947f4f64e4b7ba8c5302fa28"
    assert len(result["protocol_sha256"]) == 64
