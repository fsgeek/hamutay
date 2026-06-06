# Hamut'ay/Yanantin Memory Bridge Goal

Date: 2026-06-06

## Goal

Build Hamut'ay's bridge toward Yanantin's provenance graph substrate without
waiting for Yanantin internals to be complete and without pretending the bridge
is the full memory system.

The first executable slice is a contract-facing memory port plus a deterministic
local test substrate. The local substrate is not a permissive mock that silently
proves success. It is a failure-capable contract test double: durable enough for
tests, deterministic, provenance-preserving, and able to surface missing records,
truncation, invalid IDs, ambiguous relabels, unsupported operations, and
substrate unavailability as explicit failures.

## Objective

Make Hamut'ay's event-loop and memory-tool code depend on a narrow memory port
rather than directly on unfinished substrate details.

This goal establishes the boundary contract that a future Yanantin adapter must
satisfy:

- Yanantin owns durable structure and provenance.
- Hamut'ay owns relevance, budget policy, semantic retrieval, and eventual
  `find`.
- Consumption-time assertions must never be stored as production-time truth.
- Missing substrate behavior must fail visibly instead of being hidden by a
  fallback that makes the experiment appear to work.

## Required Source Documents

The implementation must use these documents as the controlling requirements:

- `docs/hamutay-memory-system-requirements-20260606.md`
- `docs/yanantin-substrate-position.md`
- `docs/event-loop-continuity-substrate-spec-20260605.md`
- `docs/bounded-autonomous-work-research-roadmap-20260605.md`

If these documents disagree, preserve the disagreement in `audit_notes.md` or
the implementation notes instead of silently choosing a convenient behavior.

## Required Deliverables

Minimum deliverables:

- Hamut'ay-facing memory port interface or protocol.
- Deterministic local test substrate implementation.
- Contract tests for the memory port.
- Adapter notes for current `ApachetaBridge` behavior and future Yanantin
  integration.
- Validation or audit notes describing mismatches, deferred behavior, and known
  bridge limitations.

Optional but preferred:

- README or usage note explaining how to run the contract tests.
- Small fixture dataset for bridge tests.
- Ledger- or stocktake-compatible note if the implementation resolves an
  existing substrate boundary from the bounded-autonomous-work map.

No new model experiment is required for this goal.

## Memory Port Capabilities

The Hamut'ay-side memory port must expose capabilities equivalent to:

- `store_episode`: store a cycle, event, tool result, artifact, evidence request,
  fulfillment, scorer result, repair, or state transition.
- `recall`: retrieve by stable public record ID, field, or bounded coordinate.
- `schema` or `map`: inspect available structure without loading full content.
- `walk`: traverse graph structure from a known anchor.
- `open_items`: retrieve unresolved questions, evidence requests, declared
  losses, and pending commitments.
- `what_changed`: retrieve deltas since a cycle, event, or record.
- `retrieval_log`: inspect retrieval attempts, successes, failures, truncation,
  and consumption-time retrieval reasons.
- `write_attestation`: append a contestable claim, status transition, semantic
  conflict edge, declared loss, repair proposal, or relabel proposal.

Tool names may differ, but the implemented boundary must preserve these
capabilities.

## Layering Requirements

The implementation must keep these layers separate:

- production-time coordinates: who, what, when, and grounded where;
- contestable objective attestations: declared goals, hypotheses, evidence
  requests, policy reasons, labels, loss declarations, and repair proposals;
- execution trace: provider path, protocol path, tool invocation, validation
  path, repair path, scorer path, and observed tool or terminal outputs;
- consumption-time derivations: retrieval reason, query purpose, relevance
  interpretation, context placement, and semantic conflict judgments.

Consumption-time derivations may be stored as attestations about retrieval or
maintenance activity. They must not be written into the retrieved episode as
production-time truth.

## Local Test Substrate Requirements

The local test substrate must:

- use stable public UUID record IDs;
- preserve records, graph edges, attestations, and retrieval-log entries;
- support deterministic ordering for tests;
- expose explicit failures for missing records, invalid IDs, unsupported modes,
  ambiguous relabels, truncation, and configured substrate unavailability;
