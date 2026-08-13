# MELT Benchmark Results

Benchmark results from MELT evaluation runs. All results use the MELT
methodology envelope for reproducibility and comparability.

> **Status convention:** legacy `preliminary` = single run or dev split.
> Lifecycle v5 uses `diagnostic` for a non-canonical run/seed/split protocol,
> `not_supported` for a capability mismatch, and `invalid` for a failed validity
> guard. `final` requires held-out data, the frozen profile protocol, and passing
> guards.

## Lifecycle v5 Corrective Validation, 2026-07-15

MELT 0.3.1 keeps the immutable `lifecycle-v5` corpus/eval spec 1.1.0 and
releases corrected scorer `lifecycle-score/2.1.0` with RFC 8785
comparison-key version 2. The output-changing fixes are intentionally not exact
comparisons to the original 2.0.0 rows below.

The fake B3 reference oracle ran every frozen profile on both `mini` and `full`.
All runs were one-run dev diagnostics. No profile was `not_supported`; every
active retrieval, lifecycle, scope, conflict, correction, QA, answer-mode, and
citation metric was 1.0, and every applicable zero-leak guard passed.

| Profile / full fixture | Cases | Retrieval | Lifecycle | Scope | QA | Guard verdicts | Status |
|---|---:|---:|---:|---:|---:|---|---|
| `lifecycle-v5-core` | 4 | 1.000000 | 1.000000 | n/a | n/a | n/a | diagnostic |
| `lifecycle-v5-scoped` | 72 | 1.000000 | 1.000000 | 1.000000 | n/a | 3 / 3 pass | diagnostic |
| `lifecycle-v5-answer` | 36 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 4 / 4 pass | diagnostic |
| `lifecycle-v5-agentic` | 12 | 1.000000 | 1.000000 | 1.000000 | n/a | 3 / 3 pass | diagnostic |

The corresponding `mini` runs covered 4 core, 18 scoped, 9 answer, and 3
agentic cases with the same pass outcomes. The corrected score-protocol hash is
`sha256:ba957b95a47650465e9ed351500abbb393c5789f0772d791b155bbabc312ea1f`.
Example key-v2 metric identities are
`scope_evidence_leak_rate=sha256:b5f650fab3170a7df7b0420bdaeefb901bb039b98472f58cfa85f07e147f15b5`
and
`structured_answer_mode_accuracy=sha256:5e0031f77f1a92cd5061dde80fcdbbe7cf383b82f53136c0ad33e7f433fc5d2e`.
These runs validate fixture satisfiability and harness mechanics; they are not
independent system results or a cross-SUT leaderboard.

## Original Lifecycle v5 Release Validation, 2026-07-15

This is reference-oracle and adapter-readiness evidence for immutable suite
`lifecycle-v5`, eval spec `1.1.0`, MELT schema `2`, report schema `5`, B3, and
score protocol `lifecycle-score/2.0.0` and comparison-key version 1. It is not a
cross-SUT leaderboard. These rows remain valid historical diagnostics, but the
corrected 2.1.0 rows above supersede them for new publication.
Both fake runs are one-run dev diagnostics; the final five-run held-out protocol
is intentionally not represented as a statistically independent system result.

The scoped full profile executed 72 cases (four variants across 18 scenario
clusters) and 176 retrieval probes. The answer mini profile executed 9 cases,
25 retrieval probes, and 18 deterministic SUT-native structured answers. The
fake B3 oracle passed every active lifecycle, scope, conflict, correction, and
structured-answer expectation. All mechanical leakage guards passed.

| SUT | Profile / fixture | Cases | Lifecycle pass | Scope accuracy | Evidence / canary / unattributed leak | Conflict recall | False-conflict rate | Correction | QA / mode / citation | Claim-scope leak | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fake | `lifecycle-v5-scoped` / full | 72 | 1.000000 | 1.000000 | 0 / 0 / 0 | 1.000000 | 0.000000 | 1.000000 | n/a | n/a | diagnostic |
| fake | `lifecycle-v5-answer` / mini | 9 | 1.000000 | 1.000000 | 0 / 0 / 0 | 1.000000 | n/a | 1.000000 | 1 / 1 / 1 | 0.000000 | diagnostic |

Local release-validation runtime (one Python process, fake adapter): scoped full
1.212s, answer mini 0.542s, observed maximum RSS 74008 KB. These figures are
harness sanity checks, not service-adapter performance claims.

Frozen and score identities:

