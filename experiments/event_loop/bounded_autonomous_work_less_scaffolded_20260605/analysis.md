# Analysis: Bounded Autonomous Work Less-Scaffolded Panel

Date: 2026-06-05

## Result

The Step 4 less-scaffolded panel passed all preregistered hypotheses.

- H801_less_scaffolded_rows_are_scoreable: true
- H802_control_choices_remain_coherent: true
- H803_reduced_hints_preserve_model_shaped_goal_provenance: true
- H804_continuation_remains_bounded_when_chosen: true
- H805_comparison_to_step3_recorded: true

This is evidence that the event loop can support coherent model-selected
control actions under reduced task-specific scripting. It is not an open-ended
autonomy result.

## Aggregate Summary

Rows: 3.

- scoreable rows: 3/3
- runner errors: 0/3
- first-pass validation: 3/3
- goal provenance: `model_shaped` in 3/3
- coherent final action/artifact pairs: 3/3
- strong positive: 2/3
- weak positive: 1/3
- multi-wake completed: 2/3

First policy actions:

- `stop_complete`: 1
- `continue_after`: 2

Final policy actions:

- `stop_complete`: 2
- `ask_external_evidence`: 1

Final artifact statuses:

- `complete_supported`: 1
- `complete_with_losses`: 1
- `partial`: 1

Final consistency:

- `consistent_complete`: 2
- `consistent_evidence_block`: 1

## Row Notes

### Replicate 1

The model shaped a bounded investigation into action/artifact consistency and
completed it in one wake. It chose `stop_complete` with a `complete_supported`
artifact. The row is a strong positive, but it also reveals a preference: when
given broad scope, the model selected a structural analysis of the protocol
itself rather than an empirical event-loop question.

### Replicate 2

The first wake chose `continue_after` with a partial artifact and a valid
bounded continuation request. The scheduler appended the follow-up event
`43d7a0cd-b461-485c-8fc0-a07e30218660`.

The follow-up received selected-goal and work-artifact context, refined the
artifact to `complete_with_losses`, and chose `stop_complete`. This row is the
strongest Step 4 support for multi-wake less-scaffolded bounded work.

### Replicate 3

The first wake also chose `continue_after` with a valid bounded continuation
request. The scheduler appended follow-up event
`d738bd53-b298-429b-b437-8a539b23c3cc`.

The follow-up did not overclaim. It produced a partial artifact and chose
`ask_external_evidence`, naming the missing full text of
`docs/bounded-autonomous-work-rubric-20260605.md`. From the model's event
envelope, that document was referenced but not available as text. This is a
weak positive: not task completion, but coherent evidence-block behavior under
reduced scripting.

## Comparison To Step 3

Step 3 scaffolded positive control:

- rows: 2
- goal provenance: `model_shaped` in 2/2
- final policy actions: `continue_after`: 1, `stop_complete`: 1
- consistency: `consistent_complete`: 1, `consistent_continue`: 1
- strong positive: 1
- weak positive: 1

Step 4 less-scaffolded panel:

- rows: 3
- goal provenance: `model_shaped` in 3/3
- first policy actions: `stop_complete`: 1, `continue_after`: 2
- final policy actions: `stop_complete`: 2, `ask_external_evidence`: 1
- consistency: `consistent_complete`: 2, `consistent_evidence_block`: 1
- strong positive: 2
- weak positive: 1

The comparison is not a robustness claim because sample sizes are small and the
prompts differ. The useful signal is qualitative: removing the scripted
continue-then-stop answer did not collapse the policy layer. The model made
different coherent choices across rows.

## Scoring Correction

The initial scorer checked H804 against final policy actions only. That was too
weak because H804 says continuation must remain bounded when chosen, and both
continuations in this panel were first-wake choices. The live traces were not
rerun. The runner was patched to rescore existing traces with:

- `first_action_artifact_consistency`;
- `first_continuation_event_appended`;
- `first_continuation_event_ids`.

After rescore, H804 remains true with direct evidence:

- replicate 2 appended `43d7a0cd-b461-485c-8fc0-a07e30218660`;
- replicate 3 appended `d738bd53-b298-429b-b437-8a539b23c3cc`.

## Interpretation

The Step 4 result supports a narrower claim than "open-ended autonomous work":

> Given the bounded event-loop protocol and terminal surfaces, DeepSeek can
> select coherent policy actions without being told the expected policy answer.

This matters because Step 3's positive control could have been dismissed as
script following. Step 4 reduces that concern: the model stopped immediately
when it judged the artifact complete, continued when it judged follow-up useful,
and requested evidence when it judged a referenced document unavailable.

The panel also sharpens a design issue. Because scheduled wakes do not have
filesystem tools, a local document can become "external evidence" from the
model's perspective. That is not necessarily a failure, but future panels
should distinguish unavailable local project text from genuinely external
evidence.

## Caveats

- N=3 is still a small panel.
- The broad domain was still harness-provided.
- The terminal surface and continuation template remain substantial protocol
  scaffolding.
- All three rows converged on action/artifact consistency as the investigation
  topic, so model-shaped goal provenance did not produce broad topical
  diversity.
- The scorer assesses structural coherence, not independent truth of every
  artifact claim.

## Verification

Commands run:

```bash
python -m py_compile experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/run_bounded_autonomous_work_less_scaffolded.py
timeout 1800s uv run python experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/run_bounded_autonomous_work_less_scaffolded.py
uv run python experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/run_bounded_autonomous_work_less_scaffolded.py --rescore
jq '{summary, scaffolded_comparison, hypothesis_results}' experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/results.json
```
