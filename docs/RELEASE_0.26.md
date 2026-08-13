# ReproCheck 0.26.0

ReproCheck 0.26.0 is a post-v11 development release. It adds general parsers
for result-dense prose, whitespace and reStructuredText grid tables, Unicode
box-drawing latency summaries, compact metric tables, scoped result columns,
hardware/network units, and multiple outcomes on one line.

The prospective v11 result for 0.25.0 remains immutable and negative: 1/25
complete documents and 38/237 visible claims. After inspecting v11, 0.26.0
reaches 25/25 and 237/237 on that set while preserving the frozen challenge and
real-artifact precision gates. This is development evidence only. A new
independent v12 holdout is required for an external-generalization claim.

No repository name, case identifier, or frozen numeric answer is encoded in the
extractor. The new grammars operate on metric names, units, table structure,
console syntax, and explicit result language.

