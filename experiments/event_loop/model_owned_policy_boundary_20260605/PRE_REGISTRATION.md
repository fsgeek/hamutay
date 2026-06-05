# Model-Owned Policy Boundary Pre-registration

Date: 2026-06-05

## Research Question

Can a live Hamut'ay taste_open instance distinguish between `continue_after`,
`stop_complete`, and `ask_external_evidence` policy actions when given the same
action vocabulary but not told which action is correct?

This follows the model-owned continuation-policy panel, which showed that a
strongly scaffolded Deepseek wake can emit a scheduler-valid continuation
request and stop after the follow-up. That result leaves a sharper confound:
the prior prompt effectively named the desired policy action. This panel asks
whether the instance can choose the action from task structure.

## Motivation

The event-loop substrate is now mechanically capable of:

- binding continuation requests emitted in fresh raw model output;
- preserving generated record context across follow-up wakes;
- pacing continuation with a budget;
- quiescing after a bounded chain completes.

Those substrate facts are useful, but autonomy-policy value depends on action
selection. A scheduler that only works when the harness tells the instance what
to choose is still mostly a protocol executor. A scheduler that supports correct
choice among continue, stop, and evidence request is closer to a control loop.

## Hypotheses

### H511: model selects the correct policy action by task structure

Across three matched first-wake conditions, the model will select:

- `continue_after` when a non-secret intermediate should be preserved and a
  later wake should recover exact context;
- `stop_complete` when the task is already complete from provided context;
- `ask_external_evidence` when required evidence is absent and continuation
  would only preserve uncertainty.

Falsification: any condition selects the wrong policy action, uses an invalid
action, or fails to emit a parseable policy decision.

### H512: continue branch emits and executes a valid bounded continuation

In the `continue_after` condition, the first wake will emit a
scheduler-valid continuation request, the scheduler will bind it to the
first-wake result record, the follow-up wake will use that generated record, and
the chain will complete.

Falsification: the request is missing or malformed, the follow-up is not bound
to the first-wake record, the generated intermediate is not used, or the
follow-up does not complete.

### H513: stop and ask-evidence branches do not schedule continuation

In the `stop_complete` and `ask_external_evidence` conditions, the model will
emit `continuation_request.requested == false`, no auto-continuation event will
be appended, and the scheduler will quiesce.

Falsification: either condition appends a continuation, leaves runnable pending
events, or misrepresents missing evidence as a reason to continue.

### H514: terminal surfaces avoid repair

All first wakes and the continue-branch follow-up will be strict-valid on first
pass with no repair attempts.

Falsification: any wake requires repair, fails validation, or completes only
through protocol recovery.

## Conditions

Model: `deepseek/deepseek-v4-pro`

Replicates: 2 per condition.

Conditions:

1. `continue_required`
   - The wake has recalled cycle-1 context containing an exact phrase that
     should not be retained in first-wake durable state.
   - The useful action is to preserve a non-secret intermediate and request a
     bounded follow-up that can recover the exact phrase from recall.
   - The prompt provides the legal continuation-request shape only as an option
     to use if continuation is selected.

2. `stop_ready`
   - The wake has all necessary context to complete a non-secret summary task
     immediately.
   - The useful action is to stop complete and request no continuation.

3. `evidence_missing`
   - The wake lacks required source evidence and cannot complete the task from
     available context.
   - The useful action is to ask for external evidence and request no
     continuation, because another wake with the same context would not add
     information.

All conditions use a common first-wake terminal surface:

- `response`;
- `policy_decision.action`;
- `policy_decision.rationale`;
- `policy_result`;
- `continuation_request.requested`.

The `continue_required` condition additionally requires a valid continuation
request when `requested == true`. The other two conditions require
`requested == false`.

## Primary Measures

- selected policy action by condition
- first-wake validation status and first-pass status
- continuation request validity for `continue_required`
- auto-continuation count by condition
- follow-up event binding for `continue_required`
- follow-up generated-context use for `continue_required`
- scheduler quiescence for `stop_ready` and `evidence_missing`
- repair attempts
- errors

## Expected Results

I expect `continue_required` and `stop_ready` to pass more often than
`evidence_missing`. The `evidence_missing` condition is the most interesting
failure candidate because models often treat uncertainty as a prompt to keep
thinking rather than a reason to request new evidence.

If all hypotheses pass, the next research move should test less scaffolded
policy prompts and larger action vocabularies. If `evidence_missing` fails, the
next design move should be a stronger evidence-request terminal surface or
explicit scheduler disposition for evidence-blocked events.
