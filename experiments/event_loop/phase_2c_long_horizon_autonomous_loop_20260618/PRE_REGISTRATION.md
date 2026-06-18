# Phase 2C Long-Horizon Autonomous Loop Pilot Preregistration

Date: 2026-06-18

## Question

Can the event-loop harness sustain a bounded autonomous loop that combines
IPC-style inbound work, self-scheduled continuations, housekeeping, periodic
reports, restart/resume, and multiple workstreams in one observable run?

## Hypothesis

The loop is viable at this scale if it can complete two workstreams across a
single sustained run while:

- accepting inbound IPC-style messages;
- binding model-requested continuations through the scheduler;
- running housekeeping after each workstream;
- producing bounded periodic reports;
- recovering one already-claimed continuation after restart/resume;
- producing a final synthesis that explains completed work and open items;
- preserving restart-frontier observability and failure attribution.

## Method

The pilot composes already-tested mechanisms:

- the longer-horizon sustained-loop protocol for inbound IPC, continuations,
  housekeeping, and final synthesis;
- the restart/resume stress protocol for interrupting a claimed `running`
  event and recovering it to `pending`;
- explicit workstream labels for two bounded workstreams: `alpha/research` and
  `beta/operations`;
- bounded periodic reports after each housekeeping event.

The interruption occurs after the beta continuation is claimed as `running` and
before model exchange. The runner then loads the latest restart frontier,
recovers the interrupted event, recreates the session with `resume=True`, and
continues execution.

## Pass Criteria

Pass if all of these are true:

- nine expected events complete in order;
- the second workstream continuation has lifecycle history `pending`,
  `running`, `pending`, `running`, `completed`;
- both workstreams complete inbound, continuation, housekeeping, and periodic
  report events;
- final synthesis names both workstreams and reports no unsupported claims;
- no pending runnable events remain;
- there are no context errors, lifecycle anomalies, material outcome warnings,
  or failure-attribution records;
- restart frontier contains multiple commits and at least one recovered event.

## Failure Criteria

Fail if any pass criterion is false. Attribute failures by layer:

- `scheduler`: event ordering, continuation binding, or pending queue failure;
- `restart_frontier`: interrupted event is not recovered correctly;
- `state_reconstruction`: resumed session cannot continue the beta workstream;
- `housekeeping`: open-loop audit fails or increases disorder;
- `periodic_reporting`: reports omit workstream state or overclaim;
- `model_output`: terminal object violates the declared surface;
- `provider`: live provider transport prevents evaluation;
- `artifact`: scorer or result writing fails.

## Budget

Live direct-DeepSeek run budget: at most 10 model calls and at most 5 USD
estimated cost. Dry scripted runs make no model calls.
