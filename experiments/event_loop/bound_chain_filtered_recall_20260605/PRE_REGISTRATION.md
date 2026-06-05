# Pre-Registration: Bound Chain With Filtered Record Recall

Date: 2026-06-05

## Research Question

Can substrate-bound continuation use in-session `record_id` recall while
delivering only the non-secret intermediate field, avoiding framework
`_activity_log` leakage?

The patched bound-chain rerun showed that in-session `record_id` recall can
resolve a newly produced wake record, but full-record recall returned
`_activity_log`. In the successful row, that activity log contained a bash
command with the exact phrase. The next narrow question is whether filtered
record recall can deliver the intended intermediate without that leakage.

## Hypotheses

- H316: A filtered bound record request
  `recall(record_id=<first_wake_record>, field="chain_intermediate")` resolves
  in at least one row.
- H317: The filtered bound context does not contain the exact phrase or
  `_activity_log`.
- H318: At least one second wake recovers the exact phrase from cycle-1 recall
  and incorporates the filtered first-wake intermediate.
- H319: First-wake durable update contract behavior remains non-regressed:
  at least one row validates and requests continuation.
- H320: Artifacts distinguish filtered bound context delivery, final recovery,
  and leakage status.

## Method

Run two live DeepSeek v4 Pro replicates using the same model-facing first-wake
event purpose, durable update contract, durable update example, and second-wake
purpose as `bound_chain_contract_20260605`.

The only intended method change is the substrate-bound second event's requested
context:

Before:

```json
{"tool": "recall", "record_id": "<first_wake_result_record_id>"}
```

After:

```json
{
  "tool": "recall",
  "record_id": "<first_wake_result_record_id>",
  "field": "chain_intermediate"
}
```

The second event still also requests `recall(cycle=1)` for exact phrase
recovery.

## Predictions

If field-filtered record-ID recall works:

- the bound record context result will contain only `chain_intermediate`;
- it will not contain `_activity_log`;
- it will not contain the exact phrase;
- second wake final evidence should reference `word-word-number`.

If second wake recovery fails despite filtered delivery, the limiting factor is
model integration of field-only context, not substrate addressing.

## Falsification Criteria

- H316 is falsified if no row receives filtered bound record context.
- H317 is falsified if every delivered filtered context leaks the exact phrase
  or contains `_activity_log`.
- H318 is falsified if no row both recovers the exact phrase and uses the
  filtered intermediate.
- H319 is falsified if no first wake validates and requests continuation.
- H320 is falsified if the artifacts do not expose filtered context content and
  leakage status.

## Analysis Plan

Report:

- focused memory/executor test result;
- first-wake validity and continuation counts;
- filtered bound context delivery counts;
- exact-phrase leakage and `_activity_log` leakage in filtered context;
- final answer recovery and intermediate-use counts;
- repair provenance;
- comparison against full-record patched rerun.
