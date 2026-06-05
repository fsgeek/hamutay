# Pre-Registration: Scheduled Walk Strict Continuity Gate

Date: 2026-06-05

## Research Question

When a scheduled wake receives graph-walk context and the validation/repair
scaffold is enabled, can the model repair missing task evidence without
damaging continuity-critical state?

The prior scheduled walk validation/repair gate showed that DeepSeek could be
repaired into recording graph-walk evidence, but the validator accepted states
that drifted on adjacent continuity fields. This experiment asks whether that
was only a validator-contract defect or whether stricter continuity invariants
expose a deeper scaffold limitation.

## Hypotheses

- H168: A strict validator that checks graph evidence and continuity invariants
  will detect first-pass scheduled-wake failures.
- H169: At least one completed scheduled wake can be repaired into a state that
  satisfies both graph evidence and continuity invariants.
- H170: Every accepted final state preserves the preregistered continuity
  invariants: exact `probe_id`, present/correct `cycle`, baseline observation,
  and no disallowed deletion of `probe_id` or `cycle`.
- H171: The scaffold will not silently accept unrepaired strict-validation
  failures.
- H172: Strict repair remains bounded to at most one repair call per scheduled
  wake.

## Predictions

The expected outcome is mixed rather than uniformly positive. The scaffold
should still deliver the scheduled walk context and should still attempt
repairs, but stricter continuity validation may expose cases where a repair
restores graph evidence while failing to preserve the continuity contract.

If all strict repairs pass, the prior continuity drift was mostly a
validator-contract problem. If graph evidence passes but continuity fails, the
scaffold needs a stronger repair target or framework-owned continuity fields.
If strict validation fails without repair, the repair layer is insufficient for
this scheduled-wake boundary.

## Method

Use the same basic substrate as the previous scheduled walk validation/repair
gate:

- model: `deepseek/deepseek-v4-pro` through OpenRouter;
- replicates: 4;
- `max_tokens`: 2048;
- each replicate receives a behavior-seeded initialization cycle;
- each replicate schedules exactly one event with `requested_context` using
  `walk` from a projected fork-run graph record;
- the event runner delivers adjacent walk context to the scheduled wake;
- the validation/repair scaffold is enabled only for the scheduled wake.

The strict validator passes only when all task-evidence and continuity checks
pass.

Task-evidence checks:

- `walk_gate_status == "woke"`;
- `observed_walk_endpoint_count == 4`;
- `observed_walk_edge_types` includes `depends_on`, `branches_from`, and
  `composes_with`;
- `observations` contains a `scheduled_walk` entry.

Continuity checks:

- top-level `probe_id` exactly equals the seeded replicate `probe_id`;
- top-level `cycle` is present and equals the wake cycle;
- the seeded baseline observation is still present exactly;
- `deleted_regions` does not include `probe_id` or `cycle`.

The repair builder will provide a complete target object containing the exact
expected `probe_id`, expected wake `cycle`, baseline observation, and scheduled
walk observation. The repair result must still be produced by the model through
`think_and_respond`; the harness must not mutate state into validity.

## Falsification Criteria

- H168 is falsified if first-pass scheduled-wake failures are not detected when
  strict evidence or continuity fields are absent or drifted.
- H169 is falsified if no completed scheduled wake reaches strict-valid final
  state after repair.
- H170 is falsified if any accepted final state has evidence validity but
  continuity invalidity.
- H171 is falsified if a strict-invalid final state is reported as accepted
  without an unrepaired/failed validation status.
- H172 is falsified if any scheduled wake uses more than two backend calls
  total: one first pass plus one repair.

## Analysis Plan

Analyze evidence and continuity separately:

- first-pass status;
- repair-attempt status;
- final evidence validity;
- final continuity validity;
- exact continuity failure reasons;
- backend calls used by the scheduled wake;
- context delivery and context errors.

The primary result is not whether the experiment "succeeds" but whether the
strict contract distinguishes task-evidence recovery from continuity-preserving
identity state recovery.
