from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from reprocheck.evidence_trial import lock_trial_gold, prepare_trial_review


APP_ROOT = Path("benchmarks/evidence_trial_v19")


def _module(name: str):
    path = APP_ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"evidence_trial_v19_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dump(path: Path, payload: object) -> Path:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _claim(claim_id: str, owner: str, value: float) -> dict:
    return {
        "claim_id": claim_id,
        "owner": owner,
        "repository": f"{owner}/repo",
        "url": f"https://github.com/{owner}/repo/blob/" + "a" * 40 + "/RESULTS.md",
        "commit": "a" * 40,
        "path": "RESULTS.md",
        "sha256": "b" * 64,
        "block": {"start": 1, "end": 1},
        "claim_text": f"Accuracy: {value}",
        "declared_metric": "accuracy",
        "declared_value": value,
        "stratum": "natural_unadjudicated",
        "evidence_tier": "report_only",
    }


def _review(packet_sha256: str, reviewer_id: str, statuses: tuple[str, str]) -> dict:
    return {
        "schema_version": "reprocheck.evidence-trial-review.v1",
        "reviewer_id": reviewer_id,
        "independent": True,
        "packet_sha256": packet_sha256,
        "reviews": [
            {
                "claim_id": f"claim-00{index}",
                "status": status,
                "rationale": f"Evidence-based independent review {index}",
                "evidence_refs": [f"immutable-source:{index}"],
            }
            for index, status in enumerate(statuses, start=1)
        ],
    }


def test_operator_exports_feed_the_registered_gold_lock(tmp_path: Path):
    review_app = _module("review_app")
    adjudication_app = _module("adjudication_app")
    sample = _dump(
        tmp_path / "sample.json",
        {
            "schema_version": "reprocheck.evidence-trial-sample.v1",
            "claims": [
                _claim("claim-001", "owner-a", 0.9),
                _claim("claim-002", "owner-b", 0.8),
            ],
        },
    )
    review_dir = tmp_path / "review"
    prepare_trial_review(sample, review_dir)
    packet_path = review_dir / "public" / "packet.json"
    packet = review_app.load_packet(packet_path)
    packet_sha256 = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    first_payload = _review(packet_sha256, "reviewer-a", ("supported", "supported"))
    second_payload = _review(packet_sha256, "reviewer-b", ("contradicted", "supported"))
    assert review_app.validate_review(packet, packet_sha256, first_payload) == []
    assert review_app.validate_review(packet, packet_sha256, second_payload) == []
    first = _dump(tmp_path / "review-a.json", first_payload)
    second = _dump(tmp_path / "review-b.json", second_payload)
    disagreement_packet = adjudication_app.build_disagreement_packet(packet_path, [first, second])
    adjudication = {
        "adjudications": [
            {
                "claim_id": "claim-001",
                "status": "not_verifiable",
                "rationale": "The cited material does not resolve the disagreement.",
                "evidence_refs": ["immutable-source:claim-001"],
            }
        ]
    }
    assert (
        adjudication_app.validate_adjudication(
            disagreement_packet, adjudication, "adjudicator-a", True
        )
        == []
    )
    adjudication_path = _dump(tmp_path / "adjudication.json", adjudication)
    gold = lock_trial_gold(
        review_dir,
        [first, second],
        adjudication_path,
        tmp_path / "gold.json",
    )
    assert gold["adjudication_complete"] is True
    assert gold["claims"][0]["gold_status"] == "not_verifiable"
    assert gold["claims"][1]["gold_status"] == "supported"
