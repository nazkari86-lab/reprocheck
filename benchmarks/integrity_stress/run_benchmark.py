from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from reprocheck.audit import run_audit
from reprocheck.certificate import digest_payload, verify_certificate_file
from reprocheck.signing import (
    generate_keypair,
    sign_certificate,
    verify_certificate_signature,
)
from reprocheck.version import __version__


PASSWORD = b"reprocheck-integrity-stress-password"
Mutation = Callable[[dict[str, Any]], None]


def run(output: Path | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="reprocheck-integrity-stress-") as directory:
        root = Path(directory)
        original = _base_certificate(root)
        certificate = root / "certificate.json"
        _write(certificate, original)
        private_key = root / "private.pem"
        public_key = root / "public.pem"
        signature = root / "signature.json"
        generate_keypair(private_key, public_key, PASSWORD)
        sign_certificate(certificate, private_key, signature, PASSWORD)

        cases = []
        for name, mutation, semantic_only in _mutations():
            raw = copy.deepcopy(original)
            mutation(raw["evidence_graph"])
            raw_errors, raw_signature_errors = _evaluate(root, raw, signature, public_key, "raw")

            outer_resealed = copy.deepcopy(raw)
            outer_resealed["certificate_sha256"] = digest_payload(outer_resealed)
            outer_errors, outer_signature_errors = _evaluate(
                root, outer_resealed, signature, public_key, "outer"
            )

            fully_rehashed = copy.deepcopy(raw)
            _rehash_graph(fully_rehashed["evidence_graph"])
            fully_rehashed["certificate_sha256"] = digest_payload(fully_rehashed)
            full_errors, full_signature_errors = _evaluate(
                root, fully_rehashed, signature, public_key, "full"
            )
            cases.append(
                {
                    "mutation": name,
                    "semantic_only": semantic_only,
                    "raw": {
                        "certificate_detected": bool(raw_errors),
                        "errors": raw_errors,
                        "signature_detected": bool(raw_signature_errors),
                    },
                    "outer_resealed": {
                        "graph_detected": bool(outer_errors),
                        "errors": outer_errors,
                        "signature_detected": bool(outer_signature_errors),
                    },
                    "fully_rehashed": {
                        "unsigned_detected": bool(full_errors),
                        "errors": full_errors,
                        "signature_detected": bool(full_signature_errors),
                    },
                }
            )

    result = {
        "schema": "reprocheck.integrity-stress-result.v1",
        "tool_version": __version__,
        "cases": cases,
        "summary": {
            "families": len(cases),
            "raw_certificate_detection_rate": _rate(
                cases, lambda case: case["raw"]["certificate_detected"]
            ),
            "outer_resealed_graph_detection_rate": _rate(
                cases, lambda case: case["outer_resealed"]["graph_detected"]
            ),
            "fully_rehashed_unsigned_detection_rate": _rate(
                cases, lambda case: case["fully_rehashed"]["unsigned_detected"]
            ),
            "fully_rehashed_semantic_unsigned_acceptance_rate": _rate(
                [case for case in cases if case["semantic_only"]],
                lambda case: not case["fully_rehashed"]["unsigned_detected"],
            ),
            "signature_detection_rate": _rate(
                cases, lambda case: case["fully_rehashed"]["signature_detected"]
            ),
        },
        "scientific_boundary": (
            "Controlled mechanism test. Unkeyed hashes preserve integrity only relative to a "
            "previously trusted digest; Ed25519 authenticates frozen certificate bytes relative "
            "to a trusted public key."
        ),
    }
    if output:
        _write(output, result)
    return result


def _base_certificate(root: Path) -> dict[str, Any]:
    report = root / "report.md"
    predictions = root / "predictions.csv"
    report.write_text("Accuracy: 100%\n", encoding="utf-8")
    predictions.write_text("y_true,y_pred\n0,0\n1,1\n", encoding="utf-8")
    return run_audit(report_path=report, predictions_path=predictions).to_dict()


def _mutations() -> list[tuple[str, Mutation, bool]]:
    return [
        ("node_label", lambda graph: _claim_node(graph).__setitem__("label", "accuracy=0"), True),
        (
            "node_attribute",
            lambda graph: _claim_node(graph)["attributes"].__setitem__("value", 0.0),
            True,
        ),
        (
            "edge_relation",
            lambda graph: _support_edge(graph).__setitem__("relation", "contradicts"),
            True,
        ),
        (
            "duplicate_node",
            lambda graph: graph["nodes"].append(copy.deepcopy(graph["nodes"][0])),
            False,
        ),
        (
            "duplicate_edge",
            lambda graph: graph["edges"].append(copy.deepcopy(graph["edges"][0])),
            False,
        ),
        (
            "unknown_endpoint",
            lambda graph: graph["edges"][0].__setitem__("target", "missing:0"),
            False,
        ),
        ("invalid_root_kind", lambda graph: graph.__setitem__("root_id", "artifact:0"), False),
        ("disconnected_node", _disconnect_claim, False),
        ("directed_cycle", _add_cycle, False),
    ]


def _claim_node(graph: dict[str, Any]) -> dict[str, Any]:
    return next(node for node in graph["nodes"] if node["kind"] == "claim")


def _support_edge(graph: dict[str, Any]) -> dict[str, Any]:
    return next(edge for edge in graph["edges"] if edge["relation"] == "supports")


def _disconnect_claim(graph: dict[str, Any]) -> None:
    claim_id = _claim_node(graph)["id"]
    graph["edges"] = [
        edge for edge in graph["edges"] if edge["source"] != claim_id and edge["target"] != claim_id
    ]


def _add_cycle(graph: dict[str, Any]) -> None:
    graph["edges"].append(
        {
            "source": "experiment:0",
            "target": "artifact:0",
            "relation": "flags",
            "digest_sha256": "0" * 64,
        }
    )


def _rehash_graph(graph: dict[str, Any]) -> None:
    for node in graph["nodes"]:
        canonical = {key: value for key, value in node.items() if key != "digest_sha256"}
        node["digest_sha256"] = _digest(canonical)
    for edge in graph["edges"]:
        canonical = {key: value for key, value in edge.items() if key != "digest_sha256"}
        edge["digest_sha256"] = _digest(canonical)
    canonical_graph = {key: value for key, value in graph.items() if key != "graph_sha256"}
    graph["graph_sha256"] = _digest(canonical_graph)


def _evaluate(
    root: Path,
    payload: dict[str, Any],
    signature: Path,
    public_key: Path,
    suffix: str,
) -> tuple[list[str], list[str]]:
    certificate = root / f"certificate-{suffix}.json"
    _write(certificate, payload)
    return (
        verify_certificate_file(certificate),
        verify_certificate_signature(certificate, signature, public_key),
    )


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rate(cases: list[dict[str, Any]], predicate: Callable[[dict[str, Any]], bool]) -> float:
    return sum(predicate(case) for case in cases) / len(cases) if cases else 1.0


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/integrity-stress.json"))
    args = parser.parse_args()
    benchmark = run(args.output)
    print(json.dumps(benchmark["summary"], sort_keys=True))
