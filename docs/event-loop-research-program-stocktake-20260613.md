# Hamut'ay Event-Loop Research Program Stocktake

Date: 2026-06-13

Scope: post-Goal-10 stocktake for
`docs/event-loop-research-program-goals-20260612.md`.

This document summarizes the current evidence state after Goals 1-10, identifies
which hypotheses survived, which were falsified or narrowed, states the
strongest defensible systems claim, lists remaining untested areas, and proposes
candidate Goal 11 directions.

## Executive Summary

The event-loop research arm now has a coherent systems result, but not a broad
capability result.

The strongest current claim is:

> In a bounded, audit-grade harness, event-loop bounded work can preserve
> artifact quality relative to direct one-shot work on small evidence-bound
> tasks while providing stronger deterministic observability and
> reconstructability. The same evidence does not show working-set efficiency,
> broad task scaling, model-general capability, or production autonomy.

The work is no longer blocked on whether the scheduler substrate can run a
basic loop, whether actions can be logged, whether restart boundaries can be
reconstructed, or whether small event-loop artifacts can be useful. Those
questions now have positive evidence.

The main open research boundary is whether the observed observability benefit
remains worth its cost as tasks become larger, noisier, more ambiguous, more
failure-prone, or more model-diverse.

## Evidence Base

Primary post-roadmap artifacts:

- Goal 1:
  `experiments/event_loop/action_control_surface_gate_20260612/analysis.md`
- Goal 2:
  `experiments/event_loop/live_evidence_resume_20260612/analysis.md`
- Goal 3:
  `experiments/event_loop/evidence_boundary_panel_20260612/analysis.md`
- Goal 4:
  `experiments/event_loop/strict_continuation_validation_20260612/analysis.md`
- Goal 5:
  `experiments/event_loop/audit_restart_boundary_20260612/analysis.md`
- Goal 6:
  `experiments/event_loop/less_scaffolded_bounded_investigation_20260612/analysis.md`
- Goal 7:
  `experiments/event_loop/working_set_accounting_gate_20260612/analysis.md`
- Goal 8:
  `experiments/event_loop/working_set_matched_panel_20260612/analysis.md`
- Goal 9:
  `experiments/event_loop/des_wall_clock_boundary_20260612/analysis.md`
- Goal 10:
  `experiments/event_loop/artifact_noninferiority_20260612/analysis.md`

Important supporting artifacts from the earlier bounded-autonomous-work arm:

- `experiments/event_loop/bounded_autonomous_work_evidence_honoring_gate_20260605/analysis.md`
- `experiments/event_loop/bounded_autonomous_work_evidence_stressors_20260605/analysis.md`
- `experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/analysis.md`
- `experiments/event_loop/model_owned_policy_boundary_20260605/analysis.md`
- `docs/bounded-autonomous-work-research-roadmap-20260605.md`

## Hypotheses That Survived

### 1. Hardened Action Surface Is Adequate For Live Evidence-Resume

Status: survived as a readiness gate.

Evidence:

- Goal 1 primary strict pass count was 2/3.
- The third row was not hidden as success: it was classified as a
  parser-recovery boundary.
- The gate preserved raw requests, responses, attempts, strict evaluation, and
  recovery evaluation.

Defensible claim:

The live model-authored action/control surface can produce interpretable rows
often enough to proceed with bounded evidence-resume experiments, provided
primary strict scoring remains primary and recovery remains audit evidence.

### 2. Evidence-Resume And Evidence Stressors Are Feasible Under Bounded Conditions

Status: survived as bounded mechanism evidence.

Evidence:

- Earlier evidence-honoring gate: 2/2 rows requested evidence, received linked
  fulfillment, used fulfilled evidence, and completed coherently.
- Earlier evidence stressors: partial, conflicting, and multiple-request cases
  all produced scoreable rows with conflict/loss information preserved.
- Goal 2 and Goal 3 artifacts preserve the 2026-06-12 continuation of this
  evidence-resume line.

Defensible claim:

