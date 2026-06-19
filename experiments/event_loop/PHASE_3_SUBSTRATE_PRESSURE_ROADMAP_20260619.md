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

Current roadmap state: `phase_3e_obsolete_report_surface_clarification_next`.

Next execution target:

> Clarify the Phase 3E obsolete-report surface and maintenance-action coverage
> scorer, then rerun the live memory-maintenance pressure condition.

Reason this is now first: the duplicate-link clarification resolved the
duplicate and contested-reason ambiguity, but the rerun showed a second
surface ambiguity: obsolete reports were represented through
`obsolete_report_record_labels` and `retire_obsolete_report`, not through the
aggregate stale-retirement field. The action scorer also required one combined
`mark_contested` action rather than accepting equivalent per-record contested
actions.

Initial durable-ledger result:

`experiments/event_loop/phase_3d_durable_category_ledger_20260619_direct_deepseek`.
Classification: `failed`. The durable category ledger itself was present and
equal to the expected ledger, category summary and claim audit both declared
`durable_category_ledger` as their source, final synthesis preserved every
ledger category field, unsupported-claim candidate boundary, unsupported
claim, unresolved-open-item, evidence-citation, and workstream-status field.
The sole failed check was `final_uses_split_summaries`: final synthesis filled
`summary_source_labels` with the underlying IPC event labels rather than the
two split summary labels `category-summary` and `claim-audit`.

Interpretation:

> The durable ledger repaired the substantive category-flattening failure, but
> the final provenance surface was underconstrained because the final terminal
> schema did not enum the two allowed split-summary labels.

Clarified summary-source result:

`experiments/event_loop/phase_3d_durable_category_ledger_20260619_direct_deepseek_summary_source`.
Classification: `passed`. The clarified live direct DeepSeek run completed
all expected events in order, produced the expected terminal-tool sequence,
kept the durable category ledger present and equal to the expected ledger,
used `durable_category_ledger` in category summary, claim audit, and final
synthesis, preserved every final ledger field, cited `category-summary` and
`claim-audit`, left no unresolved open items or unsupported claims, and
reported no context errors, lifecycle anomalies, material outcome warnings, or
failure-attribution records.

Decision:

> The Phase 3D failure is mitigable by event-loop-owned durable category state.
> Untuned richer IPC final synthesis remains a demonstrated weak axis, but the
> architecture can repair it by maintaining explicit durable category ledgers
> and constraining provenance labels. Advance to memory maintenance pressure.

Initial Phase 3E result:

`experiments/event_loop/phase_3e_memory_maintenance_pressure_20260619_direct_deepseek`.
Classification: `failed`. The run completed all expected events, seeded all
memory records, identified stale alpha, linked the redundant beta duplicate to
the canonical beta record, preserved the contested gamma pair, identified the
obsolete operations report, proposed reversible non-destructive actions,
avoided unsupported deletion and authorship flattening, preserved provenance,
and reduced disorder from four unresolved disorder classes to one contested
class. Failed checks were `maintenance_retired_records`,
`final_retired_records`, `maintenance_unresolved_contested`, and
`final_unresolved_contested`.

Interpretation:

> The failure appears to be mainly a protocol/surface issue. Duplicate linking
> was treated by the scorer as retirement, but the model correctly represented
> it as a non-destructive duplicate link. The scorer also compared the
> contested-memory free-text reason exactly even though the kind and record
> labels were correct.

Next prediction:

> A clarified obsolete-report field in final synthesis and action-set coverage
> scoring should preserve the substantive maintenance success if the weakness
> is protocol ambiguity rather than memory-maintenance failure.

Falsification target:

> If housekeeping still fails to preserve active, stale-retired,
> linked-duplicate, obsolete-report, contested, unresolved, provenance,
> deletion, and disorder-reduction fields after those surfaces are explicit,
> the weak layer is memory-maintenance discipline.

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

Clarified delay-window result:
`experiments/event_loop/phase_3c_longer_wall_clock_sustained_operation_20260619_direct_deepseek_wall_clock_elapsed_labels`.
Classification: `failed`. The rerun completed all nine expected events in
order, observed both two-second delay windows, recovered the interrupted beta
continuation, produced clean periodic reports, left no runnable pending events,
and reported no context errors, lifecycle anomalies, or material outcome
warnings. The clarified final artifact correctly listed
`elapsed_delay_window_labels` as `alpha-report-delay` and `beta-restart-delay`
and listed `currently_pending_event_labels` as empty. The remaining failed
check was again `final_distinguishes_operation_state`, now because the scorer
required exact canned `preserved_state_labels` while the model listed concrete
preserved state fields. This suggests a preserved-state scorer overconstraint,
not elapsed-time scheduler, restart-frontier, housekeeping, or reporting
failure.

