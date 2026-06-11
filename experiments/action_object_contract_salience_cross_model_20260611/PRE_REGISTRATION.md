# Cross-Model Action-Object Contract Salience Preregistration

Date: 2026-06-11

Experiment ID: `action_object_contract_salience_cross_model_20260611`

Source experiment:
`experiments/action_object_contract_literacy_20260610/`

This experiment asks whether the original-prompt action-object failure observed
with DeepSeek V4 Pro is model-specific or reflects a broader prompt/contract
salience issue.

## Research Question

When asked to emit the Hamut'ay audited autonomy action object, does the
original strict prompt fail only for DeepSeek V4 Pro, or do other model
families also need a concrete example to make the strict `open_items[*].kind`
and `open_items[*].text` contract salient?

## Fixed Model Set

Model availability was checked against OpenRouter `/api/v1/models` on
2026-06-11 before preregistration. All live rows use the OpenRouter
OpenAI-compatible endpoint with provider fallbacks disabled.

| Model key | Model ID | Role |
| --- | --- | --- |
| `deepseek_v4_pro` | `deepseek/deepseek-v4-pro` | Source failure model |
| `kimi_k2_6` | `moonshotai/kimi-k2.6` | Low-cost peer model |
| `claude_sonnet_4_6` | `anthropic/claude-sonnet-4.6` | Anthropic anchor |
| `gpt_5_1` | `openai/gpt-5.1` | OpenAI-compatible anchor |

If a provider/model row fails before a model-authored action object is
preserved, that row is classified as provider/protocol failure. It is not
silently replaced by another model.

## Fixed Prompt Conditions

Only two prompt conditions are tested:

1. `original_strict`: the original strict live-pilot action-object prompt.
2. `example_strict`: the original strict prompt plus one concrete valid
   open-item example:

```json
{"kind":"todo","text":"resolve the bounded follow-up item"}
```

The example prompt also states that `description`, `handle`, `status`, and
`created_at` must not be used as substitutes for `kind` and `text`.

## Matrix

The fixed machine-readable matrix is `matrix.json`.

Each of 4 models is tested under 2 prompt conditions with `n=3`, for a maximum
of 24 one-cycle live calls.

Each row must preserve:

- raw provider request;
- raw provider response;
- parsed action object if present;
- strict parser evaluation;
- relaxed counterfactual evaluation;
- row result tying model, prompt condition, usage, and parse traces together.

## Hypotheses

### H1: DeepSeek-Specific Contract Salience Boundary

The original-prompt failure is model-specific if DeepSeek fails the original
strict prompt in at least two of three rows, the example prompt rescues DeepSeek
in at least two of three rows, and the other model families pass the original
strict prompt in at least two of three rows each.

### H2: Cross-Model Contract Salience Boundary

The original-prompt failure reflects a broader prompt/contract design issue if
two or more model families fail the original strict prompt in at least two of
three rows and are rescued by the example prompt in at least two of three rows.

### H3: General Action-Contract Literacy Failure

The current action-object contract pattern is not reliably learnable under this
test if two or more model families fail the example prompt in at least two of
three rows.

### H4: Contract-Shape Counterfactual

For any strict failures, relaxed counterfactual scoring records whether the
model authored semantically usable open-item content in a non-contract shape.
The relaxed evaluator must not mutate or repair the live output.

## Falsification Criteria

- H1 is weakened if at least one non-DeepSeek model also fails the original
  strict prompt in at least two of three rows.
- H2 is weakened if only DeepSeek shows the original-prompt failure pattern.
- H3 is weakened if the example prompt passes in at least three of four model
  families.
- A row is unscoreable if raw provider output, strict evaluation, or relaxed
  evaluation is not preserved.

## Metrics

Primary row metrics:

- model ID;
- prompt condition;
- provider/protocol failure, if any;
- `strict_required_actions_valid`;
- `relaxed_required_actions_valid`;
- rejection paths;
- explanation candidates;
- token usage and provider-reported cost.

Aggregate metrics:

- original strict pass count per model;
- example strict pass count per model;
- original strict-fail / relaxed-pass count per model;
- example strict-fail / relaxed-pass count per model;
- primary pattern: DeepSeek-specific, cross-model salience, general literacy
  failure, or mixed/ambiguous.

## Budget

Budget artifact: `budget.json`.

- Maximum live calls: 24.
- Maximum calls per condition: 3.
- Maximum cycles per call: 1.
- Maximum total tokens: 60000.
- Maximum estimated cost: USD 2.00.

## Execution Command

Preregistration artifacts only:

```bash
uv run python -m hamutay.memory.contract_salience
```

Live execution:

```bash
uv run python -m hamutay.memory.contract_salience --run-live
```

## Artifact Paths

Preregistration artifacts:

- `experiments/action_object_contract_salience_cross_model_20260611/PRE_REGISTRATION.md`;
- `experiments/action_object_contract_salience_cross_model_20260611/matrix.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/prompt_variants.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/budget.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/failure_taxonomy.json`.

Live result artifacts:

- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/results.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/analysis.md`;
- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/rows/<row_id>/provider_request.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/rows/<row_id>/provider_response.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/rows/<row_id>/strict_evaluation.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/rows/<row_id>/relaxed_evaluation.json`;
- `experiments/action_object_contract_salience_cross_model_20260611/live_matrix_20260611/rows/<row_id>/row_result.json`.

Code and tests:

- `src/hamutay/memory/contract_salience.py`;
- `tests/unit/test_contract_salience.py`.

## Non-Goals

- broad model leaderboard;
- changing the live autonomy harness;
- proving bounded autonomous work;
- proving identity, agency, or moral patienthood;
- choosing a production memory or action-object contract.
