# ReproCheck Evidence Trial v19 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fail-closed, preregistered v19 trial pipeline that compares report-only, supplied-metric, and raw-recomputation verdicts on the same blinded claims without altering the preserved v18 attempt.

**Architecture:** Add one focused `evidence_trial` domain module for protocol locks, sample gates, review locks, tri-state scoring, clustered inference, and certificate-track summaries. Expose thin CLI commands, keep network acquisition in a benchmark-local script, and freeze the actual evaluator/acquisition/analysis artifacts only after all local code and tests pass.

**Tech Stack:** Python 3.11+, argparse, jsonschema, standard-library hashing/statistics/random, existing ReproCheck audit/witness APIs, pytest, Ruff, Pyright, Hatch/build, Make.

---

## File structure

- Create `src/reprocheck/evidence_trial.py`: pure trial contracts, hashing, sample gates, review/adjudication locks, scoring, bootstrap, McNemar, and result validation.
- Create `src/reprocheck/schemas/evidence-trial-protocol-v1.schema.json`: preregistration contract.
- Create `src/reprocheck/schemas/evidence-trial-sample-v1.schema.json`: immutable candidate/claim manifest contract.
- Create `src/reprocheck/schemas/evidence-trial-review-v1.schema.json`: label-hidden response and adjudicated gold contract.
- Create `src/reprocheck/schemas/evidence-trial-result-v1.schema.json`: frozen scored-result contract.
- Create `tests/test_evidence_trial.py`: unit, property, integration, statistics, and fail-closed tests.
- Modify `src/reprocheck/cli.py`: add thin `trial-*` command handlers.
- Modify `tests/test_cli_extensions.py`: CLI contract tests.
- Create `benchmarks/evidence_trial_v19/protocol.md`: human-readable frozen scientific protocol.
- Create `benchmarks/evidence_trial_v19/protocol.json`: machine-readable protocol.
- Create `benchmarks/evidence_trial_v19/exclusions.json`: permanent owner/file exclusion registry.
- Create `benchmarks/evidence_trial_v19/acquire.py`: deterministic metadata acquisition with byte/time caps and resume.
- Create `benchmarks/evidence_trial_v19/analyze.py`: frozen wrapper around the pure scorer.
- Create `benchmarks/evidence_trial_v19/verify_registration.py`: repository-local registration gate.
- Create `benchmarks/evidence_trial_v19/README.md`: operator workflow and scientific boundaries.
- Modify `Makefile`: add local v19 validation and scored-replay targets without adding network retrieval to `make gate`.
- Modify `README.md`, `docs/SCIENTIFIC_PROTOCOL.md`, and `docs/SCIENTIFIC_SCORECARD.md`: expose only implemented or observed claims.

The existing untracked `benchmarks/cross_project_holdout_v18/frames.json`, `raw/`, and `sample.json` are never staged, rewritten, moved, or imported into v19.

### Task 1: Trial protocol and canonical integrity contracts

**Files:**
- Create: `src/reprocheck/evidence_trial.py`
- Create: `src/reprocheck/schemas/evidence-trial-protocol-v1.schema.json`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write failing protocol-validation tests**

```python
def test_trial_protocol_accepts_complete_contract(tmp_path: Path):
    protocol = _write_protocol(tmp_path / "protocol.json")
    loaded = load_trial_protocol(protocol)
    assert loaded["schema_version"] == "reprocheck.evidence-trial-protocol.v1"
    assert loaded["minimum_information"]["repository_owners"] == 20


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda p: p.pop("hypotheses"), "missing required property"),
        (lambda p: p["minimum_information"].update(contradicted_claims=0), "minimum"),
        (lambda p: p.update(title="UNRESOLVED"), "placeholder"),
        (lambda p: p["arms"].remove("raw_recomputation"), "raw_recomputation"),
    ],
)
def test_trial_protocol_rejects_incomplete_contract(tmp_path: Path, mutation, message: str):
    payload = _protocol_payload()
    mutation(payload)
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_trial_protocol(path)
```

- [ ] **Step 2: Run the tests and confirm they fail because the module is absent**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'reprocheck.evidence_trial'`.

- [ ] **Step 3: Implement canonical JSON, descriptors, and schema-backed protocol loading**

```python
PROTOCOL_SCHEMA = "reprocheck.evidence-trial-protocol.v1"


def canonical_digest(payload: dict[str, Any], *, blank_field: str | None = None) -> str:
    value = copy.deepcopy(payload)
    if blank_field is not None:
        value[blank_field] = ""
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_descriptor(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"filename": path.name, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}


