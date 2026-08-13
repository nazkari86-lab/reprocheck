from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "benchmarks" / "upstream_discovery_v4" / "verify_registration.py"
    spec = importlib.util.spec_from_file_location("upstream_discovery_v4_registration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v4_registration_is_source_unseen_and_hash_locked() -> None:
    result = _module().verify()

    assert result["status"] == "registered_unretrieved"
    assert result["evaluator_commit"] == "4b1ffdf633723c2672449aa15198d259f80b7568"
    assert result["wheel_sha256"] == (
        "f73561ca61a1bb04211ef4a4d73c7250c0e969c35105077d219be54a61f810fd"
    )
    assert result["queries"] == 10
    assert result["maximum_sample"] == 250
    assert result["exclusion_inputs"] == 4
    assert len(result["protocol_sha256"]) == 64
