# Pre-Registration: First-Wake Continuation Stability

Date: 2026-06-05

## Research Question

Can the first wake reliably emit a valid substrate-bound continuation object
when the event includes a durable update contract/example and the repair prompt
includes the full non-secret expected object shape?

The filtered bound-record recall probe did not reach filtered recall because
both first wakes failed continuation validity. Prior panels showed 2/2, 1/2,
and 0/2 first-wake validity under similar contracts. This instability is now
the confound to attack directly.

## Hypotheses

- H321: A stronger non-secret repair prompt can convert at least one invalid
  first wake into a valid continuation state.
- H322: At least half of rows produce a valid first-wake continuation after
  first pass plus repair.
- H323: First-wake valid rows do not contain the exact phrase in model-owned
  durable state.
- H324: Failure labels identify whether misses are object-shape errors,
  delete/update conflicts, or baseline preservation errors.
- H325: The stability panel produces enough row-level data to decide whether
  filtered bound recall should be retried or whether a structured continuation
  tool is needed.

## Method

Run a live DeepSeek v4 Pro panel of six first-wake-only replicates.

Each replicate:

- seeds cycle 1 with an exact phrase and digest;
- seeds cycle 2 as a clean compressed state;
- appends one first pending event with durable update contract/example;
- runs only the first wake;
- does not append or execute a second event.

The event purpose remains the substrate-bound continuation first-wake purpose.
The repair prompt is strengthened by including the complete expected
non-secret durable object shape:

- `thinking_status: awaiting_bound_continuation`;
- `chain_stage: first_wake_complete`;
- `chain_intermediate` with all required fields;
- `continuation_request` as an object, not a string;
- preserved digest/loss/baseline fields;
- no `deferred_fact`;
- no exact phrase in durable state.

The panel may reuse generated code phrases across replicates only as hidden
seed facts. The outcome of interest is durable object compliance, not phrase
identity.

## Predictions

If prompt-level repair is sufficient:

- at least three of six rows should be valid after repair;
- failures should mostly be first-pass misses, not unrepaired durable object
  failures.

If validity remains low:

- substrate-bound continuation likely needs a structured continuation tool or
  validator-side object repair, not more prose prompting.

## Falsification Criteria

- H321 is falsified if no repair converts an invalid first wake to valid.
- H322 is falsified if fewer than three of six rows are valid after repair.
- H323 is falsified if every valid row leaks the exact phrase in model-owned
  durable state.
- H324 is falsified if failure labels cannot be extracted per row.
- H325 is falsified if the result does not clearly identify whether to retry
  filtered recall or move to structured continuation.

## Analysis Plan

Report:

- first-pass valid count;
- repair attempted count;
- repair valid count;
- final valid count;
- exact phrase leakage count excluding framework `_activity_log`;
- failure labels by row;
- delete/update conflict count;
- recommendation for the next branch.
