# Pre-Registration: Auto-Continuation Budget Policy

Date: 2026-06-05

## Research Question

Can the scheduler distinguish continuation-driven run length from generic wake
count and stop with an explicit continuation-budget reason?

The generated-chain repair proved that auto-continuation can quiesce when a
later wake does not emit a fresh request. The remaining policy boundary is
longer or pathological chains where each wake emits a fresh continuation. The
existing `limit` prevents unbounded execution, but it does not say whether the
run stopped because of general work volume or continuation growth.

## Hypotheses

- H451: Default scheduler behavior remains unchanged.
- H452: An optional continuation budget can stop a scheduler batch after a
  bounded number of auto-continuation appends.
- H453: The stop reason distinguishes continuation-budget exhaustion from the
  generic wake limit.
- H454: The continuation event that triggered the budget remains pending for a
  later scheduler step.
- H455: Existing event/taste and unit tests remain green.

## Predictions

- `run_pending_events` and `step_pending_events` accept an optional
  `max_auto_continuations` parameter defaulting to `None`.
- With no budget, existing tests pass and behavior is unchanged.
- With `max_auto_continuations=1`, a fixture where each wake emits a fresh
  continuation runs one source event, appends one continuation, and stops
  before executing that continuation.
- `step_pending_events` reports stop reason
  `auto_continuation_limit_reached`.
- The appended continuation remains pending and runnable/waiting according to
  normal event timing.

## Falsification Criteria

The policy is not supported if:

- default scheduler behavior changes;
- the budget suppresses or corrupts the appended event;
- the scheduler runs past the continuation budget;
- the stop reason remains only `limit_reached`;
- existing unit tests regress.

## Method

Add a pure scheduler budget parameter. Do not change model prompts, terminal
surfaces, or continuation request shape.

No live model calls are required for this smoke.

## Analysis Plan

Report unit-test evidence and whether the event log preserves the pending
continuation after the budget stop. Treat this as a scheduler-policy smoke, not
model reliability evidence.
