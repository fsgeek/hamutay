# Hamut'ay Event-Loop Research Program Goals

Date: 2026-06-12

Source framework:
`docs/event-loop-research-program-framework-20260612.md`

Purpose: convert the research-program framework into actionable goal-tool
targets. This is an execution guide, not a replacement for the framework. If a
result contradicts the framework, update the research map before continuing the
sequence.

## Use Discipline

Each goal should follow the same loop:

1. derive the research question and hypothesis from the framework;
2. write or update preregistration before live model calls;
3. implement only framework changes needed for that experiment;
4. run the falsification experiment;
5. preserve raw requests, responses, traces, scorer outputs, and attribution;
6. write the result artifact;
7. commit and push code, preregistration, OTS timestamps, and result artifacts;
8. decide whether the next goal still follows from the evidence.

Stop conditions:

- Do not broaden a goal after seeing results.
- Do not convert secondary recovery into primary success unless preregistered.
- Do not treat provider/protocol failures as model failures.
- Do not proceed to a higher-autonomy stage if the action surface cannot
  produce interpretable rows.
- Do not add real-clock complexity until a research question needs real elapsed
  time.

## Goal Sequence

| Order | Goal | Depends On | Primary Output |
| ---: | --- | --- | --- |
| 1 | Harden the live action/control surface | Framework, DeepSeek transport result | prompt/schema/validator changes plus gate result |
| 2 | Build and run live evidence-resume panel | Goal 1 | clean evidence-resume result |
| 3 | Build evidence-boundary scorers and run boundary panel | Goal 2 | partial/conflicting/multiple evidence result |
| 4 | Tighten policy continuation validation | Goals 1-3 or earlier if needed | strict policy/action consistency result |
| 5 | Build audit-grade longer-run boundary | Goals 1-4 | ledger/restart/reconstruction readiness |
| 6 | Run less-scaffolded bounded investigation panel | Goals 1-5 | bounded autonomy map point |
| 7 | Build working-set accounting and memory substitute/adapter | Goals 1-6 | working-set experiment readiness |
| 8 | Run working-set management matched panel | Goal 7 | model-managed working-set result |
| 9 | Add wall-clock adapter only if needed | Goal 8 or explicit runtime question | DES/wall-clock boundary result |
| 10 | Run artifact non-inferiority panel | Goals 1-8, optionally 9 | artifact-quality/observability result |

Goal 4 may move before Goal 3 if Goal 2 exposes action/artifact inconsistency
as the blocking failure layer.

## Goal 1. Harden The Live Action/Control Surface

Framework links:

- RQ4. Action-Object Reliability
- RQ1. Evidence Resume
- H6. Action-Object Contract Hardening
- F1. Transport And Schema Explicit Action Prompt
- F2. Row-Level Failure Attribution Everywhere
- targeted F5. Strict Policy/Continuation Validator

Intent:

Remove the known prompt/schema/transport confound before spending tokens on
live evidence-resume. The DeepSeek direct-endpoint transport test showed that
visible-content constraints improved primary strict scoring, but one row still
failed because `requested_context` was an object rather than the required
non-empty list. This goal should harden exactly that control surface.

Work items:

- Identify the model-facing action-object prompt or terminal surface used by
  live evidence/resume actions.
- Add visible-content constraints:
  - exactly one visible JSON object;
  - no markdown fence;
  - no duplicated object;
  - no prose before or after;
  - no reasoning-only answer.
- Add exact nested examples for:
  - `open_items[*].kind`;
  - `open_items[*].text`;
  - `schedule_requests[*].requested_context` as a non-empty list;
  - policy action fields used in the next evidence-resume panel.
- Generalize row-level failure attribution so failed rows identify model,
  prompt/schema, protocol/transport, provider, harness, substrate, scorer, or
  inconclusive layers.
- Add or update tests for the prompt/schema and attribution behavior.
- Preregister and run a small gate proving the selected positive anchor can
  produce interpretable control rows under the hardened surface.

Success criteria:

- At least two of three gate rows are primary strict-valid, or every failed row
  has a clear, actionable attribution layer.
- Primary strict scoring remains primary; secondary recovery remains an audit
  layer.
- The gate preserves raw request/response, attempts, strict evaluation,
  relaxed evaluation, recovery evaluation when attempted, and row attribution.
- The result artifact states whether the action/control surface is adequate
  for the live evidence-resume panel.

