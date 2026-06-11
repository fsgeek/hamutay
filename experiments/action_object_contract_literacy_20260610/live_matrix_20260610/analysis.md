# Action-Object Contract Literacy Matrix Analysis

Experiment ID: `action_object_contract_literacy_20260610`

## Execution

- Started: `2026-06-11T03:13:44.915760+00:00`
- Finished: `2026-06-11T03:15:30.925867+00:00`
- Model: `deepseek/deepseek-v4-pro`
- Endpoint: `https://openrouter.ai/api/v1`
- Rows: 12
- Total tokens: 5903
- Estimated cost USD: 0.008874

## Condition Counts

| Condition | Rows | Strict pass | Relaxed pass | Strict fail / relaxed pass | Provider failures | Protocol failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A_original_prompt_strict_contract | 3 | 0 | 3 | 3 | 0 | 0 |
| B_example_prompt_strict_contract | 3 | 3 | 3 | 0 | 0 | 0 |
| C_schema_checklist_strict_contract | 3 | 3 | 3 | 0 | 0 | 0 |
| D_relaxed_open_item_contract | 3 | 0 | 3 | 3 | 0 | 0 |

## Hypothesis Assessment

- H1 model fragility: `weakened`
- H2 prompt/schema presentation: `survives`
- H3 contract underspecification: `survives`
- H4 no autonomy claim from literacy: `retained`

Basis:

- `checklist_strict_passes`: 3
- `example_strict_passes`: 3
- `original_strict_passes`: 0
- `relaxed_condition_strict_passes`: 0
- `strict_fail_relaxed_passes`: 6
- `strict_failures`: 6

## Interpretation

The failure is best treated as a two-layer boundary. The strict contract failure is prompt/schema-presentation sensitive because both the example and checklist conditions satisfied the strict contract. It is also contract-sensitive because every strict failure contained enough authored structure for the preregistered relaxed counterfactual to score it as usable without applying hidden repair. Model fragility is weakened, not eliminated as a general possibility.

## Artifact Trail

- `results.json` contains the aggregate machine-readable result.
- `analysis.md` is this analysis artifact.
- `rows/<row_id>/provider_request.json` preserves each request.
- `rows/<row_id>/provider_response.json` preserves each response.
- `rows/<row_id>/strict_evaluation.json` preserves strict scoring.
- `rows/<row_id>/relaxed_evaluation.json` preserves relaxed scoring.
- `rows/<row_id>/row_result.json` ties each row together.
