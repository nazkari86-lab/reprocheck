import json
from pathlib import Path

from reprocheck.ablation import (
    SYSTEMS,
    _exact_mcnemar,
    ablation_passed,
    run_evidence_ablation,
)
from reprocheck.cli import main


def test_evidence_ablation_is_deterministic_and_layered(tmp_path: Path):
    first = run_evidence_ablation(tmp_path / "first.json")
    second = run_evidence_ablation(tmp_path / "second.json")

    assert first == second
    assert first["case_counts"] == {
        "total": 19,
        "defects": 12,
        "negative_controls": 7,
        "families": 13,
    }
    sensitivities = [first["systems"][system]["sensitivity"] for system in SYSTEMS]
    assert sensitivities == [1 / 12, 3 / 12, 9 / 12, 1.0]
    assert all(first["systems"][system]["false_positives"] == 0 for system in SYSTEMS)
    assert first["systems"]["graph_certified_audit"]["family_coverage_rate"] == 1.0
    assert ablation_passed(first)


def test_evidence_ablation_preserves_scientific_boundary_and_pairing(tmp_path: Path):
    result = run_evidence_ablation(tmp_path / "ablation.json")

    assert "not an independent blind estimate" in result["design"]["scientific_boundary"]
    comparisons = result["pairwise_mcnemar"]
    assert comparisons[1]["second_only_correct"] == 6
    assert comparisons[1]["exact_two_sided_p"] == 0.03125
    assert comparisons[2]["second_only_correct"] == 3
    assert comparisons[2]["exact_two_sided_p"] == 0.25
    graph_cases = [case for case in result["cases"] if case["family"] == "graph_integrity"]
    assert len(graph_cases) == 3
    assert all(case["systems"]["graph_certified_audit"]["detected"] for case in graph_cases)
    assert all(not case["systems"]["artifact_aware_audit"]["detected"] for case in graph_cases)


def test_exact_mcnemar_handles_ties_and_direction():
    assert _exact_mcnemar(0, 0) == 1.0
    assert _exact_mcnemar(0, 6) == 0.03125
    assert _exact_mcnemar(6, 0) == 0.03125


def test_cli_runs_evidence_ablation(tmp_path: Path, capsys):
    output = tmp_path / "ablation.json"

    assert main(["ablation", "--output", str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["systems"]["graph_certified_audit"]["balanced_accuracy"] == 1.0
    stdout = capsys.readouterr().out
    assert "graph_certified_audit" in stdout
    assert "balanced_accuracy=100.0%" in stdout
