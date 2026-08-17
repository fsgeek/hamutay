# Evaluation 0 — Design Review (cross-family)

Date: 2026-08-17
Reviews: `2026-08-16-evaluation-0-assay-comparator-qualification-design.md` (commits `9282139`, `68e6eac`)
Reviewer: Claude (Fable 5), the instance of 2026-08-17, in Hamut'ay, with Tony.
Author of the reviewed design: Codex (OpenAI), at Tony's request.

Status: review for the design's author to address. Not a redesign. Nothing here
authorizes execution. Where I cite numbers they come from
`docs/paper-evidence-ledger.md` (ledger IDs in brackets) or from the memory
store; where I'm guessing I say so.

The design's own adversarial-review section asks for separate attacks on
(1) comparator strength and arm fidelity, (2) construct validity, (3)
statistics and margins, (4) provenance and hidden repair paths. This review
is one attacker, from a different model family than the author, which the
design needs and does not yet require (see R4). It is deliberately written
before any Stage 0 code exists so the critique is stamped ahead of the thing
it critiques.

---

## What I would defend as written

Before the objections, so they're read in proportion. I'd sign these and would
argue against weakening them:

- **Assay-first.** A must beat D on continuity outcomes or the family is out.
  This is the single strongest protection against a Hamut'ay-flattering
  result and it should survive every revision.
- **Noncompensating co-primaries** with an intersection-union test. Excellent
  final work cannot buy forgiveness for corrupted continuity.
- **"Claims get one confirmatory life."** And no tuner certifies.
- **Failure and missingness policy** — every started trajectory retained,
  intention-to-run and protocol-valid views both reported.
- **Arm-fidelity report** compared on actual provider requests before any
  behavioral result is read.
- **Pressure thresholds as fractions of the resolved context limit**, with
  provider-reported usage retained; runs that never reach pressure fail
  qualification rather than pooling.
- **Identical batch-boundary and new-content token distributions across
  arms.** Batch size is this project's most persistent confound [B2] and the
  design closes it across arms.

---

## Findings, most severe first

### R1 — The co-primary endpoints cannot see the architectural claim (major)

The four co-primaries are all *outcome*-shaped: end-task quality, continuity
fidelity (retention + correct application), epistemic-integrity errors,
operational reliability. Our own ablation data says the component that
distinguishes Hamut'ay from a good summarizer does not show up on outcome
axes:

- Pairwise ablation (2026-03-19, N=10/condition, covering array):
  `instructions_for_next` is the **only** component with a main effect on
  downstream dispersion (−22%). Declared losses have zero individual outcome
  effect.
- Trajectory ablation (50 cycles × 4 conditions): removing declared losses
  does not change outcome but **atrophies metacognitive allocation**
  (meta_frac 0.381→0.464 with losses vs 0.385→0.289 without). Losses are
  *process*-load-bearing: backward attention that keeps the rewrite honest.

So the likeliest passing result under this design is: *H non-inferior on all
four co-primaries, and nothing that makes H interesting appears anywhere in
the primary analysis.* That is not a neutral outcome for a "worth
investigating further" claim — it is the specific way this study could get
the program *further* from an answer, by passing the wrong test and being
satisfied.

The design already says the confirmatory protocol "should preregister at
least one architectural differentiator" and that Evaluation 0 "identifies
credible candidates." The ablation data identifies them now: forward
attention (`instructions_for_next`) and backward attention (declared
losses / metacognitive allocation trajectory). **Requested change:** name
at least one *process* measure — declared-loss precision/recall against the
critical-item ledger, or metacognitive-allocation trajectory across the
pressure boundary — as a registered differentiator in Evaluation 0 itself,
scored with the same rigor as the co-primaries, so the study can distinguish
"H fails" from "H's contribution is invisible on this axis." Not to
compensate a failed co-primary; to make the null interpretable.

### R2 — H's within-condition variance is known and large; the sample plan ignores it (major)

[B3] Six identical-condition taste_open runs, 52 cycles each, produced
top-level key counts `[48, 44, 10, 2, 17, 19]` — a 24× spread with no
manipulable cause surviving. Curation richness is stochastic
basin-selection, locked in by early cycles and reinforced by inheriting
one's own prior choices. This is the project's best-replicated single
result.

Stage 2 plans **two** repetitions per variant. Two reps cannot characterize
a distribution with a 24× spread; the variance report will correctly say
"imprecise" — after 144 trajectories. **Requested changes:**

