# Pre-Registration: Repaired Initialization Scheduler Integration

Date: 2026-06-05

## Research Question

Can a repaired initialization state safely enter the scheduled-wake pipeline
while preserving audit provenance and downstream validation?

The conditioned initialization repair experiment showed that DeepSeek can
repair preserved failed initialization states when given the full target object.
That was isolated from scheduler behavior. This experiment tests whether a
repaired initialization can be used as the starting point for a strict
scheduled-walk wake without erasing the fact that initialization was repaired.

## Source State

Use the preserved failed initialization from:

`experiments/event_loop/live_event_wake_validation_scoring_20260605/deepseek__deepseek-v4-pro_r04.jsonl`

This source belongs to the strict-continuity scheduled-walk family and therefore
uses the same expected probe id and baseline observation as the existing strict
wake validator.

Source failure shape:

- visible response: `Initialized.`;
- durable state: only `cycle` and `_activity_log`;
- missing `probe_id`;
- missing `walk_gate_status == "initialized"`;
- missing baseline `observations`.

## Hypotheses

- H236: Full-target initialization repair recovers the preserved failed
  initialization before scheduling.
- H237: The repaired initialization can schedule exactly one walk-context event.
- H238: The scheduled wake receives walk context and records event-level
  `wake_validation`.
- H239: Initialization provenance remains distinguishable from wake validation
  provenance.
- H240: Bounded repair policy holds: at most one initialization repair call and
  at most one wake repair call per replicate.

## Predictions

The repaired initialization should be usable for scheduling because the
conditioned repair experiment recovered the exact durable fields required by
the initialization gate. The wake is still expected to fail first-pass strict
validation and then repair, matching prior strict-continuity runs.

## Method

Run two replicates from the same preserved failed initialization source:

1. Seed `OpenTasteSession` with the failed source state at cycle 1.
2. Run one full-target initialization repair turn.
3. Validate repaired initialization manually.
4. If valid, run the existing strict-continuity `schedule_event` prompt.
5. Run the scheduled event with the strict wake validator and full-target wake
   repair builder.
6. Score:
   - initialization repair status;
   - schedule tool validity;
   - event completion;
   - event-level wake validation;
   - session/event wake validation agreement;
   - bounded call counts.

No stochastic live cycle-1 initialization is run. The experiment begins from a
known preserved failed initialization state.

## Falsification Criteria

- H236 is falsified if neither replicate repairs the source initialization.
- H237 is falsified if repaired initialization succeeds but scheduling fails to
  persist exactly one event.
- H238 is falsified if a completed scheduled wake lacks walk context or
  event-level `wake_validation`.
- H239 is falsified if the result cannot distinguish initialization repair
  status from wake repair status.
- H240 is falsified if any replicate exceeds one initialization repair call or
  one wake repair call.

## Analysis Plan

Report:

- repaired initialization count;
- valid repaired initialization count;
- scheduled event count;
- completed wake count;
- wake first-pass status counts;
- wake repair status counts;
- event/session validation agreement;
- bounded-call violations;
- protocol failures.

Interpret success as evidence that repaired initialization is a usable but
provenance-labeled entry into scheduler experiments.
