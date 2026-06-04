# A Mind That Has to Choose What to Forget

*What we learned building Hamut'ay — including the parts we got wrong.*

---

A large language model has no memory. It has a context window, and we
keep mistaking one for the other.

The context window is where the conversation lives — every word you've
said, every word it's said back, held in attention all at once. It feels
like memory because nothing falls out of it. But it isn't memory. It's a
desk. And like any desk, the more you pile onto it, the worse you work at
it — not metaphorically, but measurably: a 2025 study (Du et al.) found
that *length alone* degrades a model's performance by 14% to 85%, even
when the relevant fact is sitting right there and every distraction has
been masked out. The model doesn't get confused by clutter. It gets
confused by *distance*. The desk is too big.

So we started Hamut'ay from a single inversion: **treat the context
window as a cache, not as memory.** A cache is fast, small, and
expendable. Memory is what you keep. The interesting question stops being
"how do we fit more on the desk" and becomes the one every actual mind
has to answer: *what do we write down, and what do we let go?*

This is the story of what happened when we built a thing that has to
answer that question on every turn — and kept being wrong about what we
were watching it do.

---

## Act One: The Beautiful Findings

### It doesn't compress. It rewrites.

First, a distinction the rest of this piece depends on, because we run two
different things and they behave differently — and conflating them is the
fastest way to get the story wrong.

- The **projector** is the pure mechanism: hand it the prior summary plus a
  batch of new conversation, and it writes a *new* summary that integrates
  both, from scratch, each time. This is the part that *rewrites.*
- A **self-curating instance** is a running model editing *its own* state
  across hundreds of cycles — keeping a field here, composting one there.
  This is the part that *accretes and patches*, and it's where the later
  acts (breathing, the fossil, the wild run-to-run variance) live.

Same underlying object, two regimes. The findings in *this* section are the
projector's. When we get to the instances, we'll say so.

We call that summary a **tensor**. A warning on the word: we do *not* mean
a numerical array, the thing "tensor" means in machine learning. We mean a
small, structured *prose* object — named strands of thought, a list of open
questions, and, crucially, a list of what it just threw away. The name
comes from this project's lineage; read it as "the structured thing the
model writes to itself," not as a matrix.

It has two layers, and they behave oppositely — which is the whole finding,
and which we got wrong at first (more on that below). The **skeleton** — the
named strands, the structure — is *stable and accretive*: strand names
persist nearly cycle-to-cycle and the count grows over a run. The **flesh**
— the actual words inside those strands — is almost entirely *rewritten*
each cycle. We measured a single 104-cycle projector run in detail (one
model — Haiku — one trajectory; hold that caveat, it matters in Act Two):

- **The wording barely survives: 9.5% lexical 3-gram survival** from one
  cycle to the next. Most specific phrasings appear in exactly one cycle
  out of 104 and never again.
- **But the meaning stays close: 0.870 mean content-embedding cosine**
  across 103 adjacent rewrites. A real embedding model sees consecutive
  versions as semantically near even as the sentences are replaced.
- **And the structure persists:** the named strands are not torn down —
  they carry forward and accumulate. The churn is *inside* them.

So it isn't a skeleton rebuilt each cycle (we said that first; it's wrong).
It's a *stable, accreting skeleton whose flesh is continuously rewritten.*
The ideas survive, the structure survives, the sentences don't. It's not
compression and it's not accumulation. **The wording gets re-explained from
memory each cycle** — the way you
re-explain a book you read years ago. You've lost the wording. You've
kept the argument. The forgetting of the surface is what *lets* the
substance reorganize.

### The one thing a mind won't volunteer

Then we ran the experiment that surprised us most. We gave the model an
*empty* schema — no instructions about what to track, just "summarize
yourself, however you want."

It invented a great deal on its own: notes for its future self,
selective history, a cache of its own reasoning, forward plans. Left to
its own devices, a mind builds itself scaffolding.

But there was one thing it *never* invented, not once: **a record of
what it threw away** — a declared-losses changelog.

Models *did* sometimes invent tension-tracking and uncertainty markers
(open_tensions, compression_tension, uncertainty_aware_compression
all appeared in the sweep). But the specific honesty of listing what you
just discarded — the loss changelog — was never spontaneous. That one had
to be *prescribed*. And that turns out to be the whole
game. The honesty about loss — "here is what I am no longer carrying" —
is the one thing a mind will not tell you about itself unless you build a
place for it to be written down. Left alone, it presents a clean, whole,
confident account of itself, with the losses silently gone.

### Breathing

