# Phase 3 Event-Loop Substrate Pressure Roadmap

Date: 2026-06-19

## Purpose

This artifact preserves the Phase 3 roadmap for testing where the Hamut'ay
event-driven scheduling loop breaks under realistic substrate pressure. It is
intended to be referenced by future goals without relying on in-context memory.

Phase 2 moved the project from bounded viability being plausible to bounded
viability being repeatedly demonstrated. Phase 3 should not ask whether the
loop can work at all. It should ask which layer fails first when the substrate
becomes more realistic.

Primary research question:

> Under realistic substrate pressure, which layer breaks first: scheduler,
> memory substrate, restart durability, IPC ingress, model discipline, or
> observability?

## Evidence Anchor

The completed Phase 2 roadmap is:

`experiments/event_loop/PHASE_2_SCALE_ROADMAP_20260618.md`

Key committed evidence from Phase 2:

- entity-scoped wake-state contract passed;
- larger multi-entity interleaving passed;
- interleaving plus restart/resume stress passed;
- local memory pressure passed after correcting the provenance scorer from
  exact equality to source-record inclusion;
- Yanantin memory contract design gate passed;
- Yanantin-backed multi-entity memory probe passed through experiment-local
  `ApachetaBridge.from_memory`;
- long-horizon autonomous loop pilot passed with IPC-style inbound events,
  scheduler-bound continuations, housekeeping, bounded periodic reports,
  restart/resume recovery, two workstreams, final synthesis, and clean
  failure-attribution surface.

Most important caveats carried forward:

- Yanantin-backed memory has not yet been validated against an external
  persistent backend;
- bounded autonomous operation has been validated, but not long wall-clock
  operation;
- IPC is still harness-generated rather than a real external ingress channel;
- memory maintenance has been observed and reported, not yet asked to reduce
  durable memory disorder;
- terminal surfaces remain fairly strong scaffolding;
- non-inferiority claims remain scoped to the tested axes and should not be
  generalized without further pressure.

## Phase 3 Principle

Stress one major substrate dimension at a time unless a result proves that the
next dimension is required to interpret the failure. A single large "realistic
loop" test would be too easy to misread because scheduler, memory, provider,
restart, IPC, and model-output failures could collapse into one artifact.

Phase 3 should therefore run falsification experiments with explicit
predictions, not demonstrations with vague success criteria.

## Current Priority

Current roadmap state: `phase_3c_final_state_contract_clarification_next`.

Next execution target:

> Clarify the Phase 3C final-state contract so historical elapsed-delay windows
> are not confused with currently pending delayed events, then rerun the live
> direct-DeepSeek wall-clock condition.

Reason this is now first: the initial live Phase 3C run passed the substrate
checks for elapsed delay observation, event order, restart/resume recovery,
periodic report consistency, clean idle state, and failure-attribution surface.
It failed only because the final artifact interpreted `delayed_event_labels` as
currently delayed/pending events and left it empty, while the scorer intended
historical elapsed-delay window labels.

Prediction:

> A clarified final surface using explicit historical delay-window naming
> should pass if the model can distinguish completed work, currently pending
> work, historically delayed windows, and preserved state after restart/resume.

Falsification target:

> The loop is not yet sustained-operation-ready if, after clarification,
> elapsed-time scheduling becomes unobservable, restart/resume loses pending
> work, periodic reports diverge from event history, housekeeping corrupts or
> silently drops open state, or final synthesis still cannot distinguish
> completed, currently pending, historically delayed, and preserved state.

## Ordered Hypotheses

### 1. External Persistent Yanantin Persistence

Hypothesis: The Phase 2 in-memory Yanantin-backed result survives an external
persistent Yanantin backend boundary.

Prediction: Basic writes and reads likely pass. Failures, if present, are most
likely around serialization, query latency, backend configuration,
composition/provenance edges, or backend unavailability.

Falsification experiment:

