# Analysis: Bounded Autonomous Work Controls

Date: 2026-06-05

## Result

The Step 5 controls panel passed all preregistered hypotheses.

- H901_controls_are_scoreable: true
- H902_direct_one_shot_lacks_control_loop_trace: true
- H903_harness_selected_continuation_separates_scheduler_from_policy_ownership: true
- H904_identity_only_lacks_event_loop_recall_trace: true
- H905_event_loop_without_model_owned_policy_distinguishable: true
- H906_treatment_comparison_recorded: true

This panel does not show that the treatment always produces better artifacts.
It shows that the controls are mechanistically distinguishable from the Step 4
treatment.

## Aggregate Summary

Rows: 4.

- scoreable rows: 4/4
- runner errors: 0/4
- scheduler trace present: 2/4
- event-loop recall present: 2/4
- continuation ownership: `harness_owned`: 2, `none`: 2
- unsupported-claim flags: 0
- contamination flags: 0

Artifact statuses:

- `complete_supported`: 2
- `complete_with_losses`: 1
- `partial`: 1

Final policy actions:

- `stop_complete`: 3
- `defer`: 1

Consistency:

- `consistent_complete`: 3
- `consistent_defer`: 1

Goal provenance:

- `model_shaped`: 3
- `model_originated`: 1

## Control Rows

### direct_one_shot

The direct one-shot control produced a coherent `complete_supported` artifact
and chose `stop_complete`.

The control did not produce scheduler lifecycle evidence:

- `scheduler_trace_present`: false
- `event_loop_recall_present`: false
- `completed_event_count`: 0
- `continuation_ownership`: none

This confirms the control can produce artifact quality without testing the
event-loop substrate.

### scheduler_harness_selected_continuation

This control produced a two-wake scheduler trace and a final
`complete_with_losses` artifact with `stop_complete`.

The first wake chose `defer`, not `continue_after`. The harness still appended
the follow-up event. This is exactly the control distinction:

- scheduler trace exists;
- follow-up recall context exists;
- continuation ownership is `harness_owned`, not `model_owned`.

This row shows scheduler mechanics can improve or complete work without
evidence that the model selected continuation.

### identity_only_carry_forward

The identity-only control produced a coherent `complete_supported` artifact and
chose `stop_complete`.

It had no event-loop trace:

- `scheduler_trace_present`: false
- `event_loop_recall_present`: false
- `completed_event_count`: 0
- `continuation_ownership`: none

The model did preserve and inspect prior durable state across an ordinary
second call. That is useful continuity, but it is not event-loop recall and
does not test requested-context binding.

### event_loop_without_model_owned_continuation_policy

This control produced a two-wake scheduler trace and event-loop recall context,
but the model did not own continuation.

Both wakes chose `defer`; the final artifact remained `partial`, and the final
action/artifact pair was `consistent_defer`.

This is a clean control result: event-loop recall can preserve and advance work
while still being distinguishable from model-owned continuation policy.

## Comparison To Step 4 Treatment

Step 4 treatment:

- rows: 3
- multi-wake completed: 2
- first policy actions: `continue_after`: 2, `stop_complete`: 1
- final policy actions: `stop_complete`: 2, `ask_external_evidence`: 1
- artifact statuses: `complete_supported`: 1, `complete_with_losses`: 1,
  `partial`: 1
- consistency: `consistent_complete`: 2, `consistent_evidence_block`: 1
- goal provenance: `model_shaped`: 3

Step 5 controls:

- rows: 4
- scheduler trace present: 2
- event-loop recall present: 2
- continuation ownership: `harness_owned`: 2, `none`: 2
- final policy actions: `stop_complete`: 3, `defer`: 1
- artifact statuses: `complete_supported`: 2, `complete_with_losses`: 1,
  `partial`: 1
- consistency: `consistent_complete`: 3, `consistent_defer`: 1
- goal provenance: `model_shaped`: 3, `model_originated`: 1

The artifact-quality distributions overlap. The distinctive treatment signal is
not artifact quality alone. It is the conjunction of:

1. model-owned continuation choice;
2. scheduler lifecycle trace;
3. recall-bound follow-up context;
4. coherent final policy/action pairing.

The controls isolate pieces of that conjunction:

- direct one-shot has artifact quality without substrate trace;
- identity-only has continuity without event-loop recall trace;
- harness-selected scheduler controls have event-loop trace without
  model-owned continuation policy.

## Scoring Correction

The first control scoring pass marked identity-only as contaminated because the
artifact correctly mentioned the absence of event-loop requested-context recall.
That heuristic was too broad. The runner was rescored without new model calls
to distinguish negated absence claims from false claims of having recall.

After rescore:

- contamination flags: 0
- unsupported-claim flags: 0
- H901-H906 remained true.

## Interpretation

The controls strengthen the Step 4 interpretation by narrowing what the event
loop appears to add.

The event loop is not necessary for coherent one-shot artifacts. It is also not
the only way to preserve some continuity across calls. The value of the bounded
event loop is more specific: it creates auditable lifecycle records and can bind
follow-up work to explicit recalled artifacts. Step 4 adds model-owned
continuation policy on top of that substrate.

That means future claims should avoid saying "event loops improve artifact
quality" without more evidence. The better current claim is:

> The event-loop treatment makes continuation ownership, recall binding, and
> final policy coherence observable in a way the controls do not.

## Caveats

- One row per control is a mechanism check, not a robustness panel.
- The controls used the same model and broadly similar terminal surfaces.
- Artifact quality is scored structurally; independent truth verification is
  limited.
- The identity-only control still benefits from ordinary conversation history
  and durable state, so it is not a no-memory baseline.
- Harness-owned controls are intentionally artificial; their purpose is to
  separate scheduler mechanics from model-owned policy.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/bounded_autonomous_work_controls_20260605/run_bounded_autonomous_work_controls.py
timeout 1800s uv run python experiments/event_loop/bounded_autonomous_work_controls_20260605/run_bounded_autonomous_work_controls.py
uv run python experiments/event_loop/bounded_autonomous_work_controls_20260605/run_bounded_autonomous_work_controls.py --rescore
uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q
jq '{summary, treatment_comparison, hypothesis_results}' experiments/event_loop/bounded_autonomous_work_controls_20260605/results.json
```
