# Substrate-Bound Chain Analysis

Date: 2026-06-05

## Result

The substrate-bound chain did not reach the record-ID recall test. Both first
wakes completed, but neither produced a valid continuation request in durable
state, so the runner did not append a bound second event.

| Rows | First wake complete | First wake valid | Continuation requested | Bound second event | Second wake complete | Bound record context delivered | Final recovered |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |

Hypothesis status from `results.json`:

- H301 first wake valid and requests continuation: falsified.
- H302 substrate binds second event: falsified because no valid continuation
  request existed.
- H303 second wake receives bound record context: falsified because no second
  wake ran.
- H304 second wake recovers using bound intermediate: falsified because no
  second wake ran.
- H305 provenance distinguishable: supported.

## Failure Pattern

Both first wakes completed and both attempted repair, but final durable state
remained invalid.

Shared first-wake failures:

- `thinking_status_not_awaiting_bound_continuation`;
- `chain_stage_not_first_wake_complete`;
- `chain_intermediate_missing`;
- `continuation_request_missing`.

The notable pattern is response/state divergence. In both replicates, the
repair response text described the required updates, including
`thinking_status`, `chain_stage`, `chain_intermediate`, and
`continuation_request`, but the durable object did not contain those updates.

Replicate 1 even named the created wake record ID in prose, but left durable
state at:

- `thinking_status: chain_scheduled`;
- `chain_stage: compressed_waiting_first_wake`;
- no `chain_intermediate`;
- no `continuation_request`.

Replicate 2 similarly described a repaired durable shape in prose, but durable
state still lacked the required fields.

No accidental model-scheduled second events occurred.

## Interpretation

This is a negative result, but not for the originally suspected record-ID recall
boundary. The experiment failed earlier at first-wake durable state-object
compliance.

That is useful because it distinguishes two possible substrate problems:

1. record-ID recall may be unavailable in JSONL-only sessions; and
2. before testing that, the event wake needs to reliably commit continuation
   fields to durable state.

The panel only supports the second point. It does not yet test the first point.

The result is consistent with the earlier identity-object confound: the model
often describes the required durable update instead of emitting it as fields.
The two-wake chain succeeded partly because its first-wake contract was simple
and familiar. The substrate-bound contract added a novel
`continuation_request` object and the model failed to write it durably.

## Method Note

The event API already supports `durable_update_contract` and
`durable_update_example` fields on scheduled events. This experiment did not
use them. That omission is now informative: a prose-only event purpose was not
enough for this continuation contract.

## Next Research Question

The next useful slice is not to retry the same prompt. It should test whether
event-level durable update examples fix the first-wake state-object failure.

Concrete next experiment:

- append the first event with `durable_update_contract` and
  `durable_update_example` showing the exact required first-wake object shape;
- keep the exact phrase out of the example;
- require `continuation_request`;
- if valid, bind the second event to the first wake `result_record_id`;
- then observe whether record-ID recall resolves or fails.

This would separate "the model needs an object example" from "record-ID recall
is unavailable without a bridge."
