# Scientific and engineering scorecard

ReproCheck does not use a single blended score. A perfect engineering result
cannot substitute for representative scientific evidence, and a strong
benchmark cannot substitute for a reproducible package. Each dimension is
reported against an explicit gate.

## Local engineering readiness

| Gate | Requirement | Current evidence | Status |
| --- | --- | --- | --- |
| Determinism | Repeated runs produce stable certificates and results | deterministic test and benchmark gates | PASS |
| Source integrity | Every natural-corpus input has an immutable URL and locked SHA-256 | 40/40 upstream files verified by `sources.lock.json` | PASS |
| Parser coverage | Recover every selected corrected claim with the expected canonical metric and value | 56/56 claims across Markdown, YAML, JSONL, prose, and COCO text | PASS |
| Natural corrections | Use real merged corrections, not injected defects, for primary evidence | 17/17 independent pull-request corrections | PASS |
| Raw evidence | Where immutable raw evidence is declared, verify it against the corrected claim | 6/6 declared raw-evidence cases | PASS |
| Selection transparency | Freeze retrieval and adjudicate every result before adding a discovery cohort | 25/25 ranked search results have a decision; 5 included and 20 excluded | PASS |
| Negative controls | Preserve unchanged cases and known failures | controlled suites and documented zero-shot failures remain in the repository | PASS |
| Test quality | Enforce tests, types, lint, and at least 97% source coverage | `make gate` and CI | PASS when the referenced commit is green |
| Reproducible package | Build from the locked dependency graph and fixed source date | lock check, SBOM, wheel build, and clean-environment smoke gates | PASS when the referenced commit is green |
| Claim discipline | Separate natural evidence, controlled mutations, development data, and held-out data | corpus-specific boundaries in benchmark docs and result JSON | PASS |
| One-command replay | Reproduce the complete local evidence suite without manual edits | `make gate` | PASS when the referenced commit is green |

This table can support **10/10 local engineering readiness** only for a commit
whose complete local and GitHub gates pass. It does not imply 100% defect recall,
real-world prevalence, or superiority to every competing tool.

## External scientific validity

| Dimension | Verified result | Remaining limitation |
| --- | --- | --- |
| Real-error existence | 17 merged upstream corrections | first 12 retrospective; added cohort is still non-random |
| Ecosystem breadth | 12 repositories, 9 organizations | concentrated in technical benchmark reporting |
| Claim breadth | 56 selected numeric/name corrections | not all research-report formats |
| Independent raw evidence | 6 corrected cases agree with immutable evidence | 11 cases lack usable immutable raw evidence |
| Selection bias control | all 25 results of one frozen query adjudicated | one query cannot represent GitHub or measure prevalence |
| Recall estimate | not claimed | requires a prospectively sampled, exhaustively labeled corpus |
| Human utility | protocol and tooling exist | no completed blinded human comparison is claimed |

Accordingly, the honest scientific result is not “10/10 universal validity.”
The strongest verified claim is narrower: on this frozen natural corpus,
ReproCheck parses all 56 selected corrected claims, validates all immutable
sources, and matches all six declared raw-evidence cases.
