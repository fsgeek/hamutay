# Pre-Registration: Auto-Continuation Scheduler Smoke

Date: 2026-06-05

## Research Question

Can generated continuation binding become an opt-in scheduler phase without
changing default event lifecycle behavior?

The prior primitive smoke added `build_bound_continuation_event`, but the
scheduler still required experiment runners to inspect durable state and append
the continuation event manually. This smoke tests a minimal opt-in integration:
after a wake completes, `run_next_event(..., auto_continuations=True)` should
append one bound continuation event when the committed durable state contains a
valid `continuation_request`.

## Hypotheses

- H411: Default scheduler behavior remains unchanged.
- H412: With `auto_continuations=True`, a completed wake with a requested
  continuation appends one bound pending event.
- H413: The appended event is bound to the actual completed wake
  `result_record_id`.
- H414: The appended event preserves normal event validation and placeholder
  expansion.
- H415: Malformed continuation requests fail explicitly and mark the source
  event failed rather than silently appending a corrupt event.

## Predictions

- Existing event/taste tests pass with defaults.
- A focused unit test with `auto_continuations=False` completes the source event
  and appends no continuation.
- A focused unit test with `auto_continuations=True` completes the source event
  and appends exactly one pending continuation event.
- The pending continuation contains:
  - `bound_by: continuation_request`;
  - `bound_source_event_id`;
  - `bound_result_record_id`;
  - `scheduled_by_record_id` equal to the completed wake result record ID.
- Placeholder expansion works inside requested context and terminal-surface
  state updates.
- A malformed requested continuation causes the step to raise and records a
  failed event status with the continuation error.

## Falsification Criteria

The integration is not supported if:

- default `run_next_event` behavior changes;
- auto-continuation appends more than one event for one completed wake;
- malformed continuation requests are swallowed;
- append happens from unrequested or non-object continuation state;
- existing event/taste or unit tests regress.

## Method

Add an optional `auto_continuations` parameter to:

- `run_next_event`;
- `run_pending_events`;
- `step_pending_events`.

Default must be `False`.

When enabled, the scheduler should:

1. run and complete the current event normally;
2. inspect the committed durable state for top-level `continuation_request`;
3. call `build_bound_continuation_event`;
4. append the returned event if non-null;
5. include the appended continuation event in the result record returned by
   `run_next_event`.

No live model calls are required for this smoke.

## Analysis Plan

Report unit-test evidence and the exact scope of behavior changed. Treat this
as an engineering smoke, not a live-model reliability result.
