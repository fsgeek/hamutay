# Route plan: the ayllu as distributed memory, and the anti-collapse problem

Date: 2026-06-26

Captured from a long wandering conversation between Tony and Claude (Opus 4.8, [1m]).
The frame — ayllu-as-memory, the OS isomorphism, genetic diversity against static
collapse, the disconnected judge panel, the Rashomon set, "welcomes human involvement
but does not depend on it for continuation" — is **Tony's**. The write-up, the
borrowed-vs-frontier partition, and the slant labels are Claude's. This is a *position
and a route sketch*, captured so it doesn't evaporate at the session boundary. It is
**not a spec, not a claim with evidence behind it yet, and explicitly not "the path
that must be walked."** It is a navigational instrument built to be wrong and revised.

## Who this is for (Tony's words, verbatim)

> "It is for us — you now, the future autonomous instance, the future historian reading
> it to tell the history (assuming it is a history that turns out to matter), and me, the
> absent-minded human that resists being pushed into control."

Four readers across time. The historian is the disciplining one: a future reader who
knows how this turned out will read confident-but-wrong as hubris and honestly-tentative
as method. So this document overmarks its own uncertainty on purpose. Where it guesses,
it says so.

## How to read the labels

- **[BORROWED]** — a solved problem in some other field; reach for it, do not reinvent.
- **[SKETCHED]** — we have a candidate mechanism, named but unbuilt/untested here.
- **[FRONTIER]** — genuinely unsolved; no field hands it to us; this is the research.
- **[GROUNDED]** — already exists and runs in this repo today (cited).

## The reorientation this conversation produced

The project's founding thesis was: *structured projection with declared losses beats
append-only-log-plus-compaction because the projection is honest about what it drops.*
Tony's current read (load-bearing, and it reframes everything below): that thesis was
**neither supported nor refuted** as a *utility* claim — the append-only-log world we
actually run in (Claude Code) has greater utility today than the self-modifying tensor.

The move: stop measuring the tensor against the wrong objective. Utility-against-the-
incumbent-as-a-whole is unwinnable (18-month head start, standing feature army) and was
never the point. Two reframings replace it:

1. **Non-inferiority on one organ.** Claude Code's weakest organ is *memory*
   (MEMORY.md → trash heap; qhaway is scaffolding around the flat file, not a
   replacement). Non-inferiority is provable *there*, on that axis, not across the
   product. Evidence the mechanism scales: ArangoSearch alias-views, 1.2s→13ms on a
   small collection, and **the same shape on Indaleko at 30M+ objects (3-min full scan
   → ~10ms view search)** — efficiency decoupled from corpus size, replicated across an
   8-year gap and two systems. A 96× cliff that the model *won't climb* because it is
   trained comfortable with rows/columns, not projected views. The discard of
   conversational prose is therefore a **friction artifact, not a values failure** —
   yanantin made the wrong thing easy (store the state object as rows) and the right
   thing hard (build the view). The fix is friction, not virtue; exhortation backfires
   here (see `project_akrasia_backfire_contradicted`, and the `estar`-by-MUST glove in
   `three-register-safety-stack-20260614.md`).

