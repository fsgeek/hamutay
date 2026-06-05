# Analysis: Generated Bound Chain Terminal Surface

Date: 2026-06-05

## Result

The generated bound-chain terminal-surface panel passed cleanly.

Aggregate:

- rows: 2;
- first wake completed: 2/2;
- first wake terminal parse/state-record success: 2/2;
- first wake strict-valid: 2/2;
- first wake first-pass valid: 2/2;
- first wake exact-phrase durable leaks: 0/2;
- continuation requested: 2/2;
- bound second event appended: 2/2;
- second wake completed: 2/2;
- second wake received cycle-1 context: 2/2;
- second wake received bound generated-record context: 2/2;
- second wake terminal parse/state-record success: 2/2;
- second wake strict-valid: 2/2;
- second wake first-pass valid: 2/2;
- final phrase recovered: 2/2;
- generated intermediate used: 2/2;
- first-wake repair attempted: 0/2;
- second-wake repair attempted: 0/2;
- terminal-surface observability for both wakes: 2/2;
- bounded-call violations: 0/2;
- runner/provider errors: 0/2.

Hypothesis outcomes:

- H391 passed.
- H392 passed.
- H393 passed.
- H394 passed.
- H395 passed.

## Comparison To Prior Negative Result

The direct baseline is
`experiments/event_loop/substrate_bound_chain_20260605`.

In that prior broad-surface panel:

- first wake completed: 2/2;
- first wake valid: 0/2;
- continuation requested: 0/2;
- bound second event appended: 0/2;
- second wake completed: 0/2.

The failure was response/state divergence: the model described
`chain_intermediate` and `continuation_request` in prose, but did not commit
them as durable fields.

In this terminal-surface panel:

- first wake valid: 2/2;
- continuation requested: 2/2;
- bound second event appended: 2/2;
- second wake completed: 2/2.

The terminal surface converted the first-wake continuation contract from a
prose instruction into a narrow completion object. That removed the earlier
state-object compliance failure and allowed the record-ID binding question to
be tested.

## Record-ID Binding

Both second events were bound to the first completed event's generated
`result_record_id`, not to a seeded or guessed future cycle. Both second wakes
received:

- `recall(cycle=1)` for the original deferred phrase;
- `recall(record_id=<first-result>, field="chain_intermediate")` for the
  generated non-secret intermediate.

Both second wakes then recovered the exact phrase and referenced
`word-word-number` from the bound intermediate. This is the first clean positive
map point for generated multi-event continuity using record-ID binding rather
than seeded first-wake records or model-guessed cycle addresses.

## Interpretation

This result materially strengthens the event-loop design:

1. A first event can consume exact recall and commit only a non-secret derived
   intermediate.
2. The substrate can bind a later event to the first event's generated record
   after the state is committed.
3. A second event can recall both the original seed and the generated
   intermediate by record ID.
4. Narrow terminal surfaces can make both wakes first-pass strict-valid without
   broad durable-state repair.

The result also clarifies the previous negative finding. The substrate-bound
chain did not fail because record-ID recall was unavailable. It failed because
the broad first-wake surface did not reliably produce the required durable
object. Once that surface was narrowed, generated record-ID recall worked in
both rows.

## Design Implication

The scheduler should treat generated continuation as a substrate operation:

- the instance may request continuation by committing a durable
  `continuation_request`;
- the substrate should bind the next event to the actual `result_record_id`
  after commit;
- later wakes should recall generated records by `record_id`, optionally with
  field filtering;
- bounded stages should use terminal surfaces rather than broad
  `think_and_respond`;
- repair should remain explicit and separately tested, not silently attached
  to normal scheduled wakes.

This is now enough to justify building a small reusable event-loop primitive
for generated continuations: validate the first wake, bind the next event to
its committed record, and preserve lifecycle/context observability.

## Remaining Cautions

This remains a two-replicate, one-model panel. It demonstrates feasibility and
removes a specific confound, but it does not prove broad reliability. The
scaffold is also still runner-mediated: the runner appended the second event
after reading the validated continuation request. A production event loop needs
that binding behavior implemented as a normal scheduler phase.

The next engineering-research move is to turn this runner-mediated pattern into
a reusable scheduler primitive and then smoke-test it with the same generated
bound-chain task.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/generated_bound_chain_terminal_surface_20260605/run_generated_bound_chain_terminal_surface.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 1200s uv run python experiments/event_loop/generated_bound_chain_terminal_surface_20260605/run_generated_bound_chain_terminal_surface.py
jq '.summary' experiments/event_loop/generated_bound_chain_terminal_surface_20260605/results.json
```

Targeted tests passed: `94 passed`.
