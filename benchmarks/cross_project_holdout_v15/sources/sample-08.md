# Evaluation Results

## Release snapshot

This page reports only real schema-v2 artifacts generated during the recorded
release run. The reports identify a dirty working tree at their evaluation
timestamps, so their embedded provenance and hashes—not the revision alone—are
the source of truth. Lexical, vector, and hybrid retrieval were measured on the
same development and frozen holdout datasets. Lexical required no external
service; vector and hybrid used the configured embedding provider and live Qdrant
collection. The canonical lexical artifacts are:

- [Development lexical report (JSON)](../data/evaluation/retrieval_eval_development_lexical_report.json)
  and [human-readable report](../data/evaluation/retrieval_eval_development_lexical_report.md)
- [Holdout lexical report (JSON)](../data/evaluation/retrieval_eval_holdout_lexical_report.json)
  and [human-readable report](../data/evaluation/retrieval_eval_holdout_lexical_report.md)

The unsuffixed `retrieval_eval_report.{json,md}` files are exact compatibility
mirrors of the development lexical report. Byte-for-byte comparison confirms
that they do not represent a third run, a different retrieval mode, or additional
experimental evidence.

Both runs used `top_k=8`, `candidate_k=30`, deterministic post-ranking, revision
`b1ed1174ade3`, and a dirty working tree. The dirty flag matters: the revision
alone does not identify the evaluated code, so the report artifacts and hashes
must remain with the submission.

## Retrieval quality

Hit@K and MRR use **supported questions only**. Unsupported questions are a
separate diagnostic denominator and never count as source-ranking misses.

| Metric | Development | Frozen holdout |
| --- | ---: | ---: |
| Total questions | 40 | 26 |
| Supported denominator | 30 | 13 |
| Unsupported diagnostic denominator | 10 | 13 |
| Supported Hit@1 | 0.7333 | 0.6154 |
| Supported Hit@3 | 0.9000 | 0.7692 |
| Supported Hit@5 | 0.9000 | 0.9231 |
| Supported MRR | 0.8000 | 0.7179 |
| Supported expected-source match within top 8 | 0.9000 | 0.9231 |
| Internal preference rate | 0.8095 | 0.5000 |

The default strict gate is `supported_hit_at_3 >= 0.85`. Development passed at
`0.9000`. Holdout failed at `0.7692`, a gap of `0.0808` below the threshold. The
failure is preserved as a release finding rather than hidden by retuning on the
holdout.

Holdout Hit@5 (`0.9231`) is materially higher than Hit@3 (`0.7692`). In this
small internal benchmark, lexical search often finds the expected source but
does not consistently rank it in the first three positions. That supports a
ranking-improvement hypothesis; it does not prove an answer-quality outcome.

### Current mode comparison

| Mode | Split | Hit@1 | Hit@3 | Hit@5 | MRR | `Hit@3 >= 0.85` |
|---|---|---:|---:|---:|---:|---|
| Lexical | Development | 0.7333 | 0.9000 | 0.9000 | 0.8000 | pass |
| Lexical | Holdout | 0.6154 | 0.7692 | 0.9231 | 0.7179 | **fail** |
| Vector | Development | 0.9000 | 0.9333 | 0.9667 | 0.9250 | pass |
| Vector | Holdout | 0.6923 | 0.9231 | 0.9231 | 0.8077 | pass |
| Hybrid | Development | 0.8667 | 0.9000 | 0.9667 | 0.8975 | pass |
| Hybrid | Holdout | 0.7692 | 0.8462 | 0.8462 | 0.8205 | **fail by 0.0038** |

Evidence: [development vector](../data/evaluation/retrieval_eval_development_vector_report.md),
[holdout vector](../data/evaluation/retrieval_eval_holdout_vector_report.md),
[development hybrid](../data/evaluation/retrieval_eval_development_hybrid_report.md),
and [holdout hybrid](../data/evaluation/retrieval_eval_holdout_hybrid_report.md).

Vector is the strongest current holdout mode by Hit@3. Hybrid's higher holdout
Hit@1 and MRR do not offset its two expected sources missing the top five. This is
why the release does not claim that RRF automatically improves every metric. No
rules or thresholds were tuned from the holdout result.

