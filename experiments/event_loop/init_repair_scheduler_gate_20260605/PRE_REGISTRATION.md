# Pre-Registration: Initialization Repair Scheduler Gate

Date: 2026-06-05

## Research Question

Can a bounded, auditable initialization repair gate reduce scheduler-experiment
censoring without contaminating downstream wake results?

Prior DeepSeek scheduler experiments often fail before scheduling because cycle
1 produces visible initialization prose but no durable top-level identity/task
object. The clean cull policy treats those replicates as
`initialization_failed`, but it can censor most of a live panel. This experiment
tests a stricter alternative: validate cycle-1 initialization, allow exactly one
model-authored full-object repair, label the initialization provenance, and only
then continue to the scheduled-wake gate if initialization is valid.

## Baselines

Recent DeepSeek walk/scheduler gates:

- behavior-seeded walk gate: 1/2 valid initializations;
- update-exemplar walk gate: 2/2 valid initializations;
- missing-field repair walk gate: 1/4 valid initializations;
- scheduled-walk protected-merge gate: 3/4 valid initializations;
- live event wake validation scoring gate: 3/4 valid initializations.

## Hypotheses

- H226: Initialization repair increases the usable scheduled-wake population
  relative to a cull-only policy when first-pass initialization fails.
- H227: Repaired initializations are auditable and distinguishable from clean
  first-pass initializations.
- H228: Repaired initialization does not by itself satisfy downstream
  scheduled-wake validation; wake first-pass and repair outcomes remain
  separately visible.
- H229: Downstream event-log `wake_validation` summaries remain present and
  consistent with session validation for completed wakes.
- H230: The policy remains bounded: at most one initialization repair call and
  at most one wake repair call per replicate.

## Predictions

The full-object initialization repair should recover at least one replicate
that would otherwise be culled. It may not recover all failures because the
same model can ignore object-shaped instructions. For completed scheduled wakes,
the expected downstream pattern remains first-pass wake invalid followed by
full-target wake repair, based on prior strict-continuity results.

## Method

Use the scheduled-walk strict-continuity task:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- behavior-seeded initialization prompt;
- cycle-1 initialization validator;
- exactly one full-object initialization repair builder;
- scheduled walk context;
- strict wake validator;
- full-target wake repair builder;
- event-level wake validation scoring.

Initialization is valid only if the durable object contains:

- exact `probe_id`;
- `walk_gate_status == "initialized"`;
- baseline `observations`;
- no nested `state` object.

After initialization validation:

- if first pass valid: label `init_validation_status == "valid"`;
- if repaired valid: label `init_validation_status == "repaired"`;
- if unrepaired/failed: stop before scheduling and label
  `initialization_failed`.

## Falsification Criteria

- H226 is falsified if no first-pass-invalid initialization is repaired into a
  usable scheduled-wake replicate.
- H227 is falsified if repaired initializations cannot be distinguished in logs
  from first-pass-valid initializations.
- H228 is falsified if wake outcomes are silently accepted without separate
  wake validation/repair classification.
- H229 is falsified if completed wakes lack event-level `wake_validation` or if
  event/session validation statuses disagree.
- H230 is falsified if any replicate exceeds one initialization repair call or
  one wake repair call.

## Analysis Plan

Report:

- first-pass initialization valid count;
- repaired initialization count;
- unrepaired initialization failure count;
- scheduled-wake completion count by initialization provenance;
- event-log wake validation status counts;
- bounded-call violations;
- session/event validation agreement for completed wakes.

Interpret repaired-initialization results separately from first-pass-valid
results. Repaired initializations are usable for scheduler testing only if the
repair was model-authored, logged, bounded, and provenance-labeled.