def load_trial_protocol(path: Path) -> dict[str, Any]:
    payload = _load_json_object(path, "trial protocol")
    _validate_schema(payload, "evidence-trial-protocol-v1.schema.json", "trial protocol")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).upper()
    if any(marker in encoded for marker in ("UNRESOLVED", "TO" + "DO", "FIX" + "ME")):
        raise ValueError("trial protocol contains an unresolved placeholder")
    if payload["arms"] != ["report_only", "supplied_metrics", "raw_recomputation"]:
        raise ValueError("trial arms must end with raw_recomputation in frozen order")
    return payload
```

The JSON schema must require the exact sections from the design: `title`, `research_question`, `hypotheses`, `arms`, `minimum_information`, `source_frame`, `annotation`, `primary_outcomes`, `secondary_outcomes`, `analysis`, `success_gate`, and `scientific_boundary`. It must set `additionalProperties: false` at the root and enforce positive integer sample thresholds.

- [ ] **Step 4: Run focused tests**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/reprocheck/evidence_trial.py src/reprocheck/schemas/evidence-trial-protocol-v1.schema.json tests/test_evidence_trial.py
git commit -m "feat: add evidence trial protocol contracts"
```

### Task 2: Immutable multi-artifact registration

**Files:**
- Modify: `src/reprocheck/evidence_trial.py`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write failing registration tests**

```python
def test_trial_registration_binds_every_executable_input(tmp_path: Path):
    protocol = _write_protocol(tmp_path / "protocol.json")
    files = _write_registration_inputs(tmp_path)
    output = tmp_path / "registration.json"
    registration = register_evidence_trial(protocol=protocol, output=output, **files)
    assert registration["status"] == "registered_not_retrieved"
    assert set(registration["artifacts"]) == {"evaluator", "acquisition", "source_config", "analysis", "exclusions"}
    assert verify_evidence_trial_registration(output, protocol=protocol, **files) == []


def test_trial_registration_rejects_overwrite_and_tamper(tmp_path: Path):
    protocol = _write_protocol(tmp_path / "protocol.json")
    files = _write_registration_inputs(tmp_path)
    output = tmp_path / "registration.json"
    register_evidence_trial(protocol=protocol, output=output, **files)
    with pytest.raises(ValueError, match="immutable"):
        register_evidence_trial(protocol=protocol, output=output, **files)
    files["analysis"].write_text("changed", encoding="utf-8")
    assert "analysis checksum or size does not match" in verify_evidence_trial_registration(
        output, protocol=protocol, **files
    )
```

- [ ] **Step 2: Confirm red state**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: FAIL because `register_evidence_trial` is undefined.

- [ ] **Step 3: Implement registration and independent verification**

```python
REGISTRATION_SCHEMA = "reprocheck.evidence-trial-registration.v1"


def register_evidence_trial(*, protocol: Path, evaluator: Path, acquisition: Path,
                            source_config: Path, analysis: Path, exclusions: Path,
                            output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("trial registration output already exists; registrations are immutable")
    load_trial_protocol(protocol)
    artifacts = {
        name: file_descriptor(path)
        for name, path in {
            "evaluator": evaluator,
            "acquisition": acquisition,
            "source_config": source_config,
            "analysis": analysis,
            "exclusions": exclusions,
        }.items()
    }
    payload = {
        "schema_version": REGISTRATION_SCHEMA,
        "status": "registered_not_retrieved",
        "protocol": file_descriptor(protocol),
        "artifacts": artifacts,
        "source_contents_inspected_after_registration": False,
        "registration_sha256": "",
    }
    payload["registration_sha256"] = canonical_digest(payload, blank_field="registration_sha256")
    _write_json_exclusive(output, payload)
    return payload
```

`verify_evidence_trial_registration` must reload the protocol, recompute every descriptor and registration digest, accumulate all errors, and never update the registration.

- [ ] **Step 4: Run focused tests and legacy registration tests**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py tests/test_holdout_registration.py -q`

Expected: PASS; existing holdout registration remains unchanged.

- [ ] **Step 5: Commit**

```bash
git add src/reprocheck/evidence_trial.py tests/test_evidence_trial.py
git commit -m "feat: lock evidence trial executables"
```

### Task 3: Candidate manifests, exclusion enforcement, and information gate

**Files:**
- Modify: `src/reprocheck/evidence_trial.py`
- Create: `src/reprocheck/schemas/evidence-trial-sample-v1.schema.json`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write failing sample-gate tests**

```python
def test_sample_gate_counts_natural_strata_by_owner(tmp_path: Path):
    protocol = _write_protocol(tmp_path / "protocol.json", minimum_information={
        "repository_owners": 2,
        "claims": 5,
        "contradicted_claims": 1,
        "not_verifiable_claims": 1,
        "supported_evidence_claims": 1,
    })
    sample = _write_sample(tmp_path / "sample.json", _five_claim_sample())
    status = validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})
    assert status["status"] == "eligible"
    assert status["counts"]["repository_owners"] == 2


