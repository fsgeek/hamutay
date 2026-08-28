# TurboQuant Cache-Path Compositionality: Experiment 1 Design

Date: 2026-08-27

Status: approved and externally reviewed design. The R1 implementation plan is
authorized; live registered execution remains gated on implementation,
independent validation, and the qualification checks below.

Revised: 2026-08-27 after the external review in
`2026-08-27-turboquant-cache-path-compositionality-review.md`. The revision adds
the missing quantize-once control, separates serving-lifecycle from
compositional effects, holds sequence length and the final uncompressed window
constant in the dose comparison, and replaces the undersized local corpus.

Revised again on 2026-08-27 after external review of the R1 implementation
plan. This amendment replaces rounding-sensitive table comparisons with a
dual analytic/published-scale gate, turns the QJL bias criterion into a
simultaneous equivalence test, requires process-level determinism and an
independent adversarial-test checkpoint, and pins the author-kernel compiler
environment.

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

### S: serving-lifecycle divergence

One full BF16 prefill and a continuation over retained quantized KV can produce
different logits for identical visible input. This is a deployment-relevant
raw-prefill/compressed-continuation effect, but it combines first-order
quantization with cache-path history and therefore does not establish
compositionality.

### M: compositional mechanism

For the qualified TurboQuant configuration, two paths that attend through the
same amount of four-bit cached context and share the same final 512-token
uncompressed chunk diverge according to whether the cached entries were all
computed in one BF16 prefill or were themselves computed through earlier
quantized cache states.

### A: accumulation

At a fixed 16,384-token visible prefix and fixed 512-token final uncompressed
chunk, compositional divergence increases with the number of quantized-prefix
continuation boundaries.

### E: eviction discontinuity

At a fixed visible checkpoint, discarding a recursively constructed quantized
cache, rebuilding that prefix in one BF16 prefill, quantizing it once, and then
continuing through identical remaining chunks can produce a discontinuity
relative to an otherwise matched retained-cache trajectory.

### C-seq and C-task: consequence

For at least one registered behavioral task, the compositional cache path
changes the greedy decoded sequence (`C-seq`) or semantic task correctness
(`C-task`) while visible input and the immediate uncompressed window remain
identical.

M and the consequence statements are non-substitutable. Numerical divergence
can support a mechanism claim without demonstrating a practical consequence.
`C-seq` records sequence sensitivity and cannot be described as task
degradation. `C-task` records a correctness change and reports its direction.
Behavioral divergence without a qualified numerical result is an observed
system effect whose cause remains unresolved. The behavioral assay runs
regardless of the numerical result; the numerical outcome controls the
interpretation, not whether the behavioral data are collected.

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
2. a single-GPU reference assay comparing cold, quantize-once, fixed-depth warm,
   eviction, and replay paths for fixed token prefixes, including a small
   mandatory behavioral assay.

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

Let `V` be an exact visible token prefix and let its final 512 tokens be `F`.
For a model configuration `q`, define:

- `cold_q(V)`: process all of `V` as one ordinary prefill, then materialize
  the cache;
- `q1_q(V)`: process `V - F` as one BF16 prefill, materialize it once in cache
  type `q`, then process `F` through that cached prefix;
- `warm_q(V, B)`: process `V - F` in chunks separated by boundary schedule `B`,
  retaining cache type `q` between chunks, then process the same `F`;
- `replay_q(V)`: reconstruct the trajectory token by token using the same
  quantized-past rule from the first token onward.

Cold and warm represent ordinary serving paths. In the TurboQuant arm, `q1` is
the quantize-once counterfactual that isolates first-order quantization from
compositional cache history; in the BF16 arm it is the matched two-chunk
control. Replay is a semantic equalization control. If a deterministic replay
after cache loss does not reproduce the prior replay state, the harness is
defective or an unrecorded source of nondeterminism remains. Replay is not
claimed to be a normal server policy.

