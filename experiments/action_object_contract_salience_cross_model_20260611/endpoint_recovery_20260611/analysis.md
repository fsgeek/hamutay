# Cross-Model Action-Object Contract Salience Analysis

Experiment ID: `action_object_contract_salience_cross_model_20260611`

## Execution

- Started: `2026-06-11T19:19:22.535014+00:00`
- Finished: `2026-06-11T19:20:33.844561+00:00`
- Endpoint: `endpoint-family-aware`
- Rows: 12
- Total tokens: 12414
- Estimated cost USD: 0.042897

Endpoint families:

- `anthropic_messages`: `https://openrouter.ai/api`
- `deepseek_anthropic_messages`: `https://api.deepseek.com/anthropic`
- `openai_chat`: `https://api.deepseek.com`

## Model Counts

| Model | Original strict pass | Example strict pass | Original strict fail / relaxed pass | Example strict fail / relaxed pass |
| --- | ---: | ---: | ---: | ---: |
| claude_sonnet_4_6 | 0/3 | 3/3 | 3 | 0 |
| deepseek_v4_pro | 0/2 | 3/3 | 2 | 0 |

## Protocol Recovery Audit

- Protocol failures: `1`
- Recoverable protocol failures: `1`
- Unrecoverable protocol failures: `0`
- Strict pass if recovered: `0`
- Relaxed pass if recovered: `0`
- Recovery methods: `{'fenced_json': 1}`

## Hypothesis Assessment

- Primary pattern: `cross_model_contract_salience_boundary`
- DeepSeek-specific boundary: `False`
- Cross-model contract salience: `True`
- General action-contract literacy failure: `False`

Evidence lists:

- Models with original-prompt failure: `['claude_sonnet_4_6', 'deepseek_v4_pro']`
- Models rescued by example prompt: `['claude_sonnet_4_6', 'deepseek_v4_pro']`
- Source-reference models with original-prompt failure: `['deepseek_v4_pro']`
- Source-reference models rescued by example prompt: `['deepseek_v4_pro']`
- Models failing the example prompt: `[]`
- Models unscoreable under original prompt: `[]`
- Models unscoreable under example prompt: `[]`
- Source DeepSeek reference used: `True`

## Interpretation

The original-prompt failure is not DeepSeek-specific in this matrix. Multiple model families fail the original strict prompt and improve with the example prompt, supporting a broader prompt/contract salience explanation.

## Limitations

No provider/protocol unscoreable model conditions were observed. Row-level residuals remain: 0 provider failure rows and 1 protocol failure rows. 1 protocol failure rows were recoverable by secondary audit without changing primary scoring.

## Artifact Trail

- `results.json` contains aggregate machine-readable results.
- `analysis.md` is this analysis artifact.
- `rows/<row_id>/provider_request.json` preserves each request.
- `rows/<row_id>/provider_response.json` preserves each response.
- `rows/<row_id>/provider_attempts.json` preserves retry/attempt telemetry.
- `rows/<row_id>/recovery_evaluation.json` preserves secondary recovery audits for invalid_action_schema rows.
- `rows/<row_id>/strict_evaluation.json` preserves strict scoring.
- `rows/<row_id>/relaxed_evaluation.json` preserves relaxed scoring.
- `rows/<row_id>/row_result.json` ties each row together.
