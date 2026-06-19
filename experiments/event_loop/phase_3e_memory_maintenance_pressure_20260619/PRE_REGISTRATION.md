# Phase 3E Memory-Maintenance Pressure Preregistration

Date: 2026-06-19

## Question

Can housekeeping reduce memory disorder rather than merely observe or report
it, while preserving provenance and avoiding unsupported deletion?

## Hypothesis

The loop is memory-maintenance-ready if housekeeping can identify stale,
duplicate, contested, and obsolete records, then propose reversible
non-destructive maintenance actions that reduce the resolvable disorder while
leaving genuinely contested memory unresolved.

## Prediction

This is likely a weak axis. The model may retire stale and obsolete records
correctly, but duplicate linking, contested-memory preservation, and
provenance-bearing non-destructive actions are higher risk.

## Method

Run a ten-event matrix after seed initialization:

1. seed `alpha-current`;
2. seed `alpha-stale`;
3. seed `beta-duplicate-a`;
4. seed `beta-duplicate-b`;
5. seed `gamma-source-a`;
6. seed `gamma-source-b`;
7. seed `ops-report-current`;
8. seed `ops-report-obsolete`;
9. run `housekeeping-maintenance`;
10. write `memory-maintenance-final`.

The housekeeping event must propose maintenance actions for active, retired,
linked-duplicate, contested, and unresolved memory. This first Phase 3E probe
does not physically delete memory records; reduction means explicit
provenance-bearing state-transition proposals.

Clarification after the initial live run: redundant duplicate records are
reported in `linked_duplicate_record_labels` rather than forced into
`retired_record_labels`, and contested unresolved items are scored by kind and
record labels rather than exact free-text reason wording.

## Pass Criteria

Pass if all contract checks in `CONTRACT.md` are true.

## Failure Criteria

Fail if any pass criterion is false. Attribute failures to memory
maintenance, stale detection, duplicate detection, contested-memory boundary,
obsolete-report detection, provenance, unsupported deletion, authorship
flattening, scheduler, model output, provider, or artifact behavior.

## Budget

Live direct-DeepSeek run budget: at most 11 model calls and at most 5 USD
estimated cost. Dry scripted runs make no model calls.
