# Multi-Rule Minimal Witness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build independently verifiable canonical minimal witnesses for claim mismatch, metric-source conflict, and exact train/test overlap, then validate them on controlled and 30-case source-derived benchmarks.

**Architecture:** Keep certificate binding, canonicalization, digesting, and v1 compatibility in `witness.py`. Move rule-specific grounding and semantics into a focused `witness_rules.py` registry whose adapters enumerate complete candidate sets. Add a separate source-derived benchmark so controlled mutations, negative controls, and natural findings remain distinct strata.

**Tech Stack:** Python 3.11+, dataclasses, pathlib, csv/json/hashlib, pytest, Ruff, Pyright, Hatchling, existing ReproCheck audit/evidence-graph APIs.

---

## File map

- Create `src/reprocheck/witness_rules.py`: rule registry, candidate type, three grounding enumerators, artifact-dependent split recomputation, semantic validators.
- Modify `src/reprocheck/witness.py`: v2 orchestration, v1 verifier compatibility, artifact-dir propagation, shared canonical validation.
- Modify `src/reprocheck/cli.py`: `witness --artifact-dir` and source-derived benchmark command.
- Modify `src/reprocheck/witness_benchmark.py`: 12-case three-rule controlled benchmark and per-rule summaries.
- Create `src/reprocheck/witness_source_benchmark.py`: 30 source-derived cases with explicit evidence strata.
- Modify `tests/test_witness.py`: v2 rule and v1 compatibility tests.
- Modify `tests/test_witness_benchmark.py`: controlled benchmark expectations.
- Create `tests/test_witness_rules.py`: adapter-level enumeration, semantic and permutation tests.
- Create `tests/test_witness_source_benchmark.py`: 30-case benchmark and stratification tests.
- Modify `tests/test_cli_extensions.py`: CLI artifact-dir and benchmark paths.
- Create `benchmarks/witness_source/protocol.json`: frozen case matrix and evidence labels.
- Create `benchmarks/witness_source/check_baseline.py`: deterministic projection checker.
- Create `benchmarks/witness_source/baseline-v1.json`: reviewed deterministic projection.
- Modify `Makefile`: benchmark targets, gate and three-rule RKNP demo.
- Modify `README.md`, `docs/RELATED_WORK.md`, `docs/REPRODUCIBILITY.md`, `docs/RKNP_PROJECT_RU.md`, `docs/RKNP_DEFENSE_RU.md`, `docs/RELEASE_0.18.md`: scope and results.
- Modify `pyproject.toml`, `src/reprocheck/version.py`, `CITATION.cff`, `uv.lock`: version 0.18.0.

### Task 1: Freeze failing public-contract tests

**Files:**
- Modify: `tests/test_witness.py`
- Create: `tests/test_witness_rules.py`
- Modify: `tests/test_cli_extensions.py`

- [ ] **Step 1: Add a metric-conflict fixture and expected v2 contract**

```python
def test_metric_conflict_builds_canonical_five_node_witness(tmp_path):
    certificate = build_metric_conflict_certificate(tmp_path)
    witness = build_witness_file(certificate, 0, tmp_path / "witness.json", tmp_path)
    assert witness["schema_version"] == "reprocheck.witness.v2"
    assert witness["finding_code"] == "metric_evidence_conflict"
    assert witness["minimality"]["minimum_node_count"] == 5
    assert verify_witness_file(tmp_path / "witness.json", certificate, tmp_path) == []
```

- [ ] **Step 2: Add an exact-overlap fixture that requires source artifacts**

```python
def test_exact_overlap_recomputes_bound_row_fingerprints(tmp_path):
    certificate = build_exact_overlap_certificate(tmp_path)
    with pytest.raises(ValueError, match="artifact-dir"):
        build_witness_file(certificate, 0, tmp_path / "witness.json")
    witness = build_witness_file(certificate, 0, tmp_path / "witness.json", tmp_path)
    assert witness["rule_inputs"]["exact_overlap_test_rows"] == 1
    assert len(witness["rule_inputs"]["overlap_identity_sha256"]) == 1
```

- [ ] **Step 3: Add v1 compatibility and fail-closed tests**

Create a frozen v1 mismatch witness from the 0.17 shape and assert that the new verifier accepts it. Add rejection tests for unknown rule, missing artifact directory, changed CSV, changed rule inputs, permuted source/value pairing, duplicate source binding and non-finite values.

- [ ] **Step 4: Run the focused tests and confirm expected failures**

Run: `python3 -m pytest tests/test_witness.py tests/test_witness_rules.py tests/test_cli_extensions.py -q`

Expected: failures for missing v2 registry, new function signatures and unsupported finding codes.

### Task 2: Implement registry and three strict adapters

**Files:**
- Create: `src/reprocheck/witness_rules.py`
- Modify: `src/reprocheck/witness.py`
- Test: `tests/test_witness.py`
- Test: `tests/test_witness_rules.py`