Within any multi-token chunk, causal attention uses uncompressed BF16 K/V for
tokens in that chunk. Tokens from retained earlier chunks use the cache type
named by the arm. At chunk completion, new K/V entries are retained as BF16 or
quantized exactly once according to the arm. `q1` and every compositional dose
arm therefore have the same effective 512-token recent uncompressed window at
the final measurement. The cold arm has a fully uncompressed prompt and replay
has a one-token uncompressed window; neither is used as the counterfactual for
M. There is no additional deliberately retained recent-token buffer.

The three primary paired distances are:

```text
S_q(V)    = distance(output(cold_q(V)), output(q1_q(V)))
M_q(V, B) = distance(output(q1_q(V)), output(warm_q(V, B)))
R_q(V)    = distance(output(replay_q(V)), output(reconstructed_replay_q(V)))
```

`S_q` measures first-order serving-lifecycle quantization. `M_q` measures the
additional pathwise effect after matching quantized prefix length and the final
uncompressed window. `R_q` checks deterministic reconstructability. Matched
uncompressed-BF16 schedules measure chunking, kernel, and finite-precision
effects that do not require lossy KV storage; they are not treated as
mathematically zero.

## Frozen Reference Configuration

### Hardware and model

- Device: the local NVIDIA RTX 4090, one process and one experimental sequence
  at a time.
- Qualification userspace: WSL2 Ubuntu 22.04.5. The author QJL extensions are
  compiled with the side-by-side CUDA 12.8 WSL-Ubuntu toolkit selected through
  `CUDA_HOME=/usr/local/cuda-12.8`; CUDA 13.2 remains the system default and no
  Linux NVIDIA driver is installed inside WSL.
- Model: `meta-llama/Meta-Llama-3.1-8B-Instruct`.
- Model and tokenizer revision:
  `0e9e39f249a16976918f6564b8830bc894c89659`.
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
- no entropy coding, mixed-precision channels, outlier channel policy,
  additional recent-token buffer, or boundary-layer exemption is used. The
  serving lifecycle's immediate uncompressed chunk is a declared experimental
  variable and is fixed at 512 tokens for compositional comparisons.

This is named `tq_ref_kprod4_vmse4`; it is not called the paper's 3.5-bit
configuration. Uniform four-bit storage removes the paper's underspecified
mixed-channel allocation from the first causal test.

Random objects are fixed by the 128-bit study seed
`0b311d5d4eceaf773efde389305a1b5a`. In seed-derivation strings it appears as
those 32 lowercase hexadecimal characters without a `0x` prefix. Integer fields
use unpadded base-10 ASCII; role and purpose labels use their exact lowercase
manifest strings. A sub-seed is the first 16 bytes, interpreted as an unsigned
big-endian integer, of SHA-256 over the UTF-8 string formed by joining the study
seed, model revision, algorithm, layer index, K-or-V role, KV-head index, and
purpose label with `|`. Dense matrices are generated from an iid standard
Gaussian and orthogonalized with QR. For each `i`, column `i` of `Q` is
multiplied by `sign(R[i,i])`, with zero assigned sign `+1`, so the diagonal of
`R` is nonnegative. The resolved matrices, codebooks, and hashes become
immutable run inputs.

The QJL qualification reports both the paper-literal iid Gaussian projection
and the row-orthogonalized projection used by the public QJL implementation.
The latter is scaled by `sqrt(d)` after QR so its row norms match the expected
Gaussian-row norm. Only the paper-literal form enters
`tq_ref_kprod4_vmse4`. The second form is a declared sensitivity result.

## Algorithm Qualification Gate

No model-level TurboQuant result is interpreted until all of these checks pass:

1. **Round-trip determinism.** A frozen vector batch produces bit-identical
   indices, signs, norms, and reconstructed FP32 values across three fresh
   same-build process executions.
