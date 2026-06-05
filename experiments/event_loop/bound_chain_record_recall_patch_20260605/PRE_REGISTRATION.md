# Pre-Registration: Bound Chain After In-Session Record-ID Recall Patch

Date: 2026-06-05

## Research Question

Does adding in-session `record_id` lookup to `recall(record_id=...)` make the
previously failing substrate-bound chain complete without changing the
model-facing prompt?

The bound-chain contract probe showed:

- first-wake continuation succeeded with durable update examples;
- the substrate appended bound second events;
- second events requested cycle-1 recall and bound first-wake `record_id`
  recall;
- bound record-ID recall failed because `record_id` mode required a bridge.

The substrate has now been changed so `record_id` recall first searches
in-session prior states, then falls back to bridge retrieval.

## Hypotheses

- H311: Bound record-ID recall resolves in at least one row after the patch.
- H312: At least one second wake recovers the exact phrase and incorporates the
  bound first-wake intermediate.
- H313: The patched behavior preserves the event-contract result: first wakes
  still validate and request continuation.
- H314: Unknown or cross-session record IDs still fall back to bridge/error
  behavior; unit tests cover this.
- H315: Provenance distinguishes the substrate patch, first wake, bound second
  event, bound record context, and second wake validation.

## Method

Run the same two-replicate live DeepSeek v4 Pro panel as
`bound_chain_contract_20260605`, in a new result directory, without changing
the model-facing event purposes, durable update contract, or durable update
example.

The only intended behavioral change is the substrate patch:

- `recall(record_id=...)` parses the UUID;
- checks session `prior_states` for a matching record ID;
- returns that in-session state if found;
- falls back to bridge retrieval only if not found.

Before live calls, run focused unit tests for memory/executor behavior.

## Predictions

If the record-ID recall gap was the limiting factor:

- bound record context will resolve in both rows or at least one row;
- second wakes will have access to cycle 1 and the first-wake record by ID;
- final recovery should match the fixed-cycle two-wake chain pattern.

If record-ID context resolves but final recovery still fails, then the next
limitation is second-wake integration, not addressing.

## Falsification Criteria

- H311 is falsified if no row has delivered bound record-ID context.
- H312 is falsified if no row both recovers the exact phrase and uses the bound
  intermediate.
- H313 is falsified if the first-wake contract regresses to no valid
  continuation requests.
- H314 is falsified if focused tests fail.
- H315 is falsified if artifacts do not expose the bound record ID and context
  result.

## Analysis Plan

Report:

- focused test result;
- first-wake validity and continuation counts;
- bound second event counts;
- bound record-ID context delivery counts;
- final recovery/intermediate use counts;
- first/second repair provenance;
- before/after comparison against `bound_chain_contract_20260605`.
