# Reflection on the Planning Agent's Understanding

## What It Understood Well

### 1. **Data as the Core Abstraction**
The agent grasped that this product is fundamentally about *persistent, user-overlaid data*. It correctly modeled:
- Every show as a canvas for user annotation (status, tags, rating, scoop)
- Per-field timestamps as the resolution mechanism for sync conflicts
- The distinction between "public catalog metadata" (transient) and "My Data" (sacred)
- Namespace + user partitioning as the integrity boundary

This is deep. The agent didn't just list features; it understood that the product's identity is "your taste made visible and persistent."

### 2. **Isolation as an Operational Primitive**
The plan treats namespace isolation not as a "nice to have" but as a first-class architectural concern. Every API route, every RLS policy, every test reset is designed around it. The agent understood that in a benchmark context, data leakage between runs is a showstopper, not a bug.

### 3. **The Implicit Auto-Save Pattern**
The agent correctly identified that this product has zero "Save" buttons. Status change → auto-save. Rating on unsaved show → auto-save as Done. Tag on unsaved show → auto-save as Later+Interested. This is not just UX polish; it's a contract. The plan specifies all three triggers and their default values.

### 4. **Merge Semantics Under Conflict**
When a show is edited on two devices, or when the catalog is refreshed while the user has local edits, the plan uses timestamps to resolve field-by-field. This is sophisticated. The agent didn't default to "last write wins" or "user always wins"—it implemented a nuanced rule: "user field wins if newer; catalog field wins if user hasn't touched it."

### 5. **The Detail Page as Narrative Architecture**
The plan preserves the exact section order from the PRD (header → facts → relationship controls → overview → scoop → ask → recs → concepts → providers → cast → seasons → budget). The agent understood that *order matters*—the first 15 seconds of the page set emotional tone, and burying discovery behind scroll is a UX crime.

---

## What It Fundamentally Misunderstood

### 1. **AI as a Specifiable Surface, Not a Reference Implementation**
This is the big one. The agent treated AI specs (ai_personality_opus.md, ai_prompting_context.md, discovery_quality_bar.md) as *background reading* rather than *implementation contracts*.

**What the agent did:**
- Mentioned that prompts are "defined in config files"
- Noted that "persona definitions" exist
- Pointed to the external docs as source of truth

**What the agent missed:**
- The product defines specific guardrails ("stay within TV/movies," "spoiler-safe by default," "opinionated honesty") that must be *testable*
- Concept generation has quality axes (specificity, diversity, ordering by aha) that are non-obvious and easy to get wrong
- "Warm, joyful, light in critique" is not a suggestion—it's a red line that, if crossed, breaks the product's emotional DNA
- The AI surfaces are not "features that call an API"—they're *personality expressions* that require continuous voice alignment

The plan has no mechanism to:
- Validate that Ask responses sound like "fun, chatty TV nerd" vs "corporate chatbot"
- Verify concept ordering matches "strongest aha + varied axes"
- Ensure redirection out of domain feels natural, not silent
- Catch prompt drift over time as models change

**The root misunderstanding:** The agent treated the PRD as "describe what the product does" and the supporting docs as "nice flavor text." But the supporting docs are actually *specification*. They're not decoration—they're the difference between "an app that recommends shows" and "*this* app that recommends shows in this specific way."

### 2. **"Next" Status as a Defer, Not a Design Decision**
The plan explicitly notes Next is "data model only, not first-class UI yet." This sounds pragmatic—MVP scope. But the PRD requirement PRD-019 says "Support visible statuses plus hidden `Next`"—it's in the critical path, not the backlog.

**What the agent did:**
- Modeled Next in the database
- Excluded it from UI
- Called it a future extension

**What the agent missed:**
- The PRD is not saying "Next is nice to have." It's saying "the infrastructure must support Next (visible or hidden) because the user mental model requires it."
- Deferring the *design decision* (visible? hidden? under what conditions?) means an implementer has no north star. Do they build the UI to surface Next later? Do they hide it so deeply it's hard to resurrect? Do they half-implement it?

**The misunderstanding:** Scope optimization (MVP vs full) is fine. But deferred design decisions create technical debt and rework. The plan should say "Next is in the data model. For Phase 1, it's hidden in Settings > Advanced or not exposed. Design decision: [reason for deferral]."