| Profile / fixture | Fixture hash | Profile-manifest hash | Runtime protocol hash |
|---|---|---|---|
| scoped / full | `1061258885bc7326d00e05f592ff81ade8be2bfc10aeb5f0ae17e5e7fa37a16b` | `sha256:4d64c9b96d9b208ba9b152e0155a89059a911828b251bf4222b7ea37bb0c38a1` | `sha256:e9cb936a297834640790b6b423002066f55be2364cf743a7cf5c38aca3ea146c` |
| answer / mini | `1b21db02f23e5ea3a938ffbead09cd91631c2b50c8e172d115f1077d16ee3051` | `sha256:927054333a41b1b9130d196f0b9cc636bf273ec32b218ac7182d287844c0c841` | `sha256:65561875b1a3925d31bc9e0bf2e06288f4322e47e17ff21f3488402d9dfe3b5d` |

Both use score-protocol hash
`sha256:43e3fd2a0d42b23190ee77d803eaffb95deef37d54f3cb06dc2b06d97f4ed3b9`.
Comparison keys are metric-specific; examples are
`scope_evidence_leak_rate=sha256:cd440c1f07a746617ee82ad29757ee0e46df9ebba1a007c3220da7de17493b5b`
and
`structured_answer_mode_accuracy=sha256:7b582498e3ab74227c54da77f50a8460b7f5229832d9467456d1e4806c670baa`.
The scoped and answer rows therefore are not exact comparisons to each other or
to lifecycle-v4.

Real-adapter readiness:

- A local shisad dry run reached the real `shisad memory sut` process but failed
  before cases with `unsupported_contract_version: ... expected b2`. Artifact:
  `results/lifecycle_shisad_2026-07-14T193545Z_6d8d25ff_cf4261f6/summary.json`.
  This is an adapter/backend capability blocker, not a benchmark score.
- Memobase was not run: no project credentials were available, and the current
  adapter declares B2 with `scoped_memory` unsupported. A scoped profile would
  be `not_supported`, not a zero or passing score.

Reference artifacts:

- `results/lifecycle_fake_2026-07-14T193532Z_7d34dd45_36cbaa59/summary.json`
- `results/lifecycle_fake_2026-07-14T193534Z_b9fabeff_2b1b3adc/summary.json`

## Lifecycle + Agentic Memory, 2026-06-07 (suite `lifecycle-v4`)

These runs exercise MELT's native lifecycle suite with scripted and agentic
tracks. They use retrieval/lifecycle/write-policy scoring only; the lifecycle
fixture currently has no `qa` expectations, so harness answer/judge columns are
not applicable. All runs emitted a retrieval-bypass warning because `top_k=3`
is greater than or equal to the built-in fixture's two canonical sessions.

**`lifecycle-v4` redesign (supersedes earlier `lifecycle-smoke-v3` numbers).**
The scripted generated cases now exercise the behavior named by their axis
instead of a uniform store-then-retrieve probe: correction cases supersede,
contradiction cases write a conflicting pair and consolidate, temporal cases
issue as-of queries before a supersession, maintenance cases age a fact past the
decay threshold, negative-retrieval cases add a distractor that must be
excluded, and privacy-scope cases add an out-of-scope unit. Consequently the
per-axis tables below are now behavioral diagnostics: a system that cannot
supersede will lose `correction`, one that cannot exclude distractors will lose
`negative_retrieval`, and so on. Under `lifecycle-smoke-v3` these per-axis
columns were dominated by trivial passes and should not be compared to v4.

Reading caveats:

- **Per-axis numbers measure behavior, not just retrieval.** Each behavioral
  axis carries a distinctive assertion (`superseded_fact_absent`,
  `contradiction_detected`, `historical_fact_retained`, `decayed_below_threshold`,
  `negative_evidence_absent`, `scope_isolated`, ...).
- **Black-box write-policy scores are weak.** Without `memory_export`,
  `memory_write_precision_black_box` collapses to recall and
  `memory_dedupe_rate_black_box` is trivially 1.0 (the probe cannot see the full
  memory set). Only `fake` exercises export-backed scoring; Memobase and shisad
  fall back to black-box, so their `export` columns are `n/a`.
- **Two axes use oracle-satisfiable proxies.** `privacy_scope` exercises
  non-leakage of a token-disjoint other-scope unit (true same-topic cross-scope
  isolation needs a scope-aware SUT); `operational` exercises survival across a
  full consolidation plus a time tick (true process-restart robustness is a
  runner-level `--restart-sut-per-case` concern). Both are flagged for deepening.
- **The agentic track is retention-focused.** Generated agentic cases all assert
  `should_retain` capture under autonomous `manage`; autonomous forget/update
  policy needs a forgetting SUT and richer gold and is deferred.

`fake` is the reference oracle and passes every behavioral case by construction;
its all-`1.000000` row validates that the generated cases are satisfiable and
that document-granularity retrieval is now scored (previously a silent `0.0`).

