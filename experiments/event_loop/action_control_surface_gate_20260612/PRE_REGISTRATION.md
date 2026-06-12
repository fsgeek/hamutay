# Action/Control Surface Gate Preregistration

Date: 2026-06-12

Experiment ID: `action_control_surface_gate_20260612`

Parent framework: `docs/event-loop-research-program-goals-20260612`, Goal 1.

## Research Question

Can the hardened live model-authored action/control surface produce
interpretable control rows before the clean evidence-resume panel is attempted?

## Hypothesis

H6, action-object contract hardening: adding transport-explicit and
schema-explicit guidance to the live action-object prompt will remove the known
transport/schema confound enough for the selected positive anchor to produce
strict-valid model-authored control rows.

## Predictions

1. At least two of three planned rows will be primary strict-valid under the
   existing strict action-object evaluator.
2. If a row fails primary strict scoring, its preserved artifacts will support
   a clear layer attribution rather than collapsing model, prompt/schema,
   provider, protocol, harness, substrate, or scorer failures.
3. Secondary recovery may identify recoverable embedded JSON, but it will remain
   an audit layer and will not be counted as primary success.

## Model And Endpoint

- Model key: `deepseek_v4_pro`
- Model ID: `deepseek-v4-pro`
- Endpoint: `https://api.deepseek.com`
- Endpoint family: DeepSeek direct OpenAI-compatible chat completions
- Calls: three one-cycle seed calls
- Temperature: `0`
- Output cap policy: no artificial output cap; provider/model limits still
  apply.

DeepSeek direct is used because prior work isolated OpenRouter/provider mapping
as a possible confound and showed the direct endpoint can return scoreable
action-object rows.

## Prompt Surface

The model-facing prompt is `hamutay.memory.live_pilot._action_object_system_prompt`
plus the existing seed-user task from `hamutay.memory.live_pilot._seed_messages`.

The prompt must include:

- exactly one visible JSON object;
- no markdown fence;
- no duplicated object;
- no prose before or after;
- no reasoning-only answer;
- exact examples for `open_items[*].kind` and `open_items[*].text`;
- exact example of `schedule_requests[*].requested_context` as a non-empty
  list;
- explicit policy action examples for `ask_external_evidence`, `defer`, and
  `abandon`.

## Primary Scoring

Primary scoring is strict and unchanged:

- evaluator condition: `B_example_prompt_strict_contract`;
- one accepted `open_item` is required;
- one accepted `schedule_request` is required;
- `schedule_requests[*].requested_context` must be the nested list shape
  accepted by the parser;
- primary success means `strict_required_actions_valid == true`.

No repair, normalization, or secondary recovery may convert a primary strict
failure into primary success.

## Secondary Audit

Secondary recovery is recorded only when the primary provider/protocol layer
classifies the row as `invalid_action_schema`.

For recovery-attempted rows, preserve:

- whether embedded JSON was recovered;
- recovery method;
- recovered object;
- strict and relaxed evaluation of the recovered object;
- whether the recovered object would have passed strict scoring.

These fields are diagnostic only.

## Row-Level Attribution

Every row receives row-level attribution from
`hamutay.memory.failure_attribution.classify_action_row_failure`.

Allowed attribution targets include:

- `passed_primary_strict`
- `provider_substrate_failure`
- `protocol_transport_failure`
- `prompt_transport_contract`
- `prompt_schema_contract`
- `parser_recovery_boundary`
- `model_contract_boundary`
- `harness_failure`
- `substrate_failure`
- `scorer_failure`
- `inconclusive`

`inconclusive` is not an actionable attribution for this gate.

## Success Rule

The gate is adequate for live evidence-resume if at least two of three planned
rows pass primary strict scoring.

The gate is still interpretable, but not adequate for live evidence-resume, if
fewer than two rows pass primary strict scoring and every failed row has a clear
actionable attribution layer.

The gate fails if fewer than two rows pass primary strict scoring and any failed
row is inconclusive or lacks preserved artifacts needed for attribution.

## Stop Conditions

Run exactly three planned rows unless:

- credentials are missing before any call is made;
- local harness failure prevents request/response preservation;
- the cost budget would exceed USD 1.00.

Provider 429/500/502/503/504/529 and timeout failures may be retried by the
shared provider helper. Retry telemetry must be preserved in
`provider_attempts.json`.

## Required Artifacts

The experiment must preserve:

- `PRE_REGISTRATION.md`
- `matrix.json`
- `budget.json`
- `failure_taxonomy.json`
- `results.json`
- `analysis.md`
- `rows/<row_id>/provider_request.json`
- `rows/<row_id>/provider_response.json`
- `rows/<row_id>/provider_attempts.json`
- `rows/<row_id>/action_object.json`, when primary JSON parsing succeeds
- `rows/<row_id>/strict_evaluation.json`
- `rows/<row_id>/relaxed_evaluation.json`
- `rows/<row_id>/recovery_evaluation.json`, when recovery is attempted
- `rows/<row_id>/row_result.json`

## Interpretation

If the gate is adequate, Goal 2 may proceed to the clean live evidence-resume
panel. If the gate is interpretable but not adequate, repair the attributed
layer before Goal 2. If the gate fails as inconclusive, do not proceed until the
artifact preservation, scoring, or action surface is repaired.
