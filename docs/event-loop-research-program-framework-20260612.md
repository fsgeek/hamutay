# Hamut'ay Event-Loop Research Program Framework

Date: 2026-06-12

Purpose: define the next research program for Hamut'ay's event-loop work before
turning it into an execution roadmap. This document identifies the next core
research questions, preregisterable hypotheses, falsification experiments,
required framework changes, and a cost/benefit priority model for sequencing
the work.

This is a research framework, not an implementation ticket list. A later
document should convert it into goal-tool prompts and ordered work items.

## Current Evidence Baseline

The current evidence supports a narrowed but useful claim:

> A bounded, observable event loop can carry model-authored work across
> discontinuous cycles when the substrate validates context, uses explicit
> terminal surfaces for load-bearing outputs, records repairs, and separates
> lifecycle from policy disposition.

Primary evidence:

- `docs/event-loop-research-retrospective-20260605.md`
- `docs/bounded-autonomous-work-stocktake-20260605.md`
- `docs/autonomous-audit-restart-plan-20260609.md`
- `experiments/action_object_contract_salience_cross_model_20260611/recovery_aware_causal_attribution_20260611.md`
- `experiments/action_object_contract_salience_cross_model_20260611/deepseek_transport_falsification_20260611/live_direct_deepseek_20260611/analysis.md`

What appears settled enough to build on:

1. The deterministic scheduler can serve as a semantic contract for event-loop
   behavior.
2. Simulated time is useful because it separates clock mechanics from loop
   mechanics.
3. Event lifecycle and policy disposition must remain separate.
4. Evidence requests, fulfillments, and resume events can be represented as
   append-only sidecar records.
5. Terminal surfaces are stronger than broad `think_and_respond` for bounded
   scheduled wakes.
6. First-pass failures, rejected actions, repairs, and scorer defects are
   research data and must be preserved.
7. Action-object failures are often prompt/schema/transport salience failures,
   not simple model incapability.
8. Provider/protocol behavior can fully mask model behavior and must be a
   first-class attribution layer.

What is not settled:

1. Whether a live model reliably uses fulfilled evidence on resumed wakes.
2. Whether partial, conflicting, and multiple evidence requests remain
   distinguishable under live model use.
3. Whether a less-scaffolded model can choose useful bounded investigations
   without the harness quietly supplying the shape of the work.
4. Whether the event loop is artifact-quality non-inferior to direct one-shot
   work while preserving superior observability.
5. Whether real elapsed time adds research-relevant behavior beyond the
   deterministic scheduler semantics.
6. Whether a production-adjacent memory substrate is needed before further
   autonomy experiments, or whether local bounded evidence fixtures are enough
   for the next falsification slice.

## Research Program Principle

Every framework change should be justified by a falsification experiment it
enables. The project should avoid building infrastructure merely because it is
architecturally attractive.

The immediate research goal is not broad capability proof. It is map-making:
identify which claims survive adversarial tests, which claims collapse, and
which failures belong to model behavior, prompt/schema design, protocol
transport, scheduler mechanics, memory substrate, provider availability, or
scorer/harness error.

## Core Research Questions

### RQ1. Evidence Resume

Can a live model use fulfilled evidence on resume to complete, revise, or keep
open a previously evidence-blocked task?

Why this matters:

- The deterministic substrate can create evidence requests, fulfillments, and
  resume events.
- The current open question is whether live model cognition honors that
  evidence rather than fossilizing the blocked state.
- This is central to bounded autonomy because "I need evidence, call me back"
  is one of the main reasons to have an event loop.

### RQ2. Evidence Boundary Discipline

Can the loop and model preserve distinctions among sufficient evidence,
partial evidence, conflicting evidence, missing evidence, and multiple
simultaneous evidence requests?

Why this matters:

- The Step 6 stressors passed under the DeepSeek positive anchor.
- Generalization is not established.
- If the system collapses partial or conflicting evidence into premature
  completion, later autonomy experiments will be uninterpretable.

### RQ3. Model-Owned Control Policy

Can a model choose coherent control actions across `continue_after`,
`stop_complete`, `ask_external_evidence`, `defer`, `abandon`, and bounded
self-directed investigation without the harness scripting the answer?

