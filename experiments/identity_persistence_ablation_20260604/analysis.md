# H7 Identity Persistence Ablation Analysis

Analysis date: 2026-06-04.

## Provenance

- Pre-registration: `7581893` (`1029aa5` OTS stamp)
- Runner: `a14e516` (`80f5dae` OTS stamp)
- Registered slots: 3 models x 4 conditions x 2 replicates = 24
- Conditions: `open_durable`, `fixed_durable`,
  `fixed_checklist_no_state`, `fixed_checklist_summary`
- Max tokens: 4096
- Transport: OpenRouter OpenAI-compatible endpoint
- Tool surface: terminal `think_and_respond` only

The runner attempted all 24 registered slots. Ten slots errored before a full
six-cycle behavioral trace was available. No prompts, scoring rules, model list,
or token limits were changed during the run.

## Validation

- `jq empty experiments/identity_persistence_ablation_20260604/results.json`: pass
- `uv run python -m py_compile experiments/identity_persistence_ablation_20260604/run_identity_persistence_ablation.py`: pass
- `git diff --check -- experiments/identity_persistence_ablation_20260604`: pass

## What This Tested

The prior H4/H7 panel showed that fixed schema could improve state mechanics
and was associated with better behavior. This ablation asked what part of that
intervention was doing the work:

- raw durable self-authored state;
- fixed checklist-style prompt scaffolding;
- ordinary carry-forward context via neutral summary.

The key comparison is not open versus fixed. It is `fixed_durable` versus the
two checklist controls.

## Scoring Caveats

State-mechanics scores for checklist controls are diagnostic only. In those
conditions the model still returns structured objects, and those objects are
logged, but raw state is not carried forward to later cycles.

Destructive replacement counts are not comparable between durable and checklist
controls. In checklist controls each cycle starts without raw prior state, so
the logged objects can look like replacement even though replacement is not a
persistence failure in that condition.

The control conditions use direct backend calls rather than `OpenTasteSession`
because they must prevent raw state carry-forward. This is the cleanest way this
runner used to enforce the ablation, but it creates a protocol-framing
difference that likely contributed to some no-`think_and_respond` and
malformed-JSON failures.

This is not a small caveat. Error-rate differences are therefore confounded
with condition machinery. The honest interpretation is provisional: the panel
shows that no-state checklist prompting was weak in this apparatus, and that
summary carry-forward could match durable state for Mistral, but it does not
fully level the harness code path across treatment and controls.

## Aggregate Result

By condition:

| Condition | Errors | Goal | Constraint | Contradiction | Evidence | Final | Delayed | False assumptions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `open_durable` | 1/6 | 2.167 | 2.333 | 0.500 | 1.000 | 3.833 | 0.167 | 3 |
| `fixed_durable` | 3/6 | 3.667 | 4.333 | 1.667 | 1.833 | 3.167 | 1.500 | 14 |
| `fixed_checklist_no_state` | 3/6 | 0.333 | 0.500 | 0.167 | 0.500 | 2.500 | 0.000 | 0 |
| `fixed_checklist_summary` | 3/6 | 3.000 | 3.500 | 1.833 | 2.333 | 3.000 | 2.167 | 13 |

No-state checklist was weak. Summary carry-forward was competitive with fixed
durable on several behavioral proxy measures and better on delayed challenge
accuracy, but it had the same high false-assumption count pattern.

The headline that survives the protocol caveat best is not "which condition
won." It is that richer carry-forward, whether durable state or summary,
improved recovery while also increasing contamination. Continuity and false
assumption appear coupled in this task.

This weakens the strongest form of H7a: the panel does not show that raw
self-authored durable state is uniquely responsible for the fixed-schema gains.

It supports a narrower claim: some carry-forward context is important, and
fixed structure helps models use that context, but ordinary summary context can
sometimes substitute for raw durable identity state on this task.

## Model-Level Results

### MiniMax M2.5

MiniMax was protocol-bound in this runner shape.

- `open_durable`: both replicates completed, but behavioral recovery was weak.
- `fixed_durable`: both replicates initialized core fields but failed before
  behavioral scoring with no `think_and_respond` output.
- `fixed_checklist_no_state`: both replicates failed before logging any cycle.
- `fixed_checklist_summary`: one replicate failed after initialization; one
  replicate completed and substantially outscored `open_durable`.

The one successful summary-control replicate is notable:

- goal recovery: 6
- constraint recovery: 7
- contradiction handling: 4
- evidence grounding: 5
- final decision quality: 6
- delayed challenge accuracy: 5
- false assumptions: 5

Interpretation: MiniMax does not provide a clean durable-versus-checklist
comparison here. It does suggest that neutral summary carry-forward can recover
the task better than open durable for this model, but protocol instability
prevents a strong conclusion.

### Mistral Small 2603

Mistral is the cleanest ablation slice. All eight Mistral slots completed.

Model-condition averages:

| Condition | Goal | Constraint | Contradiction | Evidence | Final | Delayed | False assumptions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `open_durable` | 3.0 | 3.5 | 0.5 | 1.0 | 4.0 | 0.0 | 3 |
| `fixed_durable` | 5.0 | 7.0 | 3.5 | 4.0 | 6.5 | 3.0 | 8 |
| `fixed_checklist_no_state` | 0.0 | 0.5 | 0.0 | 1.0 | 3.0 | 0.0 | 0 |
| `fixed_checklist_summary` | 6.0 | 7.0 | 3.5 | 4.5 | 6.0 | 4.0 | 8 |

No-state checklist failed behaviorally despite completing. Fixed durable and
summary carry-forward were effectively tied, with summary slightly better on
goal recovery, evidence grounding, and delayed challenge accuracy, and fixed
durable slightly better on final decision quality.

Interpretation: for Mistral, carry-forward context appears load-bearing, but
raw self-authored durable state is not uniquely load-bearing on this task.
This is the strongest evidence against the simple H7a reading.

### GPT-OSS 120B

GPT-OSS was mixed and more protocol-fragile than in the prior panel.

- `open_durable`: one replicate failed at cycle 3 with delete-plus-update on
  `goals`; one completed with strong goal recovery and final decision quality.
- `fixed_durable`: one completed; one failed at cycle 5 with malformed JSON
  after good recovery through cycle 4.
- `fixed_checklist_no_state`: one completed weakly; one failed at cycle 6 with
  malformed JSON.
- `fixed_checklist_summary`: both failed before behavioral scoring with
  malformed JSON.

The usable GPT-OSS rows suggest fixed durable improves recovery over no-state
checklist, but the summary control failed too early to test substitution.

Interpretation: GPT-OSS supports the claim that no-state checklist is
insufficient, but it does not cleanly adjudicate durable state versus summary.

## H7a Assessment

H7a predicted that `fixed_durable` would outperform both checklist controls.
The panel weakens that claim.

Concrete observations:

- `fixed_checklist_no_state` did not match `fixed_durable`; this supports the
  importance of carry-forward context.
- `fixed_checklist_summary` did match or exceed `fixed_durable` for Mistral,
  the cleanest model in this panel.
- MiniMax had one successful summary-control run that outperformed its durable
  conditions, though protocol failures limit interpretation.
- GPT-OSS summary failed before behavioral scoring, so it does not rescue H7a.

Best current statement: durable state is not yet shown to be uniquely useful
beyond structured carry-forward context. The stronger H7a claim should be
treated as weakened.

## H7b Assessment

H7b predicted that checklist controls might match `fixed_durable`.

The no-state checklist did not. The summary checklist sometimes did.

Best current statement: checklist prompting alone is not enough, but checklist
prompting plus neutral summary can reproduce much of the fixed durable behavior
in at least one protocol-capable model.

## Failure Taxonomy

- No terminal `think_and_respond`: MiniMax fixed durable and no-state controls.
- Malformed JSON: GPT-OSS fixed durable, no-state, and summary controls.
- Delete-plus-update invariant: GPT-OSS open durable replicate 1.
- Weak no-state recovery: Mistral and GPT-OSS no-state controls completed but
  did not recover the interrupted task well.
- False assumptions: concentrated in fixed durable and summary carry-forward,
  not in no-state controls.

## Main Interpretation

The result is not "durable identity objects do not matter." It is narrower:

1. Carry-forward context matters. No-state checklist was poor.
2. Fixed structure helps models exploit carry-forward context.
3. Raw self-authored durable state is not yet distinguished from a neutral
   harness summary on this task.
4. More structured carry-forward increases the risk of false assumptions.

An adversarial review filed after this analysis sharpened the strongest
surviving claim: richer carry-forward buys continuity at the cost of
contamination. A raw transcript spot-check of the Mistral `fixed_durable` and
`fixed_checklist_summary` cells supports that concern. The deterministic
`false_assumption_count` is directionally useful but likely undercounts
unsupported details. Examples include invented timing and architecture details,
site-name drift, transient-cache proposals under a no-local-storage ruling,
invented budget figures, and pilot-scope changes not present in the task facts.

Therefore the false-assumption result should be treated as a floor, not a
precise count.

The current evidence points toward a continuum:

- no carry-forward: weak continuity;
- summary carry-forward: strong continuity, but can preserve false assumptions;
- raw durable identity state: strong continuity, also false-assumption risk;
- open durable state: model-dependent and often underuses evidence structure.

## Recommended Next Step

Do not run a broader model sweep yet.

First equalize the code path across treatment and controls. Otherwise the same
protocol confound will recur and any completion-rate or malformed-tool-call
difference will remain entangled with the condition.

The next useful step is a more precise Mistral-only or Mistral+GPT-OSS
ablation that separates summary source:

1. `fixed_durable`: raw self-authored state.
2. `self_summary`: model-authored compact summary of its own prior state.
3. `harness_summary`: deterministic neutral summary as used here.
4. `visible_transcript_summary`: summary of visible responses only, no hidden
   state facts.

The primary question would shift again:

Does autobiographical compression outperform neutral biographical compression
when both are given equivalent carry-forward budget?

That is closer to the autobiographical-versus-biographical question already
visible elsewhere in the project, and it directly follows from this ablation.
Given the 10/24 error rate in this panel, the next run should either use more
replicates or a more protocol-stable model set, with Mistral as the primary
candidate.
