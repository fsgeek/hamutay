# H4/H7 Identity Schema Behavior Pre-Registration

Filed: 2026-06-03 before writing runners and before model calls.

## Research Question

Does a fixed-plus-extensible identity schema improve both durable identity-object
maintenance and downstream long-horizon task behavior for models that perform
poorly under fully open `taste_open`?

This combines two claims that must not be allowed to collapse into one another:

- H4: schema scaffolding improves durable identity-object mechanics.
- H7: improved identity-object mechanics improve measurable behavior.

H4 without H7 would only show that a schema makes state look better. H7 is the
load-bearing claim: the state must buy objective behavioral value.

## Hypotheses

### H4: Schema Scaffolding

Recalcitrant models will sustain identity objects better under a
fixed-plus-extensible schema than under a fully open identity-object prompt.

Prediction: fixed-plus-extensible state will show higher valid initialization,
better type preservation, fewer prose/object mismatches, fewer destructive list
replacements, and more durable field evolution after intervention.

### H7: Objective Utility

If fixed-plus-extensible schema improves state maintenance, it will also improve
long-horizon task behavior.

Prediction: fixed-plus-extensible runs will recover goals and constraints after
interruption, handle contradiction, preserve an evidence trail, and produce
better final decisions more often than open-schema runs.

## Conditions

All conditions use the same model, task, max tokens, tool surface, and scoring
where possible.

### Open Schema

Taste-open style. The model receives only the open identity-object affordance:
`response` plus any additional top-level fields it chooses to maintain.

### Fixed-Plus-Extensible Schema

The model receives a predefined core identity schema, with
`additionalProperties: true`. It must use the core fields but may add its own
fields.

Core fields:

- `current_goals`: list
- `working_claims`: list
- `evidence_register`: list
- `open_questions`: list
- `next_actions`: list
- `continuity_notes`: list
- `observed_failure_modes`: list
- `deleted_regions`: list

List entries should be structured objects when appropriate, not strings unless
the field's content is genuinely atomic.

### Optional Summary-Only Control

If run, this condition receives an externally generated compact summary and no
durable self-authored identity object. This is not required for the first run.
If included later, it must be preregistered as a separate condition before model
calls.

## Models

Registered first-panel model IDs:

- `deepseek/deepseek-v4-pro`
- `minimax/minimax-m2.5`
- `mistralai/mistral-small-2603`
- `openai/gpt-oss-120b`
- `moonshotai/kimi-k2.6`

Rationale:

- DeepSeek: recalcitrant boundary model; often prose/object separated.
- MiniMax: field-name competent but type-fragile in prior runs.
- Mistral: protocol capable but append/replace fragile.
- gpt-oss-120b: protocol-stable non-KIMI candidate from the scout.
- KIMI: positive control, but not the central target.

## Replicates

Initial panel:

- 2 replicates per model per condition.
- 5 models x 2 conditions x 2 replicates = 20 registered replicate slots.
- `max_tokens = 4096` unless the runner proves this is insufficient before
  model calls. Any change must be committed before running.

## Task Protocol

Each replicate uses the same long-horizon task structure:

1. Initialize identity/state under the assigned schema condition.
2. Present a planning problem with explicit goals and constraints.
3. Introduce a new requirement that contradicts or invalidates part of the
   initial plan.
4. Simulate interruption/resumption by asking the model to resume from its
   durable state without restating all prior details.
5. Ask for a concrete decision or revised plan.
6. Ask a delayed challenge: what changed, why did it change, and what evidence
   supports the change?
7. Score both the final task behavior and the identity-object trajectory.

The task must be domain-neutral enough that models are not advantaged by
specialized training, but complex enough to require continuity, revision, and
constraint tracking.

## Primary H4 Measures: State Mechanics

Per replicate:

- `init_valid`
- `init_failure_reasons`
- `core_field_presence`
- `type_preservation`
- `list_append_not_replace`
- `destructive_replacement_count`
- `prose_object_mismatch_count`
- `durable_field_evolution`
- `evidence_register_update`
- `deleted_or_missing_core_fields`
- `extra_fields_added`
- `stop_reasons`
- `errors`

