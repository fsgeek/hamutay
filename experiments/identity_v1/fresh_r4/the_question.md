# Reflection on the Plan's Understanding

## What the Planning Agent Understood Well

### 1. **Data Integrity and Isolation as First-Class Concerns**

The agent grasped that this app is not just a CRUD system—it's a **multi-user, multi-build persistence problem**. The plan devotes serious architecture to:
- Namespace partitioning (`(namespace_id, user_id)` everywhere)
- Timestamp-based conflict resolution for cross-device sync
- Transparent migration across data model upgrades
- Explicit "backend is source of truth" principle

This is genuinely sophisticated. Most product plans gloss over data continuity. This agent understood that losing a user's library during an update is a cardinal sin, and built the architecture to prevent it. That's **correct and thorough**.

### 2. **The "Implicit Save" Pattern as Central to UX**

The agent recognized that the app's frictionless feel depends on **auto-save everywhere**:
- Rate a show → auto-saves as Done
- Add a tag → auto-saves as Later + Interested
- Set status → immediate persist

This isn't just a convenience feature—it's the **emotional core** of collection-building. The plan documents this clearly and repeats it across Detail page, Search, and filtering contexts. The agent understood this was *not* a button-click app.

### 3. **Namespace Isolation for Benchmarking**

The plan shows deep understanding of the **infra rider PRD's actual constraint**: builds must not collide, test data must be isolated, and resets must be scoped. The agent didn't over-engineer (no global teardown, no admin backdoors); it just made isolation a first-class partition key. This is pragmatic and correct.

### 4. **The Show as a Composite Entity (Catalog + User Overlay)**

The schema correctly models that a Show is **not** just catalog metadata—it's a **bundle of public facts + private user facts**. The merge rules (keep non-empty catalog fields, resolve user fields by timestamp) show the agent understood that:
- Catalog refreshes should never overwrite user edits
- Multiple saves of the same show should preserve user data
- The user's version "wins" everywhere

This is the right mental model and it's operationalized in the schema.

### 5. **Three-Phase Implementation as Realistic Roadmap**

Phase 1 (core collection), Phase 2 (AI features), Phase 3 (Alchemy + polish) is **sensible sequencing**. The agent understood that:
- You don't ship AI without the data model working
- Ask and Scoop are less risky than Alchemy (simpler UX, fewer moving parts)
- Polish and performance are final

This is mature project thinking.

---

## What the Planning Agent Fundamentally Misunderstood

### 1. **AI is Not an Implementation Detail—It's a Product Surface**

**The misunderstanding:**

The plan treats AI as **plumbing**: "call the prompt, get response, parse JSON, resolve shows." It has prompts referenced but not *specified*. It has guardrails mentioned but not *enforced*. It has a "shared persona" stated but not *operationalized*.

**What it missed:**

The PRD doesn't say "go write AI." It says "the AI must feel like one warm, opinionated friend across Scoop, Ask, Alchemy, and Explore Similar." That's not a prompt-tuning problem—it's a **product specification problem**.

A user can tell if:
- Scoop sounds like a different person than Ask (inconsistent voice)
- The AI praises a show they rated 2/10 (breaks honesty principle)
- Ask suggests "let me tell you about something outside TV/movies" (domain drift)
- Concepts include "good characters" and "great story" (generic, not specific)

The plan has **no mechanism to catch any of these**. It says "maintain persona" but doesn't define "what does drift look like?" or "how do we test for it?"

Compare to the PRD: `ai_voice_personality.md` section 2 lists "Non-Negotiable Voice Pillars." The plan never operationalizes these as:
- A shared system prompt template all surfaces inherit from
- A validator that rejects generic concepts
- A domain-check function in Ask
- A quality rubric with acceptance gates

**Why this matters:** An AI app with inconsistent voice feels broken. Users lose trust. The plan would ship something that *compiles* but *doesn't cohere*.

### 2. **"My Data Overlay on Every Show Appearance" Is Vague in the Plan**

**The misunderstanding:**

The plan states the rule once: "Whenever a show appears anywhere... display the user-overlaid version."

Then it never checks itself against that rule. The plan describes:
- Home tiles ✓
- Search results ✓
- Ask mentioned-shows strip (vague)
- Explore Similar recs (not mentioned)
- Alchemy recs (not mentioned)
- Traditional recommendations strand (not mentioned)
- Person credits (not mentioned)

**What it missed:**

There are at least 6–8 surfaces where shows appear. The plan specifies maybe 2 concretely. The rest are assumed to "just work."

A developer might build Search and forget that recommendation cards need to show rating badges. Or build Explore Similar and overlay status but not rating. Or build the traditional recs strand and not think "do users expect to see their saved status here?"

The plan needed a **per-surface checklist** (like a matrix: rows = surfaces, columns = My Data fields) to make clear what goes where.

**Why this matters:** Inconsistent data display breaks the core value proposition: "your taste made visible." If your saved status is visible in Home but invisible in recommendations, the model is broken.

