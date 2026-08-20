# Scientific and engineering scorecard

ReproCheck does not use a single blended score. A perfect engineering result
cannot substitute for representative scientific evidence, and a strong
benchmark cannot substitute for a reproducible package. Each dimension is
reported against an explicit gate.

v19 status: protocol/scaffold only; no scored external result. The registered
trial is designed to test whether raw-artifact recomputation improves contradiction
recall at a <=5% false-accusation gate. It does not yet establish that claim.

## Local engineering readiness

| Gate | Requirement | Current evidence | Status |
| --- | --- | --- | --- |
| Determinism | Repeated runs produce stable certificates and results | deterministic test and benchmark gates | PASS |
| Source integrity | Every natural-corpus input has an immutable URL and locked SHA-256 | 56/56 upstream files across both natural corpora | PASS |
| Parser coverage | Recover every selected corrected claim with the expected canonical metric and value | 71/71 development-visible claims across Markdown, YAML, JSON, JSONL, prose, TSX, TOML, Python, and COCO text | PASS |
| Natural corrections | Use real merged corrections, not injected defects, for primary evidence | 20/20 independent pull-request corrections | PASS |
| Raw evidence | Where immutable raw evidence is declared, verify it against the corrected claim | 6/6 declared raw-evidence cases | PASS |
| Selection transparency | Freeze retrieval and adjudicate every result before adding a discovery cohort | 25/25 earlier results plus 75/75 prospective results have a recorded decision | PASS |
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
| Real-error existence | 20 merged upstream corrections | 12 are retrospective; both discovery procedures are query-conditioned |
| Ecosystem breadth | 15 repositories, 12 independent owners | concentrated in technical benchmark reporting |
| Claim breadth | 71 selected numeric/name corrections | not all research-report formats |
| Independent raw evidence | 6 corrected cases agree with immutable evidence | 14 cases lack usable independently frozen raw evidence |
| Selection bias control | all 75 cases in the prospective sample were labeled without parser output | three search queries cannot represent GitHub or measure prevalence |
| Prospective zero-shot | frozen 0.18.0 recovered 0/3 eligible cases and 0/15 claims | eligible n=3; observed failures motivated parser development |
| Prospective development | same frozen cases recovered at 3/3 and 15/15 | post-inspection result; case Wilson 95% CI 43.85%-100% |
| Recall estimate | only query-frame conditional outcomes are reported | requires a larger probability sample or broader independent corpus |
| Human utility | protocol and tooling exist | no completed blinded human comparison is claimed |

Accordingly, the honest scientific result is not “10/10 universal validity.”
The strongest verified claim is narrower: on the combined frozen natural
corpora, the development parser recovers all 71 selected corrected claims,
validates all 56 immutable files, and matches all six declared raw-evidence
cases. The prospective zero-shot failure remains part of the result.
