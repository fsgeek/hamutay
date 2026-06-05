# Event-Loop Research Retrospective

Filed: 2026-06-05 after the scheduled-wake, simulated-time, terminal-surface,
model-owned policy, disposition, and evidence-resume experiments.

## Scope

This retrospective covers the event-loop scheduling sequence under
`experiments/event_loop`. It complements
`docs/continuity-research-synthesis-20260605.md`, which synthesized the
identity, curator, carry-forward, and claim-table continuity experiments.

The research question here is operational:

> Can a Hamut'ay instance use an observable event loop to schedule, re-enter,
> inspect context, continue bounded work, stop, or request evidence across
> discontinuous cycles?

This is not a production-readiness claim. The relevant question is whether the
event loop is viable as a research scaffold for bounded autonomy.

## Current Answer

Yes, with narrowed scope.

The event-loop substrate is viable enough for research use. The loop can now:

- persist scheduled events and lifecycle records;
- distinguish pending, running, completed, failed, expired, waiting, and idle
  states;
- run under deterministic simulated time;
- resolve scheduled context through `recall`, `compare`, and bounded `walk`;
- deliver resolved context into wake envelopes;
- validate and repair scheduled wake outputs while preserving first-pass
  failures as data;
- protect or validate continuity invariants;
- run terminal surfaces instead of broad `think_and_respond` for bounded wake
  tasks;
- accept model-emitted continuation requests and bind follow-up events to the
  actual committed result record;
- enforce continuation budgets and quiesce when no fresh continuation is
  emitted;
- record model-owned policy dispositions separately from lifecycle state;
- turn evidence-blocked dispositions into evidence requests, fulfillments, and
  pending resume events.

The unresolved questions have shifted. The main uncertainty is no longer
"can the scheduler loop execute?" It is:

> What model-owned decisions can safely and usefully inhabit the loop?

The current frontier is evidence use, policy choice, and bounded autonomous
work inside the scheduler.

## Chronological Map

### 1. Exploratory Self-Scheduling

Primary artifact:

- `experiments/event_loop/self_scheduling_revision_probe_20260601/analysis.md`

The first probe showed that an instance could schedule future reflection,
resolve recall/compare context, and produce response-level epistemic revision.
It also exposed the first core confound: the visible response revised the claim,
but the durable identity object did not. Revision stayed response-local.

Surviving claim:

- Scheduled reflection can create a future wake with usable context.

Narrowed claim:

- Scheduled reflection does not by itself imply durable state revision. Durable
  revision requires explicit state-object weaving or a narrower terminal
  surface.

### 2. Model Suitability And Tool-Path Gates

Primary artifacts:

- `experiments/event_loop/scheduler_revision_model_panel_20260603/analysis.md`
- `experiments/event_loop/scheduler_tool_gate_20260603/analysis.md`
- `experiments/event_loop/protocol_gate_scout_20260603/analysis.md`

The model panel separated three concerns that had previously been tangled:

- identity-object initialization;
- terminal tool-call behavior;
- scheduler-path execution.

KIMI K2.6 was clean across initialization and scheduled wake execution. Qwen
Plus thinking initialized valid durable state but failed the scheduled
tool-call path. DeepSeek V4 Pro was a boundary model: unreliable initialization,
but able to complete the scheduler path once initialized.

Surviving claims:

- Scheduler experiments need initialization gates.
- Scheduler experiments need tool-path gates.
- Identity-object literacy is necessary but not sufficient for scheduler
  suitability.

Falsified or unsupported claim:

- The scheduled arm did not show a stronger semantic revision advantage over
  direct follow-up in the preregistered model panel.

### 3. Deterministic Scheduler Semantics

Primary artifacts:

- `experiments/event_loop/scheduler_des_reentry_diagnostic_20260605/analysis.md`
- `experiments/event_loop/bounded_autonomy_des_20260605/analysis.md`
- `experiments/event_loop/pending_disposition_des_20260605/analysis.md`
- `experiments/event_loop/suppression_source_des_20260605/analysis.md`
- `experiments/event_loop/fork_join_des_20260605/analysis.md`
- `experiments/event_loop/policy_boundary_des_20260605/analysis.md`

The deterministic simulated-time work separated loop semantics from provider
latency and wall-clock execution. Under deterministic responses and simulated
time, the scheduler could claim due events, build wake envelopes, resolve
context, append wake records, and preserve strict merge failures without
mutating accepted state.

Surviving claims:

- Event lifecycle semantics are testable without live provider calls.
- Failed wake outputs can preserve diagnostic evidence without mutating durable
  state.
