from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


USER_AGENT = "ReproCheck-Evidence-Trial-v19/0.30.4 (+https://github.com/nazkari86-lab/reprocheck)"
CONFIG_SCHEMA = "reprocheck.evidence-trial-source-config.v2"
STATE_SCHEMA = "reprocheck.evidence-trial-acquisition-state.v2"
CANDIDATE_SCHEMA = "reprocheck.evidence-trial-candidates.v1"
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused", headers, fp)


def network_fetch(url: str, *, timeout_seconds: float, maximum_bytes: int) -> bytes:
    _require_https(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    last_error: ValueError | None = None
    for _ in range(3):
        with urllib.request.build_opener(_NoRedirect()).open(
            request, timeout=timeout_seconds
        ) as response:
            payload = response.read(maximum_bytes + 1)
            content_length = response.headers.get("Content-Length")
        try:
            _validate_transport_json(payload, maximum_bytes, content_length)
        except ValueError as error:
            last_error = error
            continue
        return payload
    raise ValueError(f"response failed transport validation after 3 attempts: {last_error}")


def _validate_transport_json(
    payload: bytes, maximum_bytes: int, content_length: str | None = None
) -> None:
    if len(payload) > maximum_bytes:
        raise ValueError(f"response exceeds {maximum_bytes} bytes")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as error:
            raise ValueError("response Content-Length is malformed") from error
        if declared != len(payload):
            raise ValueError("response is shorter than its declared Content-Length")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("response is not complete UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError("response JSON must be an object")


def _require_https(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("acquisition permits credential-free HTTPS URLs only")


def _digest(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _exclusive_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except FileExistsError as error:
        raise ValueError(f"immutable acquisition output already exists: {path}") from error


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("unsupported evidence-trial source config schema")
    limits = config.get("limits")
    selection = config.get("selection")
    events = config.get("events")
    if not isinstance(config.get("salt"), str) or not config["salt"]:
        raise ValueError("source config requires a non-empty salt")
    if not isinstance(limits, dict) or not isinstance(selection, dict):
        raise ValueError("source config requires limits and selection objects")
    for name in ("per_response_bytes", "global_bytes", "maximum_source_bytes"):
        if not isinstance(limits.get(name), int) or limits[name] <= 0:
            raise ValueError(f"source config {name} must be a positive integer")
    if (
        not isinstance(limits.get("timeout_seconds"), (int, float))
        or limits["timeout_seconds"] <= 0
    ):
        raise ValueError("source config timeout_seconds must be positive")
    for name in ("selected_per_frame", "maximum_candidates", "owner_cap"):
        if not isinstance(selection.get(name), int) or selection[name] <= 0:
            raise ValueError(f"source config {name} must be a positive integer")
    if selection["owner_cap"] != 1:
        raise ValueError("evidence trial requires a global owner cap of one")
    if not isinstance(events, list) or not events:
        raise ValueError("source config requires at least one search event")
    identifiers: list[str] = []
    for event in events:
        if not isinstance(event, dict) or set(event) != {"event_id", "url"}:
            raise ValueError("each source event must contain only event_id and url")
        if not isinstance(event["event_id"], str) or not re.fullmatch(
            r"search-[0-9]{2}", event["event_id"]
        ):
            raise ValueError("source event IDs must use search-NN")
        if not isinstance(event["url"], str):
            raise ValueError("source event URL must be a string")
        _require_https(event["url"])
        identifiers.append(event["event_id"])
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("source event IDs must be unique")


def _load_exclusions(path: Path) -> tuple[set[str], set[str]]:
    payload = _load_object(path, "trial exclusions")
    owners = payload.get("owners")
    files = payload.get("files")
    if not isinstance(owners, list) or not isinstance(files, list):
        raise ValueError("trial exclusions must contain owners and files arrays")
    return (
        {str(owner).casefold() for owner in owners},
        {str(file_identity).casefold() for file_identity in files},
    )


def _bounded_fetch(
    *,
    url: str,
    event_id: str,
    output_dir: Path,
    state: dict[str, Any],
    limits: dict[str, Any],
    fetch: Callable[[str], bytes],
) -> bytes:
    _require_https(url)
    existing = next((row for row in state["responses"] if row.get("event_id") == event_id), None)
    if existing is not None:
        raw_path = output_dir / existing["raw_file"]
        if existing.get("url") != url or not raw_path.is_file():
            raise ValueError(f"{event_id} frozen response descriptor is inconsistent")
        payload = raw_path.read_bytes()
        if len(payload) != existing.get("size_bytes") or hashlib.sha256(payload).hexdigest() != (
            existing.get("sha256")
        ):
            raise ValueError(f"{event_id} frozen response bytes do not match their descriptor")
        return payload
    payload = fetch(url)
    if len(payload) > limits["per_response_bytes"]:
        raise ValueError(f"{event_id} exceeds the per-response byte cap")
    if state["total_bytes"] + len(payload) > limits["global_bytes"]:
        raise ValueError("acquisition exceeds the global byte cap")
    raw_path = output_dir / "raw" / f"{event_id}.bin"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = raw_path.with_suffix(".bin.part")
    temporary.write_bytes(payload)
    os.replace(temporary, raw_path)
    descriptor = {
        "event_id": event_id,
        "url": url,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "raw_file": str(raw_path.relative_to(output_dir)),
    }
    state["total_bytes"] += len(payload)
    state["responses"].append(descriptor)
    state["responses"].sort(key=lambda row: row["event_id"])
    return payload


def _json_response(payload: bytes, event_id: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{event_id} response is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{event_id} response must be a JSON object")
    return value


def _candidate_rows(search: dict[str, Any], *, salt: str, frame: str) -> list[dict[str, Any]]:
    items = search.get("items")
    if not isinstance(items, list):
        raise ValueError(f"{frame} search response does not contain an items array")
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("repository"), dict):
            continue
        repository = item["repository"].get("full_name")
        repository_url = item["repository"].get("url")
        path = item.get("path")
        indexed_blob = item.get("sha")
        if not all(
            isinstance(value, str) and value
            for value in (repository, repository_url, path, indexed_blob)
        ):
            continue
        if not _SHA40.fullmatch(str(indexed_blob)):
            continue
        _require_https(str(repository_url))
        owner = str(repository).split("/", 1)[0]
        identity = f"{str(repository).casefold()}|{path}|{indexed_blob}"
        rows.append(
            {
                "frame": frame,
                "owner": owner,
                "repository": repository,
                "repository_api_url": repository_url,
                "path": path,
                "indexed_blob_sha": indexed_blob,
                "selection_digest": hashlib.sha256(f"{salt}|{identity}".encode()).hexdigest(),
            }
        )
    return sorted(rows, key=lambda row: (row["selection_digest"], row["repository"], row["path"]))


def _commit_and_content_urls(
    candidate: dict[str, Any], default_branch: str
) -> tuple[str, str]:
    repository_url = candidate["repository_api_url"].rstrip("/")
    branch = urllib.parse.quote(default_branch, safe="")
    path = urllib.parse.quote(candidate["path"], safe="/")
    return (
        f"{repository_url}/commits/{branch}",
        f"{repository_url}/contents/{path}",
    )


def _materialize_candidate(
    candidate: dict[str, Any],
    *,
    ordinal: int,
    output_dir: Path,
    state: dict[str, Any],
    limits: dict[str, Any],
    fetch: Callable[[str], bytes],
) -> dict[str, Any]:
    prefix = f"{candidate['frame']}-candidate-{ordinal:03d}"
    repository_payload = _json_response(
        _bounded_fetch(
            url=candidate["repository_api_url"],
            event_id=f"{prefix}-repository",
            output_dir=output_dir,
            state=state,
            limits=limits,
            fetch=fetch,
        ),
        f"{prefix}-repository",
    )
    default_branch = repository_payload.get("default_branch")
    if not isinstance(default_branch, str) or not default_branch:
        raise ValueError(f"{prefix} repository response lacks a default branch")
    commit_url, content_base = _commit_and_content_urls(candidate, default_branch)
    commit_payload = _json_response(
        _bounded_fetch(
            url=commit_url,
            event_id=f"{prefix}-commit",
            output_dir=output_dir,
            state=state,
            limits=limits,
            fetch=fetch,
        ),
        f"{prefix}-commit",
    )
    commit = commit_payload.get("sha")
    if not isinstance(commit, str) or not _SHA40.fullmatch(commit):
        raise ValueError(f"{prefix} commit response lacks a lowercase 40-character SHA")
    content_url = f"{content_base}?ref={urllib.parse.quote(commit, safe='')}"
    content_payload = _json_response(
        _bounded_fetch(
            url=content_url,
            event_id=f"{prefix}-content",
            output_dir=output_dir,
            state=state,
            limits=limits,
            fetch=fetch,
        ),
        f"{prefix}-content",
    )
    encoded = content_payload.get("content")
    blob_sha = content_payload.get("sha")
    if (
        not isinstance(encoded, str)
        or not isinstance(blob_sha, str)
        or not _SHA40.fullmatch(blob_sha)
    ):
        raise ValueError(f"{prefix} content response lacks base64 content or blob SHA")
    try:
        compact_encoded = "".join(encoded.split())
        content = base64.b64decode(compact_encoded, validate=True)
    except ValueError as error:
        raise ValueError(f"{prefix} content is not valid base64") from error
    if len(content) > limits["maximum_source_bytes"]:
        raise ValueError(f"{prefix} source exceeds the source byte cap")
    if b"\x00" in content:
        raise ValueError(f"{prefix} source is binary")
    source_path = output_dir / "sources" / f"candidate-{len(state['candidates']) + 1:03d}.txt"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = source_path.with_suffix(".txt.part")
    temporary.write_bytes(content)
    os.replace(temporary, source_path)
    repository = candidate["repository"]
    quoted_path = urllib.parse.quote(candidate["path"], safe="/")
    return {
        "candidate_id": f"candidate-{len(state['candidates']) + 1:03d}",
        "frame": candidate["frame"],
        "owner": candidate["owner"],
        "repository": repository,
        "default_branch": default_branch,
        "path": candidate["path"],
        "commit": commit,
        "blob_sha": blob_sha,
        "indexed_blob_sha": candidate["indexed_blob_sha"],
        "immutable_url": f"https://github.com/{repository}/blob/{commit}/{quoted_path}",
        "api_url": content_url,
        "source_file": str(source_path.relative_to(output_dir)),
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "source_bytes": len(content),
        "selection_digest": candidate["selection_digest"],
    }


def _initial_state(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA,
        "config_sha256": _digest(config),
        "completed_event_ids": [],
        "total_bytes": 0,
        "responses": [],
        "frames": [],
        "candidates": [],
    }


def _load_state(path: Path, config: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return _initial_state(config)
    state = _load_object(path, "acquisition state")
    if state.get("schema_version") != STATE_SCHEMA:
        raise ValueError("unsupported acquisition state schema")
    if state.get("config_sha256") != _digest(config):
        raise ValueError("resume config does not match the frozen acquisition state")
    return state


def _failure_manifest(
    output_dir: Path, config: dict[str, Any], state: dict[str, Any], error: Exception
) -> Path:
    failure_dir = output_dir / "failures"
    index = 1
    while (failure_dir / f"failure-{index:03d}.json").exists():
        index += 1
    path = failure_dir / f"failure-{index:03d}.json"
    _exclusive_json(
        path,
        {
            "schema_version": "reprocheck.evidence-trial-acquisition-failure.v1",
            "config_sha256": _digest(config),
            "failure_index": index,
            "error_type": type(error).__name__,
            "error": str(error),
            "completed_event_ids": state.get("completed_event_ids", []),
            "candidate_count": len(state.get("candidates", [])),
            "state_sha256": _digest(state),
            "retry_permitted": True,
        },
    )
    return path


def acquire(
    config: dict[str, Any],
    output_dir: Path,
    fetch: Callable[[str], bytes],
    *,
    exclusions: tuple[set[str], set[str]] = (set(), set()),
) -> Path:
    _validate_config(config)
    limits = config["limits"]
    selection = config["selection"]
    events = sorted(config["events"], key=lambda event: event["event_id"])
    state_path = output_dir / "acquisition-state.json"
    state = _load_state(state_path, config)
    excluded_owners, excluded_files = exclusions
    selected_owners = {row["owner"].casefold() for row in state["candidates"]}
    selected_files = {
        f"{row['owner']}:{row['repository']}:{row['path']}".casefold()
        for row in state["candidates"]
    }
    try:
        for event in events:
            if event["event_id"] in state["completed_event_ids"]:
                continue
            search = _json_response(
                _bounded_fetch(
                    url=event["url"],
                    event_id=event["event_id"],
                    output_dir=output_dir,
                    state=state,
                    limits=limits,
                    fetch=fetch,
                ),
                event["event_id"],
            )
            candidates = _candidate_rows(search, salt=config["salt"], frame=event["event_id"])
            selected_this_frame = 0
            for ordinal, candidate in enumerate(candidates, start=1):
                owner_key = candidate["owner"].casefold()
                file_key = (
                    f"{candidate['owner']}:{candidate['repository']}:{candidate['path']}".casefold()
                )
                if owner_key in excluded_owners or file_key in excluded_files:
                    continue
                if owner_key in selected_owners or file_key in selected_files:
                    continue
                row = _materialize_candidate(
                    candidate,
                    ordinal=ordinal,
                    output_dir=output_dir,
                    state=state,
                    limits=limits,
                    fetch=fetch,
                )
                state["candidates"].append(row)
                selected_owners.add(owner_key)
                selected_files.add(file_key)
                selected_this_frame += 1
                _atomic_json(state_path, state)
                if selected_this_frame >= selection["selected_per_frame"]:
                    break
                if len(state["candidates"]) >= selection["maximum_candidates"]:
                    break
            state["frames"].append(
                {
                    "event_id": event["event_id"],
                    "query_url": event["url"],
                    "api_total_count": search.get("total_count"),
                    "api_returned_count": len(search.get("items", [])),
                    "eligible_candidate_count": len(candidates),
                    "selected_count": selected_this_frame,
                }
            )
            state["frames"].sort(key=lambda row: row["event_id"])
            state["completed_event_ids"].append(event["event_id"])
            state["completed_event_ids"].sort()
            _atomic_json(state_path, state)
            if len(state["candidates"]) >= selection["maximum_candidates"]:
                break
    except Exception as error:
        _atomic_json(state_path, state)
        _failure_manifest(output_dir, config, state, error)
        raise
    manifest = {
        "schema_version": CANDIDATE_SCHEMA,
        "status": "acquired_unreviewed",
        "config_sha256": state["config_sha256"],
        "completed_event_ids": state["completed_event_ids"],
        "frame_count": len(state["frames"]),
        "candidate_count": len(state["candidates"]),
        "independent_owner_count": len({row["owner"].casefold() for row in state["candidates"]}),
        "owner_cap": selection["owner_cap"],
        "frames": state["frames"],
        "candidates": state["candidates"],
        "response_descriptors": state["responses"],
        "candidate_manifest_sha256": "",
    }
    manifest["candidate_manifest_sha256"] = _digest({**manifest, "candidate_manifest_sha256": ""})
    output = output_dir / "candidates.json"
    if output.exists():
        existing = _load_object(output, "candidate manifest")
        if existing != manifest:
            raise ValueError("immutable candidate manifest does not match resumed acquisition")
        return output
    _exclusive_json(output, manifest)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("sources.json"))
    parser.add_argument(
        "--exclusions", type=Path, default=Path(__file__).with_name("exclusions.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    registration = _load_object(args.registration, "trial registration")
    descriptors = registration.get("artifacts", {})
    for name, path in (("acquisition", Path(__file__)), ("source_config", args.config)):
        content = path.read_bytes()
        actual = {
            "filename": path.name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
        if descriptors.get(name) != actual:
            raise SystemExit(f"FAIL: {name} does not match registration")
    config = _load_object(args.config, "source config")
    limits = config["limits"]

    def fetch(url: str) -> bytes:
        return network_fetch(
            url,
            timeout_seconds=limits["timeout_seconds"],
            maximum_bytes=limits["per_response_bytes"],
        )

    result = acquire(config, args.output, fetch, exclusions=_load_exclusions(args.exclusions))
    print(result.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
