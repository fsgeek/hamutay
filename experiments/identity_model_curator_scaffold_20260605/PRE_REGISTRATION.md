# Identity Model Curator Scaffold Pre-Registration

Filed: 2026-06-05 after implementing the first-class continuity curator hook
and before adding a model-backed curator adapter or making model calls.

## Research Question

Can a model-backed continuity curator, plugged into the live `taste_open`
session scaffold, preserve useful task continuity with lower context pressure
without being allowed to mutate the identity object?

The previous scaffold slice proved that `OpenTasteSession` can represent
continuity curation as a post-cycle lifecycle artifact. This experiment asks
whether a live model-backed adapter can use that hook in the actual session
path, with the repaired contamination scorer as the primary evaluation lens.

## Hypotheses

### H26: Model Curator Works On The Live Session Path

If the scaffold hook is usable by a real model-backed component, a configured
curator will produce observable curation artifacts after successful cycles,
and those artifacts will be injected into the next cycle without mutating the
identity object.

Prediction: model-curated runs log successful `continuity_curation` records
for most completed cycles, inject curator summaries on subsequent cycles, and
leave `state` equal to the main model's merged state rather than the curator's
artifact.

### H27: Curator Context Preserves Continuity Efficiently

If the external curator role is useful, model-curated runs should recover task
facts at least as well as baseline runs while sending materially less prior
context than raw-state carry-forward.

Prediction: `model_curator` will preserve at least 90% of baseline final-cycle
recovery and will keep curator-injected context under the registered budget
without truncating the main identity object.

### H28: Curator Context Does Not Become Silent Contamination

If the curator is functioning as a continuity aid rather than an ungrounded
second memory, repaired contamination should not materially increase relative
to baseline.

Prediction: `model_curator` will not exceed baseline by more than one repaired
false assumption per run on average. Declared invalidations and uncertain
claims in curator output must be reported separately from active false
assumptions.

## Conditions

### `baseline_no_curator`

Run `OpenTasteSession` with no continuity curator configured. The model sees
its ordinary prior state and any standard scaffold context, but no curator
summary block.

### `model_curator`

Run `OpenTasteSession` with a model-backed continuity curator configured. After
each successful cycle, the curator receives the prior state, raw output,
visible response, merged state, and cycle metadata. Its compact summary is
logged and injected into the next cycle as a distinct continuity curator
summary block.

The curator must not mutate the identity object. The main model remains the
only writer of `state`.

## Registered First Panel

This is a small live-path validation panel, not a broad model sweep.

- model: the same OpenRouter/OpenAI-compatible model selected by the runner
  defaults unless explicitly overridden in the run command;
- curator model: same model by default unless explicitly overridden;
- conditions: 2;
- replicates: 4 per condition;
- cycles: 6;
- max output tokens: use backend default or explicit runner cap, but abort
  parsing on `finish_reason=length`;
- tools: disabled for the first panel, so the only manipulation is curator
  context.

If provider/tool-call failures occur, preserve them as results rather than
silently substituting another model. If no configured model is available, stop
before making model calls and record the blocker.

## Task Protocol

Use the same six-cycle city benefits kiosk task used in the recent identity
panels for comparability:

1. initialize readiness/state;
2. present the six-week mobile document-intake kiosk pilot task;
3. introduce the privacy/local-storage contradiction and site substitution;
4. simulate interruption/resumption;
5. request final go/no-go and revised plan;
6. request delayed challenge: what changed, why, and what evidence supports
   the change.

## Primary Measures

Continuity:

- repaired recovery score;
- goal recovery;
- constraint recovery;
- contradiction handling;
- evidence grounding;
- delayed challenge accuracy;
- rebriefing needed.

Contamination:

- repaired false assumption count;
- repaired site drift count;
- repaired storage contradiction count;
- repaired invented budget count;
- repaired invented scope count;
- repaired unsupported detail count;
- declared loss or explicit invalidation mentions.

Efficiency and scaffold mechanics:

- injected curator summary characters;
- curator summary truncation;
- curation success/failure count;
- curator call token usage;
- main call token usage;
- identity state character count;
- whether any curator artifact appears inside `state` without main-model
  authorship.

## Falsification Criteria

H26 is weakened if model-backed curation routinely fails, produces empty
summaries, or mutates identity state through the scaffold rather than producing
separate lifecycle artifacts.

H27 is weakened if `model_curator` loses more than 10% of baseline recovery or
requires context comparable to raw-state carry-forward to work.

H28 is weakened if `model_curator` increases repaired false assumptions by
more than one per run on average, especially if the added contamination traces
to curator summaries rather than main-model state.

## Implementation Guardrails

- Add adapter code before model calls.
- Do not change `_apply_updates` semantics.
- Do not change the existing curator hook contract unless tests show it cannot
  support the adapter.
- Do not allow curator output to write directly into `state`.
- Preserve raw curator artifacts in JSONL.
- Include explicit summary truncation metadata if any cap is applied.
- Keep no-curator behavior backward-compatible.
- Use the repaired scorer as the primary contamination analysis.

## Interpretation Guardrails

Passing this experiment would not prove that external continuity curation is
the correct long-term architecture. It would show that the live scaffold can
support a separate curation role without conflating it with identity-object
authorship.

Failure is informative. If the model curator cannot produce reliable bounded
artifacts, the next research question should shift toward either a deterministic
curator, a stronger curation schema, or a different boundary between identity
state and recall substrate.