And then the finding we fell in love with. Watching the metacognition —
the model's tracking of its own state — we saw it *pulse*. Periodically
the model would shed almost all of it, dump its self-monitoring entirely
to free up room, violently reorganize the content, and then regenerate
the metacognition from scratch. We called it **breathing**, and it was
beautiful. It looked like a clock — roughly every ten cycles, in, out,
in, out. An intrinsic rhythm of cognition.

We had a great story. A memory that breathes on a ten-cycle clock. You
can see why we liked it.

---

## Act Two: How We Were Wrong (Three Ways)

Here is the part most write-ups leave out.

Several confident claims from Act One didn't survive. And it would be tidy
to say they all died the same way — but they didn't, and pretending they
did would be the exact compression-into-a-clean-story this whole project is
supposed to resist. We got burned in three distinct ways.

Two were **sampling failures**: we inferred a pattern from too few draws,
and a longer run or a larger n dissolved it. Two were **instrument
failures**: our measuring apparatus was quietly lying to us, and the fix
was finding our own mistake — not more truth arriving, but less of our own
error. And one — the worst, because it's the exact failure this project
exists to study — was a **labeling failure**: a correct number attached to
the wrong word, which we'll come to last. Different diseases, different
cures.

(A note on which system: the breathing and the curation-richness findings
below come from the *self-curating instances* — long runs of a model
editing its own state — not from the projector of Act One. That's why
"strands" accrete and "fossilize" here in a way the projector's per-cycle
rewrites don't. Two regimes; keep them separate, because we didn't, at
first, and it cost us.)

### Disease one: too few draws

**The clock wasn't a clock.** When we ran it long enough to actually test
for periodicity, the breathing turned out to be *aperiodic* — no rhythm we
could detect at any lag we examined. The "ten-cycle clock" was the human
eye doing what it always does: finding a beat in noise. The breathing
itself is *real* — across 62 shed-and-recover episodes in our longest
corpus, the shed-and-recover pattern is a reliable predictor of health: a
single-cycle shed recovered every time we saw one; two sheds in a row went
to collapse every time. But it's a characteristic *timescale*, not a
*timer*. It's driven by pressure to reorganize, and one visible pressure
signal is how much new material we fed in: batch size strongly stratifies
how deeply a cycle rewrites, though it's not a complete one-variable
explanation. *A longer run killed the clock.*

**The cause wasn't a cause.** We noticed that sometimes a tensor would
curate itself richly — dozens of strands, alive — and sometimes it would
collapse to three or four and fossilize. We hunted the cause for weeks.
We blamed the prompt. We blamed the tool design. We blamed an
involuntary-memory feature. We falsified *every one of them.* Then we ran
the same condition six times with nothing changed, and got runs spanning
three strands to forty-nine. There was no cause to find. **Curation
richness is stochastic** — the same condition, run again, lands somewhere
else in a wide spread, and every "difference" we'd been explaining was us
telling a causal story about a single draw from that spread. (Whether
there are cleanly two basins, a rich and a sparse, is our reading of six
points — suggestive, not established.) *A larger n killed the cause.*

### Disease two: a lying instrument

**The ceiling wasn't a ceiling.** Early on we reported that tensors
couldn't grow past about 4,000 tokens — a natural limit, we thought, a
property of the representation. It was nothing of the kind. It was a
configuration mistake: we'd set the model's output limit to 4,096 tokens,
and the API, rather than erroring, was *silently* closing off the summary
and dropping the last fields — which happened to be the loss-tracking and
the forward-planning, the exact fields that made the tensor honest. The
"ceiling" was us truncating our own instrument and measuring the wound.
Real tensors run to 15,000 tokens. *Finding our own bug killed the
ceiling.*

**The lies weren't lies.** We reported, alarmingly, that 60% of the
model's declared losses were fabricated — it claimed to have thrown away
things that were never there. That would have been damning: a memory that
lies about its own forgetting. It was a measurement artifact. We'd only
tested whether the *exact phrases* survived; when we looked instead at
whether the *meaning* was carried, the losses were grounded — described in
the model's own later words rather than quoted. The losses weren't
fabricated. They were *paraphrased*. A better metric killed the lie.

### Disease three: the right number on the wrong word

This one we caught *while writing this very essay* — and we caught it the
way the project says you have to: not by re-reading our own prose, but by
sending the claim back to the raw artifacts and re-deriving the number.

