# Analysis: Model-Owned Continuation Policy

Date: 2026-06-05

## Result

The model-owned continuation policy panel passed.

Aggregate:

- rows: 2;
- first wake strict-valid: 2/2;
- first wake first-pass valid: 2/2;
- first wake chose `continue_after`: 2/2;
- first wake emitted scheduler-valid continuation request: 2/2;
- follow-up event appended: 2/2;
- follow-up event bound to first wake result record: 2/2;
- follow-up received bound first-record context: 2/2;
- follow-up strict-valid: 2/2;
- follow-up first-pass valid: 2/2;
- follow-up chose `stop_complete`: 2/2;
- final phrase recovered: 2/2;
- generated intermediate used: 2/2;
- extra continuations after follow-up: 0;
- final quiescence: 2/2;
- repair attempts: 0/2;
- bounded call violations: 0/2;
- errors: 0/2.

Hypothesis outcomes:

- H501 passed.
- H502 passed.
- H503 passed.
- H504 passed.
- H505 passed.

## Row-Level Notes

Replicate 1:

- first wake result record: `21183129-87c6-4b48-b7db-7cb1112aef4d`;
- follow-up event bound to that same record;
- step 1 stopped at `auto_continuation_limit_reached` after one appended
  continuation;
- step 2 returned `waiting`;
- step 3 completed follow-up and returned `idle`;
- step 4 returned `idle`;
- first/follow-up failures: none.

Replicate 2:

- first wake result record: `c4f83a05-4dc9-41d4-a69f-7d816faf0dbb`;
- follow-up event bound to that same record;
- step 1 stopped at `auto_continuation_limit_reached` after one appended
  continuation;
- step 2 returned `waiting`;
- step 3 completed follow-up and returned `idle`;
- step 4 returned `idle`;
- first/follow-up failures: none.

## Interpretation

This is the first clean live map point showing that the model can emit a
complete scheduler-valid continuation request through a terminal surface, rather
than merely benefiting from a continuation request preloaded by the harness.

The relevant positive result is not just tool compliance. The emitted request
contained a nested follow-up terminal surface, preserved the
`<result_record_id>` placeholder, requested recall of the generated
`policy_intermediate`, and allowed the scheduler to bind the follow-up to the
newly committed first-wake record. The follow-up then used that generated record
and stopped.

This strengthens the event-loop story:

- the loop can run generated continuations;
- the continuation can be model-emitted rather than harness-set;
- the scheduler can pace the chain;
- the follow-up can observe and use the generated first-wake record;
- the chain can terminate without repair or extra continuations.

## Important Caveat

This was a strongly scaffolded policy decision. The prompt told the model that
bounded continuation was warranted and provided the exact JSON shape and values
for the continuation request. Therefore, this panel does not show open-ended
autonomous policy selection.

What it does show is narrower and still useful: under a closed terminal surface,
Deepseek can carry a complete model-owned continuation request through the
production scheduler without corrupting the nested terminal surface or losing
the record-binding placeholder.

## Design Implication

The next policy layer can be tested without more substrate repairs. The
mechanical substrate is now good enough to ask policy questions:

- should this wake continue, stop, or ask for evidence?
- can the model choose correctly when the expected action is not explicitly
  named?
- can the scheduler enforce budgets and disposition when the model chooses
  poorly?

The event loop is moving from a queue executor toward a bounded control loop.

## Next Research Move

The useful next falsification experiment is a policy-boundary panel with
matched tasks:

1. `continue_after`: task cannot be completed without a later wake.
2. `stop_complete`: task can be completed immediately.
3. `ask_external_evidence`: task lacks required context and should not continue
   blindly.

The expected result should not be perfect compliance by default. The purpose is
to see whether the model distinguishes policy actions when the prompt provides
the action vocabulary but not the answer.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/model_owned_continuation_policy_20260605/run_model_owned_continuation_policy.py
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
timeout 1800s uv run python experiments/event_loop/model_owned_continuation_policy_20260605/run_model_owned_continuation_policy.py
jq '{summary: .summary, rows: [.results[] | {replicate, error, policy_action, continuation_request_kind, continuation_request_scheduler_valid, continuation_request_expected_context, continuation_request_uses_placeholder, followup_event_bound_result_record_id, first_wake_result_record_id, step1_stop_reason, step1_auto_continuations, step2_stop_reason, step3_stop_reason, step3_auto_continuations, step4_stop_reason, followup_policy_action, first_failures: .first_wake_failures, followup_failures: .followup_wake_failures}]}' experiments/event_loop/model_owned_continuation_policy_20260605/results.json
```
