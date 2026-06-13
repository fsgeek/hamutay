# Working-Set Matched Panel Analysis

Experiment ID: `working_set_matched_panel_20260612`

## Result

- Classification: `falsified`
- Working-set relation: `worse`
- Artifact-quality relation: `worse`
- Token relation to direct: `not_less_than_direct`
- Decision: Event-loop working-set behavior did not meet the preregistered matched-panel threshold.

## Rows

| Condition | Working-set score | Artifact quality | Recovery | Contamination | Declared losses | Peak prompt tokens | Total prompt tokens | Artifact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| event_loop_model_controlled | 0.6000 | 0.7500 | 1.0000 | 1.0000 | 0.0000 | 2012 | 2783 | `useful` |
| harness_selected_summary | 0.9250 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 520 | 520 | `useful` |
| direct_one_shot | 0.9250 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1569 | 1569 | `useful` |

## Interpretation

Working-set benefit is scored separately from artifact quality. The working-set score combines evidence recovery, contamination avoidance, declared-loss preservation, and provenance. Artifact quality separately scores responsiveness, supported claims, and readiness conclusion quality.

## Run Integrity Note

An initial live run is archived under `aborted_initial_harness_scorer_bug/`.
That run is not treated as the panel result because the harness failed to read
the model's prompt-shaped nested `required_output.requested_context`, and the
scorer required an undeclared literal `status: supported` value. The corrected
run above preserves the aborted run and charges the final result only after
those harness/scorer defects were fixed and tested.

## Artifact Trail

- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered frame.
- `rows/<condition>/cycle_*.json` preserves raw provider requests and responses.
- `rows/<condition>/context_accounting.json` preserves context accounting, recall provenance, declared losses, and token use.
- `rows/<condition>/row_result.json` preserves recovery, contamination, artifact usefulness, and working-set scoring.
- `results.json` preserves the cross-condition comparison.
