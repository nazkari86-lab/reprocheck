# ReproCheck 0.17 external holdout

This directory separates registration from execution.

1. Build the frozen evaluator wheel.
2. Run `reprocheck holdout-register` once. The command refuses overwrite.
3. Authenticate the protocol, evaluator, and registration hashes through a
   separate trusted channel.
4. Only then fetch the pinned source contents and prepare blind reviewer
   packets.
5. Freeze two real independent responses and adjudication before revealing the
   primary evaluator result.

The protocol pins four repositories that are outside the earlier documented
ReproCheck corpora. Their HEAD commit identifiers were resolved on 2026-08-12.
Resolving commit identifiers is not a claim that the repositories contain a
minimum number of eligible numerical claims; the preregistered shortfall rule
handles that outcome.

Until those steps occur, status must remain `registered_not_executed`, external
reviewers completed must remain zero, and no accuracy result may be reported.

The two `registration-superseded-*.json` files preserve pre-execution local
locks replaced after final-build and security-hardening changes. Neither had
source inspection or external execution. `registration.json` is the active
lock and matches the wheel currently stored under `evaluator/`.
