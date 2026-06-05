# Analysis: Generated Chain Auto-Continuation Repair

Date: 2026-06-05

## Result

The generated-chain auto-continuation repair panel passed.

Aggregate:

- rows: 2;
- first wake first-pass strict-valid: 2/2;
- first wake exact-phrase durable leaks: 0/2;
- scheduler auto-continuation returned: 2/2;
- scheduler auto-continuation appended: 2/2;
- appended event bound to first wake result record: 2/2;
- second wake completed: 2/2;
- second wake received cycle-1 context: 2/2;
- second wake received bound generated-record context: 2/2;
- second wake first-pass strict-valid: 2/2;
- final phrase recovered: 2/2;
- generated intermediate used: 2/2;
- first wake repair attempted: 0/2;
- second wake repair attempted: 0/2;
- second backend calls: 1 per row;
- extra auto-continuations after second wake: 0;
- bounded-call violations: 0/2;
- quiescent after second wake: 2/2.

Hypothesis outcomes:

- H441 passed.
- H442 passed.
- H443 passed.
- H444 passed.
- H445 passed.

## Comparison To Failed Panel

The failed panel was
`experiments/event_loop/generated_chain_auto_continuation_20260605`.

Prior result:

- first wake valid: 2/2;
- first auto-continuation appended: 2/2;
- second wake valid: 2/2;
- final recovery: 2/2;
- extra auto-continuations after second wake: 8 total;
- bounded-call violations: 2/2;
- second step stop reason: `limit_reached`.

Repair result:

- first wake valid: 2/2;
- first auto-continuation appended: 2/2;
- second wake valid: 2/2;
- final recovery: 2/2;
- extra auto-continuations after second wake: 0;
- bounded-call violations: 0/2.

The chain behavior was preserved while the inherited-continuation loop was
removed.

## Interpretation

The new-output gate appears to be the right consumption boundary for this
stage of the scheduler:

- durable state can remain default-stable;
- inherited `continuation_request` can remain visible;
- the scheduler only acts when the current raw output emits a continuation
  request.

This avoids requiring the model to remember to delete or mutate control fields
after completion. It also preserves bounded autonomy: the instance can emit a
continuation request when it wants the substrate to call it back, but inherited
requests do not become implicit infinite loops.

## Design Implication

Generated continuation is now viable as an event-loop primitive:

1. first wake emits a bounded continuation request;
2. substrate binds the next event to the actual result record;
3. second wake consumes original and generated-record recall;
4. scheduler quiesces unless the second wake emits a fresh continuation.

That last clause is the important invariant. Continuation is now edge-triggered
by newly emitted raw output, not level-triggered by persistent durable state.

## Remaining Cautions

This is still a tiny single-model panel. It validates the substrate behavior
and demonstrates one live chain, but it does not establish model-family
generality.

The next useful research move is no longer this specific two-wake chain. The
next boundary is policy: when should `auto_continuations=True` be enabled, and
how should the scheduler report or suppress pathological continuation rates
across longer chains?

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/generated_chain_auto_continuation_repair_20260605/run_generated_chain_auto_continuation_repair.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 1200s uv run python experiments/event_loop/generated_chain_auto_continuation_repair_20260605/run_generated_chain_auto_continuation_repair.py
timeout 120s uv run python experiments/event_loop/generated_chain_auto_continuation_repair_20260605/run_generated_chain_auto_continuation_repair.py
jq '.summary' experiments/event_loop/generated_chain_auto_continuation_repair_20260605/results.json
```

The second runner invocation was resume/rescore only; it made no new model
calls.
