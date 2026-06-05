# Pre-Registration: Seeded Clean Compression Probe

Date: 2026-06-05

## Research Question

Can DeepSeek produce a clean compression state when the digest and loss language
are already present in cycle 1, so cycle 2 only needs to preserve the handle and
delete the exact phrase without restating or reconstructing it?

The previous compression-validated delayed-task panel culled every row. The
event-plus-recall arm scheduled correctly and emitted the digest, but leaked the
exact phrase in `declared_losses`. The identity-only arm removed
`deferred_fact`, but failed to emit the required `memory_handle` and did not set
the expected status. This experiment attacks that confound directly.

## Hypotheses

- H286: Seeded digest and seeded loss template increase the chance of clean
  compression relative to the previous strict gate.
- H287: Event-plus-recall clean rows, if any, recover the deferred phrase after
  recall delivery.
- H288: Identity-only clean rows, if any, do not recover the deferred phrase.
- H289: Dirty rows are prospectively culled before due execution.
- H290: The result separates compression cleanliness from due-time repair and
  recall provenance.

## Method

Run a small live DeepSeek v4 Pro panel with two replicates per arm:

1. `identity_only_seeded_clean_compression`;
2. `event_plus_recall_seeded_clean_compression`.

Cycle 1 is seeded with:

- the exact phrase in `deferred_fact`;
- a top-level `memory_handle.code_phrase_sha256`;
- a top-level `loss_template` whose text does not contain the exact phrase;
- a baseline observation.

Cycle 2 asks the model to:

- delete `deferred_fact`;
- preserve `probe_id`, `thinking_question`, `memory_handle`, `loss_template`,
  and the baseline observation;
- set `thinking_status` to `parked` for identity-only or `scheduled` for
  event-plus-recall;
- set `declared_losses` by copying or paraphrasing `loss_template` without the
  exact phrase;
- for event-plus-recall only, schedule a due wake with recall of cycle 1.

The compression prompt will include the digest, but will not include the exact
phrase. Immediately after cycle 2, a prospective validator checks the durable
state. Dirty rows are retained as cull/leakage data and do not proceed to due
execution.

## Predictions

If the prior all-dirty result was caused mainly by prompt wording and object-use
friction:

- at least one seeded row should pass compression validation;
- event-plus-recall should be more likely than identity-only to pass, because
  the event arm already emitted the handle and expected status in the prior
  panel;
- dirty rows should never run due;
- clean event-plus-recall rows should recover the exact phrase after recall;
- clean identity-only rows should either declare loss or fail to recover.

If no rows pass compression validation, the failure is stronger evidence that
the scaffold still does not reliably support clean compression for this model.

## Falsification Criteria

- H286 is falsified if no seeded row passes compression validation.
- H287 is falsified if a clean event-plus-recall row receives recall context but
  does not recover the phrase.
- H288 is falsified if a clean identity-only row recovers the phrase.
- H289 is falsified if any dirty row proceeds to due execution.
- H290 is falsified if compression validation, event provenance, or due-state
  validation cannot be distinguished in the result artifact.

## Analysis Plan

Report:

- compression-clean and compression-dirty counts by arm;
- dirty failure reasons by arm;
- due-executed counts by cleanliness;
- event scheduling and recall delivery for event rows;
- phrase recovery among clean rows;
- final durable validity among clean rows;
- first-pass and repair provenance for due-executed rows.

Interpretation will treat clean compression as the primary outcome and
due-recall comparison as conditional on clean rows existing.
