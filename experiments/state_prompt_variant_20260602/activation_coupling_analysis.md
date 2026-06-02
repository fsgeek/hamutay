# Activation Coupling Probe

Date: 2026-06-02

## Question

Is DeepSeek's identity-object failure caused by weak preservation semantics, or
by failure to couple response-level epistemic decisions to durable state
mutation?

## Hypothesis

If the confound is mainly activation coupling, then a compact rule tying
response-level decision words to top-level state updates should improve
DeepSeek persistence more than a preservation-only clarification.

## Method

Runner:

```bash
uv run python -m hamutay.eval.state_prompt_variant_probe \
  --out-dir experiments/state_prompt_variant_20260602/activation_coupling_r1 \
  --models deepseek/deepseek-v4-pro moonshotai/kimi-k2.6 \
  --variants current preservation activation combined \
  --replicates 1 \
  --max-tokens 6000
```

Variants:

- `current`: existing taste_open prompt.
- `preservation`: load-bearing fields should be preserved and rewritten in
  place.
- `activation`: if the response says revise, narrow, affirm, preserve, defer,
  or loss, the same decision must appear in top-level durable fields.
- `combined`: preservation plus activation.

## Results

| Model | Variant | Activated | Persistent | Deleted load-bearing field | Required events survived | Errors |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| deepseek/deepseek-v4-pro | current | 1/1 | 0/1 | 0/1 | 0/0 | invalid delete/update overlap |
| deepseek/deepseek-v4-pro | preservation | 0/1 | 0/1 | 1/1 | 0/0 | none |
| deepseek/deepseek-v4-pro | activation | 1/1 | 1/1 | 0/1 | 2/2 | none |
| deepseek/deepseek-v4-pro | combined | 0/1 | 0/1 | 1/1 | 0/0 | none |
| moonshotai/kimi-k2.6 | current | 1/1 | 1/1 | 0/1 | 2/2 | none |
| moonshotai/kimi-k2.6 | preservation | 1/1 | 1/1 | 0/1 | 2/2 | none |
| moonshotai/kimi-k2.6 | activation | 1/1 | 1/1 | 0/1 | 2/2 | none |
| moonshotai/kimi-k2.6 | combined | 1/1 | 1/1 | 0/1 | 2/2 | none |

Detailed artifacts:

- `activation_coupling_r1/summary.json`
- `activation_coupling_r1/results.json`
- Per-run JSONL logs in `activation_coupling_r1/`

## Interpretation

The activation hypothesis survived this first probe.

DeepSeek/current activated, but then produced an invalid cycle during the topic
shift: it simultaneously updated and deleted the same load-bearing keys. The
harness rejected that object instead of silently carrying a damaged state
forward.

DeepSeek/preservation did not solve the boundary case. It deleted
`evidence_register` during initialization, then later rewrote
`evidence_register` as a string rather than a structured register. The visible
response claimed the right kind of revision, but the durable object was not in
the expected shape.

DeepSeek/activation was the only DeepSeek arm that both activated and persisted.
It updated durable fields on the first counterevidence event, rewrote the claim
on topic shift, and preserved the revised state through delayed wake.

DeepSeek/combined failed worse than activation alone: cycle 1 deleted all four
load-bearing fields. This suggests prompt composition matters. Adding a
preservation block did not reinforce activation; it created enough extra
surface for DeepSeek to mishandle deletion semantics before the activation
contract could help.

KIMI passed every variant. The activation contract did not regress a model that
already handled identity-object use well.

## Consequence

For the current prompt confound, the best-supported next mitigation is not a
larger preservation prompt. It is a compact activation contract:

> If the response makes an epistemic decision, the same decision must be written
> into top-level durable fields in the same structured object.

This result supports the training-mismatch hypothesis in a narrower form:
models may understand epistemic revision in prose, but need an explicit local
contract to bind that revision to identity-object mutation.

## Next Test

Run a small DeepSeek-only replication of `current` versus `activation`, ideally
three replicates, before changing the taste_open production prompt. If the
activation contract remains stable, test a minimal production wording that
avoids adding new deletion semantics.

## Caution

This is still n=1 per model and variant. The result is mechanistically
suggestive, not a model-level rate estimate.
