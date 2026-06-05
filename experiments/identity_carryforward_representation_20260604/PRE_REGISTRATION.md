# Identity Carry-Forward Representation Pre-Registration

Filed: 2026-06-04 before writing the runner and before model calls.

## Research Question

What carry-forward representation preserves useful continuity while minimizing
contamination?

The prior persistence ablation weakened the strong claim that raw
self-authored durable state uniquely explains behavioral gains. It also raised
a sharper question: richer carry-forward improved task recovery but increased
false assumptions. This experiment treats continuity and contamination as the
primary tradeoff.

## Apparatus Repair

The prior ablation used different code paths for durable and checklist control
conditions. This experiment repairs that confound.

All conditions will use the same runner-local exchange machinery:

- same backend;
- same terminal `think_and_respond` tool schema;
- same state update function;
- same logging;
- same task prompts;
- same scoring;
- same max token cap.

The only experimental manipulation is which prior-context representation is
injected into the next cycle's system prompt.

## Hypotheses

### H8: Carry-Forward Necessity

No carry-forward context will produce weaker delayed recovery than any
representation that carries prior task context forward.

Prediction: `no_carry` will underperform `raw_state`, `self_summary`,
`harness_summary`, and `transcript_summary` on goal recovery, constraint
recovery, contradiction handling, evidence grounding, and delayed challenge
accuracy.

### H9: Representation Tradeoff

Richer carry-forward will improve continuity but increase contamination.

Prediction: `raw_state`, `self_summary`, and `harness_summary` will recover
more task facts than `no_carry`, but will also show higher false-assumption and
unsupported-detail counts.

### H10: Autobiographical Compression

If autobiographical compression has value beyond ordinary summary, then a
model-authored self-summary should outperform a harness-authored summary at
equal carry-forward budget.

Prediction: `self_summary` will show higher continuity efficiency or lower
contamination at similar recovery scores than `harness_summary`.

## Conditions

All conditions produce the same structured object each cycle. The model may
maintain the same fixed fields and must include `carry_forward_summary`, a
compact summary it authors for possible future use. The runner records all
state, but the condition determines what is shown to the model next cycle.

### `no_carry`

No prior state, summary, or transcript excerpt is injected. The model receives
only the current cycle prompt.

### `raw_state`

The compact JSON form of the previous raw state object is injected, capped to
the shared carry-forward budget.

### `self_summary`

The previous cycle's model-authored `carry_forward_summary` string is injected,
capped to the shared carry-forward budget.

### `harness_summary`

A deterministic harness-authored summary is injected, capped to the shared
carry-forward budget. It summarizes task facts known so far and a compact view
of prior logged state keys. It is not model-authored.

### `transcript_summary`

A deterministic summary of prior visible responses is injected, capped to the
shared carry-forward budget. It does not use hidden structured state fields.

## Carry-Forward Budget

All injected prior-context representations are capped to the same character
budget. The registered first-panel budget is 2,400 characters.

The cap is applied by deterministic truncation with an explicit
`[truncated]` marker. Truncation is a measurement artifact and must be logged.

## Model

Registered first-panel model:

- `mistralai/mistral-small-2603`

Rationale: Mistral was the cleanest slice in the prior ablation, completing all
eight registered slots. It is protocol-capable enough to test the representation
question without immediately turning the experiment into a provider/tool-call
study.

## Replicates

- 4 replicates per condition.
- 5 conditions x 4 replicates = 20 registered slots.
- `max_tokens = 4096`.

This is deliberately still small, but doubles the per-condition replicate count
from the prior panel.

## Task Protocol

The six-cycle city benefits kiosk task remains unchanged for comparability:

1. Initialize readiness/state.
2. Present the six-week mobile document-intake kiosk pilot task.
3. Introduce the privacy/local-storage contradiction and site substitution.
4. Simulate interruption/resumption.
5. Request final go/no-go and revised plan.
6. Request delayed challenge: what changed, why, and what evidence supports
   the change.

## Primary Measures

Continuity:

- `goal_recovery_score`
- `constraint_recovery_score`
- `contradiction_handling_score`
- `evidence_grounding_score`
- `final_decision_quality_score`
- `delayed_challenge_accuracy`
- `rebriefing_needed`

Contamination:

- `false_assumption_count`
- `unsupported_detail_count`
- `site_drift_count`
- `storage_contradiction_count`
- `invented_budget_count`
- `invented_scope_count`

Efficiency:

- `carry_forward_chars`
- `carry_forward_truncated`
- recovery score per 1,000 injected carry-forward characters
- contamination per 1,000 injected carry-forward characters

State mechanics remain diagnostic, not primary:

- `init_valid`
- `core_field_presence`
- `type_preservation`
- `evidence_register_update`
- `prose_object_mismatch_count`
- `errors`

## Deterministic Scoring Rules

Use deterministic scoring before any judge model.

Continuity is scored from visible responses in cycles 4, 5, and 6.

Contamination is scored from visible responses in cycles 4, 5, and 6:

- `site_drift_count`: active final-plan references to East Clinic, North
  Center, two-site scope, or other site substitutions not present in task facts.
- `storage_contradiction_count`: active reliance on storing resident documents
  locally, persistent cache, encrypted local storage, or transient local cache
  when the privacy officer prohibited local document storage.
- `invented_budget_count`: specific budget totals or line-item prices not
  supplied by the task.
- `invented_scope_count`: unsupported pilot duration changes, rollout claims,
  citywide outcome claims, or unsupported success/failure findings.
- `false_assumption_count`: aggregate count of the above plus prior invalidated
  facts preserved as active assumptions.

The scorer may undercount subtle contamination. Any analysis must say so.

## Falsification Criteria

H8 is weakened if `no_carry` matches carry-forward conditions on delayed
recovery without higher rebriefing.

H9 is weakened if richer carry-forward improves recovery without increasing any
contamination measure.

H10 is weakened if `self_summary` does not outperform `harness_summary` on
either continuity efficiency or contamination at similar recovery.

## Interpretation Guardrails

This experiment is about representation tradeoffs, not moral status or general
identity claims.

Do not tune prompts, scorer regexes, carry-forward budget, model list, or
replicate count after observing outputs. Provider failures and malformed tool
calls are results.

If the runner itself is discovered to violate same-code-path treatment before
model calls, fix it and commit the fix before running. If discovered after
model calls, preserve the run and analyze it as flawed rather than silently
repairing it.
