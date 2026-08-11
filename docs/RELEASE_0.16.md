# ReproCheck 0.16.0

Version 0.16.0 turns the local web demonstration into a real project-audit
workflow and publishes the expanded controlled evidence suite developed after
0.15.0.

## Real project workflow

- The web interface accepts a complete project folder or one ZIP archive and
  runs the same manifest inference and `run_audit` pipeline used by the CLI.
- ZIP ingestion rejects traversal, symlinks, encrypted members,
  case-insensitive duplicates, excessive entries, oversized members, and
  compressed or expanded projects above the documented limits.
- Backend-reported stages replace synthetic progress. The result records the
  selected experiment, inferred artifact roles, and measured stage durations.
- Manual role assignment and expert parameters remain available through
  progressive disclosure instead of dominating the first-use path.

## Evidence presentation

- The interactive evidence explorer links artifacts, metrics, claims,
  findings, and the certificate through the verified graph already embedded in
  the audit result.
- Orthogonal edge routing, semantic highlighting, filtering, and a node
  inspector make the graph usable on desktop and mobile without changing its
  scientific meaning.
- A deterministic Evidence Passport summarizes exact claim coverage,
  recomputation coverage, inspected layers, and prioritized actions. It has no
  opaque AI score and is derived from, but not inserted into, the signed
  certificate.

## Expanded controlled evidence

Four design-locked experiments cover nine integrity attacks, eight
source-derived corruptions plus three controls, thirteen numerical
representation cases, and end-to-end scaling through 1,000 claims. Their
protocols were committed before the first frozen results. The original frozen
result bytes and SHA-256 locks remain unchanged; cross-release regression
checks ignore only their historical `tool_version` label while separately
requiring every newly generated result to report `0.16.0`.

## Exact boundary

The web server remains a local tool without authentication or rate limiting.
Uploaded code is not executed. Controlled experiments remain author-designed,
and the external-review protocol still records zero completed external
reviewers. This release improves usability, traceability, and controlled
evidence; it does not claim universal scientific verification or superiority
to human artifact review.
