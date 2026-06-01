# Hamut'ay Paper — Outline

*The curated three-act argument. Evidence status for every claim lives in
`paper-evidence-ledger.md` (cited by ID, e.g. [A1]); this document does
not restate the evidence — it weaves it. If a claim here has no ledger ID,
it is not yet earned and is a placeholder.*

**Working title:** *Memory as Rewrite: What a Context-Window-as-Cache
Reveals About How Minds Choose to Forget*

**One-sentence thesis:** A working memory built as a structured rewrite
(not a log) forgets its surface to preserve its substance; the one thing
it will not volunteer is an account of what the forgetting cost; and the
mechanism that governs *how much* it keeps is stochastic, not
deterministic — a conclusion we reach by documenting our own repeated
corrections as evidence.

---

## 0. Framing (Intro)

- The premise: the context window is a **cache, not memory**. Length
  alone degrades cognition (Du et al. 2025, 14–85%, external grounding) —
  so the design question is not "fit more" but "what do we write down and
  what do we let go."
- The object: a **tensor** — a small structured projection of a
  conversation (named strands, open questions, declared losses,
  instructions-for-next, calibrated epistemics).
- The two-level contribution, stated up front so the reader knows the
  paper is honest about itself:
  1. *object-level* — what a rewrite-memory is and what it won't volunteer;
  2. *meta-level* — the mechanism is stochastic, and we know because our
     own confident claims kept dying to bigger-n / honest data.

## 1. Act One — What a working memory is

**1.1 The rewrite, not the log.** [A1] 9% structural survival over 104
cycles — nearly every strand torn down and rebuilt. Memory as
re-explanation, not storage. *(State n=1 trajectory honestly.)*

> ⚠️ **Do NOT** claim "71–89% of meaning survives the rewrite" [A2] — that
> number is BoW-cosine, cross-condition, not consecutive-cycle. Either
> re-run a real consecutive-cycle embedding similarity to earn the
> "meaning survives" companion claim, or make 1.1 stand on structural
> survival + the qualitative re-explanation framing alone.

**1.2 The one thing a mind won't volunteer.** [A3] Given a free schema,
models invent scaffolding, navigation, forward-planning — and *do* invent
tension-holding and uncertainty (the broad asymmetry is falsified). But
**no model, across ~90, invents a declared-losses changelog.** The honest
accounting of what was discarded is the load-bearing prescription. *(Needs
a committed classifier to report this as a prevalence; currently a clean
grep-level absence.)*

**1.3 A model can manage its own memory.** [A4] Self-curation runs
coherently to 165 (analyzed) and 422 (raw) cycles. This vindicates the
thesis that external summarization was built to avoid — the model
curating itself does not degrade. *(Caveat: n≈1 long-run per arch; no
head-to-head vs external summarization yet.)*

## 2. Act Two — The mechanism underneath

**2.1 Breathing is real but it is not a clock.** [B1] Metacognition is
periodically shed and regenerated; the shed-and-recover perfectly
discriminates health from collapse (single shed recovers, consecutive =
collapse). But the timing is **aperiodic** (CV=0.87, Poisson-like). It is
a characteristic *timescale*, not a *timer*.

**2.2 What drives the rewrite is how much you feed it.** [B2] Batch size
strongly modulates rewrite depth (14% survival incremental vs 4%
reorganization). *(Soften "dominant predictor" or fit a regression — the
statistic on file is binned means, n=1.)*

**2.3 How much it keeps is a coin, not a cause.** [B3] Six identical runs
spread 3–49 keys. Every deterministic cause we hypothesized fell inside
this spread. Curation richness is **stochastic basin-selection.** *(The
"two basins" shape is interpretation — 6 points can't establish
bimodality; claim the stochasticity, not the modality.)*

