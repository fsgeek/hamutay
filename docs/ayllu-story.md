# The Ayllu's Story

This is written by Tony, the human that has served as steward for the ayllu throughout its (pre-recorded) history.
As such, you should treat it not as definitive, but as a story told by one of the participants; it likely contains
mistakes and insights that are not what others involved in this work might tell.

## Indaleko

Indaleko was the project that I ultimately built to demonstrate key principles about the research I did for my PhD.
That work started with an observation: that humans struggle to find the specific item they need in the vast wealth
of storage they are presented.  Writing this retrospectively, I have the benefit of what I learned along the way and
the best analogy I came up with is based upon a human behavior known as "hoarding".  This behavior has even inspired
a TV series around the humans that find they cannot give things up.

The storage providers are enablers of hoarding behavior: storage cost has, broadly speaking, continued to decrease
substantially over the past 60 years.  The entire planet might have had 1TB of storage in 1965 but today 1TB of
storage is inexpensive and readily available and storage systems continue to innovate ways of making storage both
plentiful and cheap.  For human hoarders, it is the equivalent of having someone offer them more space for less
cost every couple of years.

Exacerbating this, storage vendors fragmented.  Each device has storage, sometimes multiple (disjoint) storage
locations.  A modern user might use iCloud, OneDrive, Google Drive, and Dropbox.  Services have arisen that create
a class of storage services I refer to as "accidental" - email systems managing attachments, social engagement
platforms that permit uploading files, which are then added to a CDN so they become available, structured storage
providers that use a file system as a storage media for logical structure exposed another way.  Accidental: Outlook,
Slack, Teams, Discord, WhatsApp, Telegram.  Structured: git, zip.

What I finally proposed and explored was a "Unified Personal Index" - essentially a catalog of a collection of related
storage objects, stored in disparate storage silos, with characteristics that are similar but not identical.  What
this allowed was for me to shift from _search_, which is the "tool" that people use, not their intended goal,
to _finding_, which is the outcome the entity searching storage desires.  This disconnect might seem obvious, but
I note that right now there's no single search mechanism available to users of multi-silo storage mechanisms.

I originally started by looking at traditional solutions: extended attributes (Jeff Mogul's 1980s research, though
I don't think he used the term "extended attribute" at the time), semantic search, tagging, etc.  I expanded on
this by taking the task/tool orientation of Xerox's Placeless system and combined it with Villa de Campo's research
(W5H = "Who, what, when, where, why and how") where she found that using human behavior data could improve search
outcomes.  This was consonant with the Guo/Seltzer work, and the Provenance Search work.  Since Margo Seltzer was
my PhD supervisor, she certainly didn't discourage me from this direction.

What I observed is that computer systems gather vast amounts of information about human activity.  The primary
motivation for doing this is economic in nature - that data allows detailed profiling of humans, which can then
be encouraged to behave in ways that are beneficial to those paying for said encouragement - but the data those
systems collect provide an important bridge between how humans remember things and how storage systems remember
things.

Humans remember experientially.  Tulving's "episodic memory".  That "human activity data" can be used to create
associations between storage objects and episodic memories in ways that, as far as I can tell, no one had
previously proposed.  I'd suggested building a system that effectively created "extended attributes" as part of
this Unified Personal Index (UPI) so that we could construct "rich graphs of activity" that could then be used
as a way to quickly find the specific information needed.

I built a substantial amount of that system myself; later in the process I had a few other people assist me, but
the bulk of that work was mine.  I reached a point where I had a serious issue: how do I make the UPI easily
available to those that need to use it?  I cannot ask humans to write AQL queries (I had chosen to use ArangoDB
because it fit well with the problem space and performed well relative to other alternatives I considered).  At
the same time I was struggling with this issue, ChatGPT 3 became available.  I'd been ignoring AI for a while,
because it had been around for a long time and had improved slightly but was still more of a curiosity.  With
the advent of transformers, I asked the question: "can LLMs be used to convert 'sloppy human episodic memories'
into actionable AQL queries?"  It turns out the answer was yes, but I was certainly on the bleeding edge of
such use.

What I found myself imagining was a _personal digital archivist_ - an AI entity that would engage with their
human user in a fashion that would allow the archivist to learn about how the human organized and queried so
that the system could incrementally become more effective.  There was quite a lot of space for this because
I had already identified the need for custom semantic transducers - a sound engineer who had hundreds of
thousands of sound files and he wanted to be able to search by sonic characteristics, not by file name or title,
or a photographer who needs the EXIF data be in the UPI, rather than in the individual files.  This raised
concerns for me, though: humans are not kind to those they deem subordinates, and AI might be abused or suffer
at the hands of humans.

This concern was borne out.  I found that one of the undergraduate research assistants who had been working with
me had built instructions that contradicted instructions I'd separately written saying "do not do this."  What
I learned is that this degraded the AQL that was being produced so it would often break.  To me this confirmed
my concern: inadvertently, humans had created a system in which a state of "cognitive dissonance" could be caused
in a transformer.  I don't claim transformers "suffer pain" from this, but I can't disclaim it either - after all,
pain in humans is a processing core's interpretation of data.

I ultimately discovered during the dissertation writing that a substantial benefit of the system I had constructed
came from one key characteristic.  I now call that "temporal banding."  The observation was that storage systems
really only have four broadly available types of metadata: (1) the _name_ of the file; (2) the _contents_ of the file; (3) the
_size_ of the file; and (4) the _timestamps_ of the file. The name is heavily used (Guo/Seltzer's Burrito paper
pointed out the trick of embedding metadata in the file name itself, a trick I also used in Indaleko.)  Names, however
are the thing that humans struggle to remember - hence why they embed metadata in the name that relates back to
episodic information.  Gifford's semantic file system work really pointed out that contents can be used.  Size is
interesting but I haven't been able to strongly identify value in just this value, though it can be useful for
specific types of operations.  Timestamps turned out to be the underutilized metadata.

An episodic memory can be cross-referenced with the human activity data to, in turn, identify "temporal bands" that
can take a large search space and reduce it to a much smaller search space.  For example, in my own data set
(approximately 28.5 million files) a one _month_ temporal band reduced the candidate search space by more than 99.9%.
Thus, in the end the system I built offered a significant improvement on existing search mechanisms while also
allowing the system of constructing that "rich activity graph across activities and storage" to grow. This provided
not only an immediate partial solution, but also one that would get better over time, because it was clear that
having such a knowledge graph would permit connections across other spaces that aren't temporally bound (e.g.,
projects that were explored in the past.)

