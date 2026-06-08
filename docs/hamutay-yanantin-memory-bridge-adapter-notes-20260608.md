# Hamut'ay/Yanantin Memory Bridge Adapter Notes

Date: 2026-06-08

## Purpose

These notes map the new Hamut'ay memory bridge contract to the current
`ApachetaBridge` surface and to the future Yanantin provenance graph substrate.
They are part of the completion evidence for
`docs/hamutay-yanantin-memory-bridge-goal-20260606.md`.

## Current Bridge Contract

The Hamut'ay-facing bridge contract is implemented in
`src/hamutay/memory/bridge.py`.

Implemented contract elements:

- `MemoryPort`: structural protocol for the Hamut'ay-facing memory boundary.
- `LocalMemorySubstrate`: deterministic, failure-capable local substrate for
  contract tests.
- `MemoryResponse` and `MemoryFailure`: explicit success/failure envelopes.
- Layer constants for production-time data, contestable attestations,
  execution trace, and consumption-time retrieval reasons.

The local substrate is a contract test double only. It is not evidence that
production Yanantin storage works.

## Mapping To Current ApachetaBridge

Current `ApachetaBridge` behavior:

- `store_open_state` stores taste_open cycle state under a caller-provided UUID.
- `store_instance_record` stores instance-authored records with bridge-minted
  UUIDs.
- `retrieve` returns full record content by UUID.
- `query_edges_by_endpoint` supports graph traversal over composition edges.
- `query_open_has_field`, `query_open_by_session`, and related methods expose
  existing open-record query helpers.
- `store_edge` can add composition edges.

Bridge-port mapping:

| Memory port capability | Current ApachetaBridge support | Notes |
| --- | --- | --- |
| `store_episode` | Partial | `store_open_state` and `store_instance_record` store records, but do not yet enforce layered production/consumption separation. |
| `recall` | Partial | `retrieve` supports UUID recall; field-level and bounded payload behavior live in Hamut'ay tools today. |
| `schema` / `map` | Partial | `memory_schema` derives shape around `retrieve`; a substrate-native map is not yet present. |
| `walk` | Partial | `query_edges_by_endpoint` supports edge traversal; current edge model is Apacheta composition-edge shaped. |
| `open_items` | Partial | Can be derived from fields and tags, but no native open-item index exists. |
| `what_changed` | Not native | Can be approximated from session sequence/cycle data, but there is no bridge-level delta API. |
| `retrieval_log` | Missing | Current memory tools return data/errors but do not persist query-path telemetry. |
| `write_attestation` | Missing | Current bridge has composition edges but no append-only attestation-chain API. |

## Future Yanantin Adapter Requirements

A future Yanantin-backed adapter should satisfy the same `MemoryPort` contract
without making Hamut'ay depend on Yanantin internals.

Required adapter behavior:

- Convert Hamut'ay public UUIDs to any internal graph IDs explicitly.
- Preserve production-time coordinates separately from consumption-time
  retrieval reasons.
- Store objective reasons, labels, losses, repair proposals, relabel proposals,
  and semantic conflict judgments as contestable attestations.
- Preserve execution trace as trace-grounded evidence, not model rationale.
- Return explicit `MemoryFailure` values for missing records, invalid IDs,
  unsupported operations, truncation, and substrate unavailability.
- Persist retrieval telemetry in a queryable store, not only as process-local
  logs.
- Expose graph walks without blending conflicting claims into synthesized
  answers.
- Keep semantic ranking, embeddings, and broad `find` outside Yanantin.

## Boundary Decisions Preserved

The bridge contract preserves these current decisions:

- Yanantin owns durable structure and provenance.
- Hamut'ay owns relevance, budget policy, semantic retrieval, and eventual
  `find`.
- `find` remains deferred until its scope is explicitly decided.
- Semantic conflict detection lives above Yanantin, but semantic conflict
  write-downs must be recorded as provenance-stamped attestations.
- The local test substrate must fail visibly and must never be used as proof of
  production-storage correctness.
