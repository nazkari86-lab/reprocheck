from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from .ml_acquisition import EXCLUSION_REASONS, RepositorySearch, SearchFrame, _validate_repository
from .ml_contracts import canonical_contract_json


DISCOVERY_SCHEMA = "reprocheck.ml-discovery.v2"


def validate_source_frame_v2(source_frame: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "freeze_state",
        "platform",
        "snapshot_sort",
        "maximum_results_per_frame",
        "development_owner_target",
        "domain_owner_targets",
        "recognized_licenses",
        "search_frames",
        "one_repository_per_owner",
        "forks_allowed",
        "required",
        "sampling_order",
        "selection_must_not_use",
        "prospective_exclusion",
        "supersedes_discovery_sha256",
    }
    if (
        set(source_frame) != required
        or source_frame.get("schema_version") != "reprocheck.ml-source-frame.v2"
    ):
        raise ValueError("v2 source frame has unexpected, missing, or unsupported fields")
    if source_frame["freeze_state"] != "selection_rules_defined_sources_not_yet_acquired":
        raise ValueError("v2 source frame is not pristine")
    if (
        source_frame["one_repository_per_owner"] is not True
        or source_frame["forks_allowed"] is not False
    ):
        raise ValueError("v2 source frame must enforce owner disjointness and reject forks")
    quotas = source_frame["domain_owner_targets"]
    if not isinstance(quotas, dict) or set(quotas) != {"computer_vision", "nlp", "other_ml"}:
        raise ValueError("v2 source frame must declare the three domain quotas")
    if any(not isinstance(value, int) or value < 1 for value in quotas.values()):
        raise ValueError("v2 domain quotas must be positive integers")
    if sum(quotas.values()) != source_frame["development_owner_target"]:
        raise ValueError("v2 domain quotas must sum to the owner target")
    frames = [SearchFrame(**item) for item in source_frame["search_frames"]]
    if {item.domain for item in frames} != set(quotas) or len(frames) != len(quotas):
        raise ValueError("v2 source frame requires exactly one frame per domain")
    if (
        not isinstance(source_frame["maximum_results_per_frame"], int)
        or not 1 <= source_frame["maximum_results_per_frame"] <= 100
    ):
        raise ValueError("v2 per-frame limit is invalid")
    licenses = source_frame["recognized_licenses"]
    if not isinstance(licenses, list) or not licenses or len(licenses) != len(set(licenses)):
        raise ValueError("v2 licenses must be non-empty and unique")
    supersedes = source_frame["supersedes_discovery_sha256"]
    if not isinstance(supersedes, str) or len(supersedes) != 64:
        raise ValueError("v2 source frame must bind the superseded discovery")


def discover_balanced_repositories(
    source_frame: dict[str, Any], client: RepositorySearch, *, retrieved_at: str | None = None
) -> dict[str, Any]:
    validate_source_frame_v2(source_frame)
    limit = source_frame["maximum_results_per_frame"]
    quotas = source_frame["domain_owner_targets"]
    licenses = set(source_frame["recognized_licenses"])
    frames = [SearchFrame(**item) for item in source_frame["search_frames"]]
    timestamp = retrieved_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("retrieved_at must be ISO-8601") from error
    owners: set[int] = set()
    repositories: set[str] = set()
    selected: list[dict[str, Any]] = []
    exclusions: list[dict[str, str]] = []
    domain_counts = {domain: 0 for domain in quotas}
    for frame in frames:
        results = sorted(
            client.search(frame.query, limit=limit),
            key=lambda item: (
                -int(item.get("stargazers_count", -1)),
                str(item.get("full_name", "")).casefold(),
            ),
        )
        for item in results:
            _validate_repository(item)
            full_name = str(item["full_name"])
            reason = None
            if item["fork"]:
                reason = "fork"
            elif item["archived"]:
                reason = "archived"
            elif item["license"] not in licenses:
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
            domain_counts[frame.domain] += 1
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
            if domain_counts[frame.domain] >= quotas[frame.domain]:
                break
    target_reached = all(domain_counts[name] >= quotas[name] for name in quotas)
    payload: dict[str, Any] = {
        "schema_version": DISCOVERY_SCHEMA,
        "status": "target_reached" if target_reached else "insufficient_candidates",
        "retrieved_at": timestamp,
        "target_owner_count": source_frame["development_owner_target"],
        "selected_owner_count": len(owners),
        "domain_owner_targets": quotas,
        "domain_owner_counts": domain_counts,
        "selected": selected,
        "exclusions": exclusions,
        "source_frame_sha256": hashlib.sha256(
            canonical_contract_json(source_frame).encode()
        ).hexdigest(),
        "supersedes_discovery_sha256": source_frame["supersedes_discovery_sha256"],
        "discovery_sha256": "",
    }
    payload["discovery_sha256"] = hashlib.sha256(
        canonical_contract_json(payload).encode()
    ).hexdigest()
    return payload


def verify_balanced_discovery(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != DISCOVERY_SCHEMA:
        errors.append("unsupported balanced discovery schema")
    selected, exclusions = payload.get("selected"), payload.get("exclusions")
    if not isinstance(selected, list) or not isinstance(exclusions, list):
        return [*errors, "balanced discovery selected and exclusions must be arrays"]
    owners = [item.get("owner_id") for item in selected if isinstance(item, dict)]
    repos = [item.get("repository_id") for item in selected if isinstance(item, dict)]
    if len(owners) != len(set(owners)):
        errors.append("balanced discovery contains duplicate owners")
    if len(repos) != len(set(repos)):
        errors.append("balanced discovery contains duplicate repositories")
    quotas, counts = payload.get("domain_owner_targets"), payload.get("domain_owner_counts")
    if not isinstance(quotas, dict) or not isinstance(counts, dict) or set(quotas) != set(counts):
        errors.append("balanced discovery domain counts are malformed")
        target_reached = False
    else:
        observed = {
            name: sum(item.get("domain") == name for item in selected if isinstance(item, dict))
            for name in quotas
        }
        if counts != observed:
            errors.append("balanced discovery domain counts do not match selected records")
        target_reached = all(counts.get(name, 0) >= quotas[name] for name in quotas)
    if any(
        item.get("reason") not in EXCLUSION_REASONS for item in exclusions if isinstance(item, dict)
    ):
        errors.append("balanced discovery contains an unsupported exclusion reason")
    if payload.get("selected_owner_count") != len(set(owners)):
        errors.append("balanced discovery owner count does not match")
    expected_status = "target_reached" if target_reached else "insufficient_candidates"
    if payload.get("status") != expected_status:
        errors.append("balanced discovery status does not match domain quotas")
    unsigned = {**payload, "discovery_sha256": ""}
    if (
        payload.get("discovery_sha256")
        != hashlib.sha256(canonical_contract_json(unsigned).encode()).hexdigest()
    ):
        errors.append("balanced discovery digest mismatch")
    return errors