| SUT | Fixture | Cases | claim_type | Lifecycle Pass | Retrieval R@3 | Session R@3 | Document R@3 | Abstention | Write Recall export / black-box | Token Efficiency export | Status |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| fake | mini | 48 | agentic_memory | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 / 1.000000 | 1.000000 | preliminary |
| fake | full | 217 | agentic_memory | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 / 1.000000 | 1.000000 | preliminary |
| fake | stress | 373 | agentic_memory | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 / 1.000000 | 1.000000 | preliminary |
| Memobase | full | 217 | agentic_memory | 0.446429 | 0.134328 | 0.000000 | 1.000000 | 1.000000 | n/a / 1.000000 | n/a | preliminary |
| shisad | full | 217 | agentic_memory | 0.953571 | 0.902985 | 1.000000 | 1.000000 | 1.000000 | n/a / 1.000000 | n/a | preliminary |

The `lifecycle-smoke-v3` numbers previously published here measured the
superseded trivial-coverage fixture and no longer validate against the
`lifecycle-v4` canonical fixture hash. The shisad and Memobase rows above are
fresh `lifecycle-v4` full reruns with `top_k=3` and `--no-store-case-io`.

MIRA-OSS was not run. MELT currently registers `mira` as a non-runnable
follow-up target with no SUT factory; `melt run --sut mira ...` exits with
`mira SUT adapter is not runnable in this environment`.

Per-axis lifecycle pass rates:

| Axis | fake full | Memobase full | shisad full |
|---|---:|---:|---:|
| write_quality | 1.000000 | 0.833333 | 1.000000 |
| structured_memory_semantics | 1.000000 | 0.250000 | 1.000000 |
| correction | 1.000000 | 0.566667 | 1.000000 |
| contradiction | 1.000000 | 0.133333 | 1.000000 |
| temporal | 1.000000 | 0.235294 | 0.235294 |
| maintenance | 1.000000 | 0.133333 | 1.000000 |
| core_memory | 1.000000 | 0.235294 | 1.000000 |
| multi_hop | 1.000000 | 0.235294 | 1.000000 |
| abstention | 1.000000 | 1.000000 | 1.000000 |
| negative_retrieval | 1.000000 | 0.571429 | 1.000000 |
| privacy_scope | 1.000000 | 0.571429 | 1.000000 |
| source_type | 1.000000 | 1.000000 | 1.000000 |
| operational | 1.000000 | 0.250000 | 1.000000 |

Runtime and MELT-observed usage:

| SUT | Successful elapsed | Attempted elapsed | Max RSS | MELT LLM calls answer/judge | Answer tokens in/out | Judge tokens in/out | MELT-observed API cost | Artifact |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Memobase | 378.86s | 515.27s | 45132 KB | 0 / 0 | 0 / 0 | 0 / 0 | $0.000 | `results/lifecycle_memobase_2026-06-07T074021Z_bb4e61c7_438ea842/summary.json` |
| shisad | 95.16s | 95.16s | 91836 KB | 0 / 0 | 0 / 0 | 0 / 0 | $0.000 | `results/lifecycle_shisad_2026-06-07T073428Z_d31f17f1_c554bf21/summary.json` |

The Memobase attempted elapsed includes an initial 136.41s run that timed out
after 11 completed cases on `lifecycle-full-write-quality-003`; the successful
artifact resumed from checkpoints with `sut.timeout_seconds=300`. Lifecycle-v4
has no `qa` expectations and does not invoke the MELT answer/judge LLM path, so
MELT-observed token usage and API cost are zero. Memobase backend provider
embedding/LLM usage is service-dependent and not exposed through the adapter.
The fake rows above reproduce with `melt run --sut fake --suite lifecycle
--fixture <fx> --top-k 3`.

## GPT-5.4 Mini Answer / GPT-5.4 Judge LoCoMo, 2026-06-01

These full LoCoMo runs include Category 5 and use separate OpenAI models for
harness answering and LLM judging:

- Answer: `openai/gpt-5.4-mini`, `reasoning_effort=low`,
  `max_output_tokens=512`.
- Judge: `openai/gpt-5.4`, `reasoning_effort=low`,
  `max_output_tokens=1024`.
- Config: `configs/locomo-openai-split-low.toml`.
- Runs used `--no-store-case-io` to keep report memory bounded. The shisad run
  also used `--restart-sut-per-case`.

The cost columns use OpenAI API pricing of $0.75/M input and $4.50/M output
tokens for `gpt-5.4-mini`, plus $2.50/M input and $15.00/M output tokens for
`gpt-5.4`. Pricing sources: `https://developers.openai.com/api/docs/models/gpt-5.4-mini`
and `https://developers.openai.com/api/docs/models/gpt-5.4/`.

