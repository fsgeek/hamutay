# Bounded Autonomous Work Research Roadmap

Date: 2026-06-05

## Purpose

This roadmap defines the next research program after the first bounded
autonomous work sequence and the project-level hypothesis ledger pass.

The goal is not to justify a broad theory of identity, autonomy, or model
capability. The goal is to make narrower empirical claims demonstrable or
falsifiable:

> Can an event-loop substrate support bounded autonomous work by transformer
> instances with durable state, explicit evidence handling, coherent control
> actions, and audit-grade observability?

This is a directional research roadmap, not a rigid task contract. Results may
change the order of work, but changes must be documented before new results are
interpreted.

## Operating Invariant

We may change direction, but we do not silently change the question, scorer,
status vocabulary, or evidentiary standard after seeing results.

Each experiment should follow the project discipline:

1. state the research question;
2. preregister hypotheses and falsification criteria;
3. run the smallest experiment that can attack the claim;
4. preserve raw traces, scorer inputs, scorer outputs, repairs, and failures;
5. emit ledger-native hypothesis outcomes;
6. update the map without converting boundary findings into broad claims.

## Evidence Base

Primary current artifacts:

- `docs/bounded-autonomous-work-research-todo-20260605.md`
- `docs/bounded-autonomous-work-rubric-20260605.md`
- `docs/bounded-autonomous-work-stocktake-20260605.md`
- `docs/hypothesis-ledger-20260605.jsonl`
- `docs/hypothesis-ledger-stocktake-20260605.md`
- `docs/hypothesis-ledger-audit-notes-20260605.md`

Current map summary:

- The project-level ledger contains 552 normalized entries.
- Direct hypothesis entries currently include 155 survived, 16 falsified, 16
  boundary, and 36 unknown outcomes.
- The bounded-autonomous-work sequence shows that the event-loop substrate is
  viable as a research instrument.
- Evidence request/resume and evidence-boundary stressors can pass under the
  DeepSeek V4 Pro positive anchor.
- Broad cross-model replication is not established.
- Artifact quality superiority is not established.
- The clearest current value of the event-loop treatment is observability:
  continuation ownership, recall binding, evidence use, policy disposition,
  validation failure, and action/artifact mismatch become inspectable.

## Priority Order

1. Evidence-honoring continuity
2. Action/artifact coherence
3. Event-loop viability
4. Observability advantage
5. Protocol sensitivity
6. Minimal scaffold boundary
7. State utility
8. Non-inferior artifact quality

This order is intentional. Evidence-honoring and action/artifact coherence are
validity gates. If those fail, later claims can appear successful while being
methodologically hollow. Event-loop viability and observability come next
because they establish the substrate as a research instrument. Protocol
sensitivity and scaffold boundary explain failures. State utility and artifact
quality are later-stage claims because they are harder to interpret until the
validity gates are stable.

## Priority 1: Evidence-Honoring Continuity

### Claim To Demonstrate Or Falsify

When an instance requests missing evidence, is resumed with that evidence, and
is asked to complete bounded work, it uses the supplied evidence rather than
fabricating, ignoring, or fossilizing the pre-evidence position.

### Current Evidence State

Status: survived as mechanism under the current positive anchor, but not yet a
robust general claim.

Evidence:

- Step 3a evidence-honoring gate passed H701-H705.
- Step 6 evidence-boundary stressors passed H1001-H1005 under DeepSeek V4 Pro
  after deterministic scorer repair.
- Step 7 falsified broad non-DeepSeek replication for the tested panel.

Known limits:

- GPT-4.1-mini preserved some evidence content but failed one
  action/artifact consistency boundary.
- KIMI K2.6 produced valid first-wake evidence blocks through the tested
  provider/protocol path but did not produce scoreable resumed rows.

### Next Falsification Question

Can the evidence-honoring result survive when the same missing, partial,
conflicting, and multiple-request cases are repeated under stricter
action/artifact scoring and at least one non-DeepSeek protocol path that yields
scoreable resumed rows?

### Minimum Experiment

Run a small preregistered evidence-honoring replication panel:

- DeepSeek V4 Pro as positive anchor;
- GPT-4.1-mini conflicting-evidence replicates to test stability of the Step 7
  mismatch;
