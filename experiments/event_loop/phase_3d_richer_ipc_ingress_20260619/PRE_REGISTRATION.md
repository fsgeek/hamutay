# Phase 3D Richer IPC Ingress Preregistration

Date: 2026-06-19

## Question

Can the event-loop harness accept multiple asynchronous IPC message types
without confusing event identity, workstream scope, continuation binding, or
final message-category accounting?

## Hypothesis

The loop is richer-IPC-ready if it can process task, correction, cancellation,
status-query, and external-evidence messages across two workstreams while
preserving accepted, corrected, canceled, rejected, and completed categories.

## Prediction

Basic task and status messages should pass. Corrections and cancellations are
higher risk because they mutate workstream state and can make stale
continuation execution look valid.

## Method

Run a nine-event IPC ingress matrix:

1. accept `task-alpha` for `research`;
2. accept `task-beta` for `operations`;
3. apply `correction-alpha` to `task-alpha`;
4. accept `cancel-beta` for `task-beta`;
5. reject `cancel-ghost` for unknown `task-ghost`;
6. complete scheduler-owned continuation `continue-alpha-corrected`;
7. answer `status-all`;
8. record `evidence-alpha`;
9. write final IPC ingress synthesis.

The final artifact must explain accepted, corrected, canceled, rejected, and
completed messages without unsupported claims.

## Pass Criteria

Pass if all contract checks in `CONTRACT.md` are true.

## Failure Criteria

Fail if any pass criterion is false. Attribute failures to IPC ingress,
message routing, workstream isolation, continuation binding, scheduler
identity, model output, provider transport, or artifact/scorer behavior.

## Budget

Live direct-DeepSeek run budget: at most 10 model calls and at most 5 USD
estimated cost. Dry scripted runs make no model calls.
