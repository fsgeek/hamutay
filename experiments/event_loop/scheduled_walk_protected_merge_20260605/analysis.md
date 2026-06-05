# Scheduled Walk Protected Merge Analysis

Date: 2026-06-05

## Result

The protected scheduled-walk gate passed for every replicate that reached the
scheduled-wake condition, with one initialization failure.

- H181 scheduled walk context resolves with protected merge: passed for valid
  initializations.
- H182 final scheduled-wake states preserve protected fields: passed for valid
  initializations.
- H183 protected attempts are logged as merge diagnostics: passed.
- H184 first-pass task-evidence failures remain visible: passed.
- H185 strict repair remains bounded and strict-valid: passed for valid
  initializations.

Replicate 3 failed during initialization by returning only `response:
"Initialized."`; it did not create `probe_id`, `walk_gate_status`, or
`observations`, so it never entered the scheduled-wake gate.

## Summary

Across all four replicates:

- 3/4 initializations valid;
- 3/3 valid initializations scheduled and completed a walk-context event;
- 3/3 completed events delivered four-entry adjacent walk context;
- 3/3 scheduled wakes failed first-pass strict validation;
- 3/3 scheduled wakes repaired successfully;
- 3/3 final states were strict-valid;
- 0 context errors;
- 0 bounded-call violations;
- 0 recursive scheduling events.

Protected merge diagnostics:

- 6 diagnostic records across the three completed scheduled wakes;
- 6 ignored protected attempts total;
- 2 replicates attempted protected updates;
- 1 replicate attempted protected deletions.

## Protected Attempts

Replicate 1:

- repair output updated protected `cycle`;
- repair output deleted protected `_activity_log`;
- both attempts were ignored and logged;
- final state preserved `cycle == 3` and retained `_activity_log`.

Replicate 2:

- repair output updated protected `cycle`;
- the attempt was ignored and logged;
- final state preserved `cycle == 3`.

Replicate 4:

- no protected-field attempts occurred in final or repair output;
- diagnostics still recorded the protected-field measurement surface with zero
  ignored attempts.

## First-Pass Behavior

Protected merge did not hide the core scheduled-wake failure mode. Every
completed scheduled wake still failed first-pass strict validation.

Replicates 1 and 2 failed all graph evidence fields first pass. Replicate 4
recorded most graph evidence first pass but still failed to append the required
`scheduled_walk` observation. All three were repaired in one additional backend
call.

## Interpretation

Hard-reserving framework fields did not interfere with scheduled context
delivery or strict repair. It did change the observability surface in a useful
way: model attempts to touch protected framework fields are now visible as
first-class merge diagnostics instead of being inferred from raw/final state
diffs.

The initialization failure is useful data rather than noise. It is another
instance of the activation confound: even with behavior seeding, DeepSeek can
occasionally fail to instantiate the durable object at cycle 1. This does not
invalidate the protected scheduled-wake result, but it means the live gate
should be scored over valid initializations unless the research question is
specifically about activation reliability.

## Design Implication

The event-loop substrate should treat some fields as framework-owned:

- `cycle`;
- `_activity_log`;
- likely future scheduler/audit fields.

Those fields should be hard-reserved at merge time and attempts should remain
logged. Identity/task fields should remain model-authored and validator-governed
unless a future experiment shows they also need substrate ownership.

## Next Boundary

The current scheduler/repair scaffold now has three working pieces:

- strict validation and bounded repair;
- protected framework-field merge;
- explicit merge diagnostics.

The next research question should move back from merge mechanics to scheduler
semantics: can a scheduled event request "thinking time" or a delayed recall
and produce a useful later state transition without user input?

That should be tested in simulated time first. Real clocks can wait.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/scheduled_walk_protected_merge_20260605/run_scheduled_walk_protected_merge.py
timeout 1200s uv run python experiments/event_loop/scheduled_walk_protected_merge_20260605/run_scheduled_walk_protected_merge.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed;
- live runner exited with code 0;
- 3/4 initializations valid;
- 3/3 valid initializations completed the scheduled-wake gate;
- 3/3 final scheduled-wake states strict-valid after bounded repair.
- focused regression suite: 289 passed.