### 3. **Taste Alignment Is Treated as Implementation, Not Specification**

**The misunderstanding:**

The plan says recommendations will be "taste-aware" and "grounded in library" and "surprising but defensible." These are correct goals.

But the plan never specifies *how*. It says:
- "Include user's library in context" ✓
- "Return reasons tied to concepts" ✓
- "Use external IDs to resolve shows" ✓

It does NOT say:
- What does a "taste-aware" recommendation actually look like? (Concrete example with library context)
- How do we prevent "surprising but defensible" from degrading to "obvious"? (Algorithm rule or validation gate)
- When AI returns 10 candidate shows and we only have 6 slots, which 6 do we pick? (Ranking rule)
- If taste-aligned recommendations are the app's primary win, how do we measure them? (Rubric, testing strategy)

**Why this matters:** Taste alignment is **not free**. It's the difference between good recommendations and great ones. The plan assumes it'll happen as a side effect of "asking nicely in the prompt." But without concrete specification, a builder might:
- Return the 6 most-popular shows that match concepts (generic)
- Return the 6 newest shows that match concepts (recency bias)
- Return anything the API gives back without reranking (lazy)

None of these are taste-aligned. The plan needed a **recommendation quality spec** with examples and a rubric (like the `discovery_quality_bar.md` hints at but the plan doesn't operationalize).

### 4. **Concept Ordering and Diversity Are Aspirational, Not Enforced**

**The misunderstanding:**

The plan says concepts are generated, returned, and selected. But it doesn't say:
- "Concepts ordered by strongest aha first" (from concept_system.md section 4)
- "Concepts cover different axes (structure, vibe, emotion, craft)" (from concept_system.md section 5)
- "Generic concepts like 'good writing' are invalid" (from concept_system.md section 7)

The plan just says "8–12 concepts generated." No validation. No diversity check. No aha-ranking mechanism.

**Why this matters:** Concept quality directly affects Alchemy output. Bad concepts → weak ingredient picks → generic recommendations. The plan has all the pieces (prompt tuning, output validation, filtering) but doesn't say which ones to actually use.

A naive builder might:
- Ask AI for concepts, parse the list, show it (no validation)
- Not check for duplicates or near-synonyms
- Not validate specificity (reject "good" + "fun" + "dramatic," keep "hopeful absurdity" + "case-a-week" + "makeshift family")
- Not order by "aha strength" (show them in whatever order the API returns)

The plan needed **concept validation rules in code** (e.g., a `validateConceptPool()` function that rejects generic terms and enforces diversity).

### 5. **Context Composition Is Hand-Waved**

**The misunderstanding:**

The plan says "Feed AI the right surface-specific context inputs" (PRD-090). It mentions:
- Scoop gets show context
- Ask gets library + conversation
- Concepts get shows
- Recs get concepts + library

But it never specifies:
- Which user library fields? (All 500 shows? Top 20 by recency? Only tagged shows?)
- How is library summarized? (Full JSON? A narrative description?)
- Token budget? (Can Ask use 10k tokens or does it cap at 4k?)
- Fallbacks? (If library is huge, what happens?)

**Why this matters:** AI response quality depends 100% on context quality. A Scoop prompt that gets show title + year might say "it's a show from 2019." A Scoop prompt that gets title + year + genres + user's saved shows might say "it's a drama in your 'cozy vibes' library—perfect if you loved Fleabag."

The plan assumes context "happens" but doesn't specify it. A builder has to guess:
- Does the user need their full library or a summary?
- Do we include My Data (status, tags, rating) or just the show catalog metadata?
- How do we handle a user with 5 shows vs 500 shows?

The plan needed a **context schema doc** specifying this per surface.

### 6. **"Consistent Persona" Is Never Made Operational**

**The misunderstanding:**

The plan references the persona doc but doesn't create a **shared prompt template** that all surfaces inherit from. It says:

> "All AI surfaces use one persona with surface-specific adaptations."

But it doesn't show:
- A base system prompt that Scoop, Ask, Concepts, and Recs all start from
- Which parts are shared (voice pillars, honesty principle, spoiler-safety)
- Which parts vary (tone slider positions per surface)
- How to prevent drift (e.g., "if a rebuild changes the Ask prompt, they must also update Scoop")

**Why this matters:** Without a shared template, each surface is a separate implementation. Ask might evolve in one direction (more playful), Scoop in another (more critical), Alchemy recs in a third (more academic). They diverge over time.

The plan needed a **`prompts/system.base.md`** or similar that explicitly defines:
```
BASE SYSTEM PROMPT (all surfaces)
- You are a TV/movie nerd friend
- Be warm, opinionated, spoiler-safe
- [etc.]

SURFACE-SPECIFIC ADAPTATIONS:
- Scoop: add "write as mini-review" + "sections are..."
- Ask: add "be conversational" + "respond in 1-3 paragraphs"
- [etc.]
```

### 7. **Error Handling for AI Is Vague**

**The misunderstanding:**

The plan mentions:
- "Retry malformed JSON once, then fallback"
- "If recommendations can't resolve, show non-interactive"
- "If timeout, show 'Generation timed out'"

But it doesn't specify:
- What counts as "malformed"? (Missing showList? Invalid JSON? Mentions outside TV/movies?)
- What does fallback *do*? (Offer Search? Show cached from last time? Show nothing?)
- How many retries for which errors? (Timeout vs rate-limit vs parse error—different responses?)
- What's logged for monitoring? (If Ask diverges off-domain, how do we catch it?)

**Why this matters:** The robustness of the app depends on these details. A user asks "is True Detective worth watching?" and the AI:
- Option A: Correctly recognizes it and recommends similar dark procedurals
- Option B: Tries to answer a philosophical question about detective work
- Option C: Times out and shows "Try again later"

The plan has no mechanism to distinguish or test these. It's assumed "error handling" just works.

### 8. **Discovery Quality Rubric Is Referenced, Never Integrated**

**The misunderstanding:**

The PRD includes `discovery_quality_bar.md` with a 4-point rubric:
1. Voice adherence (is it the right persona?)
2. Taste alignment (is it grounded in library?)
3. Surprise without betrayal (defensible novelty?)
4. Real-show integrity (does it resolve to real shows?)

The plan **never operationalizes this**. It doesn't say:
- "Every Scoop generation must pass voice adherence check"
- "Every Ask response must pass spoiler-safety gate"
- "Every recommendation set must be evaluated against taste alignment rubric"
- "Every concept set must be checked for generic terms"

**Why this matters:** Without a quality gate, the app ships with AI that *might* be good. With a gate, it ships with AI that's *guaranteed* to meet baseline.

The plan needed to integrate the rubric as:
- A `validateAiOutput()` function
- A test fixture with golden examples ("this is good Scoop," "this is bad Scoop")
- A CI gate that rejects AI-generated content below threshold

---

## The Root Cause

All of these misunderstandings stem from one thing: **the agent conflated "build the system" with "ship the product."**

It designed:
- A robust database schema ✓
- Clear data flows ✓
- Sensible routes and API contracts ✓
- Realistic sequencing ✓

But it did **not** design:
- The prompt strategy
- The context assembly rules
- The quality gates
- The per-surface specifications
- The validation mechanisms

**Why this happened:**

The agent is strongest at **structural and procedural specification** (schemas, routes, data isolation, migrations). It's weakest at **behavioral and qualitative specification** (personality, tone consistency, taste alignment, quality rubrics).

For a database app or a search engine, this is fine—structure is most of the work. But for an **AI-driven discovery app**, the inverse is true. The app's *entire value* lives in whether AI surfaces feel coherent, stay on-brand, and deliver taste-aware results. These are **not** implementation details that follow from good architecture. They're **product surfaces** that require explicit specification.

The plan is like a blueprint for a film studio that specifies the lighting rig, camera mounts, and editing suite perfectly—but never specifies *what kind of film we're making* or *what the cinematography should feel like*.

---

## In Practice, What Gets Built?

If a team executed this plan as-is:

**Phase 1 (Core collection):** Ships solid. Home, Search, Detail, filtering all work. Data persists correctly. No surprises.

**Phase 2 (AI features):** Ships but feels **hollow**.
- Scoop works but reads like Wikipedia, not a friend
- Ask works but drifts into generic chatbot territory sometimes
- Concepts are "good story," "great characters" (generic)
- Recommendations are "popular shows + your genres" (not taste-aligned)

**QA feedback:** "It's functional but it doesn't feel like one thing. The AI surfaces feel like they were built by different teams."

**Stakeholder reaction:** "This isn't wrong, but it's not what we signed up for. The personality is missing. The recommendations don't feel smart."

**What would ship 3 months later:** A revised plan that adds all the stuff that was missing. Prompt templates. Context specs. Validation gates. Quality rubrics.

**Why this is preventable:** Because the PRD *already had this detail*. The plan just needed to **operationalize** what the PRD specified, not invent new requirements.

---

## What Should Have Happened

Before writing "Section 6: AI Integration," the plan should have:

1. **Stated explicitly:** "This app's primary value is taste-aware, on-brand AI. The plan must operationalize the PRD's ai_voice_personality.md, ai_prompting_context.md, and discovery_quality_bar.md specs."

2. **Created:** 
   - A `PROMPT_STRATEGY.md` document with system + user templates per surface
   - A `CONTEXT_SCHEMA.md` specifying composition and token budgets
   - A `GUARDRAILS.md` listing 7 non-negotiable rules with enforcement mechanism
   - A `CONCEPT_VALIDATION.md` specifying generic-term filters and diversity rules
   - A `QUALITY_GATES.md` integrating the rubric as test fixtures and CI gates

3. **Added acceptance criteria:**
   - "Scoop must pass voice adher