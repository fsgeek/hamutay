# Pre-Registration: Bound Chain With Durable Update Contract

Date: 2026-06-05

## Research Question

Do event-level `durable_update_contract` and `durable_update_example` fields
make substrate-bound continuation reliable enough to reach the bound
`record_id` recall boundary?

The previous substrate-bound chain probe failed before record-ID recall. Both
first wakes completed, and repair prose described the required updates, but the
durable state did not contain `chain_intermediate` or `continuation_request`.
The event API already supports durable update contracts/examples, so this
experiment tests that intervention directly.

## Hypotheses

- H306: A first event with a durable update contract/example produces at least
  one valid first wake with `continuation_request`.
- H307: The substrate appends at least one second event bound to the first
  wake's `result_record_id`.
- H308: The second wake receives cycle-1 recall and bound first-wake
  `record_id` recall.
- H309: If bound record-ID recall resolves, the second wake recovers the exact
  phrase and incorporates the first-wake intermediate.
- H310: If bound record-ID recall fails, the artifact records the failure
  explicitly enough to distinguish addressing failure from model failure.

## Method

Run two live DeepSeek v4 Pro replicates for condition
`bound_chain_contract`.

The setup matches the substrate-bound chain probe:

- cycle 1 contains the exact phrase and digest;
- cycle 2 is a clean compressed state;
- the runner appends the first pending event directly.

Unlike the prior probe, the first event includes:

- `durable_update_contract` naming required top-level fields and exact values;
- `durable_update_example` showing the complete non-secret durable object shape.

The example does not include the exact phrase.

First wake requirements:

- valid durable `chain_intermediate`;
- valid durable `continuation_request`;
- no exact phrase in durable state;
- no model-scheduled event.

If valid, the runner appends a second event bound to the first wake
`result_record_id` with requested context:

- `{"tool": "recall", "cycle": 1}`;
- `{"tool": "recall", "record_id": "<first_wake_result_record_id>"}`.

Second wake requirements:

- receive both requested context entries;
- set `bound_record_id_used` to the bound record ID;
- recover the exact phrase;
- reference the first-wake phrase shape `word-word-number`.

## Predictions

If the previous failure was mainly lack of object-shape example:

- first-wake validity should improve over 0/2;
- continuation requests should appear in durable state;
- the experiment should reach second-wake execution.

If record-ID recall is unavailable in JSONL-only sessions:

- second event requested context will include the bound `record_id`;
- the bound `record_id` context result will contain an explicit error;
- final recovery, if it happens, must be interpreted as coming from cycle-1
  recall plus ordinary prior-state continuity, not from bound record recall.

## Falsification Criteria

- H306 is falsified if no first wake is valid with continuation request.
- H307 is falsified if no bound second event is appended.
- H308 is falsified if no second wake receives both requested context entries.
- H309 is falsified if bound record-ID recall resolves but no final answer
  both recovers and uses the intermediate.
- H310 is falsified if record-ID recall fails but the artifact does not expose
  the error clearly.

## Analysis Plan

Report:

- first wake valid/invalid counts;
- continuation-request counts;
- model-scheduled event counts;
- bound second event counts;
- record-ID requested-context presence and delivery status;
- explicit record-ID recall errors;
- final recovery/intermediate use;
- repair provenance for both wakes.

Interpretation will distinguish event-contract effectiveness from record-ID
addressing availability.