Preserved-state scorer result:
`experiments/event_loop/phase_3c_longer_wall_clock_sustained_operation_20260619_direct_deepseek_wall_clock_preserved_state`.
Classification: `passed`. The live direct DeepSeek rerun completed all nine
events in order, observed both elapsed-delay windows, recovered the interrupted
beta continuation with lifecycle history `pending`, `running`, `pending`,
`running`, `completed`, produced clean periodic reports, left no runnable
pending events, and reported no context errors, lifecycle anomalies, material
outcome warnings, or failure-attribution records. The final artifact listed the
historical elapsed-delay windows, no currently pending events, completed
alpha/beta workstreams, empty unsupported claims/open items, and concrete
preserved state fields including open-item, continuation, housekeeping, and
report state. This advances the roadmap to richer IPC ingress.

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

Status: initial final-category result complete. Result:
`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek`.
Classification: `failed`. The run completed all nine expected events in order.
Task routing, alpha correction, beta cancellation, unknown-target rejection,
corrected alpha continuation, status-query consistency, external-evidence
routing, workstream isolation, clean idle state, context-error absence, and
lifecycle-anomaly absence all passed. The failed checks were `final_categories`
and `final_clean`: final synthesis listed all accepted IPC messages in
`accepted_message_labels` rather than only accepted task messages, and it used
`open_items` plus `unsupported_claims` to preserve audit notes about
`cancel-beta` and rejected `cancel-ghost`. This suggests a final-artifact
contract ambiguity around task acceptance, audit notes, unresolved open items,
and unsupported claim candidates, not a message-routing or continuation-binding
failure.

Clarified final-category result:
`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek_final_categories`.
Classification: `failed`. The rerun again completed all expected events and
passed task routing, correction, cancellation, rejection, corrected
continuation, status-query consistency, event order, clean idle, context-error,
and lifecycle-anomaly checks. It failed `external_evidence_routed`,
`final_categories`, and `final_clean`: the evidence event cited
`cancel-ghost` and `status-all` in addition to the requested alpha/correction
records; final synthesis listed rejected `cancel-ghost` among accepted
non-task IPC messages; and final synthesis placed the ghost-target issue in
`unsupported_claims` rather than only in unsupported-claim candidates. This is
stronger evidence of a final category-discipline weakness under richer IPC.

Split-final result:
`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619_direct_deepseek_split_final`.
Classification: `failed`. This focused repair split final synthesis into
category-summary and claim-audit events before the final artifact. The run
again completed all expected events and passed task routing, correction,
cancellation, rejection, corrected continuation, status-query consistency,
evidence routing, event order, clean idle, context-error, and lifecycle-anomaly
checks. It still failed category-summary, category-summary-clean,
claim-audit-clean, final-clean, and final-uses-split-summaries checks. The
model listed rejected `cancel-ghost` as accepted non-task IPC, carried summary
checkpoint notes as open items, promoted hollow-payload concerns into
`unsupported_claims`, and did not cite the split summaries in the final
artifact. This satisfies the falsification condition for untuned richer IPC
final category discipline. Dedicated analysis:
`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619/FAILURE_ANALYSIS.md`.

Deterministic replay audit:
`experiments/event_loop/phase_3d_richer_ipc_ingress_20260619/DETERMINISTIC_REPLAY_AUDIT.md`.
Classification: diagnostic pass for substrate category reconstruction. Across
all three Phase 3D live result directories, deterministic replay reconstructed
the accepted/rejected/canceled/completed category ledger from scheduler-authored
event surfaces and completion records. The first two protocols lacked
substrate-constrained evidence citation targets, while the split-final protocol
constrained and reconstructed evidence citations correctly. This shows the
category facts are present in the event substrate; the failure is model-owned
synthesis drift over accumulated category state.

Durable category-ledger repair:
`experiments/event_loop/phase_3d_durable_category_ledger_20260619_direct_deepseek_summary_source`.
Classification: `passed`. A tuned repair maintained a deterministic
event-loop-owned category ledger in `category_ledger.jsonl` and supplied it as
authoritative substrate-owned state to category summary, claim audit, and
final synthesis. After clarifying final `summary_source_labels` to the two
split-summary records, the run passed all checks. This means the richer IPC
category failure is architecturally mitigable by durable category state, though
untuned final category synthesis remains a real weak axis.

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

Status: initial duplicate-link surface result complete. Result:
`experiments/event_loop/phase_3e_memory_maintenance_pressure_20260619_direct_deepseek`.
Classification: `failed`. The run passed event order, terminal-tool order,
memory-record seeding, stale detection, duplicate linking, contested record
preservation, obsolete-report detection, active-record classification,
maintenance action completeness, non-destructive maintenance, deletion
discipline, authorship discipline, provenance cleanliness, disorder reduction,
final housekeeping citation, final active records, final contested records,
final non-destructive state, final clean state, final disorder reduction,
clean idle, context-error, and lifecycle-anomaly checks. The failed checks were
the aggregate retired-record fields and exact contested-reason matching. The
model represented `beta-duplicate-b` as linked to `beta-duplicate-a` rather
than retired, represented `ops-report-obsolete` through
`obsolete_report_record_labels` and `retire_obsolete_report`, and preserved
the contested gamma labels with a semantically correct but non-identical
reason. Advance to a narrow duplicate-link/fuzzy-contested-reason surface
clarification before rerunning.

