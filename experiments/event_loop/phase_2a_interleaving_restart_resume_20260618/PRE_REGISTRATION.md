# Phase 2A Interleaving Restart/Resume Stress

Experiment ID: `phase_2a_interleaving_restart_resume_20260618`

## Purpose

This experiment tests whether the larger interleaved multi-entity loop remains
recoverable after an intentional interruption. It keeps Yanantin disabled and
uses local artifacts only.

## Protocol

The probe reuses the larger Phase 2A three-entity, two-round sustained loop.
During round 2, it interrupts `entity_green`'s continuation after the event is
claimed as `running` but before the model exchange. It then:

1. loads the latest restart frontier;
2. recovers the interrupted event from `running` back to `pending`;
3. resumes the Open Taste session from the durable session log;
4. reconstructs entity-scoped state from local session artifacts;
5. completes the recovered continuation;
6. finishes housekeeping and final synthesis.

## Success Criteria

The experiment passes only if:

- all larger-loop checks still pass;
- exactly one interrupted `entity_continuation` event is recovered;
- no events are suppressed during frontier load;
- the interrupted event lifecycle is `pending`, `running`, `pending`,
  `running`, `completed`;
- entity-scoped state for the interrupted entity is reconstructed before the
  resumed event;
- private entity prior states remain isolated after resume;
- final synthesis and housekeeping remain clean.

## Interpretation

- `passed`: the larger interleaved loop can recover an interrupted entity event
  from committed local artifacts without losing identity, state isolation, or
  scheduler lifecycle.
- `failed`: restart frontier, event lifecycle, state reconstruction,
  state-isolation, model-output, provider, or artifact behavior prevents the
  claim.
- `inconclusive`: provider or transport behavior prevents a fair live test.
