# Analysis: Second-Wake Filtered Integration Stability

Date: 2026-06-05

## Result

The second-wake-only panel supports the branch hypothesis: once the first wake
is made valid and the bound record is recalled through filtered field recall,
the substrate can deliver the necessary context reliably. The remaining
failures are no longer recall delivery failures.

Aggregate:

- rows: 6
- both requested contexts delivered: 6/6
- filtered bound-field context delivered: 6/6
- filtered context activity-log leaks: 0/6
- filtered context exact-phrase leaks: 0/6
- first-pass valid second wakes: 1/6
- repair attempted: 4/6
- repair valid: 2/4
- final valid: 3/6
- final answer recovered exact phrase: 5/6
- final evidence referenced `word-word-number`: 5/6
- bounded-call violations: 0/6
- runner-level errors: 0/6

Hypothesis outcomes:

- H331 passed: filtered context delivery was 6/6, above the preregistered 5/6
  threshold.
- H332 passed: stronger repair converted two invalid rows to valid.
- H333 passed: final validity was 3/6.
- H334 passed: valid rows recovered the exact phrase and referenced the
  filtered intermediate.
- H335 passed: failures separate context delivery from durable integration and
  protocol/JSON failure.

## Row Notes

| Row | Contexts | First pass | Repair | Final | Note |
| --- | --- | --- | --- | --- | --- |
| 1 | yes | invalid | invalid | invalid | recovered phrase and evidence, but also deleted `chain_intermediate` |
| 2 | yes | invalid | valid | valid | repair succeeded |
| 3 | yes | invalid | invalid | invalid | same delete/update conflict as row 1 |
| 4 | yes | valid | n/a | valid | clean first-pass success |
| 5 | yes | n/a | n/a | invalid | model/backend emitted malformed JSON tool arguments after context delivery |
| 6 | yes | invalid | valid | valid | repair succeeded |

Rows 1 and 3 are especially informative. Both produced the needed final answer
and evidence, but the validator rejected them because `deleted_regions`
included `chain_intermediate`. This is the same delete/update pattern observed
earlier with DeepSeek. It is not a failure to use the delivered information.
It is a durable-object protocol conflict.

Row 5 is also informative. The event log contains both context results, but no
state record was committed because the OpenAI-compatible backend rejected
malformed JSON arguments for `think_and_respond`. The scorer was corrected to
count context delivery from terminal failed events as well as completed events.

## Interpretation

This falsifies the idea that the current second-wake failures are primarily
caused by missing bound-record recall. The filtered recall substrate delivered
exactly the intended content in all six rows:

- cycle-1 recall carried the exact phrase;
- bound record-id field recall carried only `chain_intermediate`;
- filtered recall did not leak `_activity_log`;
- filtered recall did not leak the exact phrase.

The active boundary is now the durable update contract:

- some responses satisfy the substantive task while violating deletion/update
  invariants;
- one response never reaches validation because the tool-call JSON is malformed;
- repair is useful but not reliable enough to be treated as the final answer.

The result is therefore constructive rather than conclusive. The event-loop
substrate can preserve and deliver the needed material; the next design problem
is how strict the state object protocol should be, and whether protocol repair
belongs in model prompting, validator-side structured repair, or a narrower
completion surface.

## Next Branch

I would not widen model sweeps from this result. The next highest-value branch
is a protocol-level experiment:

- keep the same seeded second-wake setup;
- preserve filtered recall exactly as-is;
- change only the durable update surface so the model cannot both delete and
  update the same top-level key.

Two viable falsification designs:

1. A validator-side normalization rule that rejects or strips delete/update
   overlaps before final validation, while preserving an audit flag.
2. A narrower structured completion surface for second wakes that has no
   `deleted_regions` channel for protected fields.

The stronger test is the second design because it changes the affordance rather
than silently repairing the output. If it raises final validity while preserving
the same recall behavior, then the boundary is protocol ergonomics, not
identity-state recall.
