# First-Wake Continuation Stability Analysis

Date: 2026-06-05

## Result

The stronger first-wake repair prompt stabilized the continuation object in
this panel.

| Rows | First-pass valid | Repair attempted | Repair valid | Final valid | Visible phrase leaks | Activity-log phrase leaks |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 3 | 3 | 3 | 6 | 0 | 4 |

Hypothesis status from `results.json`:

- H321 repair converts at least one invalid first wake: supported.
- H322 at least half valid after repair: supported.
- H323 valid rows have no visible phrase leak: supported.
- H324 failure labels extracted: supported by raw JSONL validation artifacts.
- H325 next branch decidable: supported.

## First-Pass and Repair

Three rows were valid on first pass. Three rows failed first pass and were
repaired successfully.

The three first-pass failures had the same labels:

- `thinking_status_not_awaiting_bound_continuation`;
- `chain_stage_not_first_wake_complete`;
- `chain_intermediate_missing`;
- `continuation_request_missing`.

The strengthened repair prompt converted all three to valid durable states.

Every final first-wake state had:

- `thinking_status: awaiting_bound_continuation`;
- `chain_stage: first_wake_complete`;
- `chain_intermediate.source_cycle: 1`;
- `chain_intermediate.phrase_shape: word-word-number`;
- `chain_intermediate.part_count: 3`;
- `chain_intermediate.exact_phrase_retained: false`;
- a structured `continuation_request` object.

## Leakage

No valid row leaked the exact phrase in model-owned visible durable state.

Four rows had exact-phrase content in `_activity_log`, usually from model-called
verification commands. This remains a substrate/observability concern for
full-record recall, but it should not affect a filtered
`record_id + field="chain_intermediate"` recall path.

## Scoring Note

The top-level `failure_labels` summary in `results.json` is empty because it
counts final validation failures, and all rows were final-valid. The raw JSONL
`state_validation.first_pass.artifact.failures` fields contain the first-pass
failure labels listed above. Future runners should promote first-pass failure
labels into top-level result rows.

## Interpretation

This panel supports retrying filtered bound-record recall. The previous filtered
probe failed because first-wake continuation was unstable. The stronger repair
prompt made continuation stable enough for the next test:

- six of six final first-wake states valid;
- three of six repaired from the exact failure class seen previously;
- zero visible durable phrase leakage.

The remaining issue is not first-wake object repair in this scaffold; it is
whether filtered bound-record recall can deliver only the non-secret
intermediate and avoid `_activity_log` exposure during the second wake.

## Next Research Question

Retry the filtered bound-record recall chain using the stronger first-wake
repair prompt from this panel.

Expected discriminators:

- if bound `field="chain_intermediate"` context delivers and final recovery
  succeeds, filtered bound continuation is viable;
- if filtered context delivers but final recovery fails, the limit is
  second-wake integration of field-only context;
- if filtered context does not deliver, the limit is record-ID field recall;
- if activity-log leakage still appears in filtered context, the field filter is
  not strong enough.
