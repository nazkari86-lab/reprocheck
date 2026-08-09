import hashlib
import json
from pathlib import Path

import pytest

from reprocheck.cli import main
from reprocheck.external_review import (
    _claim_map,
    _cohen_kappa,
    prepare_external_review,
    score_external_review,
)


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    sources = root / "sources" / "repo"
    sources.mkdir(parents=True)
    artifacts = []
    for index, claims in enumerate(
        [
            [{"metric": "accuracy", "value": 0.9}],
            [{"metric": "f1", "value": 0.8}],
            [],
            [],
        ]
    ):
        local_path = f"repo/report-{index}.md"
        path = root / "sources" / local_path
        path.write_text(
            f"Accuracy: {90 - index}%\n" if claims else "No in-scope metric.\n",
            encoding="utf-8",
        )
        artifacts.append(
            {
                "repository": "repo",
                "local_path": local_path,
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "expected_claims": claims,
            }
        )
    (root / "annotations.json").write_text(json.dumps({"artifacts": artifacts}), encoding="utf-8")
    return root


def _review_from_gold(gold: dict, reviewer_id: str) -> dict:
    return {
        "schema": "reprocheck.external-review-response.v1",
        "reviewer_id": reviewer_id,
        "independent_review_confirmed": True,
        "items": [
            {
                "blind_id": item["blind_id"],
                "claims": item["expected_claims"],
                "notes": "",
            }
            for item in gold["items"]
        ],
    }


def test_prepare_external_review_keeps_gold_out_of_packet(tmp_path: Path):
    output = tmp_path / "kit"
    manifest = prepare_external_review(_corpus(tmp_path), output, sample_artifacts=4)

    packet = json.loads((output / "public/packet.json").read_text(encoding="utf-8"))
    assert packet["blind"] is True
    assert len(packet["items"]) == 4
    assert all("expected_claims" not in item for item in packet["items"])
    assert all((output / "public" / item["source_file"]).is_file() for item in packet["items"])
    assert manifest["external_reviews_completed"] == 0
    assert manifest["distribute_only"] == "public/"
    assert manifest["keep_private_until_responses_frozen"] == "private/PRIVATE-gold.json"
    assert json.loads((output / "public/reviewer-A.json").read_text())["items"][0]["claims"] == []


def test_score_external_review_reports_agreement_and_adjudication(tmp_path: Path):
    output = tmp_path / "kit"
    prepare_external_review(_corpus(tmp_path), output, sample_artifacts=4)
    gold_path = output / "private/PRIVATE-gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    first = _review_from_gold(gold, "reviewer-a")
    second = _review_from_gold(gold, "reviewer-b")
    first_path = output / "first.json"
    second_path = output / "second.json"
    first_path.write_text(json.dumps(first), encoding="utf-8")
    second_path.write_text(json.dumps(second), encoding="utf-8")

    perfect = score_external_review(gold_path, [first_path, second_path])
    assert perfect["external_validation_complete"] is True
    assert perfect["inter_reviewer"]["exact_artifact_agreement"] == 1.0
    assert perfect["inter_reviewer"]["artifact_claim_presence_cohen_kappa"] == 1.0
    assert all(summary["f1"] == 1.0 for summary in perfect["reviewer_vs_internal_gold"].values())
    assert set(perfect["input_sha256"]) == {"gold", "reviewer-a", "reviewer-b"}

    positive = next(item for item in second["items"] if item["claims"])
    positive["claims"] = []
    second_path.write_text(json.dumps(second), encoding="utf-8")
    disagreement = score_external_review(gold_path, [first_path, second_path])
    assert disagreement["external_validation_complete"] is False
    assert disagreement["adjudication_required"] is True
    assert disagreement["inter_reviewer"]["adjudication_required_ids"] == [positive["blind_id"]]

    first_positive = next(
        item for item in first["items"] if item["blind_id"] == positive["blind_id"]
    )
    first_positive["claims"] = []
    first_path.write_text(json.dumps(first), encoding="utf-8")
    both_disagree_with_gold = score_external_review(gold_path, [first_path, second_path])
    assert both_disagree_with_gold["inter_reviewer"]["exact_artifact_agreement"] == 1.0
    assert both_disagree_with_gold["adjudication_required"] is True
    assert both_disagree_with_gold["inter_reviewer"]["internal_gold_disagreement_ids"] == [
        positive["blind_id"]
    ]


