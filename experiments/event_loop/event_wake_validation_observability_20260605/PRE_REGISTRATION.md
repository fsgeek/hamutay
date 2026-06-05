# Pre-Registration: Event Wake Validation Observability

Date: 2026-06-05

## Research Question

Should the event-loop substrate record wake validation/repair outcomes directly
on completed event records?

The validation/repair scaffold already records detailed artifacts in the
session log. Scheduled-event analysis still has to join session logs and event
logs manually to classify a wake as first-pass valid, repaired, unrepaired, or
repair-failed. This experiment tests a small observability change: completed
event records should carry a compact validation summary derived from the wake
cycle record, without changing model-authored state or scheduler behavior.

## Hypotheses

- H216: Adding event-level wake validation summaries preserves scheduler
  behavior.
- H217: Completed event records include a compact summary when the wake cycle
  has `state_validation`.
- H218: Completed event records omit the summary when no validator is active,
  preserving default log shape for unvalidated wakes.
- H219: Event reports surface validation outcomes for completed wakes.
- H220: The observability change does not mutate model-authored state, repair
  outputs, or merge diagnostics.

## Predictions

The change should be deterministic because it reads only the wake record that
`OpenTasteSession.exchange` already appended. It should not require live model
calls. Existing live logs demonstrate why the field is useful, but unit tests
and a deterministic fake session are sufficient to falsify the substrate
semantics.

Expected result: all hypotheses pass. A failure would mean the event store is
not yet a reliable first-class audit substrate for validation/repair outcomes.

## Method

Add a helper that extracts a compact validation summary from the latest wake
record:

- `status`;
- first-pass status;
- `repair_attempted`;
- repair status;
- `repaired`;
- `has_repair_raw_output`;
- `has_repair_validation`;
- protected merge diagnostic counts when present.

Thread the summary into `EventStore.append_completed` from `run_next_event`.
Update `summarize_event_log` and `format_event_report` so completed-event
summaries expose validation outcomes.

Run deterministic tests covering:

- no validator: completed event has no validation summary;
- first-pass valid: completed event records `status == "valid"`;
- repaired: completed event records first-pass invalid and repaired status;
- event report renders validation status for completed wakes.

No live model call is required for this experiment.

## Falsification Criteria

- H216 is falsified if `run_next_event` or `step_pending_events` lifecycle
  behavior changes for unvalidated events.
- H217 is falsified if a wake with `state_validation` completes without a
  `wake_validation` summary.
- H218 is falsified if unvalidated wakes gain spurious validation fields.
- H219 is falsified if human-readable event reports hide validation outcomes
  for completed wakes.
- H220 is falsified if the implementation changes final durable state, raw
  model output, repair artifacts, or protected merge diagnostics.

## Analysis Plan

Compare unit-test event logs before and after completion:

- event lifecycle status sequence;
- completed event fields;
- session wake record state/validation artifacts;
- rendered report text.

If the substrate behaves deterministically, write `analysis.md` documenting the
result and whether this is sufficient to support future scheduler experiments
without manual log joins.
