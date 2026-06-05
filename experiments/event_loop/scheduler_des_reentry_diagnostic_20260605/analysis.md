# Simulated-Time Scheduler Re-entry Diagnostic Analysis

Date: 2026-06-05

## Result

All four registered hypotheses passed under deterministic simulated time.

- H73 simulated due-time claiming: passed.
- H74 successful re-entry records completion: passed.
- H75 strict merge failure records diagnostics: passed.
- H76 wake boundary receives continuity context: passed.

The core substrate result is clean: when provider latency and wall-clock waiting
are removed, the event-loop path can claim due events, build wake envelopes,
resolve requested context, inject continuity context, append wake records, and
record either successful completion or strict failure.

## Scenario Details

### success

The success scenario produced the expected sidecar sequence:

`pending -> running -> completed`

The completed sidecar record included resolved context, response text, wake
cycle, result record id, and an outcome observation. The outcome observation
reported durable state changes to `diagnostic_findings` and `reentry_status`.

The session wake record included `curator_context_injection`, confirming that
continuity curation was visible at the scheduled wake boundary.

### strict_merge_failure

The strict-failure scenario produced the expected sidecar sequence:

`pending -> running -> failed`

The wake intentionally returned both `diagnostic_findings` and
`deleted_regions: ["diagnostic_findings"]`. The strict merge rejected the
update. Accepted state remained unchanged: `reentry_status` stayed
`initialized`.

The failed session record included:

- `status: "failed"`
- `failure_classification.failure_stage: "state_merge"`
- overlap key `diagnostic_findings`
- `protocol_recovery.status: "success"`
- 3 candidate recovery rows
- `curator_context_injection`

The failed sidecar record now also includes the resolved `context_results`.

This confirms the strict invariant: failed merge output does not mutate accepted
state, but diagnostic evidence is preserved.

## Live-Run Contrast

The earlier live-provider scheduler re-entry diagnostic stalled before the
schedule step completed. Two partial logs were preserved:

- `aborted_provider_stall_r01.jsonl`
- `aborted_provider_stall_retry_r01.jsonl`

Those artifacts are not clean evidence against the event-loop substrate. They
are evidence that the live runtime layer has unresolved operational concerns:
provider latency, blocking calls, timeout/cancellation behavior, and process
supervision.

The simulated-time result separates the layers:

- the loop semantics work when time and model responses are deterministic;
- the real-clock/provider execution path still needs runtime hardening.

## Observability Fix

One gap became visible during the first DES run. On failed wakes, the event
sidecar recorded the failed status and error, but did not include the
already-resolved `context_results`. The session JSONL wake record contained the
event envelope, including context results, so the data was not lost. Still,
sidecar-only diagnosis was weaker for failures than for completions.

That gap was repaired in this slice. `EventStore.append_failed` now accepts
optional `context_results`, and `run_next_event` passes them when context
resolution occurred before the wake failure. The DES diagnostic was rerun after
the fix; the strict-merge-failure scenario now has `context_resolved: true` and
the failed sidecar includes recalled cycle-1 context.

## Interpretation

The event-loop substrate is worth continuing. The next work should not be
another live model sweep. The better engineering move is to strengthen the
runtime boundary:

1. Add subprocess-level timeout/cancellation around live provider calls.
2. Preserve failed wake record ids or cycle coordinates in the sidecar when
   available.
3. Keep simulated-time tests as the contract suite for event semantics.

After that, return to live scheduled-wake experiments with the runtime
confounds explicitly controlled.
