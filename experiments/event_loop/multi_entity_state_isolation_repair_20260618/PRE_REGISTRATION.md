# Multi-Entity State Isolation Repair Test

Experiment ID: `multi_entity_state_isolation_repair_20260618`

## Purpose

This experiment tests whether the multi-entity event loop failure is repaired
by restoring entity-scoped wake state before each entity-specific event. The
prior live multi-entity attempt completed the scheduler sequence but allowed
default-stable fields from `entity_red` to appear in `entity_blue`'s prior wake
state. This probe preserves the scheduler sequence while preventing one
entity's durable state from becoming another entity's prompt prior state.

## Sequence

The run executes:

1. Seed durable session state.
2. Restore clean/owned wake state and handle inbound work for
   `entity_red` / `red_stream`.
3. Restore `entity_red` wake state and complete its framework-scheduled
   continuation.
4. Restore clean/owned wake state and handle inbound work for
   `entity_blue` / `blue_stream`.
5. Restore `entity_blue` wake state and complete its framework-scheduled
   continuation.
6. Run an identity-isolation audit across both continuation result records.
7. Write a final multi-entity artifact.

Each event boundary commits a restart frontier.

## Success Criteria

The experiment passes only if:

- both entities complete inbound and continuation events;
- the completed event sequence matches the protocol;
- terminal-surface sequence matches the protocol;
- each entity-specific event starts from a prior wake state that does not
  mention the other entity;
- every entity-specific event preserves the expected `entity_id` and
  `workstream_id`;
- the audit reports no cross-contamination and no attribution errors;
- the final artifact reports both entities and no attribution errors;
- context resolution, lifecycle, and material outcome checks have no errors;
- restart-frontier commits occur after multiple boundaries.

## Interpretation

- `passed`: the experiment-layer state isolation repair prevents the observed
  cross-entity wake-state leak at this small panel size.
- `failed`: identity drift, context contamination, attribution error,
  entity-state isolation failure, scheduler lifecycle failure, model-output
  failure, provider failure, or artifact failure prevents the claim.
- `inconclusive`: provider or transport behavior prevents a fair test.
