# What Is a Tensor? — Empirical Findings

Results from the evaluation framework's analysis of Q2 experiment data
(104 cycles × 2 conditions, identical input, one feedback variable).

## The tensor is a categorized rewrite, not a persistent structure

Every prior description of the tensor used accumulation metaphors:
"running sum", "integrated state", "accumulated reasoning." The data
says otherwise.

**Strand stability: 9%.** Almost every strand is rebuilt each cycle.
~4.5 births and ~4.5 deaths per cycle against a strand count of 2-10.
Strand titles are ephemeral — they don't persist as persistent themes.

**Concept transience: 87%.** 87% of n-gram concepts appear in only one
cycle across 104. Only 0.9% of concepts persist for 5+ cycles, and
those are domain vocabulary ("tensor projection", "declared losses")
that would persist in any representation.

**But content persists.** Cross-condition content similarity is
0.711-0.887 across all cycles. The two conditions cover the same
semantic ground despite completely different organizational structures.

The tensor preserves content through *rewriting*, not through
*structural persistence*. Each cycle, the projector reads the prior
tensor and the new content, then writes a new tensor that integrates
both — but the *structure* of the new tensor is built fresh. The
"running sum" metaphor is wrong. It's more like rewriting a document
from memory: the ideas carry forward, but the sentences are new.

## Strand separation is a stable forced categorization

**Vocabulary specialization: 0.65.** 65% of words appear in only one
strand. Strands cover genuinely distinct semantic domains.

**Pairwise Jaccard: 0.17.** Low overlap between any two strands.

**Size distribution Gini: ~0.05.** Remarkably even allocation across
strands — the projector doesn't dump everything into one strand.

**This is stable across conditions.** Control (sees prior losses) and
treatment (no prior losses) show nearly identical separation metrics
(0.652 vs 0.655 specialization, 0.169 vs 0.171 Jaccard). The loss
feedback doesn't change how well the projector categorizes — it changes
what goes in the categories and how much budget goes to metacognition.

**Implication:** The schema's value is in *forcing categorization during
the rewrite*, not in maintaining persistent structure. When the ablation
showed `flat_strands` hurts dispersion, it was measuring the cost of
removing the categorization mandate. The projector that must organize
into strands processes the content more deeply than one that can dump
it into a single block.

## The meta/content allocation is where feedback acts

**Control (sees prior losses) final state:** 40% meta, 60% content.
**Treatment (no prior losses) final state:** 18% meta, 82% content.

The control tensor spends more than twice as much representational
budget on metacognition (declared losses, instructions_for_next, open
questions). This is the Q2 "mirror vs window" finding quantified.

But this allocation *oscillates*. At cycle 25, control is 50/50 while
treatment is 81/19. At cycle 50, it inverts — treatment goes to 70%
meta. The allocation is dynamic, not a steady drift.

**Implication:** The loss feedback doesn't just add metacognitive
content — it reshapes how the projector allocates its budget over time.
The mirror isn't free; it costs content capacity. Whether that cost is
worth paying depends on what the tensor is being used for.

## Divergence peaks and partially reconverges

**Peak divergence:** Cycle 66 (overall divergence 0.650).
**Final divergence:** Cycle 104 (overall divergence 0.285).
**Trend:** Stable (not monotonically increasing).

This is surprising for a path-dependent system. The two conditions
start from the same input and accumulate different perspectives, but
they don't drift apart indefinitely. The shared input pulls them
back together. The divergence is bounded.

**Cycle 75 anomaly:** The control tensor drops to 0% meta (content_frac=1.00)
during a landmark event (the "five-minute experiment" validation). The
projector abandoned all metacognitive machinery to record the event.
This is "flow state" or tunnel vision — high-salience events override
the normal allocation pattern.

## What this means for the tensor library

1. **The schema guides the rewrite.** Its value is categorization
   pressure, not structural persistence. This is load-bearing (ablation
   confirmed) but the mechanism is different from what was assumed.

2. **Strand identity doesn't matter.** Tracking strand persistence
   across cycles is measuring the wrong thing. Track semantic content
   persistence instead.

3. **The meta/content ratio is a key health metric.** A tensor spending
   >50% on metacognition may be "eating itself." A tensor at 0% meta
   has lost its self-awareness. The healthy range is task-dependent.

4. **Feedback changes trajectory.** Loss feedback creates more
   metacognitive allocation, different persistent concepts, and
   different analytical perspective — all from the same input. This
   confirms that the feedback channel is a real lever on tensor behavior.

5. **Content_only paradox partial explanation.** If the schema's value
   is categorization pressure during rewriting, and prose achieves the
   same content preservation without the categorization overhead, then
   prose might win on simple metrics (dispersion) while losing on
   complex properties (metacognitive capacity, task-specific organization).
   The right evaluation depends on what you're optimizing for.

## Pairwise interaction ablation (2026-03-19)

CA(8; 2, 5, 2) covering array, N=10 Sonnet runs per condition.

**IFN is the compensation hub.** Every interaction involving IFN is
synergistic — removing IFN alongside any other component produces
worse-than-additive effects. IFN absorbs the work of missing fields.

Two compensatory pairs: losses×epistemic and questions×strands_sep
(removing both is better than removing either — they interfere).

Losses, questions, epistemic, strands_sep are independent of each
other at snapshot scale.

## Multi-cycle trajectory ablation (2026-03-19)

4 conditions × 50 Haiku cycles on observation_full data.

| Condition | Strand Stability | Loss Evolution | Final Meta |
|-----------|-----------------|----------------|------------|
| full      | 0.152           | growing        | 0.461      |
| no_losses | 0.105           | shrinking      | 0.293      |
| no_ifn    | 0.181           | growing        | 0.419      |
| no_both   | 0.097           | stable         | 0.246      |

**Losses anchor.** Removing loss feedback drops strand stability by
30% and causes the loss channel itself to atrophy (shrinking evolution).

**IFN perturbs.** Removing IFN *increases* stability (0.181 vs 0.152)
and *decreases* consecutive divergence. IFN drives the projector to
restructure — it's a perturbation signal, not a stabilizer.

**Complementary mechanisms.** Losses = stability + self-awareness.
IFN = productive instability + adaptation. Together: a trajectory
that is both anchored and adaptive. Remove both: flat, incurious.

**Multi-timescale confirmed.** Losses and IFN are negligible at snapshot
scale (N=20 ablation) but load-bearing at trajectory scale (50 cycles).
The tensor format has components operating at different time constants.

## Open questions

- Does the rewrite property hold for other input types?
- Does mandating more strands improve quality (categorization pressure)?
  Strand count experiment designed, not yet run.
- What is the "right" meta/content allocation for different tasks?
- Does performance feedback (not just self-referential) change trajectory?
- Can we detect the cycle 75 "flow state" pattern in advance?
