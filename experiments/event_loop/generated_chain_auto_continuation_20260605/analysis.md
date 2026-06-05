# Analysis: Generated Chain Auto-Continuation

Date: 2026-06-05

## Result

The live auto-continuation panel produced a mixed result.

Positive endpoints:

- rows: 2;
- first wake completed: 2/2;
- first wake first-pass strict-valid: 2/2;
- first wake exact-phrase durable leaks: 0/2;
- first wake continuation requested: 2/2;
- scheduler returned an auto-continuation event: 2/2;
- scheduler appended an auto-continuation event: 2/2;
- appended event bound to generated first-wake result record: 2/2;
- second wake received cycle-1 recall: 2/2;
- second wake received bound generated-record recall: 2/2;
- second wake first-pass strict-valid: 2/2;
- final phrase recovered: 2/2;
- generated intermediate used: 2/2;
- broad repair attempted: 0/2.

Failure endpoint:

- second due step hit the scheduler limit in both rows;
- second backend calls: 4/row;
- extra auto-continuations after second wake: 8 total;
- quiescent after second wake: 0/2.

Hypothesis outcomes:

- H421 passed.
- H422 passed.
- H423 passed.
- H424 passed.
- H425 failed.

## What Happened

The intended chain worked:

1. first wake committed a non-secret `chain_intermediate`;
2. first wake durable state contained a complete `continuation_request`;
3. `step_pending_events(..., auto_continuations=True)` appended a second event;
4. the second event was bound to the first wake's generated `result_record_id`;
5. second wake recalled cycle 1 plus the generated first-wake record;
6. second wake recovered the phrase and used the intermediate.

But the second wake inherited the first wake's `continuation_request` through
default-stable durable state. Because `auto_continuations=True` blindly
inspected top-level `continuation_request` after every completed event, the
second wake appended another second wake. That repeated until the scheduler
step reached its limit.

This is a real scheduler-design failure, not a provider failure and not a
model-state failure. The live model did the bounded task; the substrate failed
to consume or scope the continuation request.

## Scoring Note

The first aggregate pass undercounted this failure because completed event-log
records do not repeat the pending event label. The runner was corrected to
join completed records back to pending labels by `event_id`, and the original
first-pass result file was preserved as `initial_looping_results.json`.

No new live calls were made during rescoring.

## Interpretation

This result is more valuable than a clean pass would have been. It shows that
the generated continuation mechanism is strong enough to complete the chain,
but unsafe as an always-on post-completion policy unless continuation requests
have consumption semantics.

The event loop now needs an explicit one-shot or consumed-continuation
invariant:

- a continuation request should be consumed after append;
- or a continuation request should include `source_cycle` / `source_record_id`
  and only be honored when it belongs to the just-completed record;
- or terminal surfaces for terminal wakes must delete/shed continuation
  requests;
- preferably the substrate should record consumed continuation request IDs so
  inherited state cannot re-trigger the same request.

The least fragile design is substrate consumption. Relying on the model to
delete `continuation_request` in every terminal wake repeats the same
state-object compliance problem this research arm has repeatedly exposed.

## Design Implication

`auto_continuations=True` should not mean "append whenever current durable
state contains a requested continuation." It should mean:

1. identify a continuation request authored by this completed wake;
2. append at most one bound continuation for that request;
3. mark the request consumed in substrate metadata;
4. do not re-trigger inherited continuation requests in later wakes.

That is the next sharp falsification target.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/generated_chain_auto_continuation_20260605/run_generated_chain_auto_continuation.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 1200s uv run python experiments/event_loop/generated_chain_auto_continuation_20260605/run_generated_chain_auto_continuation.py
timeout 120s uv run python experiments/event_loop/generated_chain_auto_continuation_20260605/run_generated_chain_auto_continuation.py
```

The second runner invocation was resume/rescore only; it made no new model
calls.
