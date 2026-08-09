# ReproCheck 0.14.0

Version 0.14.0 turns the previously implicit claim context into an explicit,
machine-verifiable evidence graph.

Each certificate now traces hashed artifacts and contexts through reported or
recomputed metrics to claims and findings. Every node, edge, and complete graph
has a deterministic SHA-256 digest. Certificate verification checks those
digests, graph endpoints, and the graph root in addition to the existing schema,
certificate, signature, and artifact checks.

`reprocheck graph` exports a verified graph as Mermaid or JSON. HTML reports and
the local web result expose graph size and digest, making the method inspectable
without treating the interface itself as scientific evidence.

Schema 1.2 keeps `evidence_graph` optional so certificates produced by older
versions remain valid. New 0.14 certificates always include graph schema 1.0.
