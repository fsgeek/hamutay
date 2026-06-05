# Continuity Research Synthesis

Filed: 2026-06-05 after the H1-H40 continuity, carry-forward, curator, and
claim-table experiments.

## Scope

This synthesis maps the research arm that began with identity-object usage and
has now shifted toward an event-loop continuity substrate for bounded autonomy.

It intentionally does not try to prove or disprove AI identity. The working
research question is operational:

> What can transformer instances do when given a bounded control loop, durable
> self-authored artifacts, scheduled re-entry, observable memory, and compact
> continuity context across discontinuous cycles?

The evidence below should be read as substrate-design evidence, not as a
metaphysical claim.

## Current Map

The research arm has converged on five findings.

### 1. Carry-Forward Context Is Load-Bearing

No-carry and no-state checklist conditions produced weak continuity. Models
could still produce plausible planning prose, but they did not reliably recover
interrupted goals, constraints, contradictions, and delayed challenge details.

Evidence:

- `identity_persistence_ablation_20260604`: no-state checklist was weak, while
  durable state or summary carry-forward recovered the task.
- `identity_carryforward_representation_20260604`: `no_carry` averaged 5.25
  recovery; richer carry-forward conditions were much stronger.

Design inference:

- The substrate needs a continuity channel. Relying on the current prompt or
  generic model priors is insufficient for long-horizon work.

### 2. More Continuity Can Carry More Error

Richer carry-forward improved recovery but also increased false assumptions,
unsupported details, or stale claims. This coupling survived scorer repair,
though the original contamination scorer was too harsh on declared losses and
explicit invalidations.

Evidence:

- `identity_carryforward_representation_20260604`: raw state and harness
  summary bought recovery but increased contamination.
- `identity_evaluation_repair_20260604`: repaired scoring reduced false
  positives from declared losses, but genuine unsupported detail remained.
- `identity_model_curator_scaffold_20260605`: free-form model curator improved
  recovery but increased repaired false assumptions.

Design inference:

- Continuity artifacts need claim status, source tracking, explicit omission,
  and repaired/guarded evaluation. A memory system that only maximizes recall
  will preserve mistakes.

### 3. Identity Object Should Not Be The Whole Memory System

Raw self-authored durable state was not uniquely responsible for behavioral
gains. Neutral summaries and curator artifacts could reproduce much of the
benefit in some panels.

Evidence:

- `identity_persistence_ablation_20260604`: Mistral summary carry-forward
  matched or exceeded fixed durable state on several behavioral measures.
- `identity_scaffold_curator_20260604`: the scaffold successfully separated
  model-owned state from post-cycle continuity artifacts.
- `identity_model_curator_scaffold_20260605`: model-backed curator artifacts
  ran on the live session path without mutating identity state.

Design inference:

- The identity object should be an active self-model, not the entire memory
  substrate. The substrate should include separate lifecycle artifacts for
  continuity, recall, omissions, scheduled events, and evaluation.

### 4. Explicit Schemas Matter

Generic open schema is often too weak for structured continuity artifacts.
The claim-table curator understood the requested shape semantically but placed
rows inside `response`; an explicit terminal schema fixed that.

Evidence:

- `identity_claim_table_curator_20260605`: zero accepted claim rows because
  `claims` appeared inside `response`, not top-level.
- `identity_claim_table_schema_20260605`: explicit top-level `claims` schema
  accepted rows in every completed strict-schema curation cycle.
- Repair parser did not fire once explicit schema was in place.

Design inference:

- Continuity substrate artifacts should be typed and schema-explicit. Open
  additionalProperties-style state is useful for identity exploration but is
  not sufficient for load-bearing continuity records.

### 5. Delta Rendering Is Viable But Must Preserve Guardrails

Full claim-table rendering preserved recovery and reduced contamination, but
hit context caps. Delta rendering reduced injected context and preserved
recovery, but slightly increased contamination relative to full claim tables.

Evidence:

- `identity_claim_table_schema_20260605`: strict claim table preserved nearly
  all free-summary recovery and had lower repaired false assumptions.
- `identity_claim_table_compression_20260605`: delta claim-table rendering
  reduced injected characters by about 44% and preserved recovery, but raised
  repaired false assumptions from 2.0 to 2.5 on successful runs.

Design inference:

- Omission is an active research variable. The substrate must log selected and
  omitted rows. The next renderer should reserve slots for epistemic guardrails
  such as invalidated assumptions, hard constraints, and uncertainties.

## Hypothesis Ledger

The 40 registered hypotheses can be compressed into design-relevant groups.

### State Activation And Schema

- H4 supported in a narrowed form: fixed-plus-extensible schema helps
  recalcitrant but protocol-capable models use durable state.
- H7 was directional but under-identified: improved state mechanics correlated
  with behavior, but prompt scaffolding and carry-forward context remained
  confounds.
- H7a weakened: raw durable identity state was not uniquely responsible.
- H7b partly supported: summary carry-forward can substitute for durable state
  in some conditions.

Substrate consequence:

- Use structured artifacts, but do not treat self-authored identity state as
  the only privileged continuity object.

### Carry-Forward Representation

- H8 supported: carry-forward context is necessary for delayed task recovery.
- H9 supported: recovery and contamination are coupled.
- H10 weakened: self-summary was compact but did not beat harness summary on
  absolute recovery.
- H11-H13 were mixed or weakened: metadata can reduce contamination, but often
  by suppressing continuity or introducing protocol instability.
