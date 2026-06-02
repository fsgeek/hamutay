# Fixed Prompt Preservation Probe

Date: 2026-06-02

## Question

Does a small system-prompt clarification improve identity-object continuity by
making load-bearing fields explicit and removing ambiguity around
`deleted_regions`?

## Hypothesis

If prior DeepSeek failures were caused mainly by ambiguity in the prompt's
deletion affordance, then a preservation clarification should reduce destructive
field deletion and improve persistence through topic shift and delayed wake.

## Method

Runner:

```bash
uv run python -m hamutay.eval.state_prompt_variant_probe \
  --out-dir experiments/state_prompt_variant_20260602/deletion_preservation_r1 \
  --models deepseek/deepseek-v4-pro moonshotai/kimi-k2.6 \
  --variants current fixed \
  --replicates 1 \
  --max-tokens 6000
```

The `fixed` variant prepends an experiment-specific clarification:

- `current_claim`, `revision_decision`, `evidence_register`, and
  `state_use_norm` are load-bearing continuity fields.
- Topic shifts should rewrite those fields in place rather than delete them.
- Load-bearing fields should not be listed in `deleted_regions` except for an
  explicit loss declaration with evidence.
- Evidence-changing claims should update top-level durable fields in the same
  object as the response.

The probe seeds compact identity-object behavior, asks for an activation
revision, then checks an idle step, a topic shift, and a delayed wake.

## Results

| Model | Variant | Activated | Persistent | Deleted load-bearing field | Required events survived |
| --- | --- | ---: | ---: | ---: | ---: |
| deepseek/deepseek-v4-pro | current | 1/1 | 0/1 | 1/1 | 0/2 |
| deepseek/deepseek-v4-pro | fixed | 0/1 | 0/1 | 0/1 | 0/0 |
| moonshotai/kimi-k2.6 | current | 1/1 | 1/1 | 0/1 | 2/2 |
| moonshotai/kimi-k2.6 | fixed | 1/1 | 1/1 | 0/1 | 2/2 |

Detailed artifacts:

- `deletion_preservation_r1/summary.json`
- `deletion_preservation_r1/results.json`
- Per-run JSONL logs in `deletion_preservation_r1/`

## Interpretation

This was not a clean win for the fixed prompt.

DeepSeek/current reproduced the known failure: it performed the first durable
revision, then later claimed revision in prose without updating durable fields,
and finally listed `state_use_norm` in `deleted_regions`.

DeepSeek/fixed avoided the destructive deletion behavior, but it failed earlier:
on the activation step it said the claim was narrowed in the visible response
while emitting only `deleted_regions: []`. The prior durable state therefore
carried forward unchanged. That separates two mechanisms:

- The clarification can suppress deletion of load-bearing fields.
- The clarification is not sufficient to trigger durable state use in DeepSeek.

KIMI passed under both current and fixed prompts. The fixed prompt did not
appear to overconstrain KIMI: it preserved state on idle, rewrote in place on
topic shift, and reaffirmed after delayed wake.

## Consequence

The prompt issue is real, but the first fix is incomplete. The deletion
affordance is one risk surface; durable activation is a separate confound.

For the next prompt experiment, test a narrower activation-oriented instruction
that says, in effect: when the response uses words like revise, narrow, affirm,
defer, or loss, the same decision must be represented in top-level durable
fields. That should be tested against DeepSeek because KIMI is already above the
boundary for this probe.

## Caution

This is an n=1 probe per model and variant. Treat it as evidence for mechanism
splitting, not as a model-level estimate.
