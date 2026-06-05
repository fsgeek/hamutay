# Bound Chain With Filtered Record Recall Analysis

Date: 2026-06-05

## Result

The filtered bound-record recall panel did not reach the filtered context
delivery point. Both first wakes completed, but neither produced a valid
continuation request, so no bound second event was appended.

| Rows | First wake complete | First wake valid | Continuation requested | Bound second event | Filtered context delivered | Final recovered |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2 | 0 | 0 | 0 | 0 | 0 |

Hypothesis status from `results.json`:

- H316 filtered bound context resolves: not supported; no bound second event
  ran.
- H317 filtered context has no phrase/activity-log leakage: not supported; no
  filtered context was delivered.
- H318 final recovers and uses filtered intermediate: not supported.
- H319 first-wake contract non-regressed: falsified in this panel.
- H320 filtered context provenance visible: supported.

## Failure Pattern

The run failed before testing filtered recall.

Replicate 1:

- reached first wake;
- repair produced `thinking_status: awaiting_bound_continuation`;
- repair produced `chain_stage: first_wake_complete`;
- `chain_intermediate` was present but incomplete:
  - missing `source_cycle`;
  - missing `part_count`;
  - missing `exact_phrase_retained`;
- `continuation_request` was a string rather than the required object;
- no second event was appended.

Replicate 2:

- reached first wake;
- repair response described the intended corrections in prose;
- durable state did not contain the required fields;
- baseline observation was deleted;
- no second event was appended.

Both rows therefore repeated the broader state-object compliance problem rather
than exercising the filtered record-ID recall path.

## Interpretation

This panel does not answer whether filtered bound-record recall avoids
`_activity_log` leakage. It instead shows that first-wake continuation remains
stochastic and brittle even with durable update contract/example support.

The previous bound-chain contract run had 2/2 valid first wakes. The patched
record-ID rerun had 1/2. This filtered run had 0/2. That instability is now
itself a map point: before treating substrate-bound continuation as a reliable
event-loop phase, the first-wake continuation object needs a stronger gate or
repair mechanism.

The failure is specific:

- the model can often understand the requested fields;
- it may describe them correctly in prose;
- it may emit a partial object;
- but it does not reliably emit the exact durable object shape.

## Next Research Question

The next useful question is not filtered recall yet. It is first-wake
continuation stability.

A suitable next experiment would isolate the first wake only:

- no second event execution;
- same seeded cycle-1/cycle-2 setup;
- first event with durable update contract/example;
- stronger first-wake repair prompt that includes the full non-secret expected
  object shape;
- larger small panel, for example 6 replicates;
- score first-pass valid, repair valid, and exact failure labels.

If that produces stable valid first wakes, filtered recall can be retried. If
not, substrate-bound continuation likely needs a structured continuation tool
or validator-side object repair rather than prompt repair.