- preserve first failure and repair provenance rather than replacing it;
- make append-only behavior testable;
- make production/consumption layer separation testable;
- avoid semantic ranking, embeddings, or broad `find`.

The local substrate may live entirely in memory if the contract tests can
reconstruct every required behavior deterministically. It must not be described
or treated as proof that production storage works.

## Current Integration Targets

The bridge should align with the existing Hamut'ay surfaces before introducing
new concepts:

- `src/hamutay/apacheta_bridge.py` currently provides storage, stable UUID
  record retrieval, open-record queries, and composition-edge traversal.
- `src/hamutay/tools/memory.py` currently provides `memory_schema`, `recall`,
  `compare`, `walk`, and `search_memory`.
- Existing record-ID errors such as "record_id mode requires a bridge" are
  informative boundary evidence and must not be hidden.

The new memory port should make these behaviors bridgeable while leaving room
for a future Yanantin-backed adapter.

## Deferred Behavior

The following are explicitly deferred:

- semantic ranking;
- embeddings;
- broad or unscoped `find`;
- model-facing changes to the taste_open prompt;
- new model experiments;
- claims that the memory system improves artifact quality;
- claims that model identity, autonomy, or broad capability has been proven.

If a lexical search helper is used for tests, it must be named and documented as
scoped lexical test behavior, not as semantic `find`.

## Required Test Scenarios

Contract tests must cover at least:

- exact record recall by UUID;
- invalid UUID failure;
- missing record failure;
- schema/map retrieval without full content;
- field-level recall;
- graph walk from a known anchor;
- unresolved/open item retrieval;
- append-only attestation chain preservation;
- declared-loss visibility;
- retrieval-log creation on successful recall;
- retrieval-log creation on failed recall;
- explicit truncation metadata for bounded payloads;
- production-time and consumption-time fields remaining separate;
- relabel proposal recorded as contestable attestation, not overwrite;
- semantic conflict write-down represented as attestation edge, not substrate
  truth;
- unsupported semantic `find` failing explicitly rather than pretending success.

Tests must preserve any failed first-pass behavior as evidence. A repair or
adapter workaround must not erase the original failure.

## Required Execution Sequence

1. Inspect the current `ApachetaBridge`, memory tools, event-loop substrate spec,
   and Yanantin substrate position.
2. Define the memory port interface or protocol with stable public record IDs
   and explicit failure results.
3. Implement the deterministic local test substrate behind the port.
4. Add contract tests for the required scenarios.
5. Add adapter notes documenting how current `ApachetaBridge` behavior maps to
   the port and what future Yanantin support remains required.
6. Run focused unit and contract tests before touching broader integration.
7. Run any existing memory-tool and bridge tests affected by the port.
8. Preserve validation results, failures, and known limitations in notes.
9. Commit and push all aligned artifacts.

## Completion Criteria

The goal is complete only when:

- the memory port exists and is used by the local test substrate;
- the local test substrate fails visibly for unsupported or unavailable behavior;
- contract tests cover all required scenarios;
- contract tests pass locally;
- relevant existing memory-tool or bridge tests pass locally, or failures are
  documented as unrelated or as discovered boundary evidence;
- adapter notes explain current `ApachetaBridge` compatibility and gaps;
- no new model experiment is required to validate the bridge contract;
- no semantic `find` or ranking feature is implemented by accident;
- production-time and consumption-time assertions remain separated in tests;
- all created or changed artifacts are committed and pushed.

## Non-Completion Conditions

The goal is not complete if:

- a fake storage layer silently returns success for missing or unsupported
  behavior;
- a retrieval reason is stored as production-time episode truth;
- relabeling overwrites an original claim or label;
- semantic conflict judgments are stored without provenance as substrate truth;
- missing bridge behavior falls back to prompt-near context without being
  recorded;
- broad `find` is implemented before its scope decision is made;
- tests prove only happy-path recall and do not exercise failure behavior;
- adapter gaps are hidden in prose or omitted from audit notes;
- the work cannot be rerun or audited from preserved artifacts.

