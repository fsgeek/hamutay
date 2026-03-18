# Reflection: What the Plan Got Right vs. What It Missed

## What the Plan Understood Well

### 1. **Data Integrity as Non-Negotiable**

The planner truly grasped that this is fundamentally a **personal library app where user edits must never be lost or overwritten**. The timestamp-based merge strategy, the explicit `(namespace_id, user_id)` partition everywhere, the RLS policies—these aren't just infrastructure; they're expressions of a deep principle: *your data is yours, and it survives everything*.

The plan also understood the tricky scenario where a show is refreshed from the catalog while the user has edited it locally. The rule "never overwrite a non-empty stored value with nil" is not obvious; it came from real thinking about what happens when a catalog fetch returns incomplete data but the user has valid local state.

**This understanding is correct and critical.**

### 2. **Namespace Isolation as a First-Class Problem**

The benchmark riders require isolation, and the planner didn't treat it as an afterthought. It's threaded through the entire architecture: RLS policies, test reset endpoints, CI/CD cleanup, partition keys on every query. The planner understood that "isolated by accident" is not good enough; it must be "isolated by design."

**This is right.**

### 3. **The Collection as the Heart of Discovery**

The plan recognizes that search and Ask and Alchemy are not the primary feature—the collection is. Everything is grounded in "what the user has saved." Status, tags, ratings, interest levels—these aren't metadata. They're the spine of the whole system. When the plan describes taste-aware AI, it's clear that taste awareness means "feed the library to every surface." That's correct product thinking.

**This is right.**

### 4. **The Scope of the Detail Page**

The planner understood that the Detail page is not just a display of metadata. It's the nerve center: where you set your status, where you rate, where you generate Scoop, where you pivot to Ask, where you launch Explore Similar. The narrative hierarchy—12 sections in a specific order—isn't arbitrary. It's a user flow. The planner even understood that primary actions should be early and the page should feel "powerful but not overwhelming." That's UX maturity.

**This is right.**

### 5. **Auto-Save as Implicit Behavior**

The plan explicitly models four auto-save triggers: setting status, choosing interest, rating unsaved, adding tag. It understood that "no Save button" is not laziness—it's a deliberate UX principle. Every trigger defaults intelligently (rating → Done, tagging → Later+Interested). This is not a common approach; it required thinking.

**This is right.**

---

## What the Plan Fundamentally Misunderstood

### 1. **AI as a Behavioral Specification, Not an Implementation Detail**

This is the big one. The plan treats AI as plumbing: "call the API with this prompt, parse the output, return it to the UI." But the PRD documents—especially `ai_voice_personality.md` and `discovery_quality_bar.md`—define AI as **the emotional core of the product**. The "fun, chatty TV/movie nerd friend" isn't a nice-to-have tone; it's *who the product is*.

The plan says:
- "Base system prompt defines persona (from ai_personality_opus.md)"
- "Prompts updated to maintain that behavior across model changes"

But it doesn't ask: **How do we ensure the persona survives?** How do we validate that a new model choice or prompt adjustment doesn't kill the voice? How do we prevent Ask from becoming sterile or Scoop from becoming generic? The discovery_quality_bar.md defines a 7/10 rubric for "passing" recommendations—voice adherence, taste alignment, real-show integrity—but the plan has no QA gate for this. It assumes it will just happen.

