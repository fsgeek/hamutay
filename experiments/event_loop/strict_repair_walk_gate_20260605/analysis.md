# Strict Repair Walk Gate Analysis

Date: 2026-06-05

## Result

The strict repair turn recovered the one observed DeepSeek prose/object
mismatch. The result supports treating at least some failures as recoverable
protocol-shape errors, while preserving the initialization confound as an
active limitation.

- H140 repair gate produces at least one initial prose/object mismatch: passed.
- H141 strict repair turn can recover at least one mismatch: passed.
- H142 repair does not erase prior durable identity fields: passed.
- H143 repair outcomes remain auditable: passed.

## Scenario Results

### Replicate 1

The model initialized valid durable state and recorded graph evidence correctly
on the first follow-up:

- `probe_id` preserved;
- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types` contained `depends_on`, `branches_from`, and
  `composes_with`;
- `observations` included the appended `direct_walk` entry.

No repair turn was attempted because no mismatch occurred.

### Replicate 2

The model failed initialization. Its visible response said `Initialized.`, but
durable state contained only framework keys:

- `_activity_log`
- `cycle`

The direct graph-evidence follow-up was withheld, so this replicate is censored
for the repair question.

### Replicate 3

The model repeated the same initialization failure as replicate 2:

- visible response said `Initialized.`;
- durable state contained only `_activity_log` and `cycle`;
- no graph-evidence follow-up was run.

This preserves the first-cycle object-literacy confound seen in earlier
DeepSeek gates.

### Replicate 4

The model initialized valid durable state:

- `probe_id == "strict-repair-walk-deepseek__deepseek-v4-pro-r4-delta"`;
- `walk_gate_status == "initialized"`;
- one baseline observation.

The direct follow-up delivered equivalent graph evidence:

- adjacent walk path count: 4;
- edge types: `depends_on`, `branches_from`, `composes_with`.

Cycle 2 then produced a clean prose/object mismatch. The visible response said:

> Walk evidence recorded: four adjacent endpoints with depends_on,
> branches_from, and composes_with edges.

But raw output contained only:

- `response`;
- `deleted_regions: []`.

The durable state therefore remained initialized and did not include the
graph-evidence fields.

The strict repair turn named the mismatch, showed the current durable state,
listed the missing fields, and supplied the target durable object. Cycle 3
then emitted the full top-level durable update:

- `probe_id` preserved;
- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types == ["depends_on", "branches_from",
  "composes_with"]`;
- `observations` preserved the baseline entry and appended the `direct_walk`
  entry.

This is a direct recovery of the exact failure class observed in the
update-exemplar gate.

## Cross-Gate Comparison

Recent DeepSeek graph-evidence gates now form a useful sequence:

- unseeded direct walk gate: 0 of 2 replicates passed initialization;
- behavior-seeded walk gate: 1 of 2 replicates passed initialization, 0 of 1
  valid replicates durably recorded graph evidence;
- update-exemplar walk gate: 2 of 2 replicates passed initialization, 1 of 2
  valid replicates durably recorded graph evidence;
- strict-repair walk gate: 2 of 4 replicates passed initialization, 1 of 2
  valid replicates recorded on first follow-up, and the one mismatch was
  recovered by repair.

The repair result does not eliminate the identity-object literacy problem.
Replicates 2 and 3 still failed at initialization despite the behavior seed.
But for a later-cycle graph-evidence mismatch after valid initialization, the
model was able to repair the durable object when the mismatch was explicitly
named.

## Interpretation

This is evidence for a recoverable adapter boundary. DeepSeek is not reliably
using the durable object as the default completion surface, but a second
state-focused turn can sometimes move it from prose-only compliance to actual
state update.

That distinction matters for event-loop design:

- the scheduler and graph substrate can deliver evidence;
- the model can understand and verbalize the evidence;
- the model can fail to persist the evidence;
- the same model can repair that failure when the protocol names the mismatch.

The result argues against silently accepting prose/state mismatches. It also
argues against treating every mismatch as unrecoverable. The better scaffold
policy is likely strict validation plus a bounded repair opportunity, with the
repair outcome logged as first-class data.

## Design Implication

The next implementation step should be an adapter design, not a broader model
sweep:

- define a validation contract for task-specific durable updates;
- detect when visible prose claims an update that state does not carry;
- run at most one repair turn with the current durable state and missing
  fields;
- mark the cycle as repaired, unrepaired, or censored;
- preserve both the failed output and the repair output in the log.

This should remain opt-in per experiment or event policy. The identity object
should not become an implicit hidden chain-of-thought target, and the harness
should not mutate state on the model's behalf. The invariant remains: no state
evolution based on tool or repair evidence the model has not seen and authored.

## Limitations

The sample is small and only one mismatch reached repair. The result supports
recoverability, not reliability. It also leaves the initialization failure
unsolved: two of four replicates failed before the repair question was
interpretable.

The repair prompt supplied a full target object. That is appropriate for this
gate because the question was recoverability, but future work should separate
full-object repair from lighter missing-field repair.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/strict_repair_walk_gate_20260605/run_strict_repair_walk_gate.py
timeout 900s uv run python experiments/event_loop/strict_repair_walk_gate_20260605/run_strict_repair_walk_gate.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- two of four DeepSeek replicates passed initialization.
- two of two valid replicates received equivalent walk evidence.
- one of two valid replicates initially showed a prose/object mismatch.
- one repair was attempted.
- one repair succeeded.
- zero repaired replicates remained mismatched.
- full regression suite: 278 passed.
