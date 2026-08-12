from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
RUNNER = ROOT / "run_zero_shot.py"
EXPECTED = ROOT / "results" / "zero-shot-v0.6.json"
WHEEL = (
    PROJECT
    / "benchmarks"
    / "challenge_artifacts"
    / "evaluator"
    / "reprocheck-0.6.0-py3-none-any.whl"
)
EXPECTED_RESULT_SHA256 = "f87ac0c5c10f00c289bd4046ea0f67d07f26d4a5aba3dab74fa8f54fe935d83f"
EXPECTED_WHEEL_SHA256 = "c9cbc753f0027d2815dcc9105603580495c2ee9797364c84e6d3f3f38b84e1f6"
EXPECTED_RUNNER_SHA256 = "d7b4320d2e47f23e79a38f5ceaebef417ae44d360559475e7bf0ede642981fee"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay() -> None:
    for path, expected in (
        (EXPECTED, EXPECTED_RESULT_SHA256),
        (WHEEL, EXPECTED_WHEEL_SHA256),
        (RUNNER, EXPECTED_RUNNER_SHA256),
    ):
        if _sha256(path) != expected:
            raise ValueError(f"frozen replay input changed: {path}")

    with tempfile.TemporaryDirectory(prefix="reprocheck-holdout-replay-") as directory:
        temporary = Path(directory)
        venv = temporary / "venv"
        isolated_env = dict(os.environ)
        isolated_env.pop("PYTHONPATH", None)
        isolated_env.pop("PYTHONHOME", None)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, env=isolated_env)
        python = venv / "bin" / "python"
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "--disable-pip-version-check",
                "install",
                "--no-deps",
                str(WHEEL),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            env=isolated_env,
        )
        actual = temporary / "zero-shot-v0.6.json"
        subprocess.run(
            [
                str(python),
                str(RUNNER),
                "--evaluator-artifact",
                str(WHEEL),
                "--output",
                str(actual),
            ],
            check=True,
            env=isolated_env,
        )
        expected_text = EXPECTED.read_text(encoding="utf-8")
        actual_text = actual.read_text(encoding="utf-8")
        if actual_text != expected_text:
            diff = "".join(
                difflib.unified_diff(
                    expected_text.splitlines(keepends=True),
                    actual_text.splitlines(keepends=True),
                    fromfile=str(EXPECTED),
                    tofile="replayed-zero-shot-v0.6.json",
                )
            )
            raise ValueError(f"holdout replay is not byte-identical:\n{diff[:8000]}")


def main() -> int:
    try:
        replay()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print(f"PASS: byte-identical preregistered holdout replay={EXPECTED.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
