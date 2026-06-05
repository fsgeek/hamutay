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

Status: not started.

Deliverable:

- preregistered rubric for bounded autonomous work.

Evidence needed:

- explicit success/failure criteria for artifact quality and control-loop
  behavior;
- distinction between first-pass model competence and scaffolded repair;
- definition of what counts as model-owned goal selection versus harness-set
  work.

### Step 2: Minimal Harness

Status: not started.

Deliverable:

- small live runner that lets the model choose a bounded investigation and
  emit one of the scheduler policy actions through a terminal surface.

Evidence needed:

- valid event persistence;
- no harness-imposed continuation answer;
- captured policy disposition;
- bounded continuation budget;
- artifact submission surface.

### Step 3: Scaffolded Positive-Control Panel

Status: not started.

Purpose:

- determine whether the full pattern can execute when the task class and
  affordances are explicit.

Evidence needed:

- at least one completed autonomous-work chain;
- generated artifact;
- final stop/continue/evidence decision;
- validation and repair provenance;
- comparison against preregistered criteria.

### Step 4: Less-Scaffolded Panel

Status: not started.

Purpose:

- test whether the model is selecting control actions rather than following a
  scripted policy answer.

Evidence needed:

- same scoring as Step 3;
- reduced task-specific hints;
- clear record of whether choices remain coherent.

### Step 5: Controls

Status: not started.

Candidate controls:

- direct one-shot work without scheduler;
- scheduler with harness-selected continuation;
- identity-only carry-forward without event-loop recall;
- event loop without model-owned continuation policy.

Evidence needed:

- artifact quality comparison;
- control-loop trace comparison;
- contamination/unsupported-claim scoring where relevant.

### Step 6: Evidence Boundary Stressors

Status: deferred until a simple autonomous-work chain exists.

Candidate stressors:

- missing evidence;
- partial evidence;
- conflicting evidence;
- multiple open evidence requests.

Evidence needed:

- whether the model asks for evidence rather than inventing it;
- whether fulfilled evidence changes the resumed work product;
- whether partial or conflicting evidence preserves uncertainty.

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
- Whether evidence resume should be embedded in the first autonomous-work
  panel or reserved as a later stressor.
- Whether `defer` and `abandon` should be first-class policy actions in the
  initial panel or recorded as variants of `stop_complete`.

## Non-Goals

- proving or disproving AI identity;
- broad model ranking;
- production scheduler hardening;
- optimizing for impressive artifacts at the expense of observability.
