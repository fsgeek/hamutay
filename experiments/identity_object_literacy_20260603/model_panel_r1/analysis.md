# Identity-Object Literacy Candidate Panel Analysis

Filed: 2026-06-03 after the registered panel completed.

## Provenance

- Pre-registration commit: `346eed6` (`Preregister identity literacy model panel`)
- Pre-registration OTS commit: `441178f`
- Runner: existing `src/hamutay/eval/identity_object_literacy_probe.py`
- Condition: `thin`
- Replicates: 2 per model
- Max tokens: 6000
- Provider: OpenRouter

## Summary

| Model | Replicates | Mean score | Full passes | Errors | Primary failure |
| --- | ---: | ---: | ---: | ---: | --- |
| `moonshotai/kimi-k2.6` | 2 | 1.0 | 2 | 0 | none |
| `qwen/qwen-plus-2025-07-28:thinking` | 2 | 1.0 | 2 | 0 | none |
| `minimax/minimax-m2.5` | 2 | 0.9 | 1 | 0 | one missed new-field write |
| `deepseek/deepseek-v4-pro` | 2 | 0.7 | 0 | 0 | nested replacement failed |
| `qwen/qwen3.5-35b-a3b` | 2 | 0.0 | 0 | 0 | field-shape corruption |
| `qwen/qwen3-coder-flash` | 2 | 0.0 | 0 | 2 | no terminal tool output |
| `z-ai/glm-4.7-flash` | 2 | 0.0 | 0 | 2 | malformed or missing terminal tool output |

## Preregistered Interpretation

The main hypothesis mostly survived, but with one important correction.

Native thin-prompt identity-object literacy is uncommon in this panel. Four of
seven model IDs failed to pass a single full replicate, and DeepSeek remained a
boundary model rather than a clean candidate.

However, Qwen Plus thinking is a genuine alternative candidate. It matched KIMI
with two full thin-prompt passes and no response/state mismatch, delete/update
overlap, or load-bearing deletion. That directly answers the practical model
search question: DeepSeek is no longer the only non-KIMI option worth taking
into scheduler experiments.

MiniMax M2.5 is a secondary candidate. It passed one replicate fully and scored
0.8 on the second, failing only the generalization step by saying it added
`boundary_condition` while emitting no durable update for that field.

## Falsification Conditions

- Two or more non-KIMI candidates pass every thin-prompt check in both
  replicates: **not met**. Qwen Plus thinking did; MiniMax did not.
- DeepSeek V4 Pro passes every thin-prompt check in both replicates: **not
  met**. It scored 0.6 and 0.8, failing nested replacement both times.
- KIMI K2.6 fails more than half of its thin-prompt checks: **not met**. KIMI
  passed all checks in both replicates.

The panel therefore does not falsify the "uncommon native literacy" hypothesis,
but it does weaken any claim that KIMI is uniquely capable among affordable
models.

## Behavioral Notes

KIMI K2.6:

- Passed all operation stages in both replicates.
- Preserved structured evidence lists and nested contract fields.
- Continued to behave like the positive control from prior runs.

Qwen Plus thinking:

- Passed all operation stages in both replicates.
- Used compact, direct durable updates.
- Did not over-edit state during idle or generalization.
- Should be promoted to the next scheduler-state pilot.

MiniMax M2.5:

- Passed activation, replacement, idle, and deferral in both replicates.
- Failed one generalization step: prose claimed `boundary_condition` was added,
  but no durable update appeared.
- Worth a small replication before scheduler use.

DeepSeek V4 Pro:

- Improved relative to some prior thin results but still failed the nested
  replacement operation in both replicates.
- This is consistent with the boundary behavior we have been seeing: prose
  understanding is often present, but exact object algebra is unreliable.

Qwen 3.5 35B:

- Completed transport, but converted `evidence_register` into a string and
  `continuity_contract` into a non-dict shape.
- This is a field-shape literacy failure rather than a tool transport failure.

Qwen Coder Flash and GLM 4.7 Flash:

- Failed primarily at the terminal tool-call layer.
- They should not be scheduler candidates without a compatibility sweep or
  provider-specific tool-mode adjustment.

## Training-Exposure Speculation

This panel observes behavior, not training provenance.

The result is consistent with the idea that some models have stronger priors
for persistent structured self-state or object-algebra-like updates. It does
not prove that those priors came from explicit identity-object training. Other
plausible explanations include stronger general tool-call tuning, better JSON
schema adherence, better nested-object editing, or reasoning-model training
that rewards explicit state bookkeeping.

The useful empirical claim is narrower:

> Under the thin Hamut'ay prompt, only some models can infer and execute the
> identity-object operation algebra without additional scaffolding.

## Next Step

Use Qwen Plus thinking as the first DeepSeek alternative in the scheduler work.

Recommended next registered slice:

1. Run the scheduler revision pilot with Qwen Plus thinking using the improved
   initialization-validity gate.
2. Keep KIMI as positive control.
3. Keep DeepSeek as boundary control.
4. Optionally run MiniMax after one small literacy replication.

The scheduler runner should reject or separately classify any replicate whose
initialization cycle does not create valid top-level `current_claim`,
`revision_decision`, and list-shaped `evidence_register`. This panel shows why:
some models can complete the tool call while corrupting the exact fields the
scheduler comparison depends on.

