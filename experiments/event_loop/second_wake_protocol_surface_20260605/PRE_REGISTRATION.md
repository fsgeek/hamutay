# Pre-Registration: Second-Wake Protocol Surface

Date: 2026-06-05

## Research Question

When second-wake recall delivery is held constant, do second-wake failures come
from the broad `think_and_respond` durable state surface rather than from the
model's ability to integrate recalled context?

The prior second-wake filtered integration panel delivered both required
contexts in 6/6 rows. Five rows recovered the exact phrase and referenced the
filtered intermediate, but only 3/6 were final-valid. Two invalid rows satisfied
the substantive task while also listing `chain_intermediate` in
`deleted_regions`. One row failed after context delivery because the
OpenAI-compatible backend rejected malformed JSON tool arguments.

## Hypotheses

- H341: A narrow second-wake completion surface will reduce final invalidity
  caused by delete/update overlap compared with the broad state surface.
- H342: The narrow surface will preserve context delivery reliability: both
  requested contexts delivered in at least five of six rows.
- H343: The narrow surface will preserve substantive task performance:
  final answer recovers the exact phrase and final evidence references
  `word-word-number` in at least five of six rows.
- H344: The narrow surface will improve final-valid rows over the prior broad
  baseline of 3/6.
- H345: If failures remain, row labels distinguish context delivery, tool-call
  parse/protocol failure, and semantic integration failure.

## Method

Run six live DeepSeek v4 Pro second-wake-only replicates using the same seeded
history as `second_wake_filtered_integration_20260605`:

- cycle 1: exact phrase and digest;
- cycle 2: clean compressed state;
- cycle 3: valid first-wake continuation state with `chain_intermediate` and no
  exact phrase in visible durable state.

The event requests the same context:

- `recall(cycle=1)`;
- `recall(record_id=<cycle_3_record_id>, field="chain_intermediate")`.

The intervention is the second-wake terminal surface. Instead of asking the
model to directly update the full durable state via broad `think_and_respond`,
the runner exposes a narrow terminal completion shape:

- `response`;
- `chain_final_answer`;
- `chain_final_evidence`.

The runner then constructs the durable update deterministically:

- preserve prior state;
- set `thinking_status: bound_chain_completed`;
- set `chain_stage: second_wake_complete`;
- set `bound_record_id_used`;
- set `chain_final_answer`;
- set `chain_final_evidence`;
- preserve baseline observation;
- no `deleted_regions` channel is available for protected continuity fields.

The narrow surface is a runner-local experimental bridge, not a production
harness change.

## Predictions

If the active boundary is protocol ergonomics, the narrow surface should:

- keep filtered recall delivery at or near 6/6;
- eliminate delete/update conflict failures;
- improve final validity above the previous 3/6 baseline;
- leave any remaining failures mostly in tool-call parsing or semantic
  integration categories.

If final validity does not improve despite no deletion channel, then the
delete/update conflict was incidental and the boundary remains elsewhere.

## Falsification Criteria

- H341 is falsified if any invalid row is still caused by delete/update overlap
  or if invalidity does not shift away from that class.
- H342 is falsified if fewer than five rows receive both contexts.
- H343 is falsified if fewer than five rows recover the exact phrase and
  reference `word-word-number`.
- H344 is falsified if final validity is not greater than 3/6.
- H345 is falsified if failure labels cannot separate context delivery,
  tool-call parse/protocol, and semantic integration failures.

## Analysis Plan

Report:

- context delivery count;
- narrow tool-call parse success count;
- final valid count;
- phrase recovery count;
- intermediate-use count;
- delete/update conflict count;
- failure labels by row;
- visible and activity-log phrase leakage counts;
- comparison to the immediately prior broad-surface baseline.
