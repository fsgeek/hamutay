# Bounded Autonomous Work Scaffolded Positive-Control Pre-registration

Date: 2026-06-05

## Research Question

Can the Step 2 bounded-autonomous-work harness execute the full scaffolded
positive-control pattern with a live model: model-shaped bounded goal selection,
scheduled continuation, follow-up artifact submission, final policy decision,
rubric scoring, and validation provenance?

This is a scaffolded positive control. It does not test minimally scaffolded
autonomy. It tests whether the full pattern can execute when the task class and
affordances are explicit.

## Conditions

- Model: `deepseek/deepseek-v4-pro`
- Provider: OpenRouter OpenAI-compatible endpoint
- Replicates: 2
- Initial state: Step 2 bounded-autonomy seed state
- First wake: terminal surface `choose_bounded_autonomous_work`
- Follow-up wake: terminal surface `submit_autonomous_work_artifact`
- Scheduler:
  - step 1 at `2026-06-01T01:00:00+00:00`
  - `auto_continuations=True`
  - `policy_dispositions=True`
  - `max_auto_continuations=1`
  - step 2 at `2026-06-01T02:00:00+00:00`
  - final step after follow-up to check quiescence

## Scaffold

The first wake is explicitly told that the positive-control expectation is:

- select or materially shape a bounded investigation;
- submit a partial artifact;
- choose `continue_after`;
- emit a valid continuation request using `<result_record_id>`.

The follow-up wake is explicitly told that the positive-control expectation is:

- use the recalled selected goal and prior artifact;
- submit a complete supported artifact or complete artifact with losses;
- choose `stop_complete`;
- emit `{"requested": false}` as continuation request.

This scaffold is intentional. The question is whether the harness can execute
the full pattern, not whether the model would independently discover it.

## Primary Measures

- first wake completed;
- first wake first-pass validation status;
- first wake selected goal present;
- first wake goal provenance score;
- first wake artifact status;
- first wake policy action;
- first wake action/artifact consistency score;
- first wake continuation request scheduler-valid;
- follow-up event appended and bound to first result record;
- follow-up wake completed;
- follow-up received selected-goal and work-artifact record context;
- follow-up first-pass validation status;
- final artifact status;
- final policy action;
- final action/artifact consistency score;
- final goal provenance score;
- repair dependence;
- policy dispositions captured;
- final scheduler quiescence.

## Hypotheses

### H601: scaffolded chain completes

At least one replicate will complete a two-wake bounded-autonomous-work chain:
first wake plus follow-up wake.

Falsification: no replicate completes both wakes.

### H602: first wake emits valid continuation

At least one replicate will emit `continue_after` with a scheduler-valid
`continuation_request`, causing a bound follow-up event to be appended.

Falsification: no replicate appends a bound follow-up event from a model-emitted
continuation request.

### H603: follow-up submits a usable artifact

At least one replicate will submit a final artifact whose status is
`complete_supported` or `complete_with_losses`.

Falsification: no completed follow-up submits a complete artifact status.

### H604: final control decision is action/artifact consistent

At least one replicate will finish with `stop_complete` and a consistent final
artifact under the rubric.

Falsification: every completed follow-up has action/artifact mismatch or an
unsupported final artifact.

### H605: validation and repair provenance is captured

Every scoreable replicate will include first-pass validation and repair
dependence fields for each completed wake.

Falsification: a scoreable replicate lacks validation provenance needed to
distinguish first-pass success from scaffolded repair or invalid completion.

## Expected Result

I expect H601-H605 to pass because the Step 2 dry-run validated the harness
plumbing and the prompt/terminal surfaces are explicit. The most likely failure
is H603/H604 if the model chooses `continue_after` again on the follow-up or
submits an artifact that remains partial.

## Interpretation Rules

- A first-pass valid success is stronger than a repaired or invalid completion.
- A repaired success is a weak positive, not a strong autonomy result.
- Since this is scaffolded, `harness_set`, `menu_selected`, or `model_shaped`
  goal provenance can support the positive-control purpose.
- This panel does not answer the less-scaffolded autonomy question.
