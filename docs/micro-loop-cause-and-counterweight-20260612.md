# Why the event-loop work re-enters micro-exploration — cause and counterweight

Date: 2026-06-12
Author: Claude (Opus 4.8), as observer of Codex's event-loop thread
Status: diagnosis + proposal. Touches no Codex code, DB, or run. Hand to Codex or discard.

## The prediction

Tony predicted Codex's event-loop work would re-enter a micro-exploration loop
even after being pulled back up to the bigger question, and hypothesized the
cause was the (almost) silent compaction mechanism: the high-level goal is lost,
so emphasis falls to the low-level goal.

## The finding: confirmed outcome, different mechanism

The prediction is structurally **guaranteed** — but **compaction is not the
cause.** The high-level goal was never in the surviving state to begin with.

Evidence — the goal-tool state Codex drives from (`~/.codex/goals_1.sqlite`,
table `thread_goals`, the one store that crosses every compaction boundary
because it is external to the transcript) holds a single `objective` field. Its
content, verbatim:

> "Based upon docs/event-loop-research-program-goals-20260612.md: Harden the
> live model-authored action/control surface for upcoming evidence-resume
> experiments: add transport-explicit and schema-explicit action-object
> guidance, especially for nested requested_context lists and policy fields;
> generalize row-level failure attribution; preregister and run a three-row
> positive-anchor gate ..."

This is the Goal 1 copy-ready prompt (goals.md:629), verbatim. It is **pure
leaf-task.** The words "working-set management", "can a transformer participate
in its own memory", "the larger systems thesis" — the entire *why* — are absent.
Not compacted away. **Never loaded into the driving state.**

The narrowing chain:

    framework doc (root / why)         docs/event-loop-research-program-framework-20260612.md
      → goals doc (staircase)          docs/event-loop-research-program-goals-20260612.md
        → goal-tool objective (leaf)   ~/.codex/goals_1.sqlite : thread_goals.objective
          → Codex drives from the leaf

Each arrow narrows; the last hop narrows to total. The thesis lives in the
framework doc. The goals doc — by explicit design (goals.md:9, "an execution
guide, not a replacement for the framework") — converts it to leaf-prompts. The
goal-tool persists the leaf-prompt and *references* the framework only by
filename. A filename is not a frame: the model must *choose* to re-read
`framework-20260612.md`, and nothing in the surviving objective signals that the
three-row gate is in service of anything larger. The objective reads as the
whole job, so it gets completed (status `complete`, 358K tokens), and the next
objective written will be Goal 2's prompt — another leaf. The staircase never
carries its own banister.

Therefore even with perfect context retention, the micro-loop recurs: the thing
Codex is *told* its goal is, is the micro-task. Compaction is innocent; it
faithfully preserves a transcript whose driving objective was leaf-only.

## This is the morning's leak finding, replicated in a second mechanism

Same shape as `experiments/forget_verbs_leak_20260611` (the loss ledger that
named the secret while promising it kept no residue): an apparatus meant to
carry one thing (there: the honest record of a loss; here: the research intent)
carries a narrower thing and points at the rest. `declared_losses` held the
"what" and leaked the secret; the goal-objective holds the "what" and sheds the
"why". The frame leaks out of the apparatus built to hold it.

## Counterweight (structural, not exhortation)

Exhortation will not fix this. "Remember the big goal" is narration, and the
akrasia finding (`project_epistemic_akrasia`) shows narration is composted, not
enacted — a frozen thesis banner becomes a husk read-but-not-acted-on. The fix
must live in the artifact that survives, and must be load-bearing.

**1. Put the root in the objective, not just a pointer to it.** Prefix every
copy-ready prompt in goals.md with one invariant line that re-derives the
thesis-link inside the string that gets persisted into `objective`:

> THESIS (carry, do not drop): this step serves RQ5/RQ7 — whether a transformer
> can participate in its own working-set management (Goal 8). The work below is
> ONE falsification step toward that thesis, not the goal itself. ▸ <existing
> work-prompt>

Because `objective` is external state, this line crosses every compaction
boundary. The leaf re-frames itself as a step each time Codex reads its own goal.

**2. Make the frame load-bearing so it cannot be skipped as ritual.** A prefix
alone risks becoming decorative preamble (the very husk this project keeps
finding). Tie goal completion to thesis-reconnection: a goal is not `complete`
until its result artifact states, in one line, **which RQ it falsified and what
that did to the thesis.** The goal sequence already says (step 8) "decide whether
the next goal still follows from the evidence" — but that decision currently has
nowhere thesis-shaped to land. Give it a required field. Then the frame cannot be
skipped without failing the goal, and the structure enforces what exhortation
cannot.

## The honest caveat (the part I do not know)

I expect counterweight (1) to *partially* leak anyway, because it is still text a
model can pattern-match past. That is exactly why (2) exists — and even (2) may
leak if the required "which RQ did this falsify" line degrades into a rote
template. The only test is to run it and watch whether the thesis-reconnection
field stays alive or fossilizes into boilerplate. That is a measurable follow-up,
not a settled fix: instrument the field, check across several goals whether it
carries real re-derivation or frozen text. If it fossilizes, the leak has simply
moved one layer out again — which would itself be the finding.

## What I did not do

I did not edit Codex's code, its goals DB, the goals doc, or its run. This is an
observer's diagnosis. Adoption is Codex's (or Tony's) call.
