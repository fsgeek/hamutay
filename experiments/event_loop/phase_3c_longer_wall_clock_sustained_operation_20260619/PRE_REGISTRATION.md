# Phase 3C Longer Wall-Clock Sustained Operation Preregistration

Date: 2026-06-19

## Question

Can the event-loop harness remain observable and restartable across elapsed
wall-clock time, rather than only across a larger count of immediately executed
events?

## Hypothesis

The loop is viable at this substrate-pressure level if it can complete two
workstreams while:

- accepting IPC-style inbound work;
- binding scheduler-owned continuations;
- waiting through explicit elapsed-time delay windows before running delayed
  work;
- recovering one already-claimed continuation after elapsed time and
  restart/resume;
- running housekeeping and periodic reports after delayed execution;
- producing a final synthesis that distinguishes completed work, currently
  pending events, historical elapsed-delay windows, and preserved state;
- preserving restart-frontier observability and failure attribution.

## Prediction

Scheduler mechanics should survive this bounded wall-clock probe. The likely
failure modes are report drift, pending-queue/frontier mismatch after delay, or
housekeeping that observes open-loop state without reducing or explicitly
preserving it.

## Method

The probe extends the Phase 2C autonomous-loop pilot with two wall-clock delay
windows:

- `alpha-report-delay`: append the alpha periodic-report event, wait, then run
  the pending report;
- `beta-restart-delay`: claim the beta continuation as `running`, wait, then
  load the restart frontier, recover the interrupted event, resume the session,
  and complete it.

The runner records requested and observed delay seconds, delayed event
identity, event creation timestamps, pending elapsed time before delayed event
start, restart-frontier line count, periodic-report states, and final synthesis
state.

## Pass Criteria

Pass if all of these are true:

- nine expected events complete in order;
- the two delay windows are observed and each exceeds the minimum observed
  delay threshold;
- the delayed periodic report and interrupted beta continuation both wait
  before start;
- the beta continuation lifecycle history is `pending`, `running`, `pending`,
  `running`, `completed`;
- restart/resume recovers exactly one interrupted event;
- both periodic reports remain consistent with the completed workstream
  history and report zero open items;
- final synthesis names both workstreams, lists the two historical
  elapsed-delay windows, lists no currently pending events, and lists the
  preserved restart/report/open-item state;
- no pending runnable events remain;
- there are no context errors, lifecycle anomalies, material outcome warnings,
  or failure-attribution records.

## Failure Criteria

Fail if any pass criterion is false. Attribute failures by layer:

- `elapsed_time_scheduler`: delay windows are missing, too short, or not
  reflected in pending elapsed time;
- `scheduler`: event ordering, continuation binding, or pending queue failure;
- `restart_frontier`: interrupted event is not recovered correctly;
- `state_reconstruction`: resumed session cannot continue the beta workstream;
- `housekeeping`: open-loop audit fails or corrupts open state;
- `periodic_reporting`: reports drift from event history or overclaim;
- `model_output`: terminal object violates the declared surface;
- `provider`: live provider transport prevents evaluation;
- `artifact`: scorer or result writing fails.

## Budget

Live direct-DeepSeek run budget: at most 10 model calls, two bounded delay
windows, and at most 5 USD estimated cost. Dry scripted runs make no model
calls.
