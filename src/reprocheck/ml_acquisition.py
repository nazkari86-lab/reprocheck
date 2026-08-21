from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .ml_contracts import canonical_contract_json


DISCOVERY_SCHEMA = "reprocheck.ml-discovery.v1"
EXCLUSION_REASONS = frozenset(
    {"fork", "archived", "unrecognized_license", "duplicate_owner", "duplicate_repository"}
)


class RepositorySearch(Protocol):
    def search(self, query: str, *, limit: int) -> list[dict[str, Any]]: ...

    def resolve_head(self, full_name: str, default_branch: str) -> str: ...


@dataclass(frozen=True)
class SearchFrame:
    frame_id: str
    domain: str
    query: str

    def __post_init__(self) -> None:
        if not self.frame_id or not self.domain or not self.query:
            raise ValueError("search frame fields must be non-empty")


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def load_source_frame(path: Path) -> dict[str, Any]:
    payload = _load_object(path, "ML source frame")
    required = {
        "schema_version",
        "freeze_state",
        "platform",
        "snapshot_sort",
        "maximum_results_per_frame",
        "development_owner_target",
        "recognized_licenses",
        "search_frames",
        "one_repository_per_owner",
        "forks_allowed",
        "required",
        "sampling_order",
        "selection_must_not_use",
        "prospective_exclusion",
    }
    if set(payload) != required or payload["schema_version"] != "reprocheck.ml-source-frame.v1":
        raise ValueError("ML source frame has unexpected, missing, or unsupported fields")
    if payload["freeze_state"] != "selection_rules_defined_sources_not_yet_acquired":
        raise ValueError("ML source frame is not in a pristine pre-acquisition state")
    if payload["one_repository_per_owner"] is not True or payload["forks_allowed"] is not False:
        raise ValueError("ML source frame must forbid forks and enforce one repository per owner")
    limit, target = payload["maximum_results_per_frame"], payload["development_owner_target"]
    if (
        not isinstance(limit, int)
        or not 1 <= limit <= 100
        or not isinstance(target, int)
        or target < 3
    ):
        raise ValueError("ML source frame limits are invalid")
    licenses = payload["recognized_licenses"]
    if not isinstance(licenses, list) or not licenses or len(set(licenses)) != len(licenses):
        raise ValueError("ML source frame licenses must be a non-empty unique array")
    raw_frames = payload["search_frames"]
    if not isinstance(raw_frames, list) or len(raw_frames) < 3:
        raise ValueError("ML source frame requires at least three search frames")
    frames = [SearchFrame(**item) for item in raw_frames]
    if len({item.frame_id for item in frames}) != len(frames):
        raise ValueError("ML source frame frame_id values must be unique")
    forbidden = ("reprocheck", "mismatch", "incorrect metric", "fixed accuracy")
    if any(term in item.query.casefold() for item in frames for term in forbidden):
        raise ValueError("ML source frame query depends on a verifier outcome")
    return payload


def _validate_repository(item: dict[str, Any]) -> None:
    required = {
        "full_name",
        "html_url",
        "owner_id",
        "owner_login",
        "fork",
        "archived",
        "license",
        "default_branch",
        "stargazers_count",
    }
    if set(item) != required:
        raise ValueError("repository search item has unexpected or missing fields")
    if not item["full_name"] or not item["owner_login"] or not item["default_branch"]:
        raise ValueError("repository identifiers must be non-empty")
    if not isinstance(item["owner_id"], int) or item["owner_id"] < 1:
        raise ValueError("repository owner_id must be a positive integer")
    if not isinstance(item["stargazers_count"], int) or item["stargazers_count"] < 0:
        raise ValueError("repository stars must be a nonnegative integer")
    if not isinstance(item["fork"], bool) or not isinstance(item["archived"], bool):
        raise ValueError("repository fork and archived flags must be boolean")


