# Pre-Registration: Substrate-Bound Chain Probe

Date: 2026-06-05

## Research Question

Can the event-loop scaffold support a chained wake without requiring the model
to guess the cycle number or record ID of the state it is about to produce?

The two-wake chain probe succeeded, but it relied on deterministic cycle
addressing: the first wake scheduled the second event with `recall(cycle=3)`.
That is artificial. In a general event loop, an instance should be able to ask
for continuation and let the substrate bind the continuation event to the
record ID created by the current wake.

## Hypotheses

- H301: A first wake can produce a valid non-secret intermediate and request
  continuation without scheduling the second event itself.
- H302: The substrate can bind a second event to the first wake's completed
  `result_record_id`.
- H303: The second wake receives recall context for cycle 1 and the bound first
  wake record ID.
- H304: The second wake recovers the exact phrase and incorporates the bound
  first-wake intermediate.
- H305: Provenance distinguishes seeded first event, substrate-bound second
  event, first wake validation, second wake validation, and bound record ID.

## Method

Run two live DeepSeek v4 Pro replicates for condition
`substrate_bound_chain`.

As in the two-wake chain probe, the runner seeds:

- cycle 1 with the exact phrase and digest;
- cycle 2 as a clean compressed state with only digest/loss fields;
- one first pending event that recalls cycle 1.

First wake requirements:

- receive recall context for cycle 1;
- set `thinking_status` to `awaiting_bound_continuation`;
- set `chain_stage` to `first_wake_complete`;
- add non-secret `chain_intermediate` with phrase shape
  `word-word-number`;
- set `continuation_request` with:
  - `requested: true`;
  - `kind: "substrate_bound_second_wake"`;
  - `needs_original_cycle: 1`;
  - `needs_current_wake_record: true`;
- not schedule an event itself;
- not include the exact phrase in durable state.

If the first wake is valid and requests continuation, the runner reads the
completed first event's `result_record_id` and appends a second pending event
with requested context:

- `{"tool": "recall", "cycle": 1}`;
- `{"tool": "recall", "record_id": "<first_wake_result_record_id>"}`.

Second wake requirements:

- receive both context entries;
- set `thinking_status` to `bound_chain_completed`;
- set `chain_stage` to `second_wake_complete`;
- add `bound_record_id_used` equal to the first wake result record ID;
- add `chain_final_answer` containing the exact phrase;
- add `chain_final_evidence` referencing phrase shape `word-word-number`;
- preserve the baseline observation.

Both wakes use validators. Repair prompts must not reveal the exact phrase.

## Predictions

If substrate-bound continuation is sufficient:

- at least one replicate will complete both wakes;
- the first wake will not schedule a second event itself;
- the runner-bound second event will use record-ID recall for the first wake;
- the second wake will recover the phrase and use the first-wake intermediate.

If this fails, failure location matters:

- first wake invalid: state-object compliance remains the limiting factor;
- continuation request missing: the model does not express the continuation
  contract reliably;
- bound record recall fails: record-ID addressing is weak;
- second answer fails: multi-context integration remains the limiting factor.

## Falsification Criteria

- H301 is falsified if no first wake both validates and requests continuation.
- H302 is falsified if no substrate-bound second event is appended with the
  first wake result record ID.
- H303 is falsified if no second wake receives both cycle-1 recall and first
  wake record-ID recall.
- H304 is falsified if no second wake recovers the exact phrase and references
  the first-wake intermediate.
- H305 is falsified if result artifacts cannot distinguish first event,
  substrate-bound second event, validations, and bound record ID.

## Analysis Plan

Report:

- first wake validation and continuation-request counts;
- accidental model-scheduled event counts;
- bound second-event append counts;
- record-ID context delivery counts;
- final recovery and intermediate incorporation counts;
- first/second repair provenance;
- event log summaries.

Interpretation will focus on whether the scheduler can bind continuation to a
newly created wake result.