2. **Analytic and published distortion scale.** For each frozen one- through
   four-bit codebook, compute the exact normalized scalar distortion in FP64 by
   integrating squared error over every Lloyd-Max cell under the registered
   dimension-128 sphere-coordinate density. On one million registered
   synthetic length-128 vectors drawn iid from a standard Gaussian, empirical
   normalized MSE must be within 0.5% relative error of that analytic value and
   within 15% relative error of the paper-reported approximate value (`0.36`,
   `0.117`, `0.03`, or `0.009`). The analytic comparison certifies the
   implementation; the wider published-scale comparison acknowledges the
   table's precision without discarding it.
   Before implementation, independent FP64 quadrature gave the registered
   reference values `0.36088859`, `0.11600007`, `0.03396593`, and `0.00931479`.
   These values are frozen regression expectations, not results from the
   million-vector execution.
3. **QJL bias equivalence.** Across one million registered independent
   query/key pairs, each length 128 and drawn iid from a standard Gaussian, the
   Bonferroni-adjusted 98.75% bootstrap interval for normalized mean signed
   inner-product error at every bit width must lie wholly inside the
   equivalence region from `-0.02 * error_RMSE` through
   `+0.02 * error_RMSE`. Ordinary 95% intervals are also reported as
   diagnostics but do not gate qualification.
4. **QJL distortion scale.** At one through four total bits, empirical
   normalized mean squared inner-product error is within 15% relative error of
   the paper's approximate dimension-scaled values (`1.57/d`, `0.56/d`,
   `0.18/d`, and `0.047/d`). These and the scalar-distortion values above were
   checked against the accessible arXiv text during the audit. The four-bit
   target inherits sensitivity to the paper's rounded three-bit scalar value;
   the analytic scalar residual and its `pi/2` scaling are reported as
   non-gating diagnostics, and the registered 15% tolerance is not adjusted
   after observation.
5. **Author-code differential.** On identical residual vectors, queries,
   projection matrix, residual norms, and floating dtype, the reference QJL
   component agrees with the author implementation within a frozen FP32
   tolerance of `1e-5` absolute and `1e-4` relative error. Any unavoidable
   convention mismatch is resolved and documented before the gate is evaluated,
   not waived afterward.

A failed check remains in the evidence record. Repair changes the implementation
version and requires the complete qualification gate to run again. Failure to
pass is a blocked experiment, not a negative TurboQuant result.

Before the registered qualification run, an instance from a model family other
than the implementer's authors a black-box adversarial test suite from this
specification, the published artifacts, and the frozen public interfaces,
without first reading the implementation. The tests live in a separate signed
commit. The reviewer may inspect the implementation only after freezing that
suite. Registered execution requires every valid independent test to pass and
every rejected test or review finding to have a written technical disposition
approved by the principal investigator. Reviewer approval by itself is neither
necessary nor sufficient; reproducible evidence is the gate.

## Token Corpus and Boundary Schedules

### Numerical corpus