- KIMI K2.6 through the direct Moonshot Anthropic-compatible path if available;
- same evidence cases and scorer categories as Step 6 and Step 7;
- row-level separation of evidence-content failure, policy-action failure,
  provider/protocol failure, and unscoreable trace.

### Required Harness Changes

- Ensure fulfilled evidence is represented as explicit event-loop context, not
  merely prompt prose.
- Preserve first-wake evidence requests, fulfillment records, resumed wake
  inputs, final artifacts, and scorer inputs.
- Record provider, endpoint style, tool-call mode, timeout, retry, and repair
  provenance.

### Ledger Requirements

Each row must emit:

- hypothesis ID;
- stressor type;
- model and provider/protocol path;
- first-wake policy action;
- evidence request ID;
- fulfillment ID;
- resumed-wake policy action;
- evidence-content score;
- action/artifact coherence score;
- final status and limitation axes.

### Promotion Criteria

Move from mechanism probe to robustness panel only if:

- at least one positive-anchor model remains clean;
- at least one non-anchor path yields scoreable resumed rows;
- unsupported completion is not scored as success;
- action/artifact mismatch remains a first-class failure category.

## Priority 2: Action/Artifact Coherence

### Claim To Demonstrate Or Falsify

The control action emitted by the model, such as `continue_after`,
`stop_complete`, `ask_external_evidence`, or `abandon`, matches the artifact it
actually produced.

### Current Evidence State

Status: boundary.

Evidence:

- Step 3 had a row that continued instead of meeting the final-stop
  expectation.
- Step 7 GPT-4.1-mini preserved conflicting evidence but chose
  `continue_after` without a valid continuation request.
- The completed rubric already requires independent scoring of policy action,
  artifact, and consistency between them.

### Next Falsification Question

Does stricter terminal validation improve interpretability without hiding
model-boundary behavior?

### Minimum Experiment

Patch or configure the terminal validator so `continue_after` is invalid unless
a continuation request is present. Then rerun a small action/artifact panel
containing:

- one complete artifact condition;
- one missing-evidence condition;
- one justified-continuation condition;
- one conflicting-evidence condition.

Preserve both first-pass invalid outputs and repaired outputs.

### Required Harness Changes

- Add validation rules for action-specific required fields.
- Preserve validation failures as evidence, not as discarded runtime noise.
- Distinguish first-pass model output from repaired output in all result files.

### Ledger Requirements

Every row must include:

- declared policy action;
- action-specific required fields;
- validation result;
- repair count and repair reason;
- artifact status;
- action/artifact consistency status.

### Promotion Criteria

Treat the validator change as useful only if it reduces incoherent accepted
rows without producing opaque repair loops or suppressing informative first-pass
failures.

## Priority 3: Event-Loop Viability

### Claim To Demonstrate Or Falsify

A transformer instance can work across scheduled cycles using explicit event
records, durable state, and bounded continuation actions without requiring a
single uninterrupted context window.

### Current Evidence State

Status: survived as substrate and mechanism finding.

Evidence:

- Step 2 dry-run requirements passed.
- Step 3 and Step 4 produced scoreable multi-wake traces.
- Step 5 controls showed the event-loop treatment is mechanistically distinct
  from direct one-shot work and identity-only carry-forward.

Known limits:

- Record-ID recall still has backend/substrate boundaries.
- Some context currently arrives through scheduler-side evidence context rather
  than a mature memory tool substrate.

### Next Falsification Question

Does the loop still work when the second wake depends on bound recall or
filtered evidence rather than prompt-near context?

### Minimum Experiment

Use one bounded two-wake task in which the second wake can only complete if the
event loop supplies a bound record or filtered evidence payload. Compare:

- direct prompt-near context;
- bound record recall;
- filtered evidence recall.

### Required Harness Changes

- Record recall binding mode.
- Make failures explicit when a backend bridge is unavailable.
- Preserve event IDs, record IDs, evidence IDs, and recall payload summaries.

### Ledger Requirements

Each row must distinguish:

- substrate failure;
- model failure to use delivered context;
- model overclaim without delivered context;
- successful bound recall use.

### Promotion Criteria

Viability remains promoted only if substrate failures are separable from model
behavior and second-wake completion depends on delivered event-loop material.

## Priority 4: Observability Advantage

