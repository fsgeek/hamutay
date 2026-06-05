# Analysis: Live Event Wake Validation Scoring

Date: 2026-06-05

## Result

The event log can now serve as the primary scoring surface for completed live
scheduled-wake validation outcomes.

- H221 scheduled-walk gate completes: supported.
- H222 completed validated events have event-level `wake_validation`: supported.
- H223 event status matches session status: supported.
- H224 event summaries classify first-pass and repair outcomes without direct
  session validation reads: supported.
- H225 context and bounded-repair diagnostics are preserved: supported.

## Summary

Across four DeepSeek replicates:

- valid initializations: 3/4;
- completed scheduled wakes: 3/3 valid initializations;
- completed wakes with event-level `wake_validation`: 3/3;
- event/session validation status agreement: 3/3;
- event-log first-pass status: 3 invalid;
- event-log validation status: 3 repaired;
- event-log repair status: 3 valid;
- context errors: 0;
- bounded wake call violations: 0.

Replicate 4 failed before scheduling. Its initial response did not create the
required durable identity/task fields:

- `probe_id`;
- `walk_gate_status`;
- `observations`.

This is the same activation confound seen in prior DeepSeek runs. It does not
falsify event-level wake scoring because no scheduled wake was created or
completed.

## Event-Log Evidence

Each completed `.events.jsonl` terminal record contains a compact
`wake_validation` object. For all three completed wakes, the event record
contains:

- `status == "repaired"`;
- `first_pass_status == "invalid"`;
- `repair_attempted == true`;
- `repair_status == "valid"`;
- `has_repair_raw_output == true`;
- `has_repair_validation == true`.

The wrapper scored these fields through `summarize_event_log`, not by reading
the session record's `state_validation` object directly. Session validation was
read only to check agreement.

## Interpretation

This substrate change is doing the intended work. Future scheduled-event
experiments can score wake outcomes from the event log itself:

- first-pass valid;
- first-pass invalid then repaired;
- unrepaired;
- repair failed;
- validator failed.

The full session log remains the source for raw model outputs and detailed
repair artifacts. The event log now carries enough summary to support scheduler
observability, dashboards, and falsification scoring without bespoke joins.

The model behavior result is not new but is consistent with prior findings:
DeepSeek again failed first-pass durable wake state use for every completed
scheduled walk, then repaired successfully under the full-target repair
scaffold.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/live_event_wake_validation_scoring_20260605/run_live_event_wake_validation_scoring.py
timeout 1200s uv run python experiments/event_loop/live_event_wake_validation_scoring_20260605/run_live_event_wake_validation_scoring.py
```

Results:

- py_compile passed;
- live runner exited with code 0;
- three scheduled wakes completed;
- all three completed event records carried event-level wake validation
  summaries;
- all preregistered hypotheses passed for completed scheduled wakes.
