# Pre-Registration: Second-Wake Protocol Surface Auto Tool Choice

Date: 2026-06-05

## Research Question

Does the narrow second-wake terminal surface remain effective when the
OpenAI-compatible request uses `tool_choice: auto` instead of an object-forced
function choice?

The prior narrow-surface panel improved final validity from 3/6 to 5/6 and
eliminated delete/update conflicts. Its sole invalid row received both
contexts, but failed because one fallback provider rejected object
`tool_choice` in thinking mode.

## Hypotheses

- H351: `tool_choice: auto` reduces provider/tool-choice failures compared
  with the object-forced narrow-surface panel.
- H352: The narrow surface still receives both requested contexts in at least
  five of six rows.
- H353: The narrow surface still produces valid final state in at least five of
  six rows.
- H354: Delete/update conflict failures remain zero because the terminal tool
  still has no `deleted_regions` channel.
- H355: If `auto` causes models not to call the narrow terminal tool, this
  failure is visible as a terminal-tool-missing failure rather than being
  conflated with semantic integration.

## Method

Run six live DeepSeek v4 Pro second-wake-only replicates with the same seeded
history and requested context as the prior two panels:

- `recall(cycle=1)`;
- `recall(record_id=<cycle_3_record_id>, field="chain_intermediate")`.

The terminal surface remains `complete_second_wake` with only:

- `response`;
- `chain_final_answer`;
- `chain_final_evidence`.

The only intervention is request routing:

- prior narrow-surface panel: object-forced `tool_choice`;
- this panel: `tool_choice: auto`.

The runner still translates successful narrow completions into the durable
state update and validates the resulting state with the same second-wake
validator.

## Predictions

If the prior miss was provider-routing friction, `auto` should preserve the
5/6 or better validity rate while reducing provider/tool-choice failure.

If `auto` lets the model skip the terminal tool, validity may fall despite no
delete/update conflicts. That would mean narrow surfaces should use provider-
specific tool forcing only when supported, and require a fallback strategy
otherwise.

## Falsification Criteria

- H351 is falsified if provider/tool-choice failures are not reduced.
- H352 is falsified if fewer than five rows receive both contexts.
- H353 is falsified if fewer than five rows end final-valid.
- H354 is falsified if any row fails from delete/update conflict.
- H355 is falsified if terminal-tool-missing failures cannot be distinguished
  from semantic integration failures.

## Analysis Plan

Report:

- context delivery count;
- terminal tool parse/success count;
- final valid count;
- phrase recovery and intermediate-use counts;
- provider/tool-choice failure count;
- terminal-tool-missing count;
- delete/update conflict count;
- comparison to the object-forced narrow-surface panel.
