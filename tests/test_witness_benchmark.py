from reprocheck.witness_benchmark import run_witness_benchmark, witness_benchmark_passed


def test_witness_benchmark_is_compact_valid_and_fail_closed(tmp_path):
    output = tmp_path / "witness-benchmark.json"
    result = run_witness_benchmark(output, repeats=2)

    assert witness_benchmark_passed(result)
    assert result["summary"]["node_reduction"] > 0
    assert result["summary"]["serialized_byte_reduction"] > 0
    assert result["summary"]["case_count"] == 12
    assert result["summary"]["one_hop_topology_complete_cases"] == 4
    assert result["summary"]["artifact_semantic_recomputation_cases"] == 4
    assert result["summary"]["tamper_rejection_rate"] == 1.0
    assert set(result["summary"]["by_rule"]) == {
        "claim_metric_mismatch",
        "metric_evidence_conflict",
        "exact_split_overlap",
    }
    assert output.is_file()
