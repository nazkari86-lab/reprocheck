import json
from pathlib import Path

from reprocheck.cli import main
from reprocheck.evidence_trial import canonical_digest

from test_evidence_trial import (
    _candidate_enrollment,
    _claims,
    _protocol,
    _registration,
    _review,
    _sample,
)
from test_evidence_trial_adversarial import _gold_pipeline


def test_trial_verify_registration_cli(tmp_path: Path, capsys):
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(tmp_path, protocol)
    args = [
        "trial-verify-registration",
        "--registration",
        str(registration),
        "--protocol",
        str(protocol),
    ]
    for name, path in artifacts.items():
        args.extend([f"--{name.replace('_', '-')}", str(path)])
    assert main(args) == 0
    assert "PASS: evidence trial registration" in capsys.readouterr().out


def test_trial_validate_sample_cli_reports_scientific_status(tmp_path: Path, capsys):
    protocol = _protocol(tmp_path / "protocol.json")
    sample = _sample(tmp_path / "sample.json")
    exclusions = tmp_path / "exclusions.json"
    payload = {
        "schema_version": "reprocheck.evidence-trial-exclusions.v1",
        "generated_from": [],
        "owners": [],
        "files": [],
        "union_sha256": "",
    }
    payload["union_sha256"] = canonical_digest(payload, blank_field="union_sha256")
    exclusions.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    assert (
        main(
            [
                "trial-validate-sample",
                "--protocol",
                str(protocol),
                "--sample",
                str(sample),
                "--exclusions",
                str(exclusions),
            ]
        )
        == 0
    )
    assert "insufficient_sample" in capsys.readouterr().out


def test_trial_build_sample_cli(tmp_path: Path, capsys):
    candidates, enrollment, _ = _candidate_enrollment(tmp_path)
    output = tmp_path / "sample.json"
    assert (
        main(
            [
                "trial-build-sample",
                "--candidates",
                str(candidates),
                "--enrollment",
                str(enrollment),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert "claims=1" in capsys.readouterr().out
    assert output.is_file()


def test_trial_register_cli_and_error_path(tmp_path: Path, capsys):
    protocol = _protocol(tmp_path / "protocol.json")
    artifacts = {}
    for name in ("evaluator", "acquisition", "source_config", "analysis", "exclusions"):
        artifacts[name] = tmp_path / name
        artifacts[name].write_text(name, encoding="utf-8")
    output = tmp_path / "registration.json"
    args = ["trial-register", "--protocol", str(protocol), "--output", str(output)]
    for name, path in artifacts.items():
        args.extend([f"--{name.replace('_', '-')}", str(path)])
    assert main(args) == 0
    assert "registered_not_retrieved" in capsys.readouterr().out
    assert main(args) == 2
    assert "immutable" in capsys.readouterr().err


def test_trial_review_gold_and_score_cli(tmp_path: Path, capsys):
    sample = _sample(tmp_path / "sample.json")
    review_dir = tmp_path / "review"
    assert (
        main(
            [
                "trial-prepare-review",
                "--sample",
                str(sample),
                "--output-dir",
                str(review_dir),
            ]
        )
        == 0
    )
    assert "reviewers_completed=0" in capsys.readouterr().out
    statuses = [item["gold_status"] for item in _claims()]
    packet = review_dir / "public" / "packet.json"
    first = _review(tmp_path / "first.json", "first", statuses, packet)
    second = _review(tmp_path / "second.json", "second", statuses, packet)
    gold = tmp_path / "gold.json"
    assert (
        main(
            [
                "trial-lock-gold",
                "--review-dir",
                str(review_dir),
                "--reviewer",
                str(first),
                "--reviewer",
                str(second),
                "--output",
                str(gold),
            ]
        )
        == 0
    )
    assert "reviewers=2" in capsys.readouterr().out

    protocol, registration, frozen_gold, arms = _gold_pipeline(tmp_path / "score")
    output = tmp_path / "score" / "result.json"
    args = [
        "trial-score",
        "--protocol",
        str(protocol),
        "--registration",
        str(registration),
        "--gold",
        str(frozen_gold),
        "--bootstrap-samples",
        "20",
        "--output",
        str(output),
    ]
    for name, path in arms.items():
        args.extend(["--arm", f"{name}={path}"])
    assert main(args) == 0
    assert "h1=" in capsys.readouterr().out


def test_trial_cli_error_branches(tmp_path: Path, capsys):
    missing = tmp_path / "missing.json"
    assert (
        main(
            [
                "trial-build-sample",
                "--candidates",
                str(missing),
                "--enrollment",
                str(missing),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
        == 2
    )
    assert "ERROR:" in capsys.readouterr().err
    protocol = _protocol(tmp_path / "protocol.json")
    registration, artifacts = _registration(
        tmp_path / "verify", _protocol(tmp_path / "verify/p.json")
    )
    artifacts["analysis"].write_text("tampered", encoding="utf-8")
    args = [
        "trial-verify-registration",
        "--registration",
        str(registration),
        "--protocol",
        str(tmp_path / "verify/p.json"),
    ]
    for name, path in artifacts.items():
        args.extend([f"--{name.replace('_', '-')}", str(path)])
    assert main(args) == 1
    assert "FAIL:" in capsys.readouterr().out
    assert (
        main(
            [
                "trial-validate-sample",
                "--protocol",
                str(protocol),
                "--sample",
                str(missing),
                "--exclusions",
                str(missing),
            ]
        )
        == 2
    )
    assert "ERROR:" in capsys.readouterr().err
    assert (
        main(
            [
                "trial-lock-gold",
                "--review-dir",
                str(tmp_path / "missing-review"),
                "--reviewer",
                str(missing),
                "--reviewer",
                str(missing),
                "--output",
                str(tmp_path / "gold.json"),
            ]
        )
        == 2
    )
    assert "ERROR:" in capsys.readouterr().err
    assert (
        main(
            [
                "trial-score",
                "--protocol",
                str(protocol),
                "--registration",
                str(missing),
                "--gold",
                str(missing),
                "--arm",
                f"report_only={missing}",
                "--arm",
                f"report_only={missing}",
                "--output",
                str(tmp_path / "score.json"),
            ]
        )
        == 2
    )
    assert "unique" in capsys.readouterr().err
    assert (
        main(
            [
                "trial-prepare-review",
                "--sample",
                str(missing),
                "--output-dir",
                str(tmp_path / "review"),
            ]
        )
        == 2
    )
    assert "ERROR:" in capsys.readouterr().err
