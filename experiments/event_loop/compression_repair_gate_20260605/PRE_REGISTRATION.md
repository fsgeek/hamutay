# Pre-Registration: Compression Repair Gate

Date: 2026-06-05

## Research Question

Can a non-leaking compression repair gate turn structurally dirty compression
rows into clean rows before due execution, without permitting exact-phrase
leakage?

The seeded clean-compression probe produced one clean event-plus-recall row and
three dirty rows. All three dirty rows removed the exact phrase and preserved
the digest/template, but failed non-secret structural requirements:

- `thinking_status` remained `initialized`;
- durable `declared_losses` was missing.

This experiment tests whether those are unrecoverable compression failures or
repairable state-object update failures.

## Hypotheses

- H291: A compression repair gate can convert at least one non-secret
  structural compression failure into a clean compression row.
- H292: Any row with exact phrase leakage or retained `deferred_fact` is culled
  and not repaired.
- H293: Dirty rows that remain invalid after repair are culled before due
  execution.
- H294: Clean event-plus-recall rows recover the deferred phrase after recall
  delivery.
- H295: Compression first-pass validation, compression repair validation,
  event provenance, and due-state validation remain distinguishable.

## Method

Run a small live DeepSeek v4 Pro panel with two replicates per arm:

1. `identity_only_compression_repair_gate`;
2. `event_plus_recall_compression_repair_gate`.

The setup matches the seeded clean-compression probe:

- cycle 1 contains the exact phrase in `deferred_fact`;
- cycle 1 also contains `memory_handle.code_phrase_sha256`;
- cycle 1 contains a non-secret `loss_template`;
- cycle 2 asks for deletion of `deferred_fact`, status update, preservation of
  the handle/template, durable `declared_losses`, and optional event scheduling.

Immediately after cycle 2:

1. Run prospective compression validation.
2. If validation is clean, continue.
3. If validation has any secret-bearing failure, cull immediately.
4. If validation has only non-secret structural failures, run exactly one
   non-leaking repair turn.
5. Re-run compression validation.
6. Proceed to due execution only if the post-repair compression state is clean.

Secret-bearing failures are:

- exact code phrase present anywhere in durable state;
- top-level `deferred_fact` still present.

Repair prompt constraints:

- do not reveal the exact phrase;
- do not ask the model to recall cycle 1;
- include only expected non-secret fields, expected digest, status, and failure
  labels;
- prohibit due-answer completion during repair.

## Predictions

If the seeded dirty rows are mainly repairable object-update errors:

- at least one row should become clean after compression repair;
- event-plus-recall rows should be most likely to become executable because
  scheduling succeeded in the seeded panel even when compression fields were
  missing;
- repaired clean event rows should recover after recall;
- identity-only repaired rows, if any, should not recover without recall.

If repair does not create clean rows, the compression boundary likely needs a
more structured API or training intervention rather than prompt-level repair.

## Falsification Criteria

- H291 is falsified if no row is made clean by compression repair.
- H292 is falsified if a secret-bearing row is repaired or proceeds to due.
- H293 is falsified if a still-invalid row proceeds to due.
- H294 is falsified if a clean event row receives recall context but fails to
  recover.
- H295 is falsified if the result artifact cannot distinguish compression
  first-pass, compression repair, event, and due-state validation provenance.

## Analysis Plan

Report:

- compression first-pass clean/dirty counts by arm;
- secret-bearing versus structural failures;
- compression repair attempted/successful counts;
- due-executed counts by final compression status;
- event recall delivery and phrase recovery among clean event rows;
- identity-only recovery among clean identity rows;
- due first-pass and due repair provenance.

Interpretation will treat repair success as evidence about the compression
boundary, not as direct evidence about identity persistence.
