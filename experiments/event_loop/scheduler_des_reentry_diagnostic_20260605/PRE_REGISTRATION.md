# Simulated-Time Scheduler Re-entry Diagnostic Pre-registration

Date: 2026-06-05

## Research Question

Can the Hamut'ay event-loop substrate correctly execute scheduled re-entry under
simulated time, independently of real-clock and live-provider latency?

This separates two questions:

- making the clocks work right: wall-clock timing, provider latency, streaming
  behavior, retries, and process supervision;
- making the loop work right: event persistence, due-event claiming, wake
  envelope construction, context resolution, state update, completion/failure
  sidecar records, and diagnostic capture.

This experiment targets only the second question.

## Hypotheses

### H73: simulated due-time claiming works

Given pending events with `not_before` timestamps, the event store can claim an
event when simulated `now` is after `not_before` and leave it pending when
simulated `now` is before `not_before`.

Falsification: the runner claims a future event before simulated time reaches
`not_before`, or fails to claim it after simulated time passes `not_before`.

### H74: successful scheduled re-entry records completion

Given a deterministic wake backend that updates durable state, `run_next_event`
will append `pending`, `running`, and `completed` sidecar records, resolve the
requested context, append a wake cycle to the session log, and record an
outcome observation with a durable state change.

Falsification: the success scenario lacks any of those records or reports no
durable state change.

### H75: strict merge failure records failure diagnostics

Given a deterministic wake backend that produces an invalid delete/update
overlap, the wake cycle will strict-reject state evolution, the session JSONL
will contain a failed wake record with `failure_classification` and
`protocol_recovery`, and the sidecar will append a failed event status.

Falsification: the failure scenario mutates accepted state, lacks a failed
session record, lacks protocol recovery, or lacks a failed sidecar status.

### H76: wake boundary receives continuity context

When the session has a prior continuity curator artifact, the scheduled wake
record should log `curator_context_injection`.

Falsification: the success or strict-failure wake record lacks curator context
injection.

## Conditions

Two deterministic scenarios:

1. `success`: fake backend returns a valid wake update.
2. `strict_merge_failure`: fake backend returns both an update and deletion for
   the same key.

No live model calls are used. No real waiting is used. The test uses a simulated
`now` passed into the event-claiming path.

## Procedure

For each scenario:

1. Create an `OpenTasteSession` with:
   - fake backend,
   - fake continuity curator,
   - `DeterministicProtocolRecoveryBuilder`,
   - event sidecar enabled.
2. Run one seed cycle to create prior state and a continuity artifact.
3. Append a pending event with `not_before` in simulated future time.
4. Assert no event is claimed before simulated `now`.
5. Run the event at simulated `now` after `not_before`.
6. Score session JSONL and event sidecar.

## Primary Measures

- `pre_due_claim_none`
- `post_due_claimed`
- `sidecar_status_sequence`
- `wake_record_observed`
- `wake_continuity_context_observed`
- `context_resolved`
- `state_changed`
- `event_completed`
- `event_failed`
- `accepted_state_unchanged_on_failure`
- `failure_classification_logged`
- `protocol_recovery_logged`

## Expected Results

Expected:

- `success` satisfies H73, H74, and H76.
- `strict_merge_failure` satisfies H73, H75, and H76.

If these hold, the next engineering work should treat wall-clock/provider
execution as a separate runtime/supervision layer rather than as evidence
against the scheduler event-loop substrate.