def test_sample_gate_fails_closed_on_seen_owner_and_shortfall(tmp_path: Path):
    protocol = _write_protocol(tmp_path / "protocol.json")
    sample = _write_sample(tmp_path / "sample.json", _five_claim_sample())
    with pytest.raises(ValueError, match="excluded owner"):
        validate_trial_sample(sample, protocol, exclusions={"owners": ["owner-a"], "files": []})
    result = validate_trial_sample(sample, protocol, exclusions={"owners": [], "files": []})
    assert result["status"] == "insufficient_sample"
    assert "repository_owners" in result["shortfalls"]
```

- [ ] **Step 2: Confirm red state**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: FAIL because sample validation is undefined.

- [ ] **Step 3: Implement schema validation, owner/file uniqueness, and gate accounting**

```python
NATURAL_STRATA = {
    "natural_correction",
    "natural_supported_control",
    "natural_not_verifiable",
    "unchanged_negative_control",
}


def validate_trial_sample(sample_path: Path, protocol_path: Path,
                          *, exclusions: dict[str, list[str]]) -> dict[str, Any]:
    sample = _load_json_object(sample_path, "trial sample")
    protocol = load_trial_protocol(protocol_path)
    _validate_schema(sample, "evidence-trial-sample-v1.schema.json", "trial sample")
    claims = sample["claims"]
    owners = {claim["owner"] for claim in claims if claim["stratum"] in NATURAL_STRATA}
    if owners & set(exclusions["owners"]):
        raise ValueError("trial sample contains an excluded owner")
    paths = {f"{claim['owner']}:{claim['repository']}:{claim['path']}" for claim in claims}
    if paths & set(exclusions["files"]):
        raise ValueError("trial sample contains an excluded file")
    counts = _trial_counts(claims)
    required = protocol["minimum_information"]
    shortfalls = {name: {"required": value, "observed": counts[name]}
                  for name, value in required.items() if counts[name] < value}
    return {"status": "insufficient_sample" if shortfalls else "eligible",
            "counts": counts, "shortfalls": shortfalls}
```

The sample schema must require immutable URL, lowercase 40-character commit, SHA-256, block coordinates, unique claim ID, owner, repository, path, stratum, and declared evidence tier. `controlled_mutation` claims remain present but are excluded from all natural counts.

- [ ] **Step 4: Run focused tests**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/reprocheck/evidence_trial.py src/reprocheck/schemas/evidence-trial-sample-v1.schema.json tests/test_evidence_trial.py
git commit -m "feat: enforce evidence trial sample gates"
```

### Task 4: Label-hidden review packets and adjudicated gold lock

**Files:**
- Modify: `src/reprocheck/evidence_trial.py`
- Create: `src/reprocheck/schemas/evidence-trial-review-v1.schema.json`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write failing blinding and adjudication tests**

```python
def test_trial_review_packet_hides_gold(tmp_path: Path):
    sample = _write_sample(tmp_path / "sample.json", _five_claim_sample(with_gold=True))
    output = tmp_path / "review"
    manifest = prepare_trial_review(sample, output)
    packet = json.loads((output / "public/packet.json").read_text())
    assert all("gold_status" not in item for item in packet["claims"])
    assert manifest["reviewers_completed"] == 0


def test_gold_lock_requires_two_reviews_and_complete_adjudication(tmp_path: Path):
    review_dir = _prepared_review_dir(tmp_path)
    first, second = _write_distinct_reviews(review_dir, disagree=True)
    with pytest.raises(ValueError, match="adjudication"):
        lock_trial_gold(review_dir, [first, second], None, review_dir / "gold-lock.json")
    adjudication = _write_adjudication(review_dir)
    locked = lock_trial_gold(
        review_dir, [first, second], adjudication, review_dir / "gold-lock.json"
    )
    assert locked["reviewer_count"] == 2
    assert locked["adjudication_complete"] is True
```

- [ ] **Step 2: Confirm red state**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: FAIL because trial review functions are undefined.

- [ ] **Step 3: Implement public/private packet separation and immutable gold locking**

