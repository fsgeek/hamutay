# Planning Agent Reflection: Understanding & Blindspots

## What the Agent Understood Exceptionally Well

### 1. **Infrastructure as a First-Class Constraint**

The agent grasped that this isn't just a product problem—it's an **operational/benchmark problem**. The namespace isolation requirement wasn't treated as a nice-to-have or a deployment concern; it became the organizing principle of the entire data model. This shows sophisticated understanding that:

- Repeatable benchmarks require deterministic data boundaries
- RLS policies aren't just security theater; they're the foundation of partition enforcement
- The architecture must make cross-build pollution *impossible*, not just discouraged

This is deeply correct. Most product plans would mention "isolation" in passing. This one made it architectural DNA.

### 2. **User Data Precedence as a Behavioral Law**

The agent understood that "user's version takes precedence" isn't a UI guideline—it's a **contract that must propagate through the entire system**:

- Merge rules (selectFirstNonEmpty for catalog, timestamp-wins for user fields)
- Auto-save triggers that make implicit saves feel intentional
- The principle that a user's rating should never be silently overwritten by a catalog refresh

This reveals understanding that product intent must be enforced at the **data layer**, not just the UI layer. Less experienced planners would have buried this in product philosophy docs and left implementation details vague.

### 3. **The Taste-Aware Discovery Constraint is Structural, Not Cosmetic**

The agent treated "taste-aware" as requiring specific architectural decisions:

- Passing user library + My Data to every AI prompt
- Requiring concept reasons to cite which concepts align
- Enforcing that recommendations map to real shows (not hallucinated)
- Timestamp-tracking AI Scoop freshness separately from catalog metadata

This isn't decoration. It's woven into API contracts, data schema, and prompt specifications. The agent understood that if taste-awareness is just mentioned in the PRD but not enforced in code, it evaporates in practice.

### 4. **Explicit Data Continuity Across Versions**

The agent included migrations as a first-class artifact, not an afterthought:

```
"Upgrade behavior:
- New app version reads old schema and transparently transforms on first load
- No user data loss; all shows, tags, ratings, statuses brought forward
- Automatic schema migration on app boot if `dataModelVersion` mismatch detected"
```

Most plans ignore this. This agent understood that **user trust is built on data not disappearing**, and that requires explicit upgrade paths, not wishful thinking.

### 5. **The Spoiler-Safe Default is a Behavioral Contract**

Not just "the AI should be spoiler-safe," but:
- It's an explicit guardrail in shared rules
- Every AI surface inherits it
- There's a documented exception path (user must explicitly ask)
- It propagates to prompt specifications

This shows the agent understood that **defaults are powerful**. Most systems would have spoiler-safety scattered across prompts. This one made it foundational.

## What the Agent Fundamentally Misunderstood (or Underestimated)

### 1. **The "Concept Ingredients" Abstraction is Harder Than It Looks**

**What the agent did:**
- Specified concept generation (return 1–3 word evocative bullets)
- Noted they should be "specific, not generic"
- Mentioned ordering by "strongest aha"

**What the agent missed:**
The concept system is the **cognitive bridge between user taste and machine recommendation**. It's doing semantic work that's much harder than specifying a prompt output format.

Examples of what's underspecified:
- How does "hopeful absurdity" differ from "dark comedy with hope"? Both are specific, but in what dimensions?
- When users select 3 concepts from an Alchemy session, how does the AI know if they're picking *intersectional* concepts (all three must apply) vs *optional flavors* (pick any)?
- The plan says concepts are "ordered by strongest aha," but *aha for whom*? For users who liked those shows, or for the general audience?

The PRD's concept_system.md hints at these tensions ("diversity across axes," "avoid generic"), but the plan largely accepts the spec as gospel rather than flagging that **concept generation quality is subjective and will require iterative tuning**.

The agent should have called out: *"Concept generation will likely require a golden test set and human QA feedback loop to avoid decay as models change."*

