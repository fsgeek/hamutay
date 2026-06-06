# Hypothesis Ledger Goal Framework

Date: 2026-06-05

## Goal

Build a project-level hypothesis ledger that makes the existing Hamut'ay
research corpus findable, attributable, and status-classified without
overstating certainty.

## Objective

Create a durable hypothesis map for the project by extracting hypotheses,
predictions, outcomes, confounds, and evidence links from existing experiment
artifacts, assigning conservative statuses, and identifying which findings are
survived, falsified, boundary-limited, contaminated, unscoreable, superseded,
deferred, or still unknown.

## Rationale

Uncatalogued research work is unlikely to remain useful. Findings buried in
prose, raw traces, or inconsistent result schemas will not improve with age.
The purpose of the ledger is not to make old experiments cleaner than they
were; it is to make the claims findable, attributable, and honestly
classified.

The work should therefore be treated as research corpus normalization for
evidence retrieval and falsification planning, not as a proof exercise or a
polishing pass.

## Success Criteria

- Every extracted hypothesis has a stable ID or source-local ID.
- Every entry points to its source artifact and, where available, result
  evidence.
- Status is conservative rather than forced.
- Messy or old work is catalogued, not discarded.
- The ledger distinguishes claim status from model, provider, protocol,
  substrate, and scorer limitations.
- The first pass includes enough automated extraction to scale beyond manual
  notes.
- The summary identifies the current project map: what survived, what was
  falsified, what is boundary-limited, what is contaminated or unscoreable, and
  where the gaps remain.

## Suggested Status Vocabulary

- `survived`: preregistered or clearly stated hypothesis survived the recorded
  falsification attempt.
- `falsified`: hypothesis failed under the recorded falsification attempt.
- `boundary`: result is meaningful but limited by model, provider, protocol,
  substrate, scorer, sample size, or scope.
- `deferred`: hypothesis or test was explicitly postponed.
- `contaminated`: prompt leak, scoring defect, harness defect, or other
  contamination prevents using the row as clean evidence.
- `unscoreable`: trace or result evidence is insufficient for classification.
- `superseded`: later experiment or corrected methodology replaces the earlier
  interpretation.
- `unknown`: hypothesis is identifiable but no reliable outcome is currently
  available.

## Non-Goals

- Do not delete messy or failed work.
- Do not force every hypothesis into `survived` or `falsified`.
- Do not treat normalization as proof that the project has established a broad
  claim.
- Do not flatten materially different failure causes into one generic failure
  category.
- Do not rely on memory when source artifacts exist.

## Initial Inputs

- `experiments/**/results.json`
- `experiments/**/PRE_REGISTRATION.md`
- `experiments/**/analysis.md`
- relevant JSONL traces where result summaries are insufficient
- `docs/*stocktake*.md`
- `docs/paper-evidence-ledger.md`

## Proposed Deliverables

- machine-readable ledger, likely `docs/hypothesis-ledger-20260605.jsonl`
- human-readable stocktake, likely
  `docs/hypothesis-ledger-stocktake-20260605.md`
- extraction script or notebook sufficient to repeat the first-pass ingestion
- audit notes describing schema gaps, ambiguous entries, and sampling checks