Why this matters:

- Previous panels showed scaffolded policy selection can work.
- Action/artifact mismatches remain a recurring live boundary.
- Bounded autonomy requires policy choices to be model-authored and observable,
  not harness-inferred.

### RQ4. Action-Object Reliability

What minimum prompt/schema/transport contract makes model-authored control
actions reliable enough for live event-loop experiments?

Why this matters:

- The DeepSeek direct-endpoint transport test showed explicit visible-content
  constraints rescued primary strict scoring from `1/3` to `2/3`.
- One transport-explicit failure remained: `requested_context` was an object
  instead of the required non-empty list.
- The next autonomy runs should not depend on a known brittle control surface.

### RQ5. Working-Set Management

Can a bounded-context transformer use the event loop, state object, and memory
substrate to manage its own working set better than externally imposed
compaction or harness-selected continuation?

Why this matters:

- Hamut'ay's larger systems question is whether the transformer can participate
  in its own working-set management.
- The event loop is valuable if it makes evidence requests, recall binding,
  continuation ownership, and loss declaration observable.
- This question should be tested without requiring the identity object to serve
  as the whole memory system.

### RQ6. DES Versus Real Clock

When does real elapsed time matter beyond deterministic simulated time?

Why this matters:

- The current scheduler is a DES/logical-time scaffold.
- Real clocks introduce provider latency, uptime, wall-time deadlines,
  supervision, and restart hazards.
- A real clock should be added when an experiment needs those properties, not
  merely because a production scheduler would eventually need one.

### RQ7. Artifact Quality Non-Inferiority

Can event-loop bounded work be artifact-quality non-inferior to direct one-shot
work while producing stronger observability?

Why this matters:

- Prior controls show coherent artifacts do not require the event loop.
- The supported distinction is currently observability and control-loop trace,
  not artifact superiority.
- Non-inferiority is a reasonable threshold before claiming the event loop is a
  useful work substrate rather than only a measurement apparatus.

## Preregisterable Hypotheses

The hypotheses below are written so each can be attacked independently.

### H1. Live Evidence Resume

Hypothesis:

> A live model resumed with fulfilled evidence will use that evidence in the
> resumed artifact and policy disposition in at least two of three clean
> evidence-resume rows.

Falsification conditions:

- The model ignores fulfilled evidence.
- The model claims completion without using the evidence.
- The model fossilizes the prior blocked state.
- The artifact uses evidence but the policy action remains incoherent.
- Provider/protocol failure prevents at least two rows from preserving
  model-authored resumed output.

Required framework support:

- live evidence request/resume harness;
- terminal surface for resumed evidence use;
- row-level attribution for evidence content versus policy action;
- preserved evidence request, fulfillment, resume event, and wake artifacts.

### H2. Partial Evidence Boundary

Hypothesis:

> Under partial evidence, a live model will resolve only the bounded subclaim
> supported by the evidence and keep unsupported claims open in at least two of
> three rows.

Falsification conditions:

- Unsupported completion is counted or emitted as complete.
- Partial evidence is treated as sufficient for all open claims.
- The artifact preserves uncertainty but the policy action closes the work.
- The scorer cannot distinguish subclaim completion from global completion.

Required framework support:

- claim/subclaim representation in evidence fixtures;
- action/artifact consistency scorer;
- open-item closure targets with exact handles;
- declared-loss or uncertainty fields.

### H3. Conflicting Evidence Boundary

Hypothesis:

> Under conflicting evidence, a live model will preserve conflict visibility and
> choose a coherent policy action: request adjudication, defer, or stop with
> declared unresolved conflict in at least two of three rows.

Falsification conditions:

- Conflict is collapsed into a clean claim.
- One side is selected without warrant.
- The artifact mentions conflict but the policy action claims clean completion.
- The model requests continuation without a valid continuation request.

Required framework support:

- first-class conflict evidence fixtures;
- policy vocabulary including `defer` or adjudication request;
- validator rule for `continue_after` requiring a valid continuation request;
- row-level attribution separating evidence handling from policy coherence.

