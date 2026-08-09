import hashlib
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("bundle", ["yolo26n-coco8", "sklearn-tabular"])
def test_external_manifest_covers_and_matches_bundle(bundle: str):
    root = Path(__file__).parents[1] / "benchmarks" / "external" / bundle
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema"] == "reprocheck.external-benchmark.v1"
    assert len({item["file"] for item in manifest["files"]}) == len(manifest["files"])
    descriptors = {item["file"]: item for item in manifest["files"]}
    bundled_files = {path.name for path in root.iterdir() if path.is_file()}
    assert set(descriptors) == bundled_files - {"manifest.json"}

    for filename, descriptor in descriptors.items():
        payload = (root / filename).read_bytes()
        assert descriptor["size_bytes"] == len(payload)
        assert descriptor["sha256"] == hashlib.sha256(payload).hexdigest()