```python
def prepare_trial_review(sample_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("trial review output directory must be empty")
    sample = _load_json_object(sample_path, "trial sample")
    claims = sample["claims"]
    public_claims = [{key: value for key, value in claim.items()
                      if key not in {"gold_status", "gold_metric", "gold_value", "gold_rationale"}}
                     for claim in claims]
    private_claims = [{key: value for key, value in claim.items()
                       if key in {"claim_id", "gold_status", "gold_metric", "gold_value", "gold_rationale"}}
                      for claim in claims]
    packet = {"schema_version": "reprocheck.evidence-trial-review-packet.v1",
              "blind": True, "claims": public_claims}
    internal = {"schema_version": "reprocheck.evidence-trial-internal-gold.v1",
                "sample_sha256": file_descriptor(sample_path)["sha256"], "claims": private_claims}
    _write_json(output_dir / "public/packet.json", packet)
    _write_json(output_dir / "private/PRIVATE-internal-gold.json", internal)
    manifest = {"schema_version": "reprocheck.evidence-trial-review-manifest.v1",
                "reviewers_completed": 0, "adjudication_complete": False,
                "packet": file_descriptor(output_dir / "public/packet.json"),
                "internal_gold": file_descriptor(output_dir / "private/PRIVATE-internal-gold.json")}
    _write_json(output_dir / "manifest.json", manifest)
    return manifest
```

`lock_trial_gold` must require exactly two distinct reviewer IDs, explicit independence confirmations, all claim IDs exactly once, valid tri-state labels, and an adjudication row for every disagreement. It writes with exclusive creation and binds reviewer files, adjudication, sample, and final gold payload by SHA-256.

The lock payload also records raw agreement and Cohen's kappa over the three
statuses. Kappa is computed from the full `3 x 3` reviewer confusion matrix;
when expected agreement is exactly one, the value is `null` rather than an
invented perfect score.

- [ ] **Step 4: Run focused and legacy external-review tests**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py tests/test_external_review.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/reprocheck/evidence_trial.py src/reprocheck/schemas/evidence-trial-review-v1.schema.json tests/test_evidence_trial.py
git commit -m "feat: add blinded trial adjudication locks"
```

### Task 5: Tri-state arm scoring and clustered statistical inference

**Files:**
- Modify: `src/reprocheck/evidence_trial.py`
- Create: `src/reprocheck/schemas/evidence-trial-result-v1.schema.json`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write failing metric and success-gate tests**

```python
def test_trial_score_separates_arms_and_natural_strata(tmp_path: Path):
    gold, arms, protocol, registration = _scoring_fixture(tmp_path)
    result = score_evidence_trial(
        gold_path=gold,
        arm_paths=arms,
        protocol_path=protocol,
        registration_path=registration,
        output=tmp_path / "result.json",
        bootstrap_samples=200,
    )
    assert result["arms"]["raw_recomputation"]["contradiction_recall"] == 1.0
    assert result["arms"]["report_only"]["contradiction_recall"] == 0.0
    assert result["controlled_mutation"]["claims"] > 0
    assert result["primary_analysis"]["h1_status"] == "supported"


def test_trial_score_marks_short_sample_and_false_accusation_as_not_supported(tmp_path: Path):
    gold, arms, protocol, registration = _scoring_fixture(tmp_path, insufficient=True)
    result = score_evidence_trial(
        gold_path=gold, arm_paths=arms, protocol_path=protocol,
        registration_path=registration, bootstrap_samples=20
    )
    assert result["primary_analysis"]["h1_status"] == "not_supported"
    assert "minimum_information" in result["primary_analysis"]["failed_gates"]
```

- [ ] **Step 2: Confirm red state**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: FAIL because scoring is undefined.

- [ ] **Step 3: Implement per-arm confusion matrices and metrics**

```python
TRIAL_STATUSES = ("supported", "contradicted", "not_verifiable")


def _score_arm(gold: dict[str, dict[str, Any]], predictions: dict[str, str]) -> dict[str, Any]:
    matrix = {actual: {predicted: 0 for predicted in TRIAL_STATUSES} for actual in TRIAL_STATUSES}
    for claim_id, item in gold.items():
        matrix[item["gold_status"]][predictions[claim_id]] += 1
    per_class = {}
    for status in TRIAL_STATUSES:
        tp = matrix[status][status]
        fp = sum(matrix[actual][status] for actual in TRIAL_STATUSES if actual != status)
        fn = sum(matrix[status][predicted] for predicted in TRIAL_STATUSES if predicted != status)
        precision = tp / (tp + fp) if tp + fp else 1.0
        recall = tp / (tp + fn) if tp + fn else 1.0
        per_class[status] = {"precision": precision, "recall": recall,
                             "f1": 2 * precision * recall / (precision + recall)
                             if precision + recall else 0.0}
    false_accusations = sum(matrix[actual]["contradicted"]
                            for actual in ("supported", "not_verifiable"))
    non_contradictions = sum(sum(matrix[actual].values())
                             for actual in ("supported", "not_verifiable"))
    return {"confusion_matrix": matrix, "per_class": per_class,
            "macro_f1": sum(row["f1"] for row in per_class.values()) / 3,
            "contradiction_recall": per_class["contradicted"]["recall"],
            "false_accusation_rate": false_accusations / non_contradictions
            if non_contradictions else 0.0}
