from reprocheck.witness_benchmark import run_witness_benchmark, witness_benchmark_passed


def test_witness_benchmark_is_compact_valid_and_fail_closed(tmp_path):
    output = tmp_path / "witness-benchmark.json"
    result = run_witness_benchmark(output, repeats=2)

    assert witness_benchmark_passed(result)
    assert result["summary"]["node_reduction"] > 0
    assert result["summary"]["serialized_byte_reduction"] > 0
    assert result["summary"]["one_hop_valid_cases"] == 0
    assert result["summary"]["tamper_rejection_rate"] == 1.0
    assert output.is_file()
