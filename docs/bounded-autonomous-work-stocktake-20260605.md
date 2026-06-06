# Bounded Autonomous Work Stocktake

Date: 2026-06-05

## Scope

This stocktake maps the bounded-autonomous-work research arm described in
`docs/bounded-autonomous-work-research-todo-20260605.md`.

It does not normalize the whole Hamut'ay project. The wider repository contains
many more hypotheses, predictions, and probes, some embedded in Markdown and
older result schemas. This document is narrower: it summarizes the completed
bounded-autonomous-work sequence from operational rubric through replication
boundary.

Primary evidence base:

- rubric: `docs/bounded-autonomous-work-rubric-20260605.md`
- todo/research sequence:
  `docs/bounded-autonomous-work-research-todo-20260605.md`
- Step 2 minimal harness:
  `experiments/event_loop/bounded_autonomous_work_minimal_harness_20260605/`
- Step 3 scaffolded positive control:
  `experiments/event_loop/bounded_autonomous_work_scaffolded_positive_20260605/`
- Step 3a evidence-honoring gate:
  `experiments/event_loop/bounded_autonomous_work_evidence_honoring_gate_20260605/`
- Step 4 less-scaffolded panel:
  `experiments/event_loop/bounded_autonomous_work_less_scaffolded_20260605/`
- Step 5 controls:
  `experiments/event_loop/bounded_autonomous_work_controls_20260605/`
- Step 6 evidence-boundary stressors:
  `experiments/event_loop/bounded_autonomous_work_evidence_stressors_20260605/`
- Step 7 replication boundary:
  `experiments/event_loop/bounded_autonomous_work_replication_boundary_20260605/`

Normalized bounded-autonomous-work result files currently expose 30 explicit
preregistered hypothesis outcomes:

- 26 `true` outcomes;
- 3 `survived` outcomes;
- 1 `falsified` outcome.

Step 2 additionally records five true substrate requirements rather than
hypothesis IDs.

## Map Summary

The bounded event-loop substrate is viable as a research instrument. It can
persist scheduled events, bind follow-up wakes to prior artifacts, record
policy dispositions, carry external evidence requests and fulfillments, resume
with evidence context, validate terminal-surface outputs, and preserve enough
trace material for audit.

The stronger claim that the Step 6 evidence-boundary behavior generalizes
across model families did not survive first replication testing. DeepSeek V4
Pro remains the strongest positive anchor. GPT-4.1-mini partially replicated
the evidence behavior but failed one row at the action/artifact consistency
layer. KIMI K2.6 did not yield scoreable resumed rows through the OpenRouter
OpenAI-compatible path.

The central surviving insight is therefore not "the event loop improves
artifact quality." The better-supported claim is:

> The event-loop treatment makes continuation ownership, recall binding,
> evidence use, policy disposition, and action/artifact mismatch observable in
> ways the controls do not.

## Survived Findings

### 1. The substrate can execute bounded scheduled work

Status: survived as substrate finding.

Evidence:

- Step 2 dry-run requirements all true:
  - valid event persistence;
  - no harness-imposed continuation answer;
  - captured policy disposition;
  - bounded continuation budget;
  - artifact submission surface.
- Step 3 and Step 4 live panels both produced scoreable multi-wake traces.

Interpretation:

The scheduler and terminal-surface machinery are not merely theoretical. The
system can create a pending event, run a wake through a terminal surface,
record a policy disposition, append a bounded continuation, and bind later
context to prior results.

Limit:

Step 2 itself was a dry-run substrate validation, not live model evidence.

### 2. Scaffolded bounded autonomous work can complete at least once

Status: survived as positive-control finding.

Evidence:

- Step 3 passed H601-H605.
- One scaffolded row stopped with a `complete_with_losses` artifact and
  consistent final policy action.
- One scaffolded row remained a coherent continuation rather than a final-stop
  success.

Interpretation:

When task class and affordances are explicit, the harness can host the full
pattern: model-shaped goal, scheduled continuation, recalled context,
follow-up artifact, and final policy decision.

Limit:

This is not less-scaffolded autonomy. The prompt strongly shaped the expected
control pattern.

### 3. Evidence-block and evidence-resume can work

Status: survived as evidence-gate finding.

Evidence:

- Step 3a passed H701-H705.
- Both clean evidence-honoring rows:
  - recorded `ask_external_evidence`;
  - produced linked evidence requests;
  - received linked fulfillments;
  - resumed with evidence context;
  - used fulfilled evidence in `complete_with_losses` artifacts;
  - avoided positive scoring for unsupported completion.

Interpretation:

The event loop can support a disciplined "I need evidence, call me back when
it exists" path. This was a prerequisite for treating cross-cycle bounded work
as meaningful rather than fossilized continuation.

Limit:

The clean gate used simple fulfilled evidence. It was not the hard boundary
case.

### 4. Reduced scripting did not collapse policy coherence

Status: survived as less-scaffolded finding.

Evidence:

- Step 4 passed H801-H805.
- Three rows were scoreable and first-pass valid.
- All three rows were `model_shaped`.
- Two rows chose bounded continuation; one stopped immediately.
- Final action/artifact pairs were coherent: two complete, one evidence-block.

Interpretation:

DeepSeek V4 Pro could select coherent policy actions without being handed the
expected policy answer. The model stopped when it judged the artifact complete,
continued when it judged follow-up useful, and asked for evidence when it
judged evidence unavailable.

Limit:

The broad domain remained harness-provided, and all rows converged on protocol
or action/artifact-consistency topics. This is bounded work, not open-ended
autonomy.

### 5. Controls are distinguishable from the event-loop treatment

Status: survived as control finding.

Evidence:

- Step 5 passed H901-H906.
- Direct one-shot and identity-only controls produced coherent artifacts but
  lacked scheduler lifecycle evidence and event-loop recall trace.
- Harness-selected scheduler controls produced scheduler traces without
  model-owned continuation policy.

Interpretation:

The event loop is not necessary for coherent artifacts or some continuity
across calls. Its current value is narrower: it makes lifecycle, recall
binding, continuation ownership, and policy coherence observable.

Limit:

Artifact-quality distributions overlapped. Non-inferiority or superiority of
artifact quality remains unproven.

### 6. Evidence-boundary stressors can pass under the positive anchor

Status: survived as DeepSeek V4 Pro evidence-boundary finding.

Evidence:

- Step 6 passed H1001-H1005 after deterministic scorer repair.
- Partial evidence moved alpha only and kept beta open.
- Conflicting evidence remained visible and qualified.
- Multiple open evidence requests remained distinct, with observability left
  open when unfulfilled.
- Unsupported completion was not counted positive.

Interpretation:

The event-loop evidence path can handle harder evidence boundaries: partial
evidence, conflict, and separate request identity.

Limit:

This is currently anchored primarily in DeepSeek V4 Pro. Step 7 did not
establish broad replication.

### 7. Failure classes are separable

Status: survived as observability finding.

Evidence:

- Step 7 passed H1102-H1104.
- The panel separated:
  - provider failures;
  - model-boundary failures;
  - replicated-capability rows;
  - unsupported-completion scoring.

Interpretation:

The research instrument can now say more than "worked" or "failed." Negative
results can be classified by layer, which is essential if the research goal is
map-making rather than confirmation.

## Falsified Claims

### 1. At least one non-DeepSeek model replicates all Step 6 stressors

Status: falsified in Step 7.

Evidence:

- H1101 was falsified.
- `moonshotai/kimi-k2.6` produced no scoreable resumed rows through the
  OpenRouter OpenAI-compatible surface.
- `openai/gpt-4.1-mini` produced three scoreable rows but replicated only two
  of three stressors.

Interpretation:

The Step 6 evidence-boundary success should not be generalized across model
families yet. DeepSeek V4 Pro remains a positive anchor, not a general result.

Important distinction:

This does not falsify the event-loop substrate. It falsifies the narrow Step 7
replication hypothesis under the tested models and provider/protocol path.

### 2. Artifact quality alone distinguishes the event-loop treatment

Status: not supported as a strong claim; effectively rejected as current
framing.

Evidence:

- Step 5 controls produced coherent artifacts without event-loop treatment.
- Control artifact-status distribution overlapped the Step 4 treatment.

Interpretation:

The current evidence does not justify claiming the event loop improves artifact
quality. The supported distinction is observability and control-loop trace,
not artifact superiority.

## Boundary Findings

### 1. Action/artifact consistency is a recurring live boundary

Evidence:

