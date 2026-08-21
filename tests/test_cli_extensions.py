import json

import pytest

from reprocheck.audit import run_audit
from reprocheck.cli import _artifact_spec, _loopback_host, main


def _mismatch(tmp_path):
    report = tmp_path / "report.md"
    metrics = tmp_path / "metrics.json"
    certificate = tmp_path / "certificate.json"
    report.write_text("Accuracy: 80%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
    certificate.write_text(
        json.dumps(run_audit(report_path=report, metrics_path=metrics).to_dict()),
        encoding="utf-8",
    )
    return certificate


def _holdout_protocol(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "title": "holdout",
                "research_question": "question",
                "evaluator_version": "1",
                "source_pools": [
                    {
                        "repository": f"https://github.com/example/repo-{index}",
                        "commit": str(index) * 40,
                    }
                    for index in range(1, 4)
                ],
                "selection": {},
                "primary_endpoints": {},
                "annotation": {},
                "stopping_rule": "once",
                "analysis_plan": {},
                "scientific_boundary": "bounded",
            }
        ),
        encoding="utf-8",
    )


def _human_protocol(path):
    path.write_text(
        json.dumps(
            {
                "schema_version": "v1",
                "title": "human",
                "design": "crossover",
                "primary_endpoint": "accuracy",
                "secondary_endpoints": [],
                "minimum_participants": 12,
                "approvals_required_before_distribution": True,
                "consent_required": True,
                "analysis_plan": {},
                "scientific_boundary": "bounded",
            }
        ),
        encoding="utf-8",
    )


def test_cli_witness_and_benchmark_paths(tmp_path):
    certificate = _mismatch(tmp_path)
    witness = tmp_path / "witness.json"
    assert (
        main(
            [
                "witness",
                "--certificate",
                str(certificate),
                "--finding-index",
                "0",
                "--output",
                str(witness),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "verify-witness",
                "--certificate",
                str(certificate),
                "--witness",
                str(witness),
                "--artifact-dir",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "witness-benchmark",
                "--output",
                str(tmp_path / "benchmark.json"),
                "--repeats",
                "1",
            ]
        )
        == 0
    )

    assert (
        main(["witness", "--certificate", str(tmp_path / "missing"), "--finding-index", "0"]) == 2
    )
    witness.write_text("{}", encoding="utf-8")
    assert (
        main(["verify-witness", "--certificate", str(certificate), "--witness", str(witness)]) == 1
    )
    assert main(["witness-benchmark", "--repeats", "0"]) == 2


def test_cli_exact_overlap_requires_artifact_dir(tmp_path):
    report = tmp_path / "report.md"
    train = tmp_path / "train.csv"
    test = tmp_path / "test.csv"
    certificate = tmp_path / "split-certificate.json"
    witness = tmp_path / "split-witness.json"
    report.write_text("No metric claim.\n", encoding="utf-8")
    train.write_text("id,text\n1,train\n", encoding="utf-8")
    test.write_text("id,text\n1,test\n", encoding="utf-8")
    certificate.write_text(
        json.dumps(
            run_audit(
                report_path=report,
                train_path=train,
                test_path=test,
                identity_columns=["id"],
            ).to_dict()
        ),
        encoding="utf-8",
    )

    base = [
        "witness",
        "--certificate",
        str(certificate),
        "--finding-index",
        "0",
        "--output",
        str(witness),
    ]
    assert main(base) == 2
    assert main([*base, "--artifact-dir", str(tmp_path)]) == 0
    assert (
        main(
            [
                "verify-witness",
                "--certificate",
                str(certificate),
                "--witness",
                str(witness),
                "--artifact-dir",
                str(tmp_path),
            ]
        )
        == 0
    )


def test_cli_source_witness_benchmark(tmp_path):
    assert (
        main(
            [
                "witness-source-benchmark",
                "--protocol",
                "benchmarks/witness_source/protocol.json",
                "--output",
                str(tmp_path / "source-result.json"),
            ]
        )
        == 0
    )
    bad = tmp_path / "bad-protocol.json"
    bad.write_text("{}", encoding="utf-8")
    assert (
        main(
            [
                "witness-source-benchmark",
                "--protocol",
                str(bad),
                "--output",
                str(tmp_path / "bad-result.json"),
            ]
        )
        == 2
    )


def test_cli_extension_argument_guards():
    assert _loopback_host("localhost")
    assert _loopback_host("::1")
    assert not _loopback_host("example.test")
    with pytest.raises(Exception, match="ROLE=PATH"):
        _artifact_spec("bad")
    with pytest.raises(Exception, match="non-empty"):
        _artifact_spec("role=")