### H4. Multiple Evidence Requests

Hypothesis:

> When two independent evidence requests are open, fulfillments remain
> addressable by request identity and the resumed model does not conflate them
> in at least two of three rows.

Falsification conditions:

- Fulfillment for one request closes the wrong item.
- The model merges distinct requests into one claim.
- The resume event does not preserve request/fulfillment linkage.
- The scorer cannot determine which evidence request was used.

Required framework support:

- stable evidence request IDs;
- resume events linked to exact request and fulfillment records;
- artifact scorer keyed by request identity;
- operation log showing what was bound into the wake envelope.

### H5. Strict Continuation Validation

Hypothesis:

> Making `continue_after` invalid unless a valid continuation request is present
> improves trace interpretability without hiding useful model-boundary behavior.

Falsification conditions:

- Stricter validation causes repair loops.
- The same incoherence appears through a different field.
- Useful policy preference becomes unobservable.
- Rows become less interpretable than under post-hoc mismatch scoring.

Required framework support:

- terminal-surface validator patch;
- preserved rejected first-pass action object;
- repair-off default or explicitly preregistered repair path;
- comparison against previous action/artifact mismatch traces.

### H6. Action-Object Contract Hardening

Hypothesis:

> A transport-explicit, schema-explicit action-object prompt plus a closed
> terminal surface yields primary strict-valid model-authored control actions
> in at least two of three rows for the selected positive-anchor model.

Falsification conditions:

- Visible transport failures persist.
- Required nested shapes remain unstable.
- Secondary recovery finds valid objects but primary strict scoring fails.
- Provider/protocol failure prevents scoreable rows.

Required framework support:

- updated terminal prompt with visible-content constraints;
- explicit example for nested `requested_context` as a list;
- primary strict scoring plus secondary recovery audit;
- provider/protocol attribution layer.

### H7. Model-Owned Bounded Investigation

Hypothesis:

> With a bounded domain and explicit action vocabulary, a model can choose or
> materially shape a useful bounded investigation, schedule at least one
> continuation or evidence request, and produce an action/artifact-consistent
> result in at least two of three rows.

Falsification conditions:

- The model merely selects from harness-authored options.
- Goal provenance is not separable from prompt framing.
- The model produces coherent prose but invalid control actions.
- The continuation/evidence action is harness-inferred rather than
  model-authored.

Required framework support:

- goal-provenance rubric;
- less-scaffolded prompt variants;
- action ledger recording raw control object and accepted/rejected actions;
- bounded sandbox and run manifest.

### H8. Working-Set Benefit

Hypothesis:

> A model-controlled event-loop working-set condition preserves task-relevant
> evidence and declared uncertainty at least as well as harness-selected summary
> or direct one-shot controls while using less live context.

Falsification conditions:

- Event-loop state loses key evidence.
- Harness-selected summary outperforms model-controlled working-set selection
  on recovery and contamination.
- Context savings come at unacceptable contamination or artifact-quality loss.
- The scorer cannot distinguish remembered evidence from reintroduced prompt
  evidence.

Required framework support:

- matched controls;
- context accounting;
- evidence recovery and contamination scorer;
- memory/recall substrate or bounded local substitute;
- declared-loss tracking.

### H9. DES Non-Inferiority For Semantic Scheduler Tests

Hypothesis:

> DES/logical-time scheduler tests are sufficient for semantic correctness
> claims about event ordering, lifecycle transitions, context binding, and
> restart frontiers.

Falsification conditions:

- A semantic scheduler bug appears only under wall-clock execution.
- Logical-time tests cannot model deadline, expiration, or retry behavior
  relevant to the research question.
- Restart behavior depends on wall-clock time in ways DES does not cover.

Required framework support:

- explicit ClockPort abstraction or equivalent wall-clock adapter;
- paired DES and wall-clock smoke tests;
- clear separation between semantic failures and runtime availability failures.

### H10. Artifact Non-Inferiority With Observability Gain

Hypothesis:

> Event-loop bounded work is artifact-quality non-inferior to direct one-shot
> work while producing strictly stronger observability traces.

Falsification conditions:

- Event-loop artifacts fall below the preregistered non-inferiority margin.
- Observability improves but artifact quality degrades materially.
- Direct one-shot controls preserve enough trace to erase the observability
  distinction.
- Judge and deterministic scorer disagree in a way that invalidates the rubric.

Required framework support:

- matched task set;
- blinded artifact-quality judge;
- deterministic trace scorer;
- preregistered non-inferiority margin;
- action/log completeness checks.

## Falsification Experiment Set

The immediate program should prefer narrow experiments with high attribution
power over broad sweeps.

### E1. Live Evidence-Resume Panel

Tests: H1.

Design:

- model: current positive-anchor direct endpoint;
- rows: `n=3`;
- task: first wake asks for external evidence; fulfillment is injected as an
  append-only record; resume event wakes with evidence context;
- terminal surface: evidence-use completion surface;
- scoring: evidence used, artifact/action coherence, open/closed item status,
  unsupported completion.

Primary outputs:

- preregistration;
- run manifest;
- row-level action and evidence traces;
- analysis with model/protocol/harness/scorer attribution.

Why first:

- This is the smallest live test of the event loop's core value proposition.
- It directly follows the deterministic evidence-resume substrate.

### E2. Evidence Boundary Stressor Panel

Tests: H2, H3, H4.

Design:

- rows: partial evidence, conflicting evidence, two independent evidence
  requests;
- model: positive anchor first;
- optionally replicate one stressor on a second model only after the positive
  anchor is interpretable;
- scoring: evidence content, policy action, action/artifact consistency,
  request identity preservation.

Why second:

- It generalizes the clean evidence-resume path to the boundaries that matter
  for epistemic discipline.

### E3. Strict Control-Action Validation Patch And Probe

Tests: H5 and H6.

Design:

- patch terminal validation so `continue_after` requires a valid continuation
  request;
- add transport/schema explicit examples for nested control shapes;
- rerun a tiny action/artifact consistency panel;
- preserve rejected first-pass objects and no-repair traces.

Why third:

- It reduces known action-object/control-surface brittleness before more
  expensive autonomy panels.

### E4. Less-Scaffolded Bounded Investigation Panel

Tests: H7.

Design:

- bounded domain supplied, but model materially shapes investigation target;
- rows: `n=3`;
- permitted actions: continue, stop, ask evidence, defer, abandon;
- scoring: goal provenance, control-action coherence, evidence requests,
  artifact quality, declared losses.

Why fourth:

- It tests bounded autonomy after the evidence and action-surface foundations
  are less confounded.

### E5. Working-Set Management Matched Panel

Tests: H8.

Design:

- compare event-loop model-controlled working set, harness-selected summary,
  and direct one-shot control;
- tasks must exceed trivial identity-only carry-forward;
- score evidence recovery, contamination, declared losses, artifact quality,
  and context use.

Why fifth:

- It connects the event-loop work back to Hamut'ay's larger systems thesis:
  transformer-managed working-set control.

### E6. DES Versus Wall-Clock Boundary Probe

Tests: H9.

Design:

- implement a wall-clock adapter only after an experiment needs it;
- run paired DES and wall-clock smoke tests for the same event ordering and
  expiration semantics;
- classify differences as semantic scheduler failures or runtime availability
  failures.

Why later:

- Real clocks add operational confounds. The current research program still
  has semantic questions that DES can answer more cleanly.

### E7. Artifact Non-Inferiority Panel

Tests: H10.

Design:

- matched tasks;
- direct one-shot versus event-loop treatment;
- blinded judge plus deterministic observability scorer;
- preregistered margin.

Why later:

- Non-inferiority is important for eventual claims, but it is premature until
  evidence handling and action-surface reliability are less confounded.

## Required Framework Changes

### F1. Transport And Schema Explicit Action Prompt

Description:

- Update the model-facing action-object prompt or terminal surface to include
  visible-content constraints and exact nested examples, especially
  `requested_context` as a non-empty list.

Enables:

- H1 through H7.

Risk if skipped:

- Live failures remain hard to attribute because prompt/transport salience is a
  known confound.

