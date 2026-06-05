# Pre-Registration: Budgeted Three-Wake Chain

Date: 2026-06-05

## Research Question

Can a deliberate longer continuation chain be split across scheduler steps by
`max_auto_continuations=1` while preserving generated-record recall and final
validity?

The budget policy smoke proved the scheduler can stop after one
auto-continuation append in unit fixtures. This live panel tests whether a
three-wake chain remains usable under that policy.

## Hypotheses

- H461: Step 1 runs the first wake, appends the bridge wake, and stops for
  `auto_continuation_limit_reached`.
- H462: Step 2 runs the bridge wake, appends the final wake, and stops for
  `auto_continuation_limit_reached`.
- H463: Step 3 runs the final wake, recovers the exact phrase, and then
  quiesces without appending another continuation.
- H464: Generated-record context is delivered at both bridge and final wakes.
- H465: All three wakes are first-pass strict-valid with no broad repair.

## Predictions

For `N=2` replicates using `deepseek/deepseek-v4-pro`:

- first wake valid: 2/2;
- bridge wake valid: 2/2;
- final wake valid: 2/2;
- step 1 stop reason: `auto_continuation_limit_reached` in both rows;
- step 2 stop reason: `auto_continuation_limit_reached` in both rows;
- step 3 stop reason: `idle` or `waiting`, not `limit_reached`;
- each of steps 1 and 2 runs exactly one wake and appends one continuation;
- step 3 runs exactly one wake and appends zero continuations;
- final answer contains the exact code phrase;
- final evidence references the bridge context and `word-word-number`.

## Falsification Criteria

The policy is not supported if:

- the budgeted steps run past one auto-continuation append;
- the chain loses generated-record recall across step boundaries;
- the final wake cannot recover the phrase;
- inherited continuation requests retrigger after the final wake;
- any wake requires broad repair.

## Method

Use terminal surfaces for all three wakes:

1. first wake recalls cycle 1 and writes non-secret `chain_intermediate`;
2. first terminal surface emits a continuation request for the bridge wake;
3. bridge wake recalls cycle 1 and first-wake `chain_intermediate`, then writes
   `chain_bridge`;
4. bridge terminal surface emits a continuation request for the final wake;
5. final wake recalls cycle 1 and bridge `chain_bridge`, then writes
   `chain_final_answer` and `chain_final_evidence`.

Each scheduler step uses:

```python
step_pending_events(..., auto_continuations=True, max_auto_continuations=1)
```

No manual bridge/final event append is allowed.

## Analysis Plan

Classify failures by stage: first wake, first budget stop, bridge wake, second
budget stop, final wake, quiescence. Preserve row-level step summaries and
event logs.
