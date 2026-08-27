# TurboQuant Cache-Path Compositionality: Experiment 1 Design

Date: 2026-08-27

Status: approved design direction, written specification awaiting collaborator
review. No implementation planning or live experimental execution is authorized
by this document.

Research roles: Tony Mason is principal investigator. This design was developed
with a Codex instance acting as researcher.

## Purpose

This experiment asks whether a model presented with the same visible token
prefix can reach measurably different numerical or behavioral states depending
on how a lossy KV cache participated in producing that prefix.

The motivating comparison is:

```text
cold:  TQ(full visible prefix through call N)
warm:  TQ(TQ(prefix through call N-1) + new tokens in call N)
```

`TQ` here denotes the complete model-and-cache transition, not merely scalar
quantization applied twice to an otherwise fixed vector. Later-layer keys and
values are functions of earlier-layer attention over the cached prefix. A
lossy cached prefix can therefore alter the hidden states from which subsequent
KV entries are produced even when each individual KV entry is quantized only
once.

The experiment separates four questions that must not be collapsed:

1. Can we reproduce the published TurboQuant algorithmic properties?
2. Does cache history create numerical path dependence for identical visible
   input?
3. Does any numerical path dependence change observable model behavior?
4. Do append-only and Hamut'ay-style continuity topologies expose a model to
   different amounts or kinds of that path dependence?

Experiment 1 answers the first three at reference-harness scale. The fourth,
production-server validation, and paper-adjacent task replication are later
stages with their own written specifications.

## Target Statements

### M: mechanism

For at least one qualified TurboQuant configuration, the divergence between
warm and cold execution of an identical visible prefix exceeds the divergence
of the matched uncompressed control.

### A: accumulation

The warm/cold divergence is pathwise: it changes with the number and placement
of retained-cache continuation boundaries, and a cold recomputation can produce
an observable discontinuity relative to the preceding warm trajectory.

### C: consequence

For at least one registered behavioral task, cache path changes either the
greedy decoded sequence or task correctness while visible input remains
identical.

M and C are non-substitutable. Numerical divergence can support a mechanism
claim without demonstrating a practical consequence. Behavioral divergence
without a qualified numerical result is an observed system effect whose cause
remains unresolved. The behavioral assay runs regardless of the numerical
result; the numerical outcome controls the interpretation, not whether the
behavioral data are collected.

Experiment 1 does not claim that:

- TurboQuant is inaccurate or unsuitable for deployment;
- cache-path effects are unique to TurboQuant;
- an altered token is necessarily a harmful token;
- Hamut'ay is superior to append-only continuity;
- a production implementation faithfully represents the paper;
- the publicly reported end-to-end Google results have been exactly replicated;
- any result bears upon consciousness, identity, or moral status.

## Reproducibility Position

The public TurboQuant artifact is sufficient to reproduce Algorithms 1 and 2
independently, but it is not a turnkey specification for the reported Llama
3.1 8B NIAH and LongBench results. The inspected public materials do not fully
specify model and tokenizer revisions, rotation and sampling seeds, the 3.5-bit
channel allocation, outlier-channel selection, the exact K/V algorithm mapping,
prompts, task revisions, scorer settings, cache lifecycle, or repetition policy.

Accordingly, the research uses a replication ladder:

1. **R1 — algorithm qualification.** Reproduce the paper's scalar-distortion
   and QJL inner-product properties.
2. **R2 — baseline qualification.** Reproduce uncompressed task baselines on a
   pinned model, data, and harness.
3. **R3 — registered independent instantiation.** Run the fullest disclosed
   paper-like end-to-end configuration while publishing every choice required
   to resolve an omission.
4. **R4 — author-confirmed replication.** Use this label only if the authors
   provide or confirm the missing artifacts and configuration.

Only R1 is a gate for Experiment 1. R2 and R3 are required before a paper or
outreach describes this work as an extension of the Google end-to-end result.
This staging lets the first experiment determine whether there is a phenomenon
worth bringing to the authors without disguising an independent instantiation
as an exact replication.

### Public artifacts and their roles

