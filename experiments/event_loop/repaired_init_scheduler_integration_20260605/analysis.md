# Analysis: Repaired Initialization Scheduler Integration

Date: 2026-06-05

## Result

A repaired initialization state successfully entered the scheduled-wake
pipeline in both replicates.

- H236 initialization repair recovers the source: supported.
- H237 repaired initialization schedules one walk event: supported.
- H238 wake receives context and event validation: supported.
- H239 initialization and wake provenance remain distinguishable: supported.
- H240 bounded repair policy holds: supported.

## Summary

Across two replicates:

- initialization repair valid: 2/2;
- schedule valid: 2/2;
- scheduled wakes completed: 2/2;
- wake first-pass valid: 0/2;
- wake repaired: 2/2;
- completed wakes with event-level `wake_validation`: 2/2;
- event/session validation agreement: 2/2;
- initialization repair call violations: 0;
- wake repair call violations: 0;
- errors: 0.

## Provenance Path

The run began from the preserved failed initialization in:

`experiments/event_loop/live_event_wake_validation_scoring_20260605/deepseek__deepseek-v4-pro_r04.jsonl`

That source state contained only:

- `cycle`;
- `_activity_log`.

Each replicate then produced this sequence:

1. cycle 2: model-authored initialization repair;
2. cycle 3: schedule exactly one walk-context event;
3. cycle 4: scheduled wake;
4. cycle 4 repair: full-target wake repair after first-pass wake validation
   failed.

Initialization provenance is visible in cycle 2 raw output and result fields.
Wake validation provenance is visible separately in cycle 4 `state_validation`
and in the terminal event record's `wake_validation` summary.

## Wake Behavior

Both wake first passes failed strict validation in the same way prior
scheduled-walk gates did:

- `walk_gate_status`;
- `observed_walk_endpoint_count`;
- all required `observed_walk_edge_types`;
- `observations.scheduled_walk`.

Continuity remained valid on first pass in both replicates. The failure was
task-evidence persistence, not identity drift.

Both repair turns produced strict-valid final state and event-level
`wake_validation.status == "repaired"` with
`first_pass_status == "invalid"` and `repair_status == "valid"`.

## Interpretation

This closes the immediate policy loop around initialization repair:

- failed initialization is recoverable when conditioned directly;
- the repaired state can be used to schedule and run a wake;
- downstream wake failures remain visible and are not silently hidden by the
  initialization repair;
- repaired initialization should be treated as usable but provenance-labeled.

The result supports a scheduler-experiment policy with three initialization
classes:

- first-pass valid;
- repaired and provenance-labeled;
- unrepaired and culled before scheduler scoring.

The model behavior boundary remains unchanged downstream: DeepSeek still tends
to verbalize scheduled walk evidence without first-pass durable state updates.
The repair scaffold recovers that failure, but the first-pass signal remains
important research data.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/repaired_init_scheduler_integration_20260605/run_repaired_init_scheduler_integration.py
timeout 1200s uv run python experiments/event_loop/repaired_init_scheduler_integration_20260605/run_repaired_init_scheduler_integration.py
```

Results:

- py_compile passed;
- live runner exited with code 0;
- two repaired initializations succeeded;
- two scheduled wakes completed;
- two wake repairs succeeded;
- zero bounded-call violations.
