# Architecture

```text
report ──> document extractor ──> claim parser ───────┐
predictions ──> deterministic metrics + Wilson CI ───┤
detection boxes ──> IoU matching + AP recomputation ─┤
train/test ──> overlap and group audit ──────────────┼─> findings
notebook ──> static pipeline-risk analysis ──────────┘
files ──> SHA-256 provenance ──> canonical report checksum
project manifest ──> N isolated audits ──> linked batch certificate
typed audit state ──> content-addressed evidence DAG ──> graph verification
```

Every metric observation carries an evidence level. Tables and report exports
are `reported`; values derived from raw labels/predictions are `recomputed`.
When two sources differ beyond the declared tolerance, the orchestrator emits
`metric_evidence_conflict` and keeps the higher-grade recomputed value visible.

Table claims can also carry bounded structured context such as model, dataset,
split, experiment, task, and variant. A selected wide-CSV evidence row carries
the selector context. Shared context dimensions must agree before a claim can
match that observation; an incompatible row becomes `no_evidence`, not a false
metric mismatch. Context-free evidence preserves the legacy metric-name path.

`evidence_graph.py` converts this typed audit state into a content-addressed
DAG. It is downstream of parsing and metric computation: the graph records
those deterministic relations but does not invent missing experiment
semantics. The certificate verifier independently checks every graph digest,
root, and edge endpoint.

The claim layer exposes `extract_claims` for complete documents and
`extract_table_claims` for explicitly table-scoped evaluation. Markdown and
HTML tables share metric normalization, preserve duplicate values from distinct
columns, and skip cells with multiple candidate numbers rather than guessing.

The core package is independent of FastAPI. `audit.run_audit` orchestrates pure
modules and returns dataclasses; CLI and web layers only map inputs and render
the same result. Uploaded notebooks are parsed but never imported or executed.
Saved textual notebook outputs can be claim evidence. The notebook risk layer
uses a bounded AST graph for assignments, train/test split outputs, aliases,
and simple function wrappers; it is not a complete interprocedural proof.

The JSON certificate excludes `created_at` from its canonical digest so the
same evidence and parameters produce the same checksum across repeated runs.
Artifact hashes remain part of the digest.

The certificate verifier treats filenames and roles as untrusted input,
rejects path traversal and malformed descriptors, and verifies both SHA-256 and
byte length. It also validates the complete payload against the bundled audit
JSON Schema before returning success. The checksum is intentionally not an
identity signature.

The optional signing layer signs the exact certificate bytes with an encrypted
Ed25519 private key and writes a strict detached JSON envelope. Verification
first rechecks the certificate and artifacts, then verifies the signature and
requires the embedded signer key to equal a separately supplied trusted public
key. This separates payload integrity, key possession, identity trust, and
timestamp trust rather than conflating them.

The leakage layer performs exact and normalized SHA-256 joins, group joins, and
an optional complete indexed lexical-similarity join. `hybrid_lexical_v1`
indexes token and Unicode character-trigram features, rejects only candidates
whose feature-set sizes mathematically cannot reach the threshold, then scores
the survivors exactly. This is equivalent to exhaustive evaluation of the
defined lexical score, not to semantic similarity.

`ordered_tokens_v1` applies `SequenceMatcher` to normalized token sequences so
word order affects the score. Its complete inverted index uses both a length
bound and a token-multiset overlap bound before sequence scoring. The public
`find_text_matches` API returns the best qualifying train row per test row plus
exhaustive, candidate, and exactly scored pair counts. Common-token corpora can
still make candidate construction approach a Cartesian product.

`batch.run_project_check` validates a declarative project manifest, resolves
all inputs beneath the manifest directory, and completes every audit before it
writes output. Child certificates retain the stable audit schema. A separate
batch certificate binds the manifest checksum, experiment IDs, statuses,
finding counts, and child certificate digests. During verification, the signed
manifest restores the role-to-relative-path mapping needed to verify artifacts
inside nested project directories.
