# Phase 2A Entity-Scoped Wake-State Contract

Experiment ID: `phase_2a_substrate_contract_20260618`

## Purpose

This contract makes the Phase 1 multi-entity state-isolation repair explicit
before larger scale tests depend on it. It is an experiment-layer substrate
contract, not a committed `src/hamutay` implementation.

## Identities

- `run_id`: scheduler-owned identifier for one execution run.
- `event_id`: scheduler-owned identifier for one event lifecycle.
- `record_id`: scheduler-owned identifier for one durable wake result.
- `entity_id`: model-visible identity for an entity-scoped workstream.
- `workstream_id`: model-visible identity for the stream of work owned by an
  entity.

Entity identity and run identity are not interchangeable. A run may contain
multiple entities; an entity may have multiple events inside a run.

## State Scopes

### Scheduler State

Scheduler state is owned by the event-loop substrate. It includes event
lifecycle, run identity, record identity, restart frontier metadata, and event
claim/completion state.

The model may observe scheduler state through event envelopes, but it must not
author scheduler-owned fields as durable model state.

### Entity State

Entity state is owned by a specific `entity_id` and `workstream_id` pair. Before
an entity-scoped wake, the substrate must select that entity's own latest state
or a clean seed-derived state for first contact.

An entity-scoped prior wake state must not mention another entity unless the
event uses an explicit authorized shared-context channel.

### Shared Context

Shared context is allowed only when an event explicitly requests records from
multiple entities through its `requested_context`. Audit and synthesis events
may use shared context; private entity events may not silently inherit it.

Shared context must remain attributable: the event envelope must preserve which
record supplied which content.

## Merge Rules

- Entity event output merges back into that entity's state only.
- Entity event output must preserve the event's required `entity_id` and
  `workstream_id`.
- Shared audit or synthesis output may produce shared summary fields, but it
  must not rewrite private entity state.
- Scheduler-owned fields such as `event_id`, `run_id`, `record_id`, and
  `scheduled_by_record_id` are substrate fields, not model-owned durable state.

## Required Checks

The contract is satisfied only if:

- private entity wakes start from prior state with no foreign-entity mention;
- private entity event outputs preserve the expected entity/workstream pair;
- audit and final synthesis use explicit shared requested context;
- audit and final synthesis report no contamination or attribution errors;
- model raw outputs do not author scheduler-owned fields;
- failures can be attributed to state isolation, model output, scheduler,
  provider, or artifact layers.

## Non-Goals

This contract does not yet introduce Yanantin-backed memory. Yanantin remains
behind the Phase 2B gate until local scale tests either pass or fail
specifically on recall, provenance, or cross-session reconstruction.