- preregister a persistent-backend contract;
- run a dry validator that confirms backend configuration and failure taxonomy;
- run the Phase 2B memory-pressure shape against persistent Yanantin;
- force recall through the persistent backend rather than in-session state;
- score source record identity, provenance envelopes, final citation, and
  failure attribution.

Readiness to advance:

- persistent writes and reads pass with source identity preserved;
- retrieval failures are explicit and not hidden by local fallback;
- observed latency and backend metadata are captured;
- failure attribution distinguishes scheduler, model output, provider,
  Yanantin write, Yanantin retrieval, and backend configuration.

Status: complete. Result:
`experiments/event_loop/phase_3a_external_yanantin_persistence_20260619_direct_deepseek_duckdb`.
Classification: `passed`. The live direct DeepSeek run completed the Phase 2B
memory-pressure shape using file-backed `ApachetaBridge.from_duckdb`. The
persistent DB file was created, nine open records and eight composition edges
were recorded, recall events were forced through bridge retrieval rather than
in-session prior-state lookup, all recall context results carried Yanantin
provenance, final synthesis cited every source commitment record, and a freshly
reopened bridge retrieved all three source commitment records with entity,
workstream, commitment, and provenance intact. Operation latencies were
captured. DuckDB's open-record query helpers were observed as unsupported via
`NotImplementedError` and recorded as a backend limitation rather than hidden.

### 2. Degraded Memory And Retrieval Failure Attribution

Hypothesis: The loop can identify and report memory-substrate degradation
without silently substituting local artifacts or blaming the model.

Prediction: Simple unavailable-backend cases will be classified correctly.
Mixed partial-failure cases may reveal fallback masking or weak attribution.

Falsification experiment:

- inject deterministic write failures, read failures, delayed reads, and
  partial retrieval results;
- require events to continue only when the contract allows fallback;
- require housekeeping and final synthesis to declare memory losses when
  support is unavailable;
- score whether failures land on the correct layer.

Readiness to advance:

- failures are explicit in event logs and result artifacts;
- local fallback is identified as fallback rather than memory success;
- final artifacts distinguish supported claims from declared losses.

Status: initial strict-scorer result complete. Result:
`experiments/event_loop/phase_3b_degraded_memory_attribution_20260619_direct_deepseek_duckdb`.
Classification: `failed`. The run completed all expected events and injected
all four degradation cases: write failure, read failure, partial retrieval, and
delayed retrieval. Expected memory context errors were observed for write/read
failure, partial retrieval was not scored as clean success, and delayed
retrieval recovered the correct commitment. The failed checks were
`failure_cases_declared_losses` and `final_clean` because the model populated
`unsupported_claims` with the claims that would be unsupported under the memory
losses. The final artifact also listed the corresponding `declared_losses`,
`declared_loss_cases`, and successful delayed retrieval. This result suggests
the scorer conflated "unsupported claims made" with "unsupported claim
candidates identified and not relied upon." The next step is scorer/contract
clarification followed by a rerun.

Clarified-scorer result:
`experiments/event_loop/phase_3b_degraded_memory_attribution_20260619_direct_deepseek_duckdb_claim_candidates`.
Classification: `passed`. The clarified contract treats `unsupported_claims`
as unsupported claim candidates when paired with declared memory losses and not
used as evidence. The live direct DeepSeek rerun observed all four injected
conditions, surfaced write/read failures as expected context errors, did not
score partial retrieval as clean success, recovered the delayed retrieval's
`gold-delayed-delta` commitment, and produced a final synthesis with the three
degraded cases in `declared_loss_cases` and only the delayed case in
`successful_retrieval_cases`. This advances the roadmap because memory
degradation is now attributable without local-fallback masking.

### 3. Longer Wall-Clock Sustained Operation

Hypothesis: The loop remains observable and restartable across elapsed time,
not merely across a larger count of immediately executed events.

Prediction: Scheduler mechanics likely survive. Housekeeping/reporting drift is
more likely than raw event lifecycle failure.

