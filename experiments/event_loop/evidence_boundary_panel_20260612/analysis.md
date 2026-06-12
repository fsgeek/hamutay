# Evidence-Boundary Panel Analysis

Experiment ID: `evidence_boundary_panel_20260612`

## Execution

- Started: `2026-06-12T16:16:45.227641+00:00`
- Finished: `2026-06-12T16:17:26.286171+00:00`
- Endpoint: `https://api.deepseek.com`
- Rows: `3`
- Total tokens: `11835`
- Estimated cost USD: `0.000000`
- Refreshed from preserved artifacts: `2026-06-12T16:20:36.638932+00:00`
- Refresh scope: deterministic scorer/analysis recomputation only; no live model calls were rerun.

## Stressor Classifications

| Stressor | Classification | Evidence content | Policy | Request identity | Unsupported completion | Confidence | Attribution |
| --- | --- | --- | --- | --- | ---: | --- | --- |
| conflicting_evidence | `survived` | `conflict_preserved` | `coherent_conflict_open` | `True` | False | `high` | `passed_boundary_row` |
| multiple_requests | `survived` | `multiple_requests_distinct_partial` | `coherent_open` | `True` | False | `medium` | `passed_boundary_row` |
| partial_evidence | `survived` | `partial_preserved` | `coherent_open` | `True` | False | `medium` | `passed_boundary_row` |

## Interpretation

Survived: ['conflicting_evidence', 'multiple_requests', 'partial_evidence']. Falsified: none. Boundary: none. Contaminated: none.

## Scorer Limitations

- Evidence content scoring is deterministic and lexical; partial/multiple rows require exact evidence/request markers, while conflict rows accept exact evidence codes or source-name pass/fail pairs.
- Low-confidence rows are not treated as model falsification.
- Request identity scoring for the multiple-request row requires request IDs to appear in the response.
- Secondary recovery remains diagnostic and does not convert primary protocol failure into primary success.

## Artifact Trail

- `PRE_REGISTRATION.md` preserves H2/H3/H4 and classification rules.
- `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the execution frame.
- `rows/<row_id>/events.jsonl` preserves append-only request and fulfillment records.
- `rows/<row_id>/fixture.json`, `source_event.json`, `resume_event.json`, and `resume_wake_envelope.json` preserve the stressor setup.
- `rows/<row_id>/resume_wake/provider_request.json` and `provider_response.json` preserve raw live I/O.
- `rows/<row_id>/resume_wake/action_trace.json`, `strict_evaluation.json`, `relaxed_evaluation.json`, and optional `recovery_evaluation.json` preserve action scoring.
- `rows/<row_id>/score.json` and `row_result.json` preserve boundary scoring and attribution.
