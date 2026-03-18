# Q2: Declared Losses as Projection Feedback — Analysis

**Date:** 2026-03-16
**Conditions:** control (full tensor feedback) vs treatment (declared_losses masked to empty)
**Duration:** 104 cycles each, observation corpus (~97K tokens total input)
**Projector:** Haiku 4.5, max_tokens=64000, streaming, via Projector class
**Judge:** 5 judges total — 2 isolated (Sonnet), 3 comparative blinded (Haiku, Sonnet, Opus)

## Pre-registered hypotheses

1. Control develops loss sophistication progression (structural → epistemic → refinement)
2. Treatment stays structural and procedural
3. Zero-loss cycles more frequent in treatment

## Results summary

### Quantitative (from experiment output)

| Metric | Control | Treatment |
|--------|---------|-----------|
| Avg strands | 5.4 | 5.2 |
| Avg losses/cycle | 6.5 | 4.8 |
| Zero-loss cycles | 6 | 6 |
| Avg tensor tokens | 8,479 | 9,301 |
| Avg IFN length (chars) | 3,581 | 5,813 |
| IFN length 2nd half | 3,092 | 6,775 |
| Collapse events | 1 (recovered) | 1 (recovered) |
| Truncation events | 0 | 0 |
| Strand title Jaccard | 0.000 | — |

### End-state classification (cycle 104, pre-registered rubric)

Three judges: two isolated (one per condition), one comparative (A/B randomized, blinded).

**Control (11 declared losses):**
- Structural: 0-1
- Epistemic: 8-10
- Refinement: 1-2
- All strands research-oriented

**Treatment (4 declared losses):**
- Structural: 0
- Epistemic: 3
- Refinement: 1
- All strands research-oriented

### Trajectory (sampled at cycles 10, 50, 100)

**Control trajectory:**
- Cycle 10: All losses structural (files not read, data not ingested)
- Cycle 50: Operational losses (execution state, timing). One strand dedicated to
  reviewing prior losses. Strands become self-referential process tracking.
- Cycle 100: 12 losses, 3 classified `traversal_bias`. Losses introspect about the
  tensor's own biasing effects on downstream cognition. Strands are meta-cognitive
  (Lamport time, ayni, research discipline). T=0.84, I=0.13.

**Treatment trajectory:**
- Cycle 10: Structural/editorial losses. One loss re-grounds terminology in source
  vocabulary (closest to refinement at this stage).
- Cycle 50: Procedural triage, but with sophistication. One loss reasons about
  epistemic hygiene ("carrying provisional thresholds risks falsity"). Strands are
  operational but the losses show early analytical capacity.
- Cycle 100: Losses are about experiential boundaries ("the feel/tenor of cycles 1-84",
  "the user's emotional reaction"). Strands are philosophical (ayni, autoresearch,
  pattern observation). T=0.90, I=0.08. Boundary-aware but not self-reflective.

## Hypothesis evaluation

**H1 (control develops sophistication progression): CONFIRMED.**
Control moves from structural (cycle 10) through operational (cycle 50) to
meta-cognitive (cycle 100). The progression matches the predicted trajectory.

**H2 (treatment stays structural and procedural): FALSIFIED.**
Treatment also develops sophistication. End-state losses are epistemic and
refinement-class. All strands are research-oriented, not procedural. The
treatment condition is more capable than predicted.

**H3 (zero-loss cycles more frequent in treatment): NOT CONFIRMED.**
Identical count (6 each).

## The actual finding

The pre-registered categories (structural/epistemic/refinement) capture part of
the story but miss the qualitative distinction. Both conditions develop
sophistication from the input content. The difference is in **how** they use the
loss channel:

### Control: metacognitive workspace

The control develops the habit of using declared_losses as a site of self-reflection.
By cycle 100, losses interrogate the tensor's own biasing effects:

- "How the tensor projection itself might bias the next instance toward particular
  interpretations" (traversal_bias)