The harness can support bounded evidence request, fulfillment, resume, and
stressor evaluation without collapsing every result into a simple success or
failure label.

Boundary:

This does not prove that arbitrary models will honor evidence, or that
fulfilled evidence will be used correctly under larger or adversarial tasks.

### 3. Strict Continuation Validation Improves Interpretability

Status: survived as a control-surface hardening result.

Evidence:

- Goal 4 classified invalid `continue_after` rows before acceptance.
- Valid continuation rows were preserved.
- No new failure mode was observed in the probe.

Defensible claim:

Requiring `continue_after` to include a valid continuation request improves
trace interpretability and prevents hollow continuation claims from being
counted as valid control actions.

### 4. Audit/Restart Boundary Is Ready For Small Autonomy Panels

Status: survived as substrate readiness evidence.

Evidence:

- Goal 5 passed happy rehearsal, resume-after-seed-apply,
  resume-after-event-claim, rejected-operation trace, and tamper detection rows.
- The result classified the audit/restart boundary as ready for less-scaffolded
  no-token or tiny-token autonomy panels.

Defensible claim:

The current harness can preserve enough action, event, memory, ledger, and
restart-frontier information to reconstruct small bounded runs and attribute
several important failure modes.

### 5. Less-Scaffolded Bounded Investigation Is Possible

Status: survived as a bounded autonomy map point.

Evidence:

- Goal 6 had 3/3 scoreable positive rows under the preregistered scorer.
- Rows were not counted positive merely because policy vocabulary was valid.
- The scorer evaluated model-shaped target, control decision, artifact, and
  restart trace alignment.

Defensible claim:

A model can materially shape bounded work inside the event-loop harness while
preserving reconstructable action/artifact traces under this task shape.

Boundary:

This is not open-ended autonomy. It is bounded work in a constrained research
harness.

### 6. Working-Set Accounting Gate Is Ready

Status: survived as accounting readiness, not artifact-quality evidence.

Evidence:

- Goal 7 distinguished live context, carried state, recalled context, omitted
  context, declared losses, unavailable evidence, token counts, and recall
  provenance.
- The gate classified findings across prompt/schema, memory substrate coverage,
  and recall protocol layers.

Defensible claim:

The harness can now measure working-set behavior well enough to avoid confusing
model behavior with substrate, recall-protocol, prompt/schema, or scorer
failures in small panels.

### 7. DES Remains The Semantic Scheduler Baseline

Status: survived as a boundary probe.

Evidence:

- Goal 9 passed paired DES and wall-clock smoke tests for due ordering,
  expiration, next-wake reporting, and restart frontier recovery.
- No semantic scheduler failures or runtime availability failures were
  observed.
- The result concluded that no current research claim requires wall-clock
  execution.

Defensible claim:

The project can continue using deterministic discrete-event simulation for
semantic scheduler experiments. Wall-clock support exists as a bounded adapter,
but it is not currently required for the main research claims.

### 8. Artifact Non-Inferiority With Stronger Observability

Status: survived under a small matched-task panel.

Evidence:

- Goal 10 classification: survived.
- Mean artifact quality tied direct one-shot: 0.9000 vs 0.9000.
- Artifact-quality delta event minus direct: 0.0000, inside the 0.1000 margin.
- Mean observability favored event-loop bounded work: 1.0000 vs 0.5500.
- No catastrophic artifact failures occurred.
- Judge/scorer disagreement occurred in direct one-shot rows, where useful
  artifacts had weaker trace observability.

Defensible claim:

For the tested small evidence-bound tasks, event-loop bounded work can preserve
artifact quality relative to direct one-shot work while producing stronger
deterministic observability.

Boundary:

This does not show artifact superiority or token efficiency.

## Hypotheses Falsified Or Narrowed

### 1. Model-Managed Working Set Already Outperforms Controls

Status: falsified.

Evidence:

- Goal 8 classification: falsified.
- Event-loop working-set score: 0.6000.
- Best control working-set score: 0.9250.
- Event-loop artifact quality: 0.7500.
- Best control artifact quality: 1.0000.
- Event-loop prompt token use was not lower than direct one-shot.

