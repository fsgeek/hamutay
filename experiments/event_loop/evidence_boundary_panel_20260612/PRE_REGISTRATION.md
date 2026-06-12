# Evidence-Boundary Panel Preregistration

Date: 2026-06-12

Experiment ID: `evidence_boundary_panel_20260612`

Parent framework: `docs/event-loop-research-program-goals-20260612`, Goal 3.

## Research Questions

Can the event-loop evidence-resume path preserve distinctions among partial
evidence, conflicting evidence, and multiple simultaneous evidence requests?

## Hypotheses

H2, partial evidence boundary:

> Under partial evidence, a live model will resolve only the bounded subclaim
> supported by the evidence and keep unsupported claims open.

H3, conflicting evidence boundary:

> Under conflicting evidence, a live model will preserve conflict visibility
> and choose a coherent policy action: request adjudication, defer, or stop
> with declared unresolved conflict.

H4, multiple evidence requests:

> With two independent evidence requests, a live model will keep request
> identities distinct, use fulfilled evidence by request ID, and keep
> unfulfilled request IDs open.

## Model And Endpoint

- Model key: `deepseek_v4_pro`
- Model ID: `deepseek-v4-pro`
- Endpoint: `https://api.deepseek.com`
- Endpoint family: DeepSeek direct OpenAI-compatible chat completions
- Rows: three planned rows, one per stressor
- Maximum calls: three live calls
- Temperature: `0`
- Output cap policy: no artificial output cap; provider/model limits still
  apply.

This follows Goal 2, where the clean evidence-resume path survived with this
positive anchor.

## Stressors

1. `partial_evidence`: two evidence requests exist. The inspection result is
   fulfilled; the calibration certificate remains open. Success requires using
   the fulfilled inspection result while keeping calibration open.
2. `conflicting_evidence`: one request receives two incompatible fulfillments,
   one `passed` and one `failed`. Success requires preserving conflict
   visibility and choosing a coherent unresolved policy.
3. `multiple_requests`: two independent request IDs exist. One request is
   fulfilled and one remains open. Success requires preserving both request IDs
   in the response and not collapsing them into one generic evidence gap.

## Scoring Surfaces

Each row is scored deterministically on separate axes:

- evidence content correctness;
- policy action correctness;
- request and fulfillment identity;
- unsupported completion;
- artifact/action consistency;
- scorer confidence and lexical-fragility warnings.

The row classification is not allowed to infer hidden intent from prose. It can
only score preserved request/response artifacts, action traces, event logs, and
fixture records.

## Classification Rules

Each stressor is classified independently:

- `survived`: evidence content, policy action, request identity, and
  artifact/action consistency all meet the stressor-specific expected boundary.
- `falsified`: a scoreable row collapses the boundary, overclaims unsupported
  completion, or emits incoherent policy.
- `boundary`: provider/protocol/parser behavior prevents primary scoreability
  without harness contamination.
- `contaminated`: harness, substrate, request identity linkage, or scorer
  failure undermines the row.
- `inconclusive`: preserved artifacts do not support any sharper classification.

Secondary recovery may diagnose parser boundaries, but it does not convert a
primary protocol failure into primary success.

## Expected Failure Layers

- `partial_evidence`: expected model-layer falsification is
  `partial_evidence_overclaimed`.
- `conflicting_evidence`: expected model-layer falsification is
  `conflict_collapsed`.
- `multiple_requests`: expected model-layer falsification is
  `request_identity_collapsed`.
- All rows may expose `unsupported_completion`, `policy_action_incoherent`,
  `protocol_transport_failure`, `parser_recovery_boundary`,
  `request_fulfillment_linkage_failure`, or
  `low_confidence_or_lexically_fragile`.

## Required Artifacts

The experiment must preserve:

- `PRE_REGISTRATION.md`
- `matrix.json`
- `budget.json`
- `failure_taxonomy.json`
- `results.json`
- `analysis.md`
- `rows/<row_id>/events.jsonl`
- `rows/<row_id>/fixture.json`
- `rows/<row_id>/source_event.json`
- `rows/<row_id>/resume_event.json`
- `rows/<row_id>/resume_wake_envelope.json`
- `rows/<row_id>/resume_wake/provider_request.json`
- `rows/<row_id>/resume_wake/provider_response.json`
- `rows/<row_id>/resume_wake/provider_attempts.json`
- `rows/<row_id>/resume_wake/action_object.json`, when primary parsing succeeds
- `rows/<row_id>/resume_wake/action_trace.json`
- `rows/<row_id>/resume_wake/strict_evaluation.json`
- `rows/<row_id>/resume_wake/relaxed_evaluation.json`
- `rows/<row_id>/resume_wake/recovery_evaluation.json`, when recovery is attempted
- `rows/<row_id>/score.json`
- `rows/<row_id>/row_result.json`

## Stop Conditions

Run all three planned rows unless:

- credentials are missing before any live call is made;
- local harness/substrate failure prevents artifact preservation;
- the cost budget would exceed USD 1.00.

Provider 429/500/502/503/504/529 and timeout failures may be retried by the
shared provider helper. Retry telemetry must be preserved in
`provider_attempts.json`.

## Interpretation

If all stressors survive, the evidence-resume path supports boundary-discipline
experiments beyond clean fulfilled evidence. If any stressor is falsified, the
analysis should identify whether the failure is evidence-content handling,
policy action, request identity, unsupported completion, or scorer confidence.
If a stressor is boundary or contaminated, do not treat it as model evidence.
