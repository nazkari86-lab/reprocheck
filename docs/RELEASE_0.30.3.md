# ReproCheck 0.30.3

ReproCheck 0.30.3 fixes the second fail-closed acquisition attempt without rewriting
its evidence.

GitHub's contents API wraps standard base64 with line breaks. Generation 3 retrieved
the search, repository, commit, and content responses but strict decoding rejected the
whitespace before any candidate source was materialized. Its registration, raw bytes,
state, and failure manifest remain frozen under `registration-v3-failed.json` and
`acquisition-v3/`.

Generation 4 removes only base64 whitespace and then retains strict alphabet and padding
validation. The behavior is covered by a line-wrapped API fixture. It uses a new
selection salt and freezes the reproducible 0.30.3 evaluator wheel with SHA-256
`98ab93115f5451cec14c67a497a7f9f5154c559e5352c88de38549e0bef316bf`.

Scientific status: generation 4 is registered and initially unexecuted. Earlier failed
acquisitions are engineering evidence, not external evaluation results.
