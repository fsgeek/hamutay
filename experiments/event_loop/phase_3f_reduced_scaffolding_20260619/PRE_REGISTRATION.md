# Phase 3F Reduced-Scaffolding Preregistration

Date: 2026-06-19

## Question

Can the event-loop framework loosen terminal surface value constraints while
preserving memory-maintenance discipline and attributable failures?

## Hypothesis

Reduced scaffolding passes this first rung if the model can preserve the
Phase 3E memory-maintenance contract when field names remain required but most
exact-value enum rails are removed.

## Prediction

This is likely to fail sooner than substrate mechanics. The most likely
failure modes are stale field leakage, action-label drift, final-claim
overreach, provenance loss, unsupported deletion, or diffuse failure
attribution.

## Method

Run the Phase 3E memory-maintenance matrix with loosened terminal schemas:
seed eight memory records, run housekeeping maintenance, and write a final
maintenance artifact. Score with the same clarified Phase 3E postconditions.

Clarification after the initial live run: fields copied into durable state by
the harness remain required even when their values are unconstrained. Absent
`superseded_by`, `duplicate_of`, and `conflict_group` values are represented
as empty strings.

## Pass Criteria

Pass if all contract checks in `CONTRACT.md` are true.

## Failure Criteria

Fail if any pass criterion is false. Attribute failures to reduced
scaffolding, model output, provenance, unsupported deletion, authorship
flattening, memory maintenance, duplicate detection, stale detection,
obsolete-report detection, contested-memory boundary, scheduler, provider, or
artifact behavior.

## Budget

Live direct-DeepSeek run budget: at most 11 model calls and at most 5 USD
estimated cost. Dry scripted runs make no model calls.
