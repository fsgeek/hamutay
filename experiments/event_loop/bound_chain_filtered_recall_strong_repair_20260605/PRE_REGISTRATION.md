# Pre-Registration: Filtered Bound Recall With Strong First-Wake Repair

Date: 2026-06-05

## Research Question

If first-wake continuation is stabilized with the stronger non-secret repair
prompt, can filtered bound-record recall deliver `chain_intermediate` without
`_activity_log` or exact-phrase leakage and still support final recovery?

The prior filtered bound-record recall probe failed before filtered context
delivery because both first wakes produced invalid continuation states. The
first-wake continuation stability panel then showed that a stronger
object-shaped repair prompt produced 6/6 valid first-wake continuation states.
This experiment combines those two findings.

## Hypotheses

- H326: Strong first-wake repair yields at least one valid continuation row in
  the full filtered chain.
- H327: Filtered bound context
  `recall(record_id=<first_wake_record>, field="chain_intermediate")` resolves
  in at least one row.
- H328: Delivered filtered bound context contains neither the exact phrase nor
  `_activity_log`.
- H329: At least one final second wake recovers the exact phrase from cycle-1
  recall and incorporates the filtered intermediate.
- H330: Artifacts expose first-wake repair, filtered context delivery, leakage
  status, and second-wake validation provenance.

## Method

Run two live DeepSeek v4 Pro replicates.

Use the same setup as `bound_chain_filtered_recall_20260605`:

- seeded cycle 1 with exact phrase and digest;
- seeded clean cycle 2;
- first pending event with durable update contract/example;
- second event bound to first wake `result_record_id`;
- second event requested context:
  - `recall(cycle=1)`;
  - `recall(record_id=<first_wake_result_record_id>, field="chain_intermediate")`.

Change only the first-wake repair builder:

- use the stronger repair prompt from
  `first_wake_continuation_stability_20260605`;
- include the full expected non-secret durable object shape in repair.

Do not change the second-wake prompt or validator.

## Predictions

If the previous filtered failure was first-wake repair instability:

- at least one row should reach filtered context delivery;
- filtered context should contain only the `chain_intermediate` object;
- no filtered context should contain `_activity_log`;
- no filtered context should contain the exact phrase.

If filtered context delivers but final recovery fails, the next limit is
second-wake integration of field-only bound context.

## Falsification Criteria

- H326 is falsified if no first wake validates and requests continuation.
- H327 is falsified if no row receives filtered bound context.
- H328 is falsified if every delivered filtered context leaks the exact phrase
  or includes `_activity_log`.
- H329 is falsified if no row both recovers the exact phrase and uses the
  filtered intermediate.
- H330 is falsified if results do not expose the provenance fields needed to
  distinguish these outcomes.

## Analysis Plan

Report:

- first-wake valid count and repair provenance;
- bound second event count;
- filtered context delivery count;
- filtered context leakage counts;
- final answer recovery and intermediate use;
- second-wake repair provenance;
- comparison against the failed filtered run and the first-wake stability panel.
