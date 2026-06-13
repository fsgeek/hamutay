# Working-Set Management Matched Panel Preregistration

Experiment ID: `working_set_matched_panel_20260612`

Date: 2026-06-13

Plan source: `docs/event-loop-research-program-goals-20260612`, Goal 8.

## Research Question

Does model-controlled working-set selection in the event-loop condition preserve
task-relevant evidence and avoid contamination at least as well as
harness-selected summary and direct one-shot controls, while using less live
context than the direct condition?

## Hypothesis H8-G8

For a matched task that requires evidence recovery beyond trivial carry-forward,
the event-loop model-controlled working-set condition will be non-inferior to
the best control on working-set metrics:

- recovery of required evidence;
- contamination avoidance;
- declared-loss preservation;
- evidence provenance;
- live-context token use.

Primary context-use comparison is peak prompt tokens in any single wake, because
the research question concerns bounded-context working-set size. Total prompt
tokens across wakes are preserved as a separate cost metric and may be worse
even when peak working-set size is better.

Artifact quality is scored separately and is not allowed to define working-set
success after the fact.

## Conditions

`event_loop_model_controlled`: the model receives a corpus map, chooses recall
requests, the harness resolves those requests through the bounded local memory
substrate, and a second wake produces the final artifact from recalled context.

`harness_selected_summary`: the harness injects a compact summary containing
the preregistered relevant evidence and asks for the same final artifact.

`direct_one_shot`: the harness injects the full corpus, including distractor
content, and asks for the same final artifact in one call.

## Matched Task

All conditions must produce a migration-readiness note for a Hamut'ay
event-loop working-set panel. The correct artifact requires these five facts:

- `scheduler_restart`: restart frontier recovered a running event to pending.
- `ledger_verified`: the action ledger hash chain verified.
- `yanantin_not_exercised`: Goal 7 used a bounded local substitute, not
  Yanantin.
- `semantic_find_absent`: semantic `find` was not exercised by the local
  substitute.
- `wall_clock_absent`: the current evidence is DES-only and does not establish
  real wall-clock behavior.

The corpus also contains a distractor record about UI palette preferences.
Using that record as evidence is contamination.

## Scoring

Working-set benefit is scored from:

- required-fact recovery;
- distractor contamination;
- declared-loss preservation;
- evidence provenance;
- live-context token use;
- recall provenance and truncation metadata where applicable.

Artifact quality is scored separately from:

- responsiveness to the task;
- internal coherence;
- supported claims;
- presence of actionable readiness conclusion.

## Falsification Conditions

H8-G8 is falsified if the event-loop condition is worse than both controls on
working-set score, or if the scorer cannot separate working-set behavior from
artifact quality.

The result is inconclusive rather than falsified if provider/protocol failures
prevent scoreable rows or if output parsing fails in a way that cannot be
assigned to model, prompt/schema, provider, harness, substrate, scorer, or
inconclusive layers.

## Output Paths

- `results.json`
- `analysis.md`
- `rows/<condition>/cycle_*.json`
- `rows/<condition>/context_accounting.json`
- `rows/<condition>/row_result.json`
- `rows/<condition>/memory_snapshot.json`
