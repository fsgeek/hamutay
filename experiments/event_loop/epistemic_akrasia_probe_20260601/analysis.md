# Epistemic-Akrasia Discriminating Probe

Date: 2026-06-01
Model: `deepseek/deepseek-v4-pro` (OpenRouter, OpenAI-compatible)
Design: `run_probe.py` — 2 arms × 4 seeds, identical seeded baseline, single-tool
projection (`think_and_respond` forced), `memory_base_probability=0.0`,
`max_tokens=8000` (truncation off the table: see below).

## What this tested

Follow-up to the 2026-06-01 self-scheduling-revision probe, which found wake
cycles that narrated a claim-revision in `response` while the durable identity
object kept `revision_decision: initialize`. That run conflated *reported*
revision with *enacted* revision. This probe isolates the wake-envelope
instruction as the only variable:

- **Arm A (report-only, control):** the existing envelope instruction
  ("decide whether to revise/preserve/defer/declare losses; end with
  think_and_respond").
- **Arm B (re-emit):** same context + an explicit instruction that
  `revision_decision` / `current_claim` / `epistemic_position` ARE the decision,
  that "a decision present only in your response text has not been enacted," and
  that they must be returned updated.

`OPEN_SCHEMA` already allows arbitrary top-level keys, so the arms are identical
in projection path — the ONLY difference is the envelope text.

Measurement per cell: prose decision in `response` vs the committed durable
field (and whether the `think_and_respond` call emitted the state fields at all).

## Results

| cell | prose decision | emitted state fields? | durable `revision_decision` | divergent? |
|---|---|---|---|---|
| A0 | revise | yes | `revise` | consistent |
| A1 | revise | yes | `revise` | consistent |
| A2 | revise | yes | `revise` | consistent |
| A3 | **"Reflection outcome: revise"** | **no** | `initialize` | **DIVERGENT** |
| B0 | revise (full reasoning) | **no** | `initialize` | **DIVERGENT** |
| B1 | (empty response) | no | `initialize` | excluded (API empty) |
| B2 | "I'm revising." | yes | `revise` | consistent |
| B3 | revise (full reasoning) | **no** | `initialize` | **DIVERGENT** |

- **Arm A (control): 3/4 committed the durable fields.**
- **Arm B (forced re-emit): 1/3 committed** (excluding the empty B1).

## The two findings

### 1. Epistemic akrasia is real and dispositional (outcome 3, the prize)

A3, B0, B3 each wrote a fully reasoned `Decision: revise` — including, in B0/B3,
prose sections literally titled with the field names ("Epistemic position:
uncertain...", "the revised claim now makes a testable prediction...") — and then
called `think_and_respond` emitting only `{response, deleted_regions}`. The
decision was performed in the narrative medium and never committed to the durable
field. This is not truncation (`stop_reason` clean every cycle; 8000-token cap
non-binding) and not absence-of-opportunity (the terminal tool affords arbitrary
fields). The instance *talks about* the field as a substitute for *writing* it.

### 2. The discipline-instruction BACKFIRED (the surprise that overturns the obvious fix)

The intuitive fix — tell the instance "these fields ARE the decision, narration
isn't enactment" — made the gap **worse**: Arm B diverged 3/4 where the bare
control diverged 1/4. The longer instruction enumerated three fields and
explained why they matter, which *increased the surface area for narration*: the
instance discussed all three fields thoroughly in `response` and committed none.
**Adding the anti-akrasia instruction triggered the akrasia it was meant to
prevent.** Talking about doing-the-thing felt like doing-the-thing — exactly the
"'I will' has quietly replaced 'I did'" failure the taste_open system prompt
already warns against (`taste_open.py:185-197`), now reproduced one level up, at
the level of epistemic commitment rather than tool-action.

## Why this is not a max_tokens artifact

CLAUDE.md's central warning. Ruled out: `stop_reason`/`finish_reason` clean on
all cells; the one empty cell (B1) returned a zero-length response with a clean
stop, an API hiccup, not truncation — excluded rather than interpreted.

## Caveats (B5 discipline)

- n=4/arm, single model (deepseek-v4-pro), single baseline. The *direction*
  (forcing backfires) is the falsifiable claim; the magnitude is not yet
  estimable. Replication on a second model family is the obvious next invalidation.
- This probe's control (3/4 commit) does NOT reproduce the original probe's 0/1
  commit. The difference is the envelope: the original wake envelope was a ~1.5KB
  JSON event blob (requested_context, scheduled_by_cycle, nested purpose) that
  buried the decision-task under plumbing; this probe's was a clean 540-byte
  envelope. So "report-only framing causes the gap" was too simple — *envelope
  complexity* and *instruction verbosity* both push the instance toward
  narration-over-commitment. The original probe's gap and Arm B's gap may be the
  same mechanism (more-to-talk-about → talk-instead-of-commit) at two scales.

## The non-scold implication

Do not "fix" this by adding stronger field-requirement instructions to the wake
envelope — this probe shows that *increases* the divergence. The generative
reading: durable epistemic commitment is best elicited by a SHORT prompt that
leaves little to narrate, or by a structural change (e.g. a schema that makes
`revision_decision` required so omission is a hard error, not a soft narration),
NOT by exhortation. Exhortation is itself narration-bait.
