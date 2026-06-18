# Phase 2A Local Memory Pressure Probe

Experiment ID: `phase_2a_local_memory_pressure_20260618`

## Purpose

This experiment tests whether current local mechanisms can support recall,
comparison-like checking, and provenance-bearing final synthesis without
Yanantin. The probe intentionally removes each commitment from the entity's
current wake state before recall, forcing recovery through explicit local
`requested_context`.

## Protocol

The run uses three entities. Each entity first records a unique commitment.
Later, each entity wakes from a clean entity state that does not contain the
commitment and must recover the commitment from the explicit recalled source
record. A housekeeping event audits the recall records, and a final artifact
cites the source record IDs.

Yanantin is disabled. The memory substrate is local requested context only.

## Success Criteria

The experiment passes only if:

- all expected commitment, recall, housekeeping, and final events complete;
- each recall event's prior state does not contain the recalled commitment;
- each recalled commitment code matches the entity's original commitment;
- each recall output cites the source commitment record ID;
- housekeeping checks all recall records and reports no unsupported claims or
  attribution errors;
- final synthesis includes all recalled commitment codes and provenance record
  IDs;
- context, lifecycle, and idle checks are clean;
- the Yanantin gate remains closed.

## Interpretation

- `passed`: local requested-context recall is sufficient for this bounded
  memory-pressure surface, so Phase 2A may continue without Yanantin.
- `failed`: if the failure is specifically recall, provenance, or
  cross-session reconstruction, the Phase 2B Yanantin gate may open. Other
  failures keep the gate closed until scheduler/model/provider issues are
  isolated.
- `inconclusive`: provider or transport behavior prevents a fair live test.
