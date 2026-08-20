from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path("benchmarks/evidence_trial_v19")
PREFIX = "reprocheck-evidence-trial-v19-curator/"


def _module():
    path = ROOT / "build_curator_handoff.py"
    spec = importlib.util.spec_from_file_location("evidence_trial_v19_curator_handoff", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_curator_handoff_is_deterministic_minimal_and_self_verifying(tmp_path: Path):
    module = _module()
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_result = module.build(ROOT.resolve(), first)
    second_result = module.build(ROOT.resolve(), second)
    assert first.read_bytes() == second.read_bytes()
    assert first_result["sha256"] == second_result["sha256"]
    assert first_result["candidate_count"] == 60
    assert first_result["payload_entry_count"] == 65
    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert len(names) == 65
        assert all(name.startswith(PREFIX) and ".." not in name for name in names)
        assert not any(
            marker in name.casefold()
            for name in names
            for marker in ("gold", "prediction", "reviewer", "evaluator")
        )
        manifest = json.loads(archive.read(PREFIX + "HANDOFF.json"))
        assert manifest["entry_count"] == 64
        assert manifest["contains_gold_labels"] is False
        assert manifest["contains_evaluator_outputs"] is False
        assert manifest["network_required"] is False
        for descriptor in manifest["entries"]:
            data = archive.read(PREFIX + descriptor["filename"])
            assert len(data) == descriptor["size_bytes"]
            assert hashlib.sha256(data).hexdigest() == descriptor["sha256"]


def test_extracted_handoff_runs_without_project_dependencies(tmp_path: Path):
    module = _module()
    archive_path = tmp_path / "handoff.zip"
    module.build(ROOT.resolve(), archive_path)
    extracted = tmp_path / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extracted)
    handoff = extracted / PREFIX.removesuffix("/")
    result = subprocess.run(
        [sys.executable, "curation_app.py", "--help"],
        cwd=handoff,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0
    assert "Local source-only Evidence Trial curator" in result.stdout
    app_path = handoff / "curation_app.py"
    spec = importlib.util.spec_from_file_location("extracted_curation_app", app_path)
    assert spec is not None and spec.loader is not None
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    packet_path = handoff / "curation-packet.json"
    packet = app.load_packet(packet_path)
    assert len(app.verify_sources(packet_path, packet)) == 60


def test_curator_handoff_rejects_tampered_source_and_overwrite(tmp_path: Path):
    module = _module()
    copied = tmp_path / "trial"
    copied.mkdir()
    for name in ("curation_app.py", "curation-packet.json", "CURATOR_GUIDE.md"):
        shutil.copyfile(ROOT / name, copied / name)
    shutil.copytree(ROOT / "acquisition-v5" / "sources", copied / "acquisition-v5" / "sources")
    source = copied / "acquisition-v5" / "sources" / "candidate-001.txt"
    source.write_bytes(source.read_bytes() + b"tampered\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        module.build(copied, tmp_path / "tampered.zip")
    shutil.copyfile(ROOT / "acquisition-v5" / "sources" / "candidate-001.txt", source)
    packet_path = copied / "curation-packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["candidates"][0]["gold_status"] = "supported"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError, match="structurally outcome-blind"):
        module.build(copied, tmp_path / "leaky.zip")
    output = tmp_path / "existing.zip"
    output.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="already exists"):
        module.build(ROOT.resolve(), output)
    assert output.read_bytes() == b"preserve"