- The event loop should keep simulated-time contract tests as the semantic
  baseline.

Narrowed claim:

- Live-provider stalls are not clean evidence against event-loop semantics.
  They are runtime-boundary evidence: provider latency, timeout/cancellation,
  and process supervision must be tracked separately.

### 4. Scheduled Context And Graph Walks

Primary artifacts:

- `experiments/event_loop/scheduler_walk_context_des_20260605/analysis.md`
- `experiments/event_loop/live_scheduler_walk_context_gate_20260605/analysis.md`
- `experiments/event_loop/update_exemplar_walk_gate_20260605/analysis.md`
- `experiments/event_loop/strict_repair_walk_gate_20260605/analysis.md`
- `experiments/event_loop/scheduled_walk_validation_repair_20260605/analysis.md`
- `experiments/event_loop/scheduled_walk_strict_continuity_20260605/analysis.md`

The graph/context branch showed that scheduled wakes can request bounded graph
neighborhood evidence through `walk`, and that event envelopes can preserve both
the request and resolved evidence.

The live scheduled-walk panels exposed a consistent model behavior: DeepSeek
often mentioned delivered graph evidence in prose but did not persist the
required durable fields on first pass. Validation and one bounded repair call
could recover the state when the contract named both task evidence and
continuity invariants.

Surviving claims:

- `requested_context` can safely support `recall`, `compare`, and bounded
  `walk` as scheduler-facing context tools.
- Graph walk delivery works as substrate evidence.
- First-pass prose/object mismatch is a real live-model failure mode.
- Validation must score task evidence and continuity invariants separately.
- Bounded repair is useful only if first-pass invalidity remains logged.

Narrowed claim:

- A validator that checks only task-specific fields is too narrow. It can
  allow collateral identity or framework-field drift.

### 5. Simulated-Time Control Loop

Primary artifact:

- `experiments/event_loop/simulated_time_scheduler_20260605/analysis.md`

`step_pending_events` gave the scheduler a DES-compatible control surface. The
loop can run due events, terminalize expired events, leave future events
pending, report `next_wake_at`, and stop without implicitly advancing time.

Surviving claims:

- Simulated time separates clock mechanics from loop mechanics.
- The scheduler can function as a discrete event simulation scaffold for
  research.
- A controller can now decide whether to advance time, stop, or inject more
  work.

### 6. Delayed Task Continuity And Compression

Primary artifacts:

- `experiments/event_loop/matched_delayed_task_continuity_20260605/analysis.md`
- `experiments/event_loop/seeded_clean_compression_20260605/analysis.md`
- `experiments/event_loop/compression_repair_gate_20260605/analysis.md`

The matched delayed-task panel was a useful falsification: event-plus-recall
did not outperform identity-only on content recovery because the task was too
easy. The model could simply preserve the full deferred fact in durable state.

Compression made the question sharper. When clean compression prevented
whole-fact carriage, the clean event-plus-recall row recovered the deferred fact
from recall context. Dirty rows were culled before due execution.

Surviving claims:

- Event-plus-recall works as a continuity substrate.
- Identity-only can recover easy delayed facts when the full fact remains in
  state.
- Recall benefit is only meaningful when the task creates an actual memory
  boundary.
- Compression/loss boundaries need structured validation and likely repair.

Falsified claim:

- The simple matched delayed-task probe did not demonstrate a content-recovery
  advantage for event-plus-recall over identity-only.

### 7. Bound Chains And Protocol Ergonomics

Primary artifacts:

- `experiments/event_loop/substrate_bound_chain_20260605/analysis.md`
- `experiments/event_loop/second_wake_filtered_integration_20260605/analysis.md`
- `experiments/event_loop/terminal_surface_substrate_smoke_repair_20260605/analysis.md`

The first substrate-bound chain failed before record-ID recall could be tested:
the model did not commit a valid `continuation_request` in durable state. Later
second-wake integration showed filtered context delivery was reliable once the
first wake was made valid. Remaining failures came from durable update protocol
issues such as delete-plus-update overlap or malformed tool arguments.

Terminal surfaces changed the boundary. A narrow completion surface removed the
broad `deleted_regions` affordance for the bounded task and produced clean
scheduled second-wake completions.

Surviving claims:

- Bound record context can be delivered reliably.
- Filtered field recall can avoid leaking unrelated activity logs or exact
  secrets.
- The active failure in these panels was protocol ergonomics, not context
  delivery.