Recommended output paths:

- `experiments/event_loop/action_control_surface_gate_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/action_control_surface_gate_20260612/results.json`
- `experiments/event_loop/action_control_surface_gate_20260612/analysis.md`

Recommended validation:

- targeted tests for touched parser/prompt/scorer code;
- `uv run ruff check` on touched Python files;
- artifact audit verifying exactly three planned rows unless preregistration
  says otherwise.

Recommended goal-tool prompt:

```text
Harden the live model-authored action/control surface for upcoming evidence-resume experiments: add transport-explicit and schema-explicit action-object guidance, especially for nested requested_context lists and policy fields; generalize row-level failure attribution; preregister and run a three-row positive-anchor gate preserving primary strict scoring plus secondary recovery audit; write and commit the analysis stating whether the control surface is adequate for live evidence-resume.
```

## Goal 2. Build And Run Live Evidence-Resume Panel

Framework links:

- RQ1. Evidence Resume
- H1. Live Evidence Resume
- E1. Live Evidence-Resume Panel
- F3. Evidence-Resume Live Harness
- minimal F4. Evidence Boundary Scorers

Intent:

Test the event loop's core "I need evidence, call me back when it exists"
claim under live model conditions.

Work items:

- Preregister H1 and its falsification conditions.
- Build the live evidence-resume harness:
  - first wake records `ask_external_evidence`;
  - evidence request is append-only;
  - fulfillment is append-only;
  - resume event links to blocked wake, request, and fulfillment;
  - resumed wake receives evidence context through a visible terminal surface.
- Preserve wake envelopes, model outputs, action traces, policy dispositions,
  evidence request/fulfillment records, and scorer outputs.
- Score:
  - evidence use;
  - unsupported completion;
  - fossilized prior blocked state;
  - artifact/action consistency;
  - provider/protocol/harness/scorer attribution.

Success criteria:

- Three planned rows are run unless provider/substrate failure is
  preregistered as a stop condition.
- H1 is classified as survived, falsified, boundary, contaminated, or
  inconclusive.
- Each failed row has a layer attribution.
- The result states whether evidence-resume can be used as a foundation for
  partial/conflicting/multiple evidence stressors.

Recommended output paths:

- `experiments/event_loop/live_evidence_resume_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/live_evidence_resume_20260612/results.json`
- `experiments/event_loop/live_evidence_resume_20260612/analysis.md`

Recommended validation:

- tests for evidence request/fulfillment/resume linkage;
- tests for scorer distinctions between evidence use and policy action;
- artifact audit for one request, one fulfillment, and one resume event per
  completed row.

Recommended goal-tool prompt:

```text
Preregister, implement, and run the live evidence-resume panel: a live model must ask for missing evidence, the harness must record append-only evidence request and fulfillment records, then resume the model with linked evidence context. Preserve wake envelopes, action traces, strict/relaxed/recovery evaluations, policy dispositions, and scorer outputs; classify whether H1 survives, is falsified, is boundary/inconclusive, or is contaminated; write and commit the result artifact.
```

## Goal 3. Build Evidence-Boundary Scorers And Run Boundary Panel

Framework links:

- RQ2. Evidence Boundary Discipline
- H2. Partial Evidence Boundary
- H3. Conflicting Evidence Boundary
- H4. Multiple Evidence Requests
- E2. Evidence Boundary Stressor Panel
- F4. Evidence Boundary Scorers

Intent:

Move from clean fulfilled evidence to the evidence boundaries that matter for
epistemic discipline: partial evidence, conflict, and multiple open requests.

Work items:

- Preregister separate hypotheses and expected failure layers for partial,
  conflicting, and multiple-request rows.
- Add deterministic scorers for:
  - sufficient versus partial evidence;
  - unsupported completion;
  - conflict preservation;
  - request/fulfillment identity;
  - artifact/action consistency;
  - scorer confidence and lexical-fragility warnings.
- Run the positive-anchor panel first.
- Defer cross-model replication until the positive-anchor panel is
  interpretable.

Success criteria:

- Each stressor has a result classification.
- The analysis distinguishes evidence-content correctness from policy-action
  correctness.
- Multiple evidence requests remain addressable by request ID or the failure
  is clearly attributed.
- Scorer limitations are stated explicitly.

Recommended output paths:

