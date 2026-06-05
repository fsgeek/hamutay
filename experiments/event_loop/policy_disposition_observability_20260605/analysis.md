# Analysis: Policy Disposition Observability

Date: 2026-06-05

## Result

The deterministic policy-disposition observability smoke passed.

Aggregate:

- event-log records: 13;
- lifecycle events: 4;
- lifecycle status counts: `completed=3`, `pending=1`;
- policy disposition records: 3;
- disposition counts:
  - `continue_after=1`;
  - `stop_complete=1`;
  - `ask_external_evidence=1`;
- lifecycle anomalies: 0.

Hypothesis outcomes:

- H521 passed.
- H522 passed.
- H523 passed.
- H524 passed.

## What Changed

The event sidecar now supports lifecycle-neutral `policy_disposition` records.
They are keyed to a completed source event through `source_event_id`, but they
do not become part of that event's lifecycle status history.

The scheduler can opt into automatic disposition capture with
`policy_dispositions=True`, parallel to the existing `auto_continuations=True`
path. When enabled, it reads only the fresh raw output from the completed wake.

Summaries now include:

- `policy_disposition_count`;
- `policy_disposition_counts`;
- recent `policy_dispositions`.

Rendered event reports now show policy disposition counts and recent
disposition records.

## Smoke Findings

The deterministic smoke created three completed wakes:

- `continue_after`;
- `stop_complete`;
- `ask_external_evidence`.

It appended one pending continuation for `continue_after`, then appended a
policy disposition for each completed wake.

The resulting report distinguished:

- ordinary lifecycle status: `completed=3`, `pending=1`;
- policy outcomes: `ask_external_evidence=1`, `continue_after=1`,
  `stop_complete=1`;
- evidence block classification with preserved missing evidence;
- continuation linkage from the `continue_after` disposition to the pending
  continuation event.

## Interpretation

This closes the substrate observability gap identified by the model-owned
policy-boundary panel. Continuation was already visible because it creates a
pending event. Now stop and evidence-block outcomes are visible as first-class
sidecar data instead of being inferred from accepted state.

The important design decision is that disposition records are companion records,
not lifecycle statuses. A wake can remain simply `completed`, while its policy
meaning is recorded separately. This avoids contaminating event lifecycle
semantics with control-loop interpretation.

## Caveats

This was deterministic and substrate-only. It does not show that a live model
will always emit useful policy decisions. That was tested separately in the
policy-boundary panel.

The automatic capture path currently records only recognized actions:
`continue_after`, `stop_complete`, and `ask_external_evidence`. If the policy
vocabulary expands, the event-store validation and summary expectations should
expand deliberately.

## Next Research Move

The next useful experiment is a live rerun of the policy-boundary panel with
`policy_dispositions=True`, verifying that the production scheduler captures
the same first-class dispositions from actual model output:

- continue branch should produce both a disposition and a pending continuation;
- stop branch should produce a completion disposition and no continuation;
- evidence branch should produce an evidence-block disposition with missing
  evidence and no continuation.

This would connect the live policy-selection result to the new substrate
observability layer.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py tests/unit/test_events.py
uv run pytest tests/unit/test_events.py -q
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
python -m py_compile experiments/event_loop/policy_disposition_observability_20260605/run_policy_disposition_observability.py
uv run python experiments/event_loop/policy_disposition_observability_20260605/run_policy_disposition_observability.py
jq '{hypothesis_results, summary: {record_count: .summary.record_count, event_count: .summary.event_count, status_counts: .summary.status_counts, policy_disposition_count: .summary.policy_disposition_count, policy_disposition_counts: .summary.policy_disposition_counts, lifecycle_anomalies: .summary.lifecycle_anomalies}, dispositions: [.summary.policy_dispositions[] | {policy_action, classification, source_event_id, continuation_event_id, continuation_kind, missing_evidence}]}' experiments/event_loop/policy_disposition_observability_20260605/results.json
```
