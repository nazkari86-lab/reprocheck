import json

from reprocheck.witness_source_benchmark import (
    deterministic_projection,
    run_witness_source_benchmark,
    witness_source_benchmark_passed,
)


def test_source_benchmark_is_stratified_complete_and_reproducible(tmp_path):
    protocol = tmp_path / "protocol.json"
    source_protocol = "benchmarks/witness_source/protocol.json"
    protocol.write_text(open(source_protocol, encoding="utf-8").read(), encoding="utf-8")
    output = tmp_path / "result.json"

    result = run_witness_source_benchmark(protocol, output)

    assert witness_source_benchmark_passed(result)
    assert result["summary"]["case_count"] == 30
    assert result["summary"]["controlled_mutation_cases"] == 27
    assert result["summary"]["negative_control_cases"] == 3
    assert result["summary"]["natural_cases"] == 0
    assert set(result["summary"]["by_rule"]) == {
        "claim_metric_mismatch",
        "metric_evidence_conflict",
        "exact_split_overlap",
    }
    assert deterministic_projection(json.loads(output.read_text())) == deterministic_projection(
        result
    )


def test_source_benchmark_rejects_protocol_drift(tmp_path):
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps({"schema_version": "bad", "cases": []}),
        encoding="utf-8",
    )
    try:
        run_witness_source_benchmark(protocol)
    except ValueError as error:
        assert "protocol" in str(error)
    else:
        raise AssertionError("protocol drift must fail closed")