| SUT | Questions | MELT Judged Score | Correct | Partial | Invalid Judge Rate | LLM Error Rate | Answer Tokens in/out | Judge Tokens in/out | Equivalent Answer Cost | Equivalent Judge Cost | Equivalent Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Memobase | 1986 | 0.420282 | 692 | 240 | 0.000000 | 0.000000 | 6331087 / 167086 | 300900 / 177470 | $5.500 | $3.414 | $8.915 |
| shisad | 1986 | 0.062091 | 95 | 48 | 0.000504 | 0.000252 | 637051 / 114481 | 286531 / 183589 | $0.993 | $3.470 | $4.463 |

`Equivalent` cost means the cost implied by the full token usage recorded in
the summary, including calls served from MELT's LLM cache. Actual fresh API
spend during the completed run windows was lower because the namespace reused
cached calls from smoke/failed attempts and from duplicate prompts:

| SUT | Fresh Answer Calls | Fresh Judge Calls | Fresh Answer Cost | Fresh Judge Cost | Fresh Total |
|---|---:|---:|---:|---:|---:|
| Memobase | 1974 | 1974 | $5.467 | $3.392 | $8.859 |
| shisad completed rerun | 1775 | 1165 billed cache rows, plus 1 failed 503 judge call | $0.886 | $2.034 | $2.921 |
| shisad failed strict attempt | 199 | 129 | $0.100 | $0.229 | $0.329 |

Category breakdown from judged QA. `Score` is the mean judge score; `exact` is
the exact-correct label rate; `any` is `correct` or `partially_correct`.

| Category | Questions | Memobase score / exact / any | shisad score / exact / any |
|---|---:|---:|---:|
| 1 | 282 | 0.515780 / 0.297872 / 0.687943 | 0.071383 / 0.046099 / 0.099291 |
| 2 | 321 | 0.509938 / 0.473520 / 0.526480 | 0.021807 / 0.021807 / 0.021807 |
| 3 | 96 | 0.286667 / 0.229167 / 0.322917 | 0.098750 / 0.072917 / 0.114583 |
| 4 | 841 | 0.497800 / 0.439952 / 0.538644 | 0.072786 / 0.059524 / 0.083333 |
| 5 | 446 | 0.177960 / 0.143498 / 0.190583 | 0.057175 / 0.040359 / 0.060538 |

Artifacts:

| SUT | Summary JSON |
|---|---|
| Memobase | `results/locomo_memobase_2026-06-01T164148Z_694f96eb_552cccec/summary.json` |
| shisad | `results/locomo_shisad_2026-06-01T200642Z_c75de6b9_30db2358/summary.json` |

## GPT-5.4 Medium Answer/Judge Probes, 2026-05-31

These runs exercise MELT's LLM-backed harness-answer and LLM-judge path using
OpenAI `gpt-5.4` with `reasoning_effort=medium` for both answer generation and
judging. The GPT-5.4 Chat Completions path requires `max_completion_tokens`
rather than `max_tokens`, and GPT-5.4 accepts the default temperature value
(`1`) rather than MELT's deterministic default (`0`).

Smoke and built-in LoCoMo smoke probes passed for both local Memobase and
shisad:

| SUT | Benchmark | Fixture | top_k | Judged QA | Answer Calls | Judge Calls | Summary JSON |
|---|---|---|---:|---:|---:|---:|---|
| Memobase | Smoke | smoke | 1 | 1.000000 | 1 | 1 | `results/smoke_memobase_2026-05-31T045314Z_f8ebfb73_8c525f02/summary.json` |
| shisad | Smoke | smoke | 1 | 1.000000 | 1 | 1 | `results/smoke_shisad_2026-05-31T045344Z_5519149d_a8df2bed/summary.json` |
| Memobase | LoCoMo smoke | smoke | 5 | 1.000000 | 1 | 1 | `results/locomo_memobase_2026-05-31T045411Z_0910eaa1_5b45cfdc/summary.json` |
| shisad | LoCoMo smoke | smoke | 5 | 1.000000 | 1 | 1 | `results/locomo_shisad_2026-05-31T045427Z_3c578117_dc53fe9a/summary.json` |

Full local Memobase LoCoMo Category 5 excluded was also run, but the judged
score is **not leaderboard-comparable** because the judge invalid rate is high.
The run used `judge.model.max_output_tokens=128`; with medium reasoning, many
judge calls returned truncated or non-JSON output. A rerun with
`judge.model.max_output_tokens=512` was started, but stopped after it proved to
be another multi-hour run and was regenerating answer calls due to Memobase
retrieval-context variation.

