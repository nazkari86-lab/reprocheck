from __future__ import annotations

import difflib
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WHEEL = ROOT / "evaluator" / "reprocheck-0.8.0-py3-none-any.whl"
RUNNER = ROOT / "run_development_v08.py"
EXPECTED = ROOT / "results" / "development-v0.8.json"
HASHES = {
    WHEEL: "c08925b2c955452c59dfe2c8f0838afb2e90b300207e990ce00041f5502733a3",
    RUNNER: "5312ec6124fa6fe3d3e4321f3f19a3b24f9669c7f949665e9f6e3c101ea57cdc",
    EXPECTED: "1b0baaa36a4f42a1780f12bb7d12aa07196b1030ee9c53d70dad3828d76f596f",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay() -> None:
    for path, expected_hash in HASHES.items():
        if _sha256(path) != expected_hash:
            raise ValueError(f"frozen v0.8 replay input changed: {path}")
    with tempfile.TemporaryDirectory(prefix="reprocheck-v08-development-replay-") as directory:
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
        actual = temporary / "development-v0.8.json"
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
                    tofile="replayed-development-v0.8.json",
                )
            )
            raise ValueError(f"v0.8 development replay is not byte-identical:\n{diff[:8000]}")


def main() -> int:
    try:
        replay()
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print(f"PASS: byte-identical v0.8 development replay={EXPECTED.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
