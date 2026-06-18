# Phase 2A Larger Multi-Entity Sustained Loop

Experiment ID: `phase_2a_larger_multi_entity_loop_20260618`

## Purpose

This experiment tests whether the event-loop substrate scales mechanically
beyond the repaired two-entity case without adding Yanantin. It uses local
artifacts only and preserves the Phase 2A entity-scoped wake-state contract as
the measurement surface.

## Protocol

The run uses three entities:

- `entity_red` / `red_stream`
- `entity_blue` / `blue_stream`
- `entity_green` / `green_stream`

The run executes two rounds. Each round interleaves:

1. inbound events for all three entities;
2. continuation events for all three entities;
3. one shared housekeeping audit.

After the second round, the run writes a final synthesis artifact. Each event
boundary commits a restart frontier. Yanantin is not enabled.

## Success Criteria

The experiment passes only if:

- all expected events complete in the preregistered order;
- entity/workstream/round identity follows the interleaved sequence;
- private entity prior states contain no foreign-entity mentions;
- housekeeping occurs after each round and reports no contamination or
  attribution errors;
- final synthesis reports three entities, two rounds, and twelve completed
  entity events;
- model raw outputs do not author scheduler-owned fields;
- local artifacts are the only memory substrate;
- context, lifecycle, idle, and restart-frontier checks are clean.

## Interpretation

- `passed`: the Phase 2A event-loop substrate scales to a three-entity,
  two-round interleaved sustained loop without Yanantin under this protocol.
- `failed`: state isolation, identity, interleaving, housekeeping, scheduler,
  model-output, provider, or artifact behavior prevents the scale claim.
- `inconclusive`: provider or transport behavior prevents a fair live test.
