# Prospective upstream-correction discovery protocol v2

Status at registration: **retrieval not started; labels unseen**.

This study estimates ReproCheck's parser visibility on a prospectively sampled
set of public pull requests that may contain natural benchmark-report
corrections. Eligibility is decided without using ReproCheck's output. This
prevents the circular rule in which a correction enters the benchmark only when
the current parser can already read it.

## Frozen evaluator

- Source repository: `https://github.com/nazkari86-lab/reprocheck`.
- Evaluator commit: `2618cad2c54c1610947f4f64e4b7ba8c5302fa28`.
- Package version: `0.18.0`.
- Dependency graph: the `uv.lock` committed at the evaluator revision.
- The zero-shot result must be produced from this revision before any parser
  change based on the sampled pull requests.

## Retrieval frames

Run these GitHub pull-request searches exactly once, in the listed order, using
GitHub CLI's authenticated search API on the retrieval date:

1. `"incorrect benchmark" in:title,body is:merged`
2. `"wrong benchmark" in:title,body is:merged`
3. `"correct benchmark" in:title,body is:merged`

Request at most 100 results per query. Preserve every returned repository, pull
request number, URL, title, creation time, merge time, and query-frame index.
The raw API response and its SHA-256 digest must be committed unchanged.

## Deterministic sample

Deduplicate a pull request appearing in more than one frame by assigning it to
the earliest frame. For each remaining candidate compute:

`SHA256("reprocheck-upstream-v2|<repository>#<pull-request-number>")`.

Within each frame, sort by this digest ascending and select the first 25
candidates, or all candidates if fewer than 25 remain. This produces at most 75
sampled pull requests without discretionary rank selection.

## Eligibility labels

Inspect every sampled pull request. A case is eligible when all conditions hold:

1. GitHub confirms that the pull request was merged.
2. The pull request corrects a pre-existing human-readable numeric benchmark or
   evaluation claim; it does not merely add a new benchmark or refresh a result
   after an intentional code/configuration change.
3. An immutable parent/merge file pair contains the old and corrected claim.
4. The old and corrected values refer to the same semantic metric, dataset,
   model/configuration, and evaluation setting.
5. The correction is natural: the project does not describe the evaluated data
   or defect as an injected, generated, mutation-test, toy, or synthetic-only
   case.
6. It is not a duplicate publication of an already eligible underlying
   correction in this sample.

Parser visibility is deliberately **not** an eligibility condition. Every
ineligible result receives one primary exclusion reason. Every eligible result
records all corrected claims visible in the immutable pair, even if the frozen
evaluator extracts none of them.

## Frozen outcomes

Primary outcome: case-level exact visibility — the fraction of eligible pull
requests for which the frozen evaluator extracts every selected old and new
claim with the correct canonical metric and numeric value.

Secondary outcomes:

- claim-level exact visibility;
- 95% Wilson confidence intervals for both proportions;
- eligible-case yield among sampled pull requests;
- repository and organization breadth;
- count and agreement rate of independently available raw-evidence cases.

No parser modifications are allowed before the zero-shot result JSON and its
SHA-256 digest are committed. Later fixes are a separate development result and
must retain the frozen zero-shot failures.

## Interpretation boundary

The deterministic sample controls discretionary selection inside three frozen
search frames. It is not a probability sample of all GitHub repositories, all
research reports, or all defects. Its confidence intervals describe only the
sampled candidate frame; they do not estimate global defect prevalence.
