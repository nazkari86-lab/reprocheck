# ReproCheck 0.25.0

ReproCheck 0.25.0 generalizes numeric-result extraction beyond the narrow
correction-oriented formats evaluated before 0.24.0. It adds reusable support
for multi-level Markdown result tables, units declared in table headers,
ranked-retrieval and generation metrics, benchmark console summaries, GPU
memory, paired timing/allocation cells, improvement prose, and multilingual
training logs.

The broad preregistered v10 holdout remains an immutable negative result for
0.24.0: 2/20 complete documents and 32/155 visible claims. After inspecting
v10, 0.25.0 reaches 20/20 and 155/155 on that same set. This is development
evidence only and is not described as zero-shot. A new independent v11 study
is required before making an external-generalization claim for 0.25.0.

The implementation contains no repository names, case identifiers, or frozen
numeric answers. Every added format family has a standalone regression test.
