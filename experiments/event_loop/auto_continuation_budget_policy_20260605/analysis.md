# Analysis: Auto-Continuation Budget Policy

Date: 2026-06-05

## Result

The auto-continuation budget policy smoke passed.

Implemented:

- `run_pending_events(..., max_auto_continuations=None)`;
- `step_pending_events(..., max_auto_continuations=None)`;
- batch observability:
  - `auto_continuation_count`;
  - `max_auto_continuations`;
  - `auto_continuation_limit_reached`;
- step stop reason `auto_continuation_limit_reached`.

Validation:

- targeted event/taste slice: `105 passed`;
- full unit suite: `274 passed`.

Hypothesis outcomes:

- H451 passed.
- H452 passed.
- H453 passed.
- H454 passed.
- H455 passed.

## Behavior

Default behavior remains unchanged because `max_auto_continuations` defaults to
`None`.

When a budget is set, the scheduler:

1. runs an event normally;
2. appends an auto-continuation if the event emits one;
3. increments the continuation counter;
4. stops the batch if the counter reaches the budget;
5. leaves the appended continuation pending for a later step;
6. reports `stop_reason: auto_continuation_limit_reached`.

The budget does not suppress or corrupt the continuation event. It controls
how much continuation-driven work a scheduler step performs.

## Interpretation

This adds a policy signal the generic wake `limit` could not provide. A long
or pathological continuation chain can now be distinguished from ordinary
queued work. That is important for observability: continuation growth is a
different scheduler phenomenon than simply having many independent pending
events.

The result also preserves the bounded-autonomy direction. An instance can emit
fresh continuation requests, but the substrate can decide how many to run in
one scheduling slice.

## Design Implication

The event loop now has three useful controls:

- `limit`: total terminalized events per step;
- `auto_continuations`: whether to honor fresh continuation requests;
- `max_auto_continuations`: how many auto-continuation appends one step may
  chase.

The next live question is whether a deliberate longer chain can be split across
multiple scheduler steps by this budget while preserving context and final
validity.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
uv run pytest tests/unit -q
```

No live model calls were made for this smoke.