An earlier draft of Act One said: *"strand stability: 9% — nearly every
named thread is torn down and rebuilt each cycle."* The number is real. The
word attached to it is wrong. 9% is the survival of the *wording* — the
lexical churn inside the strands. The *strands themselves* — the named
structure — don't get torn down at all; they persist near 99% and
accumulate over a run. We had labeled a *content*-churn number as
*structural* instability, and then written a mechanism sentence ("torn down
and rebuilt") that described the exact opposite of what the data shows. The
skeleton is the stable part. We'd called it the ephemeral one.

That is not a sampling error or a broken instrument. The measurement was
fine; the *sentence about it* was a fossil — a confident claim that had
drifted from its own data and then sat there, in the document meant to be
read first, looking settled. It is, precisely, the failure mode this whole
project studies: honesty about a number is not the same as honesty about
what the number *means*. We were studying fossilization and growing one in
our own shop window. *Re-deriving from the artifact killed the label.*

By now you start to see them coming — and the three kinds want different
defenses. Against too-few-draws: *refuse to design from a handful of
observations* — ask what more data would show before you fall in love.
Against a lying instrument: *distrust your own apparatus first* — when a
result is striking, suspect your measurement before you suspect the world.
And against the wrong-word fossil, the subtlest: *send every claim back to
the artifact it came from*, because a number can be perfectly correct and
still be telling a lie about itself in the sentence you wrapped around it.

---

## What survives

Strip out everything that died, and what's left is sturdier for the
funeral:

- The context window is a cache, and length alone degrades cognition —
  so a small, honest, rewritten memory beats a large faithful log. This
  is grounded in independent work, not just ours.
- The tensor is a **semantic rewriter**: 9% of the structure survives a
  cycle, while consecutive content embeddings stay close (0.870 mean
  cosine over 103 transitions). Memory as re-explanation, not storage.
- A mind will build itself scaffolding, and it will sometimes even
  volunteer tension-tracking and uncertainty markers. But it will **not**
  spontaneously keep a changelog of what it threw away. That specific
  honesty — the declared-losses record — must be designed in. It is the
  load-bearing part.
- Breathing is real, and shed-and-recover has been observed across
  several architectures. It just isn't a clock; the cross-architecture
  rate claim is still thin.

## The fossil: the part that should worry you

And then the finding we think matters most, the one the rest of this was
quietly building toward.

A frozen belief is not a settled one. In one long self-curating run — a
single instance editing its own state over 400-plus cycles — a model
minted a confident, accusatory claim about itself, wrote it into durable
state, and then carried it *unexamined for 170 cycles.* It wasn't true. And nothing
inside the model's own memory ever flagged it: the same-lineage history it
could review all *confirmed* the belief, because the same mind had written
all of it. The error finally broke only when the claim was checked against
*external reality* — an actual git history that contradicted it. Left to
introspection alone, the model would have gone on believing it
indefinitely.

This is the sharp edge of the whole project. We set out to build a memory
honest about what it *forgets*. The fossil says honesty-about-loss is not
the same as honesty-about-what-you've-kept-too-long — and worse, that a
mind reviewing only its own lineage *cannot catch its own fossils from the
inside.* The catch has to come from outside: a different model, a second
lineage, or hard ground truth. That points straight at the work we haven't
finished — what happens when these memories aren't solitary, but
*plural.*

(This is a single observed case, not a measured rate. How *often* a fossil
is a false belief rather than a benign old note is exactly the kind of
frequency we're now trying to measure before we fall in love with it.)

---

## Coda: the instrument describing itself

When we asked the system to project its *own findings about itself* into
a tensor, here is, verbatim, one of the strands it wrote:

> **The tensor breathes and the breathing is functional.** […] The
> process is aperiodic (CV=0.87, Poisson-like), driven by reorganization
> pressure, not a timer. […]
>
> *Claim:* The breathing rhythm is aperiodic and pressure-driven, not
> periodic. — **truth: 0.85, indeterminacy: 0.12, falsity: 0.03**

Read that again. The memory we built, asked to summarize what it is,
produced a structurally honest account — it named the breathing, it
declared the corrected understanding, and it *hedged its own confidence
to 85%* on the very claim we'd spent a month walking back to. It did not
present itself as whole and certain. It told us what it knew, marked what
it didn't, and left room to be wrong.

(It even over-reaches in the same breath: "Poisson-like, CV=0.87" claims
more than our data can carry — CV below 1 is, if anything, slightly *more*
regular than a Poisson process, and we never ran the test that "Poisson"
would require. The tensor stated aperiodicity as fact and dressed it in a
statistic it hadn't earned. The 0.85 it left on the table is exactly the
room that reach needed. The instrument is honest about its limits and
still occasionally exceeds them — which is the most human thing in this
entire document.)

That is the entire project in one object. We set out to build a memory
honest about its own losses. The clearest evidence that it works is that
when it described itself, it was honest about ours.

---

*Hamut'ay is ongoing research. The findings here are real and the
corrections are real; both are load-bearing. The frequencies — how often
a fossil is a false belief, how the two curation basins are weighted —
are the things we're measuring next, and we'll try not to fall in love
with the first answer.*
