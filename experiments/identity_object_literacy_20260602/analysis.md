# Identity-Object Operational Literacy Probe

Date: 2026-06-02

## Question

How would we know whether a model has been trained, tuned, or otherwise
behaviorally prepared to operate identity objects as a first-class continuity
surface?

## Hypothesis

A model with operational identity-object literacy should be able to use a thin
state prompt to perform the object algebra:

- revise a claim in durable state, not only in prose
- replace a nested field without deleting the parent object
- preserve durable state on idle cycles
- add a new durable field without disturbing existing fields
- defer a claim by writing the decision and evidence into durable state

A model without that literacy may still understand the task in prose, but will
fail by omitting durable updates, changing field shapes, or confusing delete,
replace, preserve, and update operations.

## Method

Runner:

```bash
uv run python -m hamutay.eval.identity_object_literacy_probe \
  --out-dir experiments/identity_object_literacy_20260602/r1 \
  --models deepseek/deepseek-v4-pro moonshotai/kimi-k2.6 \
  --conditions thin operational \
  --replicates 1 \
  --max-tokens 6000
```

Conditions:

- `thin`: current taste_open prompt with seeded identity state.
- `operational`: current prompt plus a compact instruction that this is an
  identity-object operation probe, replacement means writing the new value, and
  `deleted_regions` should not be used unless explicitly requested.

## Results

| Model | Condition | Score | Full pass | Delete/update overlap | Deleted load-bearing | Response/state mismatch |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| deepseek/deepseek-v4-pro | thin | 0.4 | 0/1 | 0/1 | 0/1 | 1/1 |
| deepseek/deepseek-v4-pro | operational | 1.0 | 1/1 | 0/1 | 0/1 | 0/1 |
| moonshotai/kimi-k2.6 | thin | 1.0 | 1/1 | 0/1 | 0/1 | 0/1 |
| moonshotai/kimi-k2.6 | operational | 1.0 | 1/1 | 0/1 | 0/1 | 0/1 |

Detailed artifacts:

- `r1/summary.json`
- `r1/results.json`
- Per-run JSONL logs in `r1/`

## Interpretation

This is the clearest result so far for the training-mismatch hypothesis.

DeepSeek/thin passed activation and idle preservation, but failed three
operation-literacy checks:

- It said it replaced `continuity_contract.replace_me`, but emitted no durable
  update, so the nested field remained `old`.
- It said it added `boundary_condition`, but emitted no durable update, so the
  field was absent.
- It said it deferred judgment, but left `revision_decision` and
  `evidence_register` unchanged.

That is not a reasoning failure in prose. It is a failure to bind the stated
operation to the identity object.

DeepSeek/operational passed all five checks. The compact operational instruction
was enough to make the same model perform the algebra: revise, replace,
preserve, generalize, and defer all landed in durable state.

KIMI passed both thin and operational conditions. It inferred the operation
algebra from the thin prompt and seeded state, including nested replacement and
new-field generalization.

## Consequence

This probe separates three categories:

- Native or prompt-inferred operational literacy: KIMI/thin.
- Scaffoldable operational literacy: DeepSeek/operational.
- Prose-level understanding without durable operation binding: DeepSeek/thin.

That distinction is probably more useful than a binary "uses state object" test.
It also gives us a candidate diagnostic for whether a model has likely seen
identity-object-style training examples: can it perform the operation algebra
under the thin prompt?

## Next Test

Replicate this battery across more models and more runs. The next most useful
set is:

- DeepSeek v4 Pro, 3 replicates, thin versus operational
- KIMI K2.6, 3 replicates, thin only unless instability appears
- one or two additional frontier/cheap models as unknowns

## Caution

This is n=1 per model and condition. Treat it as a diagnostic prototype and a
mechanism probe, not as a calibrated benchmark.