def discover_repositories(
    source_frame: dict[str, Any],
    client: RepositorySearch,
    *,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    # Validate the same structure even when the caller already loaded JSON.
    temporary = Path("source-frame.json")
    if source_frame.get("schema_version") != "reprocheck.ml-source-frame.v1":
        raise ValueError(f"unsupported source frame: {temporary}")
    limit = int(source_frame["maximum_results_per_frame"])
    target = int(source_frame["development_owner_target"])
    licenses = set(str(item) for item in source_frame["recognized_licenses"])
    frames = [SearchFrame(**item) for item in source_frame["search_frames"]]
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("retrieved_at must be an ISO-8601 timestamp") from error

    selected: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    owners: set[int] = set()
    repositories: set[str] = set()
    for frame in frames:
        results = client.search(frame.query, limit=limit)
        ordered = sorted(
            results,
            key=lambda item: (
                -int(item.get("stargazers_count", -1)),
                str(item.get("full_name", "")).casefold(),
            ),
        )
        for item in ordered:
            _validate_repository(item)
            full_name = str(item["full_name"])
            reason = None
            if item["fork"]:
                reason = "fork"
            elif item["archived"]:
                reason = "archived"
            elif str(item["license"]) not in licenses:
                reason = "unrecognized_license"
            elif full_name.casefold() in repositories:
                reason = "duplicate_repository"
            elif int(item["owner_id"]) in owners:
                reason = "duplicate_owner"
            if reason:
                exclusions.append(
                    {"frame_id": frame.frame_id, "repository": full_name, "reason": reason}
                )
                continue
            commit = client.resolve_head(full_name, str(item["default_branch"]))
            if len(commit) != 40 or any(
                character not in "0123456789abcdef" for character in commit
            ):
                raise ValueError(f"GitHub returned an invalid head commit for {full_name}")
            owners.add(int(item["owner_id"]))
            repositories.add(full_name.casefold())
            selected.append(
                {
                    "repository_id": full_name.casefold(),
                    "owner_id": f"github:{item['owner_id']}",
                    "owner_login": item["owner_login"],
                    "source_url": item["html_url"],
                    "commit_sha": commit,
                    "default_branch": item["default_branch"],
                    "license": item["license"],
                    "domain": frame.domain,
                    "frame_id": frame.frame_id,
                    "stargazers_count": item["stargazers_count"],
                }
            )
            if len(selected) >= target:
                break
        if len(selected) >= target:
            break
    payload: dict[str, Any] = {
        "schema_version": DISCOVERY_SCHEMA,
        "status": "target_reached" if len(selected) >= target else "insufficient_candidates",
        "retrieved_at": timestamp,
        "target_owner_count": target,
        "selected_owner_count": len(owners),
        "selected": selected,
        "exclusions": exclusions,
        "source_frame_sha256": hashlib.sha256(
            canonical_contract_json(source_frame).encode()
        ).hexdigest(),
        "discovery_sha256": "",
    }
    payload["discovery_sha256"] = hashlib.sha256(
        canonical_contract_json(payload).encode()
    ).hexdigest()
    return payload


def verify_discovery(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != DISCOVERY_SCHEMA:
        errors.append("unsupported ML discovery schema")
    selected = payload.get("selected")
    exclusions = payload.get("exclusions")
    if not isinstance(selected, list) or not isinstance(exclusions, list):
        errors.append("ML discovery selected and exclusions must be arrays")
        return errors
    owners = [item.get("owner_id") for item in selected if isinstance(item, dict)]
    repositories = [item.get("repository_id") for item in selected if isinstance(item, dict)]
    if len(owners) != len(set(owners)):
        errors.append("ML discovery contains duplicate owners")
    if len(repositories) != len(set(repositories)):
        errors.append("ML discovery contains duplicate repositories")
    if any(
        item.get("reason") not in EXCLUSION_REASONS for item in exclusions if isinstance(item, dict)
    ):
        errors.append("ML discovery contains an unsupported exclusion reason")
    digest = payload.get("discovery_sha256")
    unsigned = {**payload, "discovery_sha256": ""}
    expected = hashlib.sha256(canonical_contract_json(unsigned).encode()).hexdigest()
    if digest != expected:
        errors.append("ML discovery digest mismatch")
    count = payload.get("selected_owner_count")
    if not isinstance(count, int) or count != len(set(owners)):
        errors.append("ML discovery owner count does not match selected records")
    target = payload.get("target_owner_count")
    if not isinstance(target, int) or target < 1:
        errors.append("ML discovery target owner count is invalid")
    expected_status = (
        "target_reached"
        if isinstance(target, int) and len(owners) >= target
        else "insufficient_candidates"
    )
    if payload.get("status") != expected_status:
        errors.append("ML discovery status does not match its counts")
    return errors


def write_discovery(payload: dict[str, Any], path: Path) -> None:
    errors = verify_discovery(payload)
    if errors:
        raise ValueError("cannot write invalid ML discovery: " + "; ".join(errors))
    if path.exists():
        raise ValueError(f"discovery output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_contract_json(payload) + "\n", encoding="utf-8")
