# Related work and novelty boundary

ReproCheck does not claim to invent computational reproducibility. Its narrower
contribution is a deterministic claim-to-evidence audit that combines numerical
recomputation, split/notebook checks, provenance, and a machine-verifiable graph
inside one certificate.

| Work | Primary purpose | Difference from ReproCheck |
| --- | --- | --- |
| [NeurIPS reproducibility program](https://www.jmlr.org/papers/v22/20-303.html) | Policies, code submission, challenge, and checklist | Primarily procedural and human-reviewed; it does not issue ReproCheck's claim-level artifact graph |
| [ReproZip](https://doi.org/10.1145/2882903.2899401) | Capture and package the execution environment and provenance | Stronger for portable re-execution; ReproCheck instead checks declared claims, metrics, splits, and certificate relations |
| [Whole Tale](https://arxiv.org/abs/1805.00400) | Publish executable research objects combining data, code, environment, and narrative | Broader infrastructure for living publications; ReproCheck is a smaller local auditor and certificate format |
| [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current) | Human evaluation of artifact availability, functionality, reuse, and reproduced results | ReproCheck can provide machine-checkable evidence to a reviewer but cannot grant a badge or replace independent evaluation |

The defensible novelty claim is therefore not "the first reproducibility tool."
It is:

> A typed and integrity-checked claim-to-evidence graph that records how supplied
> computational artifacts support, contradict, or fail to verify numerical
> research claims, with deterministic checks for selected leakage classes.

This novelty is architectural and methodological. A literature review cannot by
itself prove worldwide priority, and the project must avoid wording such as
"unique in the world" unless a formal prior-art search supports it.
