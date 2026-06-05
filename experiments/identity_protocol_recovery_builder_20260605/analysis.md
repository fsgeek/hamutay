# Identity Protocol Recovery Builder Analysis

Filed: 2026-06-05 after implementing and validating the reusable deterministic
protocol-recovery builder.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- implementation: `src/hamutay/protocol_recovery.py`
- tests: `tests/unit/test_protocol_recovery.py`

## Validation

- `uv run pytest tests/unit/test_protocol_recovery.py`: pass
- `uv run python -m py_compile src/hamutay/protocol_recovery.py tests/unit/test_protocol_recovery.py`: pass
- `uv run pytest tests/test_taste_open.py tests/unit/test_protocol_recovery.py tests/unit/test_events.py tests/unit/test_exchange_tools.py tests/unit/test_continuity_curator.py`: pass
- `git diff --check -- src/hamutay/protocol_recovery.py tests/unit/test_protocol_recovery.py`: pass

## Result

The reusable deterministic protocol-recovery builder passed validation.

`DeterministicProtocolRecoveryBuilder` now provides a small reusable
`recover(...)` implementation matching the `OpenTasteSession` hook protocol.
It extracts candidate rows from failed visible responses using deterministic
section parsing and flags unsupported budget/cost details as contamination
warnings.

The builder never produces accepted state:

- `accepted_state: null`
- `live_policy: "strict_reject"`
- all extracted rows are `status: "candidate"`
- all extracted rows have `accepted: false`

## Hypothesis Assessment

### H62: Reusable Builder Preserves Repair Contract

Supported.

The direct unit test recovered:

- 2 invalidated-assumption rows;
- 3 constraint rows;
- 2 goal rows;
- 2 next-action rows;
- at least 1 contamination warning;
- no accepted state.

### H63: Reusable Builder Integrates With Hook

Supported.

A fake-backend `OpenTasteSession` using the reusable builder logged
`protocol_recovery.status: "success"` on strict merge failure. The failed
cycle did not mutate accepted state and the next successful exchange reused
cycle 1.

### H64: Default Interactive Behavior Is Unchanged

Supported by regression coverage.

The builder is not installed by default. Existing taste_open, event,
exchange-tool, and continuity-curator tests passed.

## Interpretation

The substrate now has a complete strict-failure side channel:

1. capture failed raw output;
2. classify merge failure;
3. optionally build deterministic candidate repair artifacts;
4. keep accepted state unchanged.

This is the right staging point before scheduler experiments. It reduces data
loss from failed wake cycles without normalizing ambiguous state.

## Design Implications

1. Experiment runners can now inject `DeterministicProtocolRecoveryBuilder`
   when studying scheduler or continuity behavior.

2. The default interactive path should remain without an automatic recovery
   builder until more repair artifacts have been evaluated.

3. Future adjudication experiments can consume protocol-recovery artifacts
   instead of raw failed responses.

4. This makes event-loop observability more robust: failed cycles can now
   produce structured side-channel data without becoming successful cycles.

## Next Research Move

The next useful step is a minimal scheduled re-entry experiment that enables:

- claim-table guardrail continuity;
- strict merge failure capture;
- deterministic protocol recovery builder;
- event sidecar logging.

The falsification question should be:

> Can a scheduled wake cycle leave enough continuity and protocol-recovery data
> to diagnose success or failure without rebriefing, even when the wake fails
> strict merge?

That returns to the original event-loop scheduler path with the observability
substrate now stronger than when we left it.
