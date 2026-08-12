from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "run_study.py"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(
    wheel: Path, expected_path: Path, phase: str, *, system_site_packages: bool = False
) -> None:
    wheel = wheel.resolve()
    expected_path = expected_path.resolve()
    expected = _load(expected_path)
    evaluator = expected["evaluator"]
    if wheel.name != evaluator["filename"] or _sha256(wheel) != evaluator["sha256"]:
        raise ValueError("wheel filename or SHA-256 differs from the expected result")
    if phase != expected["phase"]:
        raise ValueError("requested phase differs from the expected result")

    with tempfile.TemporaryDirectory(prefix="reprocheck-wheel-replay-") as directory:
        directory_path = Path(directory)
        venv = directory_path / "venv"
        isolated_env = dict(os.environ)
        isolated_env.pop("PYTHONPATH", None)
        isolated_env.pop("PYTHONHOME", None)
        venv_command = [sys.executable, "-m", "venv"]
        if system_site_packages:
            venv_command.append("--system-site-packages")
        subprocess.run([*venv_command, str(venv)], check=True, env=isolated_env)
        python = venv / "bin" / "python"
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "--disable-pip-version-check",
                "install",
                "--no-deps",
                str(wheel),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            env=isolated_env,
        )
        actual_path = directory_path / "result.json"
        subprocess.run(
            [
                str(python),
                str(RUNNER),
                "--evaluator-artifact",
                str(wheel),
                "--expected-version",
                evaluator["version"],
                "--phase",
                phase,
                "--output",
                str(actual_path),
            ],
            check=True,
            env=isolated_env,
        )
        actual_text = actual_path.read_text(encoding="utf-8")
        expected_text = expected_path.read_text(encoding="utf-8")
        if actual_text != expected_text:
            diff = "".join(
                difflib.unified_diff(
                    expected_text.splitlines(keepends=True),
                    actual_text.splitlines(keepends=True),
                    fromfile=str(expected_path),
                    tofile="replayed-result.json",
                )
            )
            raise ValueError(f"wheel replay is not byte-identical:\n{diff[:8000]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="replay a challenge result from a wheel")
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--expected-result", type=Path, required=True)
    parser.add_argument(
        "--phase",
        required=True,
        choices=["frozen_evaluator_replay", "development_after_challenge_inspection"],
    )
    parser.add_argument(
        "--system-site-packages",
        action="store_true",
        help="inherit host dependencies for compatibility with old evaluator packages",
    )
    args = parser.parse_args(argv)
    try:
        replay(
            args.wheel,
            args.expected_result,
            args.phase,
            system_site_packages=args.system_site_packages,
        )
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1
    print(f"PASS: byte-identical wheel replay={args.expected_result.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