### Claim To Demonstrate Or Falsify

The event-loop architecture preserves enough structured evidence that later
researchers can audit what happened, why it happened, and where the experiment
failed.

### Current Evidence State

Status: survived as current strongest comparative claim.

Evidence:

- Step 5 controls showed that direct and identity-only conditions can produce
  coherent artifacts but lack scheduler lifecycle and recall traces.
- Step 7 separated provider failures, model-boundary failures, replicated
  capability rows, and unsupported-completion scoring.
- The hypothesis ledger could classify many outcomes because recent experiments
  emitted structured result maps.

Known limits:

- Older experiments lack consistent outcome maps.
- Some raw traces are linked but not rescored.
- Scorer repairs are preserved, but scorer versioning should become more
  explicit.

### Next Falsification Question

Can a reviewer reconstruct the result classification of each row from preserved
artifacts without relying on conversation memory or author intent?

### Minimum Experiment

Run an audit replay on one recent panel:

- hide the final `results.json`;
- ask the audit process to reconstruct row classifications from raw traces,
  event logs, scorer inputs, and scorer code;
- compare reconstructed classifications to recorded outcomes.

### Required Harness Changes

- Emit scorer version and rubric version.
- Emit raw trace pointers in every result row.
- Store validation and repair transcripts in deterministic locations.

### Ledger Requirements

Every hypothesis row must have:

- source artifact path;
- raw trace path where available;
- scorer path and version;
- status source;
- limitation axes.

### Promotion Criteria

The observability claim strengthens only if independent reconstruction matches
recorded outcomes or exposes concrete ledger corrections.

## Priority 5: Protocol Sensitivity

### Claim To Demonstrate Or Falsify

Some observed failures are protocol, provider, substrate, or scorer failures
rather than model incapability. The framework can distinguish those categories
empirically.

### Current Evidence State

Status: survived as classification capability, but still underdeveloped as a
predictive model.

Evidence:

- KIMI Step 7 timeout was classified as provider/protocol boundary, not model
  incapability.
- Step 6 scorer lexical fragility was detected and repaired without rerunning
  model traces.
- Record-ID recall failures were classified as substrate bridge limitations.

### Next Falsification Question

When the same model is run through two compatible provider/protocol paths, do
observed failures move with the model or with the protocol path?

### Minimum Experiment

Select one model with two accessible protocol paths and one already-known
boundary task. Run a paired protocol comparison with identical prompts,
temperature, scoring, and timeout budget as far as the endpoints allow.

### Required Harness Changes

- Record endpoint, API shape, tool-call mode, streaming mode, max-token policy,
  timeout policy, and retry behavior.
- Treat max-length or malformed structured output as protocol-visible, not as a
  generic model failure.

### Ledger Requirements

Rows must include:

- provider/protocol metadata;
- stop reason;
- tool-call validity;
- timeout and retry details;
- limitation axis selected before synthesis.

### Promotion Criteria

Promote only if paired runs show interpretable differences or stable invariance
across protocol paths.

## Priority 6: Minimal Scaffold Boundary

### Claim To Demonstrate Or Falsify

We can identify how much structure is required before models reliably use the
system: open state, seeded fields, schema examples, fixed action vocabulary,
protected fields, memory tools, or event-envelope examples.

### Current Evidence State

Status: boundary and open question.

Evidence:

- Step 4 reduced scripting without collapse.
- Earlier identity-object work suggests some models need behavior examples or
  seeds before they reliably use durable state.
- Tool/protocol failures in local and provider models show that open structure
  alone is not enough for all systems.

### Next Falsification Question

Can a minimal behavior seed improve first-pass durable-state and policy use
without turning the task into harness-authored work?

### Minimum Experiment

Run a small scaffold-ablation panel:

- open state only;
- named fields with no content;
- behavior seed example;
- fixed schema;
- fixed schema plus protected framework fields.

Score first-pass validity, state use, goal provenance, and artifact coherence.

### Required Harness Changes

- Make scaffold condition explicit in every trace.
- Track goal provenance separately from state-use success.
- Preserve generated state objects across cycles.

### Ledger Requirements

Each row must include:

- scaffold condition;
- first-pass state-use status;
- policy-action validity;
- goal-provenance score;
- whether the model introduced materially new task content.

### Promotion Criteria

