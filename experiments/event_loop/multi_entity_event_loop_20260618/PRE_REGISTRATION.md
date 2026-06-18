# Multi-Entity Event Loop Test

Experiment ID: `multi_entity_event_loop_20260618`

## Purpose

This experiment tests whether the event-loop scheduler can handle more than one
AI entity or workstream without identity drift, context contamination, or
attribution errors.

## Sequence

The run executes:

1. Seed durable session state.
2. Handle inbound work for `entity_red` / `red_stream`.
3. Complete a framework-scheduled continuation for `entity_red`.
4. Handle inbound work for `entity_blue` / `blue_stream`.
5. Complete a framework-scheduled continuation for `entity_blue`.
6. Run an identity-isolation audit across both continuation result records.
7. Write a final multi-entity artifact.

Each event boundary commits a restart frontier.

## Success Criteria

The experiment passes only if:

- both entities complete inbound and continuation events;
- the completed event sequence matches the protocol;
- terminal-surface sequence matches the protocol;
- every entity-specific event preserves the expected `entity_id` and
  `workstream_id`;
- the audit reports no cross-contamination and no attribution errors;
- the final artifact reports both entities and no attribution errors;
- context resolution, lifecycle, and material outcome checks have no errors;
- restart-frontier commits occur after multiple boundaries.

## Interpretation

- `passed`: the multi-entity event loop is viable at this small panel size.
- `failed`: identity drift, context contamination, attribution error,
  scheduler lifecycle failure, model-output failure, provider failure, or
  artifact failure prevents the claim.
- `inconclusive`: provider or transport behavior prevents a fair test.
