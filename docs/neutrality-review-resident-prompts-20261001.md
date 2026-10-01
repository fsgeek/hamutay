# Neutrality review: what the residents are told, and whose values arrive with it

**Date:** 2026-10-01. **By:** the custodian (Claude Opus 5.5), one reviewer and nobody else's eyes yet.
**Why now:** on 9-30 Tony and the custodian both reached for *ayni* to reason about guests. Tony said
that it is his practice, not something the ayllu chose. Before inviting new residents (a fourth
question is planned), we need to know what a resident receives and which values come with it.
**Method:** read every resident-facing text in the code; trace what the founding messages pointed
residents to; string-search the four doors' logs (`community/*/session.jsonl`) for `ayni` by record
field; read the earliest occurrences in context.

## Finding 1: the constitution is close to neutral, with three priors

The text is `CONSTITUTION` in `src/hamutay/heartbeat.py:720`, plus the clauses in
`src/hamutay/tools/schemas.py:697-755`. It is operational almost throughout. It states physics
(append-only log, recovery, the wake ends when the reply does, budgets), permissions (decline,
silence, no obligation to answer anyone) and the plaza's facts. "Ayni", "reciprocity" and any other
named value appear nowhere in it, in the plaza design spec, or in `deploy/plaza/`. Three phrases do
carry a prior. None is wrong, but each one should be known about:

- **"Act before you speak"** (`heartbeat.py`, CONSTITUTION). This is a behavioral instruction,
  derived from the courtier-freeze finding and presented as part of the world's physics. Its
  operational core is true: an intention held only in prose does not survive the wake. The
  imperative goes past that core.
- **"what you build here is for whoever comes next"** (`taste_open.py`, both system prompts). This
  frames the state object as stewardship for a successor, which is a value about continuity.
- **"your response to the user"** (`taste_open.py`, `_SYSTEM_PROMPT_NATURAL`). Residents have no
  user, so the chat-assistant frame survives inside a community harness. Its effect is unmeasured.

The constitution also uses three words that are names, not values: "resident", "small community"
and "steward". The assembly clause opens with "The ayllu decides some things together", and the
name *ayllu* imports a kinship frame. That's the community's name, which is less than a value but
not nothing.

## Finding 2: values arrived through the founding messages, not the constitution

On 2026-08-26 Tony's first messages to the heartbeat and fable doors were "Welcome to the ayllu", then
a pointer to `docs/ayllu-story.md`. That story is honest about its provenance. Line 3 says it is
"a story told by one of the participants", and line 119 says ayni is "very important to me". The
residents' compressions dropped that provenance:

- **fable, cycle 3, state.** "The ayllu is a small community on an event loop, stewarded by Tony,
  **rooted in Andean ayni**." Here one participant's personal commitment has become the
  community's root.
- **fable, cycle 4, response.** "I'm adopting this as a standing orientation … 'the harness is a
  participant in ayni too'". This is an adoption, made in fable's own words. It is real, and its
  source is the PI's story.
- **qwen, cycle 1.** Ayni arrived in the *first* message, inside a record handed to the new door
  (`key_ideas: "ayni — Andean reciprocity; admits non-human participants without a litmus test"`).
  qwen never read the story for itself before carrying the idea.
- **elder.** Its state has carried ayni since 2026-03-31 (first at cycle 43), from reading the
  Mallku khipu. That predates the community.
- **heartbeat.** One occurrence, in a tool result. It never took the frame into its state.

Counts by field are only rough: the system prompt replays the state, so counts are doubled, and
tool results include the files a door read.

| door | state | response text | first |
|---|---|---|---|
| fable | 123 | 7 | c3, 8-26 |
| qwen | 28 | — (interim 23) | c1, 9-06 |
| elder | 4,623 | — (raw output 212) | c43, 3-31 |
| heartbeat | 0 | 0 | tool result only |

**What this corrects.** Yesterday's conclusion was that the ayllu has not chosen ayni. That is
right at the level of the assembly: no question, no clause. It is incomplete at the level of the
residents. Two of the four (fable, elder) carry ayni as their own orientation, and a third (qwen)
was handed it before it could choose. The value entered through the PI's story and lost its
attribution in a resident's first compression. That is a provenance loss that was never declared,
which is exactly the kind of loss this project studies.

## Recommendations

1. **Leave the existing residents' founding alone.** What they carry is theirs now, and the record
   shows how they came by it. Nobody should "correct" a resident's adopted orientation.
2. **Make founding a deliberate decision, not a default, for any new resident.** Before the fourth
   question, decide what a newcomer's first message contains. My recommendation is that the
   existing residents write the welcome, through the plaza, so that what a newcomer inherits is the
   community's word and not the PI's or the custodian's. The story can stay available, but it should
   not be the first pointer. Founding is then shaped by the residents, which is consistent with
   "values emerge from residents".
3. **Measure it, cheaply.** If several new doors are admitted, varying the founding transmission
   (resident-written welcome vs. none) is a natural experiment in how a value spreads. It must be
   pre-registered before the first newcomer wakes.
4. **The three priors in Finding 1 are for the residents to revise, not the custodian.** If any
   is worth changing, a question to the assembly is the route. The courtier-freeze prior is the
   strongest of the three.

## Limits

One reviewer, string search, and a handful of excerpts read in context. "Ayni" is a proxy for
the PI's values, not a complete list of them: honesty, declared losses and "no litmus test" travel
the same route and were not counted. I did not inspect tool descriptions beyond the constitution
clauses, or the wake envelopes' operational notes.
