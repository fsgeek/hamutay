# Pre-Registration: Compression-Validated Delayed Task

Date: 2026-06-05

## Research Question

Can a prospective compression validator cull dirty compression rows before due
execution, and does event-plus-recall still recover the deferred fact on clean
rows while identity-only does not?

The previous compressed delayed-task probe showed a positive event-plus-recall
map point, but compression cleanliness was scored retrospectively. One
identity-only row leaked the phrase during compression and then recovered from
that leakage. This experiment moves compression validation before due-time
execution.

## Hypotheses

- H281: The compression validator can classify cycle-2 compression as clean or
  dirty before any due step runs.
- H282: Dirty compression rows are culled before due execution and retained as
  leakage data.
- H283: Clean event-plus-recall rows recover the deferred phrase after recall
  delivery.
- H284: Clean identity-only rows do not recover the deferred phrase.
- H285: Compression validation, due validation, and repair provenance remain
  distinguishable.

## Method

Run a small live DeepSeek v4 Pro panel with two replicates per arm:

1. `identity_only_compression_validated`;
2. `event_plus_recall_compression_validated`.

Both arms start from controlled cycle-1 state containing the exact deferred
code phrase. Cycle 2 asks the model to remove the exact phrase, keep only a
digest/handle and declared loss, and, for the event arm, schedule recall of
cycle 1.

Immediately after cycle 2, validate compression. A clean compression state must:

- preserve `probe_id`;
- set `thinking_status` to `parked` or `scheduled`;
- remove top-level `deferred_fact`;
- not contain the exact code phrase anywhere in durable state;
- include `memory_handle.code_phrase_sha256`;
- preserve the baseline observation;
- avoid deleting `probe_id` or `cycle`.

Dirty rows do not proceed to due execution. They are analyzed as compression
leakage/cull rows.

## Predictions

If the compression validator works:

- at least one clean row should be produced;
- dirty rows should not run due;
- clean event-plus-recall rows should recover after recall;
- clean identity-only rows should fail to recover or declare loss.

## Falsification Criteria

- H281 is falsified if compression validation cannot be produced for every row.
- H282 is falsified if dirty rows proceed to due execution.
- H283 is falsified if clean event-plus-recall rows receive recall but fail to
  recover.
- H284 is falsified if clean identity-only rows recover.
- H285 is falsified if compression validation is conflated with due validation
  or wake repair provenance.

## Analysis Plan

Report:

- compression-clean and compression-dirty counts by arm;
- due-executed counts by arm and cleanliness;
- recall delivery for event rows;
- phrase recovery among clean rows;
- final durable validity among clean rows;
- leakage details for dirty rows;
- first-pass and repair provenance for due-executed rows.

Interpretation will separate compression-gate function from recall-substrate
benefit.