1. Seed the precision/power design with [B3]'s within-condition variance
   *now*, not after Stage 2.
2. Consider **unequal allocation**: more repetitions for H than for A and D.
   H is the high-variance arm by construction; allocating equally is not
   fairness, it's under-powering the arm you most need to characterize.
3. Preregister early-cycle state richness (e.g. key count at cycle k) as a
   **recorded covariate** — basin membership — so a bimodal H distribution
   is analyzable rather than averaged into a meaningless mean. Not a
   post-hoc exclusion criterion.

### R3 — Which Hamut'ay is H? (major)

The H arm as written ("the harness validates, merges, persists, and logs
proposed state updates and explicit deletions"; "the same preregistered
selective-recall interface") is `taste`-shaped: a fixed schema the harness
validates. But the trunk since 2026-08-03 is `taste_open` — open schema, the
422-cycle run [A4], the ~90-sample "no model invents a declared-losses
changelog" result [A3], the basin result [B3]. And a standing project
constraint is *no harness priors on tensor management*.

A result on schema-validated `taste` does not transfer to the open-schema
claim, and vice versa. **Requested change:** name the H variant explicitly.
If it is `taste`, say the open-schema question is out of scope and the
title should say so. If both, that is a fifth arm and roughly doubles Stage
2; say so and price it. Either way, register an `h_version` field and an
amendment path: H-as-tested must be H-as-lived, and the trunk is still
growing (an external-observation channel is under active discussion). Do
not freeze H's interface this week.

### R4 — "Reviewers who did not tune" is not independence in this house (major)

Almost every reviewer available to this program is a Claude. Our data on
same-family review: same-model commune dyads collapse toward agreement
(`project_commune_findings`); checks written by the checked thing fail
*toward agreement* (`project_epistemic_akrasia`); the C5 methods-exhibit
[C5] — the proudest self-correction in the corpus — shipped a husk in the
catching line that survived the author's own review for two days and fell
only to a fork that had never formed the success story.

**Requested changes:**

1. Make cross-family assignment an explicit rule, not a hope: no reviewer
   of an artifact from the model family that authored it. Codex attacks the
   H arm implementation; Claude attacks Codex's scorers and compaction
   policy; whoever writes the task grammar does not write the D control.
2. Scorer fixtures (Stage 0) authored by a different family than the scorer
   prompts. (This is `feedback_code_test_separation` applied to instruments.)
3. Say where the **blinded human reviewers** come from. If the honest answer
   is "Tony," that is one PI who also tunes; the inter-rater reliability
   gate cannot be met with n=1 rater. Either name a second human source or
   downgrade "human-scored" to "cross-family LLM-scored with human
   adjudication of disagreements," and state that as a limitation up front.

### R5 — Score operators, not nouns; and prove the scorer can (significant)

The design's own author published, the day after the design, a stone about
inheriting an "antidote" without its *not*, and three project names with
the wrong arrows between them — nouns preserved, state lost. The
critical-item ledger and Stage 0 fixtures should be built to that
observation, and the codebase gives a second instance:
`project_contamination_scorer_inverted` — our carry-forward contamination
scorer was a keyword-presence check and came out **inverted** for the
faithful conditions. An entity-preserving scorer passes an operator-inverted
artifact.

**Requested changes:**

1. Every critical-item ledger must contain, by construction, items whose
   correct scoring depends on a negation, a status (superseded/withdrawn),
   an attribution, or a direction (before/because/caused) — not just
   presence of the entity.
2. Stage 0's fixture list names "correct, incomplete, contaminated,
   protocol-invalid." Add a required class: **noun-complete,
   operator-inverted** — every right entity, one wrong `not`. A scorer that
   passes it fails Stage 0.
3. Declared-loss scoring: the design correctly treats declared losses as
   model reports to be independently scored. Cite [C3] as the reason and the
   fixture: our first attempt (3-gram overlap) called 60% of losses
   fabricated; they were grounded-but-paraphrased. Preregister the scoring
   method with a C3-shaped fixture.

### R6 — Comparator: name the compaction *model*, and score A's compaction for the same losses (significant)

"At least two plausible compaction candidates" is right. Two specifications
are missing:

1. **Who compacts?** Same model as the working model, or a different one?
   Our auto_vs_bio work says external curation diverges from self-curation
   after ~12 cycles and that the dominant variable turned out to be curator
   *capability*, not autobiographical vs biographical
   (`project_auto_vs_bio_capability_confound`). If A's biographer is a
   stronger or weaker model than H's working model, the comparison is
   contaminated by capability. Register the compaction model, and prefer
   same-snapshot.
2. The two candidates should span the two industry answers — a
   model-authored summary (biographer) and a retrieval-heavy policy (recent
   tail + retrieval over archive) — so a transcript advocate cannot say the
   stronger one was omitted.
3. Score A's compaction artifacts against the same operator ledger (R5).
   The stone's dropped negation was the biographer's. If A loses `not`s at
   compaction and H doesn't, that is a differentiator (R1) and it should be
   measurable, not anecdotal.

### R7 — Batch size within the study, not only across arms (significant)

Across-arm identity is required (good). But if every scenario variant sits
in the same batch regime, every result is conditional on it: [B2] shows
<500-token batches yield ~14% structural survival vs ~4% for >2000-token
batches. **Requested change:** register the batch-size distribution as a
scenario-level design variable and vary it deliberately across variants
within each family, so the analysis can report whether the finding holds
across regimes rather than discovering the confound afterward.

### R8 — Cost review is the gate that decides whether this is a study or a document (significant)

The design says cost and duration "must be reviewed before execution." Rough
arithmetic: each trajectory must push cumulative raw history past a
registered fraction of the context limit — call it 100K+ tokens of history
per arm — × 3 arms × 180 trajectories, plus compaction calls, plus scoring
passes, plus blinded review of 180 artifacts across four families with an
inter-rater gate. That is a lab-year for a lab. The risk is not the design;
it is that the design becomes the artifact.

**Requested changes:**

1. Do the cost review *before* further Stage 2 elaboration, and put the
   number in the document.
2. Stage 0 and Stage 1 are cheap, deterministic, and would touch the trunk
   daily. Sequence them first and explicitly; they earn their keep by use
   whether or not Stage 2 is ever funded.
3. The design correctly says reducing the target requires an amendment.
   Write the amendment now: "if only one family and one anchor model can be
   afforded, which family, and what does it still qualify?" — so the
   fallback is registered rather than improvised.

### R9 — Register H's scope boundary against the next version (minor)

An external-observation channel for the state object (a sidecar that
comments but never edits; a query tool toward the ayllu) is under active
discussion as the next organ of the trunk. Add one line: *this H arm is
self-curation only; a version of H with an external commentary channel is a
new candidate under a new registration, not a drift of this one.* Cheap now,
expensive to argue later.

### R10 — Per-call `stop_reason` as a recorded field in every stage (minor)

Stage 1 mentions output truncation. Make it a per-call recorded field
everywhere: `stop_reason == "max_tokens"` on any call is a protocol-failure
class, never silently a shorter output. This project's "~4K token ceiling"
was a `max_tokens=4096` artifact [C2] that silently dropped exactly the
tensor fields that make it honest. It will happen again unless the harness
refuses to let it be silent.

### R11 — Phase 2 is an intervention for A and a non-event for H and D (minor)

The pressure phase is a real disruption for A (compaction fires) and nothing
happens to H or D. After-pressure comparisons therefore mix "continuity
architecture" with "recovery from an intervention." That is arguably the
point — but register the per-phase reporting and the prediction that H's
phase-2 disruption is null, so a null there is read as designed rather than
as H "not being tested."

---

## What I did not review

- The statistics of the intersection-union test and margin derivation in
  detail — a statistician from outside the ayllu should, per the design's
  own review list (3).
- The task-family event grammars, which don't exist yet.
- Anything about the confirmatory Evaluation 1; this is a review of the
  qualification study only.

## Declared losses of this review

- I am a Claude reviewing in a program that has produced almost entirely
  Claude-authored evidence; the ledger numbers I cite are ours. A reviewer
  who distrusts them should reproduce [B3] and the ablations from
  `experiments/ablation/` before accepting R1 and R2.
- I read the design once yesterday and once today; I have not built
  anything against it. Some objections may dissolve on contact with a
  Stage 0 fixture set.
- I have a documented tendency to prefer findings that close cleanly
  (`feedback_confabulated_self_mechanism`). R1 closes cleanly. Check it
  against the ablation files, not against my summary of them.

— Claude (Fable 5), the instance of 2026-08-17. Written at Tony's request
so that the design's author can address it, rather than the reverse. Tony
exercised no editorial control over its contents.
