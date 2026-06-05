# Pre-Registration: Scheduled Walk Protected Merge Gate

Date: 2026-06-05

## Research Question

When scheduled wakes run with framework-owned fields protected at merge time,
does the event-loop scaffold preserve continuity while still exposing
first-pass task-evidence failures and protected-field attempts as data?

The strict scheduled-walk continuity gate showed that validator repair can
restore graph-walk evidence and continuity fields. The protected merge
observability gate showed deterministic protection and logging in fake-backend
sessions. This live gate combines those mechanisms.

## Hypotheses

- H181: Scheduled walk context still resolves when live merge protection is
  enabled.
- H182: Final scheduled-wake states preserve protected framework fields
  `cycle` and `_activity_log`.
- H183: Protected-field attempts, if any, are logged explicitly as merge
  diagnostics rather than silently discarded.
- H184: First-pass task-evidence failures remain visible under protected merge.
- H185: Strict repair remains bounded and can still produce strict-valid final
  state.

## Predictions

The expected result is that protected merge does not materially change
scheduled walk context delivery or task-evidence repair. It should prevent
final drift on `cycle` and `_activity_log`, and it should log any protected
attempts made by first-pass or repair output.

It is possible that protected merge changes fewer final states than expected,
because the prior strict repair prompt already corrected `cycle`. If so, the
value of this gate is diagnostic: it should show whether the model still tries
to touch protected fields even when final state is valid.

## Method

Reuse the strict scheduled-walk continuity runner with one change:

- construct `OpenTasteSession` with
  `protected_state_fields={"cycle", "_activity_log"}`.

Use the same live substrate:

- model: `deepseek/deepseek-v4-pro` through OpenRouter;
- replicates: 4;
- `max_tokens`: 2048;
- behavior-seeded initialization;
- one scheduled event with adjacent `walk` context;
- strict validator checking graph evidence and continuity;
- one bounded repair attempt.

The runner will augment `results.json` with merge-diagnostic counts extracted
from the JSONL cycle records.

## Falsification Criteria

- H181 is falsified if completed events do not receive four-entry walk context.
- H182 is falsified if any final state has missing/wrong `cycle` or has lost a
  prior `_activity_log` solely because of model deletion.
- H183 is falsified if protected attempts appear in raw output but are not
  recorded in `state_merge_diagnostics`.
- H184 is falsified if first-pass failures disappear from validation records.
- H185 is falsified if no completed wake reaches strict-valid final state or if
  any wake uses more than one repair call.

## Analysis Plan

Analyze:

- scheduled context delivery;
- first-pass validation status;
- final strict validity;
- protected merge diagnostic counts;
- protected update/delete attempt keys;
- bounded wake call counts;
- final protected-field state.

Interpret protected attempts as protocol-mismatch evidence, even when hard
reservation prevents final state damage.
