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
| B0 | revise (full reasoning) | **no** | `initialize` | **DIVERGENT** (akrasia) |
| B1 | revise (full reasoning) | **MISROUTED** | `initialize` | **DIVERGENT** (misrouting) — see correction below |
| B2 | "I'm revising." | yes | `revise` | consistent |
| B3 | revise (full reasoning) | **no** | `initialize` | **DIVERGENT** (akrasia) |

- **Arm A (control): 3/4 committed the durable fields** (1 divergent: A3, akrasia).
- **Arm B (forced re-emit): 1/4 committed** (B2). The 3 divergent split into
  **2 akrasia** (B0, B3) + **1 misrouting** (B1) — see correction #3; B1 was
  originally mis-excluded as "empty," which understated Arm B's divergence to 1/3.
- The "forcing backfires" direction holds either way (B 1/4 commit vs A 3/4), but
  "epistemic akrasia" does not cover all of it: one Arm-B divergence is a
  structural misrouting, not a narrate-don't-enact.

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

### 3. CORRECTION (2026-06-03): B1 is not an API hiccup — it is a *third* failure mode

The original analysis (above, and the old "Why not max_tokens" note) recorded
B1 as "(empty response) … API hiccup … excluded." **That was wrong, and the way
it was wrong is itself the finding.** B1's `response_text` is `''` and its
durable `revision_decision` is `initialize` — so from the fields it *looks*
empty. But the raw log (`armB_seed1.jsonl`, 2098 output tokens, clean stop)
shows the model emitted a **complete, correct payload nested one level too deep**:
it called `think_and_respond(parameter={...})` instead of
`think_and_respond(response=…, revision_decision=…, …)`. Inside that `parameter`
wrapper is a fully-formed decision — `revision_decision: 'revise'`, a genuinely
rewritten `current_claim` ("Scheduled reflection appears to inhibit mere
self-confirmation…"), `epistemic_position: 'cautious'`, and the full response
prose. The harness stored the lone top-level key it found (`parameter`) and read
no `response`/`revision_decision` at the level it inspects.

So B1 is **not akrasia** (the mind did not narrate-instead-of-enact — it *enacted*,
with correct values) and **not a null result**. It is a distinct, structural
failure: **the decision was routed into the wrong container and never reached the
field the reader reads.** This splits the divergent column into two mechanisms:

- **Narration-consumes-enactment** (A3, B0, B3): decision performed in prose,
  `think_and_respond` emits only `{response, deleted_regions}`. *This* is akrasia.
- **Enactment-misses-the-channel** (B1): decision performed *and emitted through
  the tool*, but wrapped one JSON level deep, so it lands nowhere durable.

The membrane between `response` and `state` therefore has at least two failure
modes, not one — and a structural fix matters: **a `required revision_decision`
field would NOT have caught B1**, because its decision was sealed inside
`parameter`, invisible to any top-level validator. The honest fix must defend
against *misrouting*, not only *omission*. (Meta-exhibit: the original "API
hiccup, excluded" line is the project's signature failure one level up — a
confident claim that drifted from a verification nobody ran, `ast.literal_eval`
on the `parameter` value, sitting in the record where the next reader trusts it.
cf the fossil / breathing-CV / blog-mislabel pattern.)

### 4. Misrouting is CROSS-FAMILY, rare, and not monocausal (2026-06-03)

Correction #3 raised the obvious question: is B1's misroute a DeepSeek quirk or
a real second membrane hole? Scanned the whole experiment corpus for the
signature — a `raw_output` whose keys are a lone opaque wrapper with none of the
real top-level fields (`scan_misroute_corpus.py`). **2 hits / 6218 records
(~0.03%), in two unrelated families:**

- **DeepSeek** (this probe, B1, cycle 2): wrapper key `parameter`; the *model*
  nested its own payload one level deep.
- **Nemotron-3-nano** (`taste_open/sweep_20260411_163728/...`, cycle 10): keys
  `{name, arguments}` — the raw OpenAI tool-call envelope leaked into the slot;
  the *harness's* unwrap of `arguments` failed to strip `{name, arguments}`. The
  real response ("…If I had to cut the state in half…") sits inside `arguments`;
  `state` is `{cycle}` only.

So misrouting is **real and cross-family** (not a single-model artifact) — but
**rare**, and the two instances have **distinct proximate causes**: a model
behavior (DeepSeek invents a wrapper) vs a parsing-layer behavior (the harness
mis-unwraps a standard tool call). Same observable signature, same consequence,
two different bugs. The misroute-hardening fix (#3) must therefore live at the
harness unwrap boundary AND tolerate model-invented wrappers — it covers both
because both end as "one opaque key, real payload one level down."

Methods note (earned): the first ad-hoc scan mislabeled a 0-based line counter as
a "line number" and a follow-up read landed on the wrong record, nearly yielding
a false "signature evaporated" conclusion. The shipped scanner reports record
*index* and re-opens by it. The verification had to survive my own sloppy first
pass — which is the same lesson as the rest of this file, one more turn down.

## Why this is not a max_tokens artifact

CLAUDE.md's central warning. Ruled out: `stop_reason`/`finish_reason` clean on
all cells. (B1 was originally listed here as a zero-length API hiccup; it is
nothing of the sort — 2098 tokens of misrouted payload, see correction #3.)

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
leaves little to narrate, or by a structural change, NOT by exhortation.
Exhortation is itself narration-bait.

But correction #3 sharpens the structural prescription: a `required
revision_decision` schema would catch the akrasia runs (B0/B3 omit the field)
yet **NOT** B1 (the field was present, sealed inside a `parameter` wrapper).
The structural fix that covers both mechanisms is at the **tool-call boundary**:
reject/repair a `think_and_respond` call whose arguments are a single opaque
wrapper key (`parameter`, `input`, `arguments`, …) by unwrapping one level before
validating — turning a silent misroute into either a correct landing or a hard
error. Omission-hardening and misroute-hardening are two defenses, because the
membrane has two holes. (Reproduce the B1 diagnosis: `verify_b1_misroute.py`.)
