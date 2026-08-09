from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "source-manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(split: str, output_dir: Path) -> Path:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    file_info = manifest["files"][split]
    output = output_dir / f"{split}.parquet"
    output.parent.mkdir(parents=True, exist_ok=True)
    url = (
        f"{manifest['mirror_repository']}/resolve/{manifest['mirror_revision']}/"
        f"{file_info['path']}?download=true"
    )
    if not output.exists() or _sha256(output) != file_info["sha256"]:
        temporary = output.with_suffix(".parquet.part")
        try:
            with (
                urllib.request.urlopen(url, timeout=120) as response,
                temporary.open("wb") as handle,
            ):
                while chunk := response.read(1024 * 1024):
                    handle.write(chunk)
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
    if output.stat().st_size != file_info["bytes"] or _sha256(output) != file_info["sha256"]:
        raise ValueError(f"PAWS {split} source does not match the locked manifest")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["validation", "test", "all"], default="validation")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "sources")
    args = parser.parse_args()
    splits = ("validation", "test") if args.split == "all" else (args.split,)
    for split in splits:
        output = fetch(split, args.output_dir)
        print(f"PASS: PAWS {split} source={output} sha256={_sha256(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
