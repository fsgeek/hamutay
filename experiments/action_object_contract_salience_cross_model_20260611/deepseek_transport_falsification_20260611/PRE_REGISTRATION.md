# DeepSeek Direct-Endpoint Transport Falsification Preregistration

Date: 2026-06-11

Experiment ID: `deepseek_transport_falsification_20260611`

Parent experiment: `action_object_contract_salience_cross_model_20260611`

## Research Question

When DeepSeek V4 Pro is called through the direct DeepSeek OpenAI-compatible
endpoint, are residual action-object failures caused by model behavior,
prompt/transport contract presentation, parser/recovery boundary, provider or
substrate failure, or inconclusive evidence?

## Motivation

The recovery-aware attribution pass found that the main action-object failure
pattern is prompt/schema salience rather than a DeepSeek-only incapability.
However, DeepSeek direct-endpoint rows still showed a residual transport
ambiguity: some rows contained recoverable embedded JSON while one row exposed
reasoning content with blank visible content. This experiment isolates that
remaining boundary without reopening a broad model sweep.

## Fixed Model And Endpoint

| Field | Value |
| --- | --- |
| Model key | `deepseek_v4_pro` |
| Model ID | `deepseek-v4-pro` |
| Endpoint | `https://api.deepseek.com` |
| API shape | OpenAI-compatible `POST /chat/completions` |
| Fallbacks | None; direct DeepSeek endpoint only |

## Conditions

Each condition runs `n=3`, for six total live calls.

1. `example_strict_current`: the existing example-strict action-object prompt.
2. `example_strict_transport_explicit`: the same example-strict prompt plus an
   explicit visible-content transport constraint:
   return exactly one JSON object in visible message content; do not wrap in
   markdown fences; do not duplicate the object; do not put the answer only in
   reasoning content; do not emit prose before or after the object.

Both conditions use the same strict evaluator condition:
`B_example_prompt_strict_contract`.

## Preserved Artifacts

For each row:

- raw provider request;
- raw provider response;
- provider attempt telemetry;
- parsed action object if primary parsing succeeds;
- primary strict evaluation;
- relaxed counterfactual evaluation;
- secondary recovery evaluation when primary failure is
  `protocol:invalid_action_schema`;
- row result tying model, endpoint, condition, usage, failures, and evaluations.

## Falsification Predictions

- If `example_strict_transport_explicit` passes primary strict in at least two
  of three rows while `example_strict_current` does not, the residual failure is
  best attributed to prompt/transport contract presentation.
- If both conditions fail primary strict but secondary recovery finds valid
  action objects in at least two of three rows, the residual failure is best
  attributed to parser/recovery boundary or transport-wrapper mismatch.
- If both conditions fail primary strict and secondary recovery cannot recover
  valid action objects in at least two of three rows, the residual failure is
  evidence for a model/contract boundary under this action-object pattern.
- If provider errors prevent at least two of three rows in either condition from
  preserving model-authored content, the experiment is inconclusive for model
  behavior and attributed to provider/substrate failure.
- If both conditions pass primary strict in at least two of three rows, the
  residual DeepSeek ambiguity from previous runs is resolved as not present
  under this direct endpoint and current example-strict prompt.

## Non-Goals

- broad model comparison;
- changing primary strict scoring;
- accepting secondary recovery as primary parser behavior;
- production scheduler readiness;
- proving broad model capability or identity/autonomy claims.