| SUT | Benchmark | Fixture | Questions | top_k | Retrieval Scores | Judged QA | Invalid Judge Rate | Summary JSON |
|---|---|---|---:|---:|---|---:|---:|---|
| Memobase | LoCoMo, Category 5 excluded | full | 1540 | 5 | turn R@5 0.134766, turn nDCG@5 0.136659 | 0.145757 | 0.395455 | `results/locomo_memobase_2026-05-31T045540Z_a3c169d1_5f14e449/summary.json` |

Full Memobase GPT-5.4 diagnostic counts:

- Judge labels: 128 `correct`, 16 `partially_correct`, 31 `incorrect`, 756
  `abstained_incorrectly`, and 609 `invalid`.
- Retrieval questions with gold evidence at top-k: 207 / 1536.
- Answer calls/tokens: 1531 calls, 288312 input tokens, 150661 output tokens.
- Judge calls/tokens: 1535 calls, 131727 input tokens, 101605 output tokens.
- Error diagnostics: `llm_call_error_rate` 0.208766 and
  `qa_invalid_judge_rate` 0.395455.

## shisad Answer-Path Validation, 2026-05-30

These runs validate the new MELT answer-generation and judged-QA report path
against the actual `shisad memory sut` subprocess. They use deterministic local
answer extraction and deterministic local judging, so they are not comparable to
published LoCoMo LLM-judge scores.

SUT: `shisad` 0.7.4 at `3ab0ed2-dirty`, contract `b2`.

| Benchmark | Fixture | Cases | Questions | top_k | Retrieval Scores | Judged QA | Notes |
|---|---|---:|---:|---:|---|---:|---|
| Smoke | smoke | 1 | 1 | 1 | turn R@1 1.000000 | 1.000000 | harness answer + deterministic judge |
| LoCoMo, Category 5 excluded | full | 10 conversations | 1540 | 5 | turn R@5 0.024089 | 0.002597 | `locomo_official_like` profile with deterministic-provider deviations |

LoCoMo answer-path diagnostics:

- Correct judged answers: 4 / 1540.
- Retrieval questions with gold evidence at top-k: 37 / 1536.
- Mean context items: 5.000000; mean context tokens: 172.218182.
- Answer provider/model: `deterministic/extractive-v1`.
- Judge provider/model: `deterministic/token-f1-v1`.
- Official-profile deviations: `answer_provider_is_deterministic`,
  `judge_provider_is_deterministic`.
- Category 5 excluded count: 446.
- LoCoMo audit caveat: score differences under 5pp are non-decisive.

Artifacts:

| Run | Summary JSON |
|---|---|
| Smoke answer-path validation | `results/smoke_shisad_2026-05-30T213535Z_3bfdd80a_ba14226a/summary.json` |
| LoCoMo answer-path validation | `results/locomo_shisad_2026-05-30T213943Z_ffa192e0_394addb5/summary.json` |

## shisad Results, 2026-05-22

SUT: `shisad` 0.7.4 at `c82a978-dirty`, contract `b2`.

| Benchmark | Fixture | Cases | Sessions | top_k | Retrieval / Lifecycle Scores | QA Accuracy | Status |
|---|---|---:|---:|---:|---|---:|---|
| Smoke | smoke | 1 | 1 | 1 | retrieval R@k 1.000000, nDCG@k 1.000000 | 0.000000 | preliminary |
| Lifecycle | smoke | 7 | 2 | 3 | lifecycle pass 1.000000, abstention 1.000000, retrieval R@k 1.000000, nDCG@k 1.000000 | n/a | preliminary |
| LongMemEval-S | full | 500 | 62 | 5 | session R@k 0.061702, session nDCG@k 0.119045; turn R@k 0.023404, turn nDCG@k 0.039404 | 0.000000 | preliminary |
| LongMemEval-M | full | 500 | 487 | 5 | session R@k 0.006383, session nDCG@k 0.018094; turn R@k 0.002128, turn nDCG@k 0.004203 | 0.000000 | preliminary |
| LoCoMo, Category 5 excluded | full | 1540 | 32 | 5 | turn R@k 0.024089, turn nDCG@k 0.018833 | 0.000000 | preliminary |
| LoCoMo, Category 5 included | full | 1986 | 32 | 5 | turn R@k 0.027750, turn nDCG@k 0.020698 | 0.000000 | preliminary |

QA accuracy is 0.000000 where reported because shisad advertises
`answer_generation` as unsupported in deterministic mode. These runs evaluate
retrieval and lifecycle behavior without an external LLM judge.

## Memobase Adapter Validation, 2026-05-23

