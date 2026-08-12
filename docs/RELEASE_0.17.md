# ReproCheck 0.17.0

Version 0.17.0 adds a narrow algorithmic contribution and prepares, without
fabricating, the two external evidence layers missing from earlier releases.

## Minimal contradiction witness

- `reprocheck witness` extracts the canonical minimum source-grounded witness
  for a `claim_metric_mismatch` under a public typed verifier rule.
- `reprocheck verify-witness` independently binds the witness to the original
  certificate and artifacts, checks numerical contradiction and internal
  digests, and repeats the complete grounding search.
- The controlled four-case benchmark compares the full graph, an invalid
  one-hop shortcut, and the exact witness. The witness reduces nodes by 58.3%
  and serialized bytes by 67.7%; 16/16 controlled tamper variants are rejected.

These are controlled capability results, not evidence of human time savings.

## External evidence infrastructure

- A source-unseen cross-domain holdout protocol pins four new repository pools,
  deterministic selection, primary endpoints, dual annotation, adjudication,
  and a one-shot stopping rule.
- Registration cryptographically binds that protocol to a frozen evaluator and
  refuses overwrite. Until execution, its status remains
  `registered_not_executed` and external reviewers completed remains zero.
- Replaced pre-execution local registrations are retained as superseded audit
  records; the active registration binds the final reproducible wheel.
- A randomized crossover human-study master generates eight paired cases,
  counterbalanced manual/assisted packets, consent checks, immutable scoring,
  and a preregistered minimum of 12 participants. Packet issuance requires a
  recorded approval reference.

No participant, reviewer, approval, timing, or accuracy result is fabricated.

## Network boundary

The web server remains loopback-only by default. A non-loopback bind is refused
unless `--allow-network` is explicit; even then, the warning states that the
server has no authentication, TLS, or multi-user isolation.

## Remaining blocker

Independent dual annotation, adjudication, source-unseen evaluation, and the
approved human study require real external people. Local readiness does not
turn them into completed scientific evidence.
