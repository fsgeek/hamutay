# Strict Continuation Validation Analysis

Experiment ID: `strict_continuation_validation_20260612`

## Result

- Classification: `survived`
- Live model calls: `False`
- Rows: `4`
- New failure mode observed: `False`
- Decision: Stricter continuation validation improved trace interpretability without creating a new failure mode in this probe.

## Rows

| Row | Expected | Passed | Validation | Policy accepted | Valid requests | Classified before acceptance | Legacy would accept | Interpretation |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| invalid_continue_no_request | `classified_before_acceptance` | True | `accepted_with_rejections` | False | 0 | True | True | `improved_trace_interpretability` |
| invalid_continue_malformed_request | `classified_before_acceptance` | True | `accepted_with_rejections` | False | 0 | True | True | `improved_trace_interpretability` |
| valid_continue_with_request | `accepted` | True | `accepted` | True | 1 | False | True | `control_ok` |
| stop_complete_no_request | `accepted` | True | `accepted` | True | 0 | False | False | `control_ok` |

## Interpretation

Stricter continuation validation improved trace interpretability without creating a new failure mode in this probe.

The two invalid `continue_after` fixtures would have passed a vocabulary-only policy-action check, but the strict validator now records an explicit policy rejection before acceptance. The raw first-pass objects remain available in row artifacts, so the failure is inspectable rather than silently repaired.

## Artifact Trail

- `PRE_REGISTRATION.md` defines H5 and falsification conditions.
- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.
- `rows/<row_id>/first_pass_output.json` preserves each authored first pass.
- `rows/<row_id>/action_trace.json` preserves accepted and rejected subactions.
- `rows/<row_id>/row_result.json` preserves row-level scoring.