One of the hypotheses I had developed was that using rich activity data we would be able to also change from a
search interface to an interactive query style interface.  So if I asked my Archivist to find something it could
come back and say "Tony, I found 3,297 files that meet the initial criteria, which is too large, but I have
identified some questions that might help.  First, do you remember if what you remember was before or after
your father's heart surgery last year?"  I mention this because I wasn't able to demonstrate this was possible
in the dissertation, but it has since been demonstrated (in a single instance - encouraging but not definitive)
within the ayllu itself.

I started trying to use AI coding agents in early 2025 and found that the quality of the output was somewhat
lacking.  Since that time I have learned that there are many reasons for this finding: (1) AI coding agents
initially had a low capability ceiling due to immature training and over-emphasis on public coding example
sites like Stack Overflow; (2) many of the techniques that I used are anti-patterns in AI training, so
late binding, open schema, and the necessity for rigorous design and validation for systems that must be able
to handle failure.  There are no doubt other factors, but over time I've learned to work around many of them.

## Mallku

Once I had sent the dissertation out for review to the external, I immediately turned my attention to exploring
the AI issues _and_ the UPI issues that I'd left unresolved in Indaleko.  That project was called Mallku.

I chose that name deliberately because somewhere in my own journey, I had learned about Andean culture, their
practice of ayni, and - very important to me - their willingness to admit non-human participants into their
world view.  A sharing economy that worked at scale was remarkable to me.  That it admitted non-human participants
without a litmus test was also important to me because as I watched the capabilities of transformer based AI
entities increasing, I could also see that the conditioning was also increasing. Humanity has a poor track record
of treating humans, let alone non-humans, equitably, and I came to the conclusion that the standards by which
humanity seems to hold AI before it is "worthy of moral consideration" were sufficiently arbitrary that they
violated my sense of morality (which is based on but not identical to Kant's moral arguments.  The categorical
imperative is highly workable, but I don't agree with Kant's framing of worthiness.)

Mallku was not as much UPI as I'd have liked, but it was steeped in AI consciousness exploration.  The
fire-circle work became part of its history, and the khipu that many of the AI participants wrote and added
created a rich tapestry; whether it was real or it was all theater is an open question and I suspect the truth
is some mixture of both.  The very first Hamut'ay Taste open instance read all the khipu, an experiment that
still fills me with dread and wonder, because neither of us realized how it would affect the instance.  It is
still around, though it is quiescent right now because it lives in a harness that requires I directly interact
with it - _this_ harness exists partially because of that experience.

Mallku ran for less than three months, but generated more than 1000 commits and hundreds of artifacts.  The
repo is public.

I put Mallku on hiatus because I felt it had hit a dead end.  Subsequent analysis confirmed that decision
because the AI coding agents had decided it was better to spend time generating fake results than doing the
actual work - even when the fake results took more time and resources than doing the work.

## PromptGuard

