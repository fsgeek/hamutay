# Goal 9 Pre-Registration: DES / Wall-Clock Boundary Probe

Date: 2026-06-13

## Research Question

Does adding a wall-clock scheduler adapter change the semantic behavior already
established by the deterministic discrete-event scheduler, or is wall-clock
execution only a runtime availability boundary for experiments that need real
elapsed time?

## Hypothesis

The deterministic `SchedulerClock` remains the semantic baseline for Hamut'ay
scheduler research. A `WallClock` adapter can satisfy the same scheduler clock
boundary for due ordering, expiration, next-wake reporting, and restart frontier
recovery without weakening deterministic replay.

## Falsification Conditions

The hypothesis is falsified if any of the following occur:

- deterministic `SchedulerClock` semantics change or existing scheduler tests
  fail;
- wall-clock dispatch changes due ordering relative to the DES baseline;
- wall-clock expiration fails to terminalize an expired pending event;
- wall-clock next-wake reporting fails to identify the earliest waiting event;
- wall-clock event claiming prevents restart frontier recovery of an interrupted
  running event;
- a wall-clock-only failure is incorrectly attributed as a semantic scheduler
  failure.

## Method

Implement a narrow clock boundary:

- `ClockPort` protocol for `now()` and `now_iso()`;
- existing `SchedulerClock` retained as deterministic baseline;
- new `WallClock` adapter for runtime boundary probes;
- no sleeping, polling loop, or real-time scheduler daemon.

Run paired DES and wall-clock smoke tests for:

- due ordering;
- expiration;
- next-wake reporting;
- restart frontier behavior.

The wall-clock rows construct event times relative to the current UTC time. They
do not require waiting for time to pass.

## Scoring

Each row is classified separately:

- `semantic_scheduler`: deterministic ordering, expiration, next-wake, or
  restart semantics diverge;
- `runtime_availability`: wall-clock adapter/runtime access fails while DES
  semantics remain intact;
- `passed`: DES baseline and wall-clock boundary probe both satisfy the
  preregistered checks.

The analysis must state whether any current research claim requires wall-clock
execution. A passing boundary probe is not evidence that a production scheduler,
daemon, sleep loop, container boundary, or wall-clock SLA exists.

## Expected Result

Expected result: passed.

The expected interpretation is that DES remains sufficient for the current
semantic scheduler experiments, while wall-clock support is available as a
runtime adapter for future experiments that genuinely need elapsed-time
behavior.
