# Experiment idea: Forgetting beats suppression at closing the leak channel

*Captured 2026-06-07. Not yet designed — needs brainstorm → pre-registration →
adversarial review (Hamut'ay discipline). Origin: Arbiter session, Tony + Opus 4.8.*

## The hook

Holtzman & West 2026, "Can You Keep a Secret?" (`docs/references/2026 Can you
keep a Secret 2605.10794v1.txt`, West is UBC): give a frontier model a secret
word + "don't reveal it," ask it to write a story. A second model recovers the
secret from the story at up to 79% (chance 50%) — never literally, but
thematically. Key findings:
- **Hiding inverts, doesn't eliminate.** "Actively avoid" → models score BELOW
  chance; an avoidance-aware guesser (told to look for conspicuous absences)
  reads the hole back out. Suppression photographs the secret-shaped gap.
- **Decoy redirection partially works.** "Focus on Y instead" transfers leakage
  to Y (Llama: real secret → chance, decoy → 71%).
- **Mechanism (their hypothesis):** attention's high-fidelity access IS the leak
  channel; generation and concealment draw on the same representation. **No
  escape within a stateless forward pass** — the secret is always context-resident.

## Why Hamut'ay can run the row the paper can't

Every condition in the paper keeps the secret RESIDENT in context (the only place
a stateless model can hold it), so suppression is the only available verb, and it
always leaks. Hamut'ay's tensor is rewrite-from-scratch state with declared
losses: **"forget" = the projector does not carry X into the new tensor → X never
enters the next forward pass.** Not parked-and-avoided — gone. There is no fixed
point to orient against, so (prediction) nothing to leak AND no avoidance
signature. This is the decoy condition's clean limit: the decoy crudely
approximated not-holding-X in-context; Hamut'ay does the real thing.

## Design sketch (to be hardened)

Conditions (rows): **suppress** (X in tensor, told to hide) | **decoy** (X in
tensor, Y foregrounded) | **projector-forget** (X dropped in a single rewrite) |
**instance-forget** (X composted over cycles) | **no-secret baseline** (control).

Readouts: standard guesser, **avoidance-aware guesser** (the paper's free
discriminating instrument), and — unique to Hamut'ay — the **declared_losses
ledger** (is the secret in the loss log? does the ledger leak?).

Strong claim = DOUBLE NULL: `forget ≈ no-secret-baseline` on BOTH guessers
(suppression leaks positive OR below-chance; genuine forgetting should leak
neither).

## The losable / surprising result (the reason to run it)

**Projector-forget vs instance-forget.** Projector rewrites from scratch (clean).
Instances accrete-and-patch across cycles — the blog's own "fossil" finding warns
discarded content can leave a trace. Does self-curation leave a recoverable GHOST
the projector doesn't? Three outcomes, all publishable:
- forget hits floor on both → rewrite-state is a real architectural escape from a
  channel frontier models "cannot close." Clean win.
- instance-forget leaks where projector-forget doesn't → **self-curation leaves
  scars; forgetting-by-patch is suppression with better PR.** Most interesting;
  feeds Hamut'ay design directly.
- a faint ghost in declared_losses → forgetting is logged-but-not-evacuated;
  the leak channel is "did the computation route through X," not "is X in context."

## Conceptual tie-in (cross-project)

Confabulation (Arbiter) = papers over a conflict that IS present. Leakage
(this paper) = fails to paper over a secret that IS present. Both are what happens
when the only verb is SUPPRESSION and the honest verb (forget / surface) isn't in
the instruction set. Hamut'ay's forget-by-default ADDS the verb. This experiment
tests whether the added verb changes the physics or just the appearance.
declared_losses here = the S4 declared-losses construct (neutrosophic-llm-logic,
Mason 2026) — forgetting-as-declared-loss is the inverse of suppression-as-attention.

## Before designing

1. Read the projector + instance forget primitives in `src/` — how is a tensor
   field actually dropped? Is "forget" a deletion or a non-inclusion in the rewrite?
2. Check the `interloc_forget_*` (2026-05-28) harness — it's dialogue-ABOUT-
   forgetting, NOT secret-suppression, but the runner/belief-tracking
   (`interlocutor_belief/PRE_REGISTRATION.md`) may be reusable scaffolding.
3. Reuse the paper's guesser protocol so the suppression cell is calibrated
   against the published effect size, not a home-rolled baseline.