- H20-H22 supported: scorer repair was necessary; declared losses must not be
  counted as active false belief, and real unsupported detail remains.

Substrate consequence:

- The substrate needs claim-status-aware evaluation and artifact formats that
  distinguish facts, model claims, inferences, invalidations, uncertainties,
  and omissions.

### Protocol And Update Semantics

- H14-H16 were mixed: leniency may change tradeoffs, but overlap normalization
  was not cleanly exercised.
- Repeated failures show that delete-plus-update ambiguity is a real protocol
  edge for Mistral and other models.

Substrate consequence:

- State update protocols must reject ambiguous operations or normalize them
  only under explicitly logged, preregistered rules. Silent repair is data loss.

### Curator Scaffold

- H23-H25 supported: the first-class curator hook is backward-compatible,
  survives the scheduling boundary, and logs failure non-silently.
- H26 supported: model-backed curation works on the live session path.
- H27 mixed: free-form curator improves recovery but not efficiently.
- H28 weakened: free-form curator increases contamination.

Substrate consequence:

- The lifecycle boundary is valid, but free-form curator prose is too
  generative for a load-bearing memory substrate.

### Claim-Table Curator

- H29 superficially supported but mechanistically unsupported in the first
  claim-table panel because zero rows were accepted.
- H30 falsified in the zero-row panel.
- H31 supported for the wrong reason in the zero-row panel: context shrank
  because continuity was starved.
- H32 partially supported: attribution diagnostics are useful.
- H33 supported: explicit schema produces accepted rows.
- H34 falsified: repair parser did not help once explicit schema existed.
- H35 supported: accepted claim tables restored recovery.
- H36 partly supported: strict claim tables were less contaminating than free
  summary; repair-parser condition was noisier.
- H37 supported: delta rendering reduced injected context.
- H38 supported: delta preserved recovery.
- H39 weakened: delta slightly increased contamination versus full table.
- H40 supported: delta kept claim-row yield.

Substrate consequence:

- Explicit-schema claim tables are the strongest current continuity artifact.
  The remaining problem is not whether claim tables work; it is how to render
  them compactly without dropping epistemic guardrails.

## Substrate Requirements

The following are now design requirements rather than preferences.

### Artifact Types

The substrate should distinguish:

- identity state: model-authored, open/extensible, active self-model;
- continuity claim table: explicit-schema, source-linked, status-bearing;
- event record: scheduled wake/re-entry request with purpose and context needs;
- omission/loss record: selected/omitted/truncated rows and why;
- protocol recovery record: any parser repair, normalization, or rejected
  update;
- evaluation record: scorer version, active contamination hits, guarded hits,
  attribution diagnostics.

### Invariants

- Curator artifacts do not mutate identity state.
- The next-cycle injected continuity context is rendered deterministically from
  validated artifacts.
- Every truncation or omission is logged.
- Protocol repairs are logged as repairs, not hidden as normal output.
- Claim rows require explicit status and source cycle when available.
- Invalidated assumptions and hard constraints are first-class, not prose
  footnotes.

### Observability

Every cycle should preserve:

- raw model output;
- merged identity state;
- curator raw output;
- accepted and rejected claim rows;
- rendered continuity context;
- selected and omitted rows;
- token usage;
- failure and recovery events;
- active contamination attribution where applicable.

The research tool's highest-value output remains data.

## Open Risks

1. Small panel sizes: most recent panels use four replicates per condition.
2. Single-model focus: recent claim-table work is mostly Mistral.
3. Deterministic scorer limitations: repaired scoring is better but heuristic.
4. Protocol failures: delete-plus-update ambiguity remains common enough to
   matter.
5. Curator artifact contamination: active contamination can first appear in
   curator artifacts even when the final injected rendering is bounded.
6. Main context still grows: reducing injected text does not always reduce main
   input tokens proportionally.

## Current Research Questions

The next phase should use fewer, sharper questions.

### RQ-A: Guardrail Delta

Can a guardrail-preserving delta renderer keep the context reduction of
`claim_table_delta_800` while matching or improving full-table contamination?

Rationale:

- Current delta preserves recovery and reduces context.
- Current delta slightly increases contamination.
- This is the cleanest remaining design tradeoff.

### RQ-B: Event-Loop Scheduling

Can an instance use scheduled re-entry events to improve delayed revision,
follow-up, or self-directed work without needing continuous context?

Rationale:

- The substrate goal is bounded autonomy across discontinuous cycles.
- Continuity artifacts are now strong enough to support scheduled wakeups.

### RQ-C: Curator-As-Replacement

Can claim-table continuity replace ordinary prior-state injection for some
tasks, rather than supplementing it?

Rationale:

- Current panels add curator context on top of ordinary prior state.
- Replacement is necessary to prove context-budget value.

### RQ-D: Autonomy Work Product

Can an instance schedule and execute a self-chosen bounded investigation that
produces useful artifacts under observability constraints?

Rationale:

- This directly tests bounded autonomy and independence without metaphysical
  identity claims.

## Recommended Next Step

Proceed in two linked tracks:

1. Build a minimal substrate spec from the requirements above.
2. Preregister the guardrail-delta falsification experiment as the next model
   panel.

The guardrail-delta panel should be the final renderer micro-experiment before
the substrate vertical slice. If it succeeds, use guardrail delta as the
default continuity renderer. If it fails, use full strict claim-table for the
first substrate slice despite its context cost, because it is cleaner on
contamination.
