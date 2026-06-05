# Pre-Registration: Live Event Wake Validation Scoring

Date: 2026-06-05

## Research Question

Can completed scheduled-event records now serve as the primary scoring surface
for live wake validation/repair outcomes?

The event substrate now copies a compact `wake_validation` summary onto
completed event records. Prior scheduled-wake analyses had to join session logs
and event logs manually. This experiment reruns the live scheduled-walk strict
continuity gate and scores first-pass/repaired outcomes from the event log.

## Hypotheses

- H221: The scheduled-walk strict-continuity gate still completes under the new
  event observability path.
- H222: Every completed event with an active wake validator has
  `wake_validation` in the completed event record.
- H223: Event-log wake validation status matches session-log
  `state_validation.status`.
- H224: Event-log summaries classify first-pass invalid and repaired wakes
  without reading session `state_validation` directly.
- H225: Event-level scoring preserves context-delivery and bounded-repair
  diagnostics from the prior strict-continuity gate.

## Predictions

The event summaries should classify all completed wakes as repaired because the
prior strict-continuity run found 4/4 first-pass invalid and 4/4 repaired under
the same gate. Exact first-pass/repaired counts may vary with stochastic model
behavior, but every completed wake should expose the validation classification
directly from the event log.

Expected result: H221-H225 pass for completed events. Initialization failures,
if any, are scored separately and do not falsify the event-log observability
claim unless they prevent all scheduled wakes from completing.

## Method

Use the existing scheduled-walk strict-continuity runner as the task substrate:

- model: `deepseek/deepseek-v4-pro`;
- replicates: 4;
- scheduled walk context;
- strict continuity validator;
- full-target repair builder;
- bounded wake calls: at most one first pass plus one repair.

Write a wrapper runner that stores output under this experiment directory and
adds event-log scoring fields by reading only `summarize_event_log` event
summaries:

- completed event `wake_validation_status`;
- completed event `wake_first_pass_status`;
- completed event `wake_repair_attempted`;
- completed event `wake_repair_status`;
- completed event `wake_repaired`;
- event-log/session-log validation agreement.

## Falsification Criteria

- H221 is falsified if no scheduled wake completes.
- H222 is falsified if any completed validated wake lacks event-level
  `wake_validation`.
- H223 is falsified if event-log status and session-log status disagree for any
  completed wake.
- H224 is falsified if completed event summaries cannot classify first-pass
  status and repair status without direct session-log inspection.
- H225 is falsified if context delivery, bounded repair calls, or event summary
  diagnostics regress relative to the strict-continuity runner.

## Analysis Plan

Report:

- initialization count;
- completed scheduled wakes;
- event-log first-pass status counts;
- event-log validation status counts;
- event-log repair status counts;
- session/event agreement count;
- context path count;
- bounded wake call violations.

This experiment is not intended to prove new DeepSeek behavior. It tests
whether the substrate now produces the data surface needed for future scheduler
experiments.
