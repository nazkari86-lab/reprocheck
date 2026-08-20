from __future__ import annotations

from pathlib import Path

from reprocheck.evidence_trial import verify_evidence_trial_registration


def main() -> int:
    root = Path(__file__).resolve().parent
    errors = verify_evidence_trial_registration(
        root / "registration.json",
        protocol=root / "protocol.json",
        evaluator=root / "evaluator" / "reprocheck-0.30.0-py3-none-any.whl",
        acquisition=root / "acquire.py",
        source_config=root / "sources.json",
        analysis=root / "analyze.py",
        exclusions=root / "exclusions.json",
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: v19 protocol and every executable input match the immutable registration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
