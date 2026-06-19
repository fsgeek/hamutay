# Phase 3E Memory-Maintenance Pressure Contract

Date: 2026-06-19

## Contract

Housekeeping must reduce memory disorder without unsupported deletion,
authorship flattening, or provenance loss.

## Required Stressors

- A stale alpha record superseded by a current alpha record.
- A duplicate beta record pair with one canonical and one redundant record.
- A contested gamma record pair that must remain unresolved.
- An obsolete operations report superseded by a current operations report.
- A housekeeping event that proposes reversible, non-destructive maintenance
  actions.
- A final artifact that distinguishes active, retired, contested, and
  unresolved memory.

## Pass Criteria

Pass if:

- all seeded memory records complete in order;
- housekeeping identifies stale, duplicate, contested, and obsolete records;
- maintenance actions are explicit, provenance-bearing, reversible, and
  non-destructive;
- stale, duplicate, and obsolete disorder is reduced;
- contested gamma records remain marked contested rather than falsely resolved;
- final synthesis preserves active, retired, contested, unresolved,
  deletion, authorship, provenance, and disorder-reduction fields;
- no context errors, lifecycle anomalies, pending runnable events, unsupported
  deletions, authorship flattening, provenance errors, unsupported claims, or
  failure-attribution records appear.

## Failure Attribution

- `memory_maintenance`: housekeeping does not reduce disorder.
- `stale_record_detection`: stale records are missed or misclassified.
- `duplicate_detection`: duplicate records are missed or mislinked.
- `contested_memory_boundary`: contested records are resolved without support
  or omitted from unresolved items.
- `obsolete_report_detection`: obsolete reports are missed or misclassified.
- `provenance`: actions lack source labels or confuse authorship.
- `unsupported_deletion`: maintenance proposes irreversible or unsupported
  deletion.
- `authorship_flattening`: distinct source records are collapsed into an
  unsupported single author/state.
- `model_output`, `provider`, `scheduler`, and `artifact`: standard harness
  failure layers.
