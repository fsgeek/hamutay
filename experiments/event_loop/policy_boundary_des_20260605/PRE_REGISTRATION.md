# Event Policy Boundary DES Pre-Registration

Date: 2026-06-05

## Research Question

Can the branch-private fork/join behavior be represented by a reusable scheduler
policy boundary rather than experiment-specific orchestration?

The prior DES runs showed that branch-visible context can be sanitized while a
shared event sidecar remains auditable. That result was implemented inside a
single experiment runner. This experiment tests whether the boundary can be
factored into a small first-class API without weakening the invariants.

## Hypotheses

### H96: Branch visibility policy is deterministic and idempotent

If a policy removes private framework-authored fields from branch-visible
records, then applying it once or repeatedly should produce the same sanitized
records, and no `_activity_log` content should remain in branch-visible state or
resolved context results.

Falsification condition: sanitized records differ between the first and second
application, or branch-visible state/context still contains `_activity_log`.

### H97: Sidecar audit projection preserves pending purpose and terminal status

If auditability lives in the append-only sidecar rather than branch-visible
context, then a policy audit projection should reconstruct each branch's
pending label/purpose and latest terminal status from the full sidecar record
history.

Falsification condition: the projection cannot recover both branch labels,
branch purposes, and terminal statuses.

### H98: Policy-driven private fork/join reproduces the successful DES behavior

If the policy boundary is sufficient, then a success run using the reusable
policy API should complete both private branches, complete an explicit join,
produce two joined findings, and leave no pending events.

Falsification condition: either branch fails to complete, join fails to
complete, joined findings are incomplete, branch-private violations are
observed, or pending events remain.

### H99: Policy-driven private failure remains bounded and source-linked

If the policy boundary composes with failure disposition, then a strict merge
failure in one private branch should fail that branch, suppress its sibling,
avoid accepted-state advancement, preserve protocol recovery evidence, and link
suppression to the failed branch record.

Falsification condition: failed branch state advances, sibling work remains
pending, protocol recovery is missing, suppression lacks source coordinates, or
branch-private violations are observed.

## Experimental Design

Implement a minimal scheduler policy API that separates:

- branch-visible context construction;
- sidecar audit projection;
- explicit join-event construction.

Then run deterministic simulated-time fork/join scenarios equivalent to the
previous branch-private DES, but make the runner call the policy API instead of
embedding private sanitization and audit reconstruction locally.

Conditions:

- deterministic fake backend;
- simulated time;
- no live provider calls;
- no production scheduler loop rewrite beyond the reusable policy boundary;
- success and failure scenarios both captured.

## Expected Result

Expected before running: H96-H99 pass. If this fails, branch privacy remains a
fragile runner convention rather than a scheduler abstraction.

## Evaluation Artifacts

- policy API implementation and unit tests;
- `run_policy_boundary_des.py`;
- scenario JSONL logs;
- shared `.events.jsonl` sidecars;
- `results.json`;
- `analysis.md`.
