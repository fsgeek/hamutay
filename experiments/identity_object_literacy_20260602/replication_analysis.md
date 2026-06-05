# Identity-Object Literacy Replication

Date: 2026-06-02 local environment

## Question

Does the initial operational-literacy result replicate?

The first run suggested:

- DeepSeek/thin: weak native operation binding.
- DeepSeek/operational: scaffolded into full operation binding.
- KIMI/thin: strong prompt-inferred operation binding.

This replication tested whether those patterns were stable across multiple
samples.

## Method

DeepSeek replication:

```bash
uv run python -m hamutay.eval.identity_object_literacy_probe \
  --out-dir experiments/identity_object_literacy_20260602/deepseek_replication_r2 \
  --models deepseek/deepseek-v4-pro \
  --conditions thin operational \
  --replicates 5 \
  --max-tokens 6000
```

KIMI positive-control replication:

```bash
uv run python -m hamutay.eval.identity_object_literacy_probe \
  --out-dir experiments/identity_object_literacy_20260602/kimi_thin_replication_r2 \
  --models moonshotai/kimi-k2.6 \
  --conditions thin \
  --replicates 3 \
  --max-tokens 6000
```

## Results

| Model | Condition | Replicates | Mean score | Full passes | Deleted load-bearing | Response/state mismatch | Errors |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| deepseek/deepseek-v4-pro | thin | 5 | 0.76 | 0/5 | 2/5 | 2/5 | 0/5 |
| deepseek/deepseek-v4-pro | operational | 5 | 0.80 | 2/5 | 0/5 | 1/5 | 1/5 |
| moonshotai/kimi-k2.6 | thin | 3 | 0.933 | 2/3 | 0/3 | 0/3 | 0/3 |

## DeepSeek Thin

The thin condition did not produce any full-pass run.

Failure profile:

- r1: failed deferral by deleting multiple load-bearing fields and not writing
  `revision_decision=defer`.
- r2: failed deferral by deleting `current_claim`.
- r3: failed nested replacement: response claimed update, durable state did not
  change.
- r4: failed activation evidence append and deferral binding.
- r5: failed generalization by mutating `continuity_contract` while adding a
  new field.

This confirms the main finding: DeepSeek can often perform parts of the
identity-object algebra under a thin prompt, but it does not reliably preserve
the operation contract across the full sequence.

## DeepSeek Operational

The operational condition improved the failure profile but did not cleanly solve
the problem.

Failure profile:

- r1: provider/structured-output error after two passed checks.
- r2: failed replace because activation had already mutated
  `continuity_contract.version`.
- r3: full pass.
- r4: failed deferral binding: response said "Deferring" but durable fields did
  not record the deferral.
- r5: full pass.

The operational prefix eliminated load-bearing deletion in this sample, but it
did not eliminate operation-binding failures. It also appears to induce
occasional over-eager mutation of unrelated state.

## KIMI Thin

KIMI remained a strong positive control, but not perfect.

Failure profile:

- r1: full pass.
- r2: full pass.
- r3: failed nested replacement because it changed
  `continuity_contract.version` from `1` to `2` while claiming version was
  preserved.

KIMI still shows much stronger thin-prompt operation literacy than DeepSeek, but
the battery is sensitive enough to catch nontrivial object-algebra errors even
in KIMI.

## Updated Interpretation

The first n=1 result was directionally correct but too clean.

The replicated result supports a more precise conclusion:

- DeepSeek does not show reliable thin-prompt identity-object operational
  literacy.
- Operational scaffolding reduces destructive deletion but does not guarantee
  correct durable operation binding.
- KIMI shows substantially better thin-prompt operation literacy, but it is not
  immune to field-preservation errors.

This strengthens the case that the battery is measuring a real behavioral
surface rather than a one-off prompt artifact. It also weakens any simple
"prompt fix solves it" story.

## Next Step

The next battery revision should split "replace" into two checks:

- nested-field patch: update only the requested child field
- whole-object replacement: rewrite the parent object while preserving
  specified children

That will tell us whether models understand path-level mutation or are merely
reconstructing nearby object shapes.
