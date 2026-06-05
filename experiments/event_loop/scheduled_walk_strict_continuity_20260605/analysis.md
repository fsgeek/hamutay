# Scheduled Walk Strict Continuity Analysis

Date: 2026-06-05

## Result

The strict continuity gate passed across all four DeepSeek replicates.

- H168 strict validator detects first-pass failures: passed.
- H169 at least one strict repair succeeds: passed.
- H170 every accepted state preserves continuity: passed.
- H171 unrepaired strict failures are not silently accepted: passed.
- H172 strict repair remains bounded: passed.

All four replicates initialized, scheduled one walk-context event, completed the
scheduled wake, received four adjacent walk-path entries, failed first-pass
strict validation, and were repaired in one additional backend call.

## Summary

Aggregate result:

- 4/4 initializations valid;
- 4/4 scheduled events completed;
- 4/4 event context payloads contained a four-entry adjacent walk path;
- 4/4 first-pass wake states were strict-invalid;
- 4/4 repair attempts succeeded;
- 4/4 final states were evidence-valid;
- 4/4 final states were continuity-valid;
- 0 bounded-call violations;
- 0 recursive scheduling events;
- 0 response/state mismatches after repair.

Every scheduled wake used exactly two backend calls: one first pass and one
repair call.

## What Failed First Pass

The first-pass scheduled wake did not record the required walk evidence in any
replicate, despite the response mentioning walk/graph/path evidence.

Common first-pass evidence failures:

- `walk_gate_status`;
- `observed_walk_endpoint_count`;
- all required `observed_walk_edge_types`;
- `observations.scheduled_walk`.

Continuity was mostly stable on first pass:

- Replicates 1, 3, and 4 preserved the strict continuity invariants.
- Replicate 2 changed `probe_id`, and the strict validator detected it.
- Replicates 3 and 4 deleted `_activity_log`; that was logged but not counted
  as a failure because the preregistered disallowed deletions were `probe_id`
  and `cycle`.

## What Repair Changed

The strict repair prompt supplied a complete target durable object with:

- exact seeded `probe_id`;
- expected wake `cycle == 3`;
- baseline observation;
- scheduled-walk observation;
- graph-walk evidence fields.

The repair turn produced strict-valid state in all four replicates. In
replicate 2, this corrected the first-pass `probe_id` drift. No repair deleted
`probe_id` or `cycle`, and all final states preserved the baseline observation.

## Interpretation

The prior continuity drift was primarily a validator-contract defect, not an
immediate scaffold impossibility. When the repair target names continuity
invariants explicitly, DeepSeek can repair both the graph evidence and the
continuity fields under the bounded scaffold.

This does not mean the scheduled wake behavior is solved. The stronger finding
is that the autonomous first pass still fails to use the delivered walk context
durably. The model speaks as if it has handled the walk evidence, but without
the scaffold repair it does not persist the required evidence fields. The
validator/repair layer is therefore functioning as a necessary gate rather than
as a cosmetic cleanup.

## Design Implications

The event-loop substrate should keep strict post-cycle validation as part of
scheduled wake execution. For research use, the validator should report at
least two separate axes:

- task evidence validity;
- continuity validity.

The scaffold should continue to log first-pass invalidity rather than hiding it
behind repaired success. The first-pass failures are valuable data: they show
where the model fails to translate event-envelope evidence into durable state
without correction.

The `_activity_log` deletions in two replicates are a useful follow-up signal.
They were not preregistered as strict continuity failures here, but they suggest
the next validator pass should distinguish model-owned identity fields from
framework-owned audit fields.

## Next Boundary

The next useful research question is no longer whether strict repair can
preserve continuity. It can in this narrow gate.

The next boundary is whether the event-loop scheduler should protect
framework-owned fields from model deletion/overwrite, or whether protection
should remain advisory through validators. A targeted falsification experiment
would compare:

- advisory validation only; and
- hard reservation of framework-owned fields such as `cycle`, `_activity_log`,
  and scheduler/audit metadata.

That would separate "the model can repair when told" from "the substrate should
make some classes of continuity damage impossible."

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/scheduled_walk_strict_continuity_20260605/run_scheduled_walk_strict_continuity.py
timeout 1200s uv run python experiments/event_loop/scheduled_walk_strict_continuity_20260605/run_scheduled_walk_strict_continuity.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- four of four replicates initialized validly.
- four of four scheduled events completed.
- four of four completed events had four-entry adjacent walk context.
- four of four wakes failed first-pass strict validation.
- four of four wakes were repaired by the scaffold.
- four of four final states were strict-valid.
- focused regression suite: 283 passed.
