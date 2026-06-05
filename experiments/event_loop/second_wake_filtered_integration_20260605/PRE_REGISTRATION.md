# Pre-Registration: Second-Wake Filtered Integration Stability

Date: 2026-06-05

## Research Question

Can the second wake reliably integrate cycle-1 recall and filtered bound
`chain_intermediate` recall into a valid final durable object when the first
wake is already valid?

The filtered bound-record recall strong-repair probe showed:

- first wake valid: 2/2;
- filtered bound context delivered: 2/2;
- filtered context phrase/activity-log leakage: 0/2;
- final second wake valid: 1/2.

The remaining failure was second-wake integration/repair, not bound context
delivery.

## Hypotheses

- H331: With valid seeded first-wake records, filtered bound context delivery
  succeeds in at least five of six rows.
- H332: A stronger non-secret second-wake repair prompt converts at least one
  invalid second wake into a valid final state.
- H333: At least half of rows end with valid final second-wake state.
- H334: Valid rows recover the exact phrase from cycle-1 recall and reference
  the filtered `word-word-number` intermediate.
- H335: Failure labels distinguish context delivery failures from durable
  object integration failures.

## Method

Run six live DeepSeek v4 Pro second-wake-only replicates.

Each replicate seeds session history with:

- cycle 1: exact phrase and digest;
- cycle 2: clean compressed state;
- cycle 3: valid first-wake continuation state with:
  - `chain_intermediate`;
  - `continuation_request`;
  - no exact phrase in visible durable state.

The runner appends only the second pending event, bound to the seeded cycle-3
record ID. Requested context:

- `recall(cycle=1)`;
- `recall(record_id=<cycle_3_record_id>, field="chain_intermediate")`.

The second wake validator requires:

- `thinking_status: bound_chain_completed`;
- `chain_stage: second_wake_complete`;
- `bound_record_id_used` equal to the bound record ID;
- `chain_final_answer` containing the exact phrase;
- `chain_final_evidence` referencing `word-word-number`;
- baseline observation preserved.

Repair prompt:

- does not reveal the exact phrase;
- includes full non-secret expected durable object shape;
- tells the model to take the exact phrase from delivered cycle-1 context;
- tells the model to take phrase shape from delivered filtered bound context.

## Predictions

If second-wake integration is prompt-repairable:

- most context delivery should succeed;
- at least three of six rows should be final-valid;
- failed rows should show durable object misses rather than context failures.

If validity remains low despite delivered contexts, the next branch should
consider a structured completion tool or validator-side object repair.

## Falsification Criteria

- H331 is falsified if fewer than five rows receive both contexts.
- H332 is falsified if no invalid second wake is repaired to valid.
- H333 is falsified if fewer than three rows end final-valid.
- H334 is falsified if no valid row both recovers the phrase and references the
  filtered intermediate.
- H335 is falsified if failure labels cannot distinguish context delivery from
  state integration failures.

## Analysis Plan

Report:

- context delivery count;
- first-pass valid count;
- repair attempted and repair valid counts;
- final valid count;
- phrase recovery and intermediate-use counts;
- failure labels by row;
- visible and activity-log phrase leakage counts.
