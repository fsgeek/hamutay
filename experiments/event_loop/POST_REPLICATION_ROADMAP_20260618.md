# Post-Replication Event-Loop Roadmap

Date: 2026-06-18

## Purpose

This artifact preserves the current roadmap after the committed prospective live
replication of symbolic event-loop append-only non-inferiority. It is intended
to be referenced by future goals so the thread does not rely on in-context
memory alone.

## Evidence Anchor

Prospective protocol:

- Commit: `156dc71` (`Preregister symbolic append-only replication`)
- Experiment: `event_loop_symbolic_append_only_noninferiority_20260618`
- Symbolic contract: `framework_bound_symbolic_continuation.v1`

Live evidence:

- Commit: `1060849` (`Record symbolic append-only live replication`)
- Result directory:
  `experiments/event_loop/event_loop_symbolic_append_only_noninferiority_20260618_direct_deepseek`
- Endpoint: direct DeepSeek, `https://api.deepseek.com`
- Model: `deepseek-v4-pro`
- Classification: `survived`
- Event-loop mean artifact quality: `0.85`
- Append-only mean artifact quality: `0.85`
- Shared-surface observability: event-loop `1.0`, append-only `1.0`
- Scheduler reconstruction added value: `1.0`

Important caveat: declared-loss rate was `0.0` across both conditions. The
replication supports non-inferiority under the committed scoring rule, but it
does not show that either condition handled declared-loss discipline well.

## Ordering Principle

Prefer experiments that maximize information gain while preserving failure
attribution clarity. Do not add broad degrees of freedom before isolating the
clearest known weakness.

In short:

1. Reduce ambiguity in the measurement surface.
2. Then raise the comparison bar.
3. Then lengthen the loop.
4. Then add concurrency and operational recovery.
5. Then generalize across providers.

## Current Priority

Current roadmap state: `harder_append_only_baseline_next`.

Next execution target:

> Build and run a harder append-only baseline test that determines whether
> symbolic event-loop non-inferiority survives against a stronger one-shot
> condition, while preserving the declared-loss measurement policy below.

Reason this is now first: the declared-loss discipline stress test satisfied
the readiness criterion for moving on. It showed that exact-marker scoring is
lexical, that the model can comply when the exact loss contract is explicit,
and that the prior `declared_loss_rate = 0.0` is best attributed to
prompt/rubric design under the current scorer, with a scorer caveat.

Measurement policy carried forward:

- future exact declared-loss scores require an explicit exact-marker contract in
  the prompt/rubric; or
- a future experiment must preregister a semantic declared-loss scorer before
  using semantic loss declarations as scored evidence.

Readiness criteria for moving to the third roadmap item:

- the harder append-only baseline test establishes whether event-loop
  non-inferiority survives, narrows, or fails against the stronger baseline; and
- any failure is attributable to artifact quality, declared-loss discipline,
  prompt/rubric design, provider behavior, or scheduler behavior without using
  scheduler observability to rescue the shared-surface comparison.

## Roadmap

### 1. Declared-Loss Discipline Stress Test

Rationale: This is the clearest weakness exposed by the prospective
replication. Both conditions survived, but both failed declared-loss discipline
under the current scorer. A narrow stress test should determine whether the
failure is caused by prompt/rubric design, model behavior, or harness/scoring
behavior.

Expected output: an experiment that makes loss declaration unavoidable and
checks whether the loss materially changes the recommendation.

Status: complete. Result:
`experiments/event_loop/declared_loss_discipline_stress_20260618_direct_deepseek`.
Classification: `prompt_rubric_primary_with_lexical_scorer_caveat`. The model
declared the limitation semantically in the unanchored live row but did not
receive exact-marker credit; it passed exact-marker scoring when the prompt
included the exact declared-loss contract.

### 2. Harder Append-Only Baseline

Rationale: The current append-only bar may be too low. Hardening the baseline
before resolving declared-loss scoring would confound failures, so this comes
second.

Expected output: a stricter append-only baseline prompt, rubric, or task set
that tests whether event-loop non-inferiority survives against a stronger
one-shot condition.

### 3. Longer-Horizon Sustained Loop

Rationale: This is strategically central to the event-loop thesis, but it has
more moving parts. It should follow cleaner measurement and baseline surfaces.

Expected output: a sustained single-entity loop with inbound work,
self-scheduled continuation, housekeeping, restart frontier updates, and final
artifact synthesis across more than one task.

### 4. Multi-Entity Event Loop

Rationale: Multi-entity scheduling adds identity, isolation, attribution, and
fairness concerns. These are valuable only after a single-entity sustained loop
is credible.

Expected output: a panel with multiple AI entities or workstreams and explicit
checks for identity drift, context contamination, and attribution errors.

### 5. Restart/Resume Under Interruption

Rationale: Existing restart-frontier evidence is structural. A stronger test
should deliberately interrupt and resume a nontrivial loop.

Expected output: a run that interrupts mid-execution and resumes from committed
artifacts without losing scheduler identity, carried state, or failure
attribution.

### 6. Provider Variance Panel

Rationale: Provider differences are real, but broad provider comparison is less
useful before the task and scoring surfaces are sharper.

Expected output: a small provider panel that distinguishes framework robustness
from provider-specific terminal-surface behavior.

## Recommended Roadmap Goal

Maintain and refine the post-replication roadmap for event-loop viability:
prioritize experiments by information gain and attribution clarity, starting
with declared-loss discipline, then harder append-only baseline, longer-horizon
sustained loop, multi-entity scheduling, restart/resume interruption, and
provider variance.

## Recommended Next Execution Goal

Build and run a harder append-only baseline test that determines whether
symbolic event-loop non-inferiority survives against a stronger one-shot
condition, while preserving the declared-loss measurement policy from this
roadmap.

## Decision Log

- 2026-06-18: Created roadmap after prospective symbolic append-only
  replication survived. Ranked declared-loss discipline first because it is the
  clearest observed weakness and can be isolated without adding sustained-loop,
  multi-entity, restart, or provider-panel degrees of freedom.
- 2026-06-18: Refined roadmap with explicit current priority and readiness
  criteria so future goals can target this artifact directly.
- 2026-06-18: Completed declared-loss discipline stress test. Deterministic
  controls showed exact-marker scoring is lexical: exact marker passed,
  semantic-equivalent loss declaration failed exact scoring, and an exact marker
  without a constrained recommendation was not materially disciplined. Live
  direct-DeepSeek rows showed the model can comply when the exact marker is
  explicit. Moved current priority to harder append-only baseline.

## Update Discipline

When the roadmap changes, update this file with:

- the new ordering;
- the rationale for the change;
- the evidence that caused the change;
- whether the change affects the roadmap goal, the next execution goal, or both.