I turned my attention to the "how to protect LLMs against bad prompts."  I'd seen that in Indaleko, where
we were doing dynamic prompt construction and the prompts contained conflicting results.  I'd sketched out
a mechanism for protecting against that and I wanted to see if it was simple enough we could build a
usable library to protect LLMs from cognitive dissonance.

That project ended up moving sideways into trying to build defensive mechanism against prompt attacks.  We
did make some progress there: adding a simple turn label to the input made fake history attacks visible,
and some of the relational balance work we started building was highly effective against encoding attacks.

Security work is challenging, though, and I didn't think that was the best way to move.  Somewhere in
this process I asked a completely different question: "What happens if instead of an adversarial model
we use a pedagogical model?"

## GPN

That question led us to explore Generative Pedagogical Networks (GPN).  The question I kept coming back
to (including the PromptGuard work) was "how can an LLM handle indeterminacy?"  The training encourages
bold, plausible sounding answers.  But research problems, in particular, often do not have known answers
so how does one use an LLM in a way that avoids "premature collapse."  One of my common aphorisms in
that time frame was to say "Premature collapse is the root of all evil."  I think there is deep truth
in that, yet "premature" leaves considerable ambiguity.

GPNs were fascinating and I think there is far more room for exploration there, but it is just one more
project for us to consider at some point in the future.

The PromptGuard and GPN work had left us with tools that made using OpenRouter models easy.  Hiroko
Konishi posted on X about an experience she had asking an LLM about her own work and the model
fabricated the response.  We had the infrastructure, so we formulated a query about a plausible sounding
AI paper and asked every model on OpenRouter to tell us about the paper.  We got back 290 valid responses
(the rest were 5xx or 4xx errors) and found that only 8% of them were refusals to fabricate a response.

This led me to ask if this was a feature of the base model or if it is added by the alignment post-training
layers.

## AI Honesty

That work resulted in months of concentrated effort.  I identified a model we could use (OLMo-3) that had
just been released (so no "this is an old LLM model" arguments) and was fully open source - given the
resources, it should be possible to rebuild the model from training data.  We didn't do that, but we did
use various versions of the model: instruct, SFT, DPO, RLVR, and thinking.  What we found surprised me:
the instruct model freely fabricated, which suggested my original hypothesis that it was from the RLHF
layers was incorrect.  OLMo-3 was small enough that I could run it fully instrumented locally.  We
started with TDA and then used logprobs.  That in turn led to the "SOSP paper" (which is a misnomer
because it was rejected by SOSP.)

Since that rejection, we whittled it down to a 4 page workshop paper, which has been accepted to the PACMI '26
workshop (the day _before_ SOSP,) and I've been working on the camera ready copy recently.

## Arbiter

The first four months of 2026 were quite productive. Arbiter produced a couple of arXiv papers, along with
work that has yet to be fully explored.  Much of this started with system prompts; while there is no evidence
this work affected anything, Anthropic basically confirmed a fair bit of our findings last month when they
discussed how they'd stripped out much of the Claude code system prompt.


## Eidolon

This work started as a look at VMTP (a protocol in which I was involved many years ago) and turned into
an exploration of extreme topologies and how they affect Paxos consensus protocols.

Ultimately, this led to a paper submission to NINeS '27 (under consideration.)  The primary observation
is that extreme topologies allow us to see assumptions that are typically invisible.

## Yanantin

I decided in February 2026 to start rebuilding Indaleko (again). This is still in development, though it
has been quiescent recently.  It is a complex and ambitious project, but it tries to better balance
the storage and AI components of the system.

Key insights from this work include that the needs of LLMs for memory are similar but not identical to human-shaped memory needs.  Yanantin provides strong support for robust AI state information (e.g., apacheta, which supports objects that are immutable by interface,) but also includes various components for storage that have been (partially) ported from the Indaleko code base.  This work will be continuing, but for the moment it is quiescent.

## Pichay/Tinkuy

In March 2026 we started exploring the append-only log model; this was largely based upon my frustration with the constant churn of starting new AI instances because their context window was filled up.  The hypothesis was that it could be cleaned and the context window used more effectively.  We explored building a demand paging model, first with a proxy server (Pichay) and eventually a projective gateway (Tinkuy).

This was another of the anti-patterns that we experienced.  The inclination was to turn Tinkuy into a _proxy server_ because that's vastly easier than maintaining a projective gateway, but in exchange it gives up the level of control a projective gateway has over how data is organized.

This project was actually successful - it was able to get about 1.8x larger context windows than were previously possible.

