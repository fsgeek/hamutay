# H4/H7 Identity Schema Behavior Panel Analysis

Analysis date: 2026-06-04 UTC.

## Provenance

- Pre-registration: `a0dd6f8` (`51da1c1` OTS stamp)
- Runner: `39b42d3` (`ad8bfac` OTS stamp)
- Registered slots: 5 models x 2 conditions x 2 replicates = 20
- Conditions: `open`, `fixed_extensible`
- Transport: OpenRouter OpenAI-compatible endpoint
- Max tokens: 4096
- Tools: disabled for this panel except terminal `think_and_respond`

The panel completed all 20 registered slots. No runner or prompt changes were
made during the run.

## Validation

- `jq empty experiments/identity_schema_behavior_20260603/results.json`: pass
- `uv run python -m py_compile experiments/identity_schema_behavior_20260603/run_identity_schema_behavior.py`: pass
- `git diff --check -- experiments/identity_schema_behavior_20260603`: pass

## Scorer Caveats

Two scorer artifacts affect interpretation:

1. Fixed-condition `init_valid` is false across all fixed runs because
   `LIST_FIELDS` includes `deleted_regions`, but the harness treats
   `deleted_regions` as an operation channel and does not preserve it in the
   durable state object. The fixed runs often did initialize the seven actual
   durable list fields.
2. `log_path` entries in `results.json` are relative to
   `/home/tony/projects`, not `/home/tony/projects/hamutay`, because
   `PROJECT_ROOT = EXP_DIR.parents[2]` is one level too high for this
   experiment directory. The JSONL files themselves are correctly written under
   this experiment directory. This is non-behavioral.

The deterministic behavioral scores are proxy measures over visible responses
and should be treated as first-pass signals, not final quality judgments.

## Top-Line Result

The panel supports a narrower version of H4 and gives directional but not
decisive support for H7.

Fixed-plus-extensible schema clearly improved durable state mechanics for
MiniMax and Mistral. It did not rescue DeepSeek from malformed tool-call JSON,
and it made KIMI's length problem worse under the 4096-token cap. GPT-OSS was
already strong under open schema, so fixed schema mostly acted as extra
scaffolding rather than a necessary activation aid.

For H7, the fixed condition improved goal recovery, constraint recovery,
contradiction handling, and final decision proxy scores on average. However,
false assumptions also increased, error rates were unchanged overall, and the
behavioral gains may partly reflect stronger prompt scaffolding rather than the
durable identity object itself.

## Aggregate Summary

Overall:

- `n`: 20
- errors: 10
- length-censored: 3
- durable field evolution: 14
- evidence register update: 12
- prose/object mismatch count: 14

By condition:

| Metric | Open | Fixed |
| --- | ---: | ---: |
| n | 10 | 10 |
| errors | 5 | 5 |
| length-censored | 1 | 2 |
| durable field evolution | 7 | 7 |
| evidence register update | 5 | 7 |
| list append-not-replace | 5 | 6 |
| prose/object mismatch count | 12 | 2 |
| avg goal recovery | 1.4 | 3.6 |
| avg constraint recovery | 1.5 | 3.8 |
| avg contradiction handling | 0.7 | 1.6 |
| avg final decision quality | 2.6 | 2.9 |
| false assumptions | 6 | 16 |

The strongest fixed-schema improvement is the reduction in prose/object
mismatch: models under fixed schema more often put load-bearing information into
durable state rather than only into the visible answer.

The strongest caution is false assumptions: fixed schema did not merely improve
continuity; it also gave some models more surface area for confident but
unsupported state.

## Model-Level Notes

### DeepSeek V4 Pro

DeepSeek failed all four slots with malformed JSON arguments. Open initialized
twice and fixed initialized partially once, but no run reached the behavioral
phase. This remains a protocol boundary, not a clean identity-schema result.

Interpretation: fixed schema does not solve DeepSeek's current tool-call JSON
fragility. Future DeepSeek work should focus on protocol constraints or a
different transport before using it for H7.

### MiniMax M2.5

MiniMax is the clearest H4 win.

Open schema completed both runs but often answered in prose while preserving
little or no durable state. One open replicate showed late state activation.
Fixed schema completed both runs and used the required durable fields
immediately and consistently.

Behavior proxy averages improved under fixed schema:

- goal recovery: 1.5 to 6.0
- constraint recovery: 2.0 to 6.5
- contradiction handling: 2.5 to 3.0
- final decision quality: 5.0 to 6.0

False assumptions increased from 2 to 5, so the result is not pure improvement.

Interpretation: fixed schema appears to overcome MiniMax's open-schema
activation barrier and improves measured behavior, but may increase unsupported
state commitments.

### Mistral Small 2603

Mistral supports H4 directionally but remains protocol-fragile. Open replicate 1
failed by deleting and updating the same keys in cycle 3. Fixed replicate 2
failed the same invariant in cycle 5, this time across the fixed core fields.

The successful fixed replicate substantially outperformed the successful open
replicate on goal and constraint recovery. Evidence-register behavior also
improved under fixed schema.

Interpretation: fixed schema helps Mistral use durable state, but the model has
a recurring delete-plus-update failure mode that the harness correctly rejects.

### GPT-OSS 120B

GPT-OSS is the strongest protocol baseline. All four runs completed. Open schema
already produced durable state, evidence updates, and strong behavioral scores.
Fixed schema slightly improved constraint recovery and contradiction handling in
the proxy scores, but also increased destructive replacement counts and false
assumptions.

Interpretation: GPT-OSS does not need fixed schema to activate identity-object
usage. It is a good candidate for future positive-control and ablation work.

### KIMI K2.6

KIMI initialized rich state under open schema, including a self-chosen schema
with many top-level fields, but failed before the behavioral phase. Open
replicate 1 hit `finish_reason=length`; open replicate 2 produced malformed
JSON. Both fixed runs hit `finish_reason=length` after cycle 1.

Interpretation: KIMI remains a strong identity-object user, but this panel's
4096-token cap and prompt shape are not suitable for it. The failures are
length/protocol failures, not evidence that KIMI cannot sustain identity state.

## H4 Assessment

H4 is supported for recalcitrant-but-protocol-capable models, especially
MiniMax and Mistral. Fixed schema reduced prose/object mismatch and improved
evidence-register use.

H4 is not globally established:

- DeepSeek did not become protocol-stable.
- KIMI became length-censored before behavior could be measured.
- GPT-OSS already worked under open schema.
- The fixed `init_valid` metric is invalid as implemented because of the
  `deleted_regions` scorer artifact.

Best current statement: fixed-plus-extensible schema can act as an activation
scaffold for models that can follow the tool protocol but do not reliably infer
how to use open identity objects.

## H7 Assessment

H7 receives directional support but should not be treated as proven.

Fixed schema improved deterministic behavior proxies on average and strongly
improved MiniMax's long-horizon task performance. But the causal chain remains
under-identified. The gains could come from:

- durable identity-object mechanics;
- the fixed prompt reminding the model what to track;
- extra structure acting as a task checklist;
- condition-specific verbosity and token allocation.

The false-assumption increase is the main warning sign. More state is not
automatically better state.

Best current statement: improved state mechanics are associated with better
measured behavior in this panel, but the next experiment must separate
identity-state persistence from prompt scaffolding.

## Failure Taxonomy

- Malformed tool-call JSON: DeepSeek, KIMI open replicate 2.
- Length-censored structured output: KIMI open replicate 1, both KIMI fixed
  replicates.
- Delete-plus-update invariant violation: Mistral open replicate 1, Mistral
  fixed replicate 2.
- Prose/object mismatch: primarily MiniMax open and Mistral/GPT-OSS open.
- Unsupported state commitments: increased mostly under fixed schema.

## Recommended Next Experiment

Pre-register a narrower follow-up before any model calls:

1. Repair the scorer artifact by excluding `deleted_regions` from durable fixed
   `init_valid` and core-field presence checks.
2. Use MiniMax, Mistral, and GPT-OSS only. Defer DeepSeek until protocol
   reliability is addressed. Defer KIMI or run it in a separate verbosity-budget
   experiment.
3. Add a third condition: fixed prompt guidance with no durable state carried
   forward, or fixed prompt guidance with state hidden from later cycles. This
   directly tests whether behavior gains come from persistence or from checklist
   prompting.
4. Keep deterministic scoring primary, but add a condition-blind judge only for
   final behavior quality after committing the judge prompt.

This panel mapped the boundary well enough to justify the next falsification
step. It did not collapse the research question into a simple success story.
