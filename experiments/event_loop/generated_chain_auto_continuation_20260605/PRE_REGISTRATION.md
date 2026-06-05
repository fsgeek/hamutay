# Pre-Registration: Generated Chain Auto-Continuation

Date: 2026-06-05

## Research Question

Does the generated bound-chain terminal-surface result survive when the
scheduler appends the second event via `auto_continuations=True`, rather than
the experiment runner appending it manually?

The prior generated bound-chain panel proved that terminal surfaces could
produce a valid first wake, and the runner could bind a second event to the
generated first-wake `result_record_id`. The auto-continuation scheduler smoke
proved the scheduler phase in unit fixtures. This panel combines the two with
live model calls.

## Hypotheses

- H421: First terminal-surface wake produces a strict-valid non-secret
  intermediate and durable continuation request.
- H422: `step_pending_events(..., auto_continuations=True)` appends the second
  pending event from that continuation request.
- H423: The appended second event is bound to the generated first-wake
  `result_record_id`.
- H424: The second terminal-surface wake receives original cycle-1 recall and
  bound first-record recall.
- H425: The chain completes first-pass valid without runner-mediated append or
  broad repair.

## Predictions

For `N=2` replicates using `deepseek/deepseek-v4-pro`:

- first wake completes in both rows;
- first wake is first-pass strict-valid in both rows;
- first wake does not leak the exact phrase into durable state;
- first wake durable state contains a complete `continuation_request`;
- first due scheduler step returns an `auto_continuation_event` in both rows;
- event logs contain a pending second event with `bound_by:
  continuation_request`;
- second wake receives both requested contexts in both rows;
- second wake is first-pass strict-valid in both rows;
- final answer recovers the exact phrase and evidence uses `word-word-number`;
- no repair is attempted in either wake.

## Falsification Criteria

The combined design is not supported if:

- the first wake cannot produce a valid non-leaking continuation state;
- auto-continuation does not append a second event;
- the appended event is not bound to the actual generated result record;
- placeholder expansion fails in requested context or terminal-surface state
  update;
- the second wake cannot recover and use the bound intermediate;
- either wake requires broad repair.

## Method

1. Seed cycle 1 with the deferred code phrase and cycle 2 with a clean waiting
   state.
2. Append the first event with terminal surface `complete_first_wake`.
3. The first terminal surface copies `chain_intermediate` and sets a complete
   durable `continuation_request` template containing `<result_record_id>`
   placeholders.
4. Run the first due step with `auto_continuations=True`.
5. Do not manually append a second event in the runner.
6. Run the second due step with `auto_continuations=True`.
7. Validate both wake states, event lifecycle, context delivery, binding
   metadata, and terminal-surface observability.

## Primary Endpoints

- `first_wake_state_valid`
- `first_wake_first_pass_valid`
- `first_wake_state_contains_code_phrase`
- `auto_continuation_event_returned`
- `auto_continuation_event_appended`
- `auto_continuation_bound_result_record_id`
- `second_wake_context_has_cycle1`
- `bound_record_context_delivered`
- `second_wake_state_valid`
- `second_wake_first_pass_valid`
- `chain_final_answer_contains_code_phrase`
- `chain_final_evidence_uses_intermediate`
- `first_wake_repair_attempted`
- `second_wake_repair_attempted`

## Analysis Plan

Classify failures by stage: first-wake model/state failure, scheduler
auto-append failure, record-ID recall failure, second-wake model/state failure,
or provider/tool failure. Do not treat manual append as an allowed fallback.
