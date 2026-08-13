# ReproCheck 0.28.0

ReproCheck 0.28.0 is a post-v14 development release. It adds portable parsing
for abbreviated classification headers, FPS cells and scaled FPS prose,
row-labeled latency tables, mean-plus-standard-deviation loss tables, GNU time
console summaries, and target-column suppression.

The preregistered v14 result for 0.27.0 remains immutable and negative: 1/25
exact documents, 28/218 gold claims recovered, and 28/58 predictions inside the
registered blocks correct. No 0.28.0 replay may replace that zero-shot result.

V14 also demonstrated why annotation ontology must be part of the input
contract: its hand labels used several metric identifiers and millisecond units
that differ from ReproCheck's stable duration-in-seconds schema. The next fresh
study must freeze the supported public ontology before retrieval and evaluate
only claims that can be linked to that ontology. This is a protocol correction,
not permission to alter v14 labels.