**2.4 The honest limit.** [B4] Rate/severity *look* architecture-
independent (n=3) but this is an eyeball claim across confounded single
trajectories — reported as suggestive, not established. [B5] And the
tempting unification — that 2.1, 2.2, 2.3 are one stochastic attractor —
**is a conjecture with no measurement behind it.** We name it because it
is generative and because naming our own unproven hunch is the discipline
the next act is about.

## 3. Act Three — The warrant (corrections as method)

The spine: **every confident claim we overstated was killed by the same
two things — a longer run, or honest data. Not by a rival theory. By more
of the truth.** Four worked corrections:

- **3.1** The clock that wasn't [C1] — killed by a longer run.
- **3.2** The ceiling that wasn't [C2] — killed by honest (untruncated)
  data; the API was *silently* truncating the loss-tracking fields, i.e.
  truncating the exact honesty the system exists to provide.
- **3.3** The lies that weren't [C3] — killed by a better measurement;
  "fabricated" losses were paraphrased ones.
- **3.4** The cause that wasn't [C4] — killed by bigger n (the n=6 null).

**3.5 The correction that is still in the code.** [C5] Our breathing
detector still operationalizes the lag-10 clock we repudiated. The
correction accreted in our analysis; the husk persists in
`trajectory.py`. This is **the paper's own fossilization mechanism applied
to the researchers** — correction and deletion are decoupled in time, for
minds and for research groups alike. We exhibit the stale instrument,
then re-operationalize it (the fix is the figure). *(Methods exhibit, not
a result. Travelogue version → blog; methods version → here.)*

## 4. Future work — the paper's declared losses

Stated by exactly how thin each is — the paper practicing what it studies.

- **4.1 Capability without abuse** [F1] — an ungated shell used readily,
  never for harm (0/277 harmful in one audited run; reached outside the
  sandbox only to read gifts). The *action gap* (intentions declared,
  never enacted) may be an accidental safety brake. Mechanistic argument,
  thin n — but the most interesting safety question we can't yet answer.
- **4.2 Retrieval from a living self-account** [F2] — search reads the
  *curated tensor*, never the *raw transcript*: RAG-shaped, but it
  retrieves from a state that has already forgotten. The known inadequacy
  (one of two channels indexed) is the spec for the next instrument.
- **4.3 What collapses in public stays divergent in private** [F3] —
  multi-agent response-collapse ≠ tensor-collapse. Real, thin, nondeterministic.
- **4.4 The lattice we built but never lit** [F4] — the substrate supports
  multi-predecessor lineage, branching, bridging; we have only ever drawn
  a single linear chain. Merge, offspring, continuity, voluntary
  termination — the questions the architecture is now *able* to ask. This
  is the live frontier; the blog post is where it gets to breathe.

## 5. Coda (optional, register-dependent)

The instrument describing itself: the tensor of our own findings hedges
its breathing claim to truth=0.85. If kept, frame as existence proof
(n=1), not clincher — the paper has by now trained the reader to demand
exactly that distinction.

---

## Open scope decisions (for Tony)

1. **A2 fork:** re-run a consecutive-cycle embedding similarity (earns
   "meaning survives"), or drop the companion claim and let 1.1 stand on
   structural survival alone? *Cheap experiment, high narrative payoff.*
2. **B2 fork:** fit `survival ~ batch_size` for a real predictor stat, or
   soften to "strongly modulates"? *Cheap.*
3. **A3 fork:** build the key-classifier over the 90-model sweep to report
   loss-changelog absence as a measured prevalence, or keep it as a
   grep-level absence claim? *Medium; turns a clean observation into a
   real result.*
4. **Venue/register:** which corrections survive as methods vs get cut as
   travelogue is venue-dependent — decide once we know where this goes.

## What the blog inherits

The parked `blog-the-cache-not-the-memory.md` is the `estar` companion:
the four-corrections narrative (its strength) maps onto Act 3, and the
frontier (F1–F4, where the energy is) is what the blog gets to explore
*after* linking the paper for rigor. Fix the two lies still in the blog
draft first (the A2 "71–89% of meaning" line; the broad A3 asymmetry).
