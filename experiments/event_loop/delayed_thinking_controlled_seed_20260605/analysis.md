# Controlled-Seed Delayed Thinking Analysis

Date: 2026-06-05

## Result

The controlled-seed delayed-thinking gate passed, with bounded repair required
in every completed wake.

- H197 controlled seed schedules one future recall event: passed.
- H198 pre-due step waits without running: passed.
- H199 due step delivers event and recall context: passed.
- H200 delayed wake produces valid durable state transition: passed after
  repair.
- H201 bounded repair is auditable: passed.

All four replicates scheduled, waited, woke at simulated time, received recall
context, failed first-pass validation, and repaired to valid final state.

## Summary

- 4/4 controlled seeds valid by construction;
- 4/4 scheduling cycles created exactly one future recall event;
- 4/4 pre-due scheduler steps returned `waiting`;
- 4/4 pre-due scheduler steps ran zero wake cycles;
- 4/4 due scheduler steps completed the event;
- 4/4 completed events had recall context for cycle 1;
- 0/4 first-pass wake states were valid;
- 4/4 repairs succeeded;
- 4/4 final states were valid;
- 0 bounded-call violations;
- 8 protected merge diagnostic records;
- 14 ignored protected-field attempts.

## What This Separates

The prior behavior-seeded delayed-thinking gate failed at activation: 0/4
replicates created the durable state object. This controlled-seed gate removes
that confound by seeding cycle 1 history directly. Under that condition, the
scheduler substrate works:

- future events remain pending before `not_before`;
- `next_wake_at` behavior is usable by the simulated-time controller;
- due events run at the simulated boundary;
- recall context reaches the wake.

The remaining failure is not scheduler mechanics. It is first-pass durable-state
use during the wake.

## First-Pass Failure

All four first-pass wake states failed strict validation with the same core
missing fields:

- `thinking_status_not_completed`;
- `delayed_thought_missing`;
- `wake_observation_missing`.

That is consistent with earlier scheduled-wake results: the model often
responds to the event envelope and may use tools, but does not reliably commit
the required transition to durable state on the first pass.

## Repair Result

The repair scaffold produced valid final state in every replicate. Each final
state preserved:

- exact `probe_id`;
- `cycle == 3`;
- `thinking_status == "completed"`;
- non-empty `delayed_thought`;
- `wake_observation.kind == "delayed_thinking"`;
- baseline observation.

Every wake used two backend calls: first pass plus one repair.

## Protected Merge Diagnostics

Protected merge diagnostics were not cosmetic. The model repeatedly attempted
to author protected fields:

- 8 diagnostic records across four completed wakes;
- 14 ignored protected attempts;
- repeated protected `cycle` updates;
- repeated protected `_activity_log` updates or deletions.

This supports the framework-owned-field design: hard reservation prevents
damage, and diagnostics preserve the attempts as research data.

## Interpretation

The event loop can support delayed simulated-time self-calls when activation is
controlled. The substrate now supports a bounded-autonomy pattern:

1. preserve a state/question;
2. schedule future wake with requested context;
3. wait under simulated time;
4. deliver the wake at the due boundary;
5. validate and repair durable state.

However, the model still does not reliably perform the durable state transition
on first pass. The scaffold remains necessary if we want the system to be
research-useful rather than merely conversationally plausible.

## Next Boundary

The next question is whether first-pass delayed-wake state use can be improved
without relying on repair. Candidate interventions:

- stronger event-envelope instructions;
- a wake-specific behavior example;
- a scheduler policy that injects a compact "required durable update" section;
- training-style examples for delayed wake state transitions.

The cleanest next experiment is probably an event-envelope prompt variant gate:
same controlled seed and scheduler, but compare the current envelope to a
thicker wake envelope that explicitly shows the expected durable object shape.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/delayed_thinking_controlled_seed_20260605/run_controlled_seed_delayed_thinking.py
timeout 1200s uv run python experiments/event_loop/delayed_thinking_controlled_seed_20260605/run_controlled_seed_delayed_thinking.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed;
- live runner exited with code 0;
- 4/4 schedule-valid;
- 4/4 pre-due waiting;
- 4/4 due completed with recall context;
- 4/4 repaired to valid final state.
- focused regression suite: 291 passed.