```

- [ ] **Step 4: Implement owner-cluster bootstrap, exact McNemar, Holm correction, and H1 gate**

```python
def _owner_bootstrap_delta(rows: list[dict[str, Any]], samples: int, seed: int) -> list[float]:
    owners = sorted({row["owner"] for row in rows})
    grouped = {owner: [row for row in rows if row["owner"] == owner] for owner in owners}
    rng = random.Random(seed)
    deltas = []
    for _ in range(samples):
        draw = [rng.choice(owners) for _ in owners]
        selected = [row for owner in draw for row in grouped[owner]]
        deltas.append(_contradiction_recall(selected, "raw_recomputation") -
                      _contradiction_recall(selected, "report_only"))
    return sorted(deltas)


def _mcnemar_exact(b: int, c: int) -> float:
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, k) for k in range(0, min(b, c) + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)
```

The H1 gate must read thresholds from the protocol, require a positive lower 2.5% owner-bootstrap delta, raw false-accusation rate `<= 0.05`, valid registration/gold locks, and a passing minimum-information gate. Result writing is exclusive; a second scored result at the same path fails.

- [ ] **Step 5: Validate result JSON and test determinism**

Run twice to two distinct temporary outputs with the same seed and assert byte equality. Validate the result against `evidence-trial-result-v1.schema.json` before writing.

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/reprocheck/evidence_trial.py src/reprocheck/schemas/evidence-trial-result-v1.schema.json tests/test_evidence_trial.py
git commit -m "feat: score blinded evidence trial arms"
```

### Task 6: Certificate-track verification summary

**Files:**
- Modify: `src/reprocheck/evidence_trial.py`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write failing certificate-track tests**

```python
def test_certificate_track_requires_matching_verdicts_and_rejects_registered_tamper(tmp_path: Path):
    cases = _certificate_track_fixture(tmp_path)
    summary = score_certificate_track(cases)
    assert summary["verdict_preservation_rate"] == 1.0
    assert summary["tamper_rejection_rate"] == 1.0
    assert summary["median_byte_reduction"] > 0


def test_certificate_track_rejects_cross_case_swap(tmp_path: Path):
    cases = _certificate_track_fixture(tmp_path)
    cases[0]["witness"], cases[1]["witness"] = cases[1]["witness"], cases[0]["witness"]
    with pytest.raises(ValueError, match="certificate/witness binding"):
        score_certificate_track(cases)
```

- [ ] **Step 2: Confirm red state**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: FAIL because certificate-track scoring is undefined.

- [ ] **Step 3: Implement a thin adapter over existing certificate and witness verifiers**

```python
def score_certificate_track(cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for case in cases:
        certificate = Path(case["certificate"])
        witness = Path(case["witness"])
        artifact_dir = Path(case["artifact_dir"])
        if file_descriptor(certificate)["sha256"] != case["certificate_sha256"]:
            raise ValueError("certificate/witness binding mismatch")
        if verify_certificate_file(certificate, artifact_dir):
            raise ValueError("certificate verification failed")
        if verify_witness_file(witness, certificate, artifact_dir):
            raise ValueError("witness verification failed")
        rows.append(_certificate_track_row(case, certificate, witness))
    return _aggregate_certificate_track(rows)
```

Register these tamper classes exactly: `node`, `edge`, `numeric_value`, `artifact_byte`, `context`, `tolerance`, `mandatory_relation`, `non_minimal`, and `cross_case_swap`. Each mutation is generated into a temporary directory and must make the appropriate verifier return errors.

- [ ] **Step 4: Run focused witness and certificate tests**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py tests/test_certificate.py tests/test_witness.py tests/test_witness_rules.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/reprocheck/evidence_trial.py tests/test_evidence_trial.py
git commit -m "feat: add evidence trial certificate track"
```

### Task 7: Trial CLI commands

**Files:**
- Modify: `src/reprocheck/cli.py`
- Modify: `tests/test_cli_extensions.py`

- [ ] **Step 1: Write failing CLI tests**

```python
def test_trial_verify_registration_cli(tmp_path: Path, capsys):
    paths = _registered_trial(tmp_path)
    assert main(["trial-verify-registration", *paths.cli_verify_args()]) == 0
    assert "PASS: evidence trial registration" in capsys.readouterr().out


def test_trial_score_cli_refuses_unlocked_gold(tmp_path: Path, capsys):
    paths = _unlocked_trial(tmp_path)
    assert main(["trial-score", *paths.cli_score_args()]) == 2
    assert "gold lock" in capsys.readouterr().err
