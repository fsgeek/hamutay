# Autonomous Audit Log and Restart Boundary Plan

Date: 2026-06-09

## Purpose

Define the work required before live autonomy experiments spend model tokens.

The current scaffold can rehearse the complete control loop without tokens:

`scheduler dispatch -> wake envelope -> autonomous driver -> cognition ->
open work -> closure attestation -> idle`.

That is not yet enough for live autonomy experiments. The blocking requirement
is an audit-grade, reproducible action log and a clear restart boundary. A live
run must tell us exactly what the model attempted, what the harness accepted or
rejected, what substrate operations occurred, what each operation returned, and
where a run can resume after interruption without inventing continuity.

## Current Baseline

Already present:

- `ToolExecutor` captures tool name, parameters excluding `reason`, reason,
  result summary, full result, result hash, duration, timestamp, and capability.
- `taste_open` stores full tool activity durably while re-feeding a lean copy
  into the model state.
- `EventStore` is append-only JSONL with file locking and atomic pending-claim
  behavior.
- scheduler lifecycle records include pending/running/completed/failed/expired.
- local `MemoryPort` logs retrieval attempts, including failures, reasons,
  returned records, fields, truncation, omissions, and error details.
- protocol failures preserve raw output and classification before rollback.
- closure semantics preserve original records and append closure attestations.
- driver rollback now mirrors `taste_open`: a cognition exception does not
  strand the driver at a false idle frontier.
- deterministic scheduler IDs now avoid random replay divergence in the local
  kernel when callers omit IDs.

Known baseline limitation:

- The current no-token rehearsal uses a rehearsal-only closure shim. It proves
  substrate flow, not model-authored action application.
- The live model-facing action surface is not yet specified or enforced.
- Tool activity is durable in cycle logs, but not yet a separate tamper-evident
  action ledger with per-operation before/after checkpoints.
- The current local rehearsal is in-memory. A live autonomy run must be
  restartable from append-only persisted artifacts.

## Blocking Requirements

### R1. Agent-visible action surface

Define a minimal model-authored action object. It must represent:

- visible response;
- open items;
- closure requests targeting exact handles;
- schedule requests;
- policy action;
- declared losses or uncertainty;
- optional abandonment/defer rationale.

The harness must never infer hidden intent. If the model did not declare an
operation, the harness must not silently perform it.

### R2. Action parse and validation trace

Every cycle must produce an append-only trace row for:

- raw model output;
- parsed candidate action object;
- parse status;
- validation status;
- accepted actions;
- rejected actions;
- rejection reasons;
- normalization or repair applied, if any;
- schema version.

Rejected actions are first-class observations, not absent operations.

### R3. Exact operation log

Every operation attempted by the model or harness on the model's behalf must be
logged with:

- run ID;
- cycle ID or wake ID;
- operation ID;
- operation type;
- actor (`model`, `harness`, `scheduler`, `memory`, `tool_executor`);
- raw parameters;
- validated parameters;
- reason/rationale if supplied;
- precondition checks;
- result status;
- full result or bounded result;
- truncation/omission metadata;
- error layer, code, and message on failure;
- records/events/attestations created;
- hashes for large payloads.

This includes failed, refused, and no-op operations.

### R4. Tamper-evident append-only action ledger

The action log must be separate from model-authored state and unavailable to
model mutation. At minimum:

- append-only JSONL or substrate-backed records;
- monotonic sequence numbers;
- previous-record hash chaining;
- current-record canonical hash;
- run manifest hash;
- explicit redaction policy for secrets;
- no write path exposed through model tools.

Future hardening may move the ledger to a container/VM boundary, append-only
filesystem, or Yanantin/Apacheta-backed immutable records. The first live pilot
does not require a VM, but it must not allow the agent to alter its audit log.

### R5. Restart boundary

Define a durable frontier for restart. A run can resume only from a committed
frontier where all of these are true:

- accepted model state is committed;
- cycle record is committed;
- action ledger rows through the cycle are committed;
- scheduled events are committed or explicitly absent;
- memory records/attestations are committed;
- event lifecycle status is committed;
- failure records are committed if the cycle failed.

If a failure occurs before the frontier, the next run must retry from the prior
frontier. It must not advance cycle count, accepted state, open-work status, or
event lifecycle as if the failed action succeeded.