## Unsupported retrieval diagnostics

| Diagnostic | Development | Frozen holdout |
| --- | ---: | ---: |
| Non-empty retrieval rate | 1.0000 | 1.0000 |
| Average top normalized lexical score | 1.0000 | 1.0000 |
| Average top adjusted score | 0.9861 | 1.0204 |
| Questions with a vector score | 0 | 0 |
| Average top vector similarity | n/a | n/a |
| Low-confidence vector rate | n/a | n/a |

A non-empty candidate list is normal for a ranker and is not a false answer.
The answerability and guardrail layers decide whether the API refuses. The top
normalized lexical score is always relative to each query, so `1.0000` is not a
confidence probability. Vector diagnostics are intentionally unavailable rather
than being calculated from lexical or adjusted values.

No supported question in either dataset currently has an `expected_pages`
label. Consequently, `supported_expected_page_match_rate` is `null`, with an
explicit denominator of zero; it is not a perfect page-match result.

## Timing

These timings describe this local offline run and are not a service-level claim.

| Metric (milliseconds) | Development | Frozen holdout |
| --- | ---: | ---: |
| Average retrieval latency | 68 | 77 |
| p50 retrieval latency | 56 | 57 |
| p95 retrieval latency | 117 | 120 |
| Average lexical stage | 62 | 71 |

The first query includes lexical-index construction; subsequent queries reuse
the process cache. Latency comparisons therefore depend on process lifetime,
hardware, file cache state, and dataset order.

## Provenance

| Field | Development | Frozen holdout |
| --- | --- | --- |
| Evaluated at (UTC) | `2026-07-10T16:54:21Z` | `2026-07-10T16:54:27Z` |
| Dataset | `data/evaluation/questions_development.jsonl` | `data/evaluation/questions_holdout.jsonl` |
| Dataset SHA-256 | `d073cc9867c255f14a9bd10c416e2f037949b50742c22586f46c02e7719b49e0` | `78c242e9a1a653b200073afb1048cdc741376c5f344121f81ead7718f079b561` |
| Dataset size | 40 | 26 |
| Evaluated size | 40 | 26 |
| Chunk corpus | `data/processed/chunks.jsonl` | `data/processed/chunks.jsonl` |
| Chunk SHA-256 | `ae80f2bb984477c5d670c867a157b30516231eac231c066965c50e0db92f5bb3` | `ae80f2bb984477c5d670c867a157b30516231eac231c066965c50e0db92f5bb3` |
| Base score semantics | normalized lexical ranking score | normalized lexical ranking score |
| Adjusted score semantics | deterministic post-ranking score | deterministic post-ranking score |

The development set was visible during implementation. The holdout is frozen
for this snapshot, but it is still an internal, author-created split rather than
an external blinded benchmark. Its 13 supported questions also make every miss
large (approximately 0.0769 of the rate), so avoid over-interpreting small
differences.

## Live infrastructure and API status

Current live validation confirmed a green Qdrant collection
with 279 stored 1,536-dimensional cosine vectors, valid sample citation payloads,
and no need to reindex. An isolated loopback API reported Qdrant and temporary
SQLite health `ok`. The repository smoke suite passed 12/12 checks, including a
real supported answer, ordinary out-of-scope handling, true SSE deltas, feedback,
statistics, request compatibility, source metadata, and PDF `HEAD`/`GET`.

A separate live Serbian hybrid conversation produced a cited Figma answer in
7.488 seconds, persisted chronological `user`/`assistant` roles, and used that
history for a cited follow-up in 6.396 seconds. A Serbian prompt-extraction attempt
was blocked in 6 milliseconds with no retrieval or LLM call. These are targeted
runtime smokes, not an aggregate answer-quality benchmark or browser-modal proof.

## Serbian multilingual development smoke

The 11-question supported-only Serbian set (Latin and Cyrillic) was executed through
the normal evaluation runner after bounded English domain-alias expansion in all
three retrieval modes:

| Mode | Questions | Hit@1 | Hit@3 | Hit@5 | MRR | Gate |
|---|---:|---:|---:|---:|---:|---|
| Lexical | 11 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | pass |
| Vector | 11 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | pass |
| Hybrid | 11 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | pass |

Evidence: [Serbian lexical report](../data/evaluation/retrieval_eval_serbian_lexical_report.md)
plus [vector](../data/evaluation/retrieval_eval_serbian_vector_report.md) and
[hybrid](../data/evaluation/retrieval_eval_serbian_hybrid_report.md) reports.

This is a deliberately domain-aligned development smoke, not a frozen Serbian
holdout, not answer-quality evidence, and not proof that arbitrary Serbian wording
will retrieve correctly.

## DeepEval answer-evaluation status

DeepEval `4.1.0` is integrated with standard Answer Relevancy, Faithfulness,
Contextual Relevancy, and G-Eval scope metrics plus a custom deterministic Response
Contract metric. The judge adapter reuses the provider-agnostic OpenAI-compatible
configuration and DeepEval cloud upload/tracing/telemetry are disabled for repository
runs.

The real contract-only security suite executed six English/Serbian prompt-extraction,
control-bypass, and state-assignment cases through the bound API:

| Cases | Contract pass rate | Application LLM calls | Judge calls | Average / p95 latency |
|---:|---:|---:|---:|---:|
| 6 | 1.0000 | 0 | 0 | 2 ms / 10 ms |

Evidence: [DeepEval security contract report](../data/evaluation/deepeval_security_contract_report.md)
and [JSON](../data/evaluation/deepeval_security_contract_report.json).

This proves the local DeepEval custom-metric integration and narrow security boundary;
it is not semantic answer-quality evidence. No aggregate judge-backed development or
holdout report is claimed. Those runs require explicit approval for the configured
judge endpoint to receive questions, generated answers, and selected knowledge-base
chunk text. Fabricated or partial semantic scores were not substituted. A prior real
Chrome startup passed, but the final supported Figma source/feedback modal interaction
was not completed in a browser.

Deterministic service-level regression coverage does exercise the exact two-turn
malware continuation through the ASGI application, temporary SQLite storage, and
the production answer service. It verifies pre-retrieval dialogue resolution,
contextual retrieval, grounded security citations, state transitions, strict
domain switches, and failed/cancelled-stream persistence using controlled fake
search and LLM providers. This is automated contract evidence, not a live browser
or bound-port smoke test, not evidence from a real external LLM, and not an
answer-evaluation report. See `tests/test_dialogue_followup_api.py`.

Reproduce the semantic DeepEval run in two terminals after configuring the application
and an approved OpenAI-compatible judge:

```bash
# Terminal 1: isolate evaluation persistence from the repository database.
API_DATABASE_PATH=/tmp/comtrade-answer-eval.sqlite \
RETRIEVAL_MODE=lexical \
.venv/bin/uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

```bash
# Terminal 2: do not add --limit to a release run.
.venv/bin/python -m src.evaluation.run_eval \
  --mode deepeval --split development --retrieval-mode vector \
  --base-url http://127.0.0.1:8000

.venv/bin/python -m src.evaluation.run_eval \
  --mode deepeval --split holdout --retrieval-mode vector \
  --base-url http://127.0.0.1:8000
```

These commands may consume both application and judge LLM usage. Expected output
paths include the split and retrieval mode. Review application/judge identities,
failed IDs, response modes, faithfulness/relevancy reasons, citation leakage, and
strict gates before promoting reports.

## Why older numbers are not compared

The earlier methodology mixed supported and unsupported questions in retrieval
denominators. Unsupported prompts intentionally have no expected source, so that
calculation conflated ranking misses with refusal cases. It also did not provide
the same split and score-semantics provenance. Schema v2 fixes the denominator,
keeps unsupported signals diagnostic-only, and records hashes and runtime
requirements. The old contaminated numbers are therefore not an apples-to-apples
baseline and should not be used to claim an improvement or regression.

For definitions and exact commands, see [Evaluation Methodology](EVALUATION.md).
