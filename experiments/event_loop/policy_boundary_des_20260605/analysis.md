# Event Policy Boundary DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed after one preserved implementation
failure.

- H96 branch visibility policy is deterministic and idempotent: passed after
  tightening the branch-visible projection.
- H97 sidecar audit projection preserves pending purpose and terminal status:
  passed.
- H98 policy-driven private fork/join reproduces successful DES behavior:
  passed.
- H99 policy-driven private failure remains bounded and source-linked: passed.

## Preserved Initial Failure

The first implementation run is preserved with the
`initial_h96_failure_` prefix. It failed H96:

- H96: false
- H97: true
- H98: true
- H99: true

The failed implementation stripped `_activity_log` from `state` and
`prior_state`, but returned full JSONL records as branch-visible seed material.
Those full records still contained framework prompt/transcript fields mentioning
`_activity_log`. The branch wake itself did not leak sibling branch context, but
the API boundary was too broad.

That failure sharpened the design: branch-visible seed data should be a minimal
projection, not a sanitized full transcript.

## Corrected Policy

`BranchContextPolicy.branch_visible_records()` now projects records down to the
fields `seed_history()` actually needs:

- `cycle`
- `record_id`
- `timestamp`
- sanitized `state`

It drops prompt, transcript, raw output, prior-state snapshots, usage, and other
framework metadata from the branch-visible seed. Audit metadata remains in the
append-only sidecar and is exposed through `sidecar_audit_projection()`.

## Scenario Results

### policy_boundary_success

Classification: `joined`

Observed:

- policy idempotence holds: true
- branch-private violations: 0
- sidecar audit preserved: true
- completed branch events: 2
- failed branch events: 0
- suppressed branch events: 0
- join completed: true
- joined findings: 2
- pending after policy: 0

### policy_boundary_failure

Classification: `branch_failed`

Observed:

- policy idempotence holds: true
- branch-private violations: 0
- sidecar audit preserved: true
- completed branch events: 0
- failed branch events: 1
- suppressed branch events: 1
- accepted state advanced after failure: false
- failure classification logged: true
- protocol recovery logged: true
- suppression source resolved: true
- pending after policy: 0

## Interpretation

The event-loop scaffold now has a real policy boundary:

- branch-visible context is a minimal sanitized projection;
- audit context remains append-only sidecar history;
- join context is explicit selected branch output;
- failure disposition remains source-linked.

This is better than the previous experiment-local convention. It makes the
privacy/audit distinction testable and reusable.

The remaining caveat is that this is still a policy helper, not a full scheduler
policy runner. Fork execution, join scheduling, and sibling suppression are
still orchestrated by the experiment runner. The next architecture question is
whether those orchestration steps should become a first-class fork/join runner
that consumes `BranchContextPolicy`.

## Verification

Command run:

```bash
uv run pytest tests/unit/test_event_policies.py tests/unit/test_events.py tests/unit/test_protocol_recovery.py tests/test_taste_open.py
```

Result: 71 passed.
