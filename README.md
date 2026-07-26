# Omar Ibrahim

I build reliable AI systems across multimodal evaluation, browser automation,
compiler/runtime infrastructure, inference reliability, and model tooling. I am
especially interested in failures at system boundaries: unreliable event
streams, model-artifact mismatches, unverified storage assumptions, ambiguous
evidence, and real inputs that clean benchmarks miss.

My projects turn those failures into bounded, reproducible experiments with
explicit trust assumptions and machine-checkable results.

## Selected work

### [ImpactDiff](https://github.com/omar07ibrahim/impactdiff) · TypeScript · Multimodal ML evaluation

ImpactDiff is a research lab for task-aware visual regression: whether a UI
change breaks a user task or damages accessibility, rather than merely changing
pixels. It captures canonical screenshots, accessibility trees, and bounded
layout graphs around a real coordinate-driven task, while storing model-visible
evidence separately from intervention metadata, execution traces, and labels.

The current milestone runs baseline and mutated candidates in distinct fresh
BrowserContexts under one verified Chromium environment, compiles and rolls
back typed palette and pointer interventions, derives and replays complete
evidence records, and atomically publishes immutable visible/sealed release
pairs. The Node 22 and 24 CI lanes exercise capture, provenance, recovery, and
publication boundaries. A multi-application dataset, isolated
feature runner, trained models, and benchmark result remain the next research
milestone; the repository makes no accuracy claim today.

### [SSemaphore](https://github.com/omar07ibrahim/ssemaphore) · Go · LLM serving infrastructure

SSemaphore is a correctness-first local gateway for bounded, multi-tenant Chat
Completions traffic. Its admission path combines estimated-service accounting
with work-deficit round robin scheduling, explicit queue and body budgets,
disconnect-aware cancellation, and a fixed upstream transport boundary.

The runnable gateway accepts a strict versioned policy from a private Linux
file, consumes bearer credentials through one-shot environment references, and
binds only to an exact numeric loopback address. End-to-end wire tests cover
admission, authenticated forwarding, signal-owned shutdown, and listener
cleanup; the release gate also exercises the race detector and 32-bit checked
arithmetic.

Its bounded SSE relay validates one `data:` event at a time under total,
per-event, count, idle-read, event, and total deadlines. It flushes validated
chunks with bounded read-ahead, keeps the admission permit through a clean
`[DONE]` and EOF, and separates pre-commit gateway errors from post-commit
stream truncation. A real loopback test proves that the first chunk reaches the
client before the upstream response completes.

### [ShardLift](https://github.com/omar07ibrahim/shardlift) · Python/PyTorch · Distributed training reliability

ShardLift is a Linux crash-consistency lab for sharded training state. Its
`killer-demo` kills an isolated checkpoint publisher with a real `SIGKILL`,
recovers from verified immutable commit records, continues the recovered
four-worker state, reshards it offline from four workers to three, and compares
the result with an uninterrupted trajectory using logical-state roots and exact
fixed-probe logits.

The canonical CPython 3.14 evidence lane runs both public crash barriers from a
hash-locked wheel and PyTorch CPU runtime, re-verifies the retained bundles, and
publishes the evidence and runtime provenance. Separate Python 3.11–3.14 lanes
exercise the core package, typing, coverage, and clean wheel install. The claim
is deliberately limited to process crashes on the recorded environment; it is
not a power-loss durability or production-training claim.

### [TensorKiln](https://github.com/omar07ibrahim/tensorkiln) · C++20 · Tensor compiler/runtime

TensorKiln is a dependency-free compiler for static `f32` tensor graphs. Its
current vertical slice includes checked rank 0-4 types, transactional graph
construction, batched `MatMul` and broadcasting, an independent reference
interpreter, dead-code elimination, and exact structural canonicalization with
composable provenance.

The released alpha's graph-to-arena boundary derives compute lifetimes, applies
a deterministic 64-byte interval planner, and returns a storage projection only
after an independently coded reverse verifier reconstructs and agrees with
every mapping, request, statistic, and allocation.

The merged [verified execution milestone](https://github.com/omar07ibrahim/tensorkiln/pull/10)
builds a minimal kernel/placement candidate and independently reconstructs its
operands, dense layouts, storage, lifetimes, limits, and work before execution.
Its arena session rejects invalid floating-point environments, guards every
non-empty workspace, audits exact kernel write sets, and keeps repeated
execution allocation-free under wrapped C/C++ allocators.

Axis-aware `Softmax` now has deterministic reference semantics for every valid
rank 1–4 axis and a separately verified allocation-free last-axis kernel. A
real release binary publishes the complete five-slice finite/NaN/infinity
policy output; an 80-digit `Decimal` oracle and 96 deterministic seeds check
the optimized boundary. Five self-contained SVGs, three raw terminal
transcripts, and a SHA-256 manifest make the architecture, arena reuse,
reproduction workflow, and runtime results visible on the default branch.
GCC/Clang, sanitizers, clean shallow clones, 217 C++ tests, and 20 visual
contract tests guard the milestone; it deliberately makes no benchmark claim.

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

The merged [inventory milestone](https://github.com/omar07ibrahim/peftlint/pull/4)
turns those immutable manifests into exact, path-scoped evidence for saved LoRA
pair closure, dimensions, and configured rank. It distinguishes modeled
two-dimensional weight pairs from higher-rank convolution candidates, which
remain `Unknown` instead of being mislabeled as incompatible. The evaluator
imports neither PEFT nor Torch, reads no tensor payload, and never executes a
retained rank-pattern regex.

The versioned compatibility contract keeps these findings separate from a full
load verdict: base topology, selection, dtype, saved-module, and vocabulary
evidence remain explicit future dependencies.

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
