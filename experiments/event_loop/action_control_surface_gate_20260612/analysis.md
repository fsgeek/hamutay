# Action/Control Surface Gate Analysis

Experiment ID: `action_control_surface_gate_20260612`

## Execution

- Started: `2026-06-12T12:44:55.371838+00:00`
- Finished: `2026-06-12T12:45:21.879220+00:00`
- Endpoint: `https://api.deepseek.com`
- Rows: `3`
- Primary scorable rows: `2`
- Primary strict pass count: `2`
- Relaxed pass count: `2`
- Total tokens: `3447`
- Estimated cost USD: `0.000000`

## Gate Verdict

- Gate interpretable: `True`
- Adequate for live evidence-resume: `True`
- Decision rule: adequate_for_live_evidence_resume requires at least two of three primary strict-valid rows; gate_interpretable also passes if every failed row has a clear actionable attribution layer.

Interpretation:

The hardened live action/control surface produced at least two primary strict-valid rows. This is adequate to proceed to the clean live evidence-resume panel, while continuing to preserve secondary recovery only as audit evidence.

## Row Attribution

| Row | Strict pass | Relaxed pass | Attribution | Rationale |
| --- | ---: | ---: | --- | --- |
| deepseek_v4_pro__hardened_live_action_surface__r01 | True | True | `passed_primary_strict` | Primary strict evaluation accepted the row. |
| deepseek_v4_pro__hardened_live_action_surface__r02 | True | True | `passed_primary_strict` | Primary strict evaluation accepted the row. |
| deepseek_v4_pro__hardened_live_action_surface__r03 | False | False | `parser_recovery_boundary` | Primary parser rejected the visible content, but secondary recovery found a strict-valid action object. |

## Secondary Recovery Audit

- Protocol failures: `1`
- Recoverable protocol failures: `1`
- Unrecoverable protocol failures: `0`
- Strict pass if recovered: `1`
- Relaxed pass if recovered: `1`
- Recovery methods: `{'embedded_json_object': 1}`

## Artifact Trail

- `PRE_REGISTRATION.md` preserves the preregistered question, hypothesis, predictions, method, and success rule.
- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.
- `results.json` preserves aggregate machine-readable results.
- `rows/<row_id>/provider_request.json` preserves each request.
- `rows/<row_id>/provider_response.json` preserves each response.
- `rows/<row_id>/provider_attempts.json` preserves retry telemetry.
- `rows/<row_id>/action_object.json` preserves parsed primary objects when present.
- `rows/<row_id>/strict_evaluation.json` preserves primary strict scoring.
- `rows/<row_id>/relaxed_evaluation.json` preserves counterfactual relaxed scoring.
- `rows/<row_id>/recovery_evaluation.json` preserves secondary recovery audits when attempted.
- `rows/<row_id>/row_result.json` ties row artifacts together.
