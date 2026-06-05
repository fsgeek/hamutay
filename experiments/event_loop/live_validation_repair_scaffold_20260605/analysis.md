# Live Validation Repair Scaffold Analysis

Date: 2026-06-05

## Result

The built-in validation/repair scaffold reproduced the external-runner repair
finding under live DeepSeek calls.

- H158 built-in validator detects the known mismatch: passed.
- H159 built-in full-target repair recovers at least one live mismatch: passed.
- H160 repaired scaffold cycles remain auditable: passed.
- H161 unrepaired scaffold cycles are not silently accepted: passed.
- H162 repair remains bounded: passed.

## Scenario Results

All four replicates seeded the same known mismatch state from cycle 2 of:

`experiments/event_loop/strict_repair_walk_gate_20260605/deepseek__deepseek-v4-pro_strict_repair_r04.jsonl`

### Replicates 1-3

The first pass produced the expected light-prompt failure: the validator marked
the candidate state invalid with missing fields:

- `walk_gate_status`;
- `observed_walk_endpoint_count`;
- `observed_walk_edge_types.branches_from`;
- `observed_walk_edge_types.composes_with`;
- `observed_walk_edge_types.depends_on`;
- `observations.appended_direct_walk`.

The scaffold then ran exactly one full-target repair call. In all three
replicates, the repair output authored the required top-level durable fields,
and the second validation passed.

Each repaired log record contains:

- `state_validation.status == "repaired"`;
- `state_validation.first_pass.status == "invalid"`;
- `state_validation.repair.raw_output`;
- `state_validation.repair.validation.status == "valid"`;
- final durable state with no missing graph-walk fields.

Backend calls per repaired replicate: 2.

### Replicate 4

The first pass authored the required durable fields directly, even under the
lighter field-values prompt. The validator accepted it as first-pass valid, and
no repair was attempted.

Backend calls: 1.

## Interpretation

This is the first live evidence that the repair scaffold works inside
`OpenTasteSession`, not only as experiment-runner logic. The result preserves
the important distinction:

- one replicate was a clean first-pass durable update;
- three replicates were first-pass prose/object mismatches repaired by the
  scaffold.

That distinction would have been lost if the harness silently repaired state or
if the runner only inspected final state. The log now carries the research
signal: the model still frequently fails the light prompt, and the full-target
repair scaffold can recover that failure without hiding it.

## Design Implication

The event-loop substrate can now support task-specific validation/repair gates
for scheduled wakes. The next scheduled-event experiment should use this
scaffold around the graph-walk wake so that wake outcomes are classified as:

- first-pass success;
- repaired success;
- unrepaired mismatch;
- repair failure.

This should let us return to the original scheduler question without the
prose/object mismatch confound swallowing the result.

## Limitations

This experiment seeded a known mismatch state and used a full-target repair
builder. It does not prove that DeepSeek can repair from lighter prompts; the
conditioned repair variants already showed it generally cannot.

The experiment also does not yet exercise a scheduled wake with scaffolded
validation. It isolates the scaffold in a direct seeded repair setting.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/live_validation_repair_scaffold_20260605/run_live_validation_repair_scaffold.py
timeout 900s uv run python experiments/event_loop/live_validation_repair_scaffold_20260605/run_live_validation_repair_scaffold.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- four replicates completed.
- three first-pass mismatches were detected.
- three scaffold repairs were attempted.
- three scaffold repairs succeeded.
- zero bounded-call violations occurred.
- full regression suite: 283 passed.
