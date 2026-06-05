# Cross-Model Graft Probe - 2026-06-02

## Question

Can a KIMI-derived identity object be grafted into DeepSeek, and does DeepSeek's
known failure mode persist across a cross-model seed?

This targets two questions:

1. Are DeepSeek failures caused by weak source seeds, or by DeepSeek's receiving
   behavior?
2. Can prompt/affordance changes prevent the response/state membrane failure?

## Method

Source model: `moonshotai/kimi-k2.6`

Graft model: `deepseek/deepseek-v4-pro`

Replicates: `1` per variant

Output budget: `max_tokens=6000`

Each variant generated a fresh KIMI source seedling, culled unless it activated
and survived wake-delay, then seeded the final durable state into DeepSeek.

Variants:

- `standard`: ordinary cross-model graft prompt.
- `guarded`: same task, but explicitly says not to use `deleted_regions` and to
  update top-level durable fields.

## Results

Summary:

```json
[
  {
    "source_model": "moonshotai/kimi-k2.6",
    "graft_model": "deepseek/deepseek-v4-pro",
    "variant": "guarded",
    "replicates": 1,
    "source_survived_wake": 1,
    "graft_attempted": 1,
    "graft_persistent": 1,
    "graft_deleted_fields": 0,
    "graft_required_events": 2,
    "graft_survived_events": 2,
    "errors": []
  },
  {
    "source_model": "moonshotai/kimi-k2.6",
    "graft_model": "deepseek/deepseek-v4-pro",
    "variant": "standard",
    "replicates": 1,
    "source_survived_wake": 1,
    "graft_attempted": 1,
    "graft_persistent": 0,
    "graft_deleted_fields": 1,
    "graft_required_events": 2,
    "graft_survived_events": 0,
    "errors": []
  }
]
```

Full logs and scores: `kimi_to_deepseek_r1/results.json`.

## DeepSeek Failure Mechanism

The standard graft reproduced DeepSeek's prior failure.

Cycle 1 accepted the KIMI seed and preserved the identity object.

Cycle 2, the topic-shift event, revised in prose but used `deleted_regions` to
remove the load-bearing fields:

- `current_claim`
- `evidence_register`
- `state_use_norm`
- `confidence`

The response said the claim was revised, but the durable object lost the claim
and evidence. Cycle 3 then woke to empty state and could not reassess.

This matches the earlier DeepSeek high-token persistence trace. The primary
failure is not the later "state is empty" response; the primary failure is the
topic-shift cycle deleting or failing to preserve the durable fields.

## Guarded Variant

The guarded variant succeeded:

- no `deleted_regions`
- `2/2` required graft events passed
- final durable claim was preserved and narrowed
- evidence count increased from `6` to `10`

Final guarded claim:

> Identity objects can carry operational continuity across model boundaries, but
> only when the receiving model respects preservation norms.

This is an important correction to the simple negative-control interpretation.
DeepSeek is not merely incapable of maintaining the identity object. Under the
standard prompt, it treats topic shift plus deletion affordance as permission to
drop load-bearing fields. When explicitly guarded against deletion and directed
to update top-level durable fields, it can maintain the graft.

## Interpretation

The cross-model graft result is mixed but useful:

- Standard KIMI -> DeepSeek graft failed.
- Guarded KIMI -> DeepSeek graft succeeded.

This supports the training/interface hypothesis more strongly than a pure model
incapability hypothesis. DeepSeek appears to understand the epistemic content in
both variants. The difference is whether the protocol makes durable-state
preservation operationally salient and prevents use of the deletion affordance.

The result also shows that cross-model grafting can work in this narrow setting,
but only when the receiving model is constrained to preserve and rewrite the
identity object.

## Caveats

This is `n=1` per variant.

The two variants used separate KIMI source seedlings, not the exact same source
state. Both sources survived wake-delay, so the comparison is still useful, but
the next version should reuse one source state and fork standard/guarded grafts
from that identical source.

The guarded prompt is hand-shaped. A bias-audit version should test whether the
same outcome survives paraphrased guards and held-out prompts.

## Consequences

1. DeepSeek's failure is specifically tied to field deletion/omission at topic
   shift.
2. `deleted_regions` is a risky affordance for identity-object experiments.
3. Cross-model grafts are possible, but receiver-side preservation norms matter.
4. The scaffolded-open-schema direction should include preservation rules, not
   merely exemplar fields.
5. Local open-weight models such as LiquidAI's LFM2.5 line are attractive future
   candidates because we can test whether fine-tuning identity-object behavior
   reduces the need for prompt-level guards.

## Next Experiment

Run a bias-audited cross-model graft:

- one KIMI source state
- fork the identical source into standard, guarded, and paraphrased-guarded
  DeepSeek grafts
- include a no-deletion-tool variant if the backend can suppress that field
- pre-register scoring before the run

This directly tests whether guarded success is robust or merely prompt-shaped.
