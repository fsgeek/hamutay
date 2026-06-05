# Pre-Registration: Simulated-Time Scheduler Step

Date: 2026-06-05

## Research Question

Can the event-loop substrate expose deterministic simulated-time scheduling
semantics without relying on real clocks or live model calls?

Prior event-loop work showed that scheduled wakes can run, that `not_before`
can be respected with an injected `now`, and that strict repair can stabilize
scheduled wake state. The next scheduler question is smaller and more
foundational: can the runner explain why it stopped and identify the next
simulated time boundary?

## Hypotheses

- H186: A scheduler step at simulated time `T` runs runnable pending events and
  leaves future `not_before` events pending.
- H187: When no event is runnable but waiting events exist, the scheduler
  reports `waiting` with the earliest waiting `not_before` as `next_wake_at`.
- H188: When no pending events exist, the scheduler reports `idle` with no
  `next_wake_at`.
- H189: Expired pending events are terminalized before waiting events are
  reported.
- H190: Batch execution under a fixed simulated `now` does not silently advance
  time.

## Predictions

The expected result is deterministic:

- a mix of overdue, due, and future events will run/expire only those eligible
  at the provided simulated `now`;
- future events will remain pending;
- the step result will expose the earliest future `not_before`;
- a second step at that future time will run the waiting event;
- if the queue is empty afterward, the step reports idle.

## Method

Add a minimal scheduler-step helper around the existing `EventStore`,
`run_next_event`, and `summarize_event_log` primitives. The helper should not
use wall-clock time except when callers omit `now`.

Use fake-backend tests only. No provider calls are needed.

The helper should preserve current `run_next_event` behavior and add a richer
batch result with:

- stop reason;
- pending runnable/waiting/expired counts;
- `next_wake_at` for the earliest waiting pending event;
- number of events run;
- number of expired events terminalized.

## Falsification Criteria

- H186 is falsified if future events run before `not_before`.
- H187 is falsified if waiting events exist but no `next_wake_at` is reported.
- H188 is falsified if an empty queue reports a waiting/runnable state.
- H189 is falsified if expired pending events remain pending when stepping.
- H190 is falsified if one fixed-now batch runs events whose `not_before` is
  later than that fixed `now`.

## Analysis Plan

Analyze deterministic test results and captured event-log summaries. The
important result is not model behavior; it is whether the substrate now has a
clear DES-compatible control surface:

- run what is due at simulated time `T`;
- stop with an explicit reason;
- tell the caller when the next event becomes due.
