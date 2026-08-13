# ReproCheck 0.27.0

ReproCheck 0.27.0 is a post-v12 development release. It generalizes result
extraction across Markdown, tab-delimited, multiline, and subheader tables;
unit-aware runtime and throughput output; Keras, Presto, Julia, fuzzing, and
compression summaries; result-dense prose; and explicit speedup ranges.

The prospective v12 result for 0.26.0 remains immutable and negative: 1/20
complete documents, 26/190 selected claims recovered, and 26/41 block-level
predictions correct. After inspecting those failures, 0.27.0 exactly matches
20/20 selected blocks and 190/190 claims with no additional block-level
predictions. A permanent regression test verifies both recall and precision and
also verifies the SHA-256 digest of the frozen zero-shot result.

The perfect v12 replay is development evidence only. It must not be reported as
zero-shot or external validation. A new preregistered holdout, frozen before
retrieval and annotation, is required to measure generalization of 0.27.0.

No repository name, case identifier, or frozen numeric answer is encoded in the
extractor. The added grammars operate on metric names, units, table structure,
console syntax, and explicit result language.
