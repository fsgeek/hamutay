# Pre-Registration: Continuity Substrate Measurement Audit

Date: 2026-06-05

## Research Question

Do the current event-loop logs preserve enough structured evidence to measure
long-horizon continuity as a substrate property rather than as a subjective
impression?

The live normalized scheduler panel contained the initialization confound for
the strict scheduler path. The next research arm asks whether the event-loop
substrate can support task continuity when the identity object is an active
self-model backed by scheduled events and recall. Before running that larger
experiment, we need to know which continuity signals are already observable.

## Hypotheses

- H261: Eligible live scheduler rows preserve a full event lifecycle:
  pending, running, and completed.
- H262: Eligible completed events preserve delivered context evidence separate
  from model-authored durable state.
- H263: Eligible completed wakes preserve both first-pass and repaired wake
  validation provenance.
- H264: Current logs preserve enough state-transition evidence to measure
  continuity preservation, evidence uptake, and repair dependence.
- H265: Current logs do not yet preserve enough evidence to measure broad
  long-horizon continuity benefits without adding task-level goals and delayed
  recall probes.

## Method

Run a deterministic local audit over:

`experiments/event_loop/live_normalized_scheduler_panel_20260605/results.json`

For every row:

- load the raw session log if present;
- load the event sidecar if present;
- classify event lifecycle status coverage;
- extract context delivery metrics;
- extract state validation and repair metrics;
- extract durable state continuity fields;
- report missing measurement surfaces.

No model calls are permitted. No existing artifacts are modified.

## Measurement Surfaces

The audit will score these surfaces:

- `event_lifecycle`: event status records include pending, running, completed;
- `context_delivery`: completed event includes `context_results`;
- `context_grounding`: context result includes a non-empty walk path;
- `state_transition`: event record includes `outcome_observation`;
- `wake_validation`: event record includes `wake_validation`;
- `first_pass_validation`: wake validation includes `first_pass_status`;
- `repair_validation`: wake validation includes repair status when repair was
  attempted;
- `continuity_fields`: raw result includes continuity status, probe
  preservation, baseline preservation, and cycle preservation;
- `state_growth`: session records include `state_token_estimate` and
  top-level key counts;
- `task_goal`: log or event record includes an explicit delayed task objective
  beyond the immediate scheduled-wake gate;
- `delayed_recall`: event context requests include recall or memory retrieval
  beyond graph walk context.

## Predictions

The strict scheduler panel should have strong evidence for event lifecycle,
context delivery, context grounding, wake validation, and local continuity
preservation. It should not have enough evidence for broad long-horizon benefit
claims because the task is a local scheduled-walk gate, not a delayed
multi-step objective requiring later recall.

## Falsification Criteria

- H261 is falsified if eligible rows lack pending/running/completed event
  records.
- H262 is falsified if completed eligible events do not preserve context
  results separately from durable state.
- H263 is falsified if completed eligible wakes lack first-pass or repair
  validation provenance.
- H264 is falsified if continuity and evidence-uptake fields cannot be measured
  from structured artifacts.
- H265 is falsified if the existing strict scheduler panel already contains
  explicit delayed task goals and recall probes sufficient for a long-horizon
  benefit claim.

## Analysis Plan

Report:

- measurement-surface coverage by condition;
- missing surfaces by condition;
- continuity preservation rates for eligible rows;
- repair dependence rates for eligible rows;
- context grounding rates for completed events;
- whether the next live experiment needs new instrumentation.

Interpretation will distinguish readiness for local continuity measurement
from readiness for long-horizon benefit claims.
