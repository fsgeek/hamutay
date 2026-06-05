# Validation Repair Scaffold Analysis

Date: 2026-06-05

## Result

The opt-in validation/repair scaffold was implemented and validated with
deterministic fake backends.

- H153 default sessions are behavior-preserving: passed.
- H154 first-pass valid state is logged as validated without repair: passed.
- H155 repair success is model-authored and auditable: passed.
- H156 repair failure does not silently pass: passed.
- H157 repair is bounded: passed.

## Implementation

`OpenTasteSession` now accepts two optional hooks:

- `state_validator`
- `state_repair_builder`

When no validator is supplied, the exchange path does not emit
`state_validation` metadata and does not add repair token fields to the usage
object.

When a validator is supplied, the scaffold validates the candidate state after
normal `_apply_updates` and tool-activity folding. If the state is valid, the
cycle logs a `state_validation` artifact with `repair_attempted: false`.

If the state is invalid and a repair builder is supplied, the session runs one
additional backend call with only `think_and_respond`, applies the repair
response through `_apply_updates`, validates again, and logs:

- first-pass validation result;
- repair raw output;
- repair usage;
- repair validation result;
- final status: `repaired`, `unrepaired`, or `repair_failed`.

The harness never fills missing durable fields itself. State changes only when
the model authors fields in first-pass or repair output.

## Test Evidence

Focused tests cover five cases:

1. No validator: default log shape has no `state_validation` metadata.
2. First-pass valid state: validation logs `status == "valid"` and no repair is
   attempted.
3. Invalid first pass, valid repair: one repair call occurs, the final state is
   model-authored repaired state, and usage includes repair tokens.
4. Invalid first pass, invalid repair: one repair call occurs, final artifact is
   `unrepaired`, and no recursive repair is attempted.
5. Validator failure: validation failure is logged and does not trigger repair.

## Interpretation

This moves the repair work from ad hoc experiment-runner convention into the
event-loop scaffold while preserving the key invariant: no hidden state
mutation. The scaffold distinguishes:

- clean first-pass success;
- repaired success;
- unrepaired prose/object mismatch;
- repair execution failure.

That distinction is now available to future live experiments without changing
the model-facing protocol globally.

## Design Implication

Future event-loop experiments can attach task-specific validators and repair
builders instead of hand-scoring prose/object mismatch in each runner. This is
especially important for scheduled wakes, because a wake can now declare that
it received evidence, fail to persist it, and be repaired or marked unrepaired
inside the same auditable cycle.

The next live research step should use this scaffold with a graph-walk
validator and a full-target repair builder, then compare:

- no validator;
- validator only;
- validator plus repair.

That would test whether the scaffold improves continuity outcomes under the
same model/provider conditions without losing the first-pass failure signal.

## Limitations

This scaffold experiment used deterministic fake backends. It proves harness
semantics, not live model behavior. The next experiment should exercise the
new hooks against a live model using the graph-evidence task that produced the
original mismatch.

The current implementation intentionally supports one repair attempt per
exchange. That bound is a feature for research auditability, not a claim that
one repair attempt is optimal.

## Verification

Commands run:

```bash
uv run python -m py_compile src/hamutay/taste_open.py tests/test_taste_open.py
uv run pytest tests/test_taste_open.py::TestStateValidationRepairScaffold -q
uv run pytest tests/unit tests/test_taste_open.py -q
```

Results:

- py_compile passed.
- focused scaffold tests: 5 passed.
- broad regression suite: 283 passed.
