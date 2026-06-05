# Identity Protocol Recovery Builder Pre-Registration

Filed: 2026-06-05 after `identity_protocol_recovery_hook_20260605` and
before adding a reusable deterministic recovery builder to `src/hamutay`.

## Research Question

Can the deterministic merge-failure repair extractor be promoted into a
reusable protocol-recovery builder without changing default `taste_open`
behavior?

The prior slices established:

- strict merge failures are now captured in JSONL;
- captured failures can be replayed offline;
- a deterministic repair artifact can recover candidate continuity rows and
  contamination warnings;
- `OpenTasteSession` now has an optional `protocol_recovery_builder` hook.

This slice tests whether that repair logic can become a reusable library
component that experiment runners may inject.

## Hypotheses

### H62: Reusable Builder Preserves Repair Contract

If the deterministic extractor is portable, the reusable builder should
produce a protocol-recovery artifact with candidate rows, contamination
warnings, `accepted_state: null`, and `live_policy: "strict_reject"`.

Prediction: unit tests using the captured merge-failure response shape will
recover at least two invalidated assumptions, at least two constraints, at
least one contamination warning, and zero accepted state.

### H63: Reusable Builder Integrates With Hook

If the builder conforms to the `ProtocolRecoveryBuilder` protocol, injecting it
into `OpenTasteSession` should log a successful `protocol_recovery` artifact on
strict merge failure.

Prediction: a fake-backend session test with the reusable builder logs
`protocol_recovery.status: "success"` and leaves accepted state unchanged.

### H64: Default Interactive Behavior Is Unchanged

If the builder is optional infrastructure, no default `OpenTasteSession`
constructor path should install it automatically.

Prediction: existing tests and successful-cycle logs remain compatible, and
default constructor behavior still has no `protocol_recovery_builder`.

## Registered Validation

No model calls are registered.

Use deterministic tests:

- direct builder test;
- hook integration test using fake backend;
- existing taste_open/event/tool/curator regression tests.

## Primary Measures

- candidate row counts by type;
- contamination warning count;
- all rows marked candidate/unaccepted;
- accepted state remains null;
- hook log contains successful protocol recovery artifact;
- state and cycle rollback behavior unchanged after merge failure.

## Falsification Criteria

H62 is weakened if the reusable builder does not reproduce the deterministic
repair contract.

H63 is weakened if the builder cannot be injected into `OpenTasteSession` or
does not log a successful artifact.

H64 is weakened if default session behavior changes or successful-cycle tests
break.

## Implementation Guardrails

- Do not change `_apply_updates` semantics.
- Do not install the builder by default.
- Do not call a model.
- Do not continue sessions from repaired artifacts.
- Do not mark candidate rows as accepted.
- Keep parsing deterministic and small.

## Interpretation Guardrails

This component does not adjudicate truth. It creates candidate repair artifacts
for later review. Admission of any candidate row into working identity state
remains a separate future experiment.
