# Human-study protocol

This directory contains a protocol, not completed human evidence.

`human-study-prepare` creates a private immutable master with eight matched
controlled cases. It does not authorize participant recruitment.
The generated `master/private/` tree is mode `0700/0600` and gitignored; never
commit, publish, or copy it into participant packets.

`human-study-issue` requires a real approval reference and creates a
counterbalanced packet. The private gold must never be sent to participants.

`human-study-score` refuses missing consent, non-independent responses,
duplicate participants, missing cases, invalid durations, and overwrite. Fewer
than 12 completed participants remain descriptive only.

Do not invent approval references, responses, timings, identities, or consent.
AI-generated responses are not human-study evidence.