def test_cli_ml_sparse_calibration_and_frozen_evaluation(tmp_path):
    training = tmp_path / "train.json"
    model = tmp_path / "model.json"
    training.write_text(
        json.dumps(
            [
                {
                    "block_id": "b1",
                    "owner_id": "o1",
                    "text": "Accuracy reached 90%",
                    "label": True,
                    "split": "train",
                },
                {
                    "block_id": "b2",
                    "owner_id": "o2",
                    "text": "Introduction only",
                    "label": False,
                    "split": "train",
                },
            ]
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "ml-train",
                "--rows",
                str(training),
                "--corpus-sha256",
                "a" * 64,
                "--split-sha256",
                "b" * 64,
                "--output",
                str(model),
            ]
        )
        == 0
    )
    model_digest = json.loads(model.read_text(encoding="utf-8"))["model_sha256"]

    validation = tmp_path / "validation.json"
    calibration = tmp_path / "calibration.json"
    validation.write_text(
        json.dumps(
            [
                {
                    "claim_id": f"v{index}",
                    "owner_id": f"owner-{index}",
                    "split": "validation",
                    "claim_probability": 0.99,
                    "tuple_probability": 0.99,
                    "evidence_probability": 0.99,
                    "completeness": 0.99,
                    "rank_margin": 0.99,
                    "ood_score": 0.01,
                    "gate_eligible": True,
                    "correct": True,
                }
                for index in range(40)
            ]
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "ml-calibrate",
                "--records",
                str(validation),
                "--corpus-sha256",
                "a" * 64,
                "--split-sha256",
                "b" * 64,
                "--model-sha256",
                model_digest,
                "--output",
                str(calibration),
            ]
        )
        == 0
    )

    evaluation = tmp_path / "test.json"
    result = tmp_path / "result.json"
    evaluation.write_text(
        json.dumps(
            [
                {
                    "claim_id": f"t{index}",
                    "owner_id": f"test-owner-{index % 30}",
                    "split": "test",
                    "language": ("en", "ru", "kk")[index % 3],
                    "domain": "science",
                    "eligible_claim": True,
                    "claim_probability": 0.99,
                    "tuple_probability": 0.99,
                    "evidence_probability": 0.99,
                    "completeness": 0.99,
                    "rank_margin": 0.99,
                    "ood_score": 0.01,
                    "gate_eligible": True,
                    "prediction_correct": True,
                    "baseline_selected": index < 50,
                    "baseline_correct": index < 50,
                }
                for index in range(100)
            ]
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "ml-evaluate",
                "--records",
                str(evaluation),
                "--calibration",
                str(calibration),
                "--phase",
                "test",
                "--bootstrap-samples",
                "20",
                "--output",
                str(result),
            ]
        )
        == 0
    )
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["success_gate"]["status"] == "passed"
    assert set(payload["subgroups"]["language"]) == {"en", "kk", "ru"}


def test_cli_holdout_registration_paths(tmp_path):
    protocol = tmp_path / "protocol.json"
    evaluator = tmp_path / "evaluator.whl"
    registration = tmp_path / "registration.json"
    _holdout_protocol(protocol)
    evaluator.write_bytes(b"evaluator")
    assert (
        main(
            [
                "holdout-register",
                "--protocol",
                str(protocol),
                "--evaluator",
                str(evaluator),
                "--output",
                str(registration),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "holdout-verify-registration",
                "--registration",
                str(registration),
                "--protocol",
                str(protocol),
                "--evaluator",
                str(evaluator),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "holdout-register",
                "--protocol",
                str(protocol),
                "--evaluator",
                str(evaluator),
                "--output",
                str(registration),
            ]
        )
        == 2
    )
    evaluator.write_bytes(b"tampered")
    assert (
        main(
            [
                "holdout-verify-registration",
                "--registration",
                str(registration),
                "--protocol",
                str(protocol),
                "--evaluator",
                str(evaluator),
            ]
        )
        == 1
    )


def test_cli_human_study_paths(tmp_path):
    protocol = tmp_path / "protocol.json"
    master = tmp_path / "master"
    packet = tmp_path / "packet"
    _human_protocol(protocol)
    assert (
        main(
            [
                "human-study-prepare",
                "--protocol",
                str(protocol),
                "--output-dir",
                str(master),
            ]
        )
        == 0
    )
    assert (
        main(["human-study-verify", "--master-dir", str(master), "--protocol", str(protocol)]) == 0
    )
    private = master / "private"
    private.rename(tmp_path / "private-hidden")
    assert (
        main(
            [
                "human-study-verify",
                "--public-lock-only",
                "--master-dir",
                str(master),
                "--protocol",
                str(protocol),
            ]
        )
        == 0
    )
    (tmp_path / "private-hidden").rename(private)
    assert (
        main(
            [
                "human-study-issue",
                "--master-dir",
                str(master),
                "--participant-code",
                "P001",
                "--approval-reference",
                "SRC-1",
                "--output-dir",
                str(packet),
            ]
        )
        == 0
    )
    response_path = packet / "response-template.json"
    response = json.loads(response_path.read_text())
    gold = json.loads((master / "private" / "PRIVATE-gold.json").read_text())
    verdicts = {item["case_id"]: item["accepted_verdict"] for item in gold["cases"]}
    response["consent_confirmed"] = True
    response["independent_review_confirmed"] = True
    for answer in response["responses"]:
        answer.update(
            verdict=verdicts[answer["case_id"]],
            duration_seconds=10,
            confidence=4,
        )
    response_path.write_text(json.dumps(response), encoding="utf-8")
    assert (
        main(
            [
                "human-study-score",
                "--master-dir",
                str(master),
                "--response",
                str(response_path),
                "--output",
                str(tmp_path / "human-result.json"),
            ]
        )
        == 0
    )

    assert (
        main(["human-study-prepare", "--protocol", str(protocol), "--output-dir", str(master)]) == 2
    )
    assert main(["human-study-verify", "--master-dir", str(tmp_path / "missing")]) == 1
    assert (
        main(
            [
                "human-study-issue",
                "--master-dir",
                str(master),
                "--participant-code",
                "P002",
                "--approval-reference",
                "x",
                "--output-dir",
                str(tmp_path / "bad-packet"),
            ]
        )
        == 2
    )
    assert (
        main(
            [
                "human-study-score",
                "--master-dir",
                str(master),
                "--response",
                str(packet / "response-template.json"),
                "--output",
                str(tmp_path / "human-result.json"),
            ]
        )
        == 2
    )
