# Phase 2B Yanantin Memory Contract Preregistration

Date: 2026-06-18

## Question

Does the event-loop roadmap have a sufficiently explicit Yanantin memory
contract to run a later live Yanantin-backed multi-entity memory probe without
collapsing memory, scheduler, model-output, and provider failures?

## Hypothesis

The contract is adequate if a dry validator can show that:

- event-loop identity remains scheduler-owned;
- Yanantin writes and local-only records are separated;
- entity-scoped, shared, and housekeeping memory access are separated;
- retrievals enter event wakes through explicit envelopes;
- provenance fields are sufficient to cite source records and authorship;
- failures can be attributed to the correct layer;
- the matrix distinguishes in-session state, local artifact recall, and
  Yanantin-backed recall.

## Method

No live model calls are permitted in this design-gate experiment. The validator
will inspect this experiment's contract artifacts and the existing local bridge
surfaces:

- `src/hamutay/memory/bridge.py`;
- `src/hamutay/apacheta_bridge.py`;
- `/home/tony/projects/yanantin/src/yanantin/apacheta/interface/abstract.py`.

The validator will not modify `src/hamutay` and will not claim that production
Yanantin integration already works.

## Pass Criteria

Pass if all required checks in `matrix.json` are true:

- required contract sections present;
- required provenance fields named;
- required memory scopes named;
- Yanantin-write and local-only boundaries named;
- retrieval envelope fields named;
- failure-attribution layers named;
- minimum Hamut'ay memory-port methods present;
- minimum Apacheta bridge methods present;
- matrix distinguishes recall substrates;
- budget prohibits live calls.

## Failure Criteria

Fail if any pass criterion is false. The most important failures are missing
provenance fields, missing retrieval envelope shape, lack of entity/shared
scope separation, or no way to distinguish Yanantin-backed recall from local
artifact recall.

## Advancement Rule

If this design gate passes, the roadmap may advance to a Yanantin-backed
multi-entity memory probe. That later probe must still be separately
preregistered before any live model or backend run.
