# Phase 2A Substrate Contract Probe

Experiment ID: `phase_2a_substrate_contract_20260618`

## Purpose

This experiment specifies and tests the experiment-layer substrate contract for
entity-scoped wake state before larger multi-entity scale tests depend on it.
It does not modify `src/hamutay`.

The contract is recorded in `CONTRACT.md`.

## Protocol

The probe reuses the previously validated
`multi_entity_state_isolation_repair_20260618` behavior as the underlying
event-loop run, then scores the resulting logs against the Phase 2A contract.

The contract checks:

- private entity wakes start from prior state with no foreign-entity mention;
- private entity event outputs preserve the expected entity/workstream pair;
- audit and final synthesis use explicit shared requested context;
- audit and final synthesis report no contamination or attribution errors;
- model raw outputs do not author scheduler-owned fields;
- the result preserves a failure-attribution surface.

## Success Criteria

The experiment passes only if:

- the underlying multi-entity state-isolation run passes;
- all contract checks pass;
- no contract-level failure attribution records are produced.

## Interpretation

- `passed`: the Phase 2A entity-scoped wake-state contract is explicit and
  behaviorally satisfied by the experiment-layer harness.
- `failed`: state isolation, identity preservation, shared-context
  authorization, scheduler field ownership, model output, provider behavior, or
  artifact behavior prevents the contract claim.
- `inconclusive`: provider or transport behavior prevents a fair live test.
