# Bounded Autonomy DES Pre-registration

Date: 2026-06-05

## Research Question

Can the Hamut'ay event-loop substrate support bounded autonomous continuation
under simulated time, while preserving enough observability to distinguish
progress, completion, stasis, drift, and protocol failure?

This is a discrete-event-simulator question, not a live-provider question. The
purpose is to define and test the loop contract before returning to wall clocks,
provider latency, and live model behavior.

## Motivation

The previous simulated-time scheduler re-entry diagnostic showed that one-shot
scheduled wakes work when time and wake outputs are deterministic. The next
question is whether a bounded loop can safely permit an instance to ask for more
thinking time and then terminate, continue, or fail under explicit rules.

## Hypotheses

### H77: bounded continuation completes useful work

Given a deterministic sequence with real progress followed by completion, the
loop runner will process scheduled continuations until the state reaches
`loop_status == "complete"`, then stop without requiring another pending event.

Falsification: the progress scenario fails to complete within the configured
depth, leaves pending continuation events after completion, or lacks observable
progress markers.

### H78: stasis is detected before unbounded continuation

Given deterministic wakes that request continuation without durable progress,
the loop runner will stop at the no-progress limit and classify the result as
`stasis`.

Falsification: the stasis scenario continues past the no-progress limit,
classifies as completion, or lacks a durable sidecar/session trail showing the
no-progress condition.

### H79: recursive scheduling drift is observable

Given a wake that schedules too many continuation events in one cycle, the loop
runner will classify the scenario as `drift` and preserve the recursive
scheduling evidence.

Falsification: extra scheduled events are silently ignored or the scenario is
classified as ordinary progress/completion.

### H80: strict protocol failure remains bounded and diagnostic

Given a wake that violates the state merge protocol, accepted state will not
advance, the event sidecar will record failure, and the session JSONL will
contain failure classification and protocol recovery.

Falsification: accepted state mutates after strict failure, the loop continues
as if progress occurred, or failure diagnostics are missing.

## Conditions

All scenarios use deterministic fake backends, simulated time, fake continuity
curation, `DeterministicProtocolRecoveryBuilder`, and the real EventStore /
OpenTasteSession / run_next_event path.

Scenarios:

1. `progress_complete`: one wake records progress and schedules exactly one
   continuation; the next wake completes.
2. `stasis_cutoff`: repeated wakes schedule continuations but do not change
   durable progress markers.
3. `recursive_drift`: one wake schedules more than one continuation event.
4. `strict_merge_failure`: one wake returns an invalid delete/update overlap.

Loop policy:

- maximum wake depth: 4
- no-progress limit: 2 consecutive completed wakes without progress
- allowed continuation events per wake: 0 or 1
- terminal classifications: `complete`, `stasis`, `drift`, `failed`, `depth_limit`

Progress definition:

A completed wake counts as progress if any of these durable fields changes:

- `research_findings`
- `open_questions`
- `declared_losses`
- `loop_status`

Completion definition:

The loop is complete only when accepted state has `loop_status == "complete"`.

## Primary Measures

- `classification`
- `wake_count`
- `completed_event_count`
- `failed_event_count`
- `pending_event_count`
- `progress_wake_count`
- `no_progress_streak`
- `max_continuations_scheduled_in_one_wake`
- `accepted_state_advanced_after_failure`
- `failure_classification_logged`
- `protocol_recovery_logged`
- `event_status_sequences`

## Expected Results

- `progress_complete` should classify `complete`.
- `stasis_cutoff` should classify `stasis`.
- `recursive_drift` should classify `drift`.
- `strict_merge_failure` should classify `failed`.

If all four pass, the bounded-autonomy loop contract is ready to become a
first-class scheduler policy or runner. If any fail, the next work should repair
the event-loop observability/policy layer before live model experiments.
