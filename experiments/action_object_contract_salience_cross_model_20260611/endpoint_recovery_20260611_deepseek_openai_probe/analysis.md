# Cross-Model Action-Object Contract Salience Analysis

Experiment ID: `action_object_contract_salience_cross_model_20260611`

## Execution

- Started: `2026-06-11T19:14:53.795923+00:00`
- Finished: `2026-06-11T19:16:19.151249+00:00`
- Endpoint: `endpoint-family-aware`
- Rows: 12
- Total tokens: 13686
- Estimated cost USD: 0.042687

Endpoint families:

- `anthropic_messages`: `https://openrouter.ai/api`
- `openai_chat`: `https://api.deepseek.com`

## Model Counts

| Model | Original strict pass | Example strict pass | Original strict fail / relaxed pass | Example strict fail / relaxed pass |
| --- | ---: | ---: | ---: | ---: |
| claude_sonnet_4_6 | 0/3 | 3/3 | 3 | 0 |
| deepseek_v4_pro | 0/1 | 2/2 | 1 | 0 |

## Protocol Recovery Audit

- Protocol failures: `3`
- Recoverable protocol failures: `2`
- Unrecoverable protocol failures: `1`
- Strict pass if recovered: `0`
- Relaxed pass if recovered: `1`
- Recovery methods: `{'embedded_json_object': 2}`

## Hypothesis Assessment

- Primary pattern: `cross_model_contract_salience_boundary`
- DeepSeek-specific boundary: `False`
- Cross-model contract salience: `True`
- General action-contract literacy failure: `False`

Evidence lists:

- Models with original-prompt failure: `['claude_sonnet_4_6']`
- Models rescued by example prompt: `['claude_sonnet_4_6']`
- Source-reference models with original-prompt failure: `['deepseek_v4_pro']`
- Source-reference models rescued by example prompt: `['deepseek_v4_pro']`
- Models failing the example prompt: `[]`
- Models unscoreable under original prompt: `['deepseek_v4_pro']`
- Models unscoreable under example prompt: `[]`
- Source DeepSeek reference used: `True`

## Interpretation

The original-prompt failure is not DeepSeek-specific in this matrix. Multiple model families fail the original strict prompt and improve with the example prompt, supporting a broader prompt/contract salience explanation.

## Limitations

Provider/protocol failures are not counted as model contract failures. Original-prompt unscoreable models: `['deepseek_v4_pro']`. Example-prompt unscoreable models: `[]`. DeepSeek and Claude current-run rows were therefore not used as direct current-run model evidence; the DeepSeek side of the cross-model comparison uses the prior committed source experiment reference.

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
