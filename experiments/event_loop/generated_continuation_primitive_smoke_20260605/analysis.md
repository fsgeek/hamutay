# Analysis: Generated Continuation Primitive Smoke

Date: 2026-06-05

## Result

The generated-continuation primitive smoke passed.

Implemented:

- `hamutay.events.build_bound_continuation_event`;
- focused unit tests for valid binding, placeholder expansion, no-op requests,
  and malformed-request rejection.

Validation:

- targeted event/taste slice: `99 passed`;
- full unit suite: `268 passed`.

Hypothesis outcomes:

- H401 passed.
- H402 passed.
- H403 passed.
- H404 passed.
- H405 passed.

## What Changed

The helper accepts:

- a completed event record with `wake_cycle` and `result_record_id`;
- a durable `continuation_request`.

If `continuation_request.requested` is not `true`, the helper returns `None`.
If it is true, the helper:

- expands `"<result_record_id>"` placeholders throughout JSON-safe fields;
- delegates event validation to `build_pending_event`;
- schedules the continuation by the completed wake cycle and generated result
  record ID;
- records binding metadata:
  - `bound_by: continuation_request`;
  - `bound_source_event_id`;
  - `bound_result_record_id`;
  - optional `continuation_kind`.

The helper is pure. It does not append to `EventStore` and does not alter
`run_next_event`.

## Interpretation

This captures the binding step used by the successful generated bound-chain
terminal-surface panel without promoting the entire runner into production
behavior. That is the right scope for this stage: the event loop now has a
validated substrate primitive for generated continuation, but policy remains
explicitly outside the helper.

The primitive also preserves the current observability posture. A continuation
event remains a normal pending event with extra binding metadata; lifecycle,
context delivery, terminal-surface metadata, and validation summaries continue
to flow through the existing event log.

## Design Implication

The next production slice can use this helper in a scheduler phase:

1. run an event;
2. inspect the committed durable state for a continuation request;
3. validate policy eligibility;
4. call `build_bound_continuation_event`;
5. append the returned event.

That should be tested separately because automatic append policy is behavior,
not merely a builder primitive.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
uv run pytest tests/unit -q
```

No live model calls were made for this smoke.
