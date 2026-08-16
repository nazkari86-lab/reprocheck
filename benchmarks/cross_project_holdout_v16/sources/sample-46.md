# pAI_Lang Benchmark Report

Created: `2026-07-19T07:32:39.621551+00:00`
Provider: `fixture`
Model: `n/a`
Evaluation tasks: **48**
Dataset hash: `bf462058903dd49f58d630f10135b0936606a8edb6e11799a22a1d42f17fccf9`
Shots per prompt: **4**
Case order: `counterbalanced`
Repair attempts allowed: **0**
Registry: `1.0.0` / `c42daf112c6498ca140d5ae541bea0935c23cd31d99b846afc4044f0a9ff26b4`
pAI_Lang parser snapshot: `0.3.0` / `ba820cc5597dc24a73dd2d1adb17c3d73424809025ee66e72de30194c5138181`

## Format results

| Format | Cases | Provider errors | Syntax | Exact semantics | Structure | Action F1 | Mean chars | Prompt tokens | Completion tokens | Total tokens | Median latency ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| json_compact | 48 | 0.0% | 100.0% | 12.5% | 0.125 | 0.591 | 22.9 | 303.4 | 6.2 | 309.6 | 0.0 |
| json_verbose | 48 | 0.0% | 100.0% | 12.5% | 0.125 | 0.591 | 39.9 | 372.1 | 10.2 | 382.3 | 0.0 |
| keyword | 48 | 0.0% | 100.0% | 12.5% | 0.125 | 0.591 | 14.9 | 264.3 | 4.2 | 268.5 | 0.0 |
| pai | 48 | 0.0% | 100.0% | 12.5% | 0.125 | 0.591 | 5.0 | 276.2 | 2.0 | 278.2 | 0.0 |
| pai_shuffled | 48 | 0.0% | 100.0% | 12.5% | 0.125 | 0.591 | 5.0 | 276.2 | 2.0 | 278.2 | 0.0 |

## Paired exact comparisons

| Pair | Delta | Left-only correct | Right-only correct | McNemar exact p |
|---|---:|---:|---:|---:|
| json_compact_vs_json_verbose | +0.000 | 0 | 0 | 1.0000 |
| json_compact_vs_keyword | +0.000 | 0 | 0 | 1.0000 |
| json_compact_vs_pai | +0.000 | 0 | 0 | 1.0000 |
| json_compact_vs_pai_shuffled | +0.000 | 0 | 0 | 1.0000 |
| json_verbose_vs_keyword | +0.000 | 0 | 0 | 1.0000 |
| json_verbose_vs_pai | +0.000 | 0 | 0 | 1.0000 |
| json_verbose_vs_pai_shuffled | +0.000 | 0 | 0 | 1.0000 |
| keyword_vs_pai | +0.000 | 0 | 0 | 1.0000 |
| keyword_vs_pai_shuffled | +0.000 | 0 | 0 | 1.0000 |
| pai_vs_pai_shuffled | +0.000 | 0 | 0 | 1.0000 |

## Results by task family

| Family | json_compact | json_verbose | keyword | pai | pai_shuffled |
|---|---:|---:|---:|---:|---:|
| atomic | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| choice | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| conditional | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| fallback | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| mixed | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| parallel | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| repeat | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| sequence | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

## Novel composition

| Novelty | json_compact | json_verbose | keyword | pai | pai_shuffled |
|---|---:|---:|---:|---:|---:|
| seen | 22.2% | 22.2% | 22.2% | 22.2% | 22.2% |
| novel | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

## Failure sample

### `eval_sequence_01` / `json_verbose`

Request: Inspect the repository, then run the linter.

Error: `semantic_mismatch`

```text
{"op":"action","name":"inspect_repository"}
```

### `eval_sequence_01` / `pai_shuffled`

Request: Inspect the repository, then run the linter.

Error: `semantic_mismatch`

```text
T008.
```

### `eval_sequence_01` / `pai`

Request: Inspect the repository, then run the linter.

Error: `semantic_mismatch`

```text
T001.
```

### `eval_sequence_01` / `json_compact`

Request: Inspect the repository, then run the linter.

Error: `semantic_mismatch`

```text
{"a":"inspect_repository"}
```

### `eval_sequence_01` / `keyword`

Request: Inspect the repository, then run the linter.

Error: `semantic_mismatch`

```text
INSPECT_REPOSITORY
```

### `eval_sequence_02` / `pai_shuffled`

Request: Run the unit tests, then build the package.

Error: `semantic_mismatch`

```text
T006.
```

### `eval_sequence_02` / `pai`

Request: Run the unit tests, then build the package.

Error: `semantic_mismatch`

```text
T002.
```

### `eval_sequence_02` / `json_compact`

Request: Run the unit tests, then build the package.

Error: `semantic_mismatch`

```text
{"a":"run_unit_tests"}
```

### `eval_sequence_02` / `keyword`

Request: Run the unit tests, then build the package.

Error: `semantic_mismatch`

```text
RUN_UNIT_TESTS
```

### `eval_sequence_02` / `json_verbose`

Request: Run the unit tests, then build the package.

Error: `semantic_mismatch`

```text
{"op":"action","name":"run_unit_tests"}
```

### `eval_sequence_03` / `pai`

Request: Verify the artifact hashes, then archive the results.

Error: `semantic_mismatch`

```text
T006.
```

### `eval_sequence_03` / `json_compact`

Request: Verify the artifact hashes, then archive the results.

Error: `semantic_mismatch`

```text
{"a":"verify_artifact_hashes"}
```

### `eval_sequence_03` / `keyword`

Request: Verify the artifact hashes, then archive the results.

Error: `semantic_mismatch`

```text
VERIFY_ARTIFACT_HASHES
```

### `eval_sequence_03` / `json_verbose`

Request: Verify the artifact hashes, then archive the results.

Error: `semantic_mismatch`

```text
{"op":"action","name":"verify_artifact_hashes"}
```

### `eval_sequence_03` / `pai_shuffled`

Request: Verify the artifact hashes, then archive the results.

Error: `semantic_mismatch`

```text
T007.
```

### `eval_sequence_04` / `json_compact`

Request: Inspect the repository, run the unit tests, and then publish the report.

Error: `semantic_mismatch`

```text
{"a":"inspect_repository"}
```

### `eval_sequence_04` / `keyword`

Request: Inspect the repository, run the unit tests, and then publish the report.

Error: `semantic_mismatch`

```text
INSPECT_REPOSITORY
```

### `eval_sequence_04` / `json_verbose`

Request: Inspect the repository, run the unit tests, and then publish the report.

Error: `semantic_mismatch`

```text
{"op":"action","name":"inspect_repository"}
```

### `eval_sequence_04` / `pai_shuffled`

Request: Inspect the repository, run the unit tests, and then publish the report.

Error: `semantic_mismatch`

```text
T008.
```

### `eval_sequence_04` / `pai`

Request: Inspect the repository, run the unit tests, and then publish the report.

Error: `semantic_mismatch`

```text
T001.
```

## Interpretation boundary

This report measures command-generation behavior for a fixed vocabulary and exact semantic target. It does not establish execution safety, universal language superiority, or a performance gain in any external application.
