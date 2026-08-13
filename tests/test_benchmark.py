from reprocheck.benchmark import run_controlled_benchmark


def test_controlled_benchmark_is_fully_detected():
    result = run_controlled_benchmark()
    assert result["tool_version"] == "0.28.0"
    assert result["case_pass_rate"] == 1.0
    assert result["expected_finding_recall"] == 1.0
    assert result["expected_finding_precision"] == 1.0
    assert result["unexpected_findings"] == 0
    assert result["certificate_integrity_rate"] == 1.0
    assert result["certificate_tamper_detection_rate"] == 1.0
    assert result["invalid_input_rejection_rate"] == 1.0
    assert len(result["cases"]) == 12
    assert len(result["rejection_cases"]) == 3
