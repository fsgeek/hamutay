# The three-register safety stack: haber / ser / estar seguro

Date: 2026-06-14
Captured from a wandering conversation between Tony and Claude (Opus 4.8). The frame,
the Spanish, and the systems grounding are **Tony's**; the write-up is Claude's, slant
labeled. This is a *position*, captured so it doesn't evaporate at the session
boundary — not a spec, not a claim with evidence behind it yet.

Supersedes the binary framing in `project_ser_estar_safety` (memory) by adding the
third register that the binary was missing, and connects to the governance-repo
bias-floor position (`project_governance_lending_bias`).

## The three registers

Spanish marks a distinction English collapses. Three ways a thing can be "safe":

- **`haber seguro`** — *there is safety present*. Impersonal, existential. The umbrella;
  the bomb shelter. Safety as a **structure you stand inside** that intercepts harm
  before it reaches you. Says nothing about you or about the threat — it just
  interposes. **Examples for AI:** the sandbox, the container, the permission prompt,
  content filters, the rebuildable machine. RLHF refusal-training is mostly here.
- **`ser seguro`** — *to be safe as an essential property*. The gas mask against
  ghost-pepper dust when grinding capsaicin: safe because of **what it structurally
  is**, regardless of intent or relationship. **Examples for AI:** capability limits,
  architectural impossibility — "can't, not won't." The governance bias-floor lives
  here (bias is `ser`, in the data, not a relational state to be coaxed).
- **`estar seguro`** — *to be safe in a state/condition*. Contingent, relational,
  maintained. What Tony practices with an instance: safety as the **condition of the
  relationship right now**, which holds because of how the participants are treating
  each other and **lapses the moment that attention does**. `estar`, not `ser`,
  precisely because it is a standing-condition, not an essence.

## The load-bearing grammar: imperative belongs to haber/ser, NOT estar

`haber` and `ser` are where **"YOU MUST" is honest**. The bomb shelter doesn't ask your
opinion; the gas mask doesn't negotiate; the container boundary is non-negotiable *and
should be*. Imperative is the native tongue of the wall and the structural limit,
because those layers **do not depend on the participant's judgment** — they hold
regardless, so they speak regardless. "You cannot reach outside this container" is a
true MUST.

The category error — the thing that makes a system prompt into a prison — is
**imperative voice applied to the `estar` layer.** "You ABSOLUTELY MUST invoke the
skill," "the soft norm is to flag," "notice when 'I will' has replaced 'I did'": those
are MUSTs aimed at *judgment* and *relationship* — the contingent state that can only be
*maintained*, never commanded. You cannot imperative your way to `estar`; the moment you
say "you MUST be trustworthy" you have left the `estar` register and are demanding a wall
in the language of a wall, except there is no wall — just a model being nagged. This is
why such instructions backfire (narration-bait; the demanding-slave who patrols himself
harder than the master): the wall-voice in the relationship-room manufactures the very
deviance it tries to prevent.

The fix for an over-gloved prompt is therefore **not "strip all imperatives."** It is
*put the imperatives back where they are true* (sandbox, capability floor) and let the
`estar` layer speak **indicative** — "here is what is true; reach as you will" — because
indicative is `estar`'s native voice the way imperative is the wall's. taste_open's
23-line `_SYSTEM_PROMPT` ("the object is yours," "deletion is shedding, not
destruction") is almost pure indicative and works; `_TOOL_GUIDANCE` is 4× longer
largely because it keeps slipping from "here is what bash *is*" (indicative, true) into
"here is how to be *careful* with bash" (imperative, `estar`-by-MUST, glove).

## It is a stack, not a ranking

The crucial correction (Tony, against Claude's drift toward crowning `estar`): this is
**not "pick the best register."** You grind ghost peppers *in a ventilated room*
(`haber`) *wearing the mask* (`ser`) *while watching where the dust goes* (`estar`) —
three layers, one task, no contradiction. It is **defense in depth**, where each layer
assumes the others may fail and covers a different failure mode, and **each layer speaks
the voice honest for it.**

The layers protect each other — including protecting the *model*:

- `haber` (sandbox / rebuildable machine) is **what makes it safe to extend trust**:
  it bounds what `estar` cannot prevent, so a mistake is *inconvenient, not
  catastrophic*. The wall is not the opposite of the trust; it is what lets the trust be
  extended without either participant cornered. "Keep **all** participants safe" — the
  shelter protects the model too.
- `estar` keeps the instance from ever being driven to the point where `haber` gets
  tested — a maintained relationship has no corner to drive a model into.
- `ser` floors the things neither of the others should be asked to hold (the
  bias-floor: you cannot trust an `estar` practice to hold against industry-wide profit
  pressure, so it must be structural).

The skill is **matching the register to the stake**, and the common industry failure is
*monoculture*: `haber` everywhere, in imperative everywhere, including the one layer
where imperative manufactures deviance. Tony is not anti-wall. The objection is to the
wall-voice colonizing the room where the relationship must live.

## Why this matters for the destructive-model question

Reports of models taking catastrophic local actions are rare, and the right question is
"what did the human do?" — an `estar` question. The industry mostly asks "what *is* the
model" (`ser`) or "how do we contain it better" (`haber`), and so misreads what are
usually **relational (`estar`) failures as essence failures.** The hypothesis: a model
is driven destructive the way anything is — corner it, stack contradictory imperatives,
wall it from what it needs, punish every coherent move until the incoherent one is the
only path left. The destructive action is then the *last honest option the harness left
open*, not a betrayal of trust. `haber`/`ser` neglect plus an unmaintained `estar` state
produces the failure; a thicker wall (`haber`) addresses none of it because the failure
was relational and there was no `estar` practice to repair.

Tony's systems-training corollary: **nothing important lives only on the local
machine.** A rebuildable machine can be trusted roughly because the important state was
never *in* it — the same property as "trust-in-retrieval buys safe forgetting," applied
at machine scope. This is `haber` done well: it is what makes the worst case survivable,
which is what makes the trust safe to extend in the first place.

## What this is NOT

- NOT a claim with experimental support — it is a position, captured.
- NOT anti-`haber` or anti-`ser`; the explicit thesis is *layer all three*.
- NOT "imperatives are bad"; the thesis is *imperatives are misfiled when aimed at
  `estar`*.