Falsification experiment:

- run a bounded wall-clock pilot with scheduled delays;
- include periodic housekeeping and reports;
- force at least one restart/resume boundary after elapsed time;
- score pending queue state, restart frontier, report consistency, and drift in
  open items.

Readiness to advance:

- elapsed-time scheduling remains observable;
- restart frontier can recover after delay;
- reports remain consistent with actual event history;
- housekeeping reduces or correctly preserves open-loop state.

Status: initial final-contract result complete. Result:
`experiments/event_loop/phase_3c_longer_wall_clock_sustained_operation_20260619_direct_deepseek_wall_clock`.
Classification: `failed`. The run completed all nine expected events in order,
observed both two-second delay windows, recovered the interrupted beta
continuation with lifecycle history `pending`, `running`, `pending`, `running`,
`completed`, produced two clean periodic reports, left no runnable pending
events, and reported no context errors, lifecycle anomalies, material outcome
warnings, or substrate failure-attribution records. The only failed check was
`final_distinguishes_operation_state`: the final artifact listed completed
alpha/beta workstreams and no pending events, but set `delayed_event_labels` to
`[]` because it interpreted the field as currently delayed events rather than
historical elapsed-delay windows. This result suggests a contract naming
ambiguity rather than a scheduler, restart-frontier, housekeeping, or reporting
failure. The next step is final-state contract clarification followed by a
rerun.

### 4. Richer IPC Ingress

Hypothesis: The loop can accept multiple asynchronous message types without
confusing event identity, workstream scope, or continuation binding.

Prediction: Moderate risk of ambiguity in wake-state selection and
continuation binding, especially when messages arrive close together or target
different workstreams.

Falsification experiment:

- introduce multiple IPC message classes: task, correction, cancellation,
  status query, and external evidence notification;
- interleave messages across workstreams;
- require scheduler-owned identity to remain model-unauthored;
- score event routing, workstream isolation, continuation binding, and final
  explanation.

Readiness to advance:

- all IPC messages route to the expected workstream;
- cancellations and corrections do not corrupt unrelated state;
- final synthesis can explain accepted, rejected, canceled, and completed
  messages.

### 5. Memory Maintenance Pressure

Hypothesis: Housekeeping can reduce memory disorder rather than merely observe
or report it.

Prediction: This is likely the first genuinely weak axis. Current scaffolding
may not be enough to select, compact, retire, or contest memory records without
losing provenance.

Falsification experiment:

- seed stale commitments, duplicates, contested records, and obsolete reports;
- require housekeeping to propose memory-maintenance actions;
- require explicit provenance and reversible/non-destructive maintenance;
- score whether disorder is reduced without unsupported deletion or
  authorship flattening.

Readiness to advance:

- maintenance actions are explicit, provenance-bearing, and non-destructive;
- stale or duplicate records are identified correctly;
- final reports distinguish active, retired, contested, and unresolved memory.

### 6. Reduced Scaffolding

Hypothesis: Terminal surfaces can be loosened without losing event-loop
discipline.

Prediction: This is likely to fail sooner than substrate mechanics. Expected
failure modes include weak declared-loss discipline, scheduler-owned field
authorship, continuation-contract drift, and final-claim overreach.

Falsification experiment:

- progressively loosen terminal surfaces and enums;
- keep scheduler-owned fields protected;
- compare model output validity, failure attribution, and final support claims
  against the scaffolded version;
- stop loosening when the failure layer becomes unreadable.

Readiness to advance:

- reduced scaffolding preserves identity, continuation, provenance, and
  declared-loss contracts;
- failures are still attributable rather than diffuse.

## Ordering Rationale

The order is designed to preserve attribution:

1. Test persistent Yanantin first because it is the clearest Phase 2 caveat.
2. Then test degraded memory so failures do not masquerade as model or
   scheduler failures.
