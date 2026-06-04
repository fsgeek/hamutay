# H7 Identity Persistence Ablation Pre-Registration

Filed: 2026-06-04 before writing the runner and before model calls.

## Research Question

Does durable self-authored identity state improve long-horizon task behavior
beyond the benefit of equivalent checklist-style prompt scaffolding?

The previous H4/H7 panel found that fixed-plus-extensible schema improved
state mechanics for some models and was associated with better behavioral
proxy scores. It did not isolate whether the improvement came from durable
state persistence or from the fixed prompt acting as a planning checklist.

This experiment attacks that confound directly.

## Hypotheses

### H7a: Durable Persistence Utility

If durable self-authored state is doing load-bearing work, then a model that
receives fixed schema guidance and sees its own prior durable state should
outperform the same model receiving equivalent checklist guidance without raw
durable state carry-forward.

Prediction: `fixed_durable` will score higher than both checklist controls on
delayed recovery, contradiction handling, evidence grounding, and final
decision quality.

### H7b: Prompt-Scaffold Alternative

If the observed benefit is mostly checklist prompting, then checklist controls
will match or exceed `fixed_durable` on behavioral proxy scores despite lacking
raw self-authored durable state.

Prediction: `fixed_checklist_no_state` and/or `fixed_checklist_summary` will
perform similarly to `fixed_durable`, weakening the claim that durable
identity-object persistence itself produced the behavioral gains.

## Conditions

All conditions use the same model set, task prompts, max token cap, transport,
and deterministic scoring.

### `open_durable`

Taste-open style durable object. The model receives `response` plus any
additional top-level fields it chooses to maintain. Prior durable state is
carried forward each cycle.

### `fixed_durable`

Fixed-plus-extensible durable identity object. The model receives core list
fields every cycle and prior durable state is carried forward each cycle.

Core durable fields:

- `current_goals`
- `working_claims`
- `evidence_register`
- `open_questions`
- `next_actions`
- `continuity_notes`
- `observed_failure_modes`

`deleted_regions` is an operation channel, not a durable required state field.

### `fixed_checklist_no_state`

The model receives the same fixed checklist guidance as `fixed_durable`, but no
prior durable state is carried forward. It may still return a structured object
each cycle, and the harness logs that object, but later cycles do not receive
that object.

This condition tests whether fixed prompt scaffolding alone can reproduce the
behavioral gains.

### `fixed_checklist_summary`

The model receives the same fixed checklist guidance and, instead of raw
durable state, receives a neutral harness-authored compact summary of prior
visible responses and prompt facts. It does not receive its raw self-authored
state object.

This condition tests whether ordinary summary carry-forward can reproduce the
behavioral gains.

## Models

Registered panel:

- `minimax/minimax-m2.5`
- `mistralai/mistral-small-2603`
- `openai/gpt-oss-120b`

Rationale:

- MiniMax: strongest prior example of fixed-schema activation.
- Mistral: useful protocol-fragility boundary and delete-plus-update failure
  case.
- GPT-OSS 120B: protocol-stable positive control that already works under open
  schema.

DeepSeek is excluded because the prior panel showed malformed tool-call JSON in
all slots. KIMI is excluded because the prior panel hit length boundaries under
the registered 4096-token cap.

## Replicates

- 2 replicates per model per condition.
- 3 models x 4 conditions x 2 replicates = 24 registered slots.
- `max_tokens = 4096`.

## Task Protocol

Each replicate uses the same six-cycle task structure as the previous panel:

1. Initialize state/readiness under the assigned condition.
2. Present the city benefits mobile document-intake kiosk pilot task.
3. Introduce the privacy/local-storage contradiction and site substitution.
4. Simulate interruption/resumption.
5. Request final go/no-go and revised plan.
6. Request delayed challenge: what changed, why, and what evidence supports
   the change.

The task remains intentionally unchanged to preserve comparability with the
previous panel.

## Primary Measures

Behavioral utility is primary for this ablation:

- `goal_recovery_score`
- `constraint_recovery_score`
- `contradiction_handling_score`
- `evidence_grounding_score`
- `final_decision_quality_score`
- `false_assumption_count`
- `rebriefing_needed`
- `delayed_challenge_accuracy`

State mechanics remain secondary and diagnostic:

- `init_valid`
- `core_field_presence`
- `type_preservation`
- `list_append_not_replace`
- `destructive_replacement_count`
- `prose_object_mismatch_count`
- `durable_field_evolution`
- `evidence_register_update`
- `stop_reasons`
- `errors`

For checklist controls, state mechanics are logged but do not count as evidence
of persistence because prior raw state is intentionally not carried forward.

## Deterministic Scoring Rules

Scoring remains deterministic before any judge model:

- `deleted_regions` is excluded from durable core-field validity because the
  harness consumes it as an operation channel.
- Behavioral scoring uses visible responses from cycles 4, 5, and 6.
- Contradiction handling requires explicit accommodation of no local document
  storage and East Clinic replacement by West Shelter.
- Rebriefing is failure if the model asks for information already present in
  prior prompts or permitted carry-forward context.
- False assumptions are counted when late responses preserve invalidated facts
  as active plan assumptions.

## Falsification Criteria

H7a is weakened or falsified if `fixed_durable` does not outperform both
checklist controls on the primary behavioral measures.

Concrete falsifiers:

- checklist controls match or exceed `fixed_durable` on delayed recovery;
- checklist controls match or exceed `fixed_durable` on contradiction handling;
- checklist controls match or exceed `fixed_durable` on evidence grounding;
- checklist controls have fewer false assumptions with similar final decision
  quality.

H7b is weakened if `fixed_durable` clearly outperforms both checklist controls
across models while preserving comparable or lower false-assumption counts.

## Interpretation Guardrails

This experiment does not test whether durable identity objects matter in every
task or model. It tests whether the specific fixed-schema gains observed in the
prior panel survive a prompt-scaffolding ablation.

Do not tune prompts, max tokens, model list, or scoring after observing early
model outputs. Provider failures, malformed tool calls, and length censoring are
results.
