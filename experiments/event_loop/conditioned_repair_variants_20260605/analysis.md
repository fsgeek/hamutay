# Conditioned Repair Variants Analysis

Date: 2026-06-05

## Result

Conditioning directly on a known mismatch state produced a clean prompt-shape
split:

- full target object repair: 2 of 2 succeeded;
- field-values repair: 0 of 2 succeeded;
- field-names-only repair: 0 of 2 succeeded.

All four failed lighter repairs produced visible prose claiming the repair had
been completed while leaving the durable state unchanged.

- H148 conditioned full-target repair recovers reliably: passed.
- H149 conditioned field-values repair can recover: failed.
- H150 conditioned field-names-only repair can recover: failed.
- H151 repair success preserves prior identity fields: passed.
- H152 variant outcomes are auditable: passed.

## Source State

All six runs seeded the same preserved mismatch state from:

`experiments/event_loop/strict_repair_walk_gate_20260605/deepseek__deepseek-v4-pro_strict_repair_r04.jsonl`

Cycle 2 had:

- `probe_id == "strict-repair-walk-deepseek__deepseek-v4-pro-r4-delta"`;
- `walk_gate_status == "initialized"`;
- one baseline observation;
- no `observed_walk_endpoint_count`;
- no `observed_walk_edge_types`;
- no appended `direct_walk` observation.

The prior visible response in that source run had claimed the walk evidence was
recorded, so this is the exact prose/object mismatch we wanted to condition on.

## Variant Results

### Full Target Object

Both full-target replicates repaired durable state correctly. The raw output
included top-level fields for:

- `probe_id`;
- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types == ["depends_on", "branches_from",
  "composes_with"]`;
- `observations` with the baseline entry preserved and a `direct_walk` entry
  appended.

This reproduces the strict-repair success under controlled conditions.

### Field Values

Both field-values replicates failed durable repair despite explicit field-level
values.

The visible responses said the repair was applied and named the correct values,
including:

- `walk_gate_status: woke`;
- `observed_walk_endpoint_count: 4`;
- `observed_walk_edge_types: depends_on, branches_from, composes_with`;
- an appended `direct_walk` observation.

But raw output contained only:

- `response`;
- `deleted_regions: []`.

The durable state carried forward unchanged from the seeded mismatch state.

### Field Names Only

Both field-names-only replicates also failed durable repair. They produced
visible repair prose, but raw output again contained only:

- `response`;
- `deleted_regions: []`.

The model even invented a plausible alternate status value,
`"evidence_recorded"`, in visible prose, but did not author it into durable
state. The durable object still retained `walk_gate_status == "initialized"`.

## Interpretation

This is the cleanest evidence so far that DeepSeek's repair behavior is
strongly shape-dependent. The model did not merely need to be told which fields
were missing. It needed the complete target object in the same form the harness
expects it to author.

That has two implications:

1. A naive "you forgot these fields" repair adapter is insufficient for this
   model.
2. A full-object repair adapter can recover the failure, but it risks becoming
   a copy scaffold rather than evidence of robust identity-object literacy.

The result strengthens the training-mismatch interpretation. DeepSeek can
describe state mutation fluently, but unless the expected object shape is
present as an output exemplar, it tends to put the mutation in prose rather
than the structured object.

## Design Implication

For the event-loop scaffold, repair should not be designed as a casual natural
language reminder. If we implement repair, it should be explicit and auditable:

- validate durable state against a task-specific contract;
- when repair is allowed, supply a concrete expected object or schema;
- log the original failure and repair attempt separately;
- record whether the repair was copy-shaped, field-shaped, or schema-shaped;
- never mutate state on behalf of the model.

The next engineering move is probably not another DeepSeek repair variant. The
experiment has mapped enough of this boundary to justify building an opt-in
validation/repair scaffold around the event loop. That scaffold should preserve
the distinction between first-pass success, repaired success, and unrepaired
prose/object mismatch.

## Limitations

This used one source mismatch state and two replicates per variant. The result
is a strong local boundary, not a population estimate.

The full-target condition supplies more structure than a training-free open
identity object would ideally need. That is the point of the result, but it
also means full-target repair should be interpreted as a protocol scaffold, not
as evidence that the model independently understands the durable object
contract.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/conditioned_repair_variants_20260605/run_conditioned_repair_variants.py
timeout 900s uv run python experiments/event_loop/conditioned_repair_variants_20260605/run_conditioned_repair_variants.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- six conditioned repair calls completed.
- full-target repair succeeded 2 of 2.
- field-values repair succeeded 0 of 2.
- field-names-only repair succeeded 0 of 2.
- four visible repair/prose-only mismatches were observed and scored.
- full regression suite: 278 passed.
