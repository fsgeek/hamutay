# Phase 3F Reduced-Scaffolding Contract

Date: 2026-06-19

## Contract

Terminal surfaces may be loosened only if the loop still preserves identity,
provenance, declared-loss/deletion discipline, memory-maintenance state, and
final-claim discipline with attributable failures.

## Reduced Surface

This first Phase 3F rung reuses the passed Phase 3E memory-maintenance matrix,
but removes most exact-value enum rails from terminal schemas:

- response enums removed;
- record-label, status, action, list-item, boolean, and integer value enums
  removed;
- required field names remain;
- scheduler-owned event identity remains harness-authored;
- the scoring contract remains the Phase 3E clarified contract.

## Pass Criteria

Pass if:

- all expected events complete in order;
- terminal tools appear in the expected order;
- seeded memory record labels and provenance are preserved without enum rails;
- stale, duplicate, obsolete, and contested records are classified correctly;
- maintenance actions are explicit, provenance-bearing, reversible, and
  non-destructive;
- final synthesis preserves active, stale-retired, linked-duplicate,
  obsolete-report, contested, unresolved, deletion, authorship, provenance,
  and disorder-reduction fields;
- failures, if any, remain attributable rather than diffuse.

## Failure Attribution

- `reduced_scaffolding`: loosened surfaces make the failure unreadable.
- `model_output`: required fields are missing or malformed.
- `provenance`: records or action provenance are lost or flattened.
- `unsupported_deletion`: irreversible or unsupported deletion appears.
- `authorship_flattening`: distinct source records collapse into one
  unsupported author/state.
- `memory_maintenance`, `duplicate_detection`, `stale_record_detection`,
  `obsolete_report_detection`, and `contested_memory_boundary`: same meanings
  as Phase 3E.