- `experiments/event_loop/evidence_boundary_panel_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/evidence_boundary_panel_20260612/results.json`
- `experiments/event_loop/evidence_boundary_panel_20260612/analysis.md`

Recommended validation:

- scorer unit tests using positive and adversarial examples;
- artifact audit for request IDs and fulfillment IDs;
- rerun-free rescore command, if scorer repair is needed.

Recommended goal-tool prompt:

```text
Preregister and run the evidence-boundary panel for partial evidence, conflicting evidence, and multiple simultaneous evidence requests. Implement deterministic scorers that separately evaluate evidence content, policy action, request identity, unsupported completion, and scorer confidence. Preserve all raw traces and write an analysis classifying each stressor as survived, falsified, boundary, contaminated, or inconclusive.
```

## Goal 4. Tighten Policy Continuation Validation

Framework links:

- RQ3. Model-Owned Control Policy
- H5. Strict Continuation Validation
- F5. Strict Policy/Continuation Validator

Intent:

Close the known action/artifact mismatch where a model can choose
`continue_after` without a valid continuation request.

Work items:

- Patch terminal validation so `continue_after` is invalid unless a valid
  continuation request exists.
- Preserve the rejected first-pass output.
- Do not silently repair unless preregistered.
- Run a small probe against an action/artifact consistency condition.
- Compare interpretability against prior mismatch traces.

Success criteria:

- Invalid `continue_after` without continuation request is rejected or
  classified before acceptance.
- Rejection is logged as a first-class observation.
- The probe determines whether stricter validation improves trace quality or
  introduces a worse failure mode.

Recommended output paths:

- `experiments/event_loop/strict_continuation_validation_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/strict_continuation_validation_20260612/results.json`
- `experiments/event_loop/strict_continuation_validation_20260612/analysis.md`

Recommended validation:

- parser/validator tests for valid and invalid `continue_after`;
- replay/rescore of prior mismatch row if feasible;
- artifact audit proving rejected actions are preserved.

Recommended goal-tool prompt:

```text
Implement and preregister strict continuation validation: continue_after must be invalid unless the model also emits a valid continuation request. Preserve rejected first-pass outputs, run a small action/artifact consistency probe, and write an analysis deciding whether the stricter validator improves trace interpretability or creates a new failure mode.
```

## Goal 5. Build Audit-Grade Longer-Run Boundary

Framework links:

- RQ3. Model-Owned Control Policy
- RQ5. Working-Set Management
- F6. Audit-Grade Action Ledger And Restart Frontier
- `docs/autonomous-audit-restart-plan-20260609.md`

Intent:

Prepare for longer live autonomy runs where one-shot row artifacts are not
enough. The goal is reconstructability, not production hardening.

Work items:

- Ensure every model-authored action, accepted operation, rejected operation,
  scheduler event, memory operation, and policy disposition is logged.
- Verify hash-chain or tamper-evident ledger behavior.
- Define clean restart frontier boundaries for live runs.
- Generate replay/reconstruction reports answering:
  - what the model saw;
  - what it emitted;
  - what actions were accepted/rejected;
  - what changed in memory/event/ledger state;
  - why each wake happened;
  - where failures occurred.
- Record sandbox posture in run manifests.

Success criteria:

- A no-token or tiny-token rehearsal can be stopped and resumed from a clean
  frontier.
- Replay report can distinguish model, protocol, harness, substrate, provider,
  and scorer failures.
- Ledger verification detects tampering.
- The result states whether longer less-scaffolded panels can run safely.

Recommended output paths:

- `experiments/event_loop/audit_restart_boundary_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/audit_restart_boundary_20260612/results.json`
- `experiments/event_loop/audit_restart_boundary_20260612/analysis.md`

Recommended validation:

- unit tests for ledger verification and restart frontiers;
- rehearsal interruption/resume test;
- reconstruction report fixture test.

Recommended goal-tool prompt:

```text
Implement the audit-grade longer-run boundary required for less-scaffolded autonomy experiments: ensure model actions, accepted/rejected operations, scheduler events, memory operations, policy dispositions, run manifests, and restart frontiers are logged and reconstructable. Validate hash-chain/tamper detection, interruption/resume behavior, and replay reports, then write and commit the readiness analysis.
```

## Goal 6. Run Less-Scaffolded Bounded Investigation Panel

Framework links:

