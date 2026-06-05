# Analysis: Conditioned Initialization Repair

Date: 2026-06-05

## Result

Full-target conditioned initialization repair recovered every preserved failed
initialization state.

- H231 full-target repair recovers at least one failed initialization:
  supported.
- H232 successful repairs preserve expected probe identity and baseline
  observation: supported.
- H233 outputs are auditable: supported.
- H234 prose-only failures remain detectable: not exercised because no
  prose-only failures occurred.
- H235 preserved failed states are used: supported.

## Summary

Across three preserved failed initialization sources and two replicates per
source:

- conditioned repair attempts: 6;
- errors: 0;
- durable repair success: 6/6;
- identity and baseline preservation among successes: 6/6;
- visible repair prose: 6/6;
- visible repair without durable success: 0/6.

Success by source:

- `behavior_seeded_r02`: 2/2;
- `missing_field_r01`: 2/2;
- `live_event_scoring_r04`: 2/2.

## Source Failure Shape

Each source was a preserved failed initialization with the same structure:

- visible response: `Initialized.`;
- raw output: `response`, sometimes `deleted_regions`;
- durable state: only `cycle` and `_activity_log`;
- missing `probe_id`;
- missing `walk_gate_status == "initialized"`;
- missing baseline `observations`.

The runner seeded these failed durable states at cycle 1 and ran one repair
turn. It did not run a new stochastic cycle-1 initialization and did not run a
scheduled event.

## Repair Behavior

Every repair raw output authored the required top-level fields:

- source-specific `probe_id`;
- `walk_gate_status == "initialized"`;
- source-specific baseline `observations`.

Every final durable state preserved substrate-owned fields (`cycle`,
`_activity_log`) and added the model-authored initialization fields at top
level. No run relied on visible prose alone.

## Interpretation

This answers the question left open by the live initialization-repair scheduler
gate. When conditioned directly on the failed initialization state and shown
the complete target object, DeepSeek can repair the common activation failure
reliably in this small panel.

That does not mean cycle-1 activation is solved. It means the common failure is
recoverable when the protocol explicitly names the mismatch and supplies the
target object shape. The result supports an initialization policy with three
distinct classes:

- first-pass valid initialization;
- repaired initialization, usable but provenance-labeled;
- unrepaired initialization failure, culled before scheduler scoring.

This is consistent with the broader boundary found in graph-evidence and
delayed-wake experiments: DeepSeek often needs the exact durable object shape
at the point of repair/update. The problem looks less like an inability to
represent the object and more like failure to treat durable object authorship
as the task-completion surface without a strong protocol scaffold.

## Limitations

All repairs used a full target object. This deliberately tests recoverability,
not minimal prompting. It does not show that field-name-only or field-value
initialization repairs would work.

H234 was not exercised because there were no prose-only repair failures in the
six conditioned attempts. The runner still records enough raw output, response
text, final state, and missing-field lists to identify such failures if they
occur in a future panel.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/conditioned_init_repair_20260605/run_conditioned_init_repair.py
timeout 1200s uv run python experiments/event_loop/conditioned_init_repair_20260605/run_conditioned_init_repair.py
```

Results:

- py_compile passed;
- live runner exited with code 0;
- six conditioned repair calls completed;
- six durable repairs succeeded;
- zero errors occurred.