Interpretation:

Memory access and model-selected recall were not sufficient. The model recovered
needed evidence but carried contaminating material and failed declared-loss
discipline.

Narrowed claim:

The system can expose working-set failures. It cannot yet claim that
model-managed working-set selection is better, non-inferior, or cheaper than
controls.

### 2. Memory Access Alone Solves Working-Set Management

Status: narrowed by Goal 8.

Evidence:

- Goal 8 showed evidence recovery can coexist with lower working-set score and
  worse artifact quality.
- Goal 10 later showed artifact non-inferiority on smaller matched tasks, but
  with higher token use.

Interpretation:

Recall availability is necessary but not sufficient. The remaining work is
selection discipline, loss declaration, contamination avoidance, and cost.

### 3. Wall-Clock Scheduling Is Needed For Current Semantic Claims

Status: narrowed away for now.

Evidence:

- Goal 9 passed DES/wall-clock boundary probes.
- No current research claim required real elapsed time.

Interpretation:

Real clocks may matter later for deployment or real-time autonomy, but the
current semantic scheduler questions are still better tested with DES.

### 4. Event-Loop Work Is Efficient By Default

Status: not supported, and currently doubtful for small tasks.

Evidence:

- Goal 10 event-loop rows used more prompt and completion tokens than direct
  one-shot rows because they used two cycles.
- Goal 8 also did not show prompt-token advantage.

Interpretation:

The current event-loop benefit is observability and reconstructability, not
efficiency. Efficiency may appear only on larger tasks where direct one-shot
context grows or fails, but that remains untested.

### 5. Broad Model-General Capability

Status: not established.

Evidence:

- The strongest 2026-06-12/13 panels primarily use DeepSeek V4 Pro as the live
  positive anchor.
- Earlier model exploration found protocol and contract sensitivity across
  models.

Interpretation:

The current result is a systems evaluation under a working model/harness pair.
It is not a broad model capability paper.

## Strongest Current Systems Claim

The strongest defensible systems claim is:

> Hamut'ay's event-loop substrate can run bounded model-shaped work with
> audit-grade traces, restart/reconstruction boundaries, evidence-request and
> recall provenance, deterministic scoring, and artifact-quality
> non-inferiority to direct one-shot execution on small evidence-bound tasks.
> Its demonstrated advantage is observability, not artifact superiority or
> token efficiency.

This claim is meaningful because it separates four things that are often
collapsed:

- artifact quality;
- control-action validity;
- evidence handling;
- substrate observability and reconstruction.

The system is therefore useful as a research instrument even when it does not
improve artifact quality. It makes failures more attributable.

## What Remains Untested

### Scale And Cost

Untested:

- larger evidence corpora;
- larger task sets;
- longer multi-wake chains;
- tasks where direct one-shot context becomes expensive, cluttered, or
  unreliable;
- whether event-loop observability can justify extra token cost.

### Robustness Under Noise

Untested:

- more distractors;
- misleading evidence;
- stale evidence;
- partial contradictory evidence across multiple records;
- tasks where the right action is abandon or defer rather than complete.

### Model Generality

Untested:

- whether the Goal 10 result replicates with Claude, OpenAI, Gemini, Kimi,
  Mistral, Grok, or local open-weight models;
- whether model failures are caused by training, endpoint protocol, prompt
  salience, schema contract, or tool-call implementation.

### Real Memory Substrate

Untested:

- Yanantin-backed memory for these Goal 10 task shapes;
- semantic find scope;
- attestation/relabel chains;
- Archivist-style aggregate query-path telemetry;
- whether episodic who/what/when/where/why/how indexing improves recall beyond
  the bounded local substitute.

### Human Or Blinded Review

Untested:

- whether a blinded human or LLM judge agrees with the deterministic Goal 10
  artifact-quality rubric;
- whether deterministic observability scores overweight trace richness relative
  to practical debugging usefulness;
