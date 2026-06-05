# Analysis: Live Normalized Scheduler Panel

Date: 2026-06-05

## Result

The live normalized scheduler panel supports the small equivalence probe:
first-pass-valid and repaired-valid initialization behaved qualitatively the
same downstream under the normalized envelope.

- H256 raw result plus `result_envelope` emitted at write time: supported.
- H257 eligible initialization classes are scheduler-score eligible: supported.
- H258 failed/culled initialization retained but ineligible: supported.
- H259 repaired-valid rows match first-pass-valid rows qualitatively:
  supported.
- H260 initialization provenance and wake validation provenance remain
  distinct: supported.

## Counts

Rows:

- failed/culled sentinel: 1;
- first-pass-valid live rows: 2;
- repaired-valid live rows: 2;
- scheduler-score eligible rows: 4/5.

Condition results:

- `failed_culled`: 0/1 eligible, 0 completed wakes;
- `first_pass_valid`: 2/2 eligible, 2/2 completed wakes;
- `repaired_valid`: 2/2 eligible, 2/2 completed wakes.

Envelope classes:

- `failed_or_culled`: 1;
- `first_pass_valid`: 2;
- `repaired_valid`: 2.

There were no class mismatches, eligibility mismatches, bounded initialization
call violations, or bounded wake call violations.

## Wake Pattern

All four eligible live rows had the same wake pattern:

- scheduled wake completed;
- wake validation source: `event_log_scoring`;
- wake validation status: `repaired`;
- wake first-pass status: `invalid`;
- wake repair status: `valid`;
- wake backend calls: 2.

The repaired-valid condition therefore did not show an obvious downstream
deficit relative to the first-pass-valid condition in this small panel. Both
conditions still reproduced the established DeepSeek pattern: scheduled-wake
evidence is not durable on first pass, but the bounded repair scaffold recovers
it.

## Interpretation

This is the first clean prospective panel where the result envelope is written
at row time and the denominator policy is explicit. The failed initialization
sentinel remains part of the dataset but is excluded from scheduler-success
scoring. The two eligible initialization populations can be compared without
silently mixing provenance classes.

The result supports using repaired-valid initialization as a qualified
scheduler population in future experiments, provided the provenance label is
preserved. It does not prove repaired initialization is generally equivalent to
first-pass initialization. The panel is too small and uses one model family.

## Research Consequence

The immediate initialization confound is now substantially contained for this
path:

1. failed initialization is identifiable and excluded from scheduler-success
   denominators;
2. repaired initialization is identifiable and can be scored separately;
3. first-pass and repaired initialization can be compared under the same
   envelope;
4. wake validation remains separate from initialization provenance.

The next useful research question is no longer "can repaired initialization
enter the scheduler?" It can. The sharper question is:

Does the event-loop substrate improve long-horizon task continuity when the
identity object is an active self-model backed by scheduler events and recall,
rather than a whole-memory substitute?

Before that larger question, a medium-size replication panel could test whether
the qualitative equivalence observed here survives more rows or another model.

## Verification

Commands run:

```bash
uv run python -m py_compile experiments/event_loop/live_normalized_scheduler_panel_20260605/run_live_normalized_scheduler_panel.py
timeout 1800s uv run python experiments/event_loop/live_normalized_scheduler_panel_20260605/run_live_normalized_scheduler_panel.py
jq '.summary' experiments/event_loop/live_normalized_scheduler_panel_20260605/results.json
```

The live runner exited successfully and wrote:

`experiments/event_loop/live_normalized_scheduler_panel_20260605/results.json`
