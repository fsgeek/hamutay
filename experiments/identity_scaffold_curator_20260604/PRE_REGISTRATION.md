# Identity Scaffold Curator Pre-Registration

Filed: 2026-06-04 after evaluation repair and before modifying the scaffold.

## Research Question

Can the live `taste_open` scaffold represent continuity curation as a
first-class post-cycle lifecycle artifact without changing default behavior or
forcing the identity object to become the whole memory system?

Recent panels showed that a separate continuity curator can preserve useful
task memory with far less injected context and no truncation. The next scaffold
step is to promote that role from experiment-runner machinery into the session
control loop.

## Scope

This is an implementation/evaluation slice, not a new model panel.

The first scaffold change is deliberately small:

- add an optional `ContinuityCurator` hook to `OpenTasteSession`;
- after a successful cycle, call the curator with prior state, raw output,
  response text, merged state, and cycle metadata;
- durably log the curator artifact in the cycle JSONL record;
- inject the latest curator summary into the next cycle's system prompt as a
  bounded prior-context representation;
- preserve existing behavior exactly when no curator is configured.

No model-backed curator is added in this slice. Unit tests use a fake curator
so lifecycle behavior can be evaluated deterministically and cheaply. A
model-backed curator can be preregistered after the hook is stable.

## Hypotheses

### H23: Curator Hook Is Backward-Compatible

If the hook is correctly isolated, existing `taste_open` sessions without a
curator will produce the same messages/log schema aside from no new
curation-specific fields.

Prediction: existing tests continue to pass, and a session with no curator does
not inject a curator context block.

### H24: Curator Artifact Survives The Scheduling Boundary

If curation is a first-class lifecycle artifact, a curator summary created
after cycle N will be visible to cycle N+1 as a distinct context block.

Prediction: with a fake curator, cycle 2 system prompt includes the cycle 1
curator summary, and cycle 2 log records which curator record was injected.

### H25: Curator Failure Is Observable And Non-Silent

If the curator fails after the main model cycle succeeds, the failure should be
logged durably and should not silently create an empty "successful" curator
summary.

Prediction: fake-curator failure records a curation error in the cycle log and
does not inject a summary into the next cycle.

## Implementation Guardrails

- Do not alter `_apply_updates` semantics.
- Do not alter memory tool behavior.
- Do not alter scheduled event semantics.
- Do not add model calls.
- Do not overwrite prior experiment artifacts.
- Keep the curator summary as context, not as an automatic state mutation.
- Log enough provenance to distinguish model output, merged state, and curator
  artifact.

## Acceptance Tests

Add or update unit tests to verify:

1. no-curator sessions do not include curator context;
2. fake-curator output is logged after a successful cycle;
3. fake-curator output is injected into the next cycle;
4. curator failure is logged and not injected;
5. existing schedule-event behavior still commits pending events after success.

## Interpretation Guardrails

Passing this slice does not prove that continuity curation improves model
behavior in live sessions. It only proves that the scaffold can represent the
curator role cleanly and observably.

The next model panel, if any, must be preregistered separately and scored with
the repaired evaluator.