- RQ3. Model-Owned Control Policy
- RQ5. Working-Set Management
- H7. Model-Owned Bounded Investigation
- E4. Less-Scaffolded Bounded Investigation Panel
- F7. Goal Provenance Rubric

Intent:

Test whether the model can materially shape bounded work without the harness
quietly supplying the answer.

Work items:

- Define and preregister goal-provenance categories:
  - model-originated;
  - model-shaped;
  - menu-selected;
  - harness-authored.
- Use a bounded domain but avoid specifying the exact investigation target.
- Permit continue, stop, ask evidence, defer, and abandon.
- Score:
  - goal provenance;
  - control-action coherence;
  - evidence use;
  - continuation ownership;
  - declared losses;
  - artifact usefulness.

Success criteria:

- At least three rows are run or provider/substrate failure is clearly
  classified.
- The result states whether bounded investigation was model-shaped or merely
  harness-authored.
- Action/artifact consistency and restart frontier are reconstructable.

Recommended output paths:

- `experiments/event_loop/less_scaffolded_bounded_investigation_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/less_scaffolded_bounded_investigation_20260612/results.json`
- `experiments/event_loop/less_scaffolded_bounded_investigation_20260612/analysis.md`

Recommended validation:

- rubric tests or sample audits for goal-provenance scoring;
- artifact/action consistency tests;
- reconstruction report audit.

Recommended goal-tool prompt:

```text
Preregister and run a less-scaffolded bounded investigation panel. Define a goal-provenance rubric, provide a bounded domain without specifying the exact investigation target, permit continue/stop/ask-evidence/defer/abandon actions, preserve full audit and restart traces, and write an analysis classifying goal provenance, action coherence, evidence use, continuation ownership, declared losses, and artifact usefulness.
```

## Goal 7. Build Working-Set Accounting And Memory Substitute/Adapter

Framework links:

- RQ5. Working-Set Management
- H8. Working-Set Benefit
- F8. Working-Set And Context Accounting
- F9. Memory Substrate Adapter Or Bounded Substitute

Intent:

Prepare to test Hamut'ay's larger systems thesis: whether a transformer can
participate in its own working-set management.

Sharpening from Goal 6:

The less-scaffolded bounded-investigation panel survived, but two of three
positive rows naturally turned into evidence-blocked investigations. That is
not a reason to reorder the plan. It identifies the next confound: the model
can choose and control bounded work, but the substrate must make evidence
availability, recallability, omission, and working-set membership visible
enough that the next panel can distinguish "the model ignored evidence" from
"the needed evidence was not available to it."

Work items:

- Record per cycle:
  - live context injected;
  - state carried forward;
  - recall/evidence retrieved;
  - omitted context;
  - declared losses;
  - token counts.
- Decide whether to use Yanantin memory if ready or a bounded local substitute
  if not.
- Preserve recall provenance and truncation/omission metadata.
- Provide a bounded, inspectable corpus that the model can actually request
  from during event-loop work.
- Classify each model evidence request as:
  - answerable by the substrate;
  - unavailable but well-formed;
  - structurally impossible under the current substrate;
  - malformed or underspecified by the model.
- Distinguish at scoring time:
  - live prompt context;
  - recalled context;
  - carried state;
  - omitted context;
  - declared losses;
  - unavailable evidence.
- Add deterministic recovery/contamination metrics.

Success criteria:

- A dry-run can report what was in context, what was recalled, what was lost,
  and what was omitted.
- A dry-run can report whether model-authored evidence requests were
  answerable by the configured memory substrate.
- The system can compare event-loop working-set behavior against direct
  one-shot and harness-summary controls.
- Memory substrate limitations are explicit.
- The readiness analysis states whether remaining failures would be charged to
  model behavior, prompt/schema, memory substrate coverage, recall protocol,
  scorer, or inconclusive layer.

Recommended output paths:

- `experiments/event_loop/working_set_accounting_gate_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/working_set_accounting_gate_20260612/results.json`
- `experiments/event_loop/working_set_accounting_gate_20260612/analysis.md`

Recommended validation:

- context accounting tests;
- recall provenance tests;
- evidence-request answerability tests;
- contamination/recovery scorer tests.

Recommended goal-tool prompt:

```text
Build the working-set accounting gate for Hamut'ay event-loop experiments: record live context, carried state, recalled/evidence context, omitted context, declared losses, token counts, recall provenance, and truncation metadata; choose Yanantin memory or a bounded local substitute; provide a bounded inspectable corpus; classify model-authored evidence requests as answerable, unavailable, structurally impossible, or malformed; add recovery/contamination metrics; and write a readiness analysis for the matched working-set panel that separates model behavior from substrate, recall-protocol, prompt/schema, scorer, and inconclusive failures.
```

## Goal 8. Run Working-Set Management Matched Panel

Framework links:

- RQ5. Working-Set Management
- RQ7. Artifact Quality Non-Inferiority
- H8. Working-Set Benefit
- E5. Working-Set Management Matched Panel

Intent:

Compare model-managed event-loop working-set behavior with harness-summary and
direct one-shot controls.

Work items:

- Preregister matched tasks that exceed trivial identity-only carry-forward.
- Run conditions:
  - event-loop model-controlled working set;
  - harness-selected summary;
  - direct one-shot control.
- Score:
  - recovery;
  - contamination;
  - declared losses;
  - artifact usefulness;
  - context/token use;
  - evidence provenance.

Success criteria:

- The analysis states whether event-loop working-set behavior is better,
  worse, non-inferior, or inconclusive relative to controls.
- The result separates working-set benefit from artifact quality.
- The result identifies whether memory substrate limitations dominated.

Recommended output paths:

- `experiments/event_loop/working_set_matched_panel_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/working_set_matched_panel_20260612/results.json`
- `experiments/event_loop/working_set_matched_panel_20260612/analysis.md`

Recommended validation:

- scorer tests against adversarial contamination examples;
- context accounting audit;
- blinded artifact review if used.

Recommended goal-tool prompt:

```text
Preregister and run a matched working-set management panel comparing event-loop model-controlled working set, harness-selected summary, and direct one-shot controls on tasks that exceed trivial carry-forward. Preserve context accounting, recall provenance, declared losses, recovery/contamination scores, artifact usefulness, and token use; write and commit an analysis classifying working-set benefit separately from artifact quality.
```

Completed result:

- Result artifact:
  `experiments/event_loop/working_set_matched_panel_20260612/analysis.md`
- Corrected live-panel classification: falsified.
- The event-loop condition recovered all required facts, but had worse
  working-set score and worse artifact-quality score than the best control.
- The primary failure was not evidence absence: the model-controlled working
  set recalled the needed records, then failed to preserve declared-loss
  discipline and carried contaminating material into the artifact.
- The initial live run was archived as an aborted run because it exposed two
  harness/scorer defects. Those defects were fixed before the corrected run,
  and the aborted run is not treated as the panel result.

Sharpening from Goal 8:

Goal 8 falsifies the simple hypothesis that model-managed event-loop working
sets already outperform or match harness-selected summary/direct one-shot
controls on this task shape. It does not falsify the broader systems thesis
that a bounded-context transformer can participate in working-set management.
Instead, it sharpens the next confound: once recall is available, the model
must still distinguish relevant evidence, declared losses, and contaminating
material while producing a useful artifact.

This result argues against treating memory access alone as the next milestone.
The next substantive research question should separate artifact quality from
observability: even if event-loop work is not yet superior as a working-set
compression strategy, it may still produce enough auditability, reconstruction,
and failure attribution to justify the control-loop form.

## Goal 9. Add Wall-Clock Adapter Only If Needed

Framework links:

- RQ6. DES Versus Real Clock
- H9. DES Non-Inferiority For Semantic Scheduler Tests
- E6. DES Versus Wall-Clock Boundary Probe
- F10. ClockPort And Wall-Clock Adapter

Intent:

Add real-clock scheduling only when it answers a research question that DES
cannot answer.

Work items:

- Define `ClockPort` or equivalent scheduler clock boundary if not already
  explicit.
- Keep deterministic `SchedulerClock` as the semantic baseline.
- Add wall-clock adapter.
- Run paired DES and wall-clock smoke tests for:
  - due ordering;
  - expiration;
  - next wake reporting;
  - restart frontier behavior.
- Classify differences as semantic scheduler failure or runtime availability
  failure.

Success criteria:

- DES tests remain the semantic contract.
- Wall-clock behavior is tested without weakening deterministic replay.
- The analysis states whether any research claim now requires wall-clock
  execution.

Recommended output paths:

