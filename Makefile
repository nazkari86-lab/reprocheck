SOURCE_DATE_EPOCH ?= 1704067200
UV_VERSION ?= 0.12.1
LOCKED_DEV_REQUIREMENTS ?= /tmp/reprocheck-dev-lock.txt
LOCKED_RUNTIME_REQUIREMENTS ?= /tmp/reprocheck-runtime-lock.txt

.PHONY: install lock-check dependency-audit runtime-sbom test lint type coverage benchmark evidence-ablation witness-benchmark witness-source-benchmark upstream-corrections upstream-discovery-v2 upstream-discovery-v2-registration external-holdout-registration human-study-master expanded-experiments near-duplicate-benchmark text-index-benchmark paws-study study challenge challenge-replay holdout holdout-replay holdout-development holdout-v07 holdout-v08-development external external-regenerate build gate demo rknp-demo serve

install:
	python3 -m pip install --quiet uv==$(UV_VERSION)
	uv export --quiet --locked --extra dev --no-emit-project --format requirements-txt --output-file $(LOCKED_DEV_REQUIREMENTS)
	python3 -m pip install --require-hashes -r $(LOCKED_DEV_REQUIREMENTS)
	python3 -m pip install --no-deps -e .

lock-check:
	uv lock --check

dependency-audit: lock-check
	uv export --quiet --locked --extra dev --no-emit-project --format requirements-txt --output-file $(LOCKED_DEV_REQUIREMENTS)
	uv run --locked --extra dev python -m pip_audit -r $(LOCKED_DEV_REQUIREMENTS) --progress-spinner off

runtime-sbom: lock-check
	uv export --quiet --locked --no-dev --no-emit-project --format requirements-txt --output-file $(LOCKED_RUNTIME_REQUIREMENTS)
	uv run --locked --extra dev python -m pip_audit -r $(LOCKED_RUNTIME_REQUIREMENTS) --format cyclonedx-json --output dist/reprocheck-sbom.cdx.json --progress-spinner off

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

evidence-ablation:
	python3 -m reprocheck.cli ablation --output outputs/evidence-ablation.json
	python3 benchmarks/evidence_ablation/check_baseline.py --result outputs/evidence-ablation.json

witness-benchmark:
	python3 -m reprocheck.cli witness-benchmark --output outputs/witness-benchmark.json

witness-source-benchmark:
	python3 -m reprocheck.cli witness-source-benchmark --protocol benchmarks/witness_source/protocol.json --output outputs/witness-source-benchmark.json
	python3 benchmarks/witness_source/check_baseline.py --result outputs/witness-source-benchmark.json

upstream-corrections:
	python3 benchmarks/upstream_corrections/verify_discovery.py
	python3 benchmarks/upstream_corrections/fetch_sources.py
	python3 benchmarks/upstream_corrections/run_benchmark.py --output outputs/upstream-corrections.json

upstream-discovery-v2-registration:
	python3 benchmarks/upstream_discovery_v2/verify_registration.py

upstream-discovery-v2: upstream-discovery-v2-registration
	python3 benchmarks/upstream_discovery_v2/evaluate.py --phase development_after_zero_shot --output benchmarks/upstream_discovery_v2/results/development-current.json
	python3 benchmarks/upstream_discovery_v2/verify_study.py

external-holdout-registration:
	python3 -m reprocheck.cli holdout-verify-registration --registration benchmarks/external_holdout_v017/registration.json --protocol benchmarks/external_holdout_v017/protocol.json --evaluator benchmarks/external_holdout_v017/evaluator/reprocheck-0.17.0-py3-none-any.whl

human-study-master:
	@if [ -f benchmarks/human_study_v1/master/private/PRIVATE-gold.json ]; then \
		python3 -m reprocheck.cli human-study-verify --master-dir benchmarks/human_study_v1/master --protocol benchmarks/human_study_v1/protocol.json; \
	else \
		python3 -m reprocheck.cli human-study-verify --public-lock-only --master-dir benchmarks/human_study_v1/master --protocol benchmarks/human_study_v1/protocol.json; \
	fi

expanded-experiments:
	python3 benchmarks/check_experiment_design_lock.py
	python3 benchmarks/integrity_stress/run_benchmark.py --output outputs/integrity-stress.json
	python3 benchmarks/representation_robustness/run_benchmark.py --output outputs/representation-robustness.json
	python3 benchmarks/real_corruptions/run_benchmark.py --output outputs/real-corruptions.json
	python3 benchmarks/scalability/run_benchmark.py --output outputs/scalability.json
	python3 benchmarks/check_expanded_results.py

