# Hamut'ay/Yanantin Memory Bridge Audit Notes

Date: 2026-06-08

## Goal Under Audit

`docs/hamutay-yanantin-memory-bridge-goal-20260606.md`

This audit records the first executable bridge slice:

- Hamut'ay-facing memory port.
- Deterministic failure-capable local test substrate.
- Contract tests for the required bridge behaviors.
- Adapter notes for current `ApachetaBridge` and future Yanantin integration.

No model experiment was run or required.

## Source Documents Used

- `docs/hamutay-memory-system-requirements-20260606.md`
- `docs/yanantin-substrate-position.md`
- `docs/event-loop-continuity-substrate-spec-20260605.md`
- `docs/bounded-autonomous-work-research-roadmap-20260605.md`

The material design tension is explicit and preserved: Hamut'ay requires a
larger working-set memory system, while Yanantin refuses to become a retrieval
engine. The bridge therefore implements the contract boundary and keeps
semantic `find`, ranking, and embeddings deferred to the consumer layer.

## Validation Evidence

Focused contract test:

```text
uv run pytest tests/unit/test_memory_bridge_contract.py -q
```

Observed result during implementation:

```text
12 passed
```

The test file covers:

- exact record recall by UUID;
- invalid UUID failure;
- missing record failure;
- schema/map retrieval without full content;
- field-level recall;
- graph walk from a known anchor;
- unresolved/open item retrieval;
- append-only attestation preservation;
- declared-loss visibility;
- retrieval-log creation on successful recall;
- retrieval-log creation on failed recall;
- explicit truncation metadata for bounded payloads;
- production-time and consumption-time separation;
- relabel proposal as contestable attestation, not overwrite;
- semantic conflict write-down as attestation edge, not substrate truth;
- unsupported semantic `find` explicit failure;
- configured substrate unavailability explicit failure.

## Repair Provenance

An initial contract test exposed that graph walking suppressed a second edge
between the same two records when the target record had already been visited.
That would have hidden a semantic-conflict write-down if a `refines` edge
already connected the same records.

Repair:

- `LocalMemorySubstrate.walk` now emits distinct edges even when the target
  record has already been visited.
- The visited set still prevents traversal loops; it no longer hides parallel
  edge evidence.

## Known Boundaries

- The local substrate is process-local test storage, not production storage.
- Retrieval telemetry is in-memory for this slice; a Yanantin adapter must
  persist it in a queryable substrate.
- Current `ApachetaBridge` does not yet expose native attestation-chain or
  retrieval-log APIs.
- Current `ApachetaBridge` does not yet enforce production/consumption layer
  separation.
- Broad semantic `find` remains intentionally unsupported.
- Existing model-facing tools have not been redesigned in this slice.

## Non-Goal Confirmation

This slice did not implement:

- embeddings;
- semantic ranking;
- broad or unscoped `find`;
- model prompt changes;
- model experiments;
- artifact-quality claims;
- broad identity, autonomy, or model-capability claims.
