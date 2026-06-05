# Identity Merge Failure Capture Analysis

Filed: 2026-06-05 after implementing and validating the observability slice.

## Artifacts

- preregistration: `PRE_REGISTRATION.md`
- implementation: `src/hamutay/taste_open.py`
- regression test: `tests/test_taste_open.py::TestExchangeCycleRollback::test_merge_failure_is_logged_without_advancing_state`

## Validation

- `uv run pytest tests/test_taste_open.py::TestExchangeCycleRollback`: pass
- `uv run python -m py_compile src/hamutay/taste_open.py tests/test_taste_open.py`: pass
- `uv run pytest tests/test_taste_open.py tests/unit/test_events.py tests/unit/test_exchange_tools.py tests/unit/test_continuity_curator.py`: pass
- `git diff --check -- src/hamutay/taste_open.py tests/test_taste_open.py`: pass

## Result

The observability slice passed.

A fake backend response with `deleted_regions` overlapping a top-level update
now produces a durable JSONL failure record before `exchange()` re-raises the
strict merge exception.

The captured failure record includes:

- raw model output;
- prior state;
- usage;
- `status: "failed"`;
- `failure_classification.failure_stage: "state_merge"`;
- error type and message;
- deleted keys;
- updated keys;
- overlap keys.

The failed cycle does not mutate state. The next successful exchange reuses
the same cycle number, and successful log records remain compatible with
existing behavior.

## Hypothesis Assessment

### H49: Merge Failures Can Be Captured Without Accepting Them

Supported by the deterministic regression test.

The failed raw output was logged, the overlap key was recorded, and
`exchange()` still raised `ValueError`.

### H50: Failure Capture Does Not Advance Durable State

Supported by the deterministic regression test.

After the failed exchange:

- `session.cycle` rolled back to 0;
- `session.state` remained `None`;
- no continuity curation record was written;
- no scheduled events were committed;
- the next successful exchange wrote cycle 1.

### H51: Successful Cycle Logs Are Unchanged

Supported by regression coverage.

The broader taste_open, event, exchange-tool, and continuity-curator tests all
passed.

## Interpretation

This removes an observability blind spot but does not resolve merge policy.

The substrate can now preserve the failed payloads needed for later replay or
normalizer experiments. That means future delete-plus-update studies should no
longer be limited to exception messages; they can inspect the actual raw
structured object that failed merge.

Strict rejection remains unchanged. The framework still refuses to let a model
delete and update the same top-level key in the same successful cycle.

## Design Implications

1. Merge failure records are now first-class protocol data.

2. The event-loop substrate can proceed with strict merge semantics while
   preserving enough data to evaluate alternative merge policies later.

3. Future normalizer experiments should use captured failure records and
   replay candidate policies offline before any live leniency is introduced.

4. Scheduler experiments remain safer with this change because failed wake
   cycles can now leave diagnostic records rather than disappearing at the
   merge boundary.
