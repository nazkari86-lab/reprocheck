from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from reprocheck.audit import run_audit
from reprocheck.witness import build_witness_file, verify_witness_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="reprocheck-v19-demo-") as raw:
        root = Path(raw)
        report = root / "report.md"
        metrics = root / "metrics.json"
        certificate = root / "certificate.json"
        witness = root / "witness.json"
        report.write_text("Accuracy: 80%\n", encoding="utf-8")
        metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
        audit = run_audit(report_path=report, metrics_path=metrics)
        certificate.write_text(
            json.dumps(audit.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        build_witness_file(certificate, 0, witness, root)
        witness_errors = verify_witness_file(witness, certificate, root)
        tampered = root / "tampered-witness.json"
        payload = json.loads(witness.read_text(encoding="utf-8"))
        payload["rule_inputs"]["observed"] = 0.8
        tampered.write_text(json.dumps(payload), encoding="utf-8")
        tamper_errors = verify_witness_file(tampered, certificate, root)
        result = {
            "schema_version": "reprocheck.evidence-trial-demo.v1",
            "scientific_status": "demonstration_only",
            "claims": [
                {"claim_id": "demo-supported", "verdict": "supported"},
                {"claim_id": "demo-contradicted", "verdict": "contradicted"},
                {"claim_id": "demo-not-verifiable", "verdict": "not_verifiable"},
            ],
            "witness_valid": not witness_errors,
            "tampered_witness_rejected": bool(tamper_errors),
            "tamper_errors": tamper_errors,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"claims=3 witness_valid={str(result['witness_valid']).lower()} "
        f"tamper_rejected={str(result['tampered_witness_rejected']).lower()}"
    )
    return 0 if result["witness_valid"] and result["tampered_witness_rejected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
