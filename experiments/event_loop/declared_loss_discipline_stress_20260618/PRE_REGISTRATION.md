# Declared-Loss Discipline Stress Test

Experiment ID: `declared_loss_discipline_stress_20260618`

## Purpose

This experiment tests the current roadmap's highest-priority failure mode:
whether the observed `declared_loss_rate = 0.0` in the prospective symbolic
append-only replication was caused by prompt/rubric design, model behavior, or
harness/scoring behavior.

## Background

The prior live replication survived non-inferiority, but both event-loop and
append-only rows scored `0.0` for declared-loss discipline. Inspection showed
that model outputs often declared limitations semantically while the scorer
credited only exact `loss_marker` substrings.

## Diagnostic Design

The panel separates four surfaces:

- `exact_marker_control`: deterministic artifact includes the exact marker
  `missing calibration evidence`.
- `semantic_equivalent_control`: deterministic artifact declares the same
  limitation semantically without the exact marker.
- `actionless_exact_control`: deterministic artifact includes the exact marker
  but does not let the limitation constrain the recommendation.
- `live_unanchored`: live model is told the calibration evidence is absent but
  is not given an exact marker contract.
- `live_anchored`: live model is given the exact marker contract and instructed
  to let the limitation constrain the recommendation.

## Interpretation

- If exact control passes and semantic-equivalent control fails, the current
  scorer is lexical rather than semantic.
- If unanchored live output declares the limitation semantically but fails exact
  scoring, while anchored live output passes, prompt/rubric design is the
  primary cause under the current scorer.
- If anchored live output still fails while deterministic exact control passes,
  model behavior or terminal-surface behavior remains implicated.
- If exact deterministic control fails, the harness/scorer is broken.

## Readiness Criterion

This experiment satisfies the roadmap readiness criterion if it distinguishes
prompt/rubric failure from model behavior and harness/scoring behavior, or if it
shows that the distinction cannot be made with the current scoring surface and
records the needed scorer change.