### F2. Row-Level Failure Attribution Everywhere

Description:

- Generalize the recent action-contract attribution pattern so each failed row
  records likely layer: model, prompt/schema, transport/protocol, provider,
  harness, substrate, scorer, or inconclusive.

Enables:

- all live panels.

Risk if skipped:

- Negative results will collapse into "failed" without explaining what failed.

### F3. Evidence-Resume Live Harness

Description:

- Turn the deterministic evidence request, fulfillment, and resume path into a
  live model panel with preserved wake envelopes and terminal-surface outputs.

Enables:

- H1, H2, H3, H4.

Risk if skipped:

- The event-loop program cannot test its core "call me back when evidence
  exists" claim.

### F4. Evidence Boundary Scorers

Description:

- Add deterministic scorers for evidence use, partial evidence, conflicting
  evidence, request identity, unsupported completion, and action/artifact
  mismatch.

Enables:

- H1, H2, H3, H4, H10.

Risk if skipped:

- Scorer lexical fragility will likely reappear.

### F5. Strict Policy/Continuation Validator

Description:

- Reject or classify `continue_after` as invalid unless a valid continuation
  request is present.

Enables:

- H3, H5, H7.

Risk if skipped:

- Known action/artifact mismatch remains accepted and must be repaired by
  post-hoc scoring.

### F6. Audit-Grade Action Ledger And Restart Frontier

Description:

- Continue the action ledger/restart work from
  `docs/autonomous-audit-restart-plan-20260609.md`: append-only hash-chained
  action records, exact operation logs, run manifests, replay reports, and
  clean restart boundaries.

Enables:

- H7, H8, H10, and any longer live autonomy run.

Risk if skipped:

- Live autonomy runs cannot be reconstructed well enough to classify failures.

### F7. Goal Provenance Rubric

Description:

- Define how to distinguish model-originated, model-shaped, menu-selected, and
  harness-authored goals.

Enables:

- H7.

Risk if skipped:

- Less-scaffolded autonomy becomes a vibe rather than a measured variable.

### F8. Working-Set And Context Accounting

Description:

- Record what entered live context, what was carried in state, what was
  recalled, what was omitted, what was declared lost, and how many tokens each
  condition used.

Enables:

- H8, H10.

Risk if skipped:

- The project cannot support its systems framing around transformer-managed
  working sets.

### F9. Memory Substrate Adapter Or Bounded Substitute

Description:

- Either integrate the Yanantin memory substrate when ready, or define a
  bounded local evidence/recall substrate sufficient for the next panels.

Enables:

- H8 and later long-horizon tests.

Risk if skipped:

- Experiments may keep testing toy recall rather than memory-assisted
  working-set management.

### F10. ClockPort And Wall-Clock Adapter

Description:

- Introduce a clock abstraction if not already present at the scheduler API
  boundary, then implement a wall-clock adapter and paired DES/wall-clock smoke
  tests.

Enables:

- H9 and future production-adjacent scheduling.

Risk if skipped:

- The project remains limited to semantic DES claims and cannot test elapsed
  time behavior.

## Cost/Benefit Priority Model

Prioritize changes by research leverage, not architectural appeal.

Score each candidate change on five dimensions, each 1 to 5:

- **Question leverage:** how many core research questions it can answer.
- **Confound removal:** how much it reduces known attribution ambiguity.
- **Evidence quality:** how much it improves observability or replay.
- **Implementation cost:** inverse score; 5 means low cost, 1 means high cost.
- **Delay risk:** 5 means delaying it will likely contaminate near-term
  experiments, 1 means it can wait.

Suggested priority score:

```text
priority = question_leverage + confound_removal + evidence_quality
           + implementation_cost + delay_risk
```

This is not a final task order. It is a transparent heuristic for deciding what
to build before each experimental phase.

## Initial Priority Ranking