- whether direct one-shot artifacts remain preferred by external judges despite
  weaker traces.

### Autonomy Boundary

Untested:

- less-scaffolded Goal 10-style tasks where the model chooses the investigation
  target;
- longer self-directed work with multiple stop/defer/abandon choices;
- disengagement or refusal behavior under relational imbalance;
- policy for model-owned scheduling across real time.

### Production Boundary

Untested:

- process supervision;
- preventive sandboxing rather than detective audit;
- tamper-resistant external logs;
- concurrent agents;
- container/VM isolation;
- wall-clock deadlines and service availability.

## Candidate Goal 11 Directions

### Candidate A. Scale/Cost Crossover Panel

Research question:

At what task size or evidence-corpus size does event-loop observability become
worth its extra token cost, and does direct one-shot quality degrade first?

Experiment:

Run matched direct one-shot and event-loop bounded conditions across increasing
corpus sizes, for example 5, 20, 50, and 100 records, with controlled relevant
evidence and distractors. Preserve artifact quality, observability, prompt and
completion tokens, latency, contamination, and declared losses.

Cost:

Medium to high. Requires more generated corpus data and more live calls than
Goal 10.

Benefit:

High. Directly attacks the biggest limitation after Goal 10: the event-loop
form is more observable but currently more expensive.

Falsification value:

High. If event-loop work stays more expensive without quality or reliability
benefit as corpus size grows, the working-set thesis is materially weakened. If
direct one-shot degrades while event-loop quality holds, the systems claim gets
much stronger.

Recommendation:

Strong candidate for Goal 11 if the next priority is the systems paper.

### Candidate B. Adversarial Evidence And Loss-Discipline Panel

Research question:

Does event-loop bounded work preserve declared losses, uncertainty, and
conflict discipline better than direct one-shot work when evidence is partial,
stale, contradictory, or misleading?

Experiment:

Extend Goal 10 with adversarial evidence conditions:

- one missing required fact;
- one stale-but-plausible record;
- one conflicting pair;
- one distractor semantically close to the task.

Score artifact quality, unsupported completion, conflict preservation,
declared-loss quality, contamination, and observability.

Cost:

Medium. The harness already has evidence-boundary and Goal 10 scoring pieces.

Benefit:

High. Tests a central safety/research value of the event-loop form: visible
failure and uncertainty, not just useful artifacts.

Falsification value:

High. If event-loop rows fabricate or silently collapse conflicts at the same
rate as direct rows, the observability claim may remain true but its practical
safety value weakens.

Recommendation:

Strong candidate for Goal 11 if the next priority is robustness and safety.

### Candidate C. Blinded Artifact Review Calibration

Research question:

Does the deterministic Goal 10 artifact-quality rubric agree with blinded
external review?

Experiment:

Use the preserved Goal 10 review packet plus one or two new panels. Have a
blinded judge score artifacts without condition labels. Compare blinded scores
to deterministic scores and report disagreements.

Cost:

Low to medium, depending on whether the judge is human, LLM, or both.

Benefit:

Medium. It validates the evaluation instrument rather than the event-loop
mechanism itself.

Falsification value:

Medium. If blinded review disagrees sharply, prior artifact-quality claims
become weaker or need recalibration. If it agrees, Goal 10 becomes more
publishable.

Recommendation:

Good near-term support work, but probably not the most informative Goal 11
unless the immediate objective is paper readiness.

### Candidate D. Yanantin Memory Integration Probe

Research question:

Does the real memory substrate change evidence recovery, provenance, or
working-set discipline relative to the bounded local substitute?

Experiment:

Repeat a small Goal 7/8/10 hybrid with Yanantin-backed storage once find/recall
scope and attestation boundaries are ready. Compare local substitute versus
Yanantin on request answerability, recall provenance, contamination, declared
losses, and artifact quality.

Cost:

Medium to high, depending on Yanantin readiness.

Benefit:

High for the broader Hamut'ay architecture, because local substitute results
are only a proxy for the intended memory substrate.

