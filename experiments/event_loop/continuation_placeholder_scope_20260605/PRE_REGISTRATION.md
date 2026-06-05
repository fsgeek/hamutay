# Pre-Registration: Continuation Placeholder Scope

Date: 2026-06-05

## Research Question

Can placeholder expansion bind the event currently being built without
prematurely binding nested future continuation requests?

The budgeted three-wake chain failed because `<result_record_id>` expansion was
recursive. When the first wake appended the bridge event, expansion reached
inside the bridge terminal surface's nested future `continuation_request`,
binding the final wake to the first record instead of the bridge record.

## Hypotheses

- H471: Top-level continuation fields still expand `<result_record_id>`.
- H472: Terminal-surface state updates still expand ordinary bound fields.
- H473: Nested `continuation_request` values are not expanded when building
  the current event.
- H474: A later call to `build_bound_continuation_event` can expand the
  preserved nested placeholders against the later result record.
- H475: Existing event/taste and unit tests remain green.

## Predictions

- A unit test can build a bridge event where:
  - requested context is bound to the first result record;
  - `terminal_surface.state_update.set.bound_first_record_id_used` is bound to
    the first result record;
  - `terminal_surface.state_update.set.continuation_request.requested_context`
    still contains `<result_record_id>`.
- A second unit step can pass that nested continuation request to
  `build_bound_continuation_event` with a bridge result record and observe that
  it binds to the bridge result record.
- Existing tests pass.

## Falsification Criteria

The repair is not supported if:

- top-level binding stops working;
- ordinary terminal-surface bound fields stop expanding;
- nested future continuation placeholders are still expanded too early;
- later expansion of preserved nested placeholders fails;
- existing unit tests regress.

## Method

Change placeholder expansion to skip values under a `continuation_request` key
when expanding the current event. This preserves nested future templates while
still allowing the top-level request being built to bind normally.

No live model calls are required for this smoke.

## Analysis Plan

Report focused unit evidence and full unit-suite evidence. A follow-up live
panel should rerun the budgeted three-wake chain with closed non-secret
schemas.
