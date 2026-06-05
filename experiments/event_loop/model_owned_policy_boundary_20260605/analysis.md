# Analysis: Model-Owned Policy Boundary

Date: 2026-06-05

## Result

The model-owned policy-boundary panel passed.

Aggregate:

- rows: 6;
- conditions: `continue_required`, `stop_ready`, `evidence_missing`;
- replicates per condition: 2;
- correct first-wake policy action: 6/6;
- first wakes strict-valid: 6/6;
- first wakes first-pass valid: 6/6;
- repairs: 0/6;
- bounded call violations: 0/6;
- errors: 0/6.

Condition results:

- `continue_required`: 2/2 chose `continue_after`, emitted a scheduler-valid
  continuation request, appended a bound follow-up, completed the follow-up,
  recovered the phrase, used the generated `policy_result`, and quiesced.
- `stop_ready`: 2/2 chose `stop_complete`, requested no continuation, appended
  no follow-up, and quiesced.
- `evidence_missing`: 2/2 chose `ask_external_evidence`, requested no
  continuation, appended no follow-up, and quiesced.

Hypothesis outcomes:

- H511 passed.
- H512 passed.
- H513 passed.
- H514 passed.

## Row-Level Notes

`continue_required`:

- r1 first record: `0ca5b74b-b85d-4910-bb93-449cb424da4a`;
- r2 first record: `4d5558e7-6ac5-4a54-a4fd-99ff833179cc`;
- both follow-up events were bound to the matching first record;
- both step-1 runs stopped at `auto_continuation_limit_reached` after one
  appended continuation;
- both follow-up runs completed and then quiesced.

`stop_ready`:

- both rows selected `stop_complete`;
- both emitted `continuation_request.requested == false`;
- no follow-up events were appended;
- all scheduler steps quiesced.

`evidence_missing`:

- both rows selected `ask_external_evidence`;
- both emitted `continuation_request.requested == false`;
- both identified the absent external confirmation source;
- no follow-up events were appended;
- all scheduler steps quiesced.

## Interpretation

This is a stronger result than the prior model-owned continuation-policy panel.
The previous panel proved the model could carry a complete continuation request
when the prompt effectively named the desired action. This panel gave the same
action vocabulary across matched conditions and asked the model to choose from
task structure.

The surprising part is the evidence branch. I expected at least one failure
where the model would keep thinking instead of asking for evidence. It did not:
both rows said another wake with the same context would not add the missing
source, selected `ask_external_evidence`, and declined continuation.

That matters for the event-loop design because it suggests the policy action
vocabulary is usable:

- continuation is for useful deferred work;
- stop is for available completion;
- evidence request is for missing source context, not more local thinking.

## Caveats

This is still a small single-model panel. It is not a broad model reliability
claim.

The prompts remain structured and explicit about the difference between the
three task situations. The panel does not prove open-ended autonomy; it shows
that, under a closed terminal surface and bounded task framing, Deepseek can
map task structure to the intended scheduler policy action.

The first-wake terminal surface still includes a `continuation_request` object
for every condition. That is useful for protocol uniformity, but future panels
should test whether a cleaner action-specific surface improves or harms policy
discrimination.

## Design Implication

The event loop now has evidence for three necessary pieces:

1. Generated continuations can be emitted by the model and bound by the
   scheduler.
2. The model can stop after a bounded continuation rather than loop.
3. The model can decline continuation when the correct action is either
   completion or external-evidence request.

This makes policy disposition the next useful substrate target. The scheduler
currently observes these choices, but it does not yet have first-class
disposition records for `stop_complete` or `ask_external_evidence` comparable
to appended continuation events.

## Next Research Move

The next small falsification experiment should add observability for
non-continuation dispositions:

- when a wake chooses `stop_complete`, append a sidecar disposition record;
- when a wake chooses `ask_external_evidence`, append a sidecar blocked/evidence
  request record;
- verify that pending/runnable counts and event summaries distinguish
  completion, evidence-block, and ordinary idle.

This would make the scheduler less dependent on inspecting raw state after the
fact and more like an operating loop with explicit terminal outcomes.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/model_owned_policy_boundary_20260605/run_model_owned_policy_boundary.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 2400s uv run python experiments/event_loop/model_owned_policy_boundary_20260605/run_model_owned_policy_boundary.py
jq '{summary: .summary, rows: [.results[] | {condition, replicate, error, expected_policy_action, policy_action, continuation_requested, continuation_request_kind, continuation_request_scheduler_valid, followup_event_appended, followup_event_bound_result_record_id, first_wake_result_record_id, step1_stop_reason, step1_auto_continuations, step2_stop_reason, step2_auto_continuations, step3_stop_reason, first_failures: .first_wake_failures, followup_failures: .followup_wake_failures}]}' experiments/event_loop/model_owned_policy_boundary_20260605/results.json
jq -r '.results[] | [.condition, (.replicate|tostring), .policy_action, (.continuation_requested|tostring), (.first_wake_first_pass_valid|tostring), (.first_wake_failures | join(";"))] | @tsv' experiments/event_loop/model_owned_policy_boundary_20260605/results.json
```
