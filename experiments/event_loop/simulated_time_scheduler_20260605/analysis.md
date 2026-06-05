# Simulated-Time Scheduler Step Analysis

Date: 2026-06-05

## Result

The simulated-time scheduler step gate passed.

- H186 scheduler step runs due events and leaves future events pending: passed.
- H187 waiting step reports `next_wake_at`: passed.
- H188 empty queue reports idle without `next_wake_at`: passed.
- H189 expired pending events are terminalized before waiting is reported:
  passed.
- H190 fixed-now batch does not advance simulated time: passed.

No provider calls were needed.

## What Changed

Added `step_pending_events` to `src/hamutay/events.py`.

The helper wraps the existing `run_pending_events` flow, but exposes a
DES-compatible control surface:

- `stop_reason`;
- `now`;
- `wake_run_count`;
- `expired_count`;
- `terminalized_count`;
- `next_wake_at`;
- pending runnable/waiting/expired counts;
- the underlying batch result and event-log summary.

It does not advance time. Callers provide `now`; if future events are waiting,
the helper reports the earliest waiting `not_before` as `next_wake_at`.

## Evidence

The main deterministic test created:

- one expired event;
- one immediately runnable event;
- one future `not_before` event.

At simulated time `2026-06-01T00:00:00+00:00`, the step:

- expired the expired event;
- ran the runnable event;
- left the future event pending;
- returned `stop_reason == "waiting"`;
- returned `next_wake_at == "2026-06-01T01:00:00+00:00"`.

At simulated time `2026-06-01T01:00:00+00:00`, the next step:

- ran the waiting event;
- returned `stop_reason == "idle"`;
- returned `next_wake_at == null`.

A second deterministic test confirmed that a fixed-now batch with a future
event does not advance simulated time implicitly.

Verification:

```bash
uv run python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py -q
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed;
- event suite: 49 passed;
- focused regression suite: 291 passed.

## Interpretation

This moves the scheduler from "can run one pending event" toward a discrete
event simulation control loop. The substrate can now say:

- I ran what was eligible at simulated time `T`;
- I expired what had passed its deadline;
- I stopped because the remaining work is waiting;
- the next simulated boundary is `next_wake_at`.

That separates clock mechanics from event-loop mechanics. A controller can now
decide whether to advance simulated time, stop, or inject more work.

## Next Boundary

The next useful research question is whether an instance can schedule a
delayed self-call for "thinking time" and then use the delayed wake to make a
durable state transition without user input.

That should be a live-model experiment over simulated time, using
`step_pending_events` rather than real clocks. The validator should distinguish:

- scheduling success;
- delayed wake delivery;
- durable state transition;
- activation failure;
- protected-field attempts.