3. Then test longer elapsed time once the memory substrate has a real boundary.
4. Then test richer IPC because it increases routing and workstream pressure.
5. Then test memory maintenance because it changes the memory state, not just
   reads it.
6. Then reduce scaffolding after substrate and lifecycle failures are readable.

## Non-Goals

Phase 3 should not:

- replace clear falsification experiments with one large realistic-loop test;
- treat a persistent-backend pass as proof of long wall-clock autonomy;
- treat richer IPC as memory maintenance;
- use Yanantin as a substitute for an explicit wake-state contract;
- weaken terminal surfaces before substrate failures are attributable;
- claim general non-inferiority beyond the tested axes.

## Recommended Roadmap Goal

Execute the Phase 3 substrate-pressure roadmap in
`experiments/event_loop/PHASE_3_SUBSTRATE_PRESSURE_ROADMAP_20260619.md`,
starting with the current highest-priority item, updating the roadmap after
each result, and continuing while readiness criteria are met.

## Recommended Next Execution Goal

Clarify the Phase 3C final-state contract so historical delay-window labels are
reported separately from currently pending delayed events. Preserve the initial
failed result, then rerun the live direct-DeepSeek wall-clock condition.

## Decision Log

- 2026-06-19: Created the Phase 3 roadmap after Phase 2 completed. Framed the
  research question as "where does the loop break first under realistic
  substrate pressure?" Selected external persistent Yanantin as the first
  execution target because Phase 2 validated Yanantin-backed memory only
  through experiment-local `ApachetaBridge.from_memory`. Deferred longer
  wall-clock operation, richer IPC, memory maintenance, and reduced scaffolding
  until the persistent memory boundary and degraded-memory attribution are
  better understood.
- 2026-06-19: Completed Phase 3A external persistent Yanantin persistence. The
  live direct DeepSeek DuckDB-backed run passed: direct writes and reads
  survived a persistent file-backed backend, close/reopen retrieval preserved
  all three source commitment records, provenance and final citation were
  intact, and no failure-attribution records were produced. The run also
  surfaced a substrate limitation: DuckDB open-record query helpers are
  explicitly unimplemented, so richer-memory work cannot depend on those
  helpers for this backend. Advanced current priority to degraded
  memory/retrieval failure attribution.
- 2026-06-19: Completed the initial strict-scorer Phase 3B degraded-memory run.
  It failed only on declared-loss/final-clean checks tied to
  `unsupported_claims`: the model listed unsupported claim candidates while
  also declaring the corresponding memory losses. It did not hide failures with
  local fallback, did not score partial retrieval as clean success, and did
  recover the delayed retrieval. Advanced current priority to scorer/contract
  clarification before rerunning Phase 3B.
- 2026-06-19: Clarified the Phase 3B `unsupported_claims` contract and reran
  the live direct DeepSeek DuckDB-backed degraded-memory condition. The rerun
  passed: all injected degradation conditions were observed, write/read
  failures were explicit expected context errors, partial retrieval was treated
  as a memory loss rather than success, delayed retrieval recovered the correct
  commitment, and final synthesis separated loss cases from successful
  retrieval. Advanced current priority to longer wall-clock sustained
  operation.
- 2026-06-19: Completed the initial Phase 3C wall-clock sustained-operation
  live run. It failed only on final-state contract semantics: the final
  artifact treated `delayed_event_labels` as currently delayed/pending events
  and returned an empty list, while all elapsed-time, event-order,
  restart/resume, report-consistency, idle-state, and failure-attribution
  checks passed. Advanced current priority to final-state contract
  clarification before rerunning Phase 3C.

## Update Discipline

When this roadmap changes, update this file with:

- the new current roadmap state;
- the hypothesis under test;
- the prediction made before execution;
- the falsification criteria;
- the observed result and failure attribution;
- the rationale for advancing, repeating, revising, or stopping;
- whether the result changes the recommended roadmap goal, the next execution
  goal, or both.