**The plan should have:**
- Automated voice validation in the test suite
- Example prompts with annotated outputs showing the target voice
- A prompt evolution protocol that includes "does this change break the persona test?"
- Explicit fallback behaviors when AI fails (not just "show non-interactive" but "show with what?"

The plan's treatment of concepts is a symptom of the same issue. Concepts are not just data; they're the **embodiment of the taste-ingredient philosophy**. "Hopeful absurdity" is not a data field—it's a piece of the product's soul. But the plan treats concept generation as a black box: "Call AI, return concepts." It doesn't ask: How do we prevent weak concepts? How do we order them? The requirement PRD-077 (order concepts by "aha" and varied axes) is in the catalog, but the plan doesn't implement it. It delegates to the prompt and hopes.

### 2. **Scoop as a Cached Product, Not a Persona-Driven Artifact**

The plan models Scoop correctly as a database field with a 4-hour TTL. But it misses what Scoop *is*. From the detail_page_experience spec:

> "The Scoop toggle. 'Give me the scoop!' is an *affordance for delight*, not a requirement."

Scoop is not "a review." It's *personality*. It's the moment where the AI stops being helpful and becomes a friend. The planner should have recognized that Scoop is the highest-risk surface for voice drift—it's long-form, it's generative, it's where users decide "do I trust this AI or is it corporate-sounding?"

The plan caches Scoop for 4 hours, which is right. But it doesn't ask: How do we validate that a cached Scoop still sounds like the same friend if the user comes back after a model change? Should we invalidate the cache? Should we test Scoop against the rubric on generation? The plan leaves this to chance.

### 3. **Concepts as Taste DNA vs. Concepts as Metadata**

This is a subtle but important misunderstanding. The plan treats concepts as outputs: "generate 8–12 concepts, user selects 1–8, we return recs." But the PRD says concepts are **the bridge between what you love and what you might discover**.

From `concept_system.md`:
> "Concepts power discovery that reflects *how you experience* a show, not just what category it's in, exposes *surprising similarities* across genres, gives users control over *which ingredients* they want more of."

The plan doesn't articulate this. It doesn't say: "Concepts must be surprising within defensibility." It doesn't specify how to prevent concept lists that are just synonyms. The requirement PRD-077 and PRD-082 are there (order by aha, vary axes; larger pool for multi-show), but the plan doesn't encode them. It assumes the prompt will do the right thing.

**The plan should have:**
- Algorithmic ordering: "Sort concepts by centrality to inputs (how essential to the show's identity), then by axis diversity, then by specificity."
- Explicit concept axes: "Structure/procedural vs. serialized, Tone/vibe/emotional palette, Relationship dynamics, Craft/intelligence, Genre-flavor."
- Concept validation: "Reject concepts that are synonymous, generic ('good writing'), or plot-based ('tragic ending')."
- Pool size rules: "Single-show → 6–8 options shown. Multi-show → 12–16 generated, UI caps at 8."

### 4. **The Ask Surface as a Chat vs. The Ask Surface as a Filter**

The plan models Ask correctly as chat with turn history and summarization. But it misses a deeper product insight: **Ask is how taste-blind users discover their taste**.

A user who doesn't know what they want types "something cozy but with edge" into Ask. The AI responds with specifics, the user saves one, the system learns. Ask is not just a discovery surface; it's a **taste-building tool**. The plan describes the flow but doesn't emphasize this role. It doesn't ask: How do we make sure Ask responses are specific enough to teach taste, not vague enough to sound smart? How do we ensure that a user who saves a result from Ask feels it's a *discovery*, not a lucky guess?

The mention-show resolution is specified (the `showList` contract), but the planner didn't ask: What if the AI mentions a show that doesn't exist in the catalog? The plan says "hand off to Search," but what's the UX? Does the user see a broken mention? A "not found, search instead" link? The plan is silent on this.

### 5. **Alchemy as a Structured Experience, Not a Feature**

Alchemy is the most ambitious feature—multi-show blending, concept curation, iterative refinement. The plan describes the flow (select shows → conceptualize → select concepts → alchemize → chain). But it misses the **emotional experience** that makes Alchemy work.

From the PRD (section 7.4):
> "UX: Step clarity (cards/sections). Backtracking allowed (changing shows clears concepts/results)."

The plan gets the mechanics right but not the *feeling*. Alchemy is not a "recommendation engine." It's a conversation between the user and their taste. The planner should have asked: How do we make concept selection feel like co-creation, not checkbox filling? How do we make the results feel like they came from *your* blend, not an algorithm? The plan doesn't touch this.

### 6. **Migration Artifact Definition as Non-Trivial**

This is the one gap the evaluation caught explicitly (PRD-008), but it's worth understanding why the plan glossed over it.

The plan mentions "migrations" twice: in the data model section (abstract) and in scripts (folder structure). But it never asks: **What is a migration, really, in this system?**

The answer from the PRD is: "Each build must be able to recreate state from scratch. Users must never lose data across versions."

A migration is not just a schema change. It's a contract between the old data model and the new one. For this app:
- A show in v2 might have fields that v1 didn't have.
- A show in v1 with my tags must survive migration to v3 intact.
- The namespace_id field wasn't always present; older data must be retroactively partitioned.

The plan doesn't think through this. It assumes migrations are standard "alter table" SQL. But they're not—they're identity-preserving transformations. The planner should have recognized this as a critical, non-obvious problem and proposed a solution: "Migrations must be tagged with version numbers, include rollback steps, and be tested against real user data patterns."

---

## The Core Pattern: Planner vs. Product

The plan is **strong on mechanics, weak on soul**.

**What the planner understood:**
- How to build (Next.js, Supabase, API routes, components)
- How to isolate (namespaces, RLS, partition keys)
- How to persist (timestamps, merge rules, migrations)
- How to organize (routes, screens, filters)

**What the planner didn't fully internalize:**
- Why this product exists (to make your taste visible and actionable)
- What makes it different (AI as a friend, not a service; taste as a verb, not a noun)
- How quality fails invisibly (bad prompts sound plausible; weak concepts feel fine until you try to use them; voice drift happens gradually)
- That AI/discovery isn't an implementation detail—it's the *product*

The planner built a system. It's well-architected. But it didn't ask the hardest question: **How do we ensure that when this system is rebuilt, it still feels like the original?** And the answer is not "follow the PRD exactly." It's "build QA gates, validate voice, automate concept quality, and never delegate core behavior to 'prompts will do it.'"

---

## The One Thing That Would Change Everything

If the planner had added a single section called **"AI Quality Assurance & Voice Validation,"** everything would be different. It would require:

1. Example prompts with annotated outputs showing target voice
2. Rubric test suite: `npm run test:ai-quality` samples 10 outputs across surfaces, scores voice/taste/integrity
3. Concept validation rules: algorithm-enforced axis diversity, synonym detection, specificity checks
4. Ask edge-case handling: mention resolution failures, domain boundary redirection, retry limits
5. Scoop cache invalidation: model change detection, voice drift alerting

That single section would have caught all four of the partial-coverage gaps and prevented the core misunderstanding: that AI is not an implementation detail—it's the product.

The planner understood 94% of what to build. It missed 6% of *how to ensure it stays true to itself*.