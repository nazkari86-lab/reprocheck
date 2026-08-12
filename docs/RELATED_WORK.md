# Related work and novelty boundary

ReproCheck does not claim to invent computational reproducibility, static data
leakage analysis, provenance, or evidence graphs. Its narrower contribution is
a deterministic claim-to-evidence audit that combines numerical recomputation,
concrete split checks, bounded notebook analysis, provenance, and an
integrity-checked graph inside one certificate.

## Closest leakage analyzers

| Work | Documented focus | Evaluation reported by its authors | Boundary relative to ReproCheck |
| --- | --- | --- | --- |
| [Yang et al., *Data Leakage in Notebooks: Static Detection and Better Processes* (ASE 2022)](https://arxiv.org/abs/2209.03345) | Static data-flow rules for preprocessing, overlap, and repeated test use | More than 100,000 public notebooks | Much broader empirical notebook-leakage study; ReproCheck's notebook checks are narrower and are only one layer of a claim-to-artifact audit |
| [Subotic et al., *A Static Analysis Framework for Data Science Notebooks* (ICSE-SEIP 2022)](https://www.microsoft.com/en-us/research/wp-content/uploads/2022/05/ICSE.pdf) | NBLyzer framework for notebook-aware abstract interpretation and several analyses | 2,211 notebooks; 98.7% analyzed within one second | Stronger formal notebook-analysis framework; ReproCheck instead combines bounded AST signals with supplied-file checks, metric recomputation, and certificates |
| [Drobnjakovic et al., *Abstract Interpretation-Based Data Leakage Static Analysis*](https://arxiv.org/abs/2211.16073) | Formal concrete and abstract leakage semantics implemented in NBLyzer | More than 2,000 Kaggle notebooks | Stronger formal leakage semantics; ReproCheck does not claim sound static proof of general leakage absence |
| [Truong et al., *LeakageDetector*](https://arxiv.org/abs/2503.14723) and [LeakageDetector 2.0](https://arxiv.org/abs/2509.15971) | IDE detection and repair guidance for overlap, preprocessing, and multi-test leakage | Tool-oriented ML pipeline and notebook evaluation | Stronger interactive remediation focus; ReproCheck's distinctive output is a cross-artifact claim audit and integrity certificate, not an IDE quick fix |

These systems invalidate any claim that ReproCheck invented automatic leakage
detection. They also show that ReproCheck's AST risk rules must not be described
as a complete, sound, or state-of-the-art notebook analyzer without a direct
head-to-head benchmark.

## Reproducibility and provenance systems

| Work | Primary purpose | Boundary relative to ReproCheck |
| --- | --- | --- |
| [NeurIPS reproducibility program](https://www.jmlr.org/papers/v22/20-303.html) | Policies, code submission, challenge, and checklist | Primarily procedural and human-reviewed; it does not issue ReproCheck's claim-level artifact graph |
| [ReproZip](https://doi.org/10.1145/2882903.2899401) | Capture and package the execution environment and provenance | Stronger for portable re-execution; ReproCheck instead checks declared claims, metrics, splits, and certificate relations without executing uploaded code |
| [Whole Tale](https://arxiv.org/abs/1805.00400) | Publish executable research objects combining data, code, environment, and narrative | Broader infrastructure for living publications; ReproCheck is a smaller local auditor and certificate format |
| [W3C PROV](https://www.w3.org/TR/prov-overview/) | General interoperable provenance data model | Broader provenance vocabulary; ReproCheck defines a narrower audit-specific graph and does not claim to replace PROV |
| [Research Object Crate](https://www.researchobject.org/ro-crate/specification/1.1/) | Package research data with structured metadata | Stronger packaging/interchange standard; ReproCheck verifies selected numerical support and integrity relations |
| [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current) | Human evaluation of artifact availability, functionality, reuse, and reproduced results | ReproCheck can provide machine-checkable evidence to a reviewer but cannot grant a badge or replace independent evaluation |

## Capability matrix

The entries below describe each work's primary documented scope, not every
possible extension or integration. `Partial` means the capability exists only
for a declared subset or serves a different primary purpose.

| System | Numerical claim link | Metric recomputation | Concrete split overlap | Static notebook leakage | Environment capture | Integrity graph/certificate |
| --- | --- | --- | --- | --- | --- | --- |
| Yang et al. | No | No | Partial | Yes | No | No |
| NBLyzer / abstract interpretation | No | No | Partial | Yes | No | No |
| LeakageDetector | No | No | Partial | Yes | No | No |
| ReproZip | No | No | No | No | Yes | Partial provenance |
| Whole Tale | Partial narrative link | No | No | No | Yes | Partial provenance |
| W3C PROV / RO-Crate | Schema-dependent | No | No | No | Partial | Provenance/metadata, not a ReproCheck audit certificate |
| ReproCheck | Yes, declared metrics | Yes, selected tasks | Yes, supplied files | Partial bounded rules | No | Yes, audit-specific |

## Defensible novelty statement

The defensible novelty claim is not "the first reproducibility tool," "the
first leakage detector," or "the first evidence graph." It is:

> A typed and integrity-checked claim-to-evidence graph that records how
> supplied computational artifacts support, contradict, or fail to verify
> selected numerical research claims, combining deterministic recomputation and
> bounded leakage checks without executing submitted code.

This is an architectural and methodological contribution. The evidence-layer
ablation evaluates which inconsistency families become observable as those
inputs are added. A literature review cannot prove worldwide priority, and the
project must avoid wording such as "unique in the world" unless a formal
prior-art search supports it.

## Minimal witness boundary

Version 0.17 does not claim to invent minimal provenance explanations. Database
provenance literature already formalizes why/why-not explanations and minimal
witness bases; for example, Green describes the minimal witness basis as an
irredundant family of contributing source sets, while PUG computes the relevant
part of a provenance graph for a why/why-not question:

- [Green, *Containment of Conjunctive Queries on Annotated Relations*, ICDT
  2009](https://openproceedings.org/2009/conf/icdt/Green09.pdf)
- [Lee, Ludäscher, Glavic, *PUG: Why & Why-Not Provenance*,
  2018](https://arxiv.org/abs/1808.05752)

ReproCheck's narrower contribution is an executable verifier rule for one
audit-specific contradiction: bind a numerical report claim and conflicting
metric observation to their exact source artifacts, preserve their typed graph
relations and digests, and independently repeat a cardinality-minimal grounding
search against the original sealed audit certificate. The controlled benchmark
supports that implementation boundary only. It does not establish a new general
theory of provenance minimization.