def test_external_review_rejects_unblinded_or_duplicate_reviewers(tmp_path: Path):
    output = tmp_path / "kit"
    prepare_external_review(_corpus(tmp_path), output, sample_artifacts=4)
    gold = json.loads((output / "private/PRIVATE-gold.json").read_text(encoding="utf-8"))
    review = _review_from_gold(gold, "same-reviewer")
    review["independent_review_confirmed"] = False
    first = output / "first.json"
    second = output / "second.json"
    first.write_text(json.dumps(review), encoding="utf-8")
    second.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(ValueError, match="did not confirm independence"):
        score_external_review(output / "private/PRIVATE-gold.json", [first, second])

    review["independent_review_confirmed"] = True
    first.write_text(json.dumps(review), encoding="utf-8")
    second.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(ValueError, match="distinct reviewer_id"):
        score_external_review(output / "private/PRIVATE-gold.json", [first, second])


def test_external_review_cli_prepares_packet(tmp_path: Path, capsys):
    corpus = _corpus(tmp_path)
    output = tmp_path / "kit"
    assert (
        main(
            [
                "review-prepare",
                "--corpus",
                str(corpus),
                "--output-dir",
                str(output),
                "--sample-artifacts",
                "4",
            ]
        )
        == 0
    )
    assert "Send only public/" in capsys.readouterr().out


def test_external_review_cli_scores_frozen_responses(tmp_path: Path, capsys):
    output = tmp_path / "kit"
    prepare_external_review(_corpus(tmp_path), output, sample_artifacts=4)
    gold_path = output / "private/PRIVATE-gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    first = output / "first.json"
    second = output / "second.json"
    first.write_text(json.dumps(_review_from_gold(gold, "reviewer-a")), encoding="utf-8")
    second.write_text(json.dumps(_review_from_gold(gold, "reviewer-b")), encoding="utf-8")
    result = output / "result.json"

    assert (
        main(
            [
                "review-score",
                "--gold",
                str(gold_path),
                "--reviewer",
                str(first),
                "--reviewer",
                str(second),
                "--output",
                str(result),
            ]
        )
        == 0
    )
    assert json.loads(result.read_text())["external_validation_complete"] is True
    assert "adjudication_required=false" in capsys.readouterr().out


@pytest.mark.parametrize("sample_size", [1, 3])
def test_external_review_rejects_invalid_sample_sizes(tmp_path: Path, sample_size: int):
    with pytest.raises(ValueError, match="even integer"):
        prepare_external_review(_corpus(tmp_path), tmp_path / "kit", sample_artifacts=sample_size)


def test_external_review_rejects_missing_annotations_and_oversampling(tmp_path: Path):
    corpus = _corpus(tmp_path)
    annotations = corpus / "annotations.json"
    annotations.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="artifacts array"):
        prepare_external_review(corpus, tmp_path / "missing", sample_artifacts=4)

    corpus = _corpus(tmp_path / "second")
    with pytest.raises(ValueError, match="too small"):
        prepare_external_review(corpus, tmp_path / "large", sample_artifacts=6)

    nonempty = tmp_path / "nonempty"
    nonempty.mkdir()
    (nonempty / "response.json").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(ValueError, match="must be empty"):
        prepare_external_review(corpus, nonempty, sample_artifacts=4)


def test_external_review_rejects_checksum_and_scoring_contract_errors(tmp_path: Path):
    corpus = _corpus(tmp_path)
    annotations_path = corpus / "annotations.json"
    annotations = json.loads(annotations_path.read_text())
    annotations["artifacts"][0]["source_sha256"] = "0" * 64
    annotations_path.write_text(json.dumps(annotations), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        prepare_external_review(corpus, tmp_path / "bad-checksum", sample_artifacts=4)

    gold = tmp_path / "gold.json"
    gold.write_text('{"schema":"wrong"}', encoding="utf-8")
    with pytest.raises(ValueError, match="exactly two"):
        score_external_review(gold, [])
    with pytest.raises(ValueError, match="unsupported external review gold schema"):
        score_external_review(gold, [tmp_path / "a", tmp_path / "b"])
    with pytest.raises(ValueError, match="finite and positive"):
        score_external_review(gold, [tmp_path / "a", tmp_path / "b"], tolerance=0)


@pytest.mark.parametrize(
    ("items", "message"),
    [
        ([], "non-empty array"),
        ([None], "must be an object"),
        ([{"blind_id": "x", "claims": {}}], "must be an array"),
        ([{"blind_id": "x", "claims": [{"metric": 1, "value": 0.5}]}], "contain a metric"),
        ([{"blind_id": "x", "claims": [{"metric": "accuracy", "value": True}]}], "finite"),
    ],
)
def test_external_review_rejects_malformed_claim_maps(items: object, message: str):
    with pytest.raises(ValueError, match=message):
        _claim_map(items, "claims")


def test_cohen_kappa_handles_invalid_and_degenerate_labels():
    with pytest.raises(ValueError, match="equal non-empty"):
        _cohen_kappa([], [])
    assert _cohen_kappa([True], [True]) is None
