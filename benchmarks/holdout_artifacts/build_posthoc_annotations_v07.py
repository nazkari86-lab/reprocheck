from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FROZEN = ROOT / "annotations.json"
OUTPUT = ROOT / "posthoc_annotations-v0.7.json"
FROZEN_SHA256 = "be84838acfb26ccb62558d6fa1a4470320b2c0aac5c469e159d3390eaaa95828"
TARGET = "ultralytics/docs/en/models/yolo-world.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    if _sha256(FROZEN) != FROZEN_SHA256:
        raise ValueError("frozen v0.6 annotations changed")
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    artifacts = json.loads(json.dumps(frozen["artifacts"]))
    corrections = 0
    for artifact in artifacts:
        if artifact["local_path"] != TARGET:
            continue
        for claim in artifact["expected_claims"]:
            origin = claim["origin"].casefold()
            if "header=map50" in origin:
                claim["metric"] = "ap50"
                claim["review"] = "posthoc_metric_category_correction"
                corrections += 1
            elif "header=map75" in origin:
                claim["metric"] = "ap75"
                claim["review"] = "posthoc_metric_category_correction"
                corrections += 1
    if corrections != 16:
        raise ValueError(f"expected exactly 16 category corrections, found {corrections}")
    return {
        "schema": "reprocheck.posthoc-holdout-annotations.v1",
        "phase": "created_after_v0.6_holdout_inspection",
        "primary_v0.6_annotations_sha256": FROZEN_SHA256,
        "primary_metrics_modified": False,
        "development_use_only": True,
        "corrections": {
            "count": corrections,
            "local_path": TARGET,
            "change": "generic AP labels under mAP50/mAP75 headers corrected to AP50/AP75",
        },
        "reviewers": {
            "internal_human": 1,
            "independent_external": 0,
            "adjudication": False,
        },
        "artifacts": artifacts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build post-hoc v0.7 development annotations")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = build()
    except (KeyError, OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 2
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        OUTPUT.write_text(serialized, encoding="utf-8")
        action = "wrote"
    elif not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != serialized:
        print("ERROR: post-hoc annotations differ; review and run with --write")
        return 1
    else:
        action = "verified"
    print(f"{action} corrections={payload['corrections']['count']} output={OUTPUT.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
