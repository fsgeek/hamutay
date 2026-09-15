# Review: TurboQuant Cache-Path Compositionality, Experiment 1 Design

Reviewer: a Claude Fable 5 session, 2026-08-27 (evening), at Tony's request.
Reviewed: `2026-08-27-turboquant-cache-path-compositionality-design.md` at
commit a21598e. Nothing here is binding; it is one reader's findings.

Overall: the preregistration discipline (outcome vocabulary, R1–R4 ladder,
failed-gate-stays-in-record, ayni boundary) is stronger than most published
designs. The defects are concentrated in one place: the arms do not isolate
the compositional effect the title names.

## Blocking

### 1. `cold_tq` logits are `cold_bf16` logits, so M measures first-order quantization

The spec defines cold as BF16 prefill, final logit computed, *then* cache
quantized. At every checkpoint `cold_tq` therefore equals `cold_bf16`
bit-for-bit. The registered "TQ warm/cold divergence" is BF16-everything vs.
one chunk attending over a 4-bit cache: first-order quantization distortion,
already characterized by the paper. It will clear "10x the BF16 chunking
median" trivially, M will pass, and the label "numerical mechanism" will
describe "4-bit quantization changes logits".

The motivation's `TQ(TQ(prefix) + new)` vs `TQ(prefix + new)` needs a control
that is absent: a **quantize-once arm** (`tq_once`) — prefill everything but
the final chunk in BF16, quantize the cache exactly once, process the final
chunk. `warm` and `tq_once` then attend over the same quantized context; the
only difference is whether each cached entry was computed through quantized
history.

- `D(cold, tq_once)` = first-order effect
- `D(warm, tq_once)` = pathwise (compositional) effect

The spec already contains the correct test in the wrong place: the 50%
eviction fork (retained vs. reconstructed-then-continued, same tokens, same
remaining chunks, only first-half cache history differs) is a clean
compositionality test, but it is the second, optional disjunct of A.

Recommendation: gate M on `tq_once` or on the fork. Rename the current
warm/cold comparison to a separate statement, e.g. **S: serving-lifecycle
divergence** (one request vs. several — the vLLM raw-prefill /
compressed-continuation question). S is a legitimate deployment finding but
not mechanism.

### 2. A's first criterion is confounded by prefix length

"Divergence at 75% exceeds divergence at 25%" compares 12K tokens / 23
boundaries against 4K / 7. Final-position divergence grows with the count of
quantized tokens attended regardless of path dependence.

Dose–response needs fixed length, varied boundary count: at 16K, e.g. `B512`
(31 boundaries), `B2048` (7), `B8192` (1), `tq_once` (1, at the end). `Bvar`
does not do this; its boundary count is close to `B512`'s.

Note the existing arms already span the boundary axis at 0 (cold), 31 (warm),
and 16,383 (replay). Replay is the maximal-boundary arm and is used only as a
determinism control. `D(cold, replay)` vs `D(cold, warm)` gives accumulation
for free.

### 3. The eligible corpus cannot supply the registered windows

Measured at commit a21598e: `docs/**/*.md` excluding `references/` and
`superpowers/` is 61 files, 742,460 bytes — roughly 185–250K Llama tokens.
The matrix needs 688,128 tokens for 72 non-overlapping windows; the primary
stratum alone (24 x 16,384) needs 393,216. The overlap clause will fire for
most of the primary stratum, 16K windows will share most of their text with
several others, and "10,000 bootstrap resamples over distinct text examples"
will resample non-independent examples.

Either enlarge the eligible corpus (sibling repos, or a pinned public text)
or shrink the primary stratum to what the corpus supports and say so.

### 4. Model revision hash is 41 characters

`0e9e39f249a16976918f6564b8830bc894c896591` — git SHA-1 is 40. Likely a
trailing `1`. The hash-mismatch stop rule would catch it, but fix it before
stamping.

## Significant

### 5. C fires on formatting jitter, and its cold arm is BF16

"At least one paired case changes greedy output" is satisfied by `X` vs
`The code is X`. Scoring separates correctness (good) but the gate and the
outcome label key off sequence change. Split into C-seq and C-correct.

Llama 3.1 8B is near ceiling on a unique-code needle at 4–16K, so the assay
only sees near-tie decisions. Pre-select cases with small BF16 top-2 margin,
or pre-register the margin distribution so a null C is interpretable.

C compares against a cold arm that is BF16 — the same first-order confound as
M. The behavioral fork (retained vs. evicted) is the comparison that speaks
to path.

### 6. There is a recent uncompressed window; it is undeclared

Within-chunk attention is BF16. Warm has an effective uncompressed window of
0–511 tokens by position; checkpoints sit at chunk ends (window = 511); replay
has 0; cold has everything. The spec lists "no recent uncompressed window" as
a design choice. Declare it as a hidden variable across arms and define
`tq_once` with the same final chunk so its window matches warm's.

### 7. The M gate has no absolute scale

"10x the matched BF16 warm/cold median" is vacuous if that median is ~0 on
deterministic single-sequence kernels (likely); the `1e-12` floor makes it a
pass by default. Use `D(cold, tq_once)` — the first-order TQ divergence — as
the reference magnitude for the compositional excess.

## Minor

- Seed derivation: specify integer formatting (decimal, padding), whether the
  study seed is joined as hex text, and what "column signs normalized" means
  (standard: positive diagonal of R).
- Budget: replay is tokenwise. ~672K sequential steps per (cache type x
  repeat), x2 cache types x3 repeats ~ 4M single-token decodes on a 4090 —
  order of 30–40 hours before the attention diagnostic pass. Write it down so
  a shortened run is not silent.
- The paper's approximate distortion values (0.36 / 0.117 / 0.03 / 0.009)
  were not verified against the arXiv text by this review.
- Keep verbatim: "The Hamut'ay comparison must not describe its state object
  as magically free of cache history... The hypothesis is reduced or
  differently bounded exposure, not absence."

## One line

Add a quantize-once arm; gate M on it or on the eviction fork; rename the
current M to a lifecycle finding; test accumulation at fixed length; enlarge
or shrink to the corpus; fix the hash.