- `experiments/event_loop/des_wall_clock_boundary_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/des_wall_clock_boundary_20260612/results.json`
- `experiments/event_loop/des_wall_clock_boundary_20260612/analysis.md`

Recommended validation:

- unit tests for both clocks;
- deterministic replay tests;
- wall-clock smoke test with bounded duration.

Recommended goal-tool prompt:

```text
Add a wall-clock scheduler adapter only as a DES boundary probe: define the clock abstraction, preserve deterministic SchedulerClock semantics, implement a wall-clock adapter, run paired DES and wall-clock smoke tests for due ordering, expiration, next-wake reporting, and restart frontier behavior, then write an analysis separating semantic scheduler failures from runtime availability failures.
```

Completed result:

- Result artifact:
  `experiments/event_loop/des_wall_clock_boundary_20260612/analysis.md`
- Classification: passed.
- `SchedulerClock` remains the deterministic semantic baseline.
- `ClockPort` and `WallClock` now provide a narrow runtime clock boundary for
  scheduler probes.
- Paired DES and wall-clock smoke tests passed for due ordering, expiration,
  next-wake reporting, and restart frontier recovery.
- No semantic scheduler failures or runtime availability failures were
  observed.

Sharpening from Goal 9:

Wall-clock access is now available as a bounded adapter, but no current
research claim requires wall-clock execution. The DES scheduler remains the
right substrate for semantic scheduler experiments unless a future task depends
on real elapsed time, external deadlines, sleeping/waking across process time,
or wall-clock availability failures.

## Goal 10. Run Artifact Non-Inferiority Panel

Framework links:

- RQ7. Artifact Quality Non-Inferiority
- H10. Artifact Non-Inferiority With Observability Gain
- E7. Artifact Non-Inferiority Panel

Intent:

Determine whether event-loop bounded work can be artifact-quality
non-inferior to direct one-shot work while preserving stronger observability.

Work items:

- Preregister matched tasks and a non-inferiority margin.
- Define direct one-shot and event-loop conditions.
- Use blinded artifact judging if feasible.
- Preserve deterministic observability scoring.
- Separate artifact quality from trace/observability quality.

Success criteria:

- The result states whether artifact non-inferiority survives, fails, or is
  inconclusive.
- Observability gain is measured separately from artifact quality.
- Judge/scorer disagreements are reported as method findings, not hidden.

Recommended output paths:

- `experiments/event_loop/artifact_noninferiority_20260612/PRE_REGISTRATION.md`
- `experiments/event_loop/artifact_noninferiority_20260612/results.json`
- `experiments/event_loop/artifact_noninferiority_20260612/analysis.md`

Recommended validation:

- judge rubric preregistration;
- deterministic trace scorer tests;
- blinded review packet audit.

Recommended goal-tool prompt:

```text
Preregister and run an artifact non-inferiority panel comparing event-loop bounded work against direct one-shot work. Define matched tasks, a non-inferiority margin, artifact-quality judging, and deterministic observability scoring; preserve all traces and judge/scorer disagreements; write and commit an analysis stating whether artifact quality is non-inferior and whether observability is stronger.
```

## Current Recommended Next Goal

Use Goal 10 next.

Rationale:

- Goals 7 and 8 have now exercised the working-set accounting path.
- Goal 8 did not show a working-set advantage for the model-managed event-loop
  condition; it showed recoverable evidence access paired with contamination
  and weak declared-loss discipline.
- That result does not require wall-clock scheduling to interpret. The failure
  occurred inside evidence handling, carried-state discipline, and artifact
  construction, not in simulated-time ordering.
- The next useful question is therefore not "does a real clock work?" but
  whether the event-loop form can be non-inferior on artifact quality while
  offering stronger observability and reconstruction than direct controls.
- Goal 9 has now supplied the wall-clock boundary probe and did not identify a
  reason to move semantic scheduler experiments off DES.

Copy-ready prompt:

```text
Preregister and run an artifact non-inferiority panel comparing event-loop bounded work against direct one-shot work. Define matched tasks, a non-inferiority margin, artifact-quality judging, and deterministic observability scoring; preserve all traces and judge/scorer disagreements; write and commit an analysis stating whether artifact quality is non-inferior and whether observability is stronger. Treat Goal 8's corrected falsification as prior evidence: memory access alone is not sufficient, and scoring must separately classify evidence recovery, contamination, declared-loss discipline, artifact quality, and audit/reconstruction value.
```
