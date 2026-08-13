# Prospective upstream-correction discovery protocol v3

Status at registration: **retrieval not started; candidates and labels unseen**.

This study is a new source-unseen test of ReproCheck 0.19.0 on public,
naturally occurring corrections to numeric benchmark or evaluation claims. The
queries, exclusion universe, sampling rule, eligibility rule, evaluator wheel,
and outcomes are fixed before the first v3 GitHub API request.

## Frozen evaluator

- Source repository: `https://github.com/nazkari86-lab/reprocheck`.
- Evaluator commit: `7e5a6c087fc6f5e5df14ccde1c8436049c39c5b7`.
- Release/tag: `0.19.0` / `v0.19.0`.
- Wheel: `evaluator/reprocheck-0.19.0-py3-none-any.whl`.
- Wheel SHA-256:
  `fb76d6ae2d9cfe6a2400e3b5be68525d54d87041f17aa3c80ad50e4233697c8e`.
- Dependency graph: `uv.lock` at the evaluator commit.

The wheel must be executed in an isolated environment for the single zero-shot
evaluation. The current source tree may not substitute for it.

## Prior-exposure exclusions

Before sampling, exclude every pull-request identity present in any of these
already inspected or previously retrieved files:

1. `../upstream_discovery_v2/frames.json`, SHA-256
   `7e2ba1e5758ae6ec2114b86bbc9e747e9a47b3fa21b5dbcdcbad7d6b67371b30`;
2. `../upstream_corrections/discovery_snapshot.json`, SHA-256
   `048ae9ca1d972d5f2998aee996dfd3010ea36d940b98a73d65dffaf148c36a0a`;
3. `../upstream_corrections/manifest.json`, SHA-256
   `d07dfec9bb9e4c83673f58051bb8108f7219d9a03562db32a0692344e61d3ed0`.

Exclusion depends only on repository and pull-request number, never on parser
output or v3 eligibility.

## Retrieval frames

Run these GitHub searches exactly once, in order, through the authenticated
GitHub search API:

1. `"fix benchmark results" in:title,body is:merged`
2. `"benchmark numbers" in:title,body is:merged`
3. `"stale benchmark" in:title,body is:merged`
4. `"benchmark typo" in:title,body is:merged`
5. `"incorrect results" benchmark in:title,body is:merged`

Request at most 100 results per query. Preserve the unmodified response bytes
and their SHA-256 digests. Deduplicate by assigning a pull request to the first
frame in which it appears, after applying the frozen prior-exposure exclusions.

## Deterministic sample

For every remaining candidate compute:

`SHA256("reprocheck-upstream-v3|<repository>#<pull-request-number>")`.

Sort each frame by that digest ascending and select the first 30 candidates, or
all candidates if fewer remain. No discretionary substitution is allowed. The
maximum sample is 150 pull requests.

## Eligibility labels

Inspect every sampled pull request without running either the frozen wheel or
the development parser. A case is eligible only when all conditions hold:

1. GitHub reports the pull request as merged.
2. It corrects a pre-existing human-readable numeric benchmark or evaluation
   claim rather than adding a new benchmark.
3. An immutable parent/merge file pair contains both old and corrected claims.
4. Old and corrected values refer to the same metric, dataset, model or system,
   configuration, and evaluation setting.
5. The correction is not merely a result refresh after an intentional code,
   dependency, dataset, or configuration change.
6. The case is natural, not described as injected, generated, toy,
   mutation-test, or synthetic-only.
7. It is not a duplicate publication of another eligible underlying correction
   in this v3 sample.

Every ineligible PR receives one primary exclusion reason. Every eligible case
records all corrected numeric claims in the immutable pair. Parser visibility
is not an eligibility condition.

## Frozen outcomes

Primary outcome: exact case visibility, the proportion of eligible corrections
for which frozen 0.19.0 extracts every selected old and new claim with the
expected canonical metric and numeric value.

Secondary outcomes:

- exact claim visibility;
- Wilson 95% confidence intervals;
- eligible-case yield;
- repository and independent-owner breadth;
- format and metric-family breadth;
- count and agreement rate of cases with independently frozen raw experimental
  evidence.

The zero-shot result and its lock must be committed before any parser change
informed by v3. Later fixes form a separately labeled development result and
must retain every frozen failure.

## Interpretation boundary

The deterministic sample controls selection discretion inside five frozen,
query-conditioned frames. It is not a probability sample of GitHub, scientific
software, or defects. Confidence intervals describe the sampled frame only and
must not be presented as global prevalence or universal recall.