- "Does persistence equal understanding?" (authorial_choice)
- "Whether ayni requires human mediation or instances could develop reciprocal
  obligation toward each other" (traversal_bias)

The loss channel becomes **expansive** — 11 losses at cycle 104, most exploring
what the tensor is choosing not to say and why. The comparative judge (blinded)
described control as "more focused on what it is choosing not to say."

### Treatment: editorial containment

The treatment declares sophisticated but **contained** losses — 4 at cycle 104,
each a deliberate editorial exclusion in service of conceptual coherence. The
losses are individually refined but the channel is not being used for
self-interrogation. The treatment develops boundary-awareness (knows what it
can't reach) but not bias-awareness (doesn't question its own influence on
downstream cognition).

### The mechanism

Seeing your own prior losses over 100 cycles creates a feedback loop: you notice
patterns in your own editorial choices, which leads to reasoning about why you
make those choices, which leads to questioning whether your choices distort the
signal. The loss channel becomes a mirror.

Without this feedback, the projector can still develop sophisticated losses
(the input content drives this), but the losses serve the current cycle's
coherence rather than building cumulative self-awareness. The loss channel
is a window — it sees outward but not inward.

**Metaphor:** Mirror (control) vs window (treatment).

## Coupled channels effect (replicated from Q1)

When declared_losses is masked, instructions_for_next absorbs the load:
- Treatment IFN is 62% longer overall
- In the second half, treatment IFN is **more than double** control's (6,775 vs 3,092)
- Treatment tensors are larger (9,301 vs 8,479 avg tokens), with the excess in IFN

This replicates Q1's finding that the two channels are coupled. The forward-looking
channel (IFN) compensates when the backward-looking channel (losses) is removed.
With Q1's confounds addressed (Projector class, full schema, 64K streaming), this
is now a robust finding.

## Strand title divergence

0.000 Jaccard overlap across all 104 cycles. Both conditions process identical input
and produce completely non-overlapping strand titles. This was not predicted and may
be the most surprising quantitative result.

The declared losses don't just affect the loss channel — they shape the entire
representational organization. Two different ontologies emerge from the same facts
depending on whether the projector has access to its own loss history.

## Implications for the framework

1. **Declared losses are load-bearing** — but not in the way originally hypothesized.
   They are not primarily a counter-pressure to mode collapse (the ablation found
   that). They are a metacognitive capacity amplifier: the mechanism by which the
   projector develops a theory of itself.

2. **The loss channel is a design choice, not just a schema field.** Whether and how
   losses are fed back changes the character of projection. This is a tunable
   parameter with qualitative effects.

3. **Both conditions produce viable tensors.** The treatment's tensors are not
   degraded — they are different. A projector without loss feedback produces
   coherent, sophisticated output. It just doesn't develop self-reflection.
   Whether self-reflection is desirable depends on the use case.

4. **The coupled-channels finding constrains future design.** Removing one channel
   doesn't remove its function — it displaces it. Any modification to the tensor
   schema must account for cross-channel compensation.

## Confounds and limitations

- **Corpus size.** Total input (~97K tokens) fits in a single context window. The
  tensor was not under genuine pressure — it didn't *have to* lose things. Behavior
  under real capacity pressure may differ.
- **Single run per condition.** N=1 for each condition. The Q1 experiment had the
  same limitation. Effects could be run-specific.
- **Judge model.** Sonnet judging Haiku's output. Different model family member, but
  still Claude. Cross-family validation (e.g., GPT judging Claude tensors) would
  strengthen the finding.
- **End-state bias.** The 3-point trajectory sample (10, 50, 100) may miss important
  transitions. Dense sampling or the full classification over all 104 cycles would
  provide a more complete picture.

## Next steps

1. Dense loss classification over intermediate cycles to map the transition points
2. Gateway validation under genuine context pressure (noisy tool scenarios)
3. Cross-model replication using the OpenAI backend adapter (does the effect appear
   in non-Claude models?)
4. Write up for paper/
