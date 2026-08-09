# Machine-verifiable evidence graph

ReproCheck models one computational audit as a directed evidence graph

\[
G = (V, E),
\]

where every vertex has one of six explicit types: `experiment`, `artifact`,
`context`, `metric`, `claim`, or `finding`. Edges use a closed relation set such
as `recomputes`, `supports`, `contradicts`, and `flags`.

The graph is not inferred by an opaque model. It is constructed
deterministically from the same typed objects that produce the audit result.
For example:

```text
predictions.csv --recomputes--> accuracy=0.9417 --supports--> report claim
train.csv ------flags----------------------------------------> split overlap
model=proposed --qualifies--> accuracy and report claim
```

## Integrity construction

For canonical JSON serialization `C` and SHA-256 `H`, each node and edge stores

\[
d_x = H(C(x \setminus \{d_x\})).
\]

The graph stores

\[
d_G = H(C(G \setminus \{d_G\})),
\]

and the ordinary ReproCheck certificate digest commits to the complete graph.
`reprocheck verify` independently checks node digests, edge digests, graph
digest, root existence, edge endpoints, schema, certificate digest, and
optionally the original artifact bytes.

This layered construction allows a graph fragment to retain a local integrity
identifier while the certificate binds the complete audit and source artifact
descriptors.

## Export

```bash
reprocheck graph \
  --certificate outputs/demo-audit.json \
  --output outputs/demo-evidence-graph.mmd
```

The output is Mermaid source suitable for documentation and presentations.
Use `--format json` for the graph object alone. Export first verifies the
certificate and refuses a graph with invalid internal digests.

## Formal boundary

The graph proves a narrower property than scientific truth: given the supplied
artifacts and declared parameters, it records which deterministic operation
produced each metric relation and whether the value supports the extracted
claim within tolerance.

It does not prove that the dataset is representative, the metric is
scientifically appropriate, the model generalizes, an undeclared artifact did
not influence the experiment, or ReproCheck found every possible leakage path.
Artifact nodes commit to bytes, not to the truth of their contents.

The research hypothesis is therefore falsifiable and bounded: artifact-aware
claim-to-evidence tracing should detect declared classes of computational
inconsistency that report-text-only analysis cannot observe. Existing mutation
and holdout studies validate components of that pipeline. A direct blinded
four-system ablation of the complete graph method remains future evidence, not
a claimed result.
