from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import run_audit
from .batch import run_project_check
from .benchmark import run_controlled_benchmark
from .certificate import verify_certificate_file
from .evidence_graph import render_mermaid
from .render import render_html
from .study import run_real_artifact_study, study_passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reprocheck")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="audit a report and its evidence")
    audit.add_argument("--report", type=Path, required=True)
    audit.add_argument("--report-selector", help="dotted selector for a JSON report")
    audit.add_argument("--notebook", type=Path)
    audit.add_argument("--metrics", type=Path)
    audit.add_argument(
        "--metrics-selector",
        help="dotted JSON selector or column=value filter for a wide CSV",
    )
    audit.add_argument(
        "--detections",
        type=Path,
        help="JSON with images, ground_truth boxes, and prediction boxes",
    )
    audit.add_argument(
        "--artifact",
        action="append",
        default=[],
        type=_artifact_spec,
        metavar="ROLE=PATH",
        help="additional model, config, lockfile, or evidence artifact",
    )
    audit.add_argument("--predictions", type=Path)
    audit.add_argument("--train", type=Path)
    audit.add_argument("--test", type=Path)
    audit.add_argument("--label-column")
    audit.add_argument("--group-column")
    audit.add_argument("--identity-columns", help="comma-separated CSV columns")
    audit.add_argument("--text-column", help="column used for heuristic near-duplicate search")
    audit.add_argument("--near-threshold", type=float, default=0.8)
    audit.add_argument(
        "--near-method",
        choices=["hybrid_lexical_v1", "ordered_tokens_v1", "token_jaccard"],
        default="hybrid_lexical_v1",
    )
    audit.add_argument("--positive-label")
    audit.add_argument(
        "--prediction-task",
        choices=["classification", "regression"],
        default="classification",
    )
    audit.add_argument("--average", choices=["auto", "binary", "macro", "weighted"], default="auto")
    audit.add_argument("--tolerance", type=float, default=0.005)
    audit.add_argument("--output", type=Path, default=Path("outputs/audit.json"))
    audit.add_argument("--html", type=Path)

    check = subparsers.add_parser("check", help="audit all experiments in a project manifest")
    check.add_argument("manifest", type=Path, nargs="?", default=Path("reprocheck.json"))
    check.add_argument("--output-dir", type=Path, default=Path("outputs/reprocheck"))
    check.add_argument("--html", action="store_true", help="also render one HTML report per audit")

    demo = subparsers.add_parser("demo", help="run the bundled reproducibility example")
    demo.add_argument("--output-dir", type=Path, default=Path("outputs"))

    serve = subparsers.add_parser("serve", help="start the local web application")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    verify = subparsers.add_parser("verify", help="verify report and optional source checksums")
    verify.add_argument("--certificate", type=Path, required=True)
    verify.add_argument("--artifact-dir", type=Path)

    graph = subparsers.add_parser("graph", help="export a certificate evidence graph")
    graph.add_argument("--certificate", type=Path, required=True)
    graph.add_argument("--output", type=Path, default=Path("outputs/evidence-graph.mmd"))
    graph.add_argument("--format", choices=["mermaid", "json"], default="mermaid")

    keygen = subparsers.add_parser("keygen", help="generate an encrypted Ed25519 signing key")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)
    keygen.add_argument("--password-env", default="REPROCHECK_KEY_PASSWORD")

    sign = subparsers.add_parser("sign", help="create a detached Ed25519 certificate signature")
    sign.add_argument("--certificate", type=Path, required=True)
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--output", type=Path)
    sign.add_argument("--password-env", default="REPROCHECK_KEY_PASSWORD")

    verify_signature = subparsers.add_parser(
        "verify-signature", help="verify a signature against a trusted Ed25519 public key"
    )
    verify_signature.add_argument("--certificate", type=Path, required=True)
    verify_signature.add_argument("--signature", type=Path, required=True)
    verify_signature.add_argument("--public-key", type=Path, required=True)
    verify_signature.add_argument("--artifact-dir", type=Path)

    benchmark = subparsers.add_parser("benchmark", help="run controlled defect benchmark")
    benchmark.add_argument("--output", type=Path, default=Path("outputs/benchmark.json"))

    study = subparsers.add_parser("study", help="run the frozen real-artifact study")
    study.add_argument("--corpus", type=Path, default=Path("benchmarks/real_artifacts"))
    study.add_argument("--output", type=Path, default=Path("outputs/real-study.json"))
    study.add_argument("--repeats", type=int, default=3)
    study.add_argument("--bootstrap-samples", type=int, default=5_000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "keygen":
        from .signing import generate_keypair, password_from_environment

        try:
            fingerprint = generate_keypair(
                args.private_key,
                args.public_key,
                password_from_environment(args.password_env),
            )
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(f"private_key={args.private_key.resolve()}")
        print(f"public_key={args.public_key.resolve()}")
        print(f"public_key_fingerprint_sha256={fingerprint}")
        return 0
    if args.command == "sign":
        from .signing import password_from_environment, sign_certificate

        output = args.output or args.certificate.with_name(f"{args.certificate.name}.sig.json")
        try:
            payload = sign_certificate(
                args.certificate,
                args.private_key,
                output,
                password_from_environment(args.password_env),
            )
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(f"signature={output.resolve()}")
        print(f"public_key_fingerprint_sha256={payload['public_key']['fingerprint_sha256']}")
        return 0
    if args.command == "verify-signature":
        from .signing import verify_certificate_signature

        errors = verify_certificate_signature(
            args.certificate,
            args.signature,
            args.public_key,
            args.artifact_dir,
        )
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print("PASS: Ed25519 signature is valid and matches the trusted public key")
        return 0
    if args.command == "serve":
        import uvicorn

        uvicorn.run("reprocheck.web:app", host=args.host, port=args.port, reload=False)
        return 0
    if args.command == "verify":
        errors = verify_certificate_file(args.certificate, args.artifact_dir)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print("PASS: certificate schema, checksum, and supplied artifacts match")
        return 0
    if args.command == "graph":
        errors = verify_certificate_file(args.certificate)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        try:
            payload = json.loads(args.certificate.read_text(encoding="utf-8"))
            graph_payload = payload.get("evidence_graph")
            if not isinstance(graph_payload, dict):
                raise ValueError("certificate does not contain an evidence graph")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        args.output.parent.mkdir(parents=True, exist_ok=True)
        content = (
            render_mermaid(graph_payload)
            if args.format == "mermaid"
            else json.dumps(graph_payload, ensure_ascii=False, indent=2) + "\n"
        )
        args.output.write_text(content, encoding="utf-8")
        print(
            f"nodes={len(graph_payload['nodes'])} edges={len(graph_payload['edges'])} "
            f"output={args.output.resolve()}"
        )
        return 0
    if args.command == "benchmark":
        result = run_controlled_benchmark(args.output)
        print(
            f"cases={len(result['cases'])} pass_rate={result['case_pass_rate']:.1%} "
            f"finding_recall={result['expected_finding_recall']:.1%} "
            f"finding_precision={result['expected_finding_precision']:.1%} "
            f"input_rejection={result['invalid_input_rejection_rate']:.1%} "
            f"tamper_detection={result['certificate_tamper_detection_rate']:.1%} "
            f"unexpected={result['unexpected_findings']}"
        )
        print(f"output={args.output.resolve()}")
        passed = (
            result["case_pass_rate"] == 1.0
            and result["expected_finding_recall"] == 1.0
            and result["expected_finding_precision"] == 1.0
            and result["invalid_input_rejection_rate"] == 1.0
            and result["certificate_integrity_rate"] == 1.0
            and result["certificate_tamper_detection_rate"] == 1.0
            and result["unexpected_findings"] == 0
        )
        return 0 if passed else 1
    if args.command == "study":
        try:
            result = run_real_artifact_study(
                args.corpus,
                args.output,
                repeats=args.repeats,
                bootstrap_samples=args.bootstrap_samples,
            )
        except (OSError, UnicodeDecodeError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(
            f"artifacts={result['corpus']['artifacts']} "
            f"claims={result['corpus']['annotated_claims']} "
            f"precision={result['reprocheck']['precision']:.1%} "
            f"recall={result['reprocheck']['recall']:.1%} "
            f"baseline_recall={result['naive_inline_baseline']['recall']:.1%} "
            f"format_baseline_recall={result['format_aware_baseline']['recall']:.1%} "
            f"defect_detection="
            f"{result['mutation_detection']['reprocheck']['defect_detection_rate']:.1%} "
            f"controls={result['mutation_detection']['reprocheck']['negative_control_correct_rate']:.1%}"
        )
        print(f"output={args.output.resolve()}")
        return 0 if study_passed(result) else 1
    if args.command == "check":
        try:
            result = run_project_check(args.manifest, args.output_dir, html=args.html)
        except (OSError, UnicodeDecodeError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        print(
            f"status={result['status']} experiments={len(result['experiments'])} "
            f"output={(args.output_dir / 'batch-certificate.json').resolve()}"
        )
        for experiment in result["experiments"]:
            print(
                f"{experiment['id']}: status={experiment['status']} "
                f"findings={experiment['findings']} certificate={experiment['certificate']}"
            )
        return 1 if result["status"] == "needs_review" else 0
    if args.command == "demo":
        root = Path(__file__).parent / "demo_data"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report = run_audit(
            report_path=root / "report.md",
            predictions_path=root / "predictions.csv",
            train_path=root / "train.csv",
            test_path=root / "test.csv",
            label_column="label",
            group_column="source_id",
            identity_columns=["text"],
        )
        json_path = args.output_dir / "demo-audit.json"
        html_path = args.output_dir / "demo-audit.html"
        _write_outputs(report, json_path, html_path)
        print(f"status={report.status} findings={len(report.findings)}")
        print(f"json={json_path.resolve()}")
        print(f"html={html_path.resolve()}")
        return 0

    identity_columns = (
        [value.strip() for value in args.identity_columns.split(",") if value.strip()]
        if args.identity_columns
        else None
    )
    try:
        report = run_audit(
            report_path=args.report,
            report_selector=args.report_selector,
            notebook_path=args.notebook,
            metrics_path=args.metrics,
            metrics_selector=args.metrics_selector,
            detections_path=args.detections,
            predictions_path=args.predictions,
            train_path=args.train,
            test_path=args.test,
            label_column=args.label_column,
            group_column=args.group_column,
            identity_columns=identity_columns,
            text_column=args.text_column,
            near_threshold=args.near_threshold,
            near_method=args.near_method,
            positive_label=args.positive_label,
            average=args.average,
            prediction_task=args.prediction_task,
            tolerance=args.tolerance,
            extra_artifacts=args.artifact,
        )
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    _write_outputs(report, args.output, args.html)
    print(f"status={report.status} findings={len(report.findings)} output={args.output}")
    return 1 if report.status == "needs_review" else 0


def _write_outputs(report, json_path: Path, html_path: Path | None) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if html_path:
        html_path.parent.mkdir(parents=True, exist_ok=True)
        render_html(report, html_path)


def _artifact_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("artifact must use ROLE=PATH")
    role, raw_path = (part.strip() for part in value.split("=", 1))
    if not role or not raw_path:
        raise argparse.ArgumentTypeError("artifact must use non-empty ROLE=PATH")
    return role, Path(raw_path)


if __name__ == "__main__":
    raise SystemExit(main())
