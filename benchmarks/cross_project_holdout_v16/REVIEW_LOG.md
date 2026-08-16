# V16 source-only screening log

This log records the first-pass eligibility review in global sample-rank order.
It is deliberately written before extracting claims with ReproCheck.  A
`candidate` has a plausible first, size-conforming result block; it is not an
eligible case until its line-level labels are independently written and checked
against the frozen public ontology.

| Rank | Disposition | Source-only reason |
|---:|---|---|
| 1 | excluded | The first detailed classification report has more than 20 scalar outcomes. |
| 2 | candidate | The first comparison table gives twelve explicit accuracy / macro-F1 outcomes. |
| 3 | excluded | Describes a system but provides no numeric result block. |
| 4 | candidate | The first timing table has four explicit mean-duration outcomes. |
| 5 | candidate | The first benchmark table contains explicit request rates and latency measurements. |
| 6 | candidate | The first console result contains throughput, latency, and success measurements. |
| 7 | excluded | The first table contains 50 timing cells, exceeding the 20-outcome limit. |
| 8 | excluded | Explicitly states that no authorized dataset / accuracy measurement exists. |
| 9 | excluded | Documentation and pending-review examples, rather than an empirical result block. |
| 10 | excluded | Release gates and quality targets are not measured public-ontology outcomes. |
| 11 | excluded | The first endpoint table exceeds the 20-outcome limit once latency outcomes are counted. |
| 12 | candidate | The recap table gives four request-rate and four p99-latency outcomes. |
| 13 | excluded | Benchmarking instructions contain no empirical measurements. |
| 14 | excluded | Descriptive accuracy/performance guidance, not a result block. |
| 15 | excluded | Calibration readings are electrical measurements outside the frozen metric ontology. |
| 16 | excluded | Tuning guidance contains no measured result block. |
| 17 | candidate | The first CoreMark result block has explicit benchmark scores; exact ontology mapping still needs review. |
| 18 | excluded | Performance budgets and pending checks are targets, not results. |
| 19 | excluded | The document provides a build observation, not a size-conforming supported result block. |
| 20 | excluded | The first sentiment table exceeds 20 supported scalar outcomes. |
| 21 | excluded | API documentation, not an empirical result report. |
| 22 | excluded | Generic indexing-time examples do not state a frozen canonical metric identifier. |
| 23 | excluded | Metric names only; no measurements. |
| 24 | excluded | CLI example enumerates metric templates, not results. |
| 25 | excluded | Coursework instructions, not reported experiment results. |
| 26 | excluded | Experimentation guide contains configuration examples, not results. |
| 27 | excluded | Product specification / expected metrics, not an empirical result block. |
| 28 | candidate | The first recall table has eight explicit recall outcomes. |
| 29 | excluded | Large experimental notebook is not a bounded first result block under the frozen ontology. |
| 30 | candidate | Reported RMSE/MAE result table may be size-conforming; labels require a separate source-only pass. |

No v16 source has been passed through ReproCheck while this log was produced.
The study remains unevaluated until the source-only labels, evaluator, and
study lock are committed and pushed.
