from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _module():
    path = ROOT / "benchmarks" / "upstream_discovery_v3" / "verify_registration.py"
    spec = importlib.util.spec_from_file_location("upstream_discovery_v3_registration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v3_registration_is_source_unseen_and_hash_locked() -> None:
    result = _module().verify()

    assert result["status"] == "registered_unretrieved"
    assert result["evaluator_commit"] == "7e5a6c087fc6f5e5df14ccde1c8436049c39c5b7"
    assert result["wheel_sha256"] == (
        "fb76d6ae2d9cfe6a2400e3b5be68525d54d87041f17aa3c80ad50e4233697c8e"
    )
    assert result["exclusion_inputs"] == 3
    assert len(result["protocol_sha256"]) == 64
