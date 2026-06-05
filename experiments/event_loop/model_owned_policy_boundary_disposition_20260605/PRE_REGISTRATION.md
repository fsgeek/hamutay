# Model-Owned Policy Boundary Disposition Capture Pre-registration

Date: 2026-06-05

## Research Question

Can the production scheduler capture live model-owned policy choices as
first-class `policy_disposition` sidecar records while preserving the behavior
observed in the model-owned policy-boundary panel?

This reruns the prior live boundary panel with `policy_dispositions=True`. The
new question is observability fidelity, not whether the model can choose the
right policy action from scratch.

## Motivation

The previous live panel showed that Deepseek could choose:

- `continue_after` for a deferred exact-phrase task;
- `stop_complete` for a task already complete from context;
- `ask_external_evidence` for a task blocked on missing source evidence.

The deterministic policy-disposition smoke then showed that the event sidecar
can represent those choices as lifecycle-neutral records. This panel connects
the two: actual model output should become explicit scheduler data.

## Hypotheses

### H531: live first-wake choices produce disposition records

Every first wake will append exactly one `policy_disposition` record whose
`policy_action` matches the model's accepted `policy_decision.action`.

Falsification: any first wake lacks a disposition, records the wrong action, or
emits multiple first-wake dispositions.

### H532: continue disposition links to continuation event

For `continue_required`, the `continue_after` disposition will include the
auto-appended continuation event ID and continuation kind, and the continuation
branch will still complete.

Falsification: the disposition lacks the continuation link, points to the wrong
event, or the continuation branch no longer completes.

### H533: non-continuation dispositions remain terminal without follow-up

For `stop_ready` and `evidence_missing`, dispositions will classify the first
wake as `complete` and `evidence_blocked` respectively, no continuation event
will be appended, and the scheduler will quiesce.

Falsification: either branch appends a continuation, lacks the expected
classification, or leaves runnable pending work.

### H534: evidence disposition preserves missing evidence

For `evidence_missing`, the disposition record will preserve a non-empty
`missing_evidence` list from live model output.

Falsification: the evidence-block disposition has no missing evidence or only a
prose rationale.

### H535: lifecycle summaries remain clean

Policy dispositions will not pollute lifecycle status counts or introduce
lifecycle anomalies.

Falsification: disposition records are counted as event statuses, lifecycle
anomalies appear because of disposition records, or event counts no longer
reflect only lifecycle events.

## Conditions

Same conditions as `model_owned_policy_boundary_20260605`:

1. `continue_required`
2. `stop_ready`
3. `evidence_missing`

Replicates: 2 per condition.

Model: `deepseek/deepseek-v4-pro`.

Scheduler change: all `step_pending_events` calls use
`policy_dispositions=True`.

## Primary Measures

- first-wake disposition count per row
- disposition action versus accepted `policy_decision.action`
- disposition classification
- disposition continuation event ID and kind
- disposition missing evidence list
- lifecycle status counts
- lifecycle anomaly count
- original policy-boundary hypothesis outcomes

## Expected Results

I expect the original policy-boundary hypotheses to remain true and the new
disposition-capture hypotheses to pass. The most likely failure is H534 if the
live model uses a prose rationale for missing evidence but does not fill the
structured `missing_evidence` field.
