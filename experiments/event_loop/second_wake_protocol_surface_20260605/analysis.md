# Analysis: Second-Wake Protocol Surface

Date: 2026-06-05

## Result

The narrow second-wake terminal surface improved final validity while holding
recall delivery constant.

Aggregate:

- rows: 6
- both requested contexts delivered: 6/6
- filtered bound-field context delivered: 6/6
- filtered context activity-log leaks: 0/6
- filtered context exact-phrase leaks: 0/6
- narrow terminal tool parse/state-record success: 5/6
- final valid: 5/6
- final answer recovered exact phrase: 5/6
- final evidence referenced `word-word-number`: 5/6
- delete/update conflicts: 0/6
- bounded-call violations: 0/6
- runner-level errors: 0/6

Prior broad-surface baseline:

- both requested contexts delivered: 6/6
- final valid: 3/6
- delete/update conflicts: 2/6

Hypothesis outcomes:

- H341 passed: delete/update invalidity fell from 2/6 to 0/6.
- H342 passed: both requested contexts were delivered in 6/6 rows.
- H343 passed: phrase recovery plus intermediate use occurred in 5/6 rows.
- H344 passed: final validity improved from 3/6 to 5/6.
- H345 passed: failures separate context delivery from provider/tool-choice
  protocol failure and semantic integration.

## Row Notes

| Row | Contexts | Narrow Parse | Final | Note |
| --- | --- | --- | --- | --- |
| 1 | yes | yes | valid | clean completion |
| 2 | yes | yes | valid | clean completion |
| 3 | yes | no | invalid | provider rejected object `tool_choice` after upstream fallback |
| 4 | yes | yes | valid | clean completion |
| 5 | yes | yes | valid | clean completion |
| 6 | yes | yes | valid | clean completion |

Row 3 received both context results before failure. The event failed because
OpenRouter routed through providers that first returned upstream rate limits
and then an Alibaba error rejecting object `tool_choice` in thinking mode. This
is a connector/provider compatibility failure, not a model-state integration
failure.

## Interpretation

This is the clearest evidence so far that the active boundary is protocol
ergonomics rather than recall delivery.

Filtered recall remained stable:

- cycle-1 recall delivered the exact phrase;
- bound record-id field recall delivered only `chain_intermediate`;
- filtered recall did not leak `_activity_log`;
- filtered recall did not leak the exact phrase.

Changing only the terminal durable update surface removed the observed
delete/update conflict class. The model still performed the substantive task:
it recovered the exact phrase from cycle-1 recall and used the filtered
`word-word-number` intermediate. The runner then deterministically constructed
the durable state update, preserving continuity fields without giving the model
a deletion channel for them.

The result does not prove the narrow surface is the final design. It does show
that broad open-state updates can manufacture avoidable invalidity even when
the model has completed the actual cognitive task. That matters for the event
loop scheduler: the event substrate should not force every wake to manipulate
the whole identity object when the intended operation is narrower.

## Design Implication

The event loop should support task-specific completion surfaces:

- broad `think_and_respond` remains appropriate for open identity evolution;
- narrow completion tools are appropriate for bounded scheduled tasks;
- the substrate can translate narrow task completions into durable state
  updates with explicit audit metadata;
- validation should evaluate the translated durable state and preserve the raw
  narrow completion for observability.

This fits the emerging architecture: identity object as active self-model,
event substrate as scheduler, and task-specific tools as safer affordances for
bounded wake work.

## Next Branch

The row 3 provider failure exposes a separate interoperability question. The
runner used object `tool_choice` to force `complete_second_wake`; one provider
rejected that form in thinking mode. A small follow-up should compare object
tool choice against `auto` for the same narrow terminal surface.

If `auto` preserves the 5/6 or better validity rate while reducing provider
failures, the implementation recommendation is straightforward: narrow
terminal surfaces should not require object `tool_choice` on OpenRouter unless
the selected provider is known to support it.