- [ ] **Step 1: Define immutable rule context and candidate contracts**

```python
@dataclass(frozen=True)
class RuleContext:
    source: dict[str, Any]
    finding_index: int
    nodes: dict[str, dict[str, Any]]
    edges: tuple[dict[str, Any], ...]
    artifact_dir: Path | None

@dataclass(frozen=True)
class WitnessCandidate:
    node_ids: tuple[str, ...]
    edge_keys: tuple[tuple[str, str, str], ...]
    rule_inputs: dict[str, Any]
```

Define `WitnessRule` with `finding_code`, `verifier_rule`, `requires_artifacts`, `enumerate_candidates` and `semantic_errors`. Register exactly the three approved finding codes.

- [ ] **Step 2: Move mismatch grounding into its adapter**

Preserve the v1 numerical predicate and complete typed enumeration. The v2 adapter must emit the same five semantic nodes and four edges, with canonical `tolerance` and `observed` inputs.

- [ ] **Step 3: Implement metric-conflict enumeration**

Enumerate pairs of `metric -> finding: flags`, require the same metric name, bind each metric through `artifact -> metric: reports|recomputes`, compare `(source, value)` pairs to the finding payload without relying on list order, and reject differences within tolerance.

- [ ] **Step 4: Implement exact-overlap recomputation**

Read the bound train/test CSV files, resolve identity columns from `experiment:0.attributes.parameters.identity_columns`, compute exact fingerprints with the same ordered column/value encoding as leakage audit, and emit sorted SHA-256 hashes for overlapping test identities. Reject empty test data, missing columns, ambiguous artifact roles and zero overlap.

- [ ] **Step 5: Refactor v2 build and verify orchestration**

Change the public builder signature to:

```python
def build_witness_file(
    certificate: Path,
    finding_index: int,
    output: Path,
    artifact_dir: Path | None = None,
) -> dict[str, Any]:
```

Build v2 through the registry. Route v1 payloads to a retained `_validate_v1_witness_shape`; route v2 to registry semantics and rebuild the canonical candidate with the supplied artifact directory.

- [ ] **Step 6: Run focused tests**

Run: `python3 -m pytest tests/test_witness.py tests/test_witness_rules.py -q`

Expected: all rule, compatibility, permutation and tamper tests pass.

- [ ] **Step 7: Commit the rule engine**

```bash
git add src/reprocheck/witness.py src/reprocheck/witness_rules.py tests/test_witness.py tests/test_witness_rules.py
git commit -m "feat: add multi-rule minimal witnesses"
```

### Task 3: Extend CLI and controlled benchmark

**Files:**
- Modify: `src/reprocheck/cli.py`
- Modify: `src/reprocheck/witness_benchmark.py`
- Modify: `tests/test_cli_extensions.py`
- Modify: `tests/test_witness_benchmark.py`

- [ ] **Step 1: Add CLI artifact binding**

Add `--artifact-dir` to `witness` and pass it to `build_witness_file`. Keep it optional at argparse level so graph-only rules work; return exit code 2 with the adapter error for exact overlap without artifacts.

- [ ] **Step 2: Expand controlled cases to 12**

Create four deterministic variants per rule. Every case records rule, full graph size, one-hop size, witness size, candidate count, median verification time and four tamper results. Tamper rule inputs, node digest, edge relation and minimality independently.

- [ ] **Step 3: Make pass criteria rule-aware**

Require 12 cases, all canonical witnesses smaller than full graphs, all semantic checks valid and 48/48 tamper cases rejected. Do not require one-hop invalidity for split when its topology happens to equal the witness; instead report whether artifact-semantic verification adds information.

- [ ] **Step 4: Run CLI and controlled benchmark tests**

Run: `python3 -m pytest tests/test_cli_extensions.py tests/test_witness_benchmark.py -q`

Expected: all tests pass and `reprocheck witness-benchmark --repeats 2` reports 12 cases and 100% tamper rejection.

- [ ] **Step 5: Commit CLI and controlled benchmark**

```bash
git add src/reprocheck/cli.py src/reprocheck/witness_benchmark.py tests/test_cli_extensions.py tests/test_witness_benchmark.py
git commit -m "feat: benchmark three witness rules"
```

### Task 4: Build the 30-case source-derived benchmark

**Files:**
- Create: `src/reprocheck/witness_source_benchmark.py`
- Create: `tests/test_witness_source_benchmark.py`
- Create: `benchmarks/witness_source/protocol.json`
- Create: `benchmarks/witness_source/check_baseline.py`
- Create: `benchmarks/witness_source/baseline-v1.json`
- Modify: `src/reprocheck/cli.py`
- Modify: `Makefile`

- [ ] **Step 1: Freeze the case protocol**

