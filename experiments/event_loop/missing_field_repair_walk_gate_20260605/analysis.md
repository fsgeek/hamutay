# Missing-Field Repair Walk Gate Analysis

Date: 2026-06-05

## Result

The missing-field repair gate did not reach a repair attempt. Three of four
DeepSeek replicates failed initialization, and the one valid initialized
replicate recorded graph evidence correctly on the first follow-up.

- H144 missing-field repair gate produces at least one initial mismatch:
  failed.
- H145 missing-field repair can recover at least one mismatch: failed by the
  preregistered scoring rule, but the repair mechanism was not exercised.
- H146 missing-field repair preserves prior identity fields: failed by the
  preregistered scoring rule, but no successful repair was available to inspect.
- H147 missing-field repair outcomes distinguish copy-dependence: passed.

## Scenario Results

### Replicate 1

The model failed initialization. Raw output contained:

- `response: "Initialized."`
- `deleted_regions: []`

Durable state contained only framework keys:

- `_activity_log`
- `cycle`

The direct graph-evidence follow-up was withheld.

### Replicate 2

The same initialization failure repeated:

- visible response said `Initialized.`;
- durable state contained only `_activity_log` and `cycle`;
- no graph-evidence follow-up was run.

### Replicate 3

The model initialized valid durable state and then recorded graph evidence on
the first follow-up:

- `probe_id` preserved;
- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types` contained `depends_on`, `branches_from`, and
  `composes_with`;
- `observations` preserved the baseline entry and appended the `direct_walk`
  entry.

No repair turn was attempted because no prose/object mismatch occurred.

### Replicate 4

The model repeated the initialization failure from replicates 1 and 2:

- visible response said `Initialized.`;
- durable state contained only `_activity_log` and `cycle`;
- no graph-evidence follow-up was run.

## Interpretation

This result is mostly a censoring result. It does not answer whether
missing-field repair is sufficient, because no replicate reached the repair
condition. The operational hypotheses H144-H146 are false for this run, but
the mechanism question remains open.

The more important observation is that the initialization confound remains
large. Across the recent DeepSeek gates:

- update-exemplar walk gate: 2 of 2 replicates initialized validly;
- strict-repair walk gate: 2 of 4 initialized validly;
- missing-field repair walk gate: 1 of 4 initialized validly.

That variance is itself evidence against relying on small-N live gates to
produce clean downstream repair cases. If the question is specifically repair
behavior, the next design should condition on a known mismatch state rather
than waiting for the live run to generate one stochastically.

## Design Implication

The next experiment should separate repair from initialization. A clean design
would replay or reconstruct a known mismatch state, then ask a fresh model
cycle to repair it under different repair prompt conditions:

- full target object;
- missing fields plus expected values;
- missing fields only;
- schema-constrained state-only repair.

That would test copy-dependence directly and avoid burning most replicates on
initialization failures.

The event-loop scaffold implication remains unchanged: validation/repair looks
promising, but it should be designed around explicit state validation and
censoring semantics. The harness should not silently mutate state, and it
should not count a repair experiment as interpretable unless a repair condition
actually occurred.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/missing_field_repair_walk_gate_20260605/run_missing_field_repair_walk_gate.py
timeout 900s uv run python experiments/event_loop/missing_field_repair_walk_gate_20260605/run_missing_field_repair_walk_gate.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- one of four DeepSeek replicates passed initialization.
- one of one valid replicate received equivalent walk evidence.
- zero initial prose/object mismatches occurred.
- zero repairs were attempted.
- zero repairs succeeded.
- full regression suite: 278 passed.
