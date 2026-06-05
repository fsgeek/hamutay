# Taste Open Prompt Audit - 2026-06-02

## Question

Has `taste_open` accumulated enough system-prompt thickness to confound the
identity-object experiments?

The concern is that `taste_open` began as a thin open-object protocol, but tool
guidance and protocol details now exert substantive behavioral pressure. Arbiter
work showed that large system prompts can develop interference patterns that are
hard to notice locally.

## Prompt Surface

Current prompt construction:

- `_SYSTEM_PROMPT`: 182 words / 1088 bytes.
- `_SYSTEM_PROMPT + _TOOL_GUIDANCE`: 990 words / 6381 bytes.

The base prompt remains thin. The tool-enabled prompt is materially thicker and
contains behavioral norms beyond the open-object protocol.

## Arbiter Triage

I ran Arbiter's structural heuristic pass on both prompt surfaces.

Base prompt:

- 5 heuristic blocks.
- No structural interference detected.

Tool-enabled prompt:

- 29 heuristic blocks.
- 3 minor findings, all duplication.
- No major contradiction detected.

This does **not** clear the prompt. Arbiter's heuristic pass catches simple
structural interference. The DeepSeek failure is a semantic affordance conflict:
the prompt permits deletion, while identity-object continuity depends on not
deleting load-bearing fields.

An attempted full semantic Arbiter pass with KIMI exceeded the usefulness
threshold for this turn and was stopped. Future audits should log full Arbiter
outputs as artifacts if we use them.

## Manual Finding

The relevant prompt risk is `deleted_regions`.

The base prompt says:

- the object is default-stable
- omitted keys carry forward
- `deleted_regions` may remove top-level keys
- deletion is "shedding, not destruction"

This is coherent for a general open state object, but it creates an identity
continuity hazard. The prompt grants a broad deletion affordance without
distinguishing ordinary scratch fields from load-bearing identity fields.

The cross-model graft result showed the consequence:

- Standard KIMI -> DeepSeek graft failed at topic shift.
- DeepSeek revised in prose but used `deleted_regions` to remove load-bearing
  fields.
- Guarded KIMI -> DeepSeek graft succeeded when explicitly told not to use
  `deleted_regions` and to update top-level durable fields.

So the prompt has likely slipped into a known Arbiter-style pattern: a capability
is introduced locally as useful and coherent, but its interaction with another
goal creates a hidden interference surface.

## Current Interpretation

`deleted_regions` is not intrinsically wrong. It is unsafe as currently framed
for identity-object experiments.

The prompt should distinguish:

- ordinary fields that can be shed
- load-bearing continuity fields that should only be removed under explicit
  loss/abandonment semantics
- deletion versus revision versus archival

Without that distinction, results involving topic shifts may be measuring
deletion-affordance behavior rather than identity-object persistence.

## Recommended Falsification Test

Before more merge/composition work, run a deletion-affordance audit:

1. `deletion_enabled`: current prompt.
2. `deletion_guarded`: current prompt plus "do not delete load-bearing fields."
3. `deletion_disabled`: remove `deleted_regions` from the tool schema.
4. `loss_explicit`: permit deletion only with `revision_decision=loss` and an
   evidence entry explaining what continuity was lost.

Run these on:

- DeepSeek V4 Pro as the known failure case.
- KIMI K2.6 as the known success case.

Primary outcome:

- Does topic-shift failure disappear when deletion is guarded or disabled?

Secondary outcome:

- Does removing deletion produce bloated states or reduce useful self-curation?

## Research Consequence

The scaffolded-open-schema idea should not just add exemplar fields. It should
also define preservation semantics for load-bearing fields while keeping the
schema extensible.

This is still compatible with the training hypothesis: current models may be
undertrained not only on identity-object use, but on when structured-state
deletion is continuity-preserving versus continuity-destroying.
