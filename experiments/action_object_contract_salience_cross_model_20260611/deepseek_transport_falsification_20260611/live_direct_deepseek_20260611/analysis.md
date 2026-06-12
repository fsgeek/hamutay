# DeepSeek Direct-Endpoint Transport Falsification Analysis

Experiment ID: `deepseek_transport_falsification_20260611`

## Execution

- Started: `2026-06-12T01:35:27.594194+00:00`
- Finished: `2026-06-12T01:36:02.906993+00:00`
- Endpoint: `https://api.deepseek.com`
- Rows: `6`
- Total tokens: `4806`
- Estimated cost USD: `0.000000`

## Condition Counts

| Condition | Rows | Primary scorable | Strict pass | Relaxed pass | Provider failures | Protocol failures | Recovered | Strict pass if recovered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| example_strict_current | 3 | 1 | 1 | 1 | 0 | 2 | 1 | 0 |
| example_strict_transport_explicit | 3 | 3 | 2 | 2 | 0 | 0 | 0 | 0 |

## Attribution

- Primary attribution: `prompt_transport_contract`
- Rationale: The transport-explicit prompt rescued primary strict scoring while the current example prompt did not.

Decision inputs:

- `current_provider_failures`: `0`
- `current_strict_pass_count`: `1`
- `current_strict_pass_if_recovered`: `0`
- `current_unrecovered_protocol_failures`: `1`
- `transport_provider_failures`: `0`
- `transport_strict_pass_count`: `2`
- `transport_strict_pass_if_recovered`: `0`
- `transport_unrecovered_protocol_failures`: `0`

## Row Failure Attribution

| Row | Condition | Attribution | Rationale |
| --- | --- | --- | --- |
| deepseek_v4_pro__example_strict_current__r01 | example_strict_current | `prompt_transport_contract` | Provider returned no visible JSON content even though the call completed; this is a visible-channel transport failure. |
| deepseek_v4_pro__example_strict_current__r02 | example_strict_current | `prompt_transport_contract` | Secondary recovery found only an embedded JSON fragment, not a complete strict-valid action object. |
| deepseek_v4_pro__example_strict_transport_explicit__r01 | example_strict_transport_explicit | `model_contract_boundary` | The model returned parseable JSON, but it failed the required action contract under both strict and relaxed scoring. |

## Protocol Recovery Audit

- Protocol failures: `2`
- Recoverable protocol failures: `1`
- Unrecoverable protocol failures: `1`
- Strict pass if recovered: `0`
- Relaxed pass if recovered: `0`
- Recovery methods: `{'embedded_json_object': 1}`

## Interpretation

The model can satisfy the action-object contract when visible transport constraints are explicit. The next harness prompt should carry those constraints before live autonomy work.

## Artifact Trail

- `results.json` contains aggregate machine-readable results.
- `analysis.md` is this analysis artifact.
- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered execution frame.
- `rows/<row_id>/provider_request.json` preserves each request.
- `rows/<row_id>/provider_response.json` preserves each response.
- `rows/<row_id>/provider_attempts.json` preserves retry/attempt telemetry.
- `rows/<row_id>/strict_evaluation.json` preserves strict scoring.
- `rows/<row_id>/relaxed_evaluation.json` preserves relaxed scoring.
- `rows/<row_id>/recovery_evaluation.json` preserves secondary recovery audits when attempted.
- `rows/<row_id>/row_result.json` ties each row together.
