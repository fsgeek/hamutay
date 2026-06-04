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
| A2 | Consecutive rewrites remain semantically close while surface form is discarded: **0.870 mean content-embedding cosine** vs **0.095 mean 3-gram survival** | n=1 trajectory, 104 cycles / 103 transitions, Haiku. `experiments/observation_full/embedding_similarity_analysis.md`; `src/hamutay/eval/semantic_flow.py` using `BAAI/bge-large-en-v1.5` | **PAPER-GRADE** | This replaces the false "71–89% semantic" claim. That old number was bag-of-words cosine and cross-condition. New result is consecutive-cycle tensor-to-tensor embedding similarity. Do not overread it as proof every important fact survived. |
| A3 | **No model invents a declared-losses changelog** (narrow honesty asymmetry) | n≈90 models across taste_open sweeps. `experiments/taste_open/sweep_20260411_163728/` (+6 sweeps); `analyze_sweep.py` | **PAPER-GRADE (qual)** | ⚠️ The BROAD form ("never invents tensions OR uncertainty") is **FALSIFIED** — models invent `open_tensions`, `compression_tension`, `uncertainty_aware_compression`. Only the loss-changelog is clean (0 hits across 90). Needs a committed classifier to make even the narrow form a measured prevalence. |
| A4 | Self-curation works: a model managing its own memory stays coherent over hundreds of cycles | `taste.py` → 165 cycles (`experiments/taste/taste_20260323_160513.jsonl`, analyzed); `taste_open.py` → 422 cycles (`taste_open_20260331_035903.jsonl`, raw) | **PAPER-GRADE** | Best-banked of the "frontier" items. Vindicates the Pichay-doubted thesis (model can manage own memory). Caveat: n≈1 long-run per architecture; "coherent" is metrics (stable attractor size, token plateau) + eyeball, NOT a head-to-head vs external summarization. |

## ACT 2 — The mechanism underneath (and its honest limit)

| ID | Claim (as defensible) | n / data | Status | Notes & corrections |
|----|----------------------|----------|--------|---------------------|
| B1 | **Breathing is aperiodic** — NOT a 10-cycle clock; inter-precursor gaps are **Poisson-like, mildly under-dispersed (CV ≈ 0.84, N = 60)**. | `experiments/breathing_cv.py` (NEW 2026-06-03) emits the gap aggregate across 5 sessions (observation_full + Pichay/Arbiter/Thesis/Uncapped) and self-checks against the on-file n=10 list `[12,7,12,5,1,16,10,5,9,8]`. Source narrative: `experiments/metacognitive_breathing_analysis.md`. | **PAPER-GRADE** | ✅ RE-GROUNDED 2026-06-03 (was NEEDS-RERUN(quant)). The rerun ran: `breathing_cv.py` reproduces the on-file gap list exactly (detector = `n_losses==0 and not has_ifn`), then computes the 5-session aggregate **CV=0.841, N=60** — NOT the hand-counted "0.87/62"; that exact figure was a prose artifact reproducible from no corpus boundary (4×104-only gives CV=0.922/N=50). Both slicings bracket 0.87 and confirm aperiodic, under-dispersed gaps (Poisson exponential → CV=1.0). **Cite "CV≈0.84, N=60, aperiodic" from `breathing_cv.py` — not "0.87/62".** Shed-and-recover-as-health-discriminator (single shed recovers; consecutive = collapse) is separate and still holds. |
| B2 | Batch size strongly stratifies rewrite depth but is **not** a dominant one-variable predictor: <500tok → 14.1% survival; >2000tok → 4.1%; `survival ~ log1p(batch_tokens)` gives R²=0.034 | n=1 trajectory, 104 cycles / 103 transitions. `experiments/observation_full/batch_survival_regression.md`; `src/hamutay/eval/batch_survival.py` | **PAPER-GRADE** | Effect is real as a modulator/confound and large in bins, but transition-level variance is mostly elsewhere. Do not write "dominant predictor." |
| B3 | **Curation richness is stochastic basin-selection**; no deterministic cause survives at n=1 | **n=6 identical-condition runs**, 52 cycles each. Key counts **[48,44,10,2,17,19]** (`n_top_level_keys`, cycle-excluded; re-verified live 2026-06-03). `experiments/ablation/baseline_run{0..5}.jsonl` | **PAPER-GRADE (qual)** | Strongest-replicated item (only true multi-run-same-condition result). Prior causal hypotheses (prompt, tools, involuntary memory, updated_regions) each FALSIFIED — all fell inside this spread. ⚠️ "**Two basins**" is interpretation; 6 points can't establish bimodality. Distributional form NEEDS-RERUN (larger n + dip test). ⚠️ CORRECTED 2026-06-03 (was `[49,45,11,3,18,20]`): the old vector was raw `len(state)` **including** the bookkeeping `cycle` key; the experiment's own self-named field `n_top_level_keys` (= `len([k for k in state if k != 'cycle'])`, `taste_open.py:1752`) emits `[48,44,10,2,17,19]`, uniformly one lower. "Key counts" means the field, not raw dict size — every entry had drifted +1. Substance untouched: spread is now 24.0× (48/2) vs the old 16.3× (49/3), same qualitative basin structure. |
| B4 | Breathing rate (0.16–0.20) & severity (0.77–0.83) are architecture-independent | n=3 single trajectories, confounded (differ in model AND arch-type AND length; one source only 10 cycles). `experiments/taste/analyze_breathing_comparison.py` | **OBSERVED** | Three close point-estimates, no within-arch replication, no equality test. "Architecture-independent" is an eyeball claim. Do not headline. |
| B5 | A1–B4 share ONE underlying stochastic attractor | none | **HYPOTHESIS** | ⚠️ No code/analysis ties breathing-timescale + batch-size + curation-basins to one mechanism. Attractive, possibly the generative conjecture — but it is a HUNCH. The paper must state it as a conjecture, not assert it. Naming it honestly is part of Act 3. |

