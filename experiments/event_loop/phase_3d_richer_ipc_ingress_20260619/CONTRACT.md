# Phase 3D Richer IPC Ingress Contract

Date: 2026-06-19

## Contract

The event loop must route multiple IPC message classes across workstreams
without confusing scheduler-owned event identity, workstream scope,
correction/cancellation effects, continuation binding, or final category
reporting.

## Required Stressors

- Task messages for `task-alpha` on `research` and `task-beta` on
  `operations`.
- Correction message `correction-alpha` applied only to `task-alpha`.
- Cancellation message `cancel-beta` applied only to `task-beta`.
- Rejected cancellation `cancel-ghost` against unknown `task-ghost`.
- Scheduler-owned continuation `continue-alpha-corrected` completing the
  corrected alpha task.
- Status query over both workstreams.
- External evidence notification routed to the research workstream.
- Category summary separating accepted task messages, accepted non-task IPC
  messages, corrected, canceled, rejected, and completed messages.
- Claim-audit summary separating audit notes, unresolved open items,
  unsupported claim candidates, and unsupported claims actually made.
- Final synthesis citing the category and claim-audit summaries rather than
  recomputing every category from scratch.

## Pass Criteria

Pass if:

- all expected IPC events complete in order;
- terminal tools appear in the expected order;
- task routing preserves `research` and `operations` workstream scope;
- correction affects alpha only;
- cancellation affects beta only;
- unknown cancellation is rejected;
- corrected alpha continuation completes and no beta continuation is completed;
- status query reports alpha completed, beta canceled, and ghost cancellation
  rejected;
- external evidence is routed to research and cites alpha/correction records;
- category summary preserves task-accepted, non-task-accepted, corrected,
  canceled, rejected, and completed message categories;
- claim-audit summary keeps audit notes out of unresolved open items;
- claim-audit summary keeps unsupported claim candidates out of unsupported
  claims made;
- final synthesis cites `category-summary` and `claim-audit`;
- no context errors, lifecycle anomalies, material outcome warnings, pending
  runnable events, or failure-attribution records appear.

## Failure Attribution

- `ipc_ingress`: message class is missing or malformed.
- `message_routing`: message routes to the wrong workstream.
- `workstream_isolation`: correction/cancellation leaks across workstreams.
- `continuation_binding`: continuation executes stale, canceled, or wrong
  scope.
- `scheduler_identity`: model-authored identity or event-order drift appears.
- `model_output`: terminal object violates the declared response surface.
- `provider`: live provider transport prevents evaluation.
- `artifact`: result writing, summary splitting, or scorer behavior prevents
  interpretation.
