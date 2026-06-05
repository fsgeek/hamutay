# Pre-Registration: Live Normalized Scheduler Panel

Date: 2026-06-05

## Research Question

Do repaired-valid initialization rows behave downstream like first-pass-valid
initialization rows when both are emitted through the normalized scheduler
result envelope?

Previous slices showed that repaired initialization can enter the scheduler
pipeline and that the normalized envelope can be applied prospectively to
representative rows. This live panel tests the next boundary: whether the
first-pass-valid and repaired-valid populations remain comparable when scored
with the same envelope policy.

## Hypotheses

- H256: A live runner can emit raw results plus `result_envelope` at write time
  for first-pass-valid, repaired-valid, and failed/culled initialization
  classes.
- H257: First-pass-valid and repaired-valid initialization rows are both
  scheduler-score eligible under the envelope policy.
- H258: Failed/culled initialization is retained as data but excluded from
  scheduler-success scoring.
- H259: Repaired-valid initialization completes scheduled wake execution with
  event-level wake validation at the same qualitative level as first-pass-valid
  initialization.
- H260: Initialization provenance and wake validation provenance remain
  distinct in every eligible row.

## Method

Run a small live panel with DeepSeek v4 Pro:

1. first-pass-valid condition: run two replicates through the bounded
   initialization-repair scheduler gate;
2. repaired-valid condition: run two replicates from the preserved failed
   initialization source used by the repaired-initialization integration;
3. failed/culled sentinel: include the preserved failed initialization row from
   `live_event_wake_validation_scoring_20260605` as an initialization-only
   denominator sentinel, without scheduler scoring.

Every row must contain:

- `condition`;
- `raw_result`;
- `result_envelope`;
- condition-specific expected initialization class;
- condition-specific expected scheduler eligibility.

No existing experiment artifacts are modified. The runner may resume from
partially written `results.json` by skipping completed condition/replicate
pairs.

## Predictions

The first-pass-valid condition should usually complete scheduled wake execution
and then require wake repair, matching prior strict scheduler behavior.

The repaired-valid condition should also complete scheduled wake execution and
then require wake repair. If it does not, the difference is strong evidence
that repaired initialization is not behaviorally equivalent downstream even
when structurally valid.

The failed/culled sentinel should be ineligible and must not contribute to
scheduler-success denominators.

## Falsification Criteria

- H256 is falsified if any row lacks `raw_result` or `result_envelope`.
- H257 is falsified if either eligible condition produces envelope-ineligible
  rows after valid initialization.
- H258 is falsified if the failed sentinel is scheduler-score eligible.
- H259 is falsified if repaired-valid rows cannot complete scheduled wake
  execution or lack event-level wake validation while first-pass-valid rows do.
- H260 is falsified if initialization provenance cannot be distinguished from
  wake validation provenance in any eligible completed row.

## Analysis Plan

Report:

- rows by condition;
- initialization class by row;
- scheduler eligibility by row;
- event completion by eligible condition;
- wake validation source/status by eligible condition;
- first-pass wake validation and wake repair status;
- bounded-call violations;
- raw/envelope mismatch or missing-field failures.

Interpretation will be qualitative. This panel can justify or block a larger
equivalence experiment, but it is not powered as a final equivalence claim.
