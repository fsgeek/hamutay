# Pre-Registration: Initialization Taxonomy Audit

Date: 2026-06-05

## Research Question

Do the existing event-loop experiment artifacts contain enough initialization
evidence to separate comparable scheduler runs from censored or repaired
initialization runs?

The recent repaired-initialization scheduler integration showed that a failed
initialization can be recovered and used downstream when its provenance remains
visible. That result creates a retrospective data-hygiene question: prior
event-loop panels should not be pooled as if initialization were a uniform
condition unless the artifacts support that claim.

## Hypotheses

- H241: Existing event-loop artifacts contain enough evidence to classify most
  scheduler-relevant rows into initialization provenance classes.
- H242: The corpus contains at least three empirically observed initialization
  classes: first-pass valid, failed/culled, and repaired-valid.
- H243: Some prior scheduler results are materially censored by initialization
  failure and therefore should be scored over valid or repaired initialization
  populations, not all attempted replicates.
- H244: Some older or deterministic scaffold artifacts remain unclassifiable
  because their schemas do not preserve row-level initialization evidence.
- H245: A reusable machine-readable manifest can be generated without model
  calls and without inferring missing evidence.

## Method

Run a deterministic local audit over `experiments/event_loop/*/results.json`.

For every row-like result, record:

- experiment name;
- result index and replicate/model if present;
- result schema root shape;
- available initialization, repair, validation, scheduler, and wake evidence;
- initialization provenance class;
- evidence fields used for classification.

Classification is evidence-based:

- `first_pass_valid`: explicit first-pass initialization validity evidence.
- `repaired_valid`: explicit initialization repair evidence with valid repair.
- `failed_or_culled`: explicit failed initialization evidence.
- `valid_legacy`: legacy `init_valid == true` without first-pass/repair
  provenance.
- `not_scheduler_scored`: deterministic or side experiment row with no
  scheduler initialization surface.
- `unclassifiable`: scheduler-relevant or row-shaped artifact lacking enough
  evidence to assign an initialization class.
- `malformed_or_aggregate`: result files whose root shape lacks row-level
  `results` data.

The audit may inspect only result JSON and directly referenced log paths for
existence checks. It must not reinterpret model prose to manufacture missing
state evidence.

## Predictions

The audit should show that the event-loop arm has not run out of questions:
the next question is now comparability and censoring, not simply whether a
model can schedule a wake.

Expected pattern:

- newer strict scheduler panels preserve enough initialization evidence for
  valid/failed/repaired classification;
- repaired-initialization runs form a distinct provenance class;
- earlier panels have weaker schema evidence and require cautious comparison;
- deterministic DES/projection artifacts are useful for scaffold design but
  should not be pooled with live scheduler-scoring panels.

## Falsification Criteria

- H241 is falsified if fewer than half of scheduler-relevant rows can be
  classified without inference.
- H242 is falsified if the audit finds fewer than three initialization
  provenance classes.
- H243 is falsified if no scheduler-relevant panel has initialization failures
  or repaired-initialization rows that change the scored population.
- H244 is falsified if every artifact is classifiable with row-level evidence.
- H245 is falsified if the manifest requires model calls, manual prose
  interpretation, or unverifiable assumptions.

## Analysis Plan

Report:

- row counts by initialization class;
- experiment counts by dominant class;
- scheduler-relevant row counts by class;
- files with aggregate/malformed or missing row-level schemas;
- panels where all-attempt scoring differs from initialization-qualified
  scoring;
- recommended comparison policy for future event-loop experiments.

Interpretation will be conservative. Missing evidence is data debt, not proof
of success or failure.