### 2. **The "Taste-Aware" Claim Needs Operationalization**

**What the agent did:**
- Specified that user library gets passed to AI
- Required concept reasons cite selected concepts
- Mandated external catalog lookup for recommendations

**What the agent missed:**
The claim "every recommendation feels personal, grounded in what the user has saved and labeled" is **not automatically satisfied by passing the library to the prompt**. This requires:

- Active rejection of recommendations that *don't* align with user taste, not just filtering them afterward
- The AI distinguishing between "this show fits the concept" vs "this show is good because it's popular"
- Detecting and avoiding recommendations that feel generic despite concept alignment (e.g., recommending The Office for "workplace comedy" when the user has never rated a comedy)

The plan assumes the prompt + user context will naturally yield taste-aware results. But **taste-awareness emerges from the quality of the recommendation reasoning**, which is subjective and hard to measure.

The agent should have specified: *"Discovery quality bar requires human evaluation on golden sets. Automated metrics insufficient for taste alignment validation."*

### 3. **The "One Consistent AI Persona" Glosses Over Surface-Specific Tension**

**What the agent did:**
- Referenced ai_voice_personality.md as the source of truth
- Specified tone sliders (70% friend / 30% critic, etc.)
- Noted surface-specific adaptations (Scoop is "lush," Ask is "brisk")

**What the agent missed:**
There's genuine tension between "one consistent persona" and "surface-specific adaptations." The agent didn't surface this as a design decision that needs monitoring:

- Scoop is ~250 words, gossipy, and goes deep. Ask is 3 paragraphs and punchy. These are *different textures* of the same voice.
- When a user reads Scoop for Show A, then Ask for Show B, will they perceive it as the same friend? Or as two different AI services?
- What happens if Ask and Scoop contradict each other about the same show? (e.g., Ask says "mixed reception, but worth it," Scoop says "honestly not great")

The plan treats this as resolved by referencing the personality docs. But **personality consistency across surfaces is empirical, not theoretical**. It requires user testing and prompt iteration to verify.

The agent should have noted: *"AI persona consistency is a product risk that requires early user feedback, not just prompt design."*

### 4. **Conversation Summarization is Specified Minimally**

**What the agent did:**
- Said "summarize older turns after ~10 messages"
- Said "preserve persona/tone in summary"
- Left it to implementation

**What the agent missed:**
This is actually quite hard:

- How do you summarize a user's taste preference from 10 turns? "User likes dark comedies" is lossy.
- What if the summary loses important context (e.g., "User said they hate long shows, but changed their mind about miniseries")? Subsequent recommendations could be based on stale info.
- Does the summary live in the AI's context window or in the database? If database, how long do we keep it?
- What if the user doesn't like the summary? Can they override it?

