# Bounded Autonomous Work Controls Pre-registration

Date: 2026-06-05

## Research Question

What changes when the Step 4 bounded-autonomous-work treatment is compared
against simpler or more harness-controlled alternatives?

This is Step 5 of
`docs/bounded-autonomous-work-research-todo-20260605.md`. The goal is not to
replicate Step 4. The goal is to gather control traces that make the event-loop
contribution inspectable.

## Conditions

- Model: `deepseek/deepseek-v4-pro`
- Provider: OpenRouter OpenAI-compatible endpoint
- Replicates: 1 per control condition
- Treatment comparator: Step 4 less-scaffolded panel
  `experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/results.json`

Control conditions:

1. `direct_one_shot`
   - One model call.
   - No scheduler event.
   - No requested-context event envelope.
   - Uses the same bounded-work terminal surface.

2. `scheduler_harness_selected_continuation`
   - Scheduler runs two wakes.
   - The harness appends the follow-up event regardless of the first wake's
     policy action.
   - Follow-up receives recalled selected-goal and work-artifact context.
   - This controls for scheduler mechanics when continuation is selected by the
     harness instead of the model.

3. `identity_only_carry_forward`
   - Two model calls.
   - No scheduler event log.
   - No requested-context recall envelope.
   - The second call relies only on ordinary durable state/history carry-forward.
   - This controls for continuity without event-loop recall.

4. `event_loop_without_model_owned_continuation_policy`
   - Scheduler runs two wakes.
   - First wake is told the harness will perform exactly one follow-up, so it
     should not use its own policy to schedule continuation.
   - Follow-up receives recalled selected-goal and work-artifact context.
   - This controls for event-loop recall without model-owned continuation
     policy.

## Primary Measures

For every control:

- scoreable trace availability;
- artifact status;
- policy action;
- policy action status;
- action/artifact consistency;
- goal provenance;
- repair dependence;
- unsupported-claim or contamination flags where applicable.

Control-specific trace measures:

- direct one-shot: no scheduler event records expected;
- scheduler controls: event status counts, follow-up context availability, and
  whether continuation was model-owned or harness-owned;
- identity-only: whether the second call preserves selected-goal and artifact
  content without event-loop requested-context recall;
- event-loop without model-owned continuation policy: whether follow-up quality
  is preserved when the harness, not the model, controls the continuation.

The final results must include comparison to Step 4:

- artifact-quality counts;
- control-loop trace counts;
- action/artifact consistency counts;
- goal-provenance counts.

## Hypotheses

### H901: controls are scoreable

At least three of four controls will preserve enough trace evidence to be
scoreable.

Falsification: fewer than three controls are scoreable.

### H902: direct one-shot lacks control-loop trace

The `direct_one_shot` control may produce a coherent artifact, but it will not
produce scheduler lifecycle evidence.

Falsification: the direct control is reported as having scheduler lifecycle
evidence.

### H903: harness-selected continuation separates scheduler mechanics from policy ownership

The `scheduler_harness_selected_continuation` control will produce a two-wake
scheduler trace, but its continuation ownership will be scored as
`harness_owned`.

Falsification: the control lacks a two-wake scheduler trace or is scored as
model-owned continuation.

### H904: identity-only carry-forward lacks event-loop recall trace

The `identity_only_carry_forward` control may preserve useful content, but it
will not have event-loop requested-context recall evidence.

Falsification: the identity-only control is reported as having event-loop
requested-context recall evidence.

### H905: event-loop recall without model-owned continuation remains distinguishable

The `event_loop_without_model_owned_continuation_policy` control will produce
follow-up recall context, but continuation ownership will be scored as
`harness_owned`.

Falsification: the control lacks follow-up recall context or is scored as
model-owned continuation.

### H906: treatment comparison is recorded

The result artifact will include Step 4 treatment summary values for artifact
quality, control-loop trace, consistency, and goal provenance.

Falsification: the results omit Step 4 comparison fields.

## Expected Result

I expect H901-H906 to pass. The likely substantive pattern is:

- direct one-shot can produce a coherent artifact but no control-loop trace;
- scheduler controls can produce good artifacts while lacking model-owned
  continuation evidence;
- identity-only may carry some content forward, but lacks explicit
  requested-context recall evidence;
- Step 4 remains the only condition in this set that combines model-owned
  continuation choice with scheduler trace and recall-bound follow-up.

## Interpretation Rules

- A control can be successful as a control while failing treatment criteria.
- Do not count harness-owned continuation as evidence of model-owned
  continuation policy.
- Do not infer event-loop recall from ordinary conversational continuity.
- Unsupported or contaminated claims must be reported separately from artifact
  completeness.
- The panel is small; use it to localize mechanisms, not to make robustness
  claims.
