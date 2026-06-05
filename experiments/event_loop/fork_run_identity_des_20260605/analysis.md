# Fork Run Identity DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed after one preserved scorer-shape
correction.

- H104 fork run records have stable identity and declared root: passed.
- H105 successful run records bind branches and join: passed.
- H106 failed run records bind failure and suppression disposition: passed.
- H107 run records are sufficient for compact evaluation: passed.

## Preserved Initial Scorer Issue

The first run is preserved with the `initial_h107_scorer_shape_` prefix. The
underlying H107 condition was truthy, but the scorer returned the suppression
record list rather than a strict boolean. The corrected scorer wraps that field
with `bool(...)`, and the rerun reports strict boolean hypothesis results.

## Scenario Results

### fork_run_identity_success

Classification: `joined`

The fork-run sidecar contains two records for `fork-run-success`: a `started`
record and a final `joined` record.

Observed final run coordinates:

- branch A event/result: present
- branch B event/result: present
- join event/result: present
- final classification: `joined`
- fork-run record count: 2

The final record binds both branch event IDs, both branch result record IDs, the
join event ID, and the join result record ID.

### fork_run_identity_failure

Classification: `branch_failed`

The fork-run sidecar contains two records for `fork-run-failure`: a `started`
record and a final `branch_failed` record.

Observed final run coordinates:

- failed branch: `branch-a`
- failed branch event: present
- failed branch wake record: present
- suppressed sibling event: present
- suppression record: present
- final classification: `branch_failed`
- fork-run record count: 2

The final record binds the failed branch terminal status, failed wake
coordinates, suppressed sibling event ID, and suppression policy source record.

## Interpretation

Fork/join now has a durable identity object, not just transient runner
telemetry. The architecture now has four separable pieces:

1. append-only event status sidecar;
2. branch-visible context policy;
3. fork/join policy runner;
4. append-only fork-run identity sidecar.

This matters because future long-horizon branch work needs a durable object to
point at. A later cycle, evaluator, or merge policy can now refer to a single
`fork_run_id` and reconstruct the root, branch dispositions, join result, and
failure suppression without reparsing branch session logs.

The run record is still local JSONL, not cross-session graph persistence. That
is acceptable for this DES layer, but it leaves a clear next boundary: mapping
fork-run records into the memory graph so recall/walk can treat a fork run as a
first-class durable object.

## Verification

Command run:

```bash
uv run pytest tests/unit/test_event_policies.py tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py
```

Result: 79 passed.
