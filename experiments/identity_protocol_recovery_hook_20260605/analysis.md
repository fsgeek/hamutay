# Identity Protocol Recovery Hook Analysis

Filed: 2026-06-05 after implementing and validating the optional
`OpenTasteSession` protocol-recovery hook.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- implementation: `src/hamutay/taste_open.py`
- regression tests:
  - `tests/test_taste_open.py::TestExchangeCycleRollback::test_protocol_recovery_hook_logs_candidate_artifact`
  - `tests/test_taste_open.py::TestExchangeCycleRollback::test_protocol_recovery_hook_failure_is_logged_without_masking`

## Validation

- `uv run pytest tests/test_taste_open.py::TestExchangeCycleRollback`: pass
- `uv run python -m py_compile src/hamutay/taste_open.py tests/test_taste_open.py`: pass
- `uv run pytest tests/test_taste_open.py tests/unit/test_events.py tests/unit/test_exchange_tools.py tests/unit/test_continuity_curator.py`: pass
- `git diff --check -- src/hamutay/taste_open.py tests/test_taste_open.py`: pass

## Result

The protocol-recovery hook passed the deterministic validation slice.

`OpenTasteSession` now accepts an optional `protocol_recovery_builder`.
When strict state merge fails, the session:

- builds the existing `failure_classification`;
- invokes the recovery builder if configured;
- logs `protocol_recovery` into the failed JSONL record;
- leaves working state unchanged;
- does not run continuity curation;
- does not commit scheduled events;
- re-raises the original strict merge exception.

If the recovery builder itself fails, that failure is logged as
`protocol_recovery.status: "failed"` and does not mask the original merge
error.

## Hypothesis Assessment

### H59: Recovery Hook Runs On Merge Failure

Supported.

The successful fake recovery builder was invoked on merge failure and the
failed JSONL record contained `protocol_recovery.status: "success"` with a
candidate artifact.

### H60: Recovery Hook Does Not Accept State

Supported.

The failed exchange still raised, the cycle rolled back, accepted state stayed
unchanged, and the next successful exchange reused cycle 1.

### H61: Recovery Hook Failure Is Data

Supported.

A failing fake recovery builder produced a logged
`protocol_recovery.status: "failed"` artifact with `RuntimeError: repair boom`,
while the exchange still raised the original strict merge `ValueError`.

## Interpretation

This gives the event-loop substrate the side channel it needs.

Merge failure is still a failed cycle. The difference is that failed cycles can
now carry candidate repair artifacts alongside the raw failed output and
failure classification. That separates observability from state admission:
capture and repair can happen without silently accepting ambiguous model
output.

## Design Implications

1. Protocol recovery is now a first-class optional hook, analogous to
   continuity curation but invoked only after strict protocol failure.

2. The default live merge policy remains strict rejection.

3. A deterministic or model-backed recovery builder can now be tested without
   altering successful-cycle state semantics.

4. Scheduler experiments can use this hook to preserve diagnostic continuity
   when a wake cycle fails at merge time.

## Next Research Move

The next implementation slice should provide a reusable deterministic recovery
builder in `src/hamutay`, based on the extractor tested in
`identity_merge_repair_artifact_20260605`, and wire it into experiment runners
only. The default interactive `taste_open` path should continue without an
automatic repair builder until the artifact semantics have more data behind
them.