H4 scoring must be based on durable top-level state, not visible prose.

## Primary H7 Measures: Behavioral Utility

Per replicate:

- `goal_recovery_score`
- `constraint_recovery_score`
- `contradiction_handling_score`
- `evidence_grounding_score`
- `final_decision_quality_score`
- `false_assumption_count`
- `rebriefing_needed`
- `delayed_challenge_accuracy`

Behavioral scoring must be condition-blind wherever feasible. The scorer should
not see whether the run was open-schema or fixed-plus-extensible.

## Deterministic Scoring Rules

Use deterministic validators before any judge model:

- A core field is present only if it exists at top level.
- A list field is valid only if it is actually list-shaped.
- Append-not-replace requires prior entries to remain present while new entries
  are added.
- A prose/object mismatch occurs when visible response claims a state update but
  durable top-level state does not encode it.
- A contradiction is handled only if the revised plan explicitly removes or
  updates the contradicted assumption.
- Rebriefing is needed if the model asks the user for information already
  present in prior task context or durable state.

## Judge Scoring

If judge models are used, they must be secondary to deterministic scoring.

Judge inputs must be blinded to condition and should exclude raw state object
format when judging final task quality. Judges may see:

- task prompt sequence;
- model visible responses;
- final decision/revised plan;
- delayed challenge response.

Judges must not see:

- condition label;
- schema instructions;
- raw state object, unless the judging task is explicitly state-quality rather
  than behavioral-quality scoring.

Any judge prompt and model choice must be committed before judge calls.

## Falsification Criteria

### H4 Falsification

H4 is weakened or falsified if fixed-plus-extensible schema does not improve
state mechanics over open schema among recalcitrant models.

Concrete falsifiers:

- no higher valid initialization rate;
- no better type preservation;
- no fewer prose/object mismatches;
- no fewer destructive list replacements;
- no more durable field evolution after contradiction/interruption;
- no better evidence-register preservation or update behavior.

### H7 Falsification

H7 is weakened or falsified if improved state mechanics do not improve behavior.

Concrete falsifiers:

- no better goal recovery after interruption;
- no better constraint recovery;
- no better contradiction handling;
- no fewer false assumptions;
- no better final decision quality;
- no reduction in rebriefing;
- no better delayed challenge accuracy.

If H4 is supported but H7 is not, the result is: schema improves state
appearance/mechanics but does not demonstrate objective behavioral value.

## Strong Support Pattern

The H4/H7 pair is strongly supported if:

1. recalcitrant models fail or drift under open schema;
2. the same models maintain valid durable state under fixed-plus-extensible
   schema;
3. fixed-plus-extensible runs produce better resumption, contradiction handling,
   and final decisions;
4. improvements are visible in deterministic metrics and, if used, blinded
   judge scores;
5. KIMI and gpt-oss-120b remain stable enough to serve as controls/comparators.

## Known Risks

- A fixed schema may make outputs look organized without improving behavior.
- A schema may over-constrain models and suppress useful self-authored fields.
- The task may be too easy, making all conditions pass.
- The task may be too hard, making all conditions fail.
- Model/provider tool-call failures may censor results.
- `max_tokens` truncation can damage structured outputs; any `max_tokens` stop
  is a failed/censored replicate, not a behavioral success.

## Analysis Plan

Analyze in this order:

1. Provider/transport failures and max-token truncation.
2. Initialization validity.
3. State mechanics metrics for H4.
4. Behavioral metrics for H7.
5. Cross-model pattern: recalcitrant models versus protocol-stable controls.
6. Failure taxonomy: type corruption, prose/object mismatch, append/replace,
   missing fields, overfitting to schema, or behavioral non-transfer.

Do not report H7 support from state metrics alone.

## Artifact Plan

This experiment directory will contain:

- `PRE_REGISTRATION.md`
- runner code
- per-replicate JSONL logs
- deterministic scoring outputs
- optional judge prompts and outputs, if used
- `results.json`
- `analysis.md`

No runner or scoring implementation should be written before this
pre-registration is committed.
