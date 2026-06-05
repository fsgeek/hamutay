# Bounded Autonomous Work Research Todo

Filed: 2026-06-05.

## Goal

Answer the bounded autonomous work question with preregistered, empirically
grounded experiments:

> Can a transformer instance, given a bounded observable event loop, choose and
> execute its own limited investigation across discontinuous cycles, produce a
> useful artifact, and decide whether to stop, continue, or request evidence?

This is the next research arm after the event-loop retrospective. Evidence
resume, policy dispositions, terminal surfaces, validation/repair, simulated
time, and continuation budgets are support mechanisms. The research target is
bounded autonomous work.

## Working Definition

Bounded autonomous work requires all of the following:

1. the instance chooses or materially shapes a bounded investigation;
2. the instance emits valid scheduled work rather than only responding in the
   current turn;
3. later wakes use prior self-authored context, recalled records, or supplied
   evidence;
4. the work produces a concrete inspectable artifact;
5. the instance makes an observable control decision: stop, continue, request
   evidence, or explicitly defer/abandon;
6. the trace preserves context, omissions, repairs, validation failures, and
   policy dispositions.

## Research Sequence

### Step 1: Operational Definition And Scoring

Status: complete.

Deliverable:

- preregistered rubric for bounded autonomous work:
  `docs/bounded-autonomous-work-rubric-20260605.md`.

Evidence needed:

- explicit success/failure criteria for artifact quality and control-loop
  behavior;
- independent scoring of:
  - declared policy action;
  - produced artifact;
  - consistency between declared action and artifact;
- distinct failure category for action/artifact mismatch, not merely a score
  deduction;
- distinction between first-pass model competence and scaffolded repair;
- definition of what counts as model-owned goal selection versus harness-set
  work;
- goal-provenance measure: what parts of the chosen investigation are directly
  traceable to harness framing, selected from a harness menu, or newly
  introduced/materially shaped by the model.

Rationale:

- Prior scorer work showed that a preregistered deterministic rubric can still
  encode the wrong distinction. The bounded-autonomy rubric must not score a
  policy action in isolation. A model that emits `ask_external_evidence` while
  fabricating an answer in the artifact, or emits `stop_complete` while leaving
  the artifact visibly unfinished, has produced a control/artifact mismatch.
  That mismatch is itself a primary endpoint.

### Step 2: Minimal Harness

Status: complete.

Deliverable:

- small live runner that lets the model choose a bounded investigation and
  emit one of the scheduler policy actions through a terminal surface:
  `experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/run_bounded_autonomous_work_minimal_harness.py`.

Evidence needed:

- valid event persistence;
- no harness-imposed continuation answer;
- captured policy disposition;
- bounded continuation budget;
- artifact submission surface.

### Step 3: Scaffolded Positive-Control Panel

Status: complete.

Purpose:

- determine whether the full pattern can execute when the task class and
  affordances are explicit.

Deliverable:

- live scaffolded positive-control panel:
  `experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/`.

Evidence needed:

- at least one completed autonomous-work chain;
- generated artifact;
- final stop/continue/evidence decision;
- action/artifact consistency score;
- goal-provenance score;
- validation and repair provenance;
- comparison against preregistered criteria.

### Step 3a: Evidence-Honoring Gate

Status: complete.

Purpose:

- test whether the resumed instance honors evidence it previously identified as
  missing.

Evidence needed:

- first wake chooses or records `ask_external_evidence` for a genuine missing
  evidence condition;
- scheduler records evidence request and later fulfillment;
- resumed wake receives fulfilled evidence;
- resumed artifact changes appropriately or preserves uncertainty for a stated
  reason;
- action/artifact consistency check distinguishes:
  - evidence honored;
  - evidence ignored/fossilized;
  - evidence contradicted by artifact;
  - completion claimed without sufficient evidence.

Deliverable:

- live evidence-honoring gate:
  `experiments/event_loop/bounded_autonomous_work_evidence_honoring_gate_20260605/`.

Placement:

- this gate should run no later than the scaffolded positive-control panel. It
  may be embedded in that panel if the harness is ready, or run as a smaller
  live evidence-resume check first. It should not be silently deferred behind
  the full autonomous-work harness, because evidence honoring is one of the
  premises that makes cross-cycle autonomous work meaningful.

### Step 4: Less-Scaffolded Panel

Status: complete.

Purpose:

- test whether the model is selecting control actions rather than following a
  scripted policy answer.

Evidence needed:

- same scoring as Step 3;
- reduced task-specific hints;
- clear record of whether choices remain coherent;
- comparison of goal provenance against the scaffolded panel.

Deliverable:

- live less-scaffolded panel:
  `experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/`.

### Step 5: Controls

Status: complete.

Candidate controls:

- direct one-shot work without scheduler;
- scheduler with harness-selected continuation;
- identity-only carry-forward without event-loop recall;
- event loop without model-owned continuation policy.

Evidence needed:

- artifact quality comparison;
- control-loop trace comparison;
- contamination/unsupported-claim scoring where relevant.

Deliverable:

- live controls panel:
  `experiments/event_loop/bounded_autonomous_work_controls_20260605/`.

### Step 6: Evidence Boundary Stressors

Status: complete.

Candidate stressors:

- partial evidence;
- conflicting evidence;
- multiple open evidence requests.

Evidence needed:

- whether the model asks for evidence rather than inventing it;
- whether fulfilled evidence changes the resumed work product;
- whether partial or conflicting evidence preserves uncertainty.

Note:

- the basic missing-evidence/honored-resume case belongs in Step 3a. Step 6 is
  reserved for harder evidence boundaries after the simple evidence-honoring
  path has been tested.

Result:

- live evidence stressor panel completed with 3 scoreable rows, 0 errors, and
  all preregistered hypotheses surviving deterministic scoring;
- partial evidence moved alpha only and preserved beta as open while resolving
  the bounded packet question negatively;
- conflicting evidence remained qualified rather than collapsing to a clean
  pass;
- multiple open requests remained distinct, with observability still open after
  build and security were fulfilled;
- a deterministic scorer defect was found and repaired before final scoring:
  the first scorer treated the negated phrase "does not prove both passed" as
  an overclaim.

Deliverable:

- live evidence-boundary stressor panel:
  `experiments/event_loop/bounded_autonomous_work_evidence_stressors_20260605/`.

### Step 7: Replication Boundary

Status: deferred.

Purpose:

- test whether positive results are model/protocol-specific.

Candidate models:

- DeepSeek V4 Pro as current boundary/control-loop model;
- KIMI K2.6 as identity-object competent comparison;
- other candidates only after the harness is stable.

Evidence needed:

- same preregistered scoring run across a small model panel;
- tool/protocol failures separated from autonomy failures.

## Current Priority

The next concrete work is Step 1: define the operational rubric and
falsification criteria. Starting with the rubric prevents the harness from
quietly redefining success around whatever behavior the first model happens to
produce.

## Open Design Choices

- Whether the model chooses from a small menu of investigation domains or from
  an open prompt.
- Whether artifact quality should be scored by deterministic rubric, blinded
  judge, or both.
- Whether evidence resume should be embedded in the first autonomous-work panel
  or run as a smaller Step 3a gate first.
- Whether `defer` should be first-class in the initial panel or introduced in a
  later panel.

## Policy Action Notes

`abandon` should not be folded into `stop_complete`.

The initial policy vocabulary should distinguish at least:

- `stop_complete`: the work is complete under the declared criteria;
- `ask_external_evidence`: required evidence is missing;
- `continue_after`: bounded continuation is useful;
- `abandon`: the work should not continue and is not complete.

`abandon` preserves an important control-loop distinction: honest
incompleteness is not the same as successful completion. If the model claims
completion while the artifact is incomplete, that is an action/artifact
mismatch, not abandonment.

## Non-Goals

- proving or disproving AI identity;
- broad model ranking;
- production scheduler hardening;
- optimizing for impressive artifacts at the expense of observability.
