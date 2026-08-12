from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WHEEL = ROOT / "evaluator" / "reprocheck-0.7.0-py3-none-any.whl"
RUNNER = ROOT / "run_development_v07.py"
EXPECTED = ROOT / "results" / "development-v0.7.json"
HASHES = {
    WHEEL: "8c182c3e2cdd41d47e296653950429d1d12cfc0837b63db565f19f2eb65a09ee",
    RUNNER: "78e172dc12a42e0dbc28890d2ba69de0161c4690d613beb84f51d002421a74b9",
    EXPECTED: "a3bb4b0a86fe14e396615b798ededb3e6cd9c97c2c17556557606722ec595e65",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay() -> None:
    for path, expected_hash in HASHES.items():
        if _sha256(path) != expected_hash:
            raise ValueError(f"frozen development replay input changed: {path}")
    with tempfile.TemporaryDirectory(prefix="reprocheck-v07-development-replay-") as directory:
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
        actual = temporary / "development-v0.7.json"
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
                    tofile="replayed-development-v0.7.json",
                )
            )
            raise ValueError(f"v0.7 development replay is not byte-identical:\n{diff[:8000]}")


def main() -> int:
    try:
        replay()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print(f"PASS: byte-identical v0.7 development replay={EXPECTED.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
