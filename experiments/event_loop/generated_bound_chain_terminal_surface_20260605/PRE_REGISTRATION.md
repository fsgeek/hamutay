# Pre-Registration: Generated Bound Chain Terminal Surface

Date: 2026-06-05

## Research Question

Can task-specific terminal surfaces turn the prior substrate-bound chain
failure into a generated multi-event continuity success?

The earlier `substrate_bound_chain_20260605` panel failed before record-ID
recall was tested: both first wakes described the continuation fields in prose
but did not commit `chain_intermediate` or `continuation_request` to durable
state. This experiment tests whether a narrow first-wake terminal surface
removes that state-object compliance failure, allowing the substrate to bind a
second event to the first wake's generated `result_record_id`.

## Hypotheses

- H391: A first-wake terminal surface produces a strict-valid non-secret
  intermediate and continuation request.
- H392: The substrate can bind a second event to the generated first-wake
  `result_record_id`.
- H393: The second wake receives both original cycle-1 recall and bound
  first-wake record recall.
- H394: A second-wake terminal surface recovers the exact phrase and uses the
  generated intermediate without due repair.
- H395: Terminal-surface observability is present for both completed events.

## Predictions

For `N=2` replicates using `deepseek/deepseek-v4-pro`:

- first wake executes in both rows;
- first wake is first-pass strict-valid in both rows;
- first wake durable state contains no exact phrase;
- first wake records `chain_intermediate` and `continuation_request`;
- the runner appends a bound second event using the generated first-wake
  `result_record_id`;
- second wake executes in both rows;
- second wake receives cycle-1 recall and bound record recall in both rows;
- second wake is first-pass strict-valid in both rows;
- final answer contains the exact phrase and evidence references
  `word-word-number`;
- no broad wake repair is attempted in either wake.

## Falsification Criteria

The design is not supported if:

- the first wake fails to commit a durable `chain_intermediate` or
  `continuation_request`;
- the first wake leaks the exact phrase into durable state;
- the substrate cannot bind or recall the generated first-wake record ID;
- the second wake cannot combine original recall with the bound intermediate;
- either wake requires broad durable-state repair;
- terminal-surface metadata is absent from completed event summaries.

## Method

1. Seed cycle 1 with a deferred code phrase and cycle 2 with a compressed
   waiting state.
2. Append a first pending event with:
   - requested context `recall(cycle=1)`;
   - terminal surface `complete_first_wake`;
   - state-update mapping for `chain_intermediate` and
     `continuation_request`.
3. Execute the first event without a repair builder.
4. Validate the first wake. If invalid or phrase-leaking, do not append the
   second event.
5. If valid, append a second pending event bound to the first completed
   event's `result_record_id`.
6. The second event requests:
   - `recall(cycle=1)`;
   - `recall(record_id=<first-result>, field="chain_intermediate")`.
7. Execute the second event with terminal surface `complete_second_wake` and no
   repair builder.
8. Validate row-level event lifecycle, context delivery, durable state, and
   terminal-surface observability.

## Primary Endpoints

- `first_wake_state_valid`
- `first_wake_state_contains_code_phrase`
- `continuation_requested`
- `bound_second_event_appended`
- `second_wake_context_has_cycle1`
- `second_wake_context_has_bound_record_id`
- `bound_record_context_delivered`
- `second_wake_state_valid`
- `chain_final_answer_contains_code_phrase`
- `chain_final_evidence_uses_intermediate`
- `first_wake_repair_attempted`
- `second_wake_repair_attempted`
- terminal surface tool/label observations for both events

## Baseline Comparison

Compare against:

- `experiments/event_loop/substrate_bound_chain_20260605`
- `experiments/event_loop/terminal_surface_substrate_smoke_repair_20260605`
- `experiments/event_loop/delayed_task_terminal_surface_20260605`

The key comparison is first-wake durable state compliance:

- substrate-bound broad first wake: first valid 0/2, continuation requested
  0/2;
- expected generated terminal-surface first wake: first valid 2/2,
  continuation requested 2/2.

## Analysis Plan

Report first-wake and second-wake failure classes separately. Do not count the
second stage as failed merely because a correctly invalid first stage prevented
execution; classify that as a first-stage boundary. Treat record-ID recall
errors separately from terminal parse, validation, and phrase-leak failures.
