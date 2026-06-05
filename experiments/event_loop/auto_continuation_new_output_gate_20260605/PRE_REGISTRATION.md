# Pre-Registration: Auto-Continuation New-Output Gate

Date: 2026-06-05

## Research Question

Can the scheduler prevent inherited continuation requests from re-triggering
by honoring only continuation requests emitted in the just-completed raw
output?

The live generated-chain auto-continuation panel showed that the second wake
inherited the first wake's durable `continuation_request`. Because the
scheduler inspected merged state, the same request repeatedly appended new
second events until the step limit. This smoke tests a stricter consumption
invariant.

## Hypotheses

- H431: `OpenTasteSession` can expose the just-committed raw output without
  changing state merge behavior.
- H432: `run_next_event(..., auto_continuations=True)` appends a continuation
  when the just-emitted raw output contains `continuation_request`.
- H433: An inherited `continuation_request` in prior/merged durable state does
  not re-trigger if the current raw output omits it.
- H434: Malformed just-emitted continuation requests still fail explicitly.
- H435: Existing event/taste and unit tests remain green.

## Predictions

- A unit test with raw-output continuation request appends one pending event.
- A unit test with prior-state continuation request but current raw output
  lacking that key appends no event.
- The durable merged state may still contain the inherited request; the
  scheduler still does not honor it.
- Existing malformed-request behavior remains a failure.
- Targeted and unit test suites pass.

## Falsification Criteria

The repair is not supported if:

- raw-output exposure changes merge behavior or log contents;
- inherited continuation requests still trigger auto-append;
- malformed current requests are ignored;
- default scheduler behavior changes;
- existing unit tests regress.

## Method

Add `_last_raw_output` to `OpenTasteSession`, set it when a cycle commits, and
change `run_next_event` auto-continuation gating to inspect
`session._last_raw_output` instead of merged `after_state`.

No live model calls are required for this smoke.

## Analysis Plan

Report the targeted scheduler tests and full unit suite. Treat this as a
substrate repair smoke. A follow-up live panel should rerun the generated chain
auto-continuation task after this gate is in place.