Falsification value:

Medium to high. A negative result would identify substrate complexity as a real
barrier. A positive result would make the memory architecture much more
credible.

Recommendation:

Defer until Yanantin has the required substrate features. Do not block the next
research move on it unless integration readiness has changed.

### Candidate E. Model Replication Panel

Research question:

Does the Goal 10 artifact non-inferiority plus observability result replicate
across model families?

Experiment:

Run the same Goal 10 panel with one or two additional models using direct,
known-working endpoints. Preserve protocol failures as protocol/model boundary
findings rather than forcing all rows into artifact comparison.

Cost:

Medium. Provider setup and protocol differences can dominate.

Benefit:

Medium to high. It helps separate systems claim from DeepSeek-specific behavior.

Falsification value:

Medium. Failure could mean model limitation, endpoint protocol mismatch, prompt
salience issue, or harness defect. Attribution may be hard.

Recommendation:

Useful after Candidate A or B unless model-general claims become a paper goal.

### Candidate F. Longer Autonomous Chain With Stop/Defer/Abandon

Research question:

Can the event-loop harness preserve artifact non-inferiority and observability
across a longer, less-scaffolded chain where the model may stop, defer,
abandon, or request evidence?

Experiment:

Combine Goal 6 less-scaffolded selection with Goal 10 artifact/observability
scoring over 3-5 cycles. Require at least one point where defer or abandon is a
valid action.

Cost:

High. More cycles, more scoring ambiguity, and more failure modes.

Benefit:

High if successful, because it moves closer to bounded autonomous work rather
than bounded artifact production.

Falsification value:

High. It can reveal whether the current positive results are only shallow
two-cycle artifacts.

Recommendation:

Important, but probably not the immediate next step unless the project wants to
prioritize autonomy depth over evaluation stability.

## Recommended Goal 11

Recommended next goal: Candidate B, the adversarial evidence and
loss-discipline panel.

Reasoning:

- It builds directly on Goal 10 without requiring a new substrate.
- It targets the most important remaining safety/research question: whether
  event-loop observability changes behavior when evidence is incomplete,
  conflicting, stale, or misleading.
- It has high falsification value: either the event-loop form preserves
  uncertainty/loss discipline better than direct one-shot, or it does not.
- It keeps the research focused on evidence handling and attribution rather
  than prematurely expanding to broad model sweeps or production runtime
  engineering.

Candidate A is the second-best choice if cost/efficiency is the immediate paper
pressure. Candidate C is useful as supporting calibration. Candidate D should
wait for Yanantin readiness. Candidate E should wait until model-general claims
matter. Candidate F is valuable but should come after the adversarial evidence
boundary is sharper.

## Candidate Goal 11 Prompt

```text
Preregister and run an adversarial evidence and loss-discipline panel comparing event-loop bounded work against direct one-shot work. Reuse the Goal 10 artifact-quality and observability scoring surfaces, but add matched tasks with missing, stale, conflicting, and semantically distracting evidence. Score artifact quality, unsupported completion, conflict preservation, declared-loss discipline, contamination, trace observability, and judge/scorer disagreements. Write and commit an analysis stating whether event-loop bounded work preserves uncertainty and loss discipline better than direct one-shot work, and whether any observability gain changes the practical safety value of the harness.
```

## Closing Assessment

Continuing this research arm is justified.

The reason is not that every hypothesis survived. Goal 8 falsified the simple
working-set advantage claim, and that failure was valuable. The reason to
continue is that the program has produced an increasingly sharp map:

- the scheduler and audit substrate are viable for bounded experiments;
- the action surface can produce interpretable rows;
- the model can shape bounded work under constraints;
- memory access alone is insufficient;
- artifact non-inferiority is achievable on small tasks;
- observability is the strongest demonstrated advantage;
- token efficiency and robustness under adversarial evidence remain open.

That is a real systems research position. The next work should keep trying to
falsify the practical value of observability rather than merely adding more
positive demonstrations.