- Terminal surfaces are a stronger pattern than broad `think_and_respond` for
  bounded scheduled wake tasks.

Narrowed claim:

- Prose-only event purposes are not enough for novel continuation contracts.
  Scheduled wakes need explicit schemas or durable update examples.

### 8. Generated Continuations And Budgeted Chains

Primary artifacts:

- `experiments/event_loop/generated_chain_auto_continuation_repair_20260605/analysis.md`
- `experiments/event_loop/budgeted_three_wake_chain_repair_20260605/analysis.md`
- `experiments/event_loop/continuation_placeholder_scope_20260605/analysis.md`

Generated continuation became viable after the scheduler changed from
level-triggered consumption of inherited durable `continuation_request` state to
edge-triggered consumption of newly emitted raw output.

The repaired three-wake chain showed a clean positive map point for longer
bounded chains: terminal surfaces, placeholder scoping, record binding,
continuation budgets, and closed non-secret schemas worked together.

Surviving claims:

- Model-generated continuation requests can drive follow-up scheduling.
- Continuations must be edge-triggered by fresh raw output, not inherited state.
- Placeholder scoping matters for nested future continuation templates.
- `max_auto_continuations` can pace generated chains across scheduler steps.
- Closed schemas prevent accidental secret leakage into explanatory side fields.

Falsified or repaired assumption:

- Persistent durable continuation requests are dangerous as a scheduler trigger.
  They can create inherited continuation loops.

### 9. Model-Owned Policy And Dispositions

Primary artifacts:

- `experiments/event_loop/model_owned_continuation_policy_20260605/analysis.md`
- `experiments/event_loop/model_owned_policy_boundary_20260605/analysis.md`
- `experiments/event_loop/policy_disposition_observability_20260605/analysis.md`
- `experiments/event_loop/model_owned_policy_boundary_disposition_20260605/analysis.md`

The model-owned continuation panel showed that DeepSeek could emit a complete
scheduler-valid continuation request through a terminal surface, preserve the
`<result_record_id>` placeholder, and stop after a follow-up wake.

The policy-boundary panel then tested three actions: `continue_after`,
`stop_complete`, and `ask_external_evidence`. The live panel selected the
correct action in all six rows. Disposition capture then made those decisions
append-only sidecar records, separate from lifecycle state.

Surviving claims:

- The scheduler can accept a model-owned continuation request through a closed
  terminal surface.
- A wake lifecycle status of `completed` is insufficient as a control-loop
  outcome.
- Policy dispositions should be sidecar records, not lifecycle states.
- The current three-action vocabulary is enough for the next research slice.

Narrowed claim:

- The successful policy selection was still scaffolded. It does not establish
  open-ended autonomous policy selection.

### 10. Evidence-Blocked Work And Resume

Primary artifacts:

- `experiments/event_loop/model_owned_policy_boundary_disposition_20260605/analysis.md`
- `experiments/event_loop/evidence_block_resume_20260605/analysis.md`

The disposition panel showed that live model output could choose
`ask_external_evidence` when required evidence was missing. The evidence-resume
smoke then validated the deterministic control path:

`blocked wake -> evidence request -> evidence fulfillment -> pending resume event`

The original blocked wake remained lifecycle-complete. Evidence request and
fulfillment were append-only records. The resume event linked to both request
and fulfillment, recalled the blocked wake result, and carried
`evidence_context`.

Surviving claims:

- Evidence-blocked work can be represented as data rather than inferred from
  idle completion.
- Evidence requests and fulfillments should be append-only sidecar records.
- Resumption should create a new pending event rather than rewrite the blocked
  wake.

Open claim:

- It is not yet known whether a live model will use `evidence_context` on the
  resumed wake to revise or complete the previously blocked task.

## Surviving Hypotheses By Design Area

### Scheduler Mechanics

Supported:

- The scheduler loop can persist, claim, run, complete, fail, expire, suppress,
  and summarize events.
- Deterministic simulated time is adequate for event-loop semantic tests.
- Scheduled event envelopes can carry validated context requests and resolved
  context results.
- Lifecycle summaries can remain clean while sidecar records carry richer
  scheduler outcomes.

### Context Delivery

Supported:

- `recall`, `compare`, and bounded `walk` can operate as event-time context
  tools.
- Record-ID and filtered field recall can deliver targeted generated context.
- Context delivery failures are now separable from durable integration
  failures.

### Durable Integration

Supported:

- First-pass model output often fails to turn delivered context into durable
  fields.
