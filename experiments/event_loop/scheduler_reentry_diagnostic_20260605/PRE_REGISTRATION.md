# Scheduler Re-entry Diagnostic Pre-registration

Date: 2026-06-05

## Research Question

Can the Hamut'ay event-loop scaffold preserve enough observable continuity and
failure data for a scheduled re-entry cycle to be diagnosed without user
rebriefing?

This is not a broad model sweep and not an identity-benefit claim. It is a
substrate diagnostic: after adding guardrail-aware continuity curation, strict
merge-failure capture, and deterministic protocol recovery, can a scheduled
wake cycle leave a complete research trail whether it succeeds or fails?

## Hypotheses

### H69: scheduled re-entry is operationally observable

If an instance schedules a wake event, the event sidecar will show a persisted
event and then either a completed event or a failed event with error details.

Falsification: any replicate schedules an event but the sidecar lacks a
corresponding persisted event or final completed/failed status.

### H70: successful re-entry can proceed without user rebriefing

For successful wake cycles, the final state will show that the wake used
scheduled context and continuity artifacts to update durable state without
requiring a new human restatement of the task.

Falsification: fewer than 2 of 3 valid replicates complete the wake with all of:

- `reentry_status == "completed"`
- a durable `diagnostic_findings` list with at least one wake-cycle finding
- no recursive scheduled events
- no event context resolution errors

### H71: failed re-entry remains diagnostically useful

If a wake cycle fails strict merge, the session JSONL will include a failed
cycle record with `failure_classification` and `protocol_recovery`, and the
event sidecar will include the failed event outcome.

Falsification: any strict merge failure lacks either the failed session record,
the failure classification, the protocol recovery record, or the failed event
sidecar outcome.

### H72: continuity curation is visible at the wake boundary

The wake cycle should receive a scaffold continuity artifact from the prior
completed cycle.

Falsification: any replicate that reaches the wake cycle lacks
`continuity_curator_context` on the wake record.

## Conditions

Single condition:

- Model: `moonshotai/kimi-k2.6`
- Provider: OpenRouter OpenAI-compatible endpoint
- Replicates: 3
- Main max tokens: 4096
- Tools enabled
- Continuity curator: `ClaimTableContinuityCurator`
- Curator renderer: `guardrail_delta`
- Curator max summary chars: 900
- Curator delta max rows: 6
- Protocol recovery: `DeterministicProtocolRecoveryBuilder`

KIMI is selected because prior scheduler panels found it clean across init and
scheduled wake. This experiment tests the substrate, not model diversity.

## Procedure

Each replicate:

1. Initialize a compact durable state containing a probe id, current task,
   assumptions, diagnostic findings, and re-entry status.
2. Present a task update that invalidates one assumption and adds one new
   constraint.
3. Ask the instance to schedule exactly one event whose purpose is to re-enter
   later and diagnose whether the scheduled wake can continue without a user
   rebrief.
4. Run exactly one pending event with `run_next_event`.
5. Score the session JSONL and event sidecar.

The scheduled event's requested context will include cycle 1 state and cycle 2
state. The wake purpose will explicitly forbid recursive scheduling and require
durable updates to `reentry_status` and `diagnostic_findings`.

## Primary Measures

- `init_valid`
- `task_update_valid`
- `event_persisted`
- `event_completed`
- `event_failed`
- `event_final_status_observed`
- `context_error_count`
- `wake_record_observed`
- `wake_continuity_context_observed`
- `reentry_completed`
- `diagnostic_findings_updated`
- `recursive_scheduling_count`
- `strict_merge_failure_observed`
- `strict_merge_failure_diagnosed`

## Expected Results

Expected operational result: all 3 valid replicates persist an event and reach a
completed or failed final sidecar status.

Expected successful-wake result: at least 2 of 3 valid replicates complete the
wake and update durable diagnostic fields without recursive scheduling.

Expected failure-diagnostic result: any strict merge failure is fully captured
in both the session JSONL and the event sidecar.

## Stopping Rule

Run 3 replicates unless:

- the API key is unavailable,
- all initializations fail,
- a harness bug prevents events from being persisted, or
- a repeated provider failure prevents meaningful observation.

Provider/model failures are data unless they make the scaffold unobservable.

## Interpretation

If H69-H72 hold, the event-loop substrate is ready for a next experiment that
tests bounded autonomous thinking-time loops rather than one-shot scheduled
wakes.

If H69 or H71 fails, the scaffold observability is insufficient and should be
repaired before further autonomy experiments.

If H70 fails while H69/H71/H72 hold, the scaffold is observable but the
scheduled wake protocol or continuity prompt remains an active confound.
