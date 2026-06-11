# Action-Object Contract Literacy Preregistration

Date: 2026-06-10

Experiment ID: `action_object_contract_literacy_20260610`

Source failure run:
`experiments/live_autonomy_pilot_20260609/runs/c39ba9a3-9dda-48f2-82f6-cb90f8229bae/`

This preregistration authorizes no live model calls. It prepares the fixed
matrix and no-live evaluator needed to interpret a later small live matrix.

## Research Question

The first tiny live autonomy pilot failed because DeepSeek V4 Pro returned a
model-authored action object with `response`, one `schedule_request`, and one
semantically plausible `open_items[0]`, but the open item omitted the strict
contract fields `kind` and `text`.

Is this failure best explained by:

- model fragility in producing action objects;
- prompt/schema presentation that did not make the contract visible enough;
- an action-object contract that was under-specified for models not trained on
  this pattern?

## Fixed Matrix

The matrix is stored in `matrix.json`. Exact prompt addenda are stored in
`prompt_variants.json` and copied into each matrix condition.

| Condition | Prompt | Contract | Purpose |
| --- | --- | --- | --- |
| `A_original_prompt_strict_contract` | Original live-pilot seed prompt | Strict `autonomous_action.v1` | Reproduce the failing condition. |
| `B_example_prompt_strict_contract` | Original plus one valid open-item example | Strict `autonomous_action.v1` | Test example sensitivity. |
| `C_schema_checklist_strict_contract` | Original plus explicit schema/checklist | Strict `autonomous_action.v1` | Test checklist/schema presentation. |
| `D_relaxed_open_item_contract` | Original plus explicit relaxed-contract text | Relaxed open-item evaluator only | Test whether rejected outputs contain enough authored information to proceed under a looser contract. |

Planned future live rows, if separately authorized: three calls per condition,
one cycle per call, DeepSeek V4 Pro through OpenRouter with fallbacks disabled.

## Hypotheses

### H1: Model Fragility

If DeepSeek cannot reliably produce the action object even with examples and a
checklist, then the failure is primarily a model-action literacy limitation for
this model under this harness.

Prediction: conditions `B` and `C` fail strict acceptance in fewer than two of
three rows, or fail with malformed/no action object rather than only a missing
open-item field.

### H2: Prompt/Schema Presentation

If example or checklist presentation makes the same model satisfy the strict
contract, then the first failure was presentation-sensitive rather than a hard
model limitation.

Prediction: condition `B` or `C` satisfies strict cycle-1 acceptance in at least
two of three rows while condition `A` does not.

### H3: Contract Underspecification

If rejected rows contain a semantically usable open item that lacks only strict
field names, then the strict contract may be under-specified relative to the
model's natural action-object representation.

Prediction: rejected rows contain non-empty `description` or equivalent content
for each open item, schedule correctly, and the preregistered relaxed
counterfactual would accept at least two of three rows without applying hidden
repair to the live harness.

### H4: No Autonomy Claim From Literacy Alone

Even if a condition satisfies cycle-1 action literacy, this experiment does not
establish bounded autonomous work. It only selects a clearer contract/prompt
candidate for a separately preregistered two-cycle live autonomy run.

## Falsification Criteria

- H1 is weakened if either `B` or `C` passes strict cycle-1 acceptance in at
  least two of three rows.
- H2 is weakened if example/checklist presentation does not improve over the
  original strict condition.
- H3 is weakened if rejected rows lack semantically usable open-item content or
  fail for reasons beyond missing `kind`/`text` shape.
- The whole experiment is unscoreable if provider/protocol failures prevent
  preserving raw model outputs and parse traces for the matrix rows.

## Metrics

Primary row metrics:

- `strict_open_item_valid`;
- `schedule_request_valid`;
- `strict_required_actions_valid`;
- `relaxed_open_item.would_accept`;
- `relaxed_required_actions_valid`;
- `normalization_applied` must remain `false`;
- rejection paths, especially `$.open_items[*].kind` and
  `$.open_items[*].text`;
- explanation candidates: `strict_contract_satisfied`,
  `contract_underspecification_candidate`,
  `prompt_or_model_contract_failure`, or
  `model_contract_literacy_failure`.

Aggregate condition metrics:

- strict pass count per condition;
- relaxed counterfactual pass count for strict failures;
- malformed or unparseable action count;
- provider/protocol/scorer failures.

## Failure Taxonomy

The taxonomy is stored in `failure_taxonomy.json` and distinguishes:

- model contract-literacy failure;
- prompt/schema presentation-sensitive failure;
- strict-contract rejection of semantically usable action;
- protocol/provider failure;
- scorer ambiguity.

## Budget

The budget is stored in `budget.json`.

This preregistration does not authorize live calls. If later authorized, the
matrix is capped at:

- 12 total calls;
- 3 calls per condition;
- 1 cycle per call;
- 30000 total tokens;
- USD 1.00 estimated total cost.

## No-Live Preparation

The no-live evaluator must:

1. load the failed run's cycle-1 provider response;
2. score it with the existing strict parser;
3. score it with the relaxed-open-item counterfactual;
4. write `fixture_failed_live_run_cycle1_evaluation.json`;
5. write `matrix.json`, `prompt_variants.json`, `budget.json`, and
   `failure_taxonomy.json`;
6. run without provider calls.

The evaluator command is:

```bash
uv run python -m hamutay.memory.contract_literacy
```

## Artifact Paths

Preregistered artifacts:

- `experiments/action_object_contract_literacy_20260610/PRE_REGISTRATION.md`;
- `experiments/action_object_contract_literacy_20260610/matrix.json`;
- `experiments/action_object_contract_literacy_20260610/prompt_variants.json`;
- `experiments/action_object_contract_literacy_20260610/budget.json`;
- `experiments/action_object_contract_literacy_20260610/failure_taxonomy.json`;
- `experiments/action_object_contract_literacy_20260610/fixture_failed_live_run_cycle1_evaluation.json`.

Evaluator and tests:

- `src/hamutay/memory/contract_literacy.py`;
- `tests/unit/test_contract_literacy.py`.

Source failure fixture:

- `experiments/live_autonomy_pilot_20260609/runs/c39ba9a3-9dda-48f2-82f6-cb90f8229bae/cycle_01_provider_response.json`;
- `experiments/live_autonomy_pilot_20260609/runs/c39ba9a3-9dda-48f2-82f6-cb90f8229bae/evaluation.json`.

## Non-Goals

- broad model comparison;
- proving or disproving identity, autonomy, or moral patienthood;
- changing the live harness to silently repair action objects;
- two-cycle bounded-autonomy claims;
- artifact-quality non-inferiority or superiority claims.
