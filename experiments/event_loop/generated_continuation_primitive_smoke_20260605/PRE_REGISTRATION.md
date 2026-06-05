# Pre-Registration: Generated Continuation Primitive Smoke

Date: 2026-06-05

## Research Question

Can the runner-mediated generated-continuation binding pattern be captured as a
small reusable scheduler primitive without changing event semantics?

The generated bound-chain terminal-surface panel succeeded because the runner
read a valid first-wake `continuation_request`, bound a second event to the
first wake's actual `result_record_id`, and executed that second event. This
experiment promotes only that binding step into substrate code.

## Hypotheses

- H401: A completed event plus a valid durable `continuation_request` can build
  a pending continuation event.
- H402: The continuation event is scheduled by the completed wake cycle and
  completed wake `result_record_id`.
- H403: Placeholder expansion can bind requested context and terminal-surface
  literals to the generated result record ID.
- H404: Malformed continuation requests fail explicitly instead of silently
  producing events.
- H405: Existing scheduled-event behavior and terminal-surface tests remain
  unchanged.

## Predictions

- Unit tests can build a bound continuation event from a synthetic completed
  event and continuation request.
- The generated event contains `bound_by`, `bound_source_event_id`, and
  `bound_result_record_id` metadata.
- `requested_context` supports `"<result_record_id>"` placeholder expansion.
- `terminal_surface.state_update.set` supports the same placeholder expansion.
- Missing purpose, missing requested context, malformed context, or missing
  completed-event result record raises a clear exception.
- Existing event tests still pass.

## Falsification Criteria

The primitive is not supported if:

- it requires changing existing `run_next_event` lifecycle behavior;
- it silently accepts malformed continuation requests;
- it cannot preserve normal `build_pending_event` validation;
- placeholder expansion corrupts terminal-surface schemas;
- existing event or taste-open tests regress.

## Method

Add a pure helper to `hamutay.events`:

- it accepts a completed event record and a durable `continuation_request`;
- it expands `"<result_record_id>"` placeholders in JSON-safe continuation
  fields;
- it delegates validation to `build_pending_event`;
- it returns a pending event record with binding metadata;
- it does not append to `EventStore` and does not alter `run_next_event`.

Then add focused unit tests and run the targeted event/taste-open test suite.

## Analysis Plan

This is an engineering smoke, not a live-model panel. Report whether the helper
preserves existing tests and whether the new unit tests cover valid binding,
placeholder expansion, no-op requests, and explicit malformed-request failure.
