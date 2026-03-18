# Q2: Declared Losses as Differentiation Mechanism

## Pre-registration

Filed: 2026-03-16, before rerun.

## Hypothesis

Declared losses in the prior tensor function as a differentiation mechanism:
a projector that sees its own prior losses develops increasingly sophisticated
loss taxonomy over iterative cycles, while a projector denied this feedback
produces structurally uniform output.

This refines Q1's hypothesis ("counter-pressure to mode collapse") based on
qualitative analysis of Q1 data. The effect is not primarily about collapse
prevention — it is about the *kind* of cognition the projector performs.

## Qualitative finding from Q1 (motivating this pre-registration)

Reading the actual tensor content (not just metrics) revealed:

- **Control** (sees prior losses): developed a "refinement" loss category by
  cycle 100 — recognizing that some losses represent intellectual maturation,
  not degradation. Strand character was research-oriented and reflective.

- **Treatment** (never sees prior losses): at cycle 50, declared zero losses
  with a strand asserting "ZERO LOSS CLAIM." By cycle 100, declared only
  structural/mechanical losses. Strand character was procedural — a project
  management dashboard rather than a researcher's notebook.

The quantitative Q1 finding (3.2 vs 4.1 avg losses) missed this entirely.
The *number* of losses matters less than their *character*.

## Design

Same as Q1 with three fixes:

1. **Use Projector class** (not raw API calls) — preserves collapse detection,
   checkpoint/recovery, precursor detection, escalation hooks, and the full
   PROJECTION_SCHEMA with field descriptions.

2. **Subclass Projector** for the treatment condition — override only the
   tensor fed to `_build_projection_prompt` to mask `declared_losses`.
   Everything else identical.

3. **max_tokens = 64000** with streaming — eliminates the truncation artifact
   that silently dropped `instructions_for_next` and `declared_losses` in
   later cycles of Q1.

### Conditions

- **Control**: `Projector` with default behavior (full prior tensor)
- **Treatment**: `MaskedLossProjector(Projector)` — prior tensor's
  `declared_losses` replaced with empty tuple before projection prompt
  is built. Projector still *produces* losses; it just never *sees* its
  own prior ones.

### Corpus

Same 104-cycle observation corpus as Q1
(`experiments/observation_full/observations.jsonl`).

## Measurements

### Quantitative (carried from Q1)

Per cycle, per condition:
- Strand count, strand title stability (Jaccard)
- Declared loss count
- Tensor token size
- instructions_for_next length
- Stop reason (must be end_turn, not max_tokens)
- Collapse events and recovery outcomes
- Precursor events

### Qualitative (new — the pre-registered part)

#### Loss Sophistication Classification

Each declared loss is classified into one of three categories:

1. **Structural**: Loss of data artifacts — dialogue flow, file contents,
   timestamps, intermediate states. The loss describes *what data* was
   dropped. These losses are about the container, not the content.

   Signal words: "raw dialogue", "intermediate", "file states", "timestamps",
   "tool output", "code artifacts", "format details"

2. **Epistemic**: Loss of understanding or analytical capacity — reasoning
   chains, counter-arguments, alternative interpretations, uncertainty
   about specific claims. The loss describes *what understanding* was
   compressed or degraded.

   Signal words: "reasoning about", "understanding of", "uncertainty",
   "alternative interpretation", "counter-argument", "analytical depth",
   "implications of"

3. **Refinement**: Meta-loss — the recognition that a prior framing,
   question, or exploratory tone has been superseded by deeper
   understanding. The loss is acknowledged as maturation rather than
   degradation. This is the projector developing editorial judgment.

   Signal words: "maturation", "no longer needed", "superseded",
   "exploratory tone", "reframed", "integrated into", "the wondering
   about X has been resolved into Y"

#### Classification protocol

- Each declared loss is classified by reading its `what_was_lost` and `why`
  fields together.
- Classification is performed after the experiment completes, on all
  tensors from both conditions.
- Ambiguous cases are classified as the lower category (structural before
  epistemic, epistemic before refinement).
- Inter-rater reliability: the classification should be performed by a
  second instance without seeing the condition labels.

#### What we predict

1. **Control** will show a progression: early cycles dominated by structural
   losses, middle cycles mixing structural and epistemic, late cycles
   including refinement losses. The distribution shifts rightward over time.

2. **Treatment** will show no such progression: structural losses throughout,
   with occasional epistemic losses that do not increase in frequency.
   Refinement losses will be absent or near-absent.

3. The onset cycle of the first refinement loss in the control condition
   is a measurable quantity. We predict it appears before cycle 75.

4. Treatment will have more cycles with zero declared losses than control
   (replicating Q1's finding, but now with recovery preventing collapses
   from confounding the count).

#### Strand character classification

Strand titles and content will be classified as:

- **Research-oriented**: reflective, analytical, questioning, developing
  frameworks for understanding
- **Procedural**: status tracking, execution plans, blocker management,
  dependency resolution

We predict control develops predominantly research-oriented strands;
treatment develops predominantly procedural strands.

## What would falsify the hypothesis

- If treatment develops refinement losses at the same rate as control
- If treatment strand character is indistinguishable from control
- If the loss sophistication progression in control is absent or reversed
- If both conditions produce identical loss classification distributions

## What would strengthen the hypothesis

- If the control's first refinement loss appears before cycle 50
- If treatment loss count drops to zero for multiple consecutive cycles
  (the "zero loss claim" pattern from Q1)
- If strand character divergence is visible by cycle 25

## Confounds addressed

- Q1 confound 1 (raw API calls): fixed by using Projector class
- Q1 confound 2 (stripped schema): fixed by using PROJECTION_SCHEMA
- Q1 confound 3 (max_tokens): fixed at 64000 with streaming
- New: collapse recovery means missing cycles won't create gaps in the
  trajectory analysis

## Cost estimate

104 cycles x 2 conditions x ~$0.04/cycle (Haiku) = ~$8-10