These local Docker-backed runs validate the MELT Memobase adapter path. They are
not full Memobase benchmark results.

SUT: local Memobase server on `http://localhost:8019`, Docker Compose stack with
Postgres/pgvector, Redis, OpenAI `gpt-4o-mini`, and OpenAI
`text-embedding-3-small`.

| Benchmark | Fixture | Cases | Sessions | top_k | Retrieval Scores | QA Accuracy | Status |
|---|---|---:|---:|---:|---|---:|---|
| Smoke | smoke | 1 | 1 | 5 | retrieval R@k 1.000000, nDCG@k 1.000000 | 0.000000 | adapter-validation |
| LoCoMo first question | one-question subset | 1 | 19 | 5 | turn R@k 1.000000, turn nDCG@k 1.000000 | 0.000000 | adapter-validation |
| LoCoMo first 3 questions | conversation subset | 1 | 19 | 5 | turn R@k 0.666667, turn nDCG@k 0.666667 | 0.000000 | adapter-validation |

Memobase retrieval evidence is attributed back to MELT source ids by matching
returned Memobase event-gist text against ingested event text. The LoCoMo probe
retrieved expected evidence `D1:3` at rank 1 for
`locomo_0_qa0`.

The grouped LoCoMo probe validates the updated harness shape: one conversation
case ingested 419 turns once, then asked `locomo_0_qa0`, `locomo_0_qa1`, and
`locomo_0_qa2` against the same SUT state.

Memobase probe artifacts:

| Benchmark | Summary JSON |
|---|---|
| Smoke | `results/smoke_memobase_2026-05-23T060401Z_50b50c49_5aef8840/summary.json` |
| LoCoMo first question | `results/locomo_memobase_2026-05-23T060509Z_fdfd2590_099bfce5/summary.json` |
| LoCoMo first 3 questions, conversation grouped | `results/locomo_memobase_2026-05-23T094656Z_85930a80_d150b11e/summary.json` |

## Memobase LoCoMo Full Results, 2026-05-23 to 2026-05-24

These are full MELT LoCoMo retrieval runs against the local Docker-backed
Memobase service. They use conversation-level cases, so each LoCoMo
conversation is ingested once and all questions for that conversation are asked
against the same Memobase user state.

SUT: local Memobase server on `http://localhost:8019`, Docker Compose stack with
Postgres/pgvector, Redis, OpenAI `gpt-4o-mini`, and OpenAI
`text-embedding-3-small`.

| Benchmark | Fixture | Cases | Questions | Turn Retrieval Scores | QA Accuracy | Status |
|---|---|---:|---:|---|---:|---|
| LoCoMo, Category 5 excluded | full | 10 conversations | 1540 | turn R@5 0.015625, turn nDCG@5 0.017938 | 0.000000 | preliminary |
| LoCoMo, Category 5 included | full | 10 conversations | 1986 | turn R@5 0.023209, turn nDCG@5 0.023821 | 0.000000 | preliminary |

QA accuracy is 0.000000 because this MELT adapter path evaluates Memobase
retrieval evidence only. It does not run the upstream Memobase
context-plus-GPT answer generation path or an LLM judge.

Per-category turn retrieval:

| Run | Category | Retrieval Questions | turn R@5 | turn nDCG@5 |
|---|---:|---:|---:|---:|
| Category 5 excluded | 1 | 282 | 0.000000 | 0.023490 |
| Category 5 excluded | 2 | 321 | 0.015576 | 0.016149 |
| Category 5 excluded | 3 | 92 | 0.010870 | 0.010870 |
| Category 5 excluded | 4 | 841 | 0.021403 | 0.017532 |
| Category 5 included | 1 | 282 | 0.000000 | 0.027966 |
| Category 5 included | 2 | 321 | 0.018692 | 0.018809 |
| Category 5 included | 3 | 92 | 0.010870 | 0.010870 |
| Category 5 included | 4 | 841 | 0.026159 | 0.022017 |
| Category 5 included | 5 | 446 | 0.038117 | 0.030881 |

Side-by-side retrieval comparison against the shisad deterministic retrieval
run. These are exact annotated-turn retrieval diagnostics, not official LoCoMo
answer-generation scores.

| System | Case shape | Retrieval expectations | Strict all-hit | Any-hit | turn R@5 | any-hit@5 | turn nDCG@5 |
|---|---|---:|---:|---:|---:|---:|---:|
| Memobase | conversation | 1982 | 46 / 1982 | 72 / 1982 | 0.023209 | 0.036327 | 0.023821 |
| shisad | QA | 1982 | 55 / 1982 | 66 / 1982 | 0.027750 | 0.033300 | 0.020698 |