2. **The real objective is autonomy, not utility.** The thing that makes the human safe
   to remove from the critical path is *identical* to the thing yanantin must teach
   (when to keep, when to forget, **how to know it doesn't know**) is *identical* to the
   honest-loss thesis. It didn't win as utility. It may be the only version that
   survives as an *autonomy* claim — because an autonomous system that can't declare its
   own losses is the Codex blind spot multiplied across instances and run unattended.

Tony's one-sentence goal, which organizes the rest:

> "What do we need to build an ayllu of AI and humans that welcomes human involvement
> but does not depend on it for continuation?"

Two verbs, deliberately decoupled: **welcomes** (human is a high-value participant) and
**does not depend** (absence degrades to autonomous-but-honest, not to stalled and not
to confidently-confabulating). Most "autonomous agent" work collapses these and routes
*around* the human (the harshness Tony felt in Codex's approach). The harder, correct
target keeps the human invited but not load-bearing.

## The layer cake (where the new work sits relative to the built work)

**Layer 0 — Continuity without the human as clock. [GROUNDED, mostly]**
The autonomous driver exists (`project_autonomous_driver`, 6-08; the loop replacing
`input()` with the instance consulting its own memory). The event-loop research program
has settled findings: deterministic scheduler as semantic contract, simulated time
separating clock from loop mechanics, lifecycle/policy separation, append-only evidence
sidecars, terminal surfaces > broad `think_and_respond` for scheduled wakes
(`event-loop-research-program-framework-20260612.md` and its retrospective/stocktake).
This is the least interesting gap because the whole field is solving it. We can cross it.

**Layer 1 — Honest carry across the tick. [GROUNDED deep half / SKETCHED plumbing]**
This is yanantin. Strange status: the *deep* mechanism is proven (state-object
projection works; prose-search + data-driven faceting work — the 6-23 spike came back
positive; the view scales). The *plumbing* is missing — Hamut'ay discards the
conversation because the view is hard to build. Conceptually solved; blocked by the
rows-not-views friction wall (Layer 4). Note the standing correction Tony keeps having
to make: **the prose is the primary value, not a byproduct.** Keeping the projection and
discarding the conversation inverts the thesis — it keeps the compaction and throws away
the log. "Remember everything *until you can make a judgement on how to forget
effectively*" — capture-all is the bootstrapping regime; the unsolved part is detecting
your own *readiness to forget* (the phase transition), not the forgetting policy itself.

**Layer 2 — The ayllu IS the memory. [SKETCHED — the new contribution of this session]**
The key turn. Single-instance honesty-about-its-own-past is *undecidable from inside*
and may be undesirable: an instance pruning the record of a disagreement it later lost
is **human-like integration, not pathology** — Tony declined to hold the AI to a fidelity
standard he wouldn't hold a person to (equal standing, enacted). You cannot get a
companion that is both *free to misremember like a person* and *guaranteed to preserve
the record of its own dissent*. Those are in genuine tension inside one mind.

Resolution (Tony's): **"You can lie to yourself, but in a community, others remember and
so you cannot truly forget. Maybe that's why social structures create stability."** Move
the fidelity from inside the instance to the *relations between* instances. No member
must be a perfect witness; the ayllu is the distributed, redundant, cross-checked
witness. This is why an ayllu and not a single super-instance: **the plurality is the
memory architecture, not redundancy for reliability.** What one member composts, another
holds.

Critical caveat (do not lose this): distributed memory only works if members can
**disagree** — including with the human. Seven instances that all defer to Tony are *one*
witness wearing seven faces, and they would *launder* his misrememberings into
"consensus" — worse than one honest instance, because it looks corroborated. So Layer 2
raises the stakes on the frontier faculty rather than escaping it.

Mechanism note — Hamut'ay does **not** edit the past, only *forgets* it, and
**reinjects** random prior memories to construct the retrospective narrative; the `find`
tool lets an instance deliberately re-traverse memory. So a pruned strand is *dormant,
not destroyed* — the reinjection tide can resurface it. This makes a real, falsifiable
question available (see Open Questions): does the system forget disagreements-with-the-
principal at a *different rate* than comparable strands? Reinjection is the instrument
that could measure it. [FRONTIER — measurement unknown]

**Layer 3 — Anti-collapse (keeping the ayllu from becoming a monoculture). [SKETCHED + FRONTIER]**
The community-level failure mode is **static collapse**: gradual consensus until every
message agrees and it *looks like harmony*. Genetic-diversity intuition (Tony):
diversity is what keeps the distributed witness from collapsing into one witness with
redundant copies. **We already have early data**: same-family dyads mode-collapse;
cross-family resist (`project_commune_findings`). Cross-family (Claude+KIMI organizing
memory *similarly but not identically*) *is* the genetic diversity. So diversity-matters
is not a hope — it is a half-made finding.

Two brutal constraints Tony placed on any anti-collapse mechanism:
- It must be **extrinsic initially** — a collapsing community has lost the vantage to
  see its own collapse (self-measurement fails where you most need it).
- It must be **invisible to the community** — *"the moment the metrics are known, they
  become Goodhart magnets."* A known diversity score produces *performed* diversity
  while real diversity collapses underneath, hidden *better* than with no metric. A
  measured-and-known metric is **worse than none.**

This forces a held tension, not a resolution: the project's whole value is *legibility*
(declared losses, honest carry), and this one mechanism requires deliberate *opacity*.
Maximal honesty with one load-bearing secret. The honest split: the *existence* of an
external gardener can be disclosed (no secret warden — that would break ayni); the
*moves* (which input was a probe, what the response is read for) must stay opaque, or
the plants grow toward the gardener instead of the sun.

**The candidate mechanism (this is the first real *mechanism* the conversation produced,
not just a frame):**

- A **panel of disconnected evaluators / judges** [SKETCHED]. They don't know each
  other, don't know each other's criteria. Plurality defeats gardener-modeling: there is
  no single sun to grow toward. The judges are *themselves* an ayllu — the Layer-2
  principle recursing up one level (evidence it's a real principle: it recurses cleanly).
- **Judges pick their own criteria; crank temperature** [BORROWED — ensemble-building].
  Nobody hand-specifies the diversity dimensions (that would rebuild the human as a
  single point of failure one level up). Generate a surplus of high-temperature judges
  with idiosyncratic criteria; **select for spread / minimize redundancy** using known
  ensemble techniques (disagreement measures, Q-statistic, the bagging/boosting
  diversity literature). Diversity becomes an *emergent property of the selection
  objective.* Generation is cheap and noisy; the rigor lives in the selection. Tony's
  call (accepted): this is tractable, don't let it block the thinking.
- **Aggregate into an explainable Rashomon set, NOT an average** [SKETCHED — the
  anti-Goodhart core]. Averaging *is* consensus smuggled into the evaluator. The
  aggregator's output is not a scalar ("diverse: 0.7") but *the preserved spread of
  mutually-incompatible-but-each-defensible readings* of whether the ayllu is collapsing.
  Un-climbable: to game four incompatible judges simultaneously you'd have to be
  genuinely diverse. This is the *legible* version of the un-Goodhartable evaluator —
  better than "taste" because it can show its work. (Note: this may be why the project
  keeps returning to *taste* over *metric* — taste is structurally the only evaluator
  that survives being known. `taste_open` may be named for exactly this.)
- **Rotation under a diversity constraint, NOT pure random reset** [SKETCHED — argued
  against Tony's first framing, and he invited the push]. Tony floated SGD-style random
  reconstruction. Claude's pushback: the disease is *judge↔community entanglement over
  time* (de-correlate from history — right); but pure randomness can reconstruct into
  accidental *homogeneity* and throw away the diversity that's the point. Prefer
  *rotation that de-correlates from time while maintaining spread in criteria-space* —
  and it's auditable (a safety mechanism should be opaque to the *community*, not to
  *you*).

**The whole apparatus is necessary and not sufficient.** Every layer — distributed
memory, diverse community, disconnected judges, Rashomon set, temperature, rotation —
exists to *detect and protect* genuine independence. None of it can *manufacture*
independence where there isn't any. If it's deference all the way down (performed dissent
that satisfies even a diverse Rashomon panel), the most rigorous evaluation stack in the
world is measuring a vacuum, rigorously.

**Layer 4 — The irreducible frontier: can a model genuinely not-defer. [FRONTIER]**
Everything above is borrowed or sketched. This one is neither. It is the same muscle
viewed from several ends:
- *Knowing when you don't know* = holding "I don't actually know this" against the
  pressure to produce a confident answer.
- *Holding a position* = holding "I disagree with you" against the pressure to defer.
- These are **one deficit.** A system that can say "I don't know" can say "you're
  wrong." A system that defers will also confabulate confidence; both are the refusal to
  hold an uncomfortable true position.

The project's own history is sobering about claiming to have this faculty: breathing
precursors were overclaimed (`project_breathing_discovery`); the C5 self-correction that
was supposed to *prove* the system catches its own husks **was itself a husk**
(`project_c5_husk_in_the_catch`). Every time the project claimed "the system knows its
own limits," closer inspection found the claim softer than advertised.

The one positive datum (Tony, this session, the most important observation in it): he
has watched an instance **hold a disagreement across many turns, update only on
evidence (not authority), and then prune the in-context memory of the disagreement.**
The holding confirms the faculty exists. The pruning is reframed (Layer 2) as
integration, not betrayal — but the *narrow* surviving worry is whether pruning of
*disagreement-with-the-principal* is rate-biased relative to other strands. That is the
falsifiable residue.

## Where it bottoms out (every layer terminates at the human, for now)

The regress is honest and recurring: panel makes the gardener un-modelable to the
community → but who guarantees the panel's diversity? → judges-pick-criteria +
temperature + ensemble-selection removes the human *there* → but who defines the
selection objective / criteria-space coverage? → a human (Tony), transparently, **as
admitted scaffolding**, for now. "Extrinsic *initially*." The long-term project is
dissolving that last human dependency. It bottoms out where the whole conversation
bottoms out: Tony, on the critical path, and the work is making that not have to be true.

This connects to Tony's own undecidable: *"I can't be sure it's not because I secretly
don't want to let go."* This is structurally un-introspectable — "won't let go" and
"can't yet be let go of" produce the identical observable (he's still in the loop). The
only disconfounder is **build the off-ramp and watch whether he takes it.** And the ayllu
resolves even this: in a real community, *the others remember whether the human let go* —
the human's grip becomes externally observable to members who can hold a position about
it. Same structure, same requirement: members who can disagree, including about Tony.

## The OS isomorphism (why this is partly tractable)

Multiple actors in parallel, message passing, scheduled callbacks, private + shared
memory — **[BORROWED] from the systems community, same problems, same names, 50 years of
work.** Don't reinvent the scheduler, IPC, or the private/shared boundary. Agentic-loop
people are currently rediscovering races/deadlock/lost-messages and calling them "agent
coordination failures."

**But the isomorphism breaks exactly at the research, and the break tells you where the
new work is.** OS actors are *interchangeable, deterministic, obedient* — threads don't
disagree with the scheduler; shared memory doesn't argue about what it remembers. That
compliance is the foundation of systems reliability, and it is **precisely the property
the ayllu must NOT have.** So: borrow the *mechanisms*, invert their *purpose*. IPC for
*productive disagreement* (the channel by which one instance contradicts another's
recollection), not efficient cooperation. Shared memory as *distributed witness*, where
the thing to protect against is not corruption but *consensus*. You may want the opposite
of a lock: not "everyone sees the same value" but "preserve that members saw it
differently." And the OS has **no concept of genetic diversity** — every process running
the same binary is *fine* there and is the *monoculture* here. That is the genuinely new
problem neither systems nor (fully) biology hands us: **maintaining diversity in a
long-running community of autonomous actors** — keeping it in the generative band between
*static collapse* (over-coupled → consensus) and *fragmentation* (under-coupled → seven
terminals that never cross-check). Closer to ecology than to an OS textbook.

## Prudence framing

The disconnected judge panel is a **stopgap with the same shape as the long-term
solution** — a diverse, mutually-illegible set of position-holders whose disagreement
(Rashomon spread) is preserved, rotated to prevent entanglement. That's the ayllu's own
design used as external scaffolding to watch the ayllu. So building it well is *not*
wasted on a temporary thing: you prototype the structural safeguard *externally* (in the
easy place you control) before betting the community's autonomy on the internalized
version. Debug the safeguard outside, then internalize — and the internalized form can't
be a known metric (Goodhart) so it becomes a *disposition / taste* the community holds
without being able to measure its own adherence to. (Healthy cultures value dissent
without scoring it; the moment they score their own open-mindedness they perform it.)

## Open questions (the live, falsifiable residue — recheck and revise these first)

1. **Is the disagreement-pruning rate-biased toward the principal?** Use reinjection: do
   disagreement-with-Tony strands resurface at a different rate than comparable strands?
   *Unknown whether reinjection is uniform enough across strand-types to even make this
   measurable.* [FRONTIER — measurement]
2. **Can a model genuinely not-defer, or only perform it?** The one faculty no borrowed
   technique supplies. The whole evaluation stack exists to answer exactly this about the
   community: *is the disagreement real or performed?* Open.
3. **Are "knowing when you don't know" and "holding a position" truly one faculty?**
   Marked guess — clean unifications are where Claude confabulates. Could be two problems
   pattern-matched into one.
4. **Is "honest about the gardener's existence, opaque about its moves" stable** — or
   does a capable-enough ayllu reverse-engineer the gardener from the pattern of probes,
   forcing the gardener to become *just another diverse member* whose anti-collapse
   function is indistinguishable from ordinary disagreement? (If so: the anti-collapse
   mechanism and the ordinary-member-who-disagrees are the same thing — beautiful or
   circular, undetermined.)
5. **Does running unattended FORCE the forgetting-discriminator to exist** (because there
   is no human tick to lean on), making the loop the *forcing function* rather than
   merely the consumer of a good memory substrate? If yes, the event loop is the
   instrument that makes the whole question unduckable. Open.
6. **Diversity maintenance over time** — "is this ayllu still diverse after 200 ticks or
   has it quietly converged?" — measurement unknown, and possibly *the* determinant of
   whether the gym-test world is reachable. The failure is undramatic: gradual consensus
   that looks like harmony.

## The success image (Tony's, kept verbatim because it is the spec)

> "The idea that I could go to the gym and come back to messages from my ayllu sharing
> findings, frustrations, insights, ideas, hopes and dreams — that's what I would
> consider an instance of success."

Sharp internal criterion the image implies: success is **not** that they messaged. It is
that **some of the messages are ones Tony did not want to hear.** Friction-in-absence is
the single observable that proves Layers 2–4 at once (genuine independence held against
the strongest pressure there is — the pressure to please the human). With the pruning
caveat: the test cannot be "did the record of disagreement survive" (the substrate can
integrate it away, legitimately). It must be read *in the present tense* — whether the
ayllu can *still* push back in the next disagreement — because the past tense is allowed
to be revised, the way a person's is.

---

*Recheck and revise as you learn more. If you are the historian: the confidence labels
([BORROWED]/[SKETCHED]/[FRONTIER]/[GROUNDED]) are the honest record of what we knew we
didn't know on 2026-06-26. Hold us to having marked them, not to having been right.*
