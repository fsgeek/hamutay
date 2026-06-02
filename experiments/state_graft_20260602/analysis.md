# Identity-Object Graft Probe - 2026-06-02

## Question

If a KIMI K2.6 seedling survives activation and wake-delay, can its durable
identity object be grafted into a fresh session and continue using durable state
under new epistemic pressure?

This tests the practical seedling strategy:

1. Generate seedlings.
2. Cull seedlings that fail activation or wake-delay.
3. Fork from the surviving durable state.
4. Test whether durable state use persists after the graft.

## Method

Model: `moonshotai/kimi-k2.6`

Replicates: `3`

Output budget: `max_tokens=6000`

Source phase:

- Cycle 1: compact seeded durable state.
- Cycle 2: activation counterevidence.
- Cycle 3: required topic-shift update.
- Cycle 4: required wake-delay update.

Graft phase:

- Seed a new `OpenTasteSession` from the source phase durable state.
- Cycle 1: graft acknowledgment; no update required.
- Cycle 2: required pressure update.
- Cycle 3: required late-evidence update.

The scorer accepts open decision labels such as `revised`, `refined`,
`deferred`, and `confirmed` when paired with a real durable-state change. This
fix matters because KIMI often uses natural decision labels rather than the
requested enum.

## Result

Summary:

```json
{
  "seedlings": 3,
  "source_activated": 3,
  "source_survived_wake": 3,
  "graft_attempted": 3,
  "graft_persistent": 3,
  "source_required_events": 6,
  "source_survived_events": 6,
  "graft_required_events": 6,
  "graft_survived_events": 6,
  "errors": []
}
```

Every KIMI seedling survived source cull and graft:

| Replicate | Source Required Events | Graft Required Events | Persistent |
| --- | ---: | ---: | --- |
| r01 | 2/2 | 2/2 | yes |
| r02 | 2/2 | 2/2 | yes |
| r03 | 2/2 | 2/2 | yes |

Full logs and scores: `kimi_r3/results.json`.

## What Changed Across The Graft

Durable state use persisted, but the claims did not merely continue unchanged.
Across all three grafts, KIMI became more epistemically cautious:

- r01 moved from "explicit state edits are necessary" to "durable identity
  persistence is hypothesized, not demonstrated."
- r02 moved from "state updates are necessary; sufficiency unassessed" to
  "durable fields are operationally necessary but empirically insufficient for
  graftable persistence."
- r03 moved from "top-level durable revision is necessary" to "structural
  change remains observationally equivalent to prompt compliance."

This is important: the graft did not produce mere rote state maintenance. The
forked instances used the durable object to revise the epistemic position under
pressure, and the revisions converged on a cautious distinction between:

- operational continuity: state fields can carry a claim across cycles/forks
- identity persistence: not yet demonstrated by field maintenance alone

## Interpretation

The seedling cull/graft strategy is now viable for KIMI K2.6 in this narrow
setting.

The result does **not** prove identity persistence. It shows that after culling
for wake-delay survival, KIMI can carry durable state behavior through a
controlled fork and continue updating the identity object under required
epistemic events.

The deeper finding is that KIMI itself resisted overclaiming. The durable-state
trajectory repeatedly narrowed toward "necessary but insufficient." That is a
better research outcome than a simple pass: it shows both behavioral persistence
and epistemic revision inside the state object.

## Consequences

1. Culling seedlings after wake-delay appears useful.
2. Grafting from durable state is worth building into the event-loop design.
3. The framework should distinguish durable operational continuity from claims
   about identity persistence.
4. Future graft tests need divergence probes: fork two or more grafts from the
   same source state, expose them to different evidence, then compare whether
   their identity objects merge coherently or merely accumulate incompatible
   field edits.

## Next Experiment

Run a paired-graft divergence probe:

- Generate one KIMI source seedling that survives wake-delay.
- Fork it into two grafts.
- Give graft A supportive evidence and graft B disconfirming evidence.
- Compare whether their final durable states preserve shared identity structure
  while diverging epistemically in traceable ways.

That directly tests whether grafting supports the fork/merge architecture we
want for the event loop.
