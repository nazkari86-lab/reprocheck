from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import shutil
import stat
from pathlib import Path
from statistics import mean, median
from typing import Any

from .audit import run_audit
from .certificate import verify_certificate_file


MASTER_SCHEMA = "reprocheck.human-study-master.v1"
PACKET_SCHEMA = "reprocheck.human-study-packet.v1"
RESPONSE_SCHEMA = "reprocheck.human-study-response.v1"


def prepare_human_study_master(protocol: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise ValueError("human-study master output already exists; preparation is immutable")
    protocol_payload = _load_object(protocol, "human-study protocol")
    _validate_protocol(protocol_payload)
    cases_dir = output_dir / "private" / "cases"
    cases_dir.mkdir(parents=True)
    gold_cases = []
    for pair, family in enumerate(("metric", "recomputation", "split", "notebook"), start=1):
        for variant, defect_present in (("A", True), ("B", False)):
            case_id = f"P{pair}{variant}"
            case_dir = cases_dir / case_id
            case_dir.mkdir()
            certificate = _build_case(case_dir, family, defect_present)
            gold_cases.append(
                {
                    "case_id": case_id,
                    "pair": pair,
                    "family": family,
                    "defect_present": defect_present,
                    "accepted_verdict": "defect" if defect_present else "clean",
                    "certificate_filename": certificate.name,
                }
            )
    gold = {
        "schema_version": "reprocheck.human-study-gold.v1",
        "protocol_sha256": _sha256(protocol),
        "randomization_salt": secrets.token_hex(32),
        "cases": gold_cases,
    }
    gold_path = output_dir / "private" / "PRIVATE-gold.json"
    gold_path.write_text(
        json.dumps(gold, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _harden_private_tree(output_dir / "private")
    manifest = {
        "schema_version": MASTER_SCHEMA,
        "status": "prepared_not_approved_not_executed",
        "participants_completed": 0,
        "protocol": _descriptor(protocol),
        "gold": _descriptor(gold_path),
        "case_count": len(gold_cases),
        "pair_count": 4,
        "master_sha256": "",
    }
    manifest["master_sha256"] = _digest(manifest, "master_sha256")
    (output_dir / "master.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def issue_human_study_packet(
    master_dir: Path,
    participant_code: str,
    approval_reference: str,
    output_dir: Path,
) -> dict[str, Any]:
    if output_dir.exists():
        raise ValueError("participant packet output already exists")
    if not participant_code or any(character.isspace() for character in participant_code):
        raise ValueError("participant code must be non-empty and contain no whitespace")
    if len(approval_reference.strip()) < 4:
        raise ValueError("a real approval reference is required before issuing a packet")
    master_errors = verify_human_study_master(master_dir)
    if master_errors:
        raise ValueError("human-study master is invalid: " + "; ".join(master_errors))
    manifest = _load_object(master_dir / "master.json", "human-study master")
    if manifest.get("status") != "prepared_not_approved_not_executed":
        raise ValueError("human-study master has an unexpected status")
    gold_path = master_dir / "private" / "PRIVATE-gold.json"
    gold = _load_object(gold_path, "human-study gold")
    salt = gold.get("randomization_salt")
    if not isinstance(salt, str) or len(salt) != 64:
        raise ValueError("human-study gold has no valid private randomization salt")
    arm = (
        int(
            hmac.new(bytes.fromhex(salt), participant_code.encode(), hashlib.sha256).hexdigest(), 16
        )
        % 2
    )
    public_cases = output_dir / "cases"
    public_cases.mkdir(parents=True)
    assignments = []
    for item in gold["cases"]:
        case_id = item["case_id"]
        pair = int(item["pair"])
        variant = case_id[-1]
        assisted = (variant == "A") == bool((arm + pair) % 2)
        condition = "assisted" if assisted else "manual"
        source_dir = master_dir / "private" / "cases" / case_id
        target_dir = public_cases / case_id
        target_dir.mkdir()
        for source in source_dir.iterdir():
            if source.name == "audit.json" and not assisted:
                continue
            if source.is_file():
                shutil.copy2(source, target_dir / source.name)
        assignments.append(
            {
                "case_id": case_id,
                "pair": pair,
                "condition": condition,
                "available_files": sorted(path.name for path in target_dir.iterdir()),
            }
        )
    assignments.sort(key=lambda item: (item["pair"], item["case_id"]))
    packet = {
        "schema_version": PACKET_SCHEMA,
        "participant_code": participant_code,
        "approval_reference": approval_reference.strip(),
        "counterbalance_arm": arm,
        "instructions": (
            "Inspect each case independently. Do not discuss cases or inspect private gold. "
            "Record elapsed active review time, verdict, confidence, and rationale."
        ),
        "assignments": assignments,
        "packet_sha256": "",
    }
    packet["packet_sha256"] = _digest(packet, "packet_sha256")
    (output_dir / "packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    response = {
        "schema_version": RESPONSE_SCHEMA,
        "participant_code": participant_code,
        "packet_sha256": packet["packet_sha256"],
        "approval_reference": approval_reference.strip(),
        "consent_confirmed": False,
        "independent_review_confirmed": False,
        "responses": [
            {
                "case_id": item["case_id"],
                "condition": item["condition"],
                "verdict": None,
                "duration_seconds": None,
                "confidence": None,
                "rationale": "",
            }
            for item in assignments
        ],
    }
    (output_dir / "response-template.json").write_text(
        json.dumps(response, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return packet


def verify_human_study_master(master_dir: Path, protocol: Path | None = None) -> list[str]:
    try:
        manifest = _load_object(master_dir / "master.json", "human-study master")
    except ValueError as error:
        return [str(error)]
    errors: list[str] = []
    if manifest.get("schema_version") != MASTER_SCHEMA:
        errors.append("unsupported human-study master schema")
    if manifest.get("status") != "prepared_not_approved_not_executed":
        errors.append("human-study master has an unexpected status")
    if manifest.get("participants_completed") != 0:
        errors.append("unexecuted human-study master cannot claim completed participants")
    if manifest.get("master_sha256") != _digest(manifest, "master_sha256"):
        errors.append("human-study master checksum does not match its payload")
    gold_path = master_dir / "private" / "PRIVATE-gold.json"
    if not gold_path.is_file() or manifest.get("gold") != _descriptor(gold_path):
        errors.append("human-study private gold checksum or size does not match")
        return errors
    insecure_private_paths = [
        path
        for path in (gold_path.parent, *gold_path.parent.rglob("*"))
        if stat.S_IMODE(path.stat().st_mode) & 0o077
    ]
    if insecure_private_paths:
        errors.append("human-study private files must not be accessible by group or other users")
    if protocol is not None:
        try:
            protocol_payload = _load_object(protocol, "human-study protocol")
            _validate_protocol(protocol_payload)
        except ValueError as error:
            errors.append(str(error))
        else:
            if manifest.get("protocol") != _descriptor(protocol):
                errors.append("human-study protocol checksum or size does not match")
    try:
        gold = _load_object(gold_path, "human-study gold")
    except ValueError as error:
        return errors + [str(error)]
    cases = gold.get("cases")
    if not isinstance(cases, list) or len(cases) != manifest.get("case_count"):
        errors.append("human-study case count does not match private gold")
        return errors
    for item in cases:
        if not isinstance(item, dict) or not isinstance(item.get("case_id"), str):
            errors.append("human-study gold contains a malformed case")
            continue
        case_dir = master_dir / "private" / "cases" / item["case_id"]
        certificate = case_dir / str(item.get("certificate_filename"))
        case_errors = verify_certificate_file(certificate, case_dir)
        errors.extend(f"{item['case_id']}: {error}" for error in case_errors)
    return errors


def score_human_study(master_dir: Path, response_paths: list[Path], output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("human-study result already exists; frozen results are immutable")
    if not response_paths:
        raise ValueError("at least one real participant response is required")
    master_errors = verify_human_study_master(master_dir)
    if master_errors:
        raise ValueError("human-study master is invalid: " + "; ".join(master_errors))
    gold = _load_object(master_dir / "private" / "PRIVATE-gold.json", "human-study gold")
    gold_by_case = {item["case_id"]: item for item in gold["cases"]}
    participants = []
    seen_codes = set()
    rows = []
    for path in response_paths:
        response = _load_object(path, "human-study response")
        code = response.get("participant_code")
        if not isinstance(code, str) or not code or code in seen_codes:
            raise ValueError("participant codes must be non-empty and unique")
        seen_codes.add(code)
        if response.get("schema_version") != RESPONSE_SCHEMA:
            raise ValueError(f"unsupported response schema for {code}")
        if response.get("consent_confirmed") is not True:
            raise ValueError(f"participant {code} did not confirm consent")
        if response.get("independent_review_confirmed") is not True:
            raise ValueError(f"participant {code} did not confirm independent review")
        packet = _load_object(path.parent / "packet.json", "human-study packet")
        if packet.get("schema_version") != PACKET_SCHEMA:
            raise ValueError(f"participant {code} has an unsupported packet schema")
        if packet.get("packet_sha256") != _digest(packet, "packet_sha256"):
            raise ValueError(f"participant {code} packet checksum does not match")
        if packet.get("participant_code") != code:
            raise ValueError(f"participant {code} packet identity does not match")
        if response.get("packet_sha256") != packet.get("packet_sha256"):
            raise ValueError(f"participant {code} response is not bound to its packet")
        if response.get("approval_reference") != packet.get("approval_reference"):
            raise ValueError(f"participant {code} approval reference does not match packet")
        assignments = packet.get("assignments")
        if not isinstance(assignments, list):
            raise ValueError(f"participant {code} packet assignments are malformed")
        assigned_conditions = {
            item.get("case_id"): item.get("condition")
            for item in assignments
            if isinstance(item, dict)
        }
        answers = response.get("responses")
        if not isinstance(answers, list) or len(answers) != len(gold_by_case):
            raise ValueError(f"participant {code} has an incomplete response set")
        seen_cases = set()
        for answer in answers:
            if not isinstance(answer, dict):
                raise ValueError(f"participant {code} has a malformed answer")
            case_id = answer.get("case_id")
            if case_id not in gold_by_case or case_id in seen_cases:
                raise ValueError(f"participant {code} has an unknown or duplicate case")
            seen_cases.add(case_id)
            condition = answer.get("condition")
            verdict = answer.get("verdict")
            duration = answer.get("duration_seconds")
            confidence = answer.get("confidence")
            if condition not in {"manual", "assisted"} or verdict not in {"clean", "defect"}:
                raise ValueError(f"participant {code} has an invalid condition or verdict")
            if assigned_conditions.get(case_id) != condition:
                raise ValueError(f"participant {code} response condition differs from packet")
            if (
                not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or duration <= 0
            ):
                raise ValueError(f"participant {code} has an invalid duration")
            if (
                not isinstance(confidence, int)
                or isinstance(confidence, bool)
                or not 1 <= confidence <= 5
            ):
                raise ValueError(f"participant {code} has invalid confidence")
            rows.append(
                {
                    "participant_code": code,
                    "case_id": case_id,
                    "condition": condition,
                    "correct": verdict == gold_by_case[case_id]["accepted_verdict"],
                    "duration_seconds": float(duration),
                    "confidence": confidence,
                    "defect_present": gold_by_case[case_id]["defect_present"],
                    "verdict": verdict,
                }
            )
        participants.append(code)
    conditions = {
        condition: _condition_summary(rows, condition) for condition in ("manual", "assisted")
    }
    participant_differences = []
    for code in participants:
        manual = [
            row for row in rows if row["participant_code"] == code and row["condition"] == "manual"
        ]
        assisted = [
            row
            for row in rows
            if row["participant_code"] == code and row["condition"] == "assisted"
        ]
        participant_differences.append(
            {
                "participant_code": code,
                "accuracy_difference_assisted_minus_manual": mean(
                    row["correct"] for row in assisted
                )
                - mean(row["correct"] for row in manual),
                "median_time_difference_assisted_minus_manual": median(
                    row["duration_seconds"] for row in assisted
                )
                - median(row["duration_seconds"] for row in manual),
            }
        )
    result = {
        "schema_version": "reprocheck.human-study-result.v1",
        "status": "descriptive_only" if len(participants) < 12 else "preregistered_sample_complete",
        "participant_count": len(participants),
        "minimum_preregistered_participants": 12,
        "conditions": conditions,
        "participant_differences": participant_differences,
        "scientific_boundary": (
            "Results below the preregistered sample size are descriptive only. Synthetic "
            "controlled cases do not establish real publication-review time savings."
        ),
        "response_sha256": [_descriptor(path) for path in response_paths],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def _build_case(root: Path, family: str, defect: bool) -> Path:
    report = root / "report.md"
    metrics = root / "metrics.json"
    predictions = root / "predictions.csv"
    train = root / "train.csv"
    test = root / "test.csv"
    notebook = root / "analysis.ipynb"
    report.write_text("Accuracy: 90%\n", encoding="utf-8")
    metrics.write_text('{"accuracy": 0.8}\n' if defect else '{"accuracy": 0.9}\n', encoding="utf-8")
    predictions.write_text(
        "y_true,y_pred\n0,0\n1,1\n" if defect else "y_true,y_pred\n0,0\n1,0\n",
        encoding="utf-8",
    )
    train.write_text("id,text,label\n1,alpha,0\n", encoding="utf-8")
    test.write_text(
        "id,text,label\n1,alpha,0\n" if defect else "id,text,label\n2,beta,1\n",
        encoding="utf-8",
    )
    notebook_source = "model.fit(X_test)" if defect else "model.fit(X_train)"
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "metadata": {},
                        "outputs": [],
                        "source": ["import random\n", "random.seed(2026)\n", notebook_source],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    kwargs: dict[str, Any] = {"report_path": report}
    if family == "metric":
        kwargs["metrics_path"] = metrics
    elif family == "recomputation":
        metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
        kwargs.update(metrics_path=metrics, predictions_path=predictions)
    elif family == "split":
        metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
        kwargs.update(
            metrics_path=metrics,
            train_path=train,
            test_path=test,
            label_column="label",
            identity_columns=["id"],
        )
    elif family == "notebook":
        metrics.write_text('{"accuracy": 0.9}\n', encoding="utf-8")
        kwargs.update(metrics_path=metrics, notebook_path=notebook)
    audit = run_audit(**kwargs)
    certificate = root / "audit.json"
    certificate.write_text(
        json.dumps(audit.to_dict(), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return certificate


def _condition_summary(rows: list[dict[str, Any]], condition: str) -> dict[str, Any]:
    selected = [row for row in rows if row["condition"] == condition]
    correct = sum(row["correct"] for row in selected)
    false_positives = sum(
        not row["defect_present"] and row["verdict"] == "defect" for row in selected
    )
    false_negatives = sum(row["defect_present"] and row["verdict"] == "clean" for row in selected)
    return {
        "responses": len(selected),
        "accuracy": correct / len(selected),
        "median_duration_seconds": median(row["duration_seconds"] for row in selected),
        "mean_confidence": mean(row["confidence"] for row in selected),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _validate_protocol(payload: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "title",
        "design",
        "primary_endpoint",
        "secondary_endpoints",
        "minimum_participants",
        "approvals_required_before_distribution",
        "consent_required",
        "analysis_plan",
        "scientific_boundary",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError("human-study protocol is missing: " + ", ".join(missing))
    if payload.get("minimum_participants") != 12:
        raise ValueError("human-study protocol must preserve the preregistered sample minimum")
    if payload.get("approvals_required_before_distribution") is not True:
        raise ValueError("human-study protocol must require approval before distribution")
    if payload.get("consent_required") is not True:
        raise ValueError("human-study protocol must require consent")


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _descriptor(path: Path) -> dict[str, Any]:
    return {"filename": path.name, "sha256": _sha256(path), "size_bytes": path.stat().st_size}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(payload: dict[str, Any], field: str) -> str:
    canonical = dict(payload)
    canonical[field] = ""
    return hashlib.sha256(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def _harden_private_tree(root: Path) -> None:
    root.chmod(0o700)
    for path in root.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
