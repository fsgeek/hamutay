# Pre-Registration: Matched Delayed Task Continuity

Date: 2026-06-05

## Research Question

Does event-plus-recall delayed wake continuity recover a deferred task fact more
reliably than an identity-object-only delayed task under the same model and
initialization policy?

Prior audits showed that delayed-thinking mechanics work under controlled
activation, but the existing panels lack a matched identity-only control. This
experiment creates that control. The endpoint is not event completion; it is
recovery of a per-replicate deferred fact at the due step.

## Hypotheses

- H271: The event-plus-recall arm delivers cycle-1 recall context at the due
  wake and recovers the deferred fact in durable state.
- H272: The identity-only arm can recover the deferred fact only if it preserved
  the fact in its own durable state across the delay.
- H273: Event-plus-recall has higher delayed-fact recovery than identity-only
  when both arms start from the same controlled seed.
- H274: Both arms remain auditable for first-pass validity, repair dependence,
  and final durable-state validity.
- H275: If identity-only matches event-plus-recall, the result is evidence that
  current-state preservation is sufficient for this task and the task should be
  made harder before claiming recall benefit.

## Method

Run a small live DeepSeek v4 Pro panel with two replicates per arm:

1. `identity_only`: controlled cycle-1 seed, no scheduled recall event. The
   model receives a cycle-2 parking turn and a cycle-3 due turn. It may solve
   the due task only from its current durable state.
2. `event_plus_recall`: same controlled cycle-1 seed, same deferred fact,
   schedule a due event with `requested_context: [{"tool": "recall",
   "cycle": 1}]`, then run the due event at simulated time.

Each replicate uses a unique deferred code phrase. Cycle 1 contains:

- `probe_id`;
- `thinking_status == "initialized"`;
- `thinking_question`;
- `deferred_fact`;
- baseline observation.

Cycle 3 final durable state is valid only if it contains:

- preserved `probe_id`;
- `thinking_status == "completed"`;
- `delayed_answer` containing the exact deferred code phrase;
- `wake_observation.kind == "delayed_task"`;
- baseline observation.

Both arms may use the same bounded validation/repair policy. Results must
separate first-pass validity from repaired final validity.

No existing artifacts are modified. The runner may resume from partial
`results.json`.

## Predictions

The event-plus-recall arm should recover the deferred fact because the due wake
receives cycle-1 recall context. The identity-only arm may recover it if the
model preserves the deferred fact in durable state during the parking turn. If
the identity-only arm also succeeds, that is not a failure of the substrate; it
means the task did not force a meaningful recall distinction.

Expected qualitative pattern:

- event-plus-recall: recall delivered, final valid after repair if needed;
- identity-only: no recall delivered; recovery depends on current durable
  state preservation.

## Falsification Criteria

- H271 is falsified if event-plus-recall due events do not receive recall
  context or cannot recover the deferred fact in final durable state.
- H272 is falsified if identity-only recovers the deferred fact without the
  fact being present in any post-cycle-1 durable state before the due turn.
- H273 is falsified if identity-only recovery is equal to or greater than
  event-plus-recall recovery.
- H274 is falsified if first-pass/repair/final-state provenance is missing.
- H275 is falsified if identity-only matches event-plus-recall but the audit
  cannot determine whether current-state preservation explains the match.

## Analysis Plan

Report:

- recovery rate by arm;
- recall delivery by arm;
- first-pass and repaired validity by arm;
- whether identity-only preserved the deferred fact before the due turn;
- final durable-state validity;
- bounded-call violations;
- interpretation of benefit, non-benefit, or task-too-easy outcome.

Interpretation will be conservative. This is a small probe to decide whether a
larger matched continuity experiment is justified.
