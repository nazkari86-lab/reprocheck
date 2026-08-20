import json
from pathlib import Path

from reprocheck.cli import main
from reprocheck.evidence_trial import canonical_digest

from test_evidence_trial import _protocol, _registration, _sample


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
        args.extend([f"--{name}", str(path)])
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
