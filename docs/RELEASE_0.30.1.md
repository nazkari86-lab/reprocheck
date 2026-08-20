# ReproCheck 0.30.1

ReproCheck 0.30.1 hardens Evidence Trial v19 before external retrieval.

The acquisition runner now freezes raw API responses, commit-pinned UTF-8 source
bytes, selection metadata, resumable state, and immutable success or failure manifests.
Selection enforces one candidate per repository owner and preserves every configured
byte cap and exclusion.

An independent source-only curator must now bind exact line spans to candidate files
before any outcome label exists. The pre-review gate checks only owners and claim count;
class-information requirements run after two independent reviews and complete
adjudication. Review, arm, candidate, enrollment, sample, and result inputs have strict
schemas and cryptographic bindings.

The certificate track requires all nine registered tamper classes and rejects duplicate
cases, swapped witnesses, certificate mismatches, and unregistered mutations.

Registration generation 1 remains byte-identical in
`registration-v1-superseded.json`; it was superseded before retrieval. Generation 2
freezes the reproducible 0.30.1 evaluator wheel with SHA-256
`00ea0b7807043a45711fcd58bb4bb8a2df78342c40f6957b3467b460743697b5`.

Scientific status: the tooling and protocol are registered but the external trial is
unexecuted. No external accuracy, generalizability, or human-review result is claimed.