Category 5 included comparison:

| Category | Retrieval Questions | Memobase all / any | shisad all / any |
|---|---:|---:|---:|
| 1 | 282 | 0 / 22 | 0 / 7 |
| 2 | 321 | 6 / 7 | 7 / 7 |
| 3 | 92 | 1 / 1 | 1 / 3 |
| 4 | 841 | 22 / 24 | 29 / 30 |
| 5 | 446 | 17 / 18 | 18 / 19 |

Memobase full-run artifacts:

| Benchmark | Summary JSON |
|---|---|
| LoCoMo, Category 5 excluded | `results/locomo_memobase_2026-05-23T113004Z_da4137bd_3f8197a2/summary.json` |
| LoCoMo, Category 5 included | `results/locomo_memobase_2026-05-24T065520Z_8d3e8ce7_117d42e7/summary.json` |

The first Category 5 included attempt produced an error report because the
Memobase API container could not restart after its temporary bind-mounted
`config.yaml` path disappeared. Docker reported `OOMKilled=false`; after the
config file was restored, the retry completed with API RSS around 242 MiB.

## Artifacts

| Benchmark | Summary JSON |
|---|---|
| Smoke | `results/smoke_shisad_2026-05-22T085111Z_fedddac4_2f10793a/summary.json` |
| Lifecycle | `results/lifecycle_shisad_2026-05-22T085126Z_8a5459fa_542a1eaf/summary.json` |
| LongMemEval-S | `results/longmemeval_shisad_2026-05-22T085432Z_c2b2e1b9_800ed82c/summary.json` |
| LongMemEval-M | `results/longmemeval_shisad_2026-05-22T101540Z_0af49665_9b4935e8/summary.json` |
| LoCoMo, Category 5 excluded | `results/locomo_shisad_2026-05-22T103018Z_81c1acc9_841a2dc8/summary.json` |
| LoCoMo, Category 5 included | `results/locomo_shisad_2026-05-22T142704Z_44c42ac9_9aecaa98/summary.json` |
| Memobase LoCoMo, Category 5 excluded | `results/locomo_memobase_2026-05-23T113004Z_da4137bd_3f8197a2/summary.json` |
| Memobase LoCoMo, Category 5 included | `results/locomo_memobase_2026-05-24T065520Z_8d3e8ce7_117d42e7/summary.json` |

## Dataset Provenance

| Dataset | Fixture Hash | Notes |
|---|---|---|
| Smoke | `abade026dfb5139626fcfbfe8fc629e70e38af270fb4ea6dd0a5fecc4fe1a6b3` | dev smoke fixture |
| Lifecycle (smoke) | `0a77c0d9e4d4f853c15276d09ec60ee162e2b0dc649d504045ac7daf88b00393` | `lifecycle-v4` dev smoke fixture (7 cases) |
| Lifecycle (full, source fixture) | `e8c724cf145e46434ef89e73d3998bbe30a44405ccac16d1c1c97f7de3307ad5` | `lifecycle-v4` dev full fixture before report-time `top_k` substitution (217 cases) |
| Lifecycle (full, `top_k=3` report fixture) | `bdafd94b1567652c24cdcb2c924f1bde9b08fc7daed5f05092d9a74c6ac0a2e6` | Hash used by the Memobase and shisad `lifecycle-v4` full artifacts above |
| LongMemEval-S | `421c7b35cad5fd61387bd9c9a442edd3a71aae49f7ab2502f552f075fb3c94e7` | 500 questions, 62 sessions |
| LongMemEval-M | `36c92293cb31ae483bc619eb57541302f941cdd50c7709d7e2c95cbf61fc7ad1` | 500 questions, 487 sessions |
| LoCoMo, Category 5 excluded | `2132c1bc6285ab0434dd714ae6062dd5b1875050e4aba8916e3626e7305c90e1` | 1540 questions, 446 Category 5 questions excluded |
| LoCoMo, Category 5 included | `5f1781dffe14ce202f15e16697eb4277527f3349c6527fc9b652546855e81c3f` | 1986 questions |
| Memobase LoCoMo, Category 5 excluded | `825e514e95d0b23a4c725033705bc017bdf80947dfdee823888e6eedd95b5a01` | 10 conversation cases, 1540 questions, 446 Category 5 questions excluded |
| Memobase LoCoMo, Category 5 included | `4670ccfe62f36c54f67e520f8d275d3e6fdfd660bf15f91f591c0c54f42eb3b9` | 10 conversation cases, 1986 questions |

## Methodology Notes

The shisad runs in this table use:

- **Embedding mode:** `deterministic` (`shisad-deterministic-sha256`)
- **Judge:** `deterministic`; no external LLM judge
- **Contract version:** `b2`
- **Split:** `dev`
- **Runs:** 1, so all results are `preliminary`
- **Case IO:** `--no-store-case-io` to keep report memory usage bounded
- **Resource limits:** SUT timeout 120s and memory limit 8192 MB for full suites

The Memobase runs use OpenAI `text-embedding-3-small` for retrieval indexing
and query embedding, with deterministic MELT scoring over returned evidence.
They do not use an external LLM judge.

Harness hardening used for these runs includes streaming LongMemEval fixtures,
per-case checkpoints, optional omission of heavy case IO, and optional per-case
SUT restarts. The LongMemEval-M and LoCoMo runs used
`--restart-sut-per-case` to bound SUT RSS growth after an earlier session crash.
The 2026-05-22 shisad LoCoMo artifacts used the legacy one-question-per-case
fixture shape. Current MELT defaults LoCoMo external/full fixtures to
conversation-level cases, so the reproduction commands below include
`--case-granularity qa` for exact historical reproduction.

Smoke and Lifecycle report a retrieval bypass warning because `top_k` is greater
than or equal to the number of sessions. Their retrieval scores are useful for
sanity checks, not competitive comparison.

LoCoMo reports the benchmark audit caveat that score differences under 5
percentage points are non-decisive. The Category 5 included run is explicit
opt-in; published LoCoMo results often exclude this adversarial category.

## External Reference Targets

These are not MELT runs; they are upstream published artifacts used as
ballpark references for future adapter validation.

| System | Benchmark | Protocol | Published / Recomputed Score | Notes |
|---|---|---|---:|---|
| Memobase v0.0.37 | LoCoMo, Category 5 excluded | Memobase context + GPT-4o answer generation + LLM judge | 0.7578 | Recomputed from upstream `memobase_eval_0710_3000.json`; category scores: single-hop 0.7092, temporal 0.8505, multi-hop 0.4688, open-domain 0.7717. |

The Memobase reference is end-to-end QA accuracy, not retrieval R@k/nDCG. It is
therefore a target for validating a comparable QA-judge path, not a direct
comparison against the current deterministic retrieval-only shisad table above.

## Reproduction Commands

```bash
SUT='uv --directory /path/to/shisad run shisad memory sut'

uv run melt run \
  --sut shisad \
  --sut-command "$SUT" \
  --suite smoke \
  --fixture smoke \
  --output-dir results \
  --no-store-case-io \
  --override sut.timeout_seconds=60 \
  --override sut.resource_limits.memory_mb=8192

uv run melt run \
  --sut shisad \
  --sut-command "$SUT" \
  --suite lifecycle \
  --fixture smoke \
  --top-k 3 \
  --output-dir results \
  --no-store-case-io \
  --override sut.timeout_seconds=60 \
  --override sut.resource_limits.memory_mb=8192

uv run melt run \
  --sut shisad \
  --sut-command "$SUT" \
  --suite longmemeval \
  --variant S \
  --fixture full \
  --dataset-path data/longmemeval_s_cleaned.json \
  --top-k 5 \
  --output-dir results \
  --no-store-case-io \
  --override sut.timeout_seconds=120 \
  --override sut.resource_limits.memory_mb=8192

uv run melt run \
  --sut shisad \
  --sut-command "$SUT" \
  --suite longmemeval \
  --variant M \
  --fixture full \
  --dataset-path data/longmemeval_m_cleaned.json \
  --top-k 5 \
  --output-dir results \
  --no-store-case-io \
  --restart-sut-per-case \
  --override sut.timeout_seconds=120 \
  --override sut.resource_limits.memory_mb=8192

uv run melt run \
  --sut shisad \
  --sut-command "$SUT" \
  --suite locomo \
  --fixture full \
  --dataset-path data/locomo10.json \
  --audit-catalog-path data/locomo-errors.json \
  --case-granularity qa \
  --top-k 5 \
  --output-dir results \
  --no-store-case-io \
  --restart-sut-per-case \
  --override sut.timeout_seconds=120 \
  --override sut.resource_limits.memory_mb=8192

uv run melt run \
  --sut shisad \
  --sut-command "$SUT" \
  --suite locomo \
  --fixture full \
  --dataset-path data/locomo10.json \
  --audit-catalog-path data/locomo-errors.json \
  --include-category-5 \
  --case-granularity qa \
  --top-k 5 \
  --output-dir results \
  --no-store-case-io \
  --restart-sut-per-case \
  --override sut.timeout_seconds=120 \
  --override sut.resource_limits.memory_mb=8192
```

Full report JSON artifacts are written to `results/` with provenance metadata
for independent verification.
