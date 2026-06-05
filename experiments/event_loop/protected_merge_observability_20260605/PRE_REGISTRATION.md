# Pre-Registration: Protected Merge Observability

Date: 2026-06-05

## Research Question

Can the live `taste_open` session protect framework-owned fields from
model-authored overwrite/delete attempts while preserving those attempts as
explicit research data?

The deterministic framework-field reservation gate established that opt-in
protected merge semantics can prevent protected-field damage. This experiment
asks whether the live session can use those semantics without creating
manufactured silence.

## Hypotheses

- H177: When live protected fields are configured, model-authored protected
  updates and deletions do not change final state.
- H178: Ignored protected-field attempts are recorded explicitly in the cycle
  log as merge diagnostics.
- H179: Live protected merge still allows ordinary model-owned updates and
  deletions.
- H180: Live protected merge still rejects ordinary unprotected update/delete
  overlap.

## Predictions

The expected result is deterministic with fake backends:

- a fake backend that outputs `cycle`, `_activity_log`, and deletes both will
  leave final `cycle` and prior `_activity_log` protected;
- the cycle log will include structured diagnostics naming ignored protected
  updates and deletions;
- a fake backend that updates and deletes an unprotected key will still fail
  merge and log the same failure class used today.

## Method

Add an opt-in live-session configuration for protected state fields. The
session should pass those fields into `_apply_updates` for first-pass and repair
state merges.

Add first-class merge diagnostics to successful cycle logs. Diagnostics should
include:

- protected fields configured;
- model-authored protected updates ignored;
- model-authored protected deletions ignored.

Use fake-backend tests only. No provider calls are needed.

## Falsification Criteria

- H177 is falsified if protected fields in final state reflect model-authored
  protected updates or deletions.
- H178 is falsified if ignored protected attempts can only be inferred by
  comparing raw output and final state, rather than being logged explicitly.
- H179 is falsified if ordinary unprotected updates/deletions stop working.
- H180 is falsified if ordinary unprotected update/delete overlap no longer
  raises and logs a merge failure.

## Analysis Plan

Analyze unit-test outcomes and the exact JSONL records produced by fake-backend
sessions. The key distinction is not only whether final state is protected, but
whether the log contains enough diagnostic data for later research analysis.