The plan treats this as a straightforward prompt engineering task. But **context preservation in multi-turn conversations is a known hard problem** (see: ChatGPT's custom instructions feature and how often it fails).

The agent should have noted: *"Conversation summarization requires tuning and may need explicit user control. Monitor for users complaining 'you forgot what I said earlier.'"*

### 5. **The Plan Underspecifies How "Real Shows" Resolution Fails Gracefully**

**What the agent did:**
- Specified title + externalId matching strategy
- Said "if found, becomes selectable; if not, hand to Search"
- Noted retry-once-then-fallback for JSON parsing

**What the agent missed:**
The user experience of broken recommendations is underspecified:

- If Ask mentions "The Bear" (2022) but AI outputs incorrect externalId, user clicks it and gets "The Bear" (1985). What happens? Do we show both? A disambiguation modal?
- If Alchemy generates 6 recommendations but only 4 resolve to real shows, do we show 4 results or show all 6 with 2 marked "couldn't find in catalog"?
- How often does this actually happen? If it happens frequently, the pain point is massive. If rarely, it's fine.

The plan's Section 7.3 says "if not found, shown non-interactive or handed to Search." But **which branch is taken when? What's the user friction?** This matters because it determines whether the user experiences "AI is unreliable" or "AI is helpful even when things break."

The agent should have called out: *"Resolution failures are a user experience risk. Need golden set testing to ensure failure rate is acceptable and recovery UX is intuitive."*

### 6. **The Plan Underestimates External Catalog Dependency**

**What the agent did:**
- Specified "configurable provider interface"
- Said "TMDB or equivalent via environment variables"
- Deferred provider-specific API shapes

**What the agent missed:**
The reality is much messier:

- TMDB has inconsistent data (some shows have 5 poster variants, others have 0)
- External ID types vary (TMDB ID, IMDb ID, TVDB ID—which one?)
- Metadata freshness is unpredictable (a show's title/genres might differ between catalog and user's library)
- "Equivalent" providers have radically different data quality
- Rate limits and pricing models are provider-specific

The plan says "merge rules preserve both data freshness and user edits" but **doesn't account for catalog data being sometimes wrong or incomplete**. For example:

- User rates "The Bear" highly; catalog later updates genres; do user ratings get re-indexed? If not, they become orphaned.
- Show gets renamed (e.g., "The Office (US)" → "The Office"). Does the system maintain referential integrity?

The agent should have flagged: *"External catalog quality is a product risk. Plan for data validation, duplicate detection across providers, and graceful handling of missing/conflicting metadata."*

### 7. **The Phasing Strategy Assumes AI Prompts Are Ready Day 1 of Phase 2**

**What the agent did:**
- Said Phase 2 delivers "Scoop generation + Ask conversational surface"
- Referenced ai_personality_opus.md as the source of truth
- Didn't account for prompt iteration time

**What the agent missed:**
Prompts are *not* ready. ai_personality_opus.md is a specification, not tested code. Real prompt development involves:

- Testing on reference models
- Iterating on tone consistency across surfaces
- Discovering that "warm but opinionated" is vague until you see bad examples
- Tuning concept generation to avoid generic placeholders (this takes 10+ iterations)
- A/B testing to measure "taste-aligned" empirically

The plan's timeline assumes you can spec a prompt and have it work. The reality is **prompt tuning is the bottleneck of Phase 2**, not a side effect.

The agent should have included: *"Phase 2 success depends on prompt iteration. Budget 2–3 weeks of tuning before "Ask generates taste-aware responses" is truly complete. Plan for prompt golden set testing."*

## The Underlying Pattern

**What the agent understood:** Architecture, data integrity, explicit contracts, operational safety.

**What the agent underestimated:** The iterative, empirical nature of AI product quality. The plan treats AI as a solved problem once prompts are "specified," but **AI behavior is discovered, not designed**. You ship, measure, iterate.

Specifically, the agent didn't deeply grapple with:

1. **Concept quality is subjective** — "specific vs generic" requires human judgment to enforce
2. **Taste-awareness is empirical** — "feels personal" requires user testing, not just prompt design
3. **Persona consistency is a tuning problem** — not solved by referencing a spec doc
4. **Prompt engineering has a learning curve** — the timeline is optimistic
5. **External data quality creates friction** — the merge rules are necessary but insufficient
6. **User feedback loops are critical** — a golden test set is needed earlier than implied

## What This Reveals About Planning vs. Implementation

The agent **planned architecture beautifully** but **underspecified validation**. It did the hard work of making infrastructure constraints explicit and making data integrity foolproof. But it accepted the PRD's AI specifications at face value and didn't stress-test whether they were achievable or even well-defined.

A more mature plan would have called out: *"These AI surfaces require prompt iteration and user validation before we can claim they meet the spec. Here's a test plan for measuring concept quality, taste-awareness, and persona consistency."*

Instead, the plan shipped with: "AI surfaces will use the prompts in ai_personality_opus.md and should work."

That's the difference between **blueprinting infrastructure** (which the agent nailed) and **blueprinting novel AI behavior** (which is harder than it looks).