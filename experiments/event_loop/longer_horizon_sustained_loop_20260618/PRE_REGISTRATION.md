# Longer-Horizon Sustained Loop Test

Experiment ID: `longer_horizon_sustained_loop_20260618`

## Purpose

This experiment tests the roadmap's current priority: whether the event loop can
operate beyond a short readiness probe by handling multiple inbound tasks,
self-scheduled continuations, housekeeping, restart-frontier updates, and a
final artifact synthesis in one sustained run.

## Sequence

The run executes:

1. Seed durable session state.
2. Handle inbound task `alpha`.
3. Complete the framework-bound continuation for task `alpha`.
4. Run housekeeping.
5. Handle inbound task `beta`.
6. Complete the framework-bound continuation for task `beta`.
7. Run housekeeping.
8. Write a final artifact synthesizing both tasks.

Each event boundary commits a restart frontier. The final synthesis must cite
state from more than one task.

## Success Criteria

The experiment passes only if:

- two inbound events complete;
- two framework-bound continuation events complete;
- two housekeeping events complete;
- one final artifact synthesis event completes;
- the completed event-type and terminal-surface sequences match the protocol;
- the final artifact reports `task_count = 2`;
- restart-frontier commits occur after multiple event boundaries;
- context resolution, lifecycle, and outcome checks have no errors.

## Interpretation

- `passed`: the single-entity sustained loop is viable at this longer horizon.
- `failed`: a scheduler, model-output, context-recovery, provider, artifact, or
  declared-loss failure prevents the long-horizon claim.
- `inconclusive`: provider or transport behavior prevents a fair test.