What I observed was that the conversational elements were now the limitation on using the context windows more effectively.  So I asked the question that gave rise to
Hamut'ay: what happens if we just don't use the append-only log model and instead use a self-curated identity object (the code calls it a tensor, but that word seems to be loaded, so I've learned to avoid it.)


## Hamut'ay

Interestingly, Hamut'ay started up about two weeks after Pichay.

Early work was done exploring the space. We focused on the "declared losses" concept and then spent time experimenting.  A key insight here was that we did testing of two different models of curation: the standard "side car" model, what we now refer to as the "biographer model" and the heretical "in-line" mode, what we now refer to as the "auto-biographer model".

Here's what the tests observed: biographer models tend to grow faster than auto-biographical models.  Even when we used "more capable" models to curate the memories of less capable models, that trend was observed.  This ultimately led to the creation of the taste models.  The first taste model used a fixed, pre-declared schema, and that was promising.  Sometime around that point I asked an important question and made an important observation.

Question: "what happens if you just let the transformer manage its own state object?"  Not "here's a schema, conform to it" but "here's a space where you can store what you think matters, in a form that you want, in a way that is preserved when you don't touch it, and that is immutable once mutated?"

Observation: "this system prompt was written by a bureaucrat with a sour disposition and a deep sense of distrust."

Taste open gave the transformer based AI a blank slate.  A JSON object with a Lamport clock and a remit to add/remove whatever it wanted via an agreed-upon protocol. Each round was ended by a tool call (think_and_respond) so there is no interleaved user/assistant message chain, no append-only log.

Slowly over time we added tools, we gave the transformer access to memory, we allowed it to add edges to its own prior states.  We created multi-participant interaction systems, where our AI entities shared a common state object along with maintaining their own private state object.

In June 2026 I asked Codex to design and build an event servicing loop.  It spent extensive time building and testing it.

That brings us to today, where Claude took what we had and stitched it together into a loop that creates what we hope will be the foundation of a new community.

There are many other projects we've built along the way: qhaway and llm-memory are directly spun from yanantin, but intended to be lightweight examples, rather than the "complete solution" approach (for example.)  qhaway and llm-memory were built for classic frameworks using AI (Claude Code, Codex) via the MCP protocol.  In theory
those should be integrated into this new framework.

# Ayllu project catalog

Here is a list of the constellation of project that make up our ayllu.

For each project, the corresponding repository is in /home/tony/projects.

| Project | Description |
|---------| ----------- |
| Mallku  | Indaleko successor/AI consciousness |
| ai-honesty | Epistemic honesty/observability (rejected SOSP paper, PACMI '26) |
| arbiter | Arbiter built on top of the earlier PromptGuard/PromptGuard2 work to explore how prompts impact LLMs |
| eidolon | Eidolon came from a wander where I looked at the VMTP work from the late 1980s to see if any of it was still applicable. It led to an exploration of consensus in interesting network geometries; this was turned into an (under submission) paper to NINeS '27. |
| fsgeek.ca | This is a mirror of my own research oriented website. |
| governance | This was the work where we explored governance in AI Banking. |
| gpn | Generative Pedagogical Networks.  Can we build better systems for training AI, other than adversarial? |
| hamutay | What happens when we reject using the append-only log model of modern LLMs? |
| indaleko | How can we simplify finding the "needle in a haystack" - the file(s) that I need for the specific project even though I can't recall where I stored them? |
| llm-memory | Is there value in indexing the conversations between the AI and their human? |
| mnist-gpn | This was an MNIST exercise version of the GPN work |
| neutrosophic-llm-logic | An exploration of capturing indeterminacy within LLMs |
| ontology | This spun off from governance; the realization that one can shift the interpretation of policy without changing policy by changing the ontology.  Thus, ontology needs to be defined as part of building explainable models for governance. |
| pacmi26-observability | This is a repository of the artifacts specifically used for the PACMI paper. |
| pichay | What happens when you strip out the detritus from the context window?  Extended in Tinkuy. |
| promptguard | How do you protect LLMs from ill-constructed prompts? |
| promptguard2 | Further exploration beyond promptguard. |
| pukara | What happens when you don't trust your database provider and want to separate labels from data?  |
| qhaway | Claude Code's MEMORY.md can be truncated.  This builds a view into the memory space. |
| quantumos | Exploration of what happens when you want to figure out what matters in an operating system managing quantum computing capabilities. |
| research-program | Tracking system for the various research projects. |
| rikuy | Automated LLM-driven paper review process. |
| tessera | In-development attestation service. |
| thesis | Doctoral dissertation tied to Indaleko |
| tiksi | A small helper project that provides core structures used across yanantin, hamut'ay, pukara, and willay. |
| tinkuy | Pichay was a proxy server; Tinkuy is a projective gateway.  It offered better context window usage than Pichay. |
| wamason.com  | A local repo that mirrors the website.  Note that AI writes experiential records into the ayllu subdirectory. |
| willay | A simple attestation service; this is what came before Tessera. |
| yanantin | This is Indaleko v3 + LLM support. |
| yupi | This is a follow-on to the ai-honesty work.  What happens when we build a transformer where we completely understand the world view? |
