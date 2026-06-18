# Restart/Resume Interruption Test

Experiment ID: `restart_resume_interruption_20260618`

## Purpose

This experiment tests whether a nontrivial event loop can recover from an
intentional interruption after an event is claimed as `running` but before the
event exchange completes. The test uses committed restart-frontier artifacts to
recover the interrupted event back to `pending`, resumes the Open Taste session
from the durable session log, and completes the recovered event.

## Sequence

The run executes:

1. Seed durable session state and commit a restart frontier.
2. Schedule and complete an inbound IPC event.
3. Auto-schedule and complete a framework-bound continuation.
4. Schedule a housekeeping event and commit a restart frontier before claim.
5. Claim the housekeeping event as `running` and simulate interruption before
   model exchange.
6. Load the latest restart frontier, recover the interrupted event to
   `pending`, and resume the session from the durable log.
7. Complete the recovered housekeeping event and commit a final frontier.

## Success Criteria

The experiment passes only if:

- the completed event sequence is inbound, self-scheduled continuation, then
  housekeeping;
- exactly one housekeeping event is recovered from `running` to `pending`;
- no events are suppressed during frontier load;
- the interrupted event history is `pending`, `running`, `pending`, `running`,
  `completed`;
- all completed event result records exist in the resumed session log;
- context resolution, lifecycle, and idle checks have no errors;
- restart-frontier commits exist across the seed, pre-interruption, and resumed
  boundaries.

## Interpretation

- `passed`: the event-loop substrate can recover an interrupted claimed event
  and resume a nontrivial loop from committed artifacts under this protocol.
- `failed`: restart frontier, event lifecycle, context reconstruction,
  scheduler, model-output, provider, or artifact behavior prevents the claim.
- `inconclusive`: provider or transport behavior prevents a fair live test.