```

- [ ] **Step 2: Confirm parser rejects the new commands**

Run: `uv run --locked --extra dev pytest tests/test_cli_extensions.py -q`

Expected: FAIL with argparse `invalid choice` for `trial-verify-registration`.

- [ ] **Step 3: Add parsers and thin handlers**

Add these commands with explicit `Path` arguments:

```text
trial-register
trial-verify-registration
trial-validate-sample
trial-prepare-review
trial-lock-gold
trial-score
```

Handlers must catch `(OSError, UnicodeDecodeError, ValueError)`, print `ERROR:` to stderr, and return `2`. Verification mismatches print `FAIL:` and return `1`. A valid but scientifically non-supporting scored result still returns `0`; scientific status is data, not a process crash.

Representative parser code:

```python
trial_score = subparsers.add_parser("trial-score", help="score one frozen evidence trial")
trial_score.add_argument("--protocol", type=Path, required=True)
trial_score.add_argument("--registration", type=Path, required=True)
trial_score.add_argument("--gold", type=Path, required=True)
trial_score.add_argument("--arm", action="append", type=_named_path, required=True,
                         metavar="NAME=PATH")
trial_score.add_argument("--bootstrap-samples", type=int, default=5_000)
trial_score.add_argument("--output", type=Path, required=True)
```

- [ ] **Step 4: Run CLI and core tests**

Run: `uv run --locked --extra dev pytest tests/test_cli_extensions.py tests/test_evidence_trial.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/reprocheck/cli.py tests/test_cli_extensions.py
git commit -m "feat: expose evidence trial commands"
```

### Task 8: Build the unregistered v19 benchmark scaffold

**Files:**
- Create: `benchmarks/evidence_trial_v19/protocol.md`
- Create: `benchmarks/evidence_trial_v19/protocol.json`
- Create: `benchmarks/evidence_trial_v19/exclusions.json`
- Create: `benchmarks/evidence_trial_v19/acquire.py`
- Create: `benchmarks/evidence_trial_v19/analyze.py`
- Create: `benchmarks/evidence_trial_v19/verify_registration.py`
- Create: `benchmarks/evidence_trial_v19/README.md`
- Test: `tests/test_evidence_trial.py`

- [ ] **Step 1: Write repository-fixture tests before creating the scaffold**

```python
def test_v19_protocol_matches_design_and_has_no_registration_yet():
    root = Path("benchmarks/evidence_trial_v19")
    protocol = load_trial_protocol(root / "protocol.json")
    assert protocol["minimum_information"] == {
        "repository_owners": 20,
        "claims": 150,
        "contradicted_claims": 20,
        "not_verifiable_claims": 30,
        "supported_evidence_claims": 30,
    }
    assert not (root / "registration.json").exists()


def test_v19_acquisition_resume_is_deterministic_without_network(tmp_path: Path):
    fixture = Path("tests/fixtures/evidence_trial/events.jsonl")
    first = run_acquisition_fixture(fixture, tmp_path / "first")
    second = run_acquisition_fixture(fixture, tmp_path / "second")
    assert first.read_bytes() == second.read_bytes()
```

- [ ] **Step 2: Confirm the scaffold tests fail**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Expected: FAIL because `benchmarks/evidence_trial_v19` does not exist.

- [ ] **Step 3: Write the complete protocol and exclusion registry**

`protocol.json` must encode the exact v19 thresholds and gates from the approved design. `exclusions.json` must contain every owner and file already used in v6-v18 plus pilot exclusions, sorted and unique, with `generated_from` source manifests and a digest field.

The repository test must reconstruct the exclusion union from those source manifests and reject omissions.

- [ ] **Step 4: Implement deterministic acquisition with dependency injection**

```python
def acquire(config: dict[str, Any], output_dir: Path, fetch: Callable[[str], bytes]) -> Path:
    state_path = output_dir / "acquisition-state.json"
    state = _load_or_initialize_state(state_path, config)
    for event in _deterministic_events(config, fetch):
        if event["event_id"] in state["completed_event_ids"]:
            continue
        payload = _bounded_fetch_event(event, fetch, config["limits"])
        _write_event_exclusive(output_dir, event, payload)
        state["completed_event_ids"].append(event["event_id"])
        state["completed_event_ids"].sort()
        _write_state_atomic(state_path, state)
    return _finalize_sample(output_dir, state)
```

Network code uses `urllib.request` with an explicit user agent, HTTPS-only URLs, redirect limit, per-response byte cap, global byte cap, timeout, and `.part`-then-rename. Tests pass a fixture `fetch` function; unit tests never access the network.

- [ ] **Step 5: Implement frozen analysis and registration wrappers**

`analyze.py` accepts only file paths and calls `score_evidence_trial`; it contains no alternate metric implementation. `verify_registration.py` resolves paths relative to its own directory and exits nonzero on any descriptor mismatch.

- [ ] **Step 6: Run scaffold and lint tests**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py -q`

