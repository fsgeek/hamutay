# Analysis: Bounded Autonomous Work Minimal Harness

Date: 2026-06-05

## Result

Step 2 of `docs/bounded-autonomous-work-research-todo-20260605.md` is complete.

The harness dry-run passed all Step 2 evidence checks:

- valid_event_persistence: true
- no_harness_imposed_continuation_answer: true
- captured_policy_disposition: true
- bounded_continuation_budget: true
- artifact_submission_surface: true

## What Was Built

The runner is:

`experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/run_bounded_autonomous_work_minimal_harness.py`

It provides:

- a live-capable OpenAI-compatible runner;
- a default dry-run validation path that makes no model call;
- a terminal surface for `choose_bounded_autonomous_work`;
- a terminal surface for `submit_autonomous_work_artifact`;
- goal-selection fields required by the bounded-autonomy rubric;
- artifact submission fields;
- policy action fields for `stop_complete`, `continue_after`,
  `ask_external_evidence`, `abandon`, and `defer`;
- a continuation-request affordance using `<result_record_id>` binding;
- scheduler execution with `policy_dispositions=True`;
- scheduler execution with `max_auto_continuations=1`.

## Dry-Run Evidence

The dry-run path uses a deterministic backend to exercise the production
terminal-surface and scheduler plumbing without making a provider call.

Observed dry-run summary:

- event records: 5
- event count: 2
- lifecycle status counts: `completed=1`, `pending=1`
- policy disposition count: 1
- policy disposition counts: `continue_after=1`
- scheduler stop reason: `auto_continuation_limit_reached`
- auto continuations appended: 1

This proves the harness can persist the first event, execute it through a
terminal surface, capture a policy disposition, consume a fresh continuation
request, append a bound follow-up event, and stop at the bounded continuation
budget.

## Substrate Change

The event-store policy vocabulary was extended to accept `abandon` and `defer`,
with classifications:

- `abandon` -> `abandoned`
- `defer` -> `deferred`

This was needed because the bounded-autonomy rubric makes `abandon` distinct
from `stop_complete`, and the Step 2 terminal surface exposes both `abandon`
and `defer`.

## What This Does Not Prove

This is not a live model result. It does not show that a model can choose a
bounded investigation well, use evidence, or produce a useful artifact.

It validates the harness surface and scheduler path needed for the next live
panel.

## Verification

Commands run:

```bash
python -m py_compile src/hamutay/events.py tests/unit/test_events.py experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/run_bounded_autonomous_work_minimal_harness.py
uv run pytest tests/unit/test_events.py -q
uv run python experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/run_bounded_autonomous_work_minimal_harness.py
jq '{step2_requirements, policy_disposition_captured, event_counts: {records: .event_summary.record_count, events: .event_summary.event_count, dispositions: .event_summary.policy_disposition_count, counts: .event_summary.policy_disposition_counts, status: .event_summary.status_counts}, scheduler: {stop_reason: .scheduler_step.stop_reason, auto_continuations: .scheduler_step.batch.auto_continuation_count, limit_reached: .scheduler_step.batch.auto_continuation_limit_reached}}' experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/results.json
```

Results:

- py_compile passed.
- event unit suite: 73 passed.
- dry-run Step 2 requirements: all true.
