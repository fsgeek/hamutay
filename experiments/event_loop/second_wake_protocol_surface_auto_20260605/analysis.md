# Analysis: Second-Wake Protocol Surface Auto Tool Choice

Date: 2026-06-05

## Result

Using `tool_choice: auto` with the same narrow second-wake terminal surface
produced a clean panel.

Aggregate:

- rows: 6
- both requested contexts delivered: 6/6
- filtered bound-field context delivered: 6/6
- filtered context activity-log leaks: 0/6
- filtered context exact-phrase leaks: 0/6
- narrow terminal parse/state-record success: 6/6
- final valid: 6/6
- final answer recovered exact phrase: 6/6
- final evidence referenced `word-word-number`: 6/6
- provider/tool-choice failures: 0/6
- terminal-tool-missing failures: 0/6
- delete/update conflicts: 0/6
- bounded-call violations: 0/6

Object-forced narrow-surface baseline:

- final valid: 5/6
- provider/tool-choice failures: 1/6
- delete/update conflicts: 0/6
- both requested contexts delivered: 6/6

Hypothesis outcomes:

- H351 passed: provider/tool-choice failures fell from 1/6 to 0/6.
- H352 passed: both contexts were delivered in 6/6 rows.
- H353 passed: final validity was 6/6.
- H354 passed: delete/update conflicts remained 0/6.
- H355 passed: there were no terminal-tool-missing failures to classify.

## Interpretation

This follow-up removes the main confound from the object-forced narrow-surface
panel. The previous invalid row was not evidence against the narrow terminal
surface; it was an OpenRouter provider-routing/tool-choice compatibility
failure.

With `tool_choice: auto`, DeepSeek still called the narrow terminal tool in all
six rows. That matters because it gives the implementation a less brittle
provider posture:

- avoid object-forced tool choice unless a provider is known to support it;
- keep the narrow completion schema;
- validate the translated durable state;
- preserve the raw completion and event context for audit.

The result strengthens the earlier design implication: for bounded scheduled
wakes, a task-specific completion surface is superior to exposing the whole
open identity-object update surface.

## Design Implication

The event loop should distinguish two classes of state work:

- open identity evolution, where broad `think_and_respond` remains appropriate;
- bounded scheduled task completion, where a narrow task-specific terminal tool
  should be preferred.

For OpenAI-compatible/OpenRouter providers, the default narrow-surface request
should use `tool_choice: auto` unless provider capability metadata indicates
that forced object/function tool choice is supported. The event substrate can
then translate successful narrow completions into durable state updates with
explicit `protocol_surface` metadata.

## What We Learned

The sequence of experiments now supports a concrete map:

1. Filtered bound record recall can deliver only the intended field without
   activity-log or phrase leakage.
2. Second-wake failures persisted under the broad durable update surface even
   when the substantive task was performed.
3. A narrow terminal surface removed delete/update conflicts and improved
   validity.
4. `tool_choice: auto` removed the remaining provider/tool-choice failure while
   preserving the narrow-surface benefit.

This gives enough evidence to move from exploratory probing into a small
production substrate change: add first-class support for task-specific terminal
completion surfaces in the scheduler.
