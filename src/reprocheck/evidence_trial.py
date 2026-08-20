from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import statistics
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROTOCOL_SCHEMA = "reprocheck.evidence-trial-protocol.v1"
SAMPLE_SCHEMA = "reprocheck.evidence-trial-sample.v1"
REGISTRATION_SCHEMA = "reprocheck.evidence-trial-registration.v1"
TRIAL_STATUSES = ("supported", "contradicted", "not_verifiable")
TRIAL_ARMS = ("report_only", "supplied_metrics", "raw_recomputation")
NATURAL_STRATA = {
    "natural_correction",
    "natural_supported_control",
    "natural_not_verifiable",
    "unchanged_negative_control",
}


def canonical_digest(payload: dict[str, Any], *, blank_field: str | None = None) -> str:
    value = copy.deepcopy(payload)
    if blank_field is not None:
        value[blank_field] = ""
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_descriptor(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"registered artifact does not exist: {path}")
    data = path.read_bytes()
    return {
        "filename": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _validate_schema(payload: dict[str, Any], schema_name: str, label: str) -> None:
    schema = json.loads(files("reprocheck").joinpath("schemas", schema_name).read_text("utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        error = errors[0]
        location = ".".join(str(item) for item in error.path) or "root"
        raise ValueError(f"{label} schema violation at {location}: {error.message}")


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    except FileExistsError as error:
        raise ValueError(f"immutable output already exists: {path}") from error


def load_trial_protocol(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path, "trial protocol")
    _validate_schema(payload, "evidence-trial-protocol-v1.schema.json", "trial protocol")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).upper()
    if any(marker in encoded for marker in ("UNRESOLVED", "TODO", "FIXME", "TBD")):
        raise ValueError("trial protocol contains an unresolved placeholder")
    if payload["schema_version"] != PROTOCOL_SCHEMA:
        raise ValueError("unsupported evidence trial protocol schema")
    if tuple(payload["arms"]) != TRIAL_ARMS:
        raise ValueError("trial arms must be report_only, supplied_metrics, raw_recomputation")
    return payload


def register_evidence_trial(
    *,
    protocol: Path,
    evaluator: Path,
    acquisition: Path,
    analysis: Path,
    exclusions: Path,
    output: Path,
) -> dict[str, Any]:
    if output.exists():
        raise ValueError("trial registration output already exists; registrations are immutable")
    load_trial_protocol(protocol)
    artifacts = {
        name: file_descriptor(path)
        for name, path in {
            "evaluator": evaluator,
            "acquisition": acquisition,
            "analysis": analysis,
            "exclusions": exclusions,
        }.items()
    }
    payload = {
        "schema_version": REGISTRATION_SCHEMA,
        "status": "registered_not_retrieved",
        "protocol": file_descriptor(protocol),
        "artifacts": artifacts,
        "source_contents_inspected_after_registration": False,
        "registration_sha256": "",
    }
    payload["registration_sha256"] = canonical_digest(payload, blank_field="registration_sha256")
    _write_json_exclusive(output, payload)
    return payload


def verify_evidence_trial_registration(
    registration_path: Path,
    *,
    protocol: Path,
    evaluator: Path,
    acquisition: Path,
    analysis: Path,
    exclusions: Path,
) -> list[str]:
    try:
        registration = _load_json_object(registration_path, "trial registration")
        load_trial_protocol(protocol)
    except ValueError as error:
        return [str(error)]
    errors: list[str] = []
    if registration.get("schema_version") != REGISTRATION_SCHEMA:
        errors.append("unsupported evidence trial registration schema")
    if registration.get("status") != "registered_not_retrieved":
        errors.append("trial registration must remain registered_not_retrieved")
    if registration.get("source_contents_inspected_after_registration") is not False:
        errors.append("trial registration source-inspection state is not pristine")
    if registration.get("registration_sha256") != canonical_digest(
        registration, blank_field="registration_sha256"
    ):
        errors.append("trial registration checksum does not match its payload")
    try:
        if registration.get("protocol") != file_descriptor(protocol):
            errors.append("protocol checksum or size does not match")
    except ValueError as error:
        errors.append(str(error))
    registered = registration.get("artifacts")
    if not isinstance(registered, dict):
        errors.append("registration artifacts must be an object")
        registered = {}
    for name, path in {
        "evaluator": evaluator,
        "acquisition": acquisition,
        "analysis": analysis,
        "exclusions": exclusions,
    }.items():
        try:
            if registered.get(name) != file_descriptor(path):
                errors.append(f"{name} checksum or size does not match")
        except ValueError:
            errors.append(f"registered {name} is missing: {path}")
    return errors


def _load_exclusions(value: Path | dict[str, Any]) -> dict[str, Any]:
    payload = _load_json_object(value, "trial exclusions") if isinstance(value, Path) else value
    if not isinstance(payload, dict):
        raise ValueError("trial exclusions must be an object")
    owners = payload.get("owners", [])
    files_ = payload.get("files", [])
    if not isinstance(owners, list) or not all(isinstance(item, str) for item in owners):
        raise ValueError("trial exclusions owners must be a string array")
    if not isinstance(files_, list) or not all(isinstance(item, str) for item in files_):
        raise ValueError("trial exclusions files must be a string array")
    if isinstance(value, Path):
        if payload.get("schema_version") != "reprocheck.evidence-trial-exclusions.v1":
            raise ValueError("unsupported trial exclusions schema")
        if payload.get("union_sha256") != canonical_digest(payload, blank_field="union_sha256"):
            raise ValueError("trial exclusions digest does not match its payload")
    return {"owners": owners, "files": files_}


def _trial_counts(claims: list[dict[str, Any]]) -> dict[str, int]:
    natural = [item for item in claims if item["stratum"] in NATURAL_STRATA]
    return {
        "repository_owners": len({item["owner"] for item in natural}),
        "claims": len(natural),
        "contradicted_claims": sum(item.get("gold_status") == "contradicted" for item in natural),
        "not_verifiable_claims": sum(
            item.get("gold_status") == "not_verifiable" for item in natural
        ),
        "supported_evidence_claims": sum(
            item.get("gold_status") == "supported" and item["evidence_tier"] != "report_only"
            for item in natural
        ),
    }


def validate_trial_sample(
    sample_path: Path,
    protocol_path: Path,
    *,
    exclusions: Path | dict[str, Any],
) -> dict[str, Any]:
    sample = _load_json_object(sample_path, "trial sample")
    protocol = load_trial_protocol(protocol_path)
    _validate_schema(sample, "evidence-trial-sample-v1.schema.json", "trial sample")
    claims = sample["claims"]
    ids = [item["claim_id"] for item in claims]
    if len(ids) != len(set(ids)):
        raise ValueError("trial sample claim_id values must be unique")
    locked = _load_exclusions(exclusions)
    owners = {item["owner"] for item in claims}
    if owners & set(locked["owners"]):
        raise ValueError("trial sample contains an excluded owner")
    paths = {f"{item['owner']}:{item['repository']}:{item['path']}" for item in claims}
    if paths & set(locked["files"]):
        raise ValueError("trial sample contains an excluded file")
    counts = _trial_counts(claims)
    required = protocol["minimum_information"]
    shortfalls = {
        name: {"required": value, "observed": counts[name]}
        for name, value in required.items()
        if counts[name] < value
    }
    return {
        "schema_version": "reprocheck.evidence-trial-sample-gate.v1",
        "status": "insufficient_sample" if shortfalls else "eligible",
        "counts": counts,
        "shortfalls": shortfalls,
    }


def prepare_trial_review(sample_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("trial review output directory must be empty")
    sample = _load_json_object(sample_path, "trial sample")
    _validate_schema(sample, "evidence-trial-sample-v1.schema.json", "trial sample")
    private_fields = {"gold_status", "gold_metric", "gold_value", "gold_rationale"}
    public_claims = [
        {key: value for key, value in claim.items() if key not in private_fields}
        for claim in sample["claims"]
    ]
    private_claims = [
        {key: value for key, value in claim.items() if key == "claim_id" or key in private_fields}
        for claim in sample["claims"]
    ]
    packet_path = output_dir / "public" / "packet.json"
    gold_path = output_dir / "private" / "PRIVATE-internal-gold.json"
    _write_json_exclusive(
        packet_path,
        {
            "schema_version": "reprocheck.evidence-trial-review-packet.v1",
            "blind": True,
            "claims": public_claims,
        },
    )
    _write_json_exclusive(
        gold_path,
        {
            "schema_version": "reprocheck.evidence-trial-internal-gold.v1",
            "sample_sha256": file_descriptor(sample_path)["sha256"],
            "claims": private_claims,
        },
    )
    manifest = {
        "schema_version": "reprocheck.evidence-trial-review-manifest.v1",
        "reviewers_completed": 0,
        "adjudication_complete": False,
        "sample": file_descriptor(sample_path),
        "packet": file_descriptor(packet_path),
        "internal_gold": file_descriptor(gold_path),
    }
    _write_json_exclusive(output_dir / "manifest.json", manifest)
    return manifest


def _review_rows(path: Path) -> tuple[str, dict[str, str], dict[str, Any]]:
    payload = _load_json_object(path, "trial review")
    _validate_schema(payload, "evidence-trial-review-v1.schema.json", "trial review")
    if payload.get("independent") is not True:
        raise ValueError("trial reviewer must explicitly confirm independence")
    rows = payload["reviews"]
    ids = [item["claim_id"] for item in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("trial review must contain every claim ID exactly once")
    return payload["reviewer_id"], {item["claim_id"]: item["status"] for item in rows}, payload


def lock_trial_gold(
    review_dir: Path,
    reviewer_paths: list[Path],
    adjudication_path: Path | None,
    output: Path,
) -> dict[str, Any]:
    if len(reviewer_paths) != 2:
        raise ValueError("trial gold lock requires exactly two independent reviews")
    _load_json_object(review_dir / "manifest.json", "trial review manifest")
    internal_path = review_dir / "private" / "PRIVATE-internal-gold.json"
    internal = _load_json_object(internal_path, "trial internal gold")
    packet = _load_json_object(review_dir / "public" / "packet.json", "trial review packet")
    public_by_id = {item["claim_id"]: item for item in packet["claims"]}
    expected_ids = {item["claim_id"] for item in internal["claims"]}
    parsed = [_review_rows(path) for path in reviewer_paths]
    if parsed[0][0] == parsed[1][0]:
        raise ValueError("trial gold lock requires two distinct reviewer IDs")
    if any(set(rows) != expected_ids for _, rows, _ in parsed):
        raise ValueError("trial review must contain every claim ID exactly once")
    disagreements = {
        claim_id for claim_id in expected_ids if parsed[0][1][claim_id] != parsed[1][1][claim_id]
    }
    adjudicated: dict[str, str] = {}
    adjudication_descriptor: dict[str, Any] | None = None
    if disagreements:
        if adjudication_path is None:
            raise ValueError("adjudication is required for every reviewer disagreement")
        payload = _load_json_object(adjudication_path, "trial adjudication")
        rows = payload.get("adjudications")
        if not isinstance(rows, list):
            raise ValueError("trial adjudication rows are missing")
        adjudicated = {
            item["claim_id"]: item["status"]
            for item in rows
            if isinstance(item, dict)
            and item.get("claim_id") in disagreements
            and item.get("status") in TRIAL_STATUSES
        }
        if set(adjudicated) != disagreements:
            raise ValueError("adjudication must resolve every disagreement exactly once")
        adjudication_descriptor = file_descriptor(adjudication_path)
    final_rows = []
    for item in internal["claims"]:
        claim_id = item["claim_id"]
        reviewer_status = parsed[0][1][claim_id]
        status = adjudicated.get(claim_id, reviewer_status)
        final_rows.append({**public_by_id[claim_id], **item, "gold_status": status})
    agree = len(expected_ids) - len(disagreements)
    total = len(expected_ids)
    confusion = {first: {second: 0 for second in TRIAL_STATUSES} for first in TRIAL_STATUSES}
    for claim_id in expected_ids:
        confusion[parsed[0][1][claim_id]][parsed[1][1][claim_id]] += 1
    observed = agree / total if total else 0.0
    marg_a = {s: sum(confusion[s].values()) / total for s in TRIAL_STATUSES} if total else {}
    marg_b = (
        {s: sum(confusion[a][s] for a in TRIAL_STATUSES) / total for s in TRIAL_STATUSES}
        if total
        else {}
    )
    expected = sum(marg_a[s] * marg_b[s] for s in TRIAL_STATUSES) if total else 0.0
    kappa = None if expected == 1 else (observed - expected) / (1 - expected)
    payload = {
        "schema_version": "reprocheck.evidence-trial-gold-lock.v1",
        "reviewer_count": 2,
        "adjudication_complete": True,
        "manifest": file_descriptor(review_dir / "manifest.json"),
        "internal_gold": file_descriptor(internal_path),
        "reviewers": [file_descriptor(path) for path in reviewer_paths],
        "adjudication": adjudication_descriptor,
        "raw_agreement": observed,
        "cohen_kappa": kappa,
        "claims": sorted(final_rows, key=lambda item: item["claim_id"]),
        "gold_sha256": "",
    }
    payload["gold_sha256"] = canonical_digest(payload, blank_field="gold_sha256")
    _write_json_exclusive(output, payload)
    return payload


def _score_arm(gold: dict[str, dict[str, Any]], predictions: dict[str, str]) -> dict[str, Any]:
    if set(predictions) != set(gold):
        raise ValueError("arm predictions must contain every gold claim exactly once")
    if any(value not in TRIAL_STATUSES for value in predictions.values()):
        raise ValueError("arm prediction contains an invalid tri-state verdict")
    matrix = {actual: {predicted: 0 for predicted in TRIAL_STATUSES} for actual in TRIAL_STATUSES}
    for claim_id, item in gold.items():
        matrix[item["gold_status"]][predictions[claim_id]] += 1
    per_class: dict[str, dict[str, float]] = {}
    for status in TRIAL_STATUSES:
        tp = matrix[status][status]
        fp = sum(matrix[actual][status] for actual in TRIAL_STATUSES if actual != status)
        fn = sum(matrix[status][predicted] for predicted in TRIAL_STATUSES if predicted != status)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        per_class[status] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        }
    false_accusations = sum(
        matrix[actual]["contradicted"] for actual in ("supported", "not_verifiable")
    )
    non_contradictions = sum(
        sum(matrix[actual].values()) for actual in ("supported", "not_verifiable")
    )
    return {
        "confusion_matrix": matrix,
        "per_class": per_class,
        "macro_f1": sum(row["f1"] for row in per_class.values()) / 3,
        "contradiction_recall": per_class["contradicted"]["recall"],
        "false_accusation_rate": false_accusations / non_contradictions
        if non_contradictions
        else 0.0,
    }


def _recall(rows: list[dict[str, Any]], arm: str) -> float:
    contradicted = [row for row in rows if row["gold_status"] == "contradicted"]
    if not contradicted:
        return 0.0
    return sum(row[arm] == "contradicted" for row in contradicted) / len(contradicted)


def _owner_bootstrap_delta(
    rows: list[dict[str, Any]], samples: int, seed: int, comparison: str = "report_only"
) -> list[float]:
    owners = sorted({row["owner"] for row in rows})
    if not owners:
        return [0.0] * samples
    grouped = {owner: [row for row in rows if row["owner"] == owner] for owner in owners}
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        draw = [rng.choice(owners) for _ in owners]
        selected = [row for owner in draw for row in grouped[owner]]
        deltas.append(_recall(selected, "raw_recomputation") - _recall(selected, comparison))
    return sorted(deltas)


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    index = probability * (len(values) - 1)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (index - lower)


def _mcnemar_exact(b: int, c: int) -> float:
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(min(b, c) + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def _holm(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for index, (name, value) in enumerate(ordered):
        running = max(running, min(1.0, value * (count - index)))
        adjusted[name] = running
    return adjusted


def _load_predictions(path: Path) -> dict[str, str]:
    payload = _load_json_object(path, "trial arm predictions")
    rows = payload.get("predictions")
    if not isinstance(rows, list):
        raise ValueError("trial arm predictions must contain a predictions array")
    result: dict[str, str] = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("claim_id"), str)
            or row.get("status") not in TRIAL_STATUSES
        ):
            raise ValueError("trial arm prediction row is invalid")
        if row["claim_id"] in result:
            raise ValueError("trial arm prediction claim IDs must be unique")
        result[row["claim_id"]] = str(row["status"])
    return result


def score_evidence_trial(
    *,
    gold_path: Path,
    arm_paths: dict[str, Path],
    protocol_path: Path,
    registration_path: Path,
    output: Path | None = None,
    bootstrap_samples: int = 5_000,
) -> dict[str, Any]:
    if bootstrap_samples <= 0:
        raise ValueError("bootstrap_samples must be positive")
    protocol = load_trial_protocol(protocol_path)
    registration = _load_json_object(registration_path, "trial registration")
    if registration.get("registration_sha256") != canonical_digest(
        registration, blank_field="registration_sha256"
    ):
        raise ValueError("trial registration checksum does not match its payload")
    if registration.get("protocol") != file_descriptor(protocol_path):
        raise ValueError("trial protocol does not match the frozen registration")
    gold_payload = _load_json_object(gold_path, "trial gold lock")
    if gold_payload.get("gold_sha256") != canonical_digest(gold_payload, blank_field="gold_sha256"):
        raise ValueError("gold lock checksum does not match its payload")
    if gold_payload.get("adjudication_complete") is not True:
        raise ValueError("gold lock is not adjudication-complete")
    if set(arm_paths) != set(TRIAL_ARMS):
        raise ValueError("trial scoring requires exactly the three registered arms")
    gold = {item["claim_id"]: item for item in gold_payload["claims"]}
    predictions = {name: _load_predictions(path) for name, path in arm_paths.items()}
    natural_gold = {
        claim_id: item for claim_id, item in gold.items() if item["stratum"] in NATURAL_STRATA
    }
    controlled_gold = {
        claim_id: item
        for claim_id, item in gold.items()
        if item["stratum"] == "controlled_mutation"
    }
    arm_scores = {
        name: _score_arm(natural_gold, {cid: rows[cid] for cid in natural_gold})
        for name, rows in predictions.items()
    }
    rows = [
        {
            **item,
            **{arm: predictions[arm][claim_id] for arm in TRIAL_ARMS},
        }
        for claim_id, item in natural_gold.items()
    ]
    comparisons: dict[str, Any] = {}
    p_values: dict[str, float] = {}
    for index, comparison in enumerate(("report_only", "supplied_metrics")):
        bootstrap = _owner_bootstrap_delta(rows, bootstrap_samples, 19 + index, comparison)
        b = c = 0
        for row in rows:
            raw_ok = row["raw_recomputation"] == row["gold_status"]
            other_ok = row[comparison] == row["gold_status"]
            b += other_ok and not raw_ok
            c += raw_ok and not other_ok
        name = f"raw_vs_{comparison}"
        p_values[name] = _mcnemar_exact(int(b), int(c))
        comparisons[name] = {
            "contradiction_recall_delta": _recall(rows, "raw_recomputation")
            - _recall(rows, comparison),
            "owner_bootstrap_ci95": [_quantile(bootstrap, 0.025), _quantile(bootstrap, 0.975)],
            "mcnemar_exact_p": p_values[name],
            "discordant": {"other_only_correct": int(b), "raw_only_correct": int(c)},
        }
    adjusted = _holm(p_values)
    for name, value in adjusted.items():
        comparisons[name]["holm_adjusted_p"] = value
    counts = _trial_counts(list(gold.values()))
    shortfalls = {
        name: {"required": required, "observed": counts[name]}
        for name, required in protocol["minimum_information"].items()
        if counts[name] < required
    }
    gate = protocol["success_gate"]
    failed = []
    if shortfalls:
        failed.append("minimum_information")
    if comparisons["raw_vs_report_only"]["owner_bootstrap_ci95"][0] <= 0:
        failed.append("positive_bootstrap_lower_bound")
    if (
        arm_scores["raw_recomputation"]["false_accusation_rate"]
        > gate["maximum_false_accusation_rate"]
    ):
        failed.append("false_accusation_rate")
    if (
        comparisons["raw_vs_report_only"]["contradiction_recall_delta"]
        < gate["minimum_contradiction_recall_delta"]
    ):
        failed.append("minimum_contradiction_recall_delta")
    controlled = (
        {
            "claims": len(controlled_gold),
            "arms": {
                name: _score_arm(controlled_gold, {cid: rows[cid] for cid in controlled_gold})
                for name, rows in predictions.items()
            },
        }
        if controlled_gold
        else {"claims": 0, "arms": {}}
    )
    result = {
        "schema_version": "reprocheck.evidence-trial-result.v1",
        "status": "scored",
        "protocol": file_descriptor(protocol_path),
        "registration": file_descriptor(registration_path),
        "gold": file_descriptor(gold_path),
        "arms": arm_scores,
        "comparisons": comparisons,
        "controlled_mutation": controlled,
        "minimum_information": {"counts": counts, "shortfalls": shortfalls},
        "primary_analysis": {
            "h1_status": "supported" if not failed else "not_supported",
            "failed_gates": failed,
        },
        "scientific_boundary": protocol["scientific_boundary"],
        "result_sha256": "",
    }
    result["result_sha256"] = canonical_digest(result, blank_field="result_sha256")
    _validate_schema(result, "evidence-trial-result-v1.schema.json", "trial result")
    if output is not None:
        _write_json_exclusive(output, result)
    return result


def score_certificate_track(cases: list[dict[str, Any]]) -> dict[str, Any]:
    from .certificate import verify_certificate_file
    from .witness import verify_witness_file

    if not cases:
        raise ValueError("certificate track requires at least one case")
    reductions: list[float] = []
    preserved = 0
    rejected = 0
    tamper_total = 0
    seen_certificates: set[str] = set()
    for case in cases:
        certificate = Path(case["certificate"])
        witness = Path(case["witness"])
        artifact_dir = Path(case["artifact_dir"])
        digest = file_descriptor(certificate)["sha256"]
        if digest != case["certificate_sha256"] or digest in seen_certificates:
            raise ValueError("certificate/witness binding mismatch")
        seen_certificates.add(digest)
        certificate_errors = verify_certificate_file(certificate, artifact_dir)
        witness_errors = verify_witness_file(witness, certificate, artifact_dir)
        if certificate_errors or witness_errors:
            raise ValueError("certificate/witness binding or verification failed")
        witness_payload = _load_json_object(witness, "witness")
        if witness_payload.get("certificate_sha256") not in (None, digest):
            raise ValueError("certificate/witness binding mismatch")
        preserved += case.get("certificate_verdict") == case.get("witness_verdict")
        full_size = len(certificate.read_bytes())
        witness_size = len(witness.read_bytes())
        reductions.append(1 - witness_size / full_size if full_size else 0.0)
        for tampered in case.get("tampered", []):
            tamper_total += 1
            tampered_path = Path(tampered["path"])
            kind = tampered.get("kind", "witness")
            errors = (
                verify_certificate_file(tampered_path, artifact_dir)
                if kind == "certificate"
                else verify_witness_file(tampered_path, certificate, artifact_dir)
            )
            rejected += bool(errors)
    return {
        "schema_version": "reprocheck.evidence-trial-certificate-track.v1",
        "cases": len(cases),
        "verdict_preservation_rate": preserved / len(cases),
        "tamper_cases": tamper_total,
        "tamper_rejection_rate": rejected / tamper_total if tamper_total else 0.0,
        "median_byte_reduction": statistics.median(reductions),
    }