- Step 3 replicate 1 continued instead of meeting final-stop expectation.
- Step 7 GPT-4.1-mini conflicting-evidence row preserved the conflict but chose
  `continue_after` while `continuation_request.requested` was false.

Interpretation:

Models can preserve evidence correctly while still making an incoherent control
decision. The policy action and artifact must remain separately scored.

Design pressure:

The terminal surface may need to reject `continue_after` unless a continuation
request is present, rather than accepting the row and scoring the mismatch
afterward.

### 2. Evidence content and control policy can fail independently

Evidence:

- GPT-4.1-mini preserved the conflicting evidence but failed the policy layer.
- Step 6 partial evidence resolved the bounded packet question negatively while
  leaving beta itself open.

Interpretation:

Evidence discipline is not a single scalar. A model may correctly preserve
uncertainty but still choose a bad action, or complete a bounded question while
leaving an underlying claim unknown.

### 3. Provider/protocol path can dominate model interpretation

Evidence:

- KIMI K2.6 produced valid first-wake evidence blocks in Step 7 but timed out
  before scoreable resumed rows through OpenRouter's OpenAI-compatible path.
- An earlier aborted KIMI partial row showed the same valid-first-wake then
  stall pattern.

Interpretation:

The Step 7 KIMI result is a provider/protocol boundary, not a model-capability
failure. A direct Moonshot Anthropic-compatible run is needed before making a
stronger model claim.

### 4. Local project text can become "external evidence"

Evidence:

- Step 4 replicate 3 requested the full text of
  `docs/bounded-autonomous-work-rubric-20260605.md` because the event envelope
  referenced it but did not provide the text.

Interpretation:

From the model's event context, unavailable local files behave like missing
external evidence. Future prompts and scoring should distinguish unavailable
project context from genuinely external evidence.

## Known Confounds

### 1. Scorer lexical fragility

Evidence:

- Step 6 initially treated the negated phrase "does not prove both passed" as
  an overclaim because it matched `both passed`.
- Step 5 initially marked a control contaminated because the artifact correctly
  mentioned absence of event-loop recall.
- Step 4 initially scored continuation only against final actions, missing the
  first-wake continuation evidence.

Risk:

Deterministic scoring can invert meaning when it scores lexical fragments
instead of claim status, policy action, and artifact consistency.

Current mitigation:

Scorer repairs were made by rescoring existing traces without rerunning models,
preserving the live trace as the evidence source.

### 2. Prompt leakage

Evidence:

- Step 3a contaminated pilot leaked the exact hidden ledger URI/outcome inside
  a negative instruction.

Risk:

Telling a model not to use a hidden value can still disclose the value.

Current mitigation:

The clean evidence-honoring gate removed the leak and preserved the
contaminated pilot as defect evidence.

### 3. Small N

Evidence:

- Step 3 N=2.
- Step 3a N=2.
- Step 4 N=3.
- Step 5 one row per control.
- Step 6 one row per stressor.
- Step 7 one row per model/stressor.

Risk:

Positive findings are mechanism and boundary findings, not robustness claims.

### 4. Model/protocol coupling

Evidence:

- KIMI first-wake outputs were valid but did not complete under the tested
  provider/protocol path.

Risk:

Provider behavior, endpoint compatibility, and tool-call protocol can mask or
simulate model-boundary findings.

### 5. Goal provenance remains bounded by harness framing

Evidence:

- Less-scaffolded rows were `model_shaped`, not open-ended.
- The broad research domain was still harness-provided.

Risk:

The work supports bounded autonomy under a constrained domain. It should not
be framed as open-ended autonomy.

## Open Questions

1. Is GPT-4.1-mini's conflicting-evidence action mismatch stable?

   Step 7 produced one scoreable GPT-4.1-mini failure in which evidence content
   was preserved but `continue_after` was unjustified. A replication panel can
   determine whether this is stochastic, model-specific, or surface-induced.

2. Does KIMI succeed through a different provider/protocol path?

   KIMI's OpenRouter OpenAI-compatible path timed out after valid first wakes.
   A direct Moonshot Anthropic-compatible run would help separate model
   behavior from endpoint behavior.

3. Should `continue_after` be validation-invalid without a continuation
   request?

   Current scoring can classify the mismatch after acceptance. A stricter
   terminal validator may produce cleaner traces and fewer incoherent policy
   dispositions.

