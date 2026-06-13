# Goal 9 Analysis: DES / Wall-Clock Boundary Probe

Date: 2026-06-13

## Result

Classification: `passed`

The wall-clock adapter satisfied the same smoke probes as the deterministic
`SchedulerClock` baseline:

| Probe | DES | Wall Clock |
| --- | --- | --- |
| Due ordering | passed | passed |
| Expiration | passed | passed |
| Next-wake reporting | passed | passed |
| Restart frontier recovery | passed | passed |

No semantic scheduler failures were observed. No runtime availability failures
were observed.

## What Changed

The scheduler now has an explicit clock boundary:

- `ClockPort`: protocol for `now()` and `now_iso()`;
- `SchedulerClock`: deterministic logical clock retained as the replay and
  semantic baseline;
- `WallClock`: UTC wall-clock adapter for bounded runtime probes;
- `EventQueue.next_wake_at(now=...)`: reports the earliest waiting pending
  event without sleeping or advancing time.

The dispatcher now depends on the clock protocol rather than the concrete
`SchedulerClock` class. Existing deterministic tests remain the semantic
contract.

## Interpretation

This result supports H9 in the narrow form preregistered for Goal 9:
wall-clock access is not required to test the scheduler semantics currently
under study. Due ordering, expiration, next-wake reporting, and restart frontier
recovery can be tested under DES and can be smoke-tested through a wall-clock
adapter without changing their meaning.

The result does not show that Hamut'ay has a production wall-clock scheduler.
There is still no daemon, sleep loop, container/VM isolation boundary,
wall-clock SLA, or persistent process supervisor. Those are runtime-system
questions, not semantic scheduler questions.

## Failure Attribution

The experiment preserves the distinction required by Goal 9:

- A DES failure would be charged to `semantic_scheduler`, because DES remains
  the replayable semantic baseline.
- A wall-clock-only failure with DES passing would be charged to
  `runtime_availability`, because it would indicate adapter/runtime trouble
  rather than a scheduler semantics failure.
- No failures occurred in this run.

## Current Research Consequence

No current research claim requires wall-clock execution. Goal 10 can proceed
with DES unless it introduces a task whose outcome depends on real elapsed time,
external deadlines, sleeping/waking across process time, or wall-clock
availability failure modes.

The practical consequence is that the project now has a real wall-clock adapter
available for boundary probes, while preserving deterministic DES as the
default experimental substrate.
