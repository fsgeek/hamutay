# Pre-Registration: Framework Field Reservation

Date: 2026-06-05

## Research Question

Should event-loop continuity rely only on validators that detect model damage
after the fact, or should the substrate make selected framework-owned fields
non-authorable by model output?

The strict scheduled-walk continuity gate showed that validator-guided repair
can restore continuity fields, but it also showed model output deleting
`_activity_log` and earlier runs showed `cycle` could be overwritten or
deleted. This experiment asks whether a minimal hard-reservation layer can
prevent that class of damage without changing the existing update/delete
semantics for model-owned fields.

## Hypotheses

- H173: With protected fields disabled, the current merge semantics permit
  model output to overwrite or delete `cycle`.
- H174: With protected fields enabled, model output cannot overwrite or delete
  protected fields such as `cycle` and `_activity_log`.
- H175: Protected-field reservation does not weaken the existing strict
  overlap rejection for unprotected model-owned fields.
- H176: Protected-field reservation does not block ordinary model-owned updates
  or deletions.

## Predictions

The expected result is deterministic:

- unprotected `_apply_updates` will continue to show the prior permissive
  behavior;
- protected `_apply_updates` will preserve framework-owned values even when
  model output tries to update or delete them;
- unprotected overlap such as updating and deleting `mood` in the same cycle
  will still raise;
- ordinary model-owned state changes will still work.

## Method

Implement a minimal opt-in reservation mechanism for the `taste_open`
state-merge helper. The mechanism must not require provider calls.

Synthetic falsification tests will exercise:

- model overwrite of `cycle`;
- model deletion of `cycle`;
- model overwrite and deletion of `_activity_log`;
- ordinary model update and deletion under protection;
- unprotected update/delete overlap under protection.

The hard-reservation layer must ignore protected-field model updates and
deletions rather than repairing them afterward. The harness must still set the
current framework `cycle` itself.

## Falsification Criteria

- H173 is falsified if current unprotected semantics do not permit `cycle`
  overwrite/delete.
- H174 is falsified if protected merge output reflects model-authored protected
  field updates or deletions.
- H175 is falsified if protected merge accepts update/delete overlap for an
  unprotected field.
- H176 is falsified if protected merge blocks ordinary unprotected field update
  or deletion.

## Analysis Plan

This is a deterministic scaffold experiment. Analyze by test result and by the
exact before/after merge states. No provider calls are needed.

If reservation passes, the next live scheduled-wake experiment should enable
the reservation layer for framework-owned fields and measure whether validators
still see fewer continuity failures while retaining first-pass evidence
failures as data.
