from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WHEEL = ROOT.parent / "holdout_artifacts" / "evaluator" / "reprocheck-0.7.0-py3-none-any.whl"
RUNNER = ROOT / "run_zero_shot.py"
EXPECTED = ROOT / "results" / "zero-shot-v0.7.json"
HASHES = {
    WHEEL: "8c182c3e2cdd41d47e296653950429d1d12cfc0837b63db565f19f2eb65a09ee",
    RUNNER: "bbcc19e39f9308cca694f3ba3d79e36c611261d7fb2f6d8fbed880e0aaa25e04",
    EXPECTED: "74c7547eee265a19c8ee2d0269f384583dddb96228d4c53eef5022e1654a1b57",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay() -> None:
    for path, expected_hash in HASHES.items():
        if _sha256(path) != expected_hash:
            raise ValueError(f"frozen cross-domain replay input changed: {path}")
    with tempfile.TemporaryDirectory(prefix="reprocheck-cross-domain-replay-") as directory:
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
        actual = temporary / "zero-shot-v0.7.json"
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
        if expected_text != actual_text:
            diff = "".join(
                difflib.unified_diff(
                    expected_text.splitlines(keepends=True),
                    actual_text.splitlines(keepends=True),
                    fromfile=str(EXPECTED),
                    tofile="replayed-zero-shot-v0.7.json",
                )
            )
            raise ValueError(f"cross-domain replay is not byte-identical:\n{diff[:8000]}")


def main() -> int:
    try:
        replay()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print(f"PASS: byte-identical cross-domain v0.7 zero-shot replay={EXPECTED.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
