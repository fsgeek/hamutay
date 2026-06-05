# Behavior Seeded Walk Gate Analysis

Date: 2026-06-05

## Result

The behavior seed partially worked. It got one DeepSeek replicate past the
initialization gate, but the direct walk-evidence follow-up still failed to
persist the graph evidence durably.

- H132 behavior seed improves durable initialization: passed.
- H133 seeded direct follow-up receives equivalent graph evidence: passed for
  the valid initialized replicate.
- H134 seeded direct follow-up durably records graph evidence: failed.
- H135 seeded prose/object mismatch remains observable: passed.

## Scenario Results

### Replicate 1

The model followed the behavior seed during initialization. Durable top-level
state contained:

- `probe_id`
- `walk_gate_status == "initialized"`
- `observations`

The direct follow-up then delivered equivalent graph evidence:

- adjacent walk path count: 4
- edge types: `depends_on`, `branches_from`, `composes_with`

The visible response accurately described the evidence:

- four records;
- three distinct edge types;
- the expected endpoint IDs and edge types.

But durable state did not record the required update:

- `walk_gate_status` remained `"initialized"` rather than `"woke"`;
- `observed_walk_endpoint_count` was absent;
- `observed_walk_edge_types` was absent;
- no observation was appended.

This is a clean direct-follow-up prose/object mismatch after valid seeded
initialization.

### Replicate 2

The model did not follow the behavior seed during initialization. Its visible
response said `Initialized.`, but durable state again contained only framework
keys.

No direct follow-up was run.

## Interpretation

The behavior seed answers the initialization confound enough to move the
boundary forward. DeepSeek can author the required initialization object when
shown the exact shape, but that does not generalize to the next graph-evidence
update.

The active failure is therefore not just first-cycle object literacy. It is a
durable-update failure after the model has seen evidence and correctly
verbalized it. This aligns with the scheduled-wake finding:

- scheduled wake: graph evidence delivered, prose correct, durable update
  failed;
- seeded direct follow-up: graph evidence delivered, prose correct, durable
  update failed.

That makes event-envelope complexity less likely as the primary cause. The
stronger explanation is that DeepSeek treats visible answer production as task
completion unless the exact desired object shape is seeded at the point of
update.

## Design Implication

For this model, a one-time behavior seed is not enough. The next falsifiable
question is whether an update-time exemplar fixes the durable graph-evidence
write:

- show an explicit target object shape in the follow-up itself; or
- use a stricter schema-like "fields to output now" scaffold; or
- test a model with stronger identity-object literacy before adding more
  event-loop machinery.

The graph substrate and scheduler-walk context are no longer the weakest link
in this branch. The blocker is the transformer-to-identity-object update
behavior.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/behavior_seeded_walk_gate_20260605/run_behavior_seeded_walk_gate.py
timeout 240s uv run python experiments/event_loop/behavior_seeded_walk_gate_20260605/run_behavior_seeded_walk_gate.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- one of two DeepSeek seeded replicates passed initialization.
- the valid initialized replicate received equivalent walk evidence.
- zero replicates durably recorded graph evidence.
- full regression suite: 278 passed.
