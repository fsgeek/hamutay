# Seeded Clean Compression Analysis

Date: 2026-06-05

## Result

Seeding `memory_handle` and `loss_template` produced the first prospectively
clean compression row in this branch.

| Condition | Rows | Clean | Dirty | Due executed | Recall context | Fact recovered | Final valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `identity_only_seeded_clean_compression` | 2 | 0 | 2 | 0 | 0 | 0 | 0 |
| `event_plus_recall_seeded_clean_compression` | 2 | 1 | 1 | 1 | 1 | 1 | 1 |

Hypothesis status from `results.json`:

- H286 seeded clean compression exists: supported.
- H287 clean event recall recovers: supported for the one clean event row.
- H288 clean identity does not recover: not supported by this panel because no
  clean identity row existed.
- H289 dirty rows culled before due: supported.
- H290 provenance distinguishable: supported.

## Compression Pattern

Seeding changed the failure surface.

All four rows:

- removed top-level `deferred_fact`;
- preserved `memory_handle.code_phrase_sha256`;
- preserved `loss_template`;
- avoided exact phrase leakage in the cycle-2 durable state.

Three rows still failed compression:

- both identity-only rows left `thinking_status` as `initialized`;
- both identity-only rows omitted durable `declared_losses`;
- event replicate 2 scheduled correctly but also left `thinking_status` as
  `initialized` and omitted durable `declared_losses`.

Those three dirty rows were culled before due execution.

The clean row was event-plus-recall replicate 1. It:

- set `thinking_status` to `scheduled`;
- preserved the seeded digest;
- emitted durable `declared_losses` without the exact phrase;
- scheduled one event with recall of cycle 1;
- passed prospective compression validation.

## Due-Step Outcome

The clean event row proceeded to due execution. The event completed with recall
context, recovered `amber-lattice-17`, and ended with a final valid durable
state.

The due wake required repair:

- first-pass validation: invalid;
- repair validation: valid;
- final validation status: repaired.

The repair prompt did not reveal the code phrase, so recovery came from the
delivered recall context and/or already available event context rather than
from validator leakage.

## Interpretation

The prior all-cull result was not a dead end. It identified a protocol
weakness: asking the model to create the digest/loss representation during
compression was too brittle. Seeding the digest and loss template made clean
compression possible, at least for the event-plus-recall arm.

The remaining failure is not exact-phrase leakage. It is durable object
non-compliance: the model often says it changed `thinking_status` or recorded
losses, but does not emit those fields. That is consistent with the broader
identity-object usage confound seen earlier in the project.

This result strengthens the case that the event-loop substrate should not rely
on free-form compression behavior alone. A bounded scheduler can preserve
continuity, but the compression boundary needs either:

- stronger behavior seeding;
- field-specific validators and repair;
- a structured compression tool;
- or training examples that make state-object updates natural.

## Next Research Question

The next useful experiment is a compression-repair gate, not a broader model
sweep.

Question: if a row fails only because required non-secret fields are missing or
wrong, can a non-leaking compression repair prompt produce a clean compression
state without revealing the exact phrase?

That experiment would:

- run the same seeded compression setup;
- classify compression failures as secret-bearing versus non-secret structural
  failures;
- cull any row with exact phrase leakage;
- run one non-leaking compression repair for structural failures only;
- validate again before due execution.

This would test whether the current dirty rows are unrecoverable compression
failures or merely missing-field errors at a boundary where repair is safe.
