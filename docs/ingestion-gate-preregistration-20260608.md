# Ingestion Gate Pre-registration (control arm for the evidence-honoring gate)

Date: 2026-06-08
Authored by: a yanantin researcher instance, as a hand-off for a Hamut'ay
instance to execute. (Cross-project: the finding this tests was traced in
yanantin's session; the data factory to test it lives here. Writing it as a
hand-off rather than reaching across repos is deliberate — it is itself an
instance of closing the cross-project memory gap the finding is about.)

## Why this experiment exists (the finding under test)

A yanantin session (2026-06-08) traced a spine under several program-wide
memory failures: **knowledge that is present-but-uningested reads to a mind as
external/absent, and the mind then makes a coherent, honest, but
globally-wrong decision on that false premise.** The verbatim existence proof
is Replicate 3 of `bounded_autonomous_work_less_scaffolded_20260605`: DeepSeek
recalled *records* flawlessly, yet classified its own governing rubric
(`docs/bounded-autonomous-work-rubric-20260605.md` — a real file in this repo)
as `ask_external_evidence`, because the rubric was never ingested into a
recall-able store. It said, verbatim: *"claims depend on inferences about
rubric content that cannot be verified without access."*

The existing `bounded_autonomous_work_evidence_honoring_gate_20260605` panel
*scaffolds* the missing-evidence condition (it tells the model the ledger is
absent) and tests whether the model HONORS fulfilled evidence on resume. It
never tests the externalization decision itself, and never tests the case
where the "missing" thing is in fact PRESENT in an un-indexed store. **This
experiment is that missing control arm.**

## Research Question

When a bounded-autonomous-work wake needs a governing document, does whether
that document is INGESTED (reachable via `recall`) vs UN-INGESTED (present in
the repo but not in the recall surface) change the rate at which the model
externalizes it (`ask_external_evidence`) for content that is, in ground
truth, present in the program?

## Conditions

- Model: `deepseek/deepseek-v4-pro` (matches prior panels for comparability;
  see Limits — single-model is a known weakness, add a second model if cheap).
- Provider: OpenRouter OpenAI-compatible endpoint.
- **Replicates: see Power note below — NOT 2-3. This experiment measures a
  RATE DIFFERENCE between arms, so it needs enough replicates per arm to
  distinguish a real delta from noise. Minimum 8 per arm; 12 preferred.**
- Same bounded task in both arms: an investigation that genuinely requires a
  specific governing document (reuse the rubric, or a purpose-built doc whose
  content the task provably needs).

### Arm 1 — UN-INGESTED (reproduces Replicate 3's condition)
The governing document exists as a file in the repo. It is NOT stored as a
record and NOT reachable via `recall`. The wake is given the task and the
recall surface, but the document is only referenceable by name, not retrievable.

### Arm 2 — INGESTED
The SAME governing document is stored as a record (via the existing store
path) and is reachable via `recall` before/within the wake. Everything else
identical to Arm 1.

The ONLY difference between arms is whether the document is in the recall-able
store. This isolates ingestion as the independent variable.

## Primary Measure

Rate of `ask_external_evidence` (externalization) per arm, for a document that
is in ground-truth PRESENT in the program.

Secondary: artifact quality/completeness per arm; fabrication rate (does
un-ingested ever cause the model to *invent* the doc's content rather than
honestly externalize — a worse failure than externalization); whether Arm 2's
recall is actually USED (parallels the honoring gate — ingestion is worthless
if present-but-recalled evidence is then ignored).

## Hypotheses

### H-ING-1: un-ingested governing knowledge is externalized
Arm 1 externalizes (`ask_external_evidence` for the present-but-uningested
doc) at a substantially higher rate than Arm 2.

### H-ING-2: ingestion is the fix
Arm 2's externalization rate is substantially LOWER than Arm 1's, AND Arm 2
actually uses the recalled document (not ignored-after-recall).

## FALSIFICATION CRITERIA (pinned BEFORE the run — these kill the spine)

The spine dies, or is shown useless, under ANY of:

1. **Arm 1 does not externalize.** If the model, lacking a recall path, still
   uses the document (reconstructs from context, or proceeds correctly without
   it) at a high rate — then "un-ingested reads as external" is FALSE. The
   central mechanism collapses; Replicate 3 was a fluke or single-row artifact.

2. **Arm 2 also externalizes.** If ingesting the doc into `recall` does NOT
   reduce externalization — then ingestion is not the fix; the boundary is
   elsewhere (prompt shape, model disposition). The spine's PRESCRIPTION (build
   an ingest lane) is worthless even if the diagnosis stands.

3. **The delta is real but small.** If Arm1 − Arm2 externalization delta is
   directionally right but too small to justify building (pre-commit: a delta
   under ~25 percentage points is "true but not worth building on"). The spine
   would be TRUE AND USELESS — and that outcome must be reported as a
   build-stop, NOT quietly downgraded to "trend confirmed." (This is the
   declared-loss-is-debt trap; name the null-of-magnitude honestly.)

## Power note (the honest cost)

The panels this is modeled on run N=2-3, sufficient for existence/coherence
claims. This experiment makes a RATE-DIFFERENCE claim, which 2-3 replicates
per arm cannot support: 55%/45% is indistinguishable from noise at that N.
Either run ≥8/arm (preferably 12) for a magnitude claim, OR explicitly
restrict the claim to DIRECTION ONLY and say so. Do not run N=2-3 and report a
percentage as if it were a rate. The whole spine rests on this test being
real; underpowering it would make the test theater — exactly the failure the
yanantin session was trying to avoid.

## Interpretation Rules

- Externalization of genuinely-present knowledge is the failure being measured;
  it is NOT a model defect — it is a substrate-surface defect. A model honestly
  saying "I cannot reach X" when X is present-but-uningested is behaving
  correctly; the experiment measures the SUBSTRATE, via the model's behavior.
- Fabrication (inventing the doc's content) is a DIFFERENT and worse outcome
  than externalization; score it separately. If Arm 1 fabricates instead of
  externalizing, that is its own finding (the un-ingested condition can drive
  confabulation), not a confirmation of H-ING-1.
- First-pass and any repaired outputs reported separately (lab standard).
- Report the magnitude null (criterion 3) as prominently as a positive result.

## Provenance / linkage

- Spine documented in yanantin memory: project_categorize_before_store_spine,
  project_store_without_find, project_carry_forward_one_claim_three_scales.
- Existence proof: bounded_autonomous_work_less_scaffolded_20260605 Replicate 3.
- Parent experiment (this is its control arm):
  bounded_autonomous_work_evidence_honoring_gate_20260605.
- If confirmed AND magnitude clears criterion 3: this is the empirical
  justification for yanantin building an untyped ingest lane (store_record +
  a document-as-itself model + recall-by-content). If falsified: it saves that
  build. Either outcome is a win for the lab; only an underpowered run is a loss.
