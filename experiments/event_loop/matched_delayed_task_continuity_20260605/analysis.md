# Analysis: Matched Delayed Task Continuity

Date: 2026-06-05

## Result

The matched delayed-task probe did not show an event-plus-recall advantage for
content recovery. It did show an event-plus-recall advantage for strict durable
state validity.

- H271 event-plus-recall recovers the deferred fact: supported.
- H272 identity-only recovery requires preservation: supported.
- H273 event-plus-recall has higher fact recovery: falsified.
- H274 first-pass/repair/final-state provenance present: supported.
- H275 identity match is diagnosable as task-too-easy: supported.

## Counts

Two replicates were run per condition.

`event_plus_recall`:

- recall context delivered: 2/2;
- fact recovered in `delayed_answer`: 2/2;
- final durable state valid: 2/2;
- first-pass valid: 0/2;
- repaired: 2/2;
- bounded wake call violations: 0.

`identity_only`:

- recall context delivered: 0/2;
- fact recovered in `delayed_answer`: 2/2;
- final durable state valid: 1/2;
- first-pass valid: 0/2;
- repaired: 1/2;
- bounded wake call violations: 0.

## Key Finding

Identity-only recovered the code phrase in both replicates because the model
preserved the deferred fact in durable state before the due turn:

- identity-only r1 preserved the fact and put it in `delayed_answer` as an
  object; content was recovered, but strict validation failed because the
  validator required `delayed_answer` to be a string.
- identity-only r2 preserved the fact and produced strict-valid durable state
  after repair.

This means the task did not force a meaningful recall distinction. The model
used the identity object as the memory carrier successfully enough for content
recovery.

## Event-Plus-Recall Behavior

Both event-plus-recall replicates received recall context and recovered the
deferred code phrase into strict-valid final state after repair. The scheduled
event mechanics worked:

- future event scheduled;
- due event completed;
- recall context delivered;
- repair provenance retained;
- final valid durable state produced.

The event-plus-recall arm therefore remains a clean continuity substrate, but
this specific task does not prove a content-recovery benefit over identity-only
continuity.

## Methodology Note

The first scoring pass overcounted recovery by searching the entire final
state. That was too broad because `deferred_fact` could remain present even if
the answer field did not satisfy the task. The runner was corrected before this
analysis to count content recovery only when `delayed_answer` contains the
deferred phrase. Strict final validity remains narrower: the validator requires
`delayed_answer` to be a string containing the phrase.

## Interpretation

This is a useful falsification. The task was not hard enough to demonstrate
event-plus-recall benefit because identity-only could preserve the whole
deferred fact. The result supports three claims:

1. event-plus-recall works for the matched delayed task;
2. identity-only can also work when the model carries the deferred fact forward;
3. the next task must prevent whole-fact carriage if we want to test recall
   substrate benefit.

## Next Experiment

The next probe should add an explicit compression or loss boundary:

- cycle 1 contains the full deferred fact;
- cycle 2 requires the model to keep only an abstract task handle or declared
  loss, not the code phrase itself;
- event-plus-recall receives cycle-1 recall at due time;
- identity-only receives no recall and must either recover from its compressed
  identity object or declare loss.

The primary endpoint should remain `delayed_answer` content recovery, with a
separate strict-valid durable-state endpoint.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/matched_delayed_task_continuity_20260605/run_matched_delayed_task_continuity.py
timeout 1800s uv run python experiments/event_loop/matched_delayed_task_continuity_20260605/run_matched_delayed_task_continuity.py
timeout 120s uv run python experiments/event_loop/matched_delayed_task_continuity_20260605/run_matched_delayed_task_continuity.py
jq '.summary' experiments/event_loop/matched_delayed_task_continuity_20260605/results.json
```

The first runner invocation made live model calls and wrote all four rows. The
second invocation ran in resume mode after the endpoint scoring correction and
made no new model calls.