### R6. Replay/reconstruction report

At the end of a run, the framework must be able to generate a report answering:

- what did the model see;
- what did it emit;
- what actions did it attempt;
- which actions were accepted/rejected;
- what operations were performed;
- what each operation returned;
- what state/memory/event records changed;
- why each wake happened;
- why the run stopped;
- where any failure occurred;
- whether the restart frontier is clean.

If the report cannot distinguish model failure, protocol failure, harness
failure, substrate failure, provider failure, and scorer failure, observability
is not yet sufficient for live experiments.

### R7. Sandbox policy recorded per run

Each run manifest must record the sandbox posture:

- filesystem roots allowed;
- write targets allowed;
- network status;
- shell/tool availability;
- secrets policy;
- model/provider/API endpoint;
- token/cycle/wall-time budgets;
- container/VM identity if applicable;
- audit ledger storage location.

For initial live autonomy experiments, the recommended posture is:

- no shell;
- no network tools;
- read-only repo access;
- writes limited to experiment output, event logs, memory logs, and action
  ledger;
- memory/event/action operations only through allowlisted harness APIs.

## Implementation Plan

### Phase 1. Action schema and parser

Deliverables:

- `AutonomousAction` schema/version;
- parser from model raw output to candidate action;
- validator that emits accepted/rejected action rows;
- tests for valid action, missing fields, malformed closure target, invalid
  schedule request, unknown action, and rejected-but-logged behavior.

Completion evidence:

- model-authored open/closure/schedule/policy objects can be parsed without
  harness inference;
- rejected actions appear in the trace with exact reasons.

### Phase 2. Action ledger

Deliverables:

- append-only action ledger writer;
- hash-chained canonical records;
- run manifest record;
- operation record schema;
- redaction policy hook;
- tests proving append order, hash chain validation, and no model-facing write
  API.

Completion evidence:

- every action parse, validation, accepted operation, rejected operation, and
  operation result is written to the ledger;
- tampering with a prior record breaks verification.

### Phase 3. Action application layer

Deliverables:

- apply accepted open items to memory;
- apply accepted closures as closure attestations;
- apply accepted schedule requests as pending events;
- apply policy disposition records;
- log exact parameters/results for each application operation;
- refuse invalid operations without mutating substrate state.

Completion evidence:

- live-equivalent fake run can create open work, close it, schedule a wake, and
  stop from model-authored action objects only;
- no rehearsal-only closure shim is needed.

### Phase 4. Restart frontier

Deliverables:

- persisted run manifest;
- persisted action ledger;
- persisted event queue;
- persisted memory/state frontier or replayable local substrate snapshot;
- resume loader that reconstructs the latest committed frontier;
- tests for interruption before parse, after parse, after memory write, after
  event claim, and after completion.

Completion evidence:

- failed partial cycle retries from the prior frontier;
- completed cycle resumes from the new frontier;
- no duplicate accepted operations appear after restart;
- event lifecycle is not advanced by failed partial work.

### Phase 5. End-to-end no-token rehearsal, restartable

Deliverables:

- replacement for the current in-memory rehearsal using the action parser and
  ledger;
- run once through seed/open/schedule/closure/idle;
- interrupt-and-resume tests.

Completion evidence:

- final report reconstructs the whole run from persisted artifacts;
- action ledger verifies;
- no open items remain only because a model-authored closure action was
  accepted and applied.

### Phase 6. First live pilot gate

Deliverables:

- preregistration for one tiny live autonomy pilot;
- sandbox manifest;
- token/cycle budget;
- failure taxonomy;
- evaluator/report script.

Completion evidence:

- a dry run passes all gates;
- the live run can be reproduced or resumed from persisted artifacts;
- failures produce enough evidence to classify where they occurred.

## Non-Goals For This Plan

- broad model comparison;
- production-grade VM/container isolation;
- unrestricted shell/file/network autonomy;
- proving identity or moral patienthood;
- optimizing artifact quality before auditability and restartability.

## Immediate Next Step

Implement Phase 1 and Phase 2 together. The action schema without a ledger would
create unobservable control, and the ledger without a model-facing action schema
would only log the old harness-controlled path.
