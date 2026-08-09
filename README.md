# Omar Ibrahim

I build reliable AI systems where model behavior meets browsers, streaming
protocols, storage, compilers, and experimental evidence. My work favors
bounded inputs, deterministic replay, independent verification, and explicit
claim limits.

This profile is a fast path through seven current systems projects. Each
summary below names the public evidence that exists today and the conclusion
that evidence does not support.

## Systems map

![Source-derived map of seven selected public AI systems projects, their evidence surfaces, and claim boundaries](assets/portfolio-systems-map.svg)

*Curated portfolio navigation.* The strict
[`portfolio/projects.v1.json`](portfolio/projects.v1.json) source binds every
card to a reviewed default-branch commit, one public evidence surface, and one
explicit non-goal. It is not a benchmark scorecard or live remote-state
attestation.

Reproduce the SVG and verify its exact two-file bundle:

```bash
python3 tools/render_portfolio_map.py --check
```

The adjacent
[manifest](assets/portfolio-systems-map.manifest.json) binds the contract,
renderer, semantic digest, seven immutable refs, and SVG bytes.

## Selected systems

### [ImpactDiff](https://github.com/omar07ibrahim/impactdiff) · TypeScript · Multimodal evaluation

Task-aware browser-change evidence for asking whether a visual change breaks a
user workflow or accessibility surface. The current authoring bundle contains
two synthetic applications, four workflows, and 12 real deterministic Chromium
checkpoints with accessibility, layout, action, provenance, and manifest
records. It contains no official pair, released dataset, trained model,
benchmark result, or accuracy claim.

### [SSemaphore](https://github.com/omar07ibrahim/ssemaphore) · Go · LLM serving infrastructure

A Linux loopback gateway for bounded multi-tenant Chat Completions traffic,
weighted-deficit admission, validated buffered/SSE relay, cancellation, and
signal-owned shutdown. Public evidence covers one controlled loopback workflow
and one fixed-seed 28-job saturation run whose dispatches match an independent
bounded oracle. It does not report throughput, latency, RSS, a fairness score,
or a service-share benchmark.

### [RunnelMoE](https://github.com/omar07ibrahim/runnelmoe) · Rust / Python · Sparse MoE inference

A model-agnostic laboratory for verified out-of-core expert storage, bounded
DRAM caching, cache-policy research, and a narrow BF16/AVX2 kernel. The closed
M1-M4 bundle exposes captured command output, raw evidence, source-bound
visuals, and explicit milestone reviews. Its M3 evidence measures synthetic
modeled traffic, and M4 covers fixed synthetic GEMV batches on one recorded
host; neither is an end-to-end inference or serving-speed claim.

### [TensorKiln](https://github.com/omar07ibrahim/tensorkiln) · C++20 · Tensor compiler/runtime

A dependency-free static `f32` compiler/runtime with checked graphs, explicit
rewrites, reverse-verified arena planning, independently reconstructed
execution plans, guarded allocation-free sessions, and a separate reference
interpreter. Real release-CLI transcripts and a three-frame workflow exercise
two compiled-in workloads, including a six-step ReGLU slice with exact output
agreement. The project makes no benchmark, general-model, or full-transformer
claim.

### [FalseWake](https://github.com/omar07ibrahim/falsewake) · Python / PyTorch · Streaming keyword spotting

An open-set keyword-spotting research system built around the failure mode that
clip accuracy misses: false activations on continuous unrelated speech.
Experiments 000 and 001 provide the measured linear baseline and development
replay; all 1,001 registered thresholds failed the joint retention and
false-event gates. Experiments 002-006 are retained engineering and incident
evidence only: they produced no valid neural metric, reusable checkpoint, ONNX
result, or continuous-replay score.

### [StrataFold](https://github.com/omar07ibrahim/stratafold) · Python · MoE compression research

A clean-room lab for structural expert compression without silently relabeling
dtype changes as compression. Its current M1 result is a pinned, bounded
official-metadata target genome with raw records, a deliberate rejection path,
and an 11-file visual atlas. No full checkpoint was downloaded or run, so M1
makes no compression-ratio, quality, throughput, active-compute, or
state-of-the-art claim.

### [PEFTLint](https://github.com/omar07ibrahim/peftlint) · Python · Model artifact tooling

A fail-closed local preflight for PEFT LoRA checkpoints that inventories
components, parses pinned configuration and safetensors headers, and emits
deterministic structural evidence without importing model code or reading
tensor payload bytes. Eight real CLI cases expose the current 8-of-17 rule
slice. Even a clean run remains `UNKNOWN`; it is not proof that an adapter can
load against a base model.

## Additional maintained systems

- [Netveil](https://github.com/omar07ibrahim/netveil) · Python · Privacy and supply-chain security — offline pseudonymized audit receipts, guarded wheel execution, a published v0.3.0 evidence bundle, and explicit disclosure limits.
- [K2DO](https://github.com/omar07ibrahim/k2do) · Python · Agent orchestration — a provenance-explicit nanobot derivative with routed DeepThink, real MCP subprocess fault labs, bounded cancellation, and three source-bound visual evidence suites.
- [MeasureTrace](https://github.com/omar07ibrahim/measuretrace) · Python · Exact computing — rational m/km/mi conversion, independently recomputed receipts, reproducible packages, and real responsive browser captures.
- [ShardLift](https://github.com/omar07ibrahim/shardlift) · Python / PyTorch · Distributed training — crash-consistent checkpoints, deterministic recovery, and auditable real-SIGKILL evidence.
- [KVCrucible](https://github.com/omar07ibrahim/kvcrucible) · Rust / Python · LLM inference reliability — an offline conformance lab for unreliable KV-cache event streams, explicit uncertainty, replayable witnesses, and fault-injection evidence.

Also maintained: [RecallLedger / note](https://github.com/omar07ibrahim/note) · [UnitSentinel / units](https://github.com/omar07ibrahim/units) · [Casefold / case](https://github.com/omar07ibrahim/case) · [PasswordGenerator](https://github.com/omar07ibrahim/PasswordGenerator) · [GWorker](https://github.com/omar07ibrahim/GWorker) · [WitnessGap](https://github.com/omar07ibrahim/witnessgap) · [A1220](https://github.com/omar07ibrahim/A1220-lab1-omar07ibrahim)## Engineering approach

- State the trust boundary and non-goal before making a claim.
- Bound bytes, shapes, work, queues, retained state, and diagnostics.
- Prefer deterministic state machines, property tests, pinned toolchains, and
  machine-readable evidence.
- Keep optimized paths answerable to a separate reference or verifier.
