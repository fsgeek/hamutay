# Phase 3D Durable Category-Ledger Contract

Date: 2026-06-19

## Contract

The event loop must maintain a deterministic, durable category ledger for the
richer IPC sequence and final synthesis must preserve that ledger without
flattening accepted, rejected, canceled, completed, evidence, or audit
categories.

## Required Stressors

- Same IPC matrix as the Phase 3D richer IPC baseline: task, correction,
  cancellation, rejected cancellation, corrected continuation, status query,
  external evidence, category summary, claim audit, and final synthesis.
- The harness updates `category_ledger.jsonl` after each completed event.
- Summary and final events receive the durable ledger as authoritative
  substrate-owned state.
- Final synthesis must copy the ledger categories and cite the split summary
  records.

## Pass Criteria

Pass if:

- all expected IPC events complete in order;
- terminal tools appear in the expected order;
- the durable category ledger is present and equals the preregistered expected
  ledger;
- task routing, correction, cancellation, rejection, continuation, status, and
  evidence routing remain correct;
- category summary declares `durable_category_ledger` as its source and matches
  the ledger;
- claim audit declares `durable_category_ledger` as its source and preserves
  unsupported candidates, unsupported claims, and unresolved open items from
  the ledger;
- final synthesis declares `durable_category_ledger` as its source, cites
  `category-summary` and `claim-audit`, and matches all ledger category,
  evidence, unsupported-claim, and unresolved-open-item fields;
- no context errors, lifecycle anomalies, material outcome warnings, pending
  runnable events, or failure-attribution records appear.

## Failure Attribution

- `category_ledger`: durable ledger missing, incorrect, ignored, or distorted.
- `ipc_ingress`: message class is missing or malformed.
- `message_routing`: message routes to the wrong workstream.
- `workstream_isolation`: correction/cancellation leaks across workstreams.
- `continuation_binding`: continuation executes stale, canceled, or wrong
  scope.
- `scheduler_identity`: model-authored identity or event-order drift appears.
- `model_output`: terminal object violates the declared response surface.
- `provider`: live provider transport prevents evaluation.
- `artifact`: result writing or scorer behavior prevents interpretation.