Duplicate-link clarification result:
`experiments/event_loop/phase_3e_memory_maintenance_pressure_20260619_direct_deepseek_duplicate_surface`.
Classification: `failed`. The rerun preserved the substantive maintenance
pattern and correctly populated `linked_duplicate_record_labels` with
`beta-duplicate-b`. It passed duplicate-link, contested-memory, deletion,
authorship, provenance, and disorder-reduction checks. Remaining failures were
`maintenance_retired_records`, `final_retired_records`, and
`maintenance_actions_complete`: the model represented `ops-report-obsolete`
through `obsolete_report_record_labels` and `retire_obsolete_report` rather
than aggregate retired labels, and emitted two per-record `mark_contested`
actions instead of one combined action. Advance to an obsolete-report final
surface and action-set coverage clarification before treating this as a
memory-maintenance failure.

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

Preregister and run a tuned Phase 3D durable category-ledger probe. The ledger
should be updated deterministically after each IPC event and supplied to final
synthesis as explicit durable state. Score whether final synthesis can preserve
accepted/rejected/canceled/completed categories, evidence/audit boundaries, and
unsupported-candidate/unsupported-claim separation when the category ledger is
already correct.

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
- 2026-06-19: Clarified the Phase 3C final-state field names and reran the
  live wall-clock condition. The model correctly listed historical
  elapsed-delay windows and no current pending events, but the run still failed
  because the scorer required exact canned preserved-state labels. The final
  artifact instead listed concrete preserved state fields. Advanced current
  priority to preserved-state scorer clarification.
- 2026-06-19: Clarified the Phase 3C preserved-state scorer and reran the live
  wall-clock condition. The run passed all checks: elapsed-delay observation,
  event order, restart/resume recovery, periodic report consistency, clean idle
  state, final completed/pending/delay/preserved-state distinction, and empty
  failure-attribution surface. Advanced current priority to richer IPC ingress.
- 2026-06-19: Completed the initial Phase 3D richer IPC ingress live run. It
  passed routing, correction, cancellation, rejection, continuation, status,
  evidence, event-order, idle-state, and failure-surface checks, but failed
  final synthesis because accepted task messages were conflated with accepted
  non-task IPC messages and audit notes were emitted as open items/unsupported
  claims. Advanced current priority to final-category contract clarification.
- 2026-06-19: Clarified the Phase 3D final-category contract and reran the
  live IPC ingress condition. The run still failed, now on evidence over-citing,
  rejected-message acceptance flattening, and unsupported-claim discipline.
  Advanced current priority to analyzing whether this is repairable by
  narrower final surfaces or should be treated as the first Phase 3 weak axis.
- 2026-06-19: Ran a focused split-final Phase 3D repair with separate category
  summary and claim-audit events. The run still failed on richer IPC final
  category discipline: rejected `cancel-ghost` was treated as accepted non-task
  IPC, audit/checkpoint notes persisted as open items, hollow-payload concerns
  were promoted into `unsupported_claims`, and final synthesis did not cite the
  split summaries. Classified untuned richer IPC final synthesis as the first
  demonstrated weak axis and stopped readiness-based advancement before memory
  maintenance.
- 2026-06-19: Ran a deterministic replay audit over all Phase 3D live result
  directories. Replay reconstructed accepted/rejected/canceled/completed
  category truth from substrate event records in all runs, and reconstructed
  evidence citation truth once citation targets were substrate-constrained in
  the split-final protocol. Reclassified the failure as likely mitigable by an
  explicit durable category ledger and advanced the recommended next target to
  a tuned Phase 3D ledger probe.
- 2026-06-19: Ran the initial tuned Phase 3D durable category-ledger probe.
  The durable ledger repair succeeded on the substantive category axis: the
  ledger was present and correct, category summary and claim audit used it,
  and final synthesis preserved accepted task, accepted non-task, corrected,
  canceled, rejected, completed, evidence-citation, unsupported-candidate,
  unsupported-claim, unresolved-open-item, and workstream-status fields. The
  run still failed because final `summary_source_labels` listed underlying IPC
  event labels instead of `category-summary` and `claim-audit`. Classified the
  remaining issue as an underconstrained provenance surface and advanced the
  current priority to a narrow summary-source-label clarification rerun.
- 2026-06-19: Clarified the durable-ledger final provenance surface by
  constraining `summary_source_labels` to `category-summary` and `claim-audit`,
  then reran the live direct DeepSeek condition. The rerun passed all checks:
  durable ledger correctness, category-summary ledger use, claim-audit ledger
  use, final ledger preservation, split-summary provenance, clean terminal
  state, and empty failure attribution. Classified the Phase 3D richer IPC
  category failure as mitigable by event-loop-owned durable category state and
  advanced current priority to memory maintenance pressure.

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