- Bounded validation/repair can recover many failures.
- Repairs must be logged as repairs, not treated as ordinary success.
- Contracts must include continuity invariants, not only task output fields.

### Terminal Surfaces

Supported:

- Narrow terminal surfaces can eliminate broad-state protocol errors for
  bounded scheduled tasks.
- Terminal surfaces are preferable when a wake has a known load-bearing output
  schema.

### Continuation Policy

Supported:

- Model-emitted continuation requests can be scheduler-valid under a closed
  surface.
- Continuation must be edge-triggered by current raw output.
- Continuation budgets can pace generated chains and prevent runaway loops.

### Evidence Handling

Supported deterministically and partially live:

- Live model output can choose `ask_external_evidence` in the policy-boundary
  condition.
- The scheduler can capture that disposition and create evidence request,
  fulfillment, and resume records.

Still open:

- Live use of supplied evidence on resume.
- Partial evidence.
- Conflicting evidence.
- Multiple open evidence requests.

## Falsified Or Narrowed Hypotheses

The event-loop arm falsified or narrowed several attractive early claims:

- Scheduled reflection did not guarantee durable epistemic revision.
- A simple delayed-task probe did not show event-plus-recall superiority when
  identity-only could preserve the whole fact.
- Identity-object literacy alone did not imply scheduler suitability.
- Context delivery alone did not imply durable state integration.
- Prose-only scheduled purposes were not enough for novel continuation
  contracts.
- Broad `think_and_respond` was too error-prone for some bounded wake tasks.
- Persistent durable continuation requests were unsafe as level-triggered
  scheduler signals.
- Validator contracts that ignored continuity invariants were too narrow.

These are not failures of the research arm. They are the useful map points that
made the current design sharper.

## Current Design Requirements

The following requirements are now evidence-backed:

1. Keep event lifecycle state and policy disposition state separate.
2. Preserve first-pass invalid outputs and repair attempts as data.
3. Use deterministic simulated-time tests as the scheduler semantic contract.
4. Validate requested context before event persistence.
5. Preserve resolved context on failed wakes when resolution occurred.
6. Score task evidence and continuity invariants separately.
7. Protect or strictly validate framework-owned fields.
8. Use terminal surfaces for bounded scheduled wake outputs.
9. Trigger auto-continuation only from fresh raw output.
10. Bind generated continuations to committed result record IDs.
11. Pace continuation chains with explicit budgets.
12. Represent evidence-blocked work as append-only requests and fulfillments.
13. Resume evidence-blocked work with a new event, not mutation of the blocked
    wake.

## Current Limits

The evidence is still narrow in these ways:

- Most live positive panels are small and single-model, often DeepSeek V4 Pro.
- Strong results frequently rely on terminal surfaces or explicit schemas.
- First-pass autonomy remains weaker than scaffolded autonomy.
- Repair succeeds in many panels but is not itself an explanation of native
  model competence.
- Real-clock/provider runtime hardening is not the main research goal, but
  live stalls remain operational confounds.
- The latest evidence-resume path is deterministic; live resumed evidence use
  has not been tested.

## Status Of The Event-Loop Research Arm

The scheduling loop itself is viable as a research scaffold. The strongest
surviving operational claim is:

> A bounded, observable event loop can carry model-authored work across
> discontinuous cycles when the substrate validates context, uses explicit
> terminal surfaces for load-bearing outputs, records repairs, and separates
> lifecycle from policy disposition.

The work has therefore moved from scheduler mechanics to model-owned control
behavior.

## Remaining Known Questions

The known next questions are:

1. Can a live model use fulfilled `evidence_context` on resume to complete or
   revise a previously evidence-blocked task?
2. Can the loop distinguish partial evidence from sufficient evidence?
3. Can the loop preserve uncertainty or request adjudication under conflicting
   evidence?
4. Can multiple open evidence requests remain addressable through fulfillment
   and resume?
5. Can a model choose among continue, stop, ask evidence, defer, and
   self-directed investigation with less scaffolding?
6. Can bounded autonomous work produce useful artifacts under the same
   observability and validation constraints?

## Recommended Next Step

Run a live evidence-block resume panel.

This is the cleanest next falsification target because the deterministic
substrate now works. The experiment should test whether the model uses newly
supplied evidence on resume rather than fossilizing the prior blocked state or
claiming completion without evidence.

If that passes, move to partial/conflicting evidence. If it fails, the next
substrate question is whether `evidence_context` must be rendered through a
narrower terminal surface, a standard recall-like context result, or a dedicated
evidence-adjudication surface.