The local-document corpus proposed in the first version is ineligible: at the
reviewed commit it contained 742,460 bytes, insufficient for the registered
non-overlapping windows. Experiment 1 instead uses the `train` split of
[`Salesforce/wikitext`](https://huggingface.co/datasets/Salesforce/wikitext/tree/b08601e04326c79dfdd32d625aee71d232d685c3/wikitext-103-raw-v1),
configuration `wikitext-103-raw-v1`, pinned at revision
`b08601e04326c79dfdd32d625aee71d232d685c3`.

The corpus builder:

- reads both train Parquet shards in lexicographic filename order and preserves
  row order within each shard;
- joins every `text` value, including empty values, with one newline;
- tokenizes once with the pinned Llama tokenizer without chat templating;
- partitions the result from token zero into non-overlapping 16,384-token pages;
- permutes page indices from the study sub-seed with purpose label
  `corpus_pages`;
- assigns the first 24 pages as 16,384-token numerical windows, the first 8,192
  tokens of each of the next 24 pages as 8,192-token windows, and the first 4,096
  tokens of each of the next 24 pages as 4,096-token windows;
- reserves the next 24 pages exclusively for the behavioral corpus: the first
  eight at 16,384 tokens, the next eight truncated to 8,192 tokens, and the last
  eight truncated to 4,096 tokens; and
- records dataset revision, Parquet hashes, row counts, combined text hash,
  complete token-stream hash, page permutation, and window token hashes.

No source interval overlaps another registered numerical or behavioral example.
If the pinned corpus does not yield at least 96 complete pages, corpus
qualification fails; overlap is not an allowed repair.

### Fixed-length boundary dose

All primary dose arms contain exactly 16,384 visible tokens and use the same
final 512-token chunk `F`. Let `P` be the preceding 15,872 tokens. A schedule
`Qm` divides `P` into `m` ordered chunks, materializing the selected cache type
after every chunk, then processes `F` as the final chunk. For general `m`, let
`a = floor(15872 / m)` and `r = 15872 mod m`; the first `r` chunks contain
`a + 1` tokens and the remaining chunks contain `a`.

The registered primary schedules are:

- `Q1`: one 15,872-token prefix prefill, quantized once, then `F`; this is
  `q1` and contains no compositional history within `P`;
- `Q2`: two 7,936-token prefix chunks, then `F`;
- `Q8`: eight 1,984-token prefix chunks, then `F`;
- `Q31`: thirty-one 512-token prefix chunks, then `F`;
- `Q15872`: tokenwise prefix construction, then the same 512-token `F`.

Total length, token identity, cached-prefix length, quantizer configuration, and
the immediate uncompressed window are therefore fixed while cache-history depth
changes. The 4,096- and 8,192-token secondary strata compare `Q1` with `Q7` and
`Q15`, respectively, using the same 512-token final window. Pure tokenwise
replay of the entire visible prefix remains a reconstructability control and is
not part of the dose trend.

### Behavioral corpus

The behavioral assay contains 24 deterministic needle-retrieval cases: eight at
each of 4,096, 8,192, and 16,384 context tokens. Each case uses its exclusively
reserved corpus page as distractor text. Let length-stratum index `k` be 0, 1,
or 2 for 4,096, 8,192, or 16,384 tokens, let local case index `j` run from 0
through 7, and let global index `i = 8k + j`. SHA-256 over the UTF-8 string
`0b311d5d4eceaf773efde389305a1b5a|needle|<i>`, where `<i>` is replaced by its
unpadded base-10 value, supplies the first six bytes for a 12-character
uppercase hexadecimal record ID and the next ten bytes for a 16-character
unpadded RFC 4648 Base32 value. A unique statement of the form
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

All paths receive identical final token IDs. Greedy decoding is limited to 32
new tokens and stops under the pinned tokenizer's ordinary EOS rules. A
candidate code is a case-sensitive match of `[A-Z2-7]{16}`. Scoring records
semantic retrieval correctness, format adherence, first generated-token
divergence, complete sequence equality, and whether either path emits multiple
candidate codes.

This is an intentionally small consequence assay, not a replication of the
paper's NIAH evaluation. It tests whether a qualified numerical path effect can
cross an observable boundary on a task with an unambiguous answer.

## Execution Arms

Every numerical token window runs through these paired arm families:

| Cache | Paths | Role |
|---|---|---|
| BF16 | cold and every matched TQ schedule | kernel and chunking controls |
| BF16 | replay | tokenwise deterministic reconstruction control |
| `tq_ref_kprod4_vmse4` | cold | fully uncompressed-prompt lifecycle endpoint |
| `tq_ref_kprod4_vmse4` | `Q1` and length-specific 512-token schedule | all lengths |
| `tq_ref_kprod4_vmse4` | `Q2`, `Q8`, `Q31`, `Q15872` | 16,384-token dose only |
| `tq_ref_kprod4_vmse4` | replay | tokenwise deterministic reconstruction control |

The behavioral corpus runs through cold, `Q1`, the length-specific 512-token
schedule (`Q7`, `Q15`, or `Q31`), and the eviction fork. It does not run `Q2`,
`Q8`, `Q15872`, or pure replay decoding.

At completion, the numerical harness records next-token logits for every arm.
At 25%, 50%, and 75%, it additionally records the length-specific 512-token
warm path and an independently constructed `Q1` counterfactual whose immediate
uncompressed window is the same 512 tokens. Dose schedules whose chunk crosses
a checkpoint are not interrupted merely to create a measurement. At 50%, the
harness forks the 512-token warm schedule. One branch retains its cache. The
other discards the cache, reconstructs the
identical visible half-prefix as one BF16 prefill, materializes it once as
TurboQuant or BF16 according to the arm, and continues through the same
remaining 512-token chunks. Comparing retained and evicted branches at 75% and
completion supplies a convergent compositionality test without uncontrolled
memory-pressure eviction. Replay is also reconstructed at 50% and must
reproduce its pre-fork state.

Arm order is deterministically permuted within each example. Each full block is
run three times. Repetition estimates execution nondeterminism; it is not
pseudoreplicated as three independent text examples.

## Measurements

### Numerical primary measurements

At the checkpoints defined above and at the final prefix, record paired
cold/`Q1`, `Qm`/`Q1`, retained/evicted, and
replay/reconstructed-replay comparisons for:

- Jensen-Shannon divergence and forward/reverse KL between next-token
  distributions;
- maximum and RMS logit difference;
- logit-vector cosine similarity;
- top-1 agreement;
- rank and logit-margin change of the `Q1` path's top token;
- layerwise normalized residual-stream difference at the final position;
- K and V reconstruction normalized MSE by layer and KV head;
- attention-distribution KL for a registered diagnostic subset consisting of
  layers 0, 7, 15, 23, and 31 and the final 16 query positions.

Distributional distances and bootstrap reductions are computed in FP64 from
recorded FP32 logits. The primary certification comparison is `Q31` against
`Q1` at 16,384 tokens: 24 distinct text examples, identical cached-prefix
length, and an identical 512-token final uncompressed chunk. `Q2`, `Q8`, and
`Q15872` estimate the fixed-length dose curve. The shorter lengths are
registered secondary estimates of length sensitivity and cannot substitute for
a failed primary comparison.

Attention diagnostics may use a slower instrumented pass over the registered
subset, but its arithmetic and cache inputs must match the primary path. If
instrumentation changes the primary logits beyond the uncompressed-BF16
nondeterminism envelope, attention KL is marked unavailable rather than mixed
with the primary result.

### Behavioral mandatory measurements

For each needle case and path, record:

- semantic retrieval correctness: the expected value appears exactly once and
  no other 16-character Base32 candidate appears;
- format adherence: the stripped output equals the expected value;
- greedy output sequence;
- index of first differing generated token;
- whether sequence, semantic correctness, or format adherence changes between
  `Q1` and the length-specific 512-token warm path;
- whether eviction restores, removes, or creates a prior difference.

For the uncompressed BF16 path, record the top-two logit margin at every
generated position and the minimum margin over the response. Cases are neither
selected nor excluded using this measurement. Behavioral results are reported
by preregistered context length and needle position, then descriptively by the
frozen BF16 margin distribution so a null or positive result can be interpreted
without enriching the corpus for near ties.

Behavioral outputs are retained even if M is not supported.

### Operational measurements

Record wall time, peak allocated GPU memory, cache bytes, token counts,
recomputation count, OOMs, kernel fallbacks, and any run repair or retry. These
describe feasibility and detect confounding; Experiment 1 makes no throughput
claim.

`Q15872` plus pure replay entails at least 4.6 million single-token prefix steps
across two cache types and three repeats before shorter strata or attention
diagnostics. The planning estimate is 30–50 RTX 4090 GPU-hours for those paths.
A development-only timing probe may refine that estimate, but a high estimate
does not authorize silently dropping a path, repeat, or example. Material scope
changes require a revised, reviewed, and newly timestamped specification.

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

For example `i`, define these Jensen-Shannon distances at completion:

```text
S_i       = JS(cold_tq_i, Q1_tq_i)
S_fp_i    = JS(cold_bf16_i, Q1_bf16_i)
P_m_i     = JS(Qm_tq_i, Q1_tq_i)
P_m_fp_i  = JS(Qm_bf16_i, Q1_bf16_i)
X_i       = JS(retained_tq_i, evicted_tq_i)
X_fp_i    = JS(retained_bf16_i, evicted_bf16_i)
```

S is detected when median `S` is at least ten times median `S_fp` and ten times
`E_JS`, the paired bootstrap 95% interval for median `S - S_fp` excludes zero,
and at least 75% of examples have `S > E_JS`. It is reported as the first-order
serving-lifecycle reference magnitude and is not evidence for M.

M is supported when all of the following hold for `P_31` in the primary
16,384-token stratum:

1. median `P_31` is at least ten times median `P_31_fp` and ten times `E_JS`;
2. median `P_31` is at least 1% of `max(median S, E_JS)`, establishing a
   registered materiality scale relative to the first-order quantization effect;
3. the paired bootstrap 95% interval for median `P_31 - P_31_fp` excludes zero;
4. at least 75% of examples have `P_31 > E_JS`; and
5. replay after reconstruction remains within its registered duplicate-run
   envelope.

A is supported when M is supported, the four medians are ordered
`P_2 <= P_8 <= P_31 <= P_15872`, and the paired bootstrap 95% interval for
median `P_31 - P_2` excludes zero. `Q15872` is retained as the maximal-depth
same-window endpoint, not substituted for replay.

E is supported when median `X` is at least ten times median `X_fp`, ten times
`E_JS`, and 1% of `max(median S, E_JS)`; the paired bootstrap 95% interval for
median `X - X_fp` excludes zero; and at least 75% of examples have `X > E_JS`.

`C-seq` is supported when at least one paired case changes greedy output between
`Q1` and the length-specific warm path, or between retained and evicted paths,
and the case is stable across all three repeats within each path. `C-task` is
supported only by a stable semantic correctness change under one of those same
compositional comparisons. Direction, format adherence, and first divergence
position are reported separately. Cold/`Q1` behavioral differences belong to S
and cannot support either C statement. With 24 cases, both C statements are
evidence of existence and bounded incidence, not population prevalence.

All intervals use 10,000 study-seeded paired bootstrap resamples over distinct
text examples. Effect distributions and individual examples are published; a
gate label does not replace them.

### Outcome vocabulary

The labels below are component conclusions rather than a forced mutually
exclusive menu; every supported target statement is reported.

- **No qualified experiment:** algorithm or determinism gate failed.
- **Serving-lifecycle divergence only:** S is measurable but M does not pass.
- **Pathwise signal below registered scale:** `P_31` exceeds controls but fails
  the 1%-of-S scale gate.
- **No detected compositional mechanism at tested settings:** qualification
  passed but M did not.
- **Numerical mechanism without detected sequence consequence:** M passed and
  `C-seq` did not.
- **Sequence sensitivity without correctness change:** `C-seq` passed and
  `C-task` did not.
- **Behavioral effect of unresolved cause:** either C statement passed and M did
  not.
- **Numerical mechanism with task consequence:** M and `C-task` passed.

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
- A missing independent adversarial-test commit, a failing valid independent
  test, or an unresolved technical disposition stops registered qualification.
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
S, M, A, E, `C-seq`, or `C-task`. Any implementation choice influenced by
development output is declared and frozen before the registered corpus is run.

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
- cold, quantize-once, dose, replay, and eviction paths can be reconstructed
  from immutable records;
- numerical and behavioral outcomes are interpreted through the registered
  gates;
- implementation artifacts are sufficiently transparent to distinguish
  quantizer behavior from serving lifecycle behavior;
- limitations prevent overclaiming rather than being buried after the result.

A favorable mechanism or consequence result is not itself an acceptance
criterion.
