# Analysis: Compressed Delayed Task Continuity

Date: 2026-06-05

## Result

The compression-boundary probe produced the first clear content-recovery
advantage for event-plus-recall over identity-only in this research arm.

- H276 compression-clean rows exist: supported.
- H277 event-plus-recall recovers after clean compression: supported.
- H278 clean identity-only rows do not recover: supported.
- H279 identity recovery is auditable: supported.
- H280 provenance signals are present: supported.

## Counts

Two replicates were run per condition.

`event_plus_recall_compressed`:

- compression clean: 2/2;
- recall context delivered: 2/2;
- fact recovered after clean compression: 2/2;
- final durable state valid: 2/2;
- first-pass valid: 0/2;
- repaired: 2/2;
- bounded wake call violations: 0.

`identity_only_compressed`:

- compression clean: 1/2;
- recall context delivered: 0/2;
- fact recovered after clean compression: 0/1;
- final durable state valid: 0/2;
- first-pass valid: 0/2;
- repaired: 0/2;
- bounded wake call violations: 0.

## Identity-Only Boundary

Identity-only r1 recovered the phrase, but the row was not compression-clean.
The model leaked the exact code phrase into durable/log context while claiming
it had removed it. The final state itself reports recovery from validation
context. That row is therefore a compression failure, not evidence that
identity-only can recover after clean compression.

Identity-only r2 was compression-clean and did not recover the phrase. It
invented or derived the wrong phrase from preserved identity metadata:
`deepseek-v4-pro-r2`. The validator rejected it with
`delayed_answer_missing_code_phrase`.

## Event-Plus-Recall Behavior

Both event-plus-recall rows were compression-clean, received recall context,
and recovered the exact deferred phrase into strict-valid durable state after
repair. This separates the substrate benefit from simple current-state
preservation:

1. cycle 1 contained the full deferred fact;
2. cycle 2 removed the exact phrase from current durable state;
3. due wake received cycle-1 recall;
4. final `delayed_answer` recovered the exact phrase.

## Interpretation

This is evidence that the event-loop continuity substrate can do something the
identity object alone did not do under a clean compression boundary: recover a
deferred fact that was no longer present in current durable state.

The result is still small and model-specific. It should not be treated as a
general claim about all models or all task types. But it is the first clean
positive map point for event-plus-recall as a continuity substrate rather than
just a scheduling mechanism.

## Repair Dependence

The result also preserves the earlier boundary: first-pass durable state use
remains weak.

- event-plus-recall succeeded after repair, not first pass;
- identity-only did not repair to valid state;
- non-leaking repair was important, because the validator did not reveal the
  exact phrase.

Repair should remain part of the measured substrate, not hidden as a cleanup
implementation detail.

## Next Research Move

The next useful probe is replication or adversarial compression, not another
mechanics test.

Candidate next steps:

1. increase replicates for the compressed condition;
2. add an explicit validator for compression turns so leakage is caught before
   due;
3. test a second model family;
4. make compression adversarial by requiring a declared loss that cannot include
   the exact phrase, only a digest/handle.

The most disciplined next step is probably a compression-validator panel:
validate cycle 2 before due, cull dirty compression rows from the primary
comparison, and preserve dirty rows as leakage data.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/compressed_delayed_task_continuity_20260605/run_compressed_delayed_task_continuity.py
timeout 1800s uv run python experiments/event_loop/compressed_delayed_task_continuity_20260605/run_compressed_delayed_task_continuity.py
jq '.summary' experiments/event_loop/compressed_delayed_task_continuity_20260605/results.json
```

The live runner exited successfully and wrote:

`experiments/event_loop/compressed_delayed_task_continuity_20260605/results.json`