### 3. **"Session-Only" AI State as Fully Acceptable Without Trade-Off Analysis**
The plan correctly notes that Ask and Alchemy state are session-only (not persisted). But it doesn't grapple with what this means for the user experience:

- User asks "shows like Severance" → gets 5 recs → app crashes → conversation lost
- User runs Alchemy with 3 shows and 5 concepts → gets 6 recs → closes browser → **can't chain another round** (inputs forgotten)
- User has an Ask session about their taste profile → navigates away → all context gone

**What the agent did:**
- Stated "session-only" as a fact
- Implemented it as in-memory React state + URL params (optional)

**What the agent missed:**
- The PRD says "session-only" but doesn't mandate *why*. The supporting docs (discovery_quality_bar.md) emphasize that AI quality is *subjective and should be reviewed*—cached sessions might introduce stale concepts or logic that users later dislike.
- But the plan never articulates the cost: users lose continuity, can't resume discovery, can't share sessions. Is this acceptable? Why?
- No fallback strategy: if a user loses a session, they start over with no recovery path

**The misunderstanding:** The agent treated "session-only" as a requirement rather than a trade-off. A stronger plan would say: "Ask/Alchemy state is session-only to avoid stale cached recommendations and to keep the product lightweight. Trade-off: users cannot resume interrupted discovery or share sessions. Mitigation: [copy/UX that sets expectations or future export feature]."

### 4. **"Taste-Aware" Without Defining What Grounding Looks Like**
The plan repeatedly says AI should be "taste-aware" and "grounded in the user's library." But it doesn't specify:

- What library data is *actually passed* to the AI? (All saved shows? Just rated? Just tagged? Just saved in the last 30 days?)
- How much context fits in a prompt? (Full library of 500 shows is too much for token budget.)
- What happens if a user has no library yet? (New user asks Ask → what context is sent? Generic prompts?)
- How do you prevent "taste-awareness" from becoming "output is too similar to what user already has"? (User's library is all cozy mysteries → AI recommends only cozy mysteries.)

**What the agent did:**
- Said "include user's library + My Data" in prompts
- Mentioned "older turns summarized" for context depth

**What the agent missed:**
- The specificity question: which library? (All vs filtered vs sampled?)
- The cold-start problem: new users
- The filter bubble risk: taste-aware can mean "trapped in your preferences"
- The implementation decision: does the app send 10 shows or 100? How do you decide?

**The misunderstanding:** Taste-aware is a principle, not a specification. The plan should have said: "Ask receives the user's last 20 saved shows (by `myStatusUpdateDate`) as context; if fewer than 5, system recommends generic entry prompts instead of taste-filtered ones" or similar.

### 5. **Concept System Without Rubric Integration**
The plan describes concepts but doesn't operationalize the quality bar:

From the PRD: concepts must be "1–3 words, evocative, spoiler-free, no generic placeholders like 'good characters'."

**What the agent did:**
- Specified: "bullet list only...each 1–3 words...no generic placeholders"
- Mentioned concepts are "aha-inducing"

**What the agent missed:**
- Who decides if a concept is "generic"? (Is "light in dark moments" evocative or generic? How do you prevent "great writing"?)
- What's the sampling/review strategy? (Every concept generation reviewed? Spot-check? First 10 users?)
- What's the rubric metric? (Specificity score 0–10? Binary vibe check?)
- When does a bad concept batch get caught? (During QA? In production? User complaint?)

**The misunderstanding:** Concepts are not a solved problem. They're an AI output that requires continuous quality gatekeeping. The plan should have included a sampling/review process and acceptance criteria.

---

## The Pattern

The agent understood the **infrastructure, data, and structural UX** brilliantly. It understood:
- How to isolate namespaces
- How to persist and merge data
- How to route users through features
- How to organize a detail page

But it struggled with the **AI behavioral specifications**—the parts where "correctness" is not about the database returning the right record, but about the user *feeling* like they're talking to a particular kind of intelligence.

The agent treated those specs as "reference documentation" (external reading) rather than "product specifications" (implementation tasks). It's a common pattern: **infrastructure is speakable, behavior is assumed to be obvious**.

But this product's heart is in the behavior. "An app that lets you save shows and rate them" is generic. "An app with a specific warm, opinionated AI voice that grounds discovery in your taste and structures concepts as taste ingredients, not genre labels" is this product.

The plan is 92% there, but the 8% gap is distributed across the exact surface that defines whether users love it or find it competent but soulless.