Run: `uv run --locked --extra dev ruff check benchmarks/evidence_trial_v19 src/reprocheck/evidence_trial.py tests/test_evidence_trial.py`

Expected: both commands pass.

- [ ] **Step 7: Commit the unregistered scaffold**

```bash
git add benchmarks/evidence_trial_v19 src/reprocheck/evidence_trial.py tests/test_evidence_trial.py
git commit -m "feat: add evidence trial v19 scaffold"
```

### Task 9: Make targets, documentation, and offline RKNP demonstration

**Files:**
- Modify: `Makefile`
- Modify: `README.md`
- Modify: `docs/SCIENTIFIC_PROTOCOL.md`
- Modify: `docs/SCIENTIFIC_SCORECARD.md`
- Create: `benchmarks/evidence_trial_v19/demo/`
- Test: `tests/test_action.py`

- [ ] **Step 1: Write failing Makefile and documentation contract tests**

```python
def test_makefile_has_offline_trial_targets():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    assert "evidence-trial-v19-local:" in makefile
    assert "evidence-trial-v19-registration:" in makefile
    assert "evidence-trial-v19-replay:" in makefile
    gate = makefile.split("gate:", 1)[1].split("\n\n", 1)[0]
    assert "trial-retrieve" not in gate


def test_scorecard_does_not_claim_v19_external_result_before_scoring():
    text = Path("docs/SCIENTIFIC_SCORECARD.md").read_text(encoding="utf-8")
    assert "v19 status: protocol/scaffold only; no scored external result" in text
```

- [ ] **Step 2: Confirm red state**

Run: `uv run --locked --extra dev pytest tests/test_action.py -q`

Expected: FAIL because targets and status text do not exist.

- [ ] **Step 3: Add offline-safe Make targets**

```make
evidence-trial-v19-local:
	python3 -m reprocheck.cli trial-validate-sample --protocol benchmarks/evidence_trial_v19/protocol.json --sample benchmarks/evidence_trial_v19/demo/sample.json --exclusions benchmarks/evidence_trial_v19/exclusions.json
	python3 benchmarks/evidence_trial_v19/demo/run_demo.py --output outputs/evidence-trial-v19-demo.json

evidence-trial-v19-registration:
	python3 benchmarks/evidence_trial_v19/verify_registration.py

evidence-trial-v19-replay: evidence-trial-v19-registration
	python3 benchmarks/evidence_trial_v19/analyze.py --frozen-inputs benchmarks/evidence_trial_v19/scored-inputs.json --output outputs/evidence-trial-v19-replay.json
```

Only `evidence-trial-v19-local` enters `make gate` before registration. Retrieval never enters the ordinary gate because it depends on mutable external state.

- [ ] **Step 4: Add a three-claim offline demo**

The demo must contain one supported, one contradicted, and one not-verifiable claim. It runs report-only and raw-recomputation arms, builds a real minimal witness for the contradiction, verifies it, mutates one numeric value in a temporary copy, and records verifier rejection.

- [ ] **Step 5: Update docs using bounded status language**

Before a real score exists, documentation may say only:

```text
v19 status: protocol/scaffold only; no scored external result.
The trial is designed to test whether raw-artifact recomputation improves
contradiction recall at a <=5% false-accusation gate. It does not yet establish that claim.
```

- [ ] **Step 6: Run offline demo and documentation tests**

Run: `make evidence-trial-v19-local`

Expected: exit 0, three tri-state demo rows, valid witness, and rejected mutation.

Run: `uv run --locked --extra dev pytest tests/test_action.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add Makefile README.md docs/SCIENTIFIC_PROTOCOL.md docs/SCIENTIFIC_SCORECARD.md benchmarks/evidence_trial_v19/demo tests/test_action.py
git commit -m "docs: expose bounded evidence trial workflow"
```

### Task 10: Full local gate, evaluator freeze, and immutable registration

**Files:**
- Create: `benchmarks/evidence_trial_v19/evaluator/reprocheck-0.30.0-py3-none-any.whl`
- Create: `benchmarks/evidence_trial_v19/registration.json`
- Modify: `pyproject.toml`
- Modify: `src/reprocheck/version.py`
- Modify: `docs/RELEASE_0.30.md`

- [ ] **Step 1: Bump the version only after all trial code is green**

Set both package version locations to `0.30.0`. Release notes must label v19 as registered and unexecuted, not externally validated.

- [ ] **Step 2: Run focused checks before the expensive gate**