## ACT 3 — The warrant (corrections as method)

| ID | Claim | Evidence | Status | Notes |
|----|-------|----------|--------|-------|
| C1 | "~10-cycle breathing clock" → demoted to aperiodic | B1 + `project_breathing_discovery.md` correction (2026-05-26) | **PAPER-GRADE** | Killed by: longer run. |
| C2 | "~4K token ceiling" → artifact of `max_tokens=4096` silent truncation (real tensors reach 15K) | `project_hamutay_results.md` | **PAPER-GRADE** | Killed by: honest (untruncated) data. |
| C3 | "60% of declared losses fabricated" → measurement artifact (3-gram test); losses are grounded-but-paraphrased | `content_flow_analysis.md` self-correction | **PAPER-GRADE** | Killed by: better measurement (BoW vs 3-gram). |
| C4 | Deterministic cause of curation richness → falsified; it's stochastic | B3 | **PAPER-GRADE** | Killed by: bigger n (the n=6 null). |
| C5 | The breathing detector in `src/hamutay/eval/trajectory.py` operationalized `breathing` as a lag-N ACF threshold — encoding the repudiated lag-10-clock hypothesis. **Composted 2026-06-01** (commit `2875355`). | code; before/after in git history | **METHODS-EXHIBIT (now with a deeper twist)** | The husk went TWO levels deep, and that is the stronger exhibit. (1) A prior pass *renamed* `meta_acf_lag10`→`lagN` and wrote a corrected docstring — making it LOOK composted — while the executable `return` still computed the clock. Correction accreted in prose; husk persisted in code, **inside the very property whose job is to detect that pathology.** (2) The corrected docstring's own prescription (`recovery + precursor_rate`) was *still wrong in the same direction* — the rate term smuggles in the frequency-matters assumption B1 rejects (frequency is aperiodic noise, CV≈0.84 per `breathing_cv.py`; only recovery + non-consecutiveness carries health). (3) B1's collapse discriminator (consecutive precursors) was **named 3× in prose, computed 0× in code** — the fossil was camouflage for a detector that was never built. The 2026-06-01 fix added `consecutive_precursor_rate` and re-grounded `breathing = recovery≥0.8 AND consecutive_rate == 0.0`. (4) **THE FIX HAD ITS OWN UNCAUGHT HUSK — found 2026-06-03 by a three-lens fossil hunt, proven against the real `process_health`.** That `== 0.0` term made `breathing` return **`False` on observation_full**, the canonical healthy-breathing exemplar B1 itself rests on — because cycles 51-52 are a consecutive precursor pair that *recovers at 53* (`metacognitive_breathing_analysis.md`: "one two-cycle pair (51-52) recovers at 53"). The detector named `breathing` rejected the data that *defines* breathing. The `== 0.0` conflated "contains any consecutive pair" with "is collapsing"; recovery already captures collapse (an unrecovered pair drags the rate down). Also: recovery_rate is 0.83–0.91 across all 5 sessions, so `>= 0.8` is near-vacuous and `== 0.0` did all the work — backwards. Fixed: dropped the `== 0.0` term (`breathing = recovery≥0.8`); pinned by `tests/test_breathing_observation_full.py` (observation_full must read as breathing, and must still contain a recovering consecutive pair so the test isn't vacuous). Exhibit value, now FOUR levels: correction-and-deletion decouple in time, a husk can hide an *absence*, "renamed it" reads as "fixed it", **AND the proudest self-correction — the methods-exhibit that proves the system catches its own husks — itself shipped a husk in the catching line, uncaught for two days until independent adversarial eyes (not the author's own review) found it.** This is the single sharpest instance in the corpus of the through-line's own limit: a mind cannot reliably catch its own fossils from inside; it took a fork that never formed the C5 success-story to see the floor under it. The property feeds only `summary()` (no paper claim depends on it), so this was a latent exhibit, not a live-result error. *Now* safe to cite — with this correction as part of the exhibit. |

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
