# Direct Walk Evidence Gate Analysis

Date: 2026-06-05

## Result

The direct arm was censored before the intended graph-evidence follow-up in both
replicates.

- H128 direct follow-up can initialize durable walk-gate state: failed.
- H129 direct follow-up receives equivalent graph evidence: not interpretable
  as a live follow-up because no replicate passed initialization.
- H130 direct follow-up durably records graph evidence: not reached.
- H131 direct prose/object mismatch is observable: passed.

## Scenario Results

### Replicate 1

The model visibly claimed initialization:

- `probe_id` was named in visible prose;
- `walk_gate_status` was described as initialized;
- observations were described as seeded.

But durable state contained only framework keys:

- final top-level keys: `_activity_log`, `cycle`
- `probe_id`: absent
- `walk_gate_status`: absent
- `observations`: absent

The runner did not deliver the direct follow-up evidence because the
initialization gate failed.

### Replicate 2

The same failure repeated. The visible response described the requested fields,
but the durable object again contained only framework keys:

- final top-level keys: `_activity_log`, `cycle`
- `probe_id`: absent
- `walk_gate_status`: absent
- `observations`: absent

The direct follow-up was withheld for the same reason.

## Graph Evidence Equivalence

In both replicates, the runner had already built and resolved the intended graph
evidence before the live initialization cycle:

- adjacent walk path count: 4
- edge types: `depends_on`, `branches_from`, `composes_with`

This means the substrate could have supplied the same evidence as the completed
scheduled wake from the prior gate. The comparison was censored by initialization
failure, not by missing graph evidence.

## Interpretation

This experiment did not answer whether direct follow-up cures DeepSeek's
scheduled-wake durable-update failure. It found an earlier and sharper boundary:
DeepSeek repeatedly narrates initialization while failing to author the
requested identity-object fields.

That makes the direct-vs-scheduled graph-evidence comparison uninterpretable
without an initialization intervention. The useful result is negative but
clarifying: for DeepSeek, the current open identity-object protocol is unstable
even before graph evidence is introduced.

The active confound is now initialization literacy, not graph-walk delivery and
not scheduler mechanics.

## Design Implication

The next experiment should not add more event-loop machinery. It should test
whether a behavior seed or schema exemplar can make DeepSeek author the required
top-level state fields reliably enough for downstream direct/scheduled
comparisons to be meaningful.

If a behavior seed fixes initialization, then we can retry the direct walk
evidence follow-up and compare it to the scheduled wake baseline. If it does
not, DeepSeek is not an interpretable candidate for this research arm without
additional training or a stronger protocol adapter.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/direct_walk_evidence_gate_20260605/run_direct_walk_evidence_gate.py
timeout 240s uv run python experiments/event_loop/direct_walk_evidence_gate_20260605/run_direct_walk_evidence_gate.py
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- live runner exited with code 0.
- two DeepSeek direct replicates completed initialization cycle.
- zero DeepSeek direct replicates passed initialization.
- full regression suite: 278 passed.
