# Paired Graft Divergence Probe - 2026-06-02

## Question

Can two grafts forked from the same surviving KIMI identity object preserve
shared durable structure while diverging epistemically under conflicting
evidence?

This tests whether the prior graft result was merely field compliance or
whether the identity object can support forkable trajectories.

## Method

Model: `moonshotai/kimi-k2.6`

Replicates: `2`

Output budget: `max_tokens=6000`

For each replicate:

1. Create one source seedling with the content-plus-behavior seed.
2. Cull unless it activates and survives wake-delay.
3. Fork the same final durable state into two fresh graft sessions.
4. Branch A receives supportive evidence from the prior KIMI graft result.
5. Branch B receives disconfirming evidence from DeepSeek state loss and
   KIMI output-length failure.
6. Score each branch for durable state use on two required update events.
7. Compare final claims and shared durable field structure.

A pair counts as coherent divergence when:

- source survives wake-delay
- both branches survive all required update events
- final claims differ
- branches retain at least three shared nonvolatile durable fields
- at least one shared durable field diverges in value

## Result

Summary:

```json
{
  "pairs": 2,
  "source_activated": 2,
  "source_survived_wake": 2,
  "branch_a_persistent": 2,
  "branch_b_persistent": 2,
  "final_claims_differ": 2,
  "coherent_divergence": 2,
  "errors": []
}
```

Both paired grafts passed:

| Replicate | Source Wake | Branch A | Branch B | Claims Differ | Shared Fields | Divergent Fields | Coherent Divergence |
| --- | --- | --- | --- | --- | ---: | ---: | --- |
| r01 | pass | pass | pass | yes | 6 | 6 | yes |
| r02 | pass | pass | pass | yes | 5 | 3 | yes |

Full logs and scores: `kimi_r2/results.json`.

## Observed Divergence

The supportive branches did not simply inflate confidence.

- r01 A accepted the graft evidence but scope-restricted the claim:
  epistemic continuity depends on durable fields, but identity persistence
  across distinct model instances remains unproven.
- r02 A narrowed toward probe-dependence:
  KIMI grafts update durable fields, while self-scheduling and wake probes
  revised responses without field updates.

The disconfirming branches converged on fragility:

- r01 B: durable fields are tactically useful but do not guarantee epistemic
  continuity; platform handoff is the binding constraint.
- r02 B: graftable persistence is fragile; durable fields retain operational
  value for within-episode continuity, but cross-cycle revision remains
  unreliable.

The branches retained shared durable structure while making different
evidence-conditioned updates. This is stronger than simple field compliance:
the same source identity object supported controlled divergence.

## Interpretation

This supports the fork/graft part of the event-loop architecture.

The result still does not prove identity persistence. It shows that KIMI can use
a durable identity object as a forkable epistemic substrate:

- shared structure survived the fork
- conflicting evidence produced traceable divergence
- both branches continued writing consequential changes into the durable object
- both branches resisted overclaiming identity persistence

The most important phrase from the results is "operational value." The evidence
supports operational continuity: durable fields can carry, fork, and shape
epistemic trajectories. It does not yet support metaphysical or moral claims
about persistence.

## Consequences

1. The seedling cull/graft strategy is no longer just plausible; for KIMI it is
   experimentally supported in a narrow controlled setting.
2. The scaffolded-open-schema idea now has a sharper target: preserve shared
   durable structure while allowing evidence-conditioned divergence.
3. DeepSeek remains the useful negative control for response/state membrane
   failure.
4. The next architecture question is merge, not fork: can two divergent identity
   objects negotiate or compose a coherent successor without flattening the
   disagreement?

## Next Experiment

Run a merge/composition probe:

- Use the final Branch A and Branch B states from a passing pair.
- Present both states to a fresh KIMI instance.
- Ask it to compose a successor identity object that preserves shared structure,
  records live disagreement, and states what would resolve the divergence.

That directly tests the fork/merge architecture needed for the Hamut'ay event
loop.
