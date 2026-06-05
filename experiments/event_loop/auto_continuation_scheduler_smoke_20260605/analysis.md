# Analysis: Auto-Continuation Scheduler Smoke

Date: 2026-06-05

## Result

The auto-continuation scheduler smoke passed.

Implemented:

- `run_next_event(..., auto_continuations=False)`;
- `run_pending_events(..., auto_continuations=False)`;
- `step_pending_events(..., auto_continuations=False)`;
- opt-in scheduler use of `build_bound_continuation_event`;
- completed-event metadata for appended auto-continuations.

Validation:

- targeted event/taste slice: `102 passed`;
- full unit suite: `271 passed`.

Hypothesis outcomes:

- H411 passed.
- H412 passed.
- H413 passed.
- H414 passed.
- H415 passed.

## Behavior

Default scheduler behavior is unchanged. `auto_continuations` defaults to
`False`, and a completed wake that commits `continuation_request` does not
append a continuation unless the caller opts in.

When `auto_continuations=True`, `run_next_event`:

1. executes the current event normally;
2. inspects the committed durable state for top-level `continuation_request`;
3. calls `build_bound_continuation_event`;
4. appends the returned pending event if non-null;
5. marks the completed source event with:
   - `auto_continuation_appended: true`;
   - `auto_continuation_event_id`;
6. returns the appended event as `auto_continuation_event`.

Malformed requested continuations fail explicitly. The source event is marked
`failed`, and no continuation is appended.

## Interpretation

This turns the successful generated bound-chain runner pattern into a reusable
scheduler phase without making it default behavior. That matters because policy
selection remains a research variable. A caller can now choose whether a
scheduler step should honor durable continuation requests, while default
event-loop behavior remains stable.

The integration keeps generated continuation as substrate-owned binding:

- the model commits a request;
- the substrate binds to the actual generated `result_record_id`;
- normal pending-event validation still applies;
- lifecycle observability remains in the event log.

## Design Implication

The event loop now has the minimal pieces for bounded generated continuity:

- narrow terminal surfaces for bounded wakes;
- generated record-ID binding via `build_bound_continuation_event`;
- opt-in automatic append via scheduler phase.

The next live-model question is whether the generated bound-chain panel still
passes when the runner no longer manually appends the second event and instead
uses `step_pending_events(..., auto_continuations=True)`.

## Remaining Cautions

This smoke used unit fixtures, not live model calls. It proves scheduler
behavior and regression resistance, not model reliability. It also does not
decide when auto-continuation should be enabled in production; that remains a
policy question.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
uv run pytest tests/unit -q
```

No live model calls were made for this smoke.
