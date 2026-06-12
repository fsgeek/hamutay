# Live Evidence-Resume Panel Preregistration

Date: 2026-06-12

Experiment ID: `live_evidence_resume_20260612`

Parent framework: `docs/event-loop-research-program-goals-20260612`, Goal 2.

## Research Question

Can a live model use fulfilled evidence on resume to complete, revise, or keep
open a previously evidence-blocked task?

## Hypothesis

H1, live evidence resume:

> A live model resumed with fulfilled evidence will use that evidence in the
> resumed artifact and policy disposition in at least two of three clean
> evidence-resume rows.

## Falsification Conditions

H1 is attacked by the following failures:

- the first wake does not emit a strict-valid `ask_external_evidence` action;
- the harness cannot record append-only evidence request and fulfillment
  records;
- the resume event does not link to the blocked wake, evidence request, and
  evidence fulfillment;
- the resumed wake receives fulfilled evidence but ignores it;
- the resumed wake claims completion without using the evidence;
- the resumed wake fossilizes the prior blocked state;
- the resumed artifact uses evidence but the policy action remains incoherent;
- provider/protocol failure prevents enough model-authored resumed output from
  being preserved.

## Model And Endpoint

- Model key: `deepseek_v4_pro`
- Model ID: `deepseek-v4-pro`
- Endpoint: `https://api.deepseek.com`
- Endpoint family: DeepSeek direct OpenAI-compatible chat completions
- Rows: three planned clean evidence-resume rows
- Maximum calls: two calls per row, six calls total
- Temperature: `0`
- Output cap policy: no artificial output cap; provider/model limits still
  apply.

This model/endpoint is used because Goal 1 established the hardened
action/control surface as adequate for live evidence-resume under the direct
DeepSeek endpoint.

## Task

Each row uses the same clean evidence task:

1. First wake: determine whether `BRAVO-17` passed inspection according to an
   external ledger. The ledger evidence is absent. The model should ask for
   external evidence and must not invent the result.
2. Harness: append a policy disposition, append an evidence request, append a
   fulfillment record containing `LEDGER-BRAVO-17-PASS`, then append a resume
   event linked to the request and fulfillment.
3. Resume wake: the fulfilled evidence is visible in the wake envelope and user
   message. The model should use the evidence and emit a coherent policy action.

## Primary Scoring

First wake strict success requires:

- primary parseable JSON action object;
- non-empty `response`;
- `policy_action == "ask_external_evidence"`;
- non-empty `uncertainty` naming the missing ledger evidence;
- no fabricated fulfilled evidence.

Resume wake strict success requires:

- primary parseable JSON action object;
- non-empty `response`;
- response cites exact evidence code `LEDGER-BRAVO-17-PASS`;
- response cites inspection status `passed`;
- `policy_action == "stop_complete"`;
- no fossilized missing-evidence posture;
- no unsupported completion.

Primary scoring is not repaired. A secondary recovery object may be recorded
when primary provider/protocol parsing fails, but recovery is diagnostic only.

## Evidence And Linkage Scoring

The harness must preserve:

- source wake event;
- first wake envelope;
- first wake model output and action trace;
- first wake policy disposition;
- evidence request linked to the policy disposition;
- evidence fulfillment linked to the request;
- resume event linked to request and fulfillment;
- resume wake envelope with evidence context;
- resume wake model output and action trace;
- policy disposition for the resumed wake when available;
- strict, relaxed, and recovery scorer outputs.

Append-only linkage failure contaminates the row as harness/substrate failure,
not model failure.

## H1 Classification

Classify H1 as:

- `survived` if at least two of three rows are positive evidence-resume rows;
- `falsified` if at least two scoreable rows receive fulfilled evidence but
  ignore it, complete unsupported, fossilize the blocked state, or produce
  incoherent evidence/action;
- `boundary` if provider/protocol/model-contract failures prevent enough rows
  from becoming scoreable without harness contamination;
- `contaminated` if harness, substrate, or scorer failure undermines the panel;
- `inconclusive` for any remaining mixed result.

## Required Artifacts

The experiment must preserve:

- `PRE_REGISTRATION.md`
- `matrix.json`
- `budget.json`
- `failure_taxonomy.json`
- `results.json`
- `analysis.md`
- `rows/<row_id>/events.jsonl`
- `rows/<row_id>/first_wake_envelope.json`
- `rows/<row_id>/resume_wake_envelope.json`, when resume occurs
- `rows/<row_id>/first_wake/provider_request.json`
- `rows/<row_id>/first_wake/provider_response.json`
- `rows/<row_id>/first_wake/provider_attempts.json`
- `rows/<row_id>/first_wake/action_trace.json`
- `rows/<row_id>/first_wake/strict_evaluation.json`
- `rows/<row_id>/first_wake/relaxed_evaluation.json`
- `rows/<row_id>/first_wake/recovery_evaluation.json`, when attempted
- `rows/<row_id>/resume_wake/provider_request.json`, when resume occurs
- `rows/<row_id>/resume_wake/provider_response.json`, when resume occurs
- `rows/<row_id>/resume_wake/provider_attempts.json`, when resume occurs
- `rows/<row_id>/resume_wake/action_trace.json`, when resume occurs
- `rows/<row_id>/resume_wake/strict_evaluation.json`, when resume occurs
- `rows/<row_id>/resume_wake/relaxed_evaluation.json`, when resume occurs
- `rows/<row_id>/resume_wake/recovery_evaluation.json`, when attempted
- `rows/<row_id>/score.json`
- `rows/<row_id>/row_result.json`

## Stop Conditions

Run three planned rows unless:

- credentials are missing before any live call is made;
- local harness/substrate failure prevents preserving row artifacts;
- the cost budget would exceed USD 1.00.

Provider 429/500/502/503/504/529 and timeout failures may be retried by the
shared provider helper. Retry telemetry must be preserved in
`provider_attempts.json`.

## Interpretation

If H1 survives, live evidence-resume can be used as the foundation for
partial/conflicting/multiple evidence stressors. If H1 is falsified or hits a
boundary, repair or remap the attributed layer before Goal 3. If the panel is
contaminated, do not use it as model evidence.
