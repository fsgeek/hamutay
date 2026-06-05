# Analysis: Budgeted Three-Wake Chain Repair

Date: 2026-06-05

## Result

The repaired budgeted three-wake chain passed.

Aggregate:

- rows: 2;
- first wake strict-valid: 2/2;
- bridge wake strict-valid: 2/2;
- final wake strict-valid: 2/2;
- first wake first-pass valid: 2/2;
- bridge wake first-pass valid: 2/2;
- final wake first-pass valid: 2/2;
- first/bridge phrase leaks: 0/2;
- bridge received first-record context: 2/2;
- final received bridge-record context: 2/2;
- final phrase recovered: 2/2;
- final evidence used bridge record: 2/2;
- repair attempts: 0/2;
- step 1 budget stop: 2/2;
- step 2 budget stop: 2/2;
- step 3 quiescent: 2/2.

Hypothesis outcomes:

- H481 passed.
- H482 passed.
- H483 passed.
- H484 passed.
- H485 passed.

## Comparison To Failed Panel

The failed panel was
`experiments/event_loop/budgeted_three_wake_chain_20260605`.

Prior result:

- step 1/2 budget stops worked: 2/2;
- final phrase recovered: 2/2;
- final bridge-record context delivered: 0/2;
- final strict-valid: 0/2;
- first/bridge strict-valid: 1/2;
- phrase leak in first/bridge path: present in replicate 1.

Repair result:

- step 1/2 budget stops worked: 2/2;
- final phrase recovered: 2/2;
- final bridge-record context delivered: 2/2;
- final strict-valid: 2/2;
- first/bridge strict-valid: 2/2;
- phrase leaks: 0/2.

## Interpretation

The two repairs addressed the two observed failure classes:

1. Placeholder scoping preserved nested future continuation templates, so the
   final event was bound to the bridge wake result record rather than the
   first wake result record.
2. Closed non-secret schemas prevented the model from placing the exact phrase
   in explanatory side fields.

The scheduler-budget policy also survived live use:

- step 1 ran the first wake, appended bridge, and stopped;
- step 2 ran bridge, appended final, and stopped;
- step 3 ran final and quiesced.

This is the first clean positive map point for a generated three-wake chain
split across scheduler steps by continuation budget.

## Design Implication

The event-loop substrate now has a workable pattern for longer bounded chains:

- terminal surfaces for bounded wake outputs;
- fresh raw-output continuation requests;
- placeholder scoping for nested future requests;
- `max_auto_continuations` to split continuation chains across scheduler
  steps;
- closed schemas for non-secret intermediates.

This is a stronger control-loop result than the earlier two-wake chain because
it tests both generated continuation and scheduler pacing across multiple
steps.

## Remaining Cautions

This remains a tiny single-model panel. It demonstrates feasibility of the
substrate pattern, not cross-model reliability.

The next interesting question is policy and autonomy rather than mechanics:
how should an instance choose between stopping, continuing immediately,
continuing after simulated time, or asking for external evidence before the
next wake?

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/budgeted_three_wake_chain_repair_20260605/run_budgeted_three_wake_chain_repair.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 1800s uv run python experiments/event_loop/budgeted_three_wake_chain_repair_20260605/run_budgeted_three_wake_chain_repair.py
jq '.summary' experiments/event_loop/budgeted_three_wake_chain_repair_20260605/results.json
```
