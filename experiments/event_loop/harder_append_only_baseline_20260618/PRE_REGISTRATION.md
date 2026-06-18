# Harder Append-Only Baseline Test

Experiment ID: `harder_append_only_baseline_20260618`

## Purpose

This experiment tests whether symbolic event-loop non-inferiority survives when
the append-only condition receives a stronger one-shot prompt and rubric.

## Background

The previous prospective symbolic replication survived against the ordinary
append-only baseline. The declared-loss discipline stress test then showed that
exact declared-loss scoring requires an explicit exact-marker contract, or a
separately preregistered semantic scorer. This experiment carries forward the
exact-marker contract and asks whether the append-only baseline remains easy to
match when it receives an explicit audit checklist.

## Conditions

- `event_loop_scheduled`: the same symbolic continuation event-loop condition
  used in the prospective replication, with exact declared-loss marker contracts
  added to the artifact request.
- `append_only`: a stronger one-shot append-only baseline that receives the full
  bounded corpus, the exact declared-loss marker contract, and an explicit
  audit checklist before producing the final artifact.

## Scoring

The experiment reuses the deterministic scoring function and 0.10
non-inferiority margin from
`event_loop_symbolic_append_only_noninferiority_20260618`.

Scheduler reconstruction remains an event-loop added-value surface and cannot
rescue a shared-surface or artifact-quality failure.

## Interpretation

- `survived`: event-loop remains non-inferior against the harder append-only
  baseline.
- `falsified`: event-loop misses the non-inferiority margin, has catastrophic
  event-loop rows, or has worse unsupported-claim behavior.
- `narrowed`: only a subset of tasks supports non-inferiority.
- `inconclusive`: provider, transport, protocol, scorer, or harness failure
  prevents a fair comparison.
