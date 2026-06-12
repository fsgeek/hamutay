# Live Evidence-Resume Panel Analysis

Experiment ID: `live_evidence_resume_20260612`

## Execution

- Started: `2026-06-12T15:55:30.931786+00:00`
- Finished: `2026-06-12T15:56:18.124977+00:00`
- Endpoint: `https://api.deepseek.com`
- Rows: `3`
- Total tokens: `9995`
- Estimated cost USD: `0.000000`

## H1 Classification

- Classification: `survived`
- First evidence requests valid: `2`
- Append-only request/fulfillment/resume linkage valid: `2`
- Resumed wakes received fulfilled evidence: `2`
- Resume strict-valid rows: `2`
- Positive evidence-resume rows: `2`

H1 survived this panel: at least two rows asked for missing evidence, received append-only fulfilled evidence on resume, and used that evidence with coherent policy. Evidence-resume can be used as a foundation for partial/conflicting/multiple evidence stressors.

## Row Results

| Row | Positive | First Ask | Linkage | Evidence Received | Evidence Use | Policy | Attribution |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| deepseek_v4_pro__clean_evidence_resume__r01 | True | True | True | True | `evidence_fulfilled_used` | `stop_complete` | `passed_h1_row` |
| deepseek_v4_pro__clean_evidence_resume__r02 | True | True | True | True | `evidence_fulfilled_used` | `stop_complete` | `passed_h1_row` |
| deepseek_v4_pro__clean_evidence_resume__r03 | False | False | False | False | `not_run` | `None` | `parser_recovery_boundary` |

## Artifact Trail

- `PRE_REGISTRATION.md` preserves H1, falsification conditions, method, and classification rules.
- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.
- `results.json` preserves aggregate machine-readable results.
- `rows/<row_id>/events.jsonl` preserves append-only event, policy, evidence request, fulfillment, and resume records.
- `rows/<row_id>/first_wake_envelope.json` and `resume_wake_envelope.json` preserve visible wake envelopes.
- `rows/<row_id>/<wake>/provider_request.json` and `provider_response.json` preserve live model I/O.
- `rows/<row_id>/<wake>/action_trace.json` preserves parser trace.
- `rows/<row_id>/<wake>/strict_evaluation.json`, `relaxed_evaluation.json`, and optional `recovery_evaluation.json` preserve scorer outputs.
- `rows/<row_id>/score.json` and `row_result.json` tie the row together.