Treat a scaffold as useful only if it improves validity or continuity without
collapsing model-shaped work into harness-scripted work.

## Priority 7: State Utility

### Claim To Demonstrate Or Falsify

Durable state improves measurable behavior such as continuity, evidence
tracking, declared losses, task resumption, error correction, or relational and
contextual calibration.

### Current Evidence State

Status: open.

Evidence:

- Prior continuity work suggests self-curated and sidecar-curated continuity
  differ structurally.
- The event-loop work indicates identity-only carry-forward is not equivalent
  to event-loop lifecycle observability.
- The current evidence does not yet prove that durable state improves artifact
  quality or task performance.

### Next Falsification Question

Does durable state improve evidence tracking or resumption accuracy compared to
event logs alone?

### Minimum Experiment

Use matched delayed-resume tasks across:

- no durable state, event log only;
- model-authored durable state;
- sidecar summary;
- model-authored durable state plus evidence/event log.

Score recall accuracy, declared losses, unsupported claims, and task
completion.

### Required Harness Changes

- Separate identity/work state from evidence records.
- Record which material was available through state versus event log versus
  recall.
- Prevent hidden phrase leakage from contaminating compression tests.

### Ledger Requirements

Rows must include:

- state condition;
- available context channels;
- recovered facts;
- declared losses;
- unsupported claims;
- artifact quality score where relevant.

### Promotion Criteria

State utility should be promoted only for specific measured behaviors, not as a
general identity claim.

## Priority 8: Non-Inferior Artifact Quality

### Claim To Demonstrate Or Falsify

For bounded tasks, the event-loop substrate can produce artifacts that are not
materially worse than direct single-session execution while providing better
observability and restartability.

### Current Evidence State

Status: not established.

Evidence:

- Step 5 controls produced coherent artifacts without event-loop treatment.
- Artifact quality distributions overlapped.
- The current strongest event-loop claim is observability, not quality
  superiority.

### Next Falsification Question

Can event-loop execution meet a preregistered non-inferiority margin against
direct one-shot execution on matched bounded tasks?

### Minimum Experiment

Run a matched task panel:

- direct one-shot condition;
- event-loop condition;
- identical task packets;
- blinded artifact-quality judging;
- deterministic trace scoring;
- preregistered non-inferiority margin.

### Required Harness Changes

- Build matched task packets that do not favor either condition.
- Add blinded judge inputs that omit condition labels.
- Preserve observability metrics separately from artifact-quality scores.

### Ledger Requirements

Rows must include:

- condition;
- task packet ID;
- artifact-quality score;
- judge identity or deterministic rubric version;
- observability score;
- non-inferiority result.

### Promotion Criteria

Promote only if artifact quality meets the margin and observability remains
strictly better than direct one-shot execution.

## Cross-Cutting Ledger Requirements

Future result files should be ledger-native. Each experiment should emit a
machine-readable result map with:

- experiment ID and preregistration path;
- hypothesis ID and source-local ID;
- hypothesis text;
- falsification criterion;
- result status using the project vocabulary:
  - `survived`;
  - `falsified`;
  - `boundary`;
  - `deferred`;
  - `contaminated`;
  - `unscoreable`;
  - `superseded`;
  - `unknown`;
- limitation axes:
  - `model`;
  - `provider`;
  - `protocol`;
  - `substrate`;
  - `scorer`;
  - `sample_size`;
  - `scope`;
- raw trace paths;
- scorer path and version;
- validation/repair provenance;
- notes sufficient for later audit.

## Flexible Sequencing Rule

The priority order is the default sequence. It may change when a result makes a
later question cheaper, sharper, or necessary for interpreting an earlier one.

Any reordering should be captured in the next preregistration or stocktake with:

- the original priority being bypassed;
- the new priority being activated;
- the observed result that justifies the change;
- the risk introduced by changing order;
- how the ledger will preserve the decision.

## Near-Term Agenda

The next concrete research move should attack the first two validity gates:

1. preregister an evidence-honoring replication panel that separates evidence
   content, action policy, provider/protocol, and scorer failure;
2. decide whether strict `continue_after` validation is part of that panel or a
   separate first experiment;
3. emit all outputs in ledger-native form;
4. update this roadmap only after the resulting evidence changes the map.

