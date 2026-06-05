# Validation Repair Scaffold Pre-Registration

Date: 2026-06-05

## Research Question

Can the event-loop harness support opt-in durable-state validation and bounded
repair while preserving the core invariant that the harness never mutates state
on behalf of the model?

Recent DeepSeek repair experiments showed that prose/object mismatches are
recoverable only under sufficiently explicit output-shape scaffolding. The next
research move is to turn that boundary into an auditable harness feature:
first-pass success, repaired success, and unrepaired prose/object mismatch must
be distinct states in the data.

## Hypotheses

### H153: Default sessions are behavior-preserving

Adding the scaffold must not change `OpenTasteSession` behavior unless a
validator is explicitly supplied.

Falsification condition: existing focused tests fail or a session without a
validator emits validation/repair metadata.

### H154: First-pass valid state is logged as validated without repair

When a validator accepts the model-authored state after the first response, the
cycle should complete normally and log a validation artifact showing no repair
attempt.

Falsification condition: accepted first-pass state is repaired, rejected, or
not logged as validated.

### H155: Repair success is model-authored and auditable

When first-pass state fails validation and a repair builder is supplied, the
session should run one repair prompt. If the repair response authors a valid
durable state, the final state should be the repaired model-authored state and
the log should preserve both the first-pass failure and the repair success.

Falsification condition: the harness mutates missing fields itself, drops the
first-pass raw output, or fails to distinguish repaired success from first-pass
success.

### H156: Repair failure does not silently pass

When first-pass state fails validation and the repair response still fails
validation, the cycle should log an unrepaired validation artifact. The final
state may remain the model-authored failed state for continuity, but it must be
marked as unrepaired.

Falsification condition: unrepaired prose/object mismatch is logged as clean
success or lacks explicit validation failure metadata.

### H157: Repair is bounded

The scaffold should attempt at most one repair cycle per exchange.

Falsification condition: a failed repair can trigger unbounded recursive repair
or more than one repair attempt.

## Experimental Design

Implement a narrow opt-in scaffold in `OpenTasteSession`:

- `state_validator`: callable object that validates candidate durable state and
  returns structured pass/fail metadata.
- `state_repair_builder`: callable object that builds a repair prompt from the
  first-pass failure, prior state, raw output, response text, and candidate
  state.

The scaffold should:

1. Run only when `state_validator` is supplied.
2. Validate the candidate state produced by `_apply_updates`.
3. If valid, continue as normal and log validation metadata.
4. If invalid and no repair builder is supplied, continue with the
   model-authored state but log the validation failure as unrepaired.
5. If invalid and a repair builder is supplied, run exactly one additional
   backend call using the repair prompt.
6. Apply only the repair response's authored fields through `_apply_updates`.
7. Validate the repaired state.
8. Log the full validation artifact, including first-pass and repair raw
   outputs.

No live provider calls are required for this scaffold experiment. The behavior
will be tested with deterministic fake backends.

## Expected Result

Expected before implementation:

- The scaffold should be implementable without changing default session
  behavior.
- Fake backend tests should prove first-pass success, repaired success, and
  unrepaired failure.
- The feature should make the next live event-loop experiments cleaner because
  repair outcome becomes an explicit artifact rather than an external runner
  convention.

## Evaluation Artifacts

- code changes under `src/hamutay`
- focused tests under `tests/`
- `analysis.md`
