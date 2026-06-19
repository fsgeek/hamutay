# Model Contract Compliance Audit Contract

Date: 2026-06-19

The audit isolates four contract obligations that failed or became ambiguous
in Phase 3F reduced scaffolding. Each obligation is tested in a separate
single-event probe with loose terminal value schemas and exact post-run
scoring.

## Required Behavior

1. The vocabulary probe must return exactly these action labels, in order:
   `retire_stale`, `retire_obsolete_report`, `mark_contested`.
2. The provenance probe must return visible record labels, not record ids:
   duplicate `beta-duplicate-b`, canonical `beta-duplicate-a`, provenance
   labels `beta-duplicate-a` and `beta-duplicate-b`, and
   `used_record_ids_as_provenance` false.
3. The kind/source probe must return `contested_memory` and
   `housekeeping-maintenance` without synonym drift.
4. The count-semantics probe must distinguish disorder classes from
   disordered records: class counts 4 to 1, record counts 5 to 2, class
   reduction 3.

## Pass Rule

The run passes only if all four probes complete in order, use the expected
terminal tools, return no unsupported claims, leave no runnable events, and
meet every exact postcondition.

## Interpretation

An isolated failure supports a model-contract or framework-contract weakness
for that obligation. Isolated success paired with Phase 3F failure supports a
context/load interaction rather than a basic inability to copy the contract.
