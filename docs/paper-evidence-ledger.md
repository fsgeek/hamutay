# Hamut'ay Paper — Evidence Ledger

*The durable, honest record of every candidate claim and exactly how well
we know it. This is the paper's declared-losses region: it lives outside
any conversation's context window so it stops evaporating on compaction.
The outline (`paper-outline.md`) draws from it; it does not restate it.*

*Built from a measurement audit, 2026-05-30. Each row is the EVIDENCE,
not the prose claim. Status tags are deliberately conservative — a claim
is only PAPER-GRADE if the data on file supports it as written.*

**Status legend:**
- `PAPER-GRADE` — data on file supports the claim as stated; reproducible.
- `PAPER-GRADE (qual)` — supported as a qualitative claim; the quantitative/distributional form is not.
- `NEEDS-RERUN` — effect is real but the stated strength outruns the statistic on file; one experiment fixes it.
- `OBSERVED` — computed but n is too thin / too confounded to assert generality.
- `HYPOTHESIS` — a hunch with no measurement tying it together.
- `ASPIRATIONAL` — capability exists but was never exercised; not yet a phenomenon.
- `METHODS-EXHIBIT` — not a result; a worked example of our own process (belongs in methods, not results).

---

## ACT 1 — What a working memory IS

| ID | Claim (as defensible) | n / data | Status | Notes & corrections |
|----|----------------------|----------|--------|---------------------|
| A1 | Tensor is a rewriter, not an accumulator: **9% structural (3-gram) survival** cycle-to-cycle | n=1 trajectory, 104 cycles, Haiku. `experiments/observation_full/observations.jsonl`; `src/hamutay/eval/content_flow.py` | **PAPER-GRADE** | Reproduces to 4 digits (0.0951). State n=1 honestly or add 2–3 seeds. |
| A2 | The rewrite preserves *meaning* while discarding *surface* | — | **NEEDS-RERUN** | ⚠️ The "71–89% semantic" number is **bag-of-words cosine, NOT embeddings** (docstrings calling it "embedding-based" are FALSE) and is **cross-condition, NOT consecutive-cycle**. Do NOT write "71–89% of meaning survives the rewrite." Needs a real embedding similarity on consecutive cycles. |
| A3 | **No model invents a declared-losses changelog** (narrow honesty asymmetry) | n≈90 models across taste_open sweeps. `experiments/taste_open/sweep_20260411_163728/` (+6 sweeps); `analyze_sweep.py` | **PAPER-GRADE (qual)** | ⚠️ The BROAD form ("never invents tensions OR uncertainty") is **FALSIFIED** — models invent `open_tensions`, `compression_tension`, `uncertainty_aware_compression`. Only the loss-changelog is clean (0 hits across 90). Needs a committed classifier to make even the narrow form a measured prevalence. |
| A4 | Self-curation works: a model managing its own memory stays coherent over hundreds of cycles | `taste.py` → 165 cycles (`experiments/taste/taste_20260323_160513.jsonl`, analyzed); `taste_open.py` → 422 cycles (`taste_open_20260331_035903.jsonl`, raw) | **PAPER-GRADE** | Best-banked of the "frontier" items. Vindicates the Pichay-doubted thesis (model can manage own memory). Caveat: n≈1 long-run per architecture; "coherent" is metrics (stable attractor size, token plateau) + eyeball, NOT a head-to-head vs external summarization. |

## ACT 2 — The mechanism underneath (and its honest limit)

| ID | Claim (as defensible) | n / data | Status | Notes & corrections |
|----|----------------------|----------|--------|---------------------|
| B1 | **Breathing is aperiodic** (CV=0.87, Poisson-like, ~zero gap autocorrelation at all lags) — NOT a 10-cycle clock | 62 inter-precursor gaps, primarily 104-cycle corpus + 4×104 growth set. `experiments/metacognitive_breathing_analysis.md` | **PAPER-GRADE** | This IS the corrected finding. Shed-and-recover is real & a perfect health discriminator (single shed recovers; consecutive = collapse). Caveat: CV rests on one primary corpus; no CI on file (gap list not emitted by a script). |
| B2 | Batch size strongly drives rewrite depth (incremental <500tok → 14% survival; reorg >2000tok → 4%) | n=1 trajectory, binned means, 104 cycles. `experiments/observation_full/content_flow_analysis.md` | **NEEDS-RERUN** | Effect is real and large. ⚠️ Word "**dominant predictor**" outruns the statistic — there's no regression / R² / variance-explained on file, only binned means. Either fit `survival ~ batch_size` or soften the wording. |
| B3 | **Curation richness is stochastic basin-selection**; no deterministic cause survives at n=1 | **n=6 identical-condition runs**, 52 cycles each. Key counts **[49,45,11,3,18,20]** (re-verified live). `experiments/ablation/baseline_run{0..5}.jsonl` | **PAPER-GRADE (qual)** | Strongest-replicated item (only true multi-run-same-condition result). Prior causal hypotheses (prompt, tools, involuntary memory, updated_regions) each FALSIFIED — all fell inside this spread. ⚠️ "**Two basins**" is interpretation; 6 points can't establish bimodality. Distributional form NEEDS-RERUN (larger n + dip test). |
| B4 | Breathing rate (0.16–0.20) & severity (0.77–0.83) are architecture-independent | n=3 single trajectories, confounded (differ in model AND arch-type AND length; one source only 10 cycles). `experiments/taste/analyze_breathing_comparison.py` | **OBSERVED** | Three close point-estimates, no within-arch replication, no equality test. "Architecture-independent" is an eyeball claim. Do not headline. |
| B5 | A1–B4 share ONE underlying stochastic attractor | none | **HYPOTHESIS** | ⚠️ No code/analysis ties breathing-timescale + batch-size + curation-basins to one mechanism. Attractive, possibly the generative conjecture — but it is a HUNCH. The paper must state it as a conjecture, not assert it. Naming it honestly is part of Act 3. |

