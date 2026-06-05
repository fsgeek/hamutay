# Fork Run Identity DES Pre-Registration

Date: 2026-06-05

## Research Question

Can an explicit fork/join run mint a durable run identity record that binds the
coordinator, branch events, branch result records, join event, join result, and
failure/suppression disposition into one reconstructable object?

The prior runner DES gave us reusable fork/join orchestration and structured
telemetry. It did not create a first-class durable object representing the run
itself. Without that object, long-horizon fork work still requires joining
separate session logs and sidecar records by convention.

## Hypotheses

### H104: Fork run records have stable identity and declared root

If a fork/join run is first-class, then the runner should mint a stable
`fork_run_id` and a durable `fork_run` record with coordinator/fork coordinates
before branch execution results are interpreted.

Falsification condition: the run record lacks `fork_run_id`,
`scheduled_by_cycle`, `scheduled_by_record_id`, or branch labels.

### H105: Successful run records bind branches and join

If durable run identity is sufficient, then a successful run record should bind
both branch event IDs, both branch result record IDs, the join event ID, the
join result record ID, and final classification `joined`.

Falsification condition: any branch event/result coordinate is absent, join
coordinates are absent, final classification is not `joined`, or sidecar audit
projection disagrees with the run record.

### H106: Failed run records bind failure and suppression disposition

If durable run identity composes with failure disposition, then a failed run
record should bind the failed branch event, failed branch wake record, failed
status/error, suppressed sibling event, suppression record, and final
classification `branch_failed`.

Falsification condition: failed branch source coordinates are absent,
suppression coordinates are absent, suppressed sibling cannot be identified, or
final classification is not `branch_failed`.

### H107: Run records are sufficient for compact evaluation

If the run record is a real durable identity object, then evaluation should be
possible from the run record plus append-only event sidecar without reading
branch session JSONL logs.

Falsification condition: the scorer must parse branch session logs to determine
branch labels, terminal statuses, result record IDs, join result, or suppression
source.

## Experimental Design

Extend the fork/join policy runner with durable run-record helpers:

- create an initial `fork_run` record from coordinator/fork coordinates and
  branch labels;
- update/finalize a successful run with branch results and join result;
- update/finalize a failed run with failed branch result and suppression
  records;
- serialize the records to an append-only `.fork_runs.jsonl` sidecar.

Run deterministic simulated-time success and failure scenarios equivalent to
the prior fork/join runner DES. The scorer must use the fork-run sidecar and
event sidecar, not branch session logs, for H105-H107 evaluation.

Conditions:

- deterministic fake backend;
- simulated time;
- no live provider calls;
- no new external persistence backend;
- success and failure scenarios both captured.

## Expected Result

Expected before running: H104-H107 pass. If this fails, fork/join execution is
not yet durable enough for long-horizon branch identity and later merge/recall
work.

## Evaluation Artifacts

- run identity implementation and unit tests;
- `run_fork_run_identity_des.py`;
- scenario JSONL logs;
- shared `.events.jsonl` sidecars;
- `.fork_runs.jsonl` sidecars;
- `results.json`;
- `analysis.md`.
