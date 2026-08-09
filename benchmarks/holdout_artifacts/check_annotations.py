from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCES = ROOT / "sources"
MANIFEST = ROOT / "source_manifest.json"
ANNOTATIONS = ROOT / "annotations.json"
ANNOTATION_LOCK = ROOT / "annotation.lock.json"
PREREGISTRATION_LOCK = ROOT / "preregistration.lock.json"
EXPECTED_METRICS = {"ap": 229, "ap50": 67, "ap75": 17}
EXPECTED_REPOSITORIES = {"detr": 10, "ultralytics": 256, "yolov5": 28, "yolox": 19}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check() -> list[str]:
    try:
        manifest = _load(MANIFEST)
        annotations = _load(ANNOTATIONS)
        annotation_lock = _load(ANNOTATION_LOCK)
        preregistration_lock = _load(PREREGISTRATION_LOCK)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [str(error)]
    errors: list[str] = []
    if annotation_lock.get("source_manifest_sha256") != _sha256(MANIFEST):
        errors.append("source manifest changed after annotation lock")
    if annotation_lock.get("annotations_sha256") != _sha256(ANNOTATIONS):
        errors.append("annotations changed after annotation lock")
    if annotation_lock.get("evaluator_sha256") != preregistration_lock.get("evaluator_sha256"):
        errors.append("annotation and preregistration evaluator locks disagree")
    if annotations.get("preregistration_sha256") != preregistration_lock.get(
        "preregistration_sha256"
    ):
        errors.append("annotations are not bound to the preregistration")
    if annotations.get("evaluator_sha256") != preregistration_lock.get("evaluator_sha256"):
        errors.append("annotations are not bound to the frozen evaluator")
    entries = {
        entry["local_path"]: entry
        for entry in manifest.get("entries", [])
        if entry.get("kind") == "artifact"
    }
    artifacts = annotations.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 25:
        return ["annotations must contain exactly 25 artifacts"]
    paths = [artifact.get("local_path") for artifact in artifacts]
    if len(paths) != len(set(paths)) or set(paths) != set(entries):
        errors.append("annotation and manifest artifact paths disagree")
    metrics: Counter[str] = Counter()
    repositories: Counter[str] = Counter()
    claim_bearing = 0
    for artifact in artifacts:
        local_path = artifact["local_path"]
        source = SOURCES / local_path
        entry = entries[local_path]
        if _sha256(source) != entry["sha256"] or _sha256(source) != artifact["source_sha256"]:
            errors.append(f"source hash mismatch: {local_path}")
        claims = artifact.get("expected_claims", [])
        claim_bearing += bool(claims)
        origins = [claim.get("origin") for claim in claims]
        if len(origins) != len(set(origins)):
            errors.append(f"duplicate claim origin: {local_path}")
        for claim in claims:
            metric = claim.get("metric")
            value = claim.get("value")
            if metric not in EXPECTED_METRICS:
                errors.append(f"out-of-scope metric {metric}: {local_path}")
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not 0 <= value <= 1
            ):
                errors.append(f"invalid normalized value: {local_path}")
            metrics[metric] += 1
            repositories[artifact["repository"]] += 1
    if dict(metrics) != EXPECTED_METRICS:
        errors.append(f"metric count drift: {dict(metrics)}")
    if dict(repositories) != EXPECTED_REPOSITORIES:
        errors.append(f"repository count drift: {dict(repositories)}")
    if claim_bearing != 15:
        errors.append(f"claim-bearing artifact count drift: {claim_bearing}")
    if annotations.get("reviewers", {}).get("internal_human") != 1:
        errors.append("pre-output internal review is not recorded")
    return errors


def main() -> int:
    errors = check()
    for error in errors:
        print(f"FAIL: {error}")
    if not errors:
        print("PASS: preregistered holdout annotations satisfy all locked invariants")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
