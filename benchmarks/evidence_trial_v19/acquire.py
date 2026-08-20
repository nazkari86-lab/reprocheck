from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


USER_AGENT = "ReproCheck-Evidence-Trial-v19/0.30 (+https://github.com/nazkari86-lab/reprocheck)"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def network_fetch(url: str, *, timeout_seconds: float, maximum_bytes: int) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("acquisition permits HTTPS URLs only")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.build_opener(_NoRedirect()).open(
        request, timeout=timeout_seconds
    ) as response:
        payload = response.read(maximum_bytes + 1)
    if len(payload) > maximum_bytes:
        raise ValueError(f"response exceeds {maximum_bytes} bytes")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def acquire(config: dict[str, Any], output_dir: Path, fetch: Callable[[str], bytes]) -> Path:
    limits = config["limits"]
    events = sorted(config["events"], key=lambda event: event["event_id"])
    state_path = output_dir / "acquisition-state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["config_sha256"] != _digest(config):
            raise ValueError("resume config does not match the frozen acquisition state")
    else:
        state = {
            "schema_version": "reprocheck.evidence-trial-acquisition-state.v1",
            "config_sha256": _digest(config),
            "completed_event_ids": [],
            "total_bytes": 0,
            "records": [],
        }
    for event in events:
        if event["event_id"] in state["completed_event_ids"]:
            continue
        if not event["url"].startswith("https://"):
            raise ValueError("acquisition permits HTTPS URLs only")
        payload = fetch(event["url"])
        if len(payload) > limits["per_response_bytes"]:
            raise ValueError("response exceeds the per-response byte cap")
        if state["total_bytes"] + len(payload) > limits["global_bytes"]:
            raise ValueError("acquisition exceeds the global byte cap")
        digest = hashlib.sha256(payload).hexdigest()
        raw_path = output_dir / "raw" / f"{event['event_id']}.bin"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = raw_path.with_suffix(".bin.part")
        temporary.write_bytes(payload)
        os.replace(temporary, raw_path)
        state["completed_event_ids"].append(event["event_id"])
        state["completed_event_ids"].sort()
        state["total_bytes"] += len(payload)
        state["records"].append(
            {
                "event_id": event["event_id"],
                "url": event["url"],
                "sha256": digest,
                "size_bytes": len(payload),
                "raw_file": str(raw_path.relative_to(output_dir)),
            }
        )
        state["records"].sort(key=lambda row: row["event_id"])
        _atomic_json(state_path, state)
    sample = output_dir / "sample.json"
    _atomic_json(
        sample,
        {
            "schema_version": "reprocheck.evidence-trial-acquisition.v1",
            "config_sha256": state["config_sha256"],
            "records": state["records"],
        },
    )
    return sample


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("sources.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    registration = json.loads(args.registration.read_text(encoding="utf-8"))
    current = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if registration["artifacts"]["acquisition"]["sha256"] != current:
        raise SystemExit("FAIL: acquisition script does not match registration")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    limits = config["limits"]

    def fetch(url: str) -> bytes:
        return network_fetch(
            url,
            timeout_seconds=limits["timeout_seconds"],
            maximum_bytes=limits["per_response_bytes"],
        )

    result = acquire(config, args.output, fetch)
    print(result.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
