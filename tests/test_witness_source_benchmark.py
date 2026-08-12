import json

import pytest

import reprocheck.witness_source_benchmark as source_benchmark
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


def test_source_benchmark_protocol_validation_rejects_all_structural_drift():
    with open("benchmarks/witness_source/protocol.json", encoding="utf-8") as handle:
        base = json.load(handle)

    def rejected(mutate, expected):
        payload = json.loads(json.dumps(base))
        mutate(payload)
        with pytest.raises(ValueError, match=expected):
            source_benchmark._validate_protocol(payload)

    rejected(lambda item: item.update(cases=[]), "exactly 30 cases")
    rejected(lambda item: item["cases"][1].update(id=item["cases"][0]["id"]), "ids")
    rejected(lambda item: item["cases"][0].update(evidence_stratum="other"), "27 mutations")
    rejected(lambda item: item["cases"][0].update(evidence_stratum="natural"), "cannot prelabel")


def test_source_benchmark_mutations_and_json_loading_fail_closed(tmp_path):
    with pytest.raises(ValueError, match="unsupported source benchmark mutation"):
        source_benchmark._mutate(
            tmp_path,
            {"rule": "unknown", "domain": "iris", "target": "accuracy", "variant": 1},
        )

    (tmp_path / "iris_report.md").write_text("no target here", encoding="utf-8")
    with pytest.raises(ValueError, match="did not resolve once"):
        source_benchmark._mutate_report(tmp_path, "iris", "accuracy", 1)

    (tmp_path / "official_metrics.json").write_text('{"iris": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="target is missing"):
        source_benchmark._mutate_metric_source(tmp_path, "iris", "accuracy", 1)

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be read"):
        source_benchmark._load_object(malformed, "payload")
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        source_benchmark._load_object(malformed, "payload")
