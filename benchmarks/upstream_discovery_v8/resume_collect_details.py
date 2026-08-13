from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "upstream_discovery_v5" / "collect_details.py"


def unavailable(candidate: dict[str, Any], error: Exception) -> dict[str, Any]:
    return {
        **candidate,
        "body": "",
        "base_sha_at_open": None,
        "head_sha": None,
        "merge_commit_sha": None,
        "merge_parent_sha": None,
        "changed_files": 0,
        "files_returned": 0,
        "files": [],
        "source_unavailable": True,
        "collection_error": f"{type(error).__name__}: {error}",
    }


def is_transient_rate_limit(item: dict[str, Any]) -> bool:
    return bool(item.get("source_unavailable")) and "rate limit exceeded" in str(
        item.get("collection_error", "")
    ).lower()


def is_rate_limit_error(error: Exception) -> bool:
    return "rate limit exceeded" in str(error).lower()


def main() -> int:
    spec = importlib.util.spec_from_file_location("reprocheck_v5_collect_resume", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT

    output = ROOT / "details.json"
    checkpoint = ROOT / "details.partial.json"
    if output.exists():
        raise FileExistsError(output)
    sample = json.loads((ROOT / "sample.json").read_text(encoding="utf-8"))
    details = json.loads(checkpoint.read_text(encoding="utf-8"))["details"]
    transient = [item for item in details if is_transient_rate_limit(item)]
    if transient:
        details = [item for item in details if not is_transient_rate_limit(item)]
        module._write_checkpoint(checkpoint, details)
        print(f"retrying {len(transient)} transient rate-limit records", flush=True)
    completed = {(item["repository"], item["pull_request"]) for item in details}
    pending = [
        candidate
        for candidate in sample["samples"]
        if (candidate["repository"], candidate["pull_request"]) not in completed
    ]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(module._collect_candidate, candidate): candidate
            for candidate in pending
        }
        for future in as_completed(futures):
            candidate = futures[future]
            try:
                detail = future.result()
            except Exception as error:
                if is_rate_limit_error(error):
                    for pending_future in futures:
                        pending_future.cancel()
                    module._write_checkpoint(checkpoint, details)
                    raise RuntimeError(
                        "transient GitHub API rate limit; checkpoint preserved without "
                        f"marking {candidate['repository']}#{candidate['pull_request']} unavailable"
                    ) from error
                detail = unavailable(candidate, error)
                print(
                    f"unavailable {candidate['repository']}#{candidate['pull_request']}: {error}",
                    flush=True,
                )
            details.append(detail)
            if len(details) % 10 == 0 or len(details) == sample["sample_size"]:
                module._write_checkpoint(checkpoint, details)
            print(f"collected {len(details)}/{sample['sample_size']}", flush=True)
    module._write_checkpoint(output, details)
    checkpoint.unlink(missing_ok=True)
    unavailable_count = sum(bool(item.get("source_unavailable")) for item in details)
    print(
        json.dumps(
            {
                "sample_size": len(details),
                "files": sum(len(item["files"]) for item in details),
                "source_unavailable": unavailable_count,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
