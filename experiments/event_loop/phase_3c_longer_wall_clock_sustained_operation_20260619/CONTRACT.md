# Phase 3C Longer Wall-Clock Sustained Operation Contract

Date: 2026-06-19

## Contract

The event loop must complete a bounded autonomous run across elapsed wall-clock
delay windows while preserving scheduler identity, restart-frontier recovery,
periodic-report consistency, housekeeping state, and final failure attribution.

## Required Stressors

- Two workstreams: `alpha/research` and `beta/operations`.
- Two explicit delay windows:
  - `alpha-report-delay` before running the alpha periodic report;
  - `beta-restart-delay` after claiming the beta continuation as `running` and
    before restart/resume recovery.
- One recovered already-claimed continuation with lifecycle history `pending`,
  `running`, `pending`, `running`, `completed`.
- Periodic reports after housekeeping.
- Final synthesis that distinguishes completed, pending, delayed, and
  preserved state.

## Pass Criteria

Pass if:

- all nine expected events complete in order;
- both delay windows are observed and exceed the minimum delay threshold;
- delayed events remain pending until after their delay windows;
- restart/resume recovers exactly one interrupted event;
- periodic reports remain consistent with workstream history and zero open
  items;
- final synthesis reports both workstreams complete, no pending event labels,
  both delayed window labels, and preserved restart/report/open-item state;
- no context errors, lifecycle anomalies, material outcome warnings, or
  failure-attribution records appear.

## Failure Attribution

- `elapsed_time_scheduler`: missing/short delay windows or unobservable pending
  elapsed time.
- `scheduler`: event ordering, continuation binding, or pending queue failure.
- `restart_frontier`: interrupted event is not recovered correctly.
- `state_reconstruction`: resumed session cannot continue after restart.
- `housekeeping`: open state is corrupted or silently dropped.
- `periodic_reporting`: reports drift from actual workstream history.
- `model_output`: terminal object violates the declared response surface.
- `provider`: live provider transport prevents evaluation.
- `artifact`: result writing or scorer behavior prevents interpretation.