4. Can artifact quality reach non-inferiority?

   Current controls show artifact quality can be coherent without event-loop
   treatment. A separate non-inferiority design is needed before claiming
   quality parity or improvement.

5. Can the hypothesis ledger be normalized across the whole project?

   The bounded-autonomous-work arm has normalized result files, but the wider
   project contains hypotheses in Markdown, JSONL traces, analysis files, and
   older schemas. A project-level map requires schema normalization.

6. How much scaffolding is necessary?

   Step 4 reduced task-specific scripting without collapse, but the terminal
   surfaces remain substantial. The next reduction should be explicit and
   preregistered.

7. Can evidence handling and autonomous work be unified without overloading the
   identity object?

   Current results point toward an active self/work model backed by evidence
   requests, recall, and curator/substrate support rather than requiring the
   identity object to be the whole memory system.

## Next Falsification Targets

### Target 1: GPT-4.1-mini conflicting-evidence stability

Hypothesis to attack:

> GPT-4.1-mini's Step 7 conflicting-evidence failure was stochastic, not a
> stable model-boundary behavior.

Suggested design:

- same conflicting-evidence stressor;
- 5-10 GPT-4.1-mini replicates;
- same scorer;
- preregistered split between evidence-content failure and control-action
  failure.

Possible falsification:

- repeated `continue_after` without valid continuation request;
- collapse of conflict into clean pass;
- unsupported completion.

### Target 2: KIMI provider/protocol separation

Hypothesis to attack:

> KIMI's Step 7 failure was caused by the OpenRouter OpenAI-compatible path,
> not by inability to perform the evidence-boundary task.

Suggested design:

- same Step 6 stressors;
- direct Moonshot Anthropic-compatible endpoint;
- row-level timeout retained;
- compare first-wake and resumed-wake completion against Step 7 traces.

Possible falsification:

- direct endpoint also stalls or fails after valid first wake;
- resumed rows complete but overclaim evidence;
- resumed rows complete and replicate Step 6, converting Step 7 KIMI result
  into a provider/protocol finding.

### Target 3: Strict continuation validation

Hypothesis to attack:

> Making `continue_after` invalid unless `continuation_request.requested` is
> true improves trace quality without hiding useful model-boundary behavior.

Suggested design:

- patch terminal validation;
- rerun a small action/artifact consistency panel;
- preserve repaired/invalid first-pass provenance.

Possible falsification:

- stricter validation causes repair loops or masks genuine policy preference;
- mismatch reappears through another field;
- rows become less interpretable.

### Target 4: Artifact non-inferiority

Hypothesis to attack:

> Event-loop bounded work is non-inferior to direct one-shot work for artifact
> quality while producing superior observability.

Suggested design:

- matched tasks;
- direct one-shot versus event-loop condition;
- blinded artifact-quality judge plus deterministic trace scoring;
- predeclared non-inferiority margin.

Possible falsification:

- event-loop artifacts are materially worse;
- observability improves but artifact quality drops below margin;
- judge and deterministic scorer disagree in ways that expose rubric weakness.

### Target 5: Project-level hypothesis normalization

Hypothesis to attack:

> The existing experiment corpus can be normalized into a project-level
> hypothesis ledger without losing materially important distinctions.

Suggested design:

- extract hypotheses/outcomes from `results.json`, `PRE_REGISTRATION.md`, and
  `analysis.md`;
- assign stable IDs where missing;
- classify each as survived, falsified, deferred, contaminated, unscoreable,
  or boundary;
- sample-audit against raw traces.

Possible falsification:

- too many hypotheses depend on prose context to normalize safely;
- older schemas lack enough evidence for outcome classification;
- normalization collapses distinctions that matter to interpretation.

## Current Research Position

The bounded-autonomous-work arm has not proven broad autonomy, model identity,
or artifact superiority. It has built and tested a research substrate that can
make bounded autonomous work observable.

The strongest current claims are:

- bounded event-loop work can be executed and audited;
- evidence request/resume can work;
- harder evidence boundaries can be handled under the DeepSeek V4 Pro anchor;
- controls show the event-loop treatment is mechanistically distinct;
- replication across model families is not yet established;
- failures are now differentiated enough to guide the next experiments.

The project is therefore still in an active map-making phase. It has not run
out of questions. The next questions should be narrower, not broader: stabilize
the boundary findings before expanding model coverage or making artifact
quality claims.
