# Policy Disposition Observability Pre-registration

Date: 2026-06-05

## Research Question

Can the Hamut'ay event-loop sidecar represent model policy choices as
first-class append-only disposition records, so `continue_after`,
`stop_complete`, and `ask_external_evidence` are observable without reverse
engineering the accepted state?

This is a deterministic substrate question. It follows the live
model-owned policy-boundary panel, where Deepseek chose the correct action in
all six rows. The remaining gap is observability: continuation already becomes
a pending event, while stop/evidence outcomes are currently inferred from
terminal-surface raw state.

## Motivation

An operating loop needs explicit terminal outcomes. If a wake chooses
`stop_complete`, the sidecar should record that completion policy. If a wake
chooses `ask_external_evidence`, the sidecar should record the evidence-block
instead of leaving the scheduler merely idle. If a wake chooses
`continue_after`, the sidecar should connect the policy choice to the appended
continuation event.

This keeps the most valuable research output, the event data, faithful to the
control-loop decision rather than forcing later analysis to rediscover it from
JSON state.

## Hypotheses

### H521: policy disposition records are append-only and lifecycle-neutral

Given completed wake records with policy actions, the sidecar will append
`policy_disposition` records keyed by the completed event ID without changing
the event's lifecycle status.

Falsification: appending a disposition changes a completed event status,
creates lifecycle anomalies, or cannot be associated with the completed event.

### H522: summaries distinguish continue, stop, and evidence-block

`summarize_event_log` will report disposition counts and recent disposition
records for `continue_after`, `stop_complete`, and `ask_external_evidence`.

Falsification: summaries omit disposition records, collapse the three actions
into ordinary idle, or count them as event lifecycle statuses.

### H523: continuation disposition links to appended continuation event

For a `continue_after` wake, the disposition record will include the appended
continuation event ID and continuation kind when available.

Falsification: the disposition cannot link the completed wake to the appended
continuation event.

### H524: evidence-block disposition preserves missing evidence

For an `ask_external_evidence` wake, the disposition record will preserve the
missing evidence list and classify the wake as evidence-blocked.

Falsification: missing evidence is lost, flattened into prose only, or omitted
from the event summary.

## Conditions

This experiment uses deterministic event-store records, not a live provider.

Conditions:

1. `continue_after`
   - Completed event has a policy decision of `continue_after`.
   - A continuation event has been appended.
   - Disposition should link to that continuation.

2. `stop_complete`
   - Completed event has a policy decision of `stop_complete`.
   - No continuation event is appended.
   - Disposition should mark the event complete by policy.

3. `ask_external_evidence`
   - Completed event has a policy decision of `ask_external_evidence`.
   - No continuation event is appended.
   - Disposition should preserve the missing evidence list.

## Primary Measures

- event lifecycle status counts
- policy disposition counts by action
- recent policy disposition records
- linkage from completed event ID to disposition record
- linkage from continue disposition to continuation event ID
- preservation of missing evidence values
- lifecycle anomaly count

## Expected Results

I expect all hypotheses to pass with a small event-store extension. If they do
not, the failure should reveal whether disposition belongs inside completed
records, as separate sidecar records, or in a higher-level scheduler report.