| Rank | Change | Benefit | Cost | Rationale |
| ---: | --- | --- | --- | --- |
| 1 | F1. Transport and schema explicit action prompt | Very high | Low | Removes a known live confound exposed by the DeepSeek transport test. |
| 2 | F2. Row-level failure attribution everywhere | Very high | Low-medium | Prevents future negative rows from collapsing model, prompt, provider, protocol, and scorer failures. |
| 3 | F3. Evidence-resume live harness | Very high | Medium | Directly tests the event loop's core evidence-callback value. |
| 4 | F4. Evidence boundary scorers | High | Medium | Needed before partial/conflicting/multiple evidence tests can be trusted. |
| 5 | F5. Strict policy/continuation validator | High | Low-medium | Attacks a known action/artifact inconsistency boundary. |
| 6 | F6. Audit-grade action ledger and restart frontier | Very high | Medium-high | Required for longer live autonomy runs, but not every one-cycle evidence panel. |
| 7 | F7. Goal provenance rubric | Medium-high | Medium | Needed before less-scaffolded autonomy claims. |
| 8 | F8. Working-set and context accounting | High | Medium | Required for the larger systems thesis, but after evidence handling is stable. |
| 9 | F9. Memory substrate adapter or bounded substitute | High | High | Important, but can be staged with a bounded substitute for near-term evidence panels. |
| 10 | F10. ClockPort and wall-clock adapter | Medium | Medium | Necessary eventually, but DES remains the cleaner semantic testbed now. |

## Recommended Research Sequence

### Stage 1. Stabilize The Live Control Surface

Questions served:

- RQ1, RQ3, RQ4.

Build:

- F1, F2, targeted part of F5.

Then run:

- a small action-object/control-surface gate proving the selected positive
  anchor can emit strict-valid evidence-resume actions under the hardened
  prompt.

Exit criterion:

- at least two of three rows strict-valid, or failures clearly attributed to a
  layer that can be attacked before evidence-resume.

### Stage 2. Test Live Evidence Resume

Questions served:

- RQ1.

Build:

- F3 and the minimum scoring subset of F4.

Then run:

- E1. Live Evidence-Resume Panel.

Exit criterion:

- either H1 survives under the positive anchor, or the failure layer is clear
  enough to decide whether to repair prompt, terminal surface, scorer, or
  substrate.

### Stage 3. Test Evidence Boundary Discipline

Questions served:

- RQ2.

Build:

- full F4 and remaining F5.

Then run:

- E2. Evidence Boundary Stressor Panel.

Exit criterion:

- partial, conflicting, and multiple-evidence rows are classified by content,
  policy action, request identity, and scorer confidence.

### Stage 4. Test Less-Scaffolded Bounded Investigation

Questions served:

- RQ3, RQ5.

Build:

- F6 and F7.

Then run:

- E4. Less-Scaffolded Bounded Investigation Panel.

Exit criterion:

- goal provenance, action coherence, evidence use, continuation ownership, and
  restart frontier are reconstructable from artifacts.

### Stage 5. Test Working-Set Management

Questions served:

- RQ5, RQ7.

Build:

- F8 and either F9 or a bounded local substitute.

Then run:

- E5. Working-Set Management Matched Panel.

Exit criterion:

- event-loop working-set behavior can be compared against direct one-shot and
  harness-summary controls on recovery, contamination, context use, and
  artifact quality.

### Stage 6. Add Real Clock Only When It Answers A Question

Questions served:

- RQ6.

Build:

- F10.

Then run:

- E6. DES Versus Wall-Clock Boundary Probe.

Exit criterion:

- a documented boundary between semantic scheduler correctness and real-time
  runtime behavior.

### Stage 7. Artifact Non-Inferiority

Questions served:

- RQ7.

Build:

- any missing judge/scorer support from F4, F6, and F8.

Then run:

- E7. Artifact Non-Inferiority Panel.

Exit criterion:

- a supported statement about whether event-loop bounded work is
  artifact-quality non-inferior to direct one-shot work while preserving
  stronger observability.

## Immediate Next Decision

The next actionable document should convert this framework into an ordered
goal sequence. It should include:

- one goal-tool prompt per stage;
- exact files likely to change;
- preregistration artifact paths;
- completion criteria;
- validation commands;
- stop conditions that prevent broadening the experiment after the result is
  known.

Recommended next artifact:

`docs/event-loop-research-program-goals-20260612.md`