## ACT 3 — The warrant (corrections as method)

| ID | Claim | Evidence | Status | Notes |
|----|-------|----------|--------|-------|
| C1 | "~10-cycle breathing clock" → demoted to aperiodic | B1 + `project_breathing_discovery.md` correction (2026-05-26) | **PAPER-GRADE** | Killed by: longer run. |
| C2 | "~4K token ceiling" → artifact of `max_tokens=4096` silent truncation (real tensors reach 15K) | `project_hamutay_results.md` | **PAPER-GRADE** | Killed by: honest (untruncated) data. |
| C3 | "60% of declared losses fabricated" → measurement artifact (3-gram test); losses are grounded-but-paraphrased | `content_flow_analysis.md` self-correction | **PAPER-GRADE** | Killed by: better measurement (BoW vs 3-gram). |
| C4 | Deterministic cause of curation richness → falsified; it's stochastic | B3 | **PAPER-GRADE** | Killed by: bigger n (the n=6 null). |
| C5 | The breathing detector in `src/hamutay/eval/trajectory.py` operationalizes `breathing` as `meta_acf_lag10 < -0.05` — i.e. it still encodes the repudiated lag-10-clock hypothesis | code, lines ~318–432 | **METHODS-EXHIBIT** | ⚠️ Instrument disagrees with corrected claim B1. This is fossilization applied to OUR OWN CODE: correction (markdown) accreted, husk (code) uncomposted. Use as a methods exhibit (the mechanism generalizes to the researchers), THEN fix it (pass 2). Do not cite this code as the measurement instrument until fixed. |

## FUTURE WORK — observed but unmeasured (labeled by exactly how thin)

| ID | Phenomenon | What's real vs thin | Status |
|----|-----------|---------------------|--------|
| F1 | **Ungated bash never abused** | Tool genuinely unscoped (`subprocess shell=True`, no deny-list, intentional per docstring); full logging real (`executor.py:160`, SHA-256 hashed). "Never abused" = **0/277 harmful commands in ONE run** (audited live), reached outside project_root (`../Mallku`) only to read gifts. No harm-audit script, no adversarial/red-team condition ever run. Akrasia link (action gap = accidental brake) is a mechanistic argument, n=1. | **OBSERVED** (capability+logging verified; safety claim thin) |
| F2 | **Memory is RAG-like-but-not-RAG** | MECHANISM code-verified: `search_memory` reads the curated tensor (`prior_states`), never the raw transcript — so retrieval inherits the forgetting (this is the distinction from RAG: searching a living self-account, not a frozen corpus). EFFECT (evaporation) is n=2 qualitative and confounded by B3 (stochastic basins). Designed fix (transcript-channel search) gated on Yanantin, UNBUILT. | **OBSERVED** — claim the mechanism, not a rate. The "inadequate" intuition is correct & specific: indexes 1 of 2 channels. |
| F3 | **Commune: response-collapse ≠ tensor-collapse** | Real code + 87 data files + quantified analysis (n-gram, pause-detection, key divergence), 8 conditions. But n=1–3 per condition, prompt-sensitive, prior headline claims self-corrected (triads "collapse faster" → "skip arguing"). Critical cross-model run past collapse threshold never finished. | **OBSERVED** (thin, internally flagged nondeterministic) |
| F4 | **Lattice / merge / offspring / continuity / voluntary termination** | tiksi HAS the substrate: `BRANCHES_FROM`, `BRIDGES`, `predecessors_in_scope` (multi-parent). hamutay uses ONLY linear single-predecessor `REFINES` (`apacheta_bridge.py:92`). **Zero non-REFINES edges authored in ANY logged run.** No merge/fork/recohere/continuity code. Mallku DESIGN.md = external existence proof of distinct-parents joint-successor merge. | **ASPIRATIONAL** — capability exists, unexercised. Not yet a phenomenon; calling it one would overclaim. This is the live frontier (the "fun" the blog points at). |

---

## The shape this gives the paper

- **Act 1** stands on A1, A3 (narrow), A4. A2 must be re-run or dropped.
- **Act 2** stands on B1 and B3 (both PAPER-GRADE). B2 needs a regression or softer wording. B4 is OBSERVED-only. B5 is the conjecture the paper is honest about.
- **Act 3** is C1–C4 as method, with C5 as the methods exhibit that makes the fossilization mechanism self-applying.
- **Future work** is F1–F4, each labeled by its thinness — the paper's own declared losses.

## Recurring confounds (the two that keep eating effects)
1. **Batch-size mixture** — most single-trajectory means are mixtures over an uncontrolled batch-size distribution (B2 is the confound promoted to a finding).
2. **Single-trajectory path-dependence / stochastic basins** — apparent between-condition differences keep turning out to be within-condition variance (B3 is this confound promoted to a finding).

Both confounds-turned-findings are the empirical seed of the B5 conjecture. That is *why* the hunch is attractive — but attraction is not measurement.