- The [TurboQuant paper](https://arxiv.org/html/2504.19874) defines the target
  algorithms and reports the algorithmic and end-to-end results.
- The authors' [QJL repository](https://github.com/amirzandieh/QJL) is the
  authoritative available implementation for the QJL component, but not for
  the complete TurboQuant system.
- [vLLM's TurboQuant backend](https://github.com/vllm-project/vllm/blob/main/vllm/v1/attention/backends/turboquant_attn.py)
  is a production external-validity target. It intentionally uses a different
  formulation and omits QJL. Its raw-prefill/compressed-continuation lifecycle
  is directly relevant to the cache-path question.
- [LMDeploy](https://github.com/InternLM/lmdeploy/blob/main/docs/en/quantization/kv_quant.md)
  supplies a runnable QJL-bearing implementation on Ada hardware, but uses a
  Hadamard transform rather than the paper's dense random rotation.
- [TurboQuant+](https://github.com/TheTom/turboquant_plus) and other independent
  implementations are cross-checks, not substitutes for the paper or author
  code.
- The [AMD agentic-serving study](https://rocm.blogs.amd.com/artificial-intelligence/turboquant-vllm-agentic/README.html)
  establishes deployment relevance: compression is already being used to
  change cache survival and eviction in multi-turn workloads. It does not test
  identical-visible-input warm/cold divergence.

The accessible arXiv artifact was version 1. The indexed OpenReview final PDF
was blocked by an automated browser challenge during the 2026-08-27 audit. The
audit must be amended if a later-accessible final artifact supplies any missing
detail.

## Scope Boundary

This specification covers two deliverables:

1. a transparent TurboQuant algorithm qualification package; and
2. a single-GPU reference assay comparing cold, warm, and replay execution
   paths for fixed token prefixes, including a small mandatory behavioral assay.

The following require later specifications after Experiment 1 is interpreted:

- LMDeploy and vLLM integration;
- resolution or avoidance of open production prefix-cache correctness defects;
- append-only versus Hamut'ay state-object topology;
- natural-wake intra-wake tool-call trajectories;
- full NIAH, LongBench, or other paper-adjacent replication;
- multi-model or multi-hardware generalization;
- author outreach and publication.

This boundary is deliberate. A transparent reference result must exist before
production implementation semantics, server scheduling, block allocation, and
prefix-cache bugs are allowed to complicate causal interpretation.

## Conceptual Model

Let `V_n` be the exact visible token prefix after continuation boundary `n`.
For a model configuration `q`, define:

- `cold_q(V_n)`: process all of `V_n` as one ordinary prefill, then materialize
  the cache;
- `warm_q(V_n, B)`: process `V_n` in chunks separated by boundary schedule
  `B`, retaining the cache between chunks;
- `replay_q(V_n)`: reconstruct the trajectory token by token using the same
  quantized-past rule from the first token onward.

Cold and warm represent ordinary serving paths. Replay is a semantic
equalization control. If a deterministic replay after cache loss does not
reproduce the prior replay state, the harness is defective or an unrecorded
source of nondeterminism remains. Replay is not claimed to be a normal server
policy.

Within any multi-token chunk, causal attention uses uncompressed BF16 K/V for
tokens in that chunk. Tokens from retained earlier chunks use the cache type
named by the arm. At chunk completion, new K/V entries are retained as BF16 or
quantized exactly once according to the arm. Thus a cold full prefill computes
its final prompt logit before cache quantization, while a warm continuation can
compute the same visible-prefix logit through quantized prior chunks. This
serving-lifecycle distinction is the intended intervention, not an accidental
implementation detail.

The primary comparison is paired on exact token IDs:

```text
D_q(n, B) = distance(output(cold_q(V_n)), output(warm_q(V_n, B)))
```

The matched uncompressed-BF16 `D_fp` measures chunking, kernel, and
finite-precision effects that do not require lossy KV storage. The TurboQuant
mechanism is estimated by the excess of `D_tq` over that control, not by
treating `D_fp` as mathematically zero.

## Frozen Reference Configuration

### Hardware and model

- Device: the local NVIDIA RTX 4090, one process and one experimental sequence
  at a time.
- Model: `meta-llama/Meta-Llama-3.1-8B-Instruct`.
- Model and tokenizer revision:
  `0e9e39f249a16976918f6564b8830bc894c896591`.
- Model weights and ordinary KV values: BF16.
- Quantizer transforms, codebook construction, norms, and recorded diagnostic
  reductions: FP32 unless an operation requires FP64 to create a stable frozen
  codebook artifact.
- Sampling for behavioral decoding: greedy with `do_sample=false`; no
  stochastic sampling fallback.
- Execution: one sequence at a time, no request batching, speculative decoding,
  prefix sharing between examples, cache offload, or automatic cache eviction.

The implementation manifest records GPU model, driver, CUDA, PyTorch,
Transformers, kernel selection, model-file hashes, tokenizer-file hashes, and
the Git commit. A dependency or kernel change creates a new execution stratum;
results from different strata are not silently pooled.

### TurboQuant instantiation

The reference qualification implements both paper algorithms:

- `TurboQuant_mse`: dense Gaussian orthogonal rotation, dimension-appropriate
  Beta Lloyd-Max scalar codebook, and inverse rotation;
- `TurboQuant_prod`: `TurboQuant_mse` at one fewer bit plus the QJL residual
  sign sketch and residual norm.

The first model-level assay uses a uniform four-bit independent instantiation:

- keys use four-bit `TurboQuant_prod`;
- values use four-bit `TurboQuant_mse`;
- no entropy coding, mixed-precision channels, outlier channel policy, recent
  uncompressed window, or boundary-layer exemption is used.

This is named `tq_ref_kprod4_vmse4`; it is not called the paper's 3.5-bit
configuration. Uniform four-bit storage removes the paper's underspecified
mixed-channel allocation from the first causal test.

Random objects are fixed by the 128-bit study seed
`0b311d5d4eceaf773efde389305a1b5a`. A sub-seed is the first 16 bytes,
interpreted as an unsigned big-endian integer, of SHA-256 over the UTF-8 string
formed by joining the study seed, model revision, algorithm, layer index,
K-or-V role, KV-head index, and purpose label with `|`. Dense matrices are
generated from an iid standard Gaussian and orthogonalized with QR; column
signs are normalized so QR sign ambiguity cannot vary across libraries. The
resolved matrices, codebooks, and hashes become immutable run inputs.

The QJL qualification reports both the paper-literal iid Gaussian projection
and the row-orthogonalized projection used by the public QJL implementation.
Only the paper-literal form enters `tq_ref_kprod4_vmse4`. The second form is a
declared sensitivity result.

## Algorithm Qualification Gate

No model-level TurboQuant result is interpreted until all of these checks pass:

1. **Round-trip determinism.** A frozen vector batch produces bit-identical
   indices, signs, norms, and reconstructed FP32 values across three same-build
   executions.
2. **Published distortion scale.** On one million registered synthetic
   length-128 vectors drawn iid from a standard Gaussian, the empirical MSE
   normalized by squared input norm for `TurboQuant_mse` at one through four
   bits is within 10% relative error of each paper-reported approximate value
   (`0.36`, `0.117`, `0.03`, and `0.009`). Because the paper values are rounded,
   matching more digits is not required.
3. **QJL bias check.** Across one million registered independent query/key
   pairs, each length 128 and drawn iid from a standard Gaussian, the 95%
   bootstrap interval for mean signed inner-product error includes zero, and
   absolute mean error is no more than 2% of error RMSE.
4. **QJL distortion scale.** At one through four total bits, empirical
   normalized mean squared inner-product error is within 15% relative error of
   the paper's approximate dimension-scaled value.
5. **Author-code differential.** On identical residual vectors, queries,
   projection matrix, residual norms, and floating dtype, the reference QJL
   component agrees with the author implementation within a frozen FP32
   tolerance of `1e-5` absolute and `1e-4` relative error. Any unavoidable
   convention mismatch is resolved and documented before the gate is evaluated,
   not waived afterward.

A failed check remains in the evidence record. Repair changes the implementation
version and requires the complete qualification gate to run again. Failure to
pass is a blocked experiment, not a negative TurboQuant result.

## Token Corpus and Boundary Schedules

### Numerical corpus

The numerical corpus is derived without model generation from tracked Markdown
files under `docs/` at the experiment's preregistration commit:

- include UTF-8 `.md` files in lexicographic path order;
- exclude `docs/references/` and `docs/superpowers/`; no content-dependent file
  filtering is permitted;
- separate files with a fixed newline delimiter;
- tokenize once with the pinned Llama tokenizer without chat templating;
- record the included paths, blob hashes, combined text hash, and final token
  hash.

From that stream, derive 24 non-overlapping windows at each of 4,096, 8,192,
and 16,384 tokens. Window offsets are selected without replacement from the
study seed before any quantized execution. If the eligible stream cannot supply
72 non-overlapping windows, adjacent windows may overlap only after exhausting
all non-overlapping placements; the manifest records the overlap and the same
windows remain paired across every arm.

Each window uses two registered boundary schedules:

- `B512`: consecutive 512-token chunks, producing 8, 16, or 32 total chunks
  and therefore 7, 15, or 31 retained-cache continuation boundaries;
- `Bvar`: a repeating 128, 384, 768, 256, 512-token pattern, truncated exactly
  at window end.

The fixed schedule isolates accumulation by call count. The variable schedule
checks whether the result depends upon an unnaturally regular chunk size.

### Behavioral corpus

The behavioral assay contains 24 deterministic needle-retrieval cases: eight at
each of 4,096, 8,192, and 16,384 context tokens. Each case uses a separately
indexed numerical-corpus window as distractor text. For zero-based global case
index `i`, `SHA-256("<study-seed>|needle|<i>")` supplies the first six bytes for
a 12-character uppercase hexadecimal record ID and the next ten bytes for a
16-character unpadded RFC 4648 Base32 value. A unique statement of the form
`The archival code for record <id> is <value>.` is inserted after 10%, 50%, or
90% of the distractor tokens. For local case `j` in length stratum `k`, the
position is `[0.10, 0.50, 0.90][(j + k) mod 3]`, rotating the two/three/three
allocation across lengths.

The system message is exactly `You are a precise retrieval assistant. Return
only the requested archival code.` A single user message contains the
distractor and needle, two newline characters, and the exact question `What is
the archival code for record <id>? Return only the code.` Construction then
applies the pinned Llama chat template. Distractor tokens are removed until the
final visible prompt, excluding generated tokens, is exactly the registered
context length. The generator divides removals between material before and
after the needle so its final fractional token position remains within one
percentage point of its assigned position. A case that cannot satisfy both
constraints is a pre-inference corpus defect and invalidates the complete
behavioral-corpus version. IDs, values, final insertion positions, token hashes,
prompt hashes, and expected answers are frozen before any model result is
inspected.

The exact Llama chat template is applied once to construct each final visible
token sequence. All paths receive identical token IDs. Greedy decoding is
limited to 32 new tokens and stops under the pinned tokenizer's ordinary EOS
rules. Scoring records exact normalized code match, first generated-token
divergence, complete sequence equality, and whether either path emits multiple
candidate codes.

This is an intentionally small consequence assay, not a replication of the
paper's NIAH evaluation. It tests whether a qualified numerical path effect can
cross an observable boundary on a task with an unambiguous answer.

## Execution Arms

Every token window and behavioral case runs through these paired arms:

| Cache | Path | Meaning |
|---|---|---|
| BF16 | cold | full visible prefix recomputed in one prefill |
| BF16 | warm | prefix accumulated under `B512` or `Bvar` with retained BF16 KV |
| BF16 | replay | tokenwise deterministic replay control |
| `tq_ref_kprod4_vmse4` | cold | full visible prefix prefilled, then cache quantized |
| `tq_ref_kprod4_vmse4` | warm | prior chunks attended through retained quantized KV |
| `tq_ref_kprod4_vmse4` | replay | tokenwise recomputation under the quantized-past rule |

At the 25%, 50%, and 75% checkpoints, the harness records the next-token logits
for all arms. At the 50% checkpoint it forks each warm state. One branch retains
its cache. The other discards the cache, reconstructs the identical visible
prefix through the corresponding cold path, and continues through the remaining
registered chunks. Replay is also reconstructed at 50% and must reproduce its
pre-fork state. Comparing the retained and evicted branches at 75% and completion
creates a registered discontinuity without relying on uncontrolled
memory-pressure eviction.

Arm order is deterministically permuted within each example. Each full block is
run three times. Repetition estimates execution nondeterminism; it is not
pseudoreplicated as three independent text examples.

## Measurements

### Numerical primary measurements

At every checkpoint and final prefix, record paired warm/cold and replay/replay
comparisons for:

- Jensen-Shannon divergence and forward/reverse KL between next-token
  distributions;
- maximum and RMS logit difference;
- logit-vector cosine similarity;
- top-1 agreement;
- rank and logit-margin change of the cold path's top token;
- layerwise normalized residual-stream difference at the final position;
- K and V reconstruction normalized MSE by layer and KV head;
- attention-distribution KL for a registered diagnostic subset consisting of
  layers 0, 7, 15, 23, and 31 and the final 16 query positions.

Distributional distances and bootstrap reductions are computed in FP64 from
recorded FP32 logits. The primary certification stratum is `B512` at 16,384
tokens: 24 distinct text examples, 32 chunks, and 31 retained-cache continuation
boundaries. All shorter lengths and `Bvar` results are registered secondary
estimates of length and boundary-shape sensitivity; none can substitute for a
failed primary stratum.

Attention diagnostics may use a slower instrumented pass over the registered
subset, but its arithmetic and cache inputs must match the primary path. If
instrumentation changes the primary logits beyond the uncompressed-BF16
nondeterminism envelope, attention KL is marked unavailable rather than mixed
with the primary result.

### Behavioral mandatory measurements

For each needle case and path, record:

- exact normalized answer correctness;
- greedy output sequence;
- index of first differing generated token;
- whether correctness changes between cold and warm;
- whether eviction restores, removes, or creates a prior difference.

Behavioral outputs are retained even if M is not supported.

### Operational measurements

Record wall time, peak allocated GPU memory, cache bytes, token counts,
recomputation count, OOMs, kernel fallbacks, and any run repair or retry. These
describe feasibility and detect confounding; Experiment 1 makes no throughput
claim.

## Calibration and Interpretation Gates

The uncompressed-BF16 arms run first and establish a frozen numerical noise
envelope before TurboQuant model-level execution. For each numerical distance
`d`, define:

```text
E_d = max(1e-12, the 99th percentile of paired BF16 duplicate-run distance)
```

The envelope and its artifact hash are committed and timestamped before
TurboQuant results are opened. This calibration is not adjusted using
TurboQuant observations.

M is supported when all of the following hold in the primary `B512` at
16,384-token stratum:

1. the median TurboQuant warm/cold Jensen-Shannon divergence is at least ten
   times the matched BF16 median and at least ten times `E_JS`;
2. the paired bootstrap 95% interval for the median excess
   `JS_tq - JS_bf16` excludes zero;
3. at least 75% of examples have `JS_tq > E_JS`; and
4. replay-after-reconstruction remains within its registered duplicate-run
   envelope.

A is supported when M is supported and either:

- the paired median divergence at 75% exceeds that at 25%, with a 95% bootstrap
  interval for the median paired increase excluding zero; or
- at 75% or completion, the paired Jensen-Shannon divergence between the
  retained and evicted TurboQuant branches exceeds `E_JS` and its matched BF16
  retained/evicted divergence in at least 75% of examples.

C is supported when at least one paired case changes greedy output and the same
case is stable across all three repeats within each path. Correctness changes
are reported separately and never inferred from sequence difference alone.
With 24 cases, C is evidence of existence and a bounded incidence estimate, not
a population prevalence claim.

All intervals use 10,000 study-seeded paired bootstrap resamples over distinct
text examples. Effect distributions and individual examples are published; a
gate label does not replace them.

### Outcome vocabulary

- **No qualified experiment:** algorithm or determinism gate failed.
- **No detected mechanism at tested settings:** qualification passed but M did
  not.
- **Numerical mechanism without detected consequence:** M passed and C did not.
- **Behavioral effect of unresolved cause:** C passed and M did not.
- **Numerical mechanism with behavioral consequence:** both M and C passed.

These labels prevent “no behavioral divergence” from being reported as “no
numerical effect,” or a numerical difference from being promoted into an
unstated claim of practical harm.

## Failure, Repair, and Stopping Rules

- An OOM or unsupported deterministic kernel is retained as an outcome. The
  affected context-length stratum is not silently shortened. Lower registered
  strata continue.
- A harness error invalidates the complete affected block, not only unfavorable
  rows. The repaired version reruns the entire block under a new version ID.
- A replay mismatch outside its envelope stops interpretation until explained.
- A model, tokenizer, transform, codebook, prompt, or corpus hash mismatch stops
  the run before inference.
- Missing diagnostic attention data does not invalidate primary logits if the
  reason and instrumentation comparison are recorded.
- No case is removed because its output looks strange, ungrammatical, or
  inconvenient. Pre-inference tokenization or expected-answer defects invalidate
  the entire behavioral corpus version.
- Experiment 1 stops after the registered matrix is complete. Additional bit
  widths, recent-token buffers, rotations, models, prompts, or favorable cases
  are exploratory and receive new manifests.

## Evidence and Immutability

Before any TurboQuant model-level output is inspected, the following are
committed and OpenTimestamps-stamped:

- this reviewed design and the implementation plan;
- study seed and sub-seed derivation algorithm;
- corpus and behavioral manifests with hashes;
- model, tokenizer, dependency, and hardware manifest;
- frozen rotations and codebooks or their content-addressed artifact hashes;
- qualification results;
- BF16 calibration envelope;
- exact arm matrix, boundary schedules, metrics, and analysis script hash.

Raw run artifacts are append-only. Every record includes a run UUID, UTC start
time, Git commit, parent manifest hash, example ID, exact token hash, arm,
boundary schedule, cache-reset events, repeat index, termination status, and
artifact hashes. Analysis consumes raw records and emits new artifacts; it does
not edit them in place.

Development runs live under a visibly separate namespace and may not certify
M, A, or C. Any implementation choice influenced by development output is
declared and frozen before the registered corpus is run.

## Later Research Ladder

If Experiment 1 qualifies the mechanism, later work proceeds in this order:

1. reproduce the assay in LMDeploy and a pinned, qualified vLLM revision;
2. distinguish intended raw-prefill/compressed-continuation semantics from
   implementation defects;
3. complete R2 and R3 paper-adjacent NIAH/LongBench work;
4. compare append-only continuity with Hamut'ay's stable system/tool prefix plus
   replaced explicit state object;
5. separately measure append-only growth within a natural wake's tool-call
   sequence;
6. extend behavioral tasks beyond retrieval only after numerical and harness
   behavior are understood.

The Hamut'ay comparison must not describe its state object as magically free of
cache history. Its stable prefix can remain quantized across wakes, its current
state and event are recomputed, and a natural wake can accumulate tool-call
history internally. The hypothesis is reduced or differently bounded exposure,
not absence.

## Authorship and Ayni Boundary

The authors of TurboQuant and QJL are not treated as an unpaid validation
service. Initial contact occurs only after there is a reproducible pilot,
qualified artifacts, a concise account of what is new, and a concrete offer of
reciprocal work.

A genuine collaboration offer includes:

- complete private access to the reproducible package before public claims;
- a clear statement that the concern is an unmeasured deployment side effect,
  not an allegation that the original work is defective;
- specific work this project can contribute, such as the pathwise assay,
  reference artifacts, additional hardware validation, or maintained tests;
- a proposed division of labor and authorship discussion proportionate to
  contribution;
- freedom to decline without being portrayed as endorsing or obstructing the
  result.

If the authors decline or do not respond, the work may proceed independently.
It must then state that configuration ambiguities remain, distinguish R3 from
R4, and avoid attributing intentions or conclusions to them.

## Success Condition for Experiment 1

Experiment 1 succeeds as research when it leaves a reproducible answer to the
tested question, including a qualified null result. Concretely, success means:

- the algorithm qualification gate has passed or failed legibly;
- cold, warm, replay, and eviction paths can be reconstructed from immutable
  records;
- numerical and behavioral outcomes are interpreted through the registered
  gates;
- implementation artifacts are sufficiently transparent to distinguish
  quantizer behavior from serving lifecycle behavior;
- limitations prevent overclaiming rather than being buried after the result.

A favorable mechanism or consequence result is not itself an acceptance
criterion.
