from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


ROOT = Path("benchmarks/evidence_trial_v19")


def _module():
    path = ROOT / "verify_operator_tools.py"
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_operator_status", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_operator_tool_status_matches_current_bytes():
    module = _module()
    assert module.verify(ROOT / "operator-tooling-status.json") == []


def test_operator_tool_status_rejects_tampering(tmp_path: Path):
    module = _module()
    for name in (
        "registration.json",
        "curation-packet.json",
        "curation_app.py",
        "review_app.py",
        "adjudication_app.py",
        "operator-tooling-status.json",
    ):
        shutil.copyfile(ROOT / name, tmp_path / name)
    (tmp_path / "review_app.py").write_text("tampered\n", encoding="utf-8")
    errors = module.verify(tmp_path / "operator-tooling-status.json")
    assert any("review_app.py" in error for error in errors)
    payload = json.loads((tmp_path / "operator-tooling-status.json").read_text())
    payload["independent_human_status"] = "complete"
    (tmp_path / "operator-tooling-status.json").write_text(json.dumps(payload), encoding="utf-8")
    errors = module.verify(tmp_path / "operator-tooling-status.json")
    assert any("must remain pending" in error for error in errors)