Run: `uv run --locked --extra dev pytest tests/test_evidence_trial.py tests/test_cli_extensions.py tests/test_action.py -q`

Expected: PASS.

Run: `uv run --locked --extra dev ruff format --check src/reprocheck/evidence_trial.py tests/test_evidence_trial.py benchmarks/evidence_trial_v19`

Expected: PASS.

Run: `uv run --locked --extra dev pyright src tests`

Expected: `0 errors`.

- [ ] **Step 3: Run the complete existing gate**

Run: `make gate`

Expected: every legacy frozen benchmark, coverage threshold, lint, types, deterministic build, and offline v19 local target pass. A focused green test is not sufficient.

- [ ] **Step 4: Build twice and verify reproducibility**

Run: `make build && shasum -a 256 dist/reprocheck-0.30.0-py3-none-any.whl`

Copy the first digest, remove only the newly generated `dist/reprocheck-0.30.0*` artifacts, run `make build` again, and compare. Expected: wheel SHA-256 is identical under `SOURCE_DATE_EPOCH`.

- [ ] **Step 5: Copy the frozen wheel and register all executable inputs**

```bash
mkdir -p benchmarks/evidence_trial_v19/evaluator
cp dist/reprocheck-0.30.0-py3-none-any.whl benchmarks/evidence_trial_v19/evaluator/
python3 -m reprocheck.cli trial-register \
  --protocol benchmarks/evidence_trial_v19/protocol.json \
  --evaluator benchmarks/evidence_trial_v19/evaluator/reprocheck-0.30.0-py3-none-any.whl \
  --acquisition benchmarks/evidence_trial_v19/acquire.py \
  --analysis benchmarks/evidence_trial_v19/analyze.py \
  --exclusions benchmarks/evidence_trial_v19/exclusions.json \
  --output benchmarks/evidence_trial_v19/registration.json
python3 benchmarks/evidence_trial_v19/verify_registration.py
```

Expected: registration status `registered_not_retrieved`, followed by PASS.

- [ ] **Step 6: Verify clean-wheel command surface**

Create a temporary virtual environment, install only the frozen wheel, then run:

```bash
reprocheck --version
reprocheck trial-verify-registration \
  --registration benchmarks/evidence_trial_v19/registration.json \
  --protocol benchmarks/evidence_trial_v19/protocol.json \
  --evaluator benchmarks/evidence_trial_v19/evaluator/reprocheck-0.30.0-py3-none-any.whl \
  --acquisition benchmarks/evidence_trial_v19/acquire.py \
  --analysis benchmarks/evidence_trial_v19/analyze.py \
  --exclusions benchmarks/evidence_trial_v19/exclusions.json
```

Expected: version `0.30.0` and registration PASS.

- [ ] **Step 7: Confirm v18 remains untouched**

Run: `git status --short benchmarks/cross_project_holdout_v18`

Expected: exactly the pre-existing untracked `frames.json`, `raw/`, and `sample.json`; no staged v18 paths.

- [ ] **Step 8: Commit the freeze**

```bash
git add pyproject.toml src/reprocheck/version.py docs/RELEASE_0.30.md \
  benchmarks/evidence_trial_v19/evaluator/reprocheck-0.30.0-py3-none-any.whl \
  benchmarks/evidence_trial_v19/registration.json
git commit -m "release: freeze ReproCheck 0.30 evidence trial"
```

### Task 11: Retrieval readiness checkpoint

**Files:**
- No code changes unless a preregistered acquisition invariant fails.

- [ ] **Step 1: Verify registration immediately before any network call**

Run: `make evidence-trial-v19-registration`

Expected: PASS.

- [ ] **Step 2: Run only the registered pilot-excluded main acquisition**

Run: `python3 benchmarks/evidence_trial_v19/acquire.py --registration benchmarks/evidence_trial_v19/registration.json --output benchmarks/evidence_trial_v19/acquisition`

Expected: deterministic state/sample artifacts or a preserved failure manifest. Do not edit the evaluator, acquisition script, source configuration, analysis script, protocol, or exclusions after this command.

- [ ] **Step 3: Validate the information gate without scoring**

Run: `reprocheck trial-validate-sample --protocol benchmarks/evidence_trial_v19/protocol.json --sample benchmarks/evidence_trial_v19/acquisition/sample.json --exclusions benchmarks/evidence_trial_v19/exclusions.json`

Expected: either `eligible` with all counts or `insufficient_sample` with exact shortfalls. Both are valid scientific outcomes; only `eligible` may proceed to blinded review.

- [ ] **Step 4: Stop before review distribution**

Do not fabricate reviewer responses or use AI as an external reviewer. Report the acquisition status and request the real reviewer/SRC coordination required by the approved design.
