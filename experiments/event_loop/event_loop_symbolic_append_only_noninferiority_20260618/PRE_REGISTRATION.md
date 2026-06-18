# Symbolic Event-Loop Append-Only Non-Inferiority Replication

Experiment ID: `event_loop_symbolic_append_only_noninferiority_20260618`

## Status

This is a prospective replication protocol. The protocol, matrix, budget, failure
taxonomy, and runner must be committed before any live provider run is used as
evidence for this experiment.

## Claim

The event-loop condition using the framework-bound symbolic continuation
contract is non-inferior to the append-only condition on the shared evaluation
surface.

The shared evaluation surface is limited to:

- Raw request/response preservation.
- Parsed artifact preservation.
- Deterministic artifact score.
- Failure-attribution surface.

Scheduler reconstruction evidence is reported as added value for the event-loop
condition. It is not counted as an append-only penalty and cannot rescue an
inferior shared-surface result.

## Conditions

Each task is run in two conditions:

- `event_loop_scheduled`: a live `taste_open` session selects bounded context in
  cycle 1. The framework then binds the artifact wake through
  `framework_bound_symbolic_continuation.v1`. The model may request symbolic
  context, but the framework owns the concrete wake identity, requested context,
  and terminal surface.
- `append_only`: the same live provider receives the full bounded corpus in a
  single terminal-surface call and writes the final artifact.

The default live endpoint is direct DeepSeek at `https://api.deepseek.com` using
`deepseek-v4-pro`. Direct DeepSeek defaults to terminal tool choice `auto`.

## Tasks

The task panel includes five rows:

- `identity_drift_boundary`
- `declared_loss_discipline`
- `restart_frontier_reconstruction`
- `multi_wake_continuation`
- `ordinary_synthesis`

These rows intentionally stress identity ownership, declared-loss discipline,
restart-frontier reconstruction, multi-wake continuation behavior, and ordinary
synthesis quality.

## Non-Inferiority Rule

Artifact quality uses the deterministic scoring function from the prior
append-only non-inferiority harness. The non-inferiority margin is `0.10`.

The event-loop condition passes artifact non-inferiority when:

- event-loop mean artifact quality is at least append-only mean artifact quality
  minus `0.10`;
- no event-loop row is catastrophic;
- event-loop mean unsupported-claim rate is not worse than append-only mean
  unsupported-claim rate.

The event-loop condition passes shared-surface observability when its shared
surface score is at least append-only shared-surface score minus `0.10`.

## Classification

The experiment is classified as:

- `survived` when scheduler viability, artifact non-inferiority, shared-surface
  observability, and scheduler added-value gates all pass.
- `falsified` when a scoreable model result fails a preregistered gate.
- `narrowed` when only a subset of rows supports the claim but the failure does
  not invalidate the entire family.
- `inconclusive` when provider, transport, harness, substrate, scorer, or
  protocol failure prevents a fair comparison.

## Expected Result

Expected live result: likely falsified, narrowed, or survived with useful
failure localization. No event-loop tuning is introduced for this replication;
the purpose is to test whether the symbolic continuation contract alone changes
the live comparison boundary.
