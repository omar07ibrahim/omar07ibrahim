# Omar Ibrahim

I build reliable AI systems across inference infrastructure, model tooling, and
evaluation. I am especially interested in failures at system boundaries:
unreliable event streams, model-artifact mismatches, ambiguous evidence, and
real inputs that clean benchmarks miss.

My projects turn those failures into bounded, reproducible experiments with
explicit trust assumptions and machine-checkable results.

## Selected work

### [KVCrucible](https://github.com/omar07ibrahim/kvcrucible) · Rust · AI inference reliability

KVCrucible is an offline conformance lab for reconstructing LLM KV-cache
metadata from unreliable publisher streams. Its bounded Rust core validates
canonical JSONL and tracks per-publisher `Exact` / `Recovering` / `Unknown`
state. It materializes deterministic drop, duplicate, and reorder schedules,
then compares fresh pristine and faulted folds without turning incomplete
evidence into a false divergence claim.

The implementation includes opaque semantic fingerprints, atomic cache-view
projection, property-tested fault materialization, a first-class per-stream
convergence oracle, and a statically linked musl release gate.

### [peftlint](https://github.com/omar07ibrahim/peftlint) · Python · Model artifact tooling

peftlint moves LoRA adapter failures into a bounded preflight step without
importing model code or allocating model tensors. The current vertical slice
ships pure parsers for pinned PEFT adapter configurations and safetensors
manifests, including duplicate-key rejection, explicit byte and JSON budgets,
checked tensor-shape arithmetic, span validation, and payload-coverage proofs.

Its versioned compatibility contract distinguishes evidence that can justify a
static result from cases that must remain `Unknown` until runtime validation is
available.

### [OrthoDrift](https://github.com/omar07ibrahim/orthodrift) · Python · Retrieval evaluation

OrthoDrift finds minimal grapheme-level changes that make a retriever lose the
relevant document. Its first research lane is Azerbaijani retrieval, while its
core text and provenance machinery remains language-agnostic.

The current implementation runs deterministic BM25 experiments, reduces rank
failures to minimal counterexamples, and emits self-contained JSONL evidence
that can be independently replayed and verified against its recorded runtime
environment.

## Engineering approach

- State the trust boundary, uncertainty, and non-goals before making a claim.
- Bound untrusted input, retained state, and diagnostic work before execution.
- Prefer deterministic state machines, property tests, golden vectors, pinned
  toolchains, and machine-readable evidence over screenshot-only demos.