Declare exactly 30 cases from Iris, Diabetes and YOLO frozen experiments: three untouched negative controls and 27 deterministic controlled mutations split across claim mismatch, metric conflict and exact split overlap. Label `evidence_stratum` explicitly; initialize `natural` count to zero unless an unchanged source truly yields a supported finding.

- [ ] **Step 2: Implement isolated case construction**

Copy verified source artifacts into a temporary directory, apply the protocol mutation, run the standard audit, locate the declared finding, build and independently verify its witness. Negative controls must produce no supported-rule finding.

- [ ] **Step 3: Compute honest outcomes**

Return case count, counts by stratum/rule/domain, build success, verification success, negative-control specificity, tamper rejection and per-rule compactness. Include `scientific_boundary` stating that 27 cases are mutations of three real deterministic experiments, not 27 natural defects or projects.

- [ ] **Step 4: Freeze a version-independent baseline projection**

The checker removes only `tool_version` and timing fields. It must compare case IDs, source hashes, expected/actual codes, witness node/edge counts, pass flags and aggregate outcomes byte-for-byte.

- [ ] **Step 5: Add CLI and Make targets**

Add `reprocheck witness-source-benchmark --protocol ... --output ...` and `make witness-source-benchmark`. Include the target in `make gate` before build.

- [ ] **Step 6: Run and freeze the benchmark**

Run: `python3 -m reprocheck.cli witness-source-benchmark --protocol benchmarks/witness_source/protocol.json --output outputs/witness-source-benchmark.json`

Expected: 30 cases, 27 controlled mutations, 3 negative controls, 100% expected witness construction/verification and no claim of natural-case evidence.

- [ ] **Step 7: Commit source-derived evidence**

```bash
git add src/reprocheck/witness_source_benchmark.py src/reprocheck/cli.py tests/test_witness_source_benchmark.py benchmarks/witness_source Makefile
git commit -m "test: add source-derived witness benchmark"
```

### Task 5: Update the RKNP demo and scientific documentation

**Files:**
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `docs/RELATED_WORK.md`
- Modify: `docs/REPRODUCIBILITY.md`
- Modify: `docs/RKNP_PROJECT_RU.md`
- Modify: `docs/RKNP_DEFENSE_RU.md`
- Create: `docs/RELEASE_0.18.md`

- [ ] **Step 1: Generate three demonstrator certificates**

Extend `make rknp-demo` to generate one certificate and canonical witness per rule, verify each against its artifacts, then run both witness benchmarks.

- [ ] **Step 2: Document the exact contribution**

State that ReproCheck implements three audit-specific canonical rules, not universal minimal provenance. Report controlled and source-derived strata separately and state `natural finding count = 0` if that remains the result.

- [ ] **Step 3: Add defense questions and limitations**

Cover why split requires reading CSV, why a graph-only shortcut is insufficient, why mutations are not natural errors, why v1 remains accepted, and what evidence would be required to claim reviewer-time savings.

- [ ] **Step 4: Run documentation command examples**

Run `make rknp-demo witness-source-benchmark` and verify every documented command succeeds with generated outputs.

- [ ] **Step 5: Commit docs and demo**

```bash
git add Makefile README.md docs benchmarks/rknp_witness_demo
git commit -m "docs: present three-rule RKNP evidence"
```

### Task 6: Release 0.18.0 and run final gates

**Files:**
- Modify: `src/reprocheck/version.py`
- Modify: `pyproject.toml`
- Modify: `CITATION.cff`
- Modify: `uv.lock`

- [ ] **Step 1: Bump version consistently**

Set package and citation version to `0.18.0`, date `2026-08-12`, then run `uv lock`.

- [ ] **Step 2: Run deterministic quality gate**

Run: `make gate`

Expected: Ruff format/check, Pyright, coverage threshold, all frozen old baselines, both witness benchmarks, external holdout lock, human-study lock, external experiments and deterministic package build pass.

- [ ] **Step 3: Check protected 0.17 artifacts**

Verify the registered holdout protocol, evaluator and registration still match their committed hashes. Verify `benchmarks/human_study_v1/master/private/` remains ignored and mode-restricted.

- [ ] **Step 4: Install final wheel in a new venv**

Install `dist/reprocheck-0.18.0-py3-none-any.whl`; run `--version`, both witness benchmarks, one witness build per rule and their independent verifiers.

- [ ] **Step 5: Audit repository state**

Run `git diff --check`, inspect `git status --short`, scan staged content for private keys/tokens and confirm no `outputs/`, `dist/` or private human-study files are staged.

- [ ] **Step 6: Commit release**

```bash
git add .gitignore CITATION.cff Makefile README.md SECURITY.md benchmarks docs pyproject.toml src tests uv.lock
git commit -m "release: prepare ReproCheck 0.18.0"
```

- [ ] **Step 7: Push after local verification**

Run `git fetch origin --prune`, confirm `main` can fast-forward, then `git push origin main`. Verify `git ls-remote origin refs/heads/main` equals local `HEAD`.