near-duplicate-benchmark:
	python3 benchmarks/near_duplicate/run_benchmark.py --output outputs/near-duplicate-benchmark.json
	python3 benchmarks/near_duplicate/check_baseline.py --result outputs/near-duplicate-benchmark.json

text-index-benchmark:
	python3 benchmarks/text_index/run_benchmark.py --output outputs/text-index-benchmark.json
	python3 benchmarks/text_index/check_baseline.py --result outputs/text-index-benchmark.json

paws-study:
	python3 benchmarks/paws_leakage/verify_registration.py
	python3 benchmarks/paws_leakage/verify_locked_test.py

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

gate: lock-check lint type coverage benchmark evidence-ablation witness-benchmark witness-source-benchmark upstream-corrections upstream-discovery-v2 external-holdout-registration human-study-master expanded-experiments near-duplicate-benchmark text-index-benchmark paws-study study challenge challenge-replay holdout holdout-replay holdout-development holdout-v07 holdout-v08-development demo external build

demo:
	python3 -m reprocheck.cli demo

rknp-demo:
	python3 -m reprocheck.cli audit --report benchmarks/external/sklearn-tabular/iris_report.md --metrics benchmarks/external/sklearn-tabular/official_metrics.json --metrics-selector iris --predictions benchmarks/external/sklearn-tabular/iris_predictions.csv --average macro --train benchmarks/external/sklearn-tabular/iris_train.csv --test benchmarks/external/sklearn-tabular/iris_test.csv --label-column target --identity-columns sample_id --tolerance 1e-9 --output outputs/rknp-clean.json
	python3 -m reprocheck.cli verify --certificate outputs/rknp-clean.json --artifact-dir benchmarks/external/sklearn-tabular
	python3 -m reprocheck.cli demo --output-dir outputs/rknp-corrupted
	-python3 -m reprocheck.cli audit --report benchmarks/rknp_witness_demo/report.md --metrics benchmarks/rknp_witness_demo/metrics.json --metrics-selector iris --tolerance 1e-9 --output outputs/rknp-witness-certificate.json
	python3 -m reprocheck.cli witness --certificate outputs/rknp-witness-certificate.json --finding-index 0 --artifact-dir benchmarks/rknp_witness_demo --output outputs/rknp-witness.json
	python3 -m reprocheck.cli verify-witness --witness outputs/rknp-witness.json --certificate outputs/rknp-witness-certificate.json --artifact-dir benchmarks/rknp_witness_demo
	-python3 -m reprocheck.cli audit --report benchmarks/rknp_witness_demo/conflict_report.md --metrics benchmarks/rknp_witness_demo/conflict_metrics.json --predictions benchmarks/rknp_witness_demo/conflict_predictions.csv --tolerance 1e-9 --output outputs/rknp-conflict-certificate.json
	python3 -m reprocheck.cli witness --certificate outputs/rknp-conflict-certificate.json --finding-index 0 --artifact-dir benchmarks/rknp_witness_demo --output outputs/rknp-conflict-witness.json
	python3 -m reprocheck.cli verify-witness --witness outputs/rknp-conflict-witness.json --certificate outputs/rknp-conflict-certificate.json --artifact-dir benchmarks/rknp_witness_demo
	-python3 -m reprocheck.cli audit --report benchmarks/rknp_witness_demo/split_report.md --train benchmarks/rknp_witness_demo/split_train.csv --test benchmarks/rknp_witness_demo/split_test.csv --identity-columns id --output outputs/rknp-split-certificate.json
	python3 -m reprocheck.cli witness --certificate outputs/rknp-split-certificate.json --finding-index 0 --artifact-dir benchmarks/rknp_witness_demo --output outputs/rknp-split-witness.json
	python3 -m reprocheck.cli verify-witness --witness outputs/rknp-split-witness.json --certificate outputs/rknp-split-certificate.json --artifact-dir benchmarks/rknp_witness_demo
	python3 -m reprocheck.cli witness-benchmark --output outputs/rknp-witness-benchmark.json
	python3 -m reprocheck.cli witness-source-benchmark --protocol benchmarks/witness_source/protocol.json --output outputs/rknp-witness-source-benchmark.json
	python3 benchmarks/witness_source/check_baseline.py --result outputs/rknp-witness-source-benchmark.json
	python3 -m reprocheck.cli ablation --output outputs/rknp-ablation.json
	python3 benchmarks/evidence_ablation/check_baseline.py --result outputs/rknp-ablation.json

serve:
	python3 -m reprocheck.cli serve
