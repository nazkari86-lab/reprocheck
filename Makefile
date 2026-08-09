SOURCE_DATE_EPOCH ?= 1704067200

.PHONY: install test lint type coverage benchmark study challenge challenge-replay holdout holdout-replay holdout-development holdout-v07 holdout-v08-development external external-regenerate build gate demo serve

install:
	python3 -m pip install -c requirements-ci.txt -e '.[dev]'

test:
	python3 -m pytest

lint:
	python3 -m ruff format --check .
	python3 -m ruff check .

type:
	python3 -m pyright src tests

coverage:
	python3 -m pytest --cov=src/reprocheck --cov-report=term-missing --cov-fail-under=97

benchmark:
	python3 -m reprocheck.cli benchmark --output outputs/benchmark.json
	python3 benchmarks/check_controlled_baseline.py --result outputs/benchmark.json

study:
	python3 benchmarks/real_artifacts/fetch_sources.py
	python3 benchmarks/real_artifacts/build_annotations.py
	python3 -m reprocheck.cli study --corpus benchmarks/real_artifacts --output outputs/real-study.json --repeats 3 --bootstrap-samples 5000
	python3 benchmarks/real_artifacts/check_baseline.py --result outputs/real-study.json

challenge:
	python3 benchmarks/challenge_artifacts/fetch_sources.py
	python3 benchmarks/challenge_artifacts/build_annotations.py
	python3 benchmarks/challenge_artifacts/check_results.py

challenge-replay:
	python3 benchmarks/challenge_artifacts/replay_wheel.py --wheel benchmarks/challenge_artifacts/evaluator/reprocheck-0.5.0-py3-none-any.whl --expected-result benchmarks/challenge_artifacts/results/frozen-replay-v0.5.json --phase frozen_evaluator_replay --system-site-packages
	python3 benchmarks/challenge_artifacts/replay_wheel.py --wheel benchmarks/challenge_artifacts/evaluator/reprocheck-0.6.0-py3-none-any.whl --expected-result benchmarks/challenge_artifacts/results/development-v0.6.json --phase development_after_challenge_inspection

holdout:
	python3 benchmarks/holdout_artifacts/fetch_sources.py
	python3 benchmarks/holdout_artifacts/build_annotations.py
	python3 benchmarks/holdout_artifacts/check_annotations.py
	python3 benchmarks/holdout_artifacts/check_result.py

holdout-replay:
	python3 benchmarks/holdout_artifacts/replay_zero_shot.py

holdout-development:
	python3 benchmarks/holdout_artifacts/build_posthoc_annotations_v07.py
	python3 benchmarks/holdout_artifacts/check_development_v07.py
	python3 benchmarks/holdout_artifacts/replay_development_v07.py

holdout-v07:
	python3 benchmarks/holdout_v07_artifacts/fetch_sources.py
	python3 benchmarks/holdout_v07_artifacts/build_annotations.py
	python3 benchmarks/holdout_v07_artifacts/check_result.py
	python3 benchmarks/holdout_v07_artifacts/replay_zero_shot.py

holdout-v08-development:
	python3 benchmarks/holdout_v07_artifacts/check_development_v08.py
	python3 benchmarks/holdout_v07_artifacts/replay_development_v08.py

external:
	python3 -m reprocheck.cli audit --report benchmarks/external/yolo26n-coco8/report.md --metrics benchmarks/external/yolo26n-coco8/official_metrics_flat.json --detections benchmarks/external/yolo26n-coco8/coco8_detections.json --tolerance 0.001 --output outputs/yolo26n-coco8-audit.json
	python3 -m reprocheck.cli verify --certificate outputs/yolo26n-coco8-audit.json --artifact-dir benchmarks/external/yolo26n-coco8
	python3 -m reprocheck.cli audit --report benchmarks/external/sklearn-tabular/iris_report.md --metrics benchmarks/external/sklearn-tabular/official_metrics.json --metrics-selector iris --predictions benchmarks/external/sklearn-tabular/iris_predictions.csv --average macro --train benchmarks/external/sklearn-tabular/iris_train.csv --test benchmarks/external/sklearn-tabular/iris_test.csv --label-column target --identity-columns sample_id --tolerance 1e-9 --output outputs/iris-audit.json
	python3 -m reprocheck.cli verify --certificate outputs/iris-audit.json --artifact-dir benchmarks/external/sklearn-tabular
	python3 -m reprocheck.cli audit --report benchmarks/external/sklearn-tabular/diabetes_report.md --metrics benchmarks/external/sklearn-tabular/official_metrics.json --metrics-selector diabetes --predictions benchmarks/external/sklearn-tabular/diabetes_predictions.csv --prediction-task regression --train benchmarks/external/sklearn-tabular/diabetes_train.csv --test benchmarks/external/sklearn-tabular/diabetes_test.csv --label-column target --identity-columns sample_id --tolerance 1e-9 --output outputs/diabetes-audit.json
	python3 -m reprocheck.cli verify --certificate outputs/diabetes-audit.json --artifact-dir benchmarks/external/sklearn-tabular

external-regenerate:
	python3 benchmarks/external/sklearn-tabular/generate.py
	python3 -m pytest tests/test_external_benchmark.py

build:
	SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH) python3 -m build

gate: lint type coverage benchmark study challenge challenge-replay holdout holdout-replay holdout-development holdout-v07 holdout-v08-development demo external build

demo:
	python3 -m reprocheck.cli demo

serve:
	python3 -m reprocheck.cli serve
