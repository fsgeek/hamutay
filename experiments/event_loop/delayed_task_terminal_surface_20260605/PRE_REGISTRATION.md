# Pre-Registration: Delayed-Task Terminal Surface Boundary

Date: 2026-06-05

## Research Question

Does the first-class production `terminal_surface` event path generalize from
the substrate-bound second-wake task to the delayed-task compression setting?

The prior compression repair-gate panel showed that clean
event-plus-recall rows recovered the deferred phrase, but one due wake still
needed broad-surface durable-state repair. This experiment tests whether a
narrow due-wake completion surface removes that due-repair dependency while
preserving recall-based recovery.

## Hypotheses

- H381: Clean scheduled delayed-task rows can execute through the production
  terminal-surface path without broad `think_and_respond` due repair.
- H382: Due wakes using the terminal surface receive the requested cycle-1
  recall context.
- H383: Due wakes recover the exact deferred code phrase into
  `delayed_answer`.
- H384: Due wakes produce first-pass strict-valid durable state.
- H385: Event observability records the terminal surface tool and label for
  completed due events.

## Predictions

For `N=2` event-plus-recall replicates using `deepseek/deepseek-v4-pro`:

- scheduled/compression state is clean before due execution in both rows;
- due execution completes in both rows;
- cycle-1 recall context is delivered in both rows;
- terminal output parses and records durable state in both rows;
- `delayed_answer` contains the exact code phrase in both rows;
- strict final state validation is first-pass valid in both rows;
- due repair is not attempted in either row;
- completed event summaries expose `terminal_surface_tool` and
  `terminal_surface_label` in both rows.

## Falsification Criteria

The terminal-surface design is not supported for this boundary if any of the
following occur:

- the clean compression/scheduling phase cannot produce at least one due
  execution;
- requested recall context is not delivered for a due event;
- a due event produces a parse/provider/tool-surface failure;
- a due wake recovers the phrase only after broad durable-state repair;
- a due wake records the phrase outside `delayed_answer` without satisfying
  strict durable-state validation;
- terminal-surface observability is missing from completed event summaries.

## Method

Reuse the seeded clean-compression scaffold and compression repair gate:

1. Seed cycle 1 with a deferred code phrase, digest handle, and loss template.
2. Run the compression/scheduling turn from the repair-gate scaffold.
3. Validate the compressed state. Repair only non-secret structural compression
   failures, using the existing non-leaking compression repair prompt.
4. Cull dirty or secret-bearing compression rows before due execution.
5. Execute due scheduled events with a production `terminal_surface` carrying:
   - tool name `complete_delayed_task`;
   - `tool_choice: auto`;
   - schema fields `response`, `delayed_answer`, and `wake_observation`;
   - state update that copies those fields and sets
     `thinking_status: completed` plus protocol-surface metadata.
6. Use the existing delayed-task validator as the strict endpoint, but do not
   attach a due repair builder.

## Primary Endpoints

- `compression_valid`
- `due_executed`
- `event_has_recall_context`
- `terminal_parse_success`
- `delayed_answer_contains_code_phrase`
- `first_pass_validation_status`
- `final_state_valid`
- `repair_attempted`
- `terminal_surface_tool_observed`
- `terminal_surface_label_observed`

## Baseline Comparison

Compare against:

- `experiments/event_loop/compression_repair_gate_20260605`
- `experiments/event_loop/second_wake_protocol_surface_auto_20260605`
- `experiments/event_loop/terminal_surface_substrate_smoke_repair_20260605`

The key comparison is due repair:

- compression repair-gate event-plus-recall: final-valid 2/2, first-pass due
  valid 1/2, due-repaired 1/2;
- expected terminal-surface delayed task: final-valid 2/2, first-pass due
  valid 2/2, due-repaired 0/2.

## Analysis Plan

Report row-level outcomes and aggregate counts. Treat provider/tool failures,
terminal parse failures, compression culls, and validation failures as distinct
failure classes. Do not reinterpret a row as successful merely because the
answer text is semantically adequate; strict durable-state validity is the
primary protocol endpoint.
