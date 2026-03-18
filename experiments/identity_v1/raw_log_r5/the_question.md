# Reflections on the Plan's Understanding

## What the Planning Agent Understood Well

### 1. **The Data Integrity Model is Crystalline**

The agent fully grasped that this product's soul lives in **user data ownership and conflict resolution**. The plan doesn't just mention timestamps—it understands *why* they matter:
- Per-field timestamps for merge resolution
- The asymmetry between user edits (preserve via timestamp) and catalog refreshes (never overwrite non-nil)
- The removal semantics (status removed = all My Data cleared, not soft-deleted)

This is sophisticated. Most plans would miss the cascade effects. This one got it right.

### 2. **Isolation as a First-Class Constraint**

The agent understood that namespace/user partitioning isn't "nice to have"—it's structural. Every table gets `namespace_id` and `user_id`. RLS policies are explicit. The test reset endpoint is scoped. This is a benchmark requirement, yes, but the plan didn't treat it as a checkbox; it threaded it through architecture, schema, queries, and testing.

### 3. **Auto-Save is Behavioral, Not Just UI**

The agent understood the subtle product rule that saving is *implicit*, not explicit. Setting a status saves immediately. Rating an unsaved show defaults to Done. Adding a tag defaults to Later+Interested. These aren't UI flourishes—they're product logic that touches data model, API contracts, and user experience. The plan captured all three angles.

### 4. **Navigation and Feature Sequencing**

The three-phase rollout (Core Collection → AI Features → Alchemy & Polish) is realistic and respects dependencies. Phase 1 doesn't require AI. Phase 2 stacks Ask, Scoop, and Explore Similar (all use similar context). Phase 3 adds the orchestration layer (Alchemy chaining). This shows understanding of *buildability*, not just features.

### 5. **External Catalog Resolution**

The plan grasps a subtle requirement: AI outputs titles; the system must map them back to real catalog items. It specifies external ID + title match fallback, handles "not found" gracefully (non-interactive mention or handoff to Search). This is a real implementation problem most plans would gloss over.

---

## What the Planning Agent Fundamentally Misunderstood

### 1. **AI is Not Just a Feature—It's a Constraint on the Entire Product**

**The misunderstanding:** The plan treats AI voice/personality as a reference-doc topic. It says "base system prompt defines persona (from ai_personality_opus.md)" and then moves on. It defers to supporting docs for tone, warmth, and guardrails.

**What it missed:** The PRD documents are **prescriptive about product intent, not just style guides**. The ai_voice_personality.md and discovery_quality_bar.md aren't flavor text—they're *requirements* that every AI output must satisfy to be acceptable. The plan should have embedded:

- A **validation pipeline**: every Scoop, Ask response, recommendation reason must pass a quality gate before being shown
- **Prompt engineering as product spec**: not just "call AI with show context" but "the system prompt must enforce these five pillars, and responses scoring <7/10 on the rubric are rejected"
- **Shared constants**: rules like "never output generic concepts" and "reasons must cite which concepts align" shouldn't live only in prompts—they should be testable, auditable constraints

The plan treats prompts as black boxes. But the PRD treats them as *product boundaries*. That's a fundamental disconnect.

### 2. **Concepts Are Not Just Data—They're a Language**

**The misunderstanding:** The plan describes concepts generation as a straightforward API call: "Call AI with appropriate prompt. Parse bullet list into string array. Return to UI for chip selection."

**What it missed:** Concepts are a *vocabulary* the product uses to make taste visible and actionable. The plan should have:

- Specified the concept taxonomy explicitly (structure, vibe, emotion, craft, dynamics)
- Required ordering by relevance and axis diversity (not just "return 8–12")
- Defined what makes a concept "good" (evocative, specific) vs. "bad" (generic, synonymous)
- Built acceptance gates: concepts that fail the quality bar get regenerated
- Treated multi-show concept pools as larger than single-show as a *behavioral requirement*, not a prompt hint

Instead, the plan treats concepts like any other AI output. But the PRD treats them like a *design system language*. The difference is subtle but critical: one is "call an API"; the other is "build a vocabulary."

### 3. **"Taste-Aware" is Not Just Context—It's Accountability**

**The misunderstanding:** The plan includes user library context in AI prompts ("Include user's saved shows + My Data for context"). That's good. But then it assumes the AI will use it. It doesn't specify *how to verify* that recommendations are actually grounded in taste, not just genre-adjacent.

**What it missed:**

- No requirement that recommendation reasons *cite specific concepts or user library signals*
- No fallback for recs that can't be grounded (e.g., "if AI recommends something unrelated to saved shows, ask for justification or reject")
- No distinction between "surprising" (good: pleasantly unexpected but defensible) and "random" (bad: breaks the vibe)

The plan says "recommendations must resolve to real catalog items" (true, critical) but doesn't say "and must be traceable back to why the user would want them." It conflates *coherence* (does it exist?) with *relevance* (does it fit?).

### 4. **The Detail Page is Not Just a Display—It's a Relationship Hub**

**The misunderstanding:** The plan lists all the Detail page sections in order and describes them as layout/UX. It calls out "primary actions clustered early" and "long-tail info down-page." Good UX thinking, but surface-level.

**What it missed:** The Detail page is the *single source of truth for a show*. The supporting doc (detail_page_experience.md) emphasizes that users should leave feeling:
- Oriented in what the show *is*
- Clear on what they *think/feel* about it
- Excited about what to watch next

The plan describes **sections** but not **the narrative flow** that makes a show feel alive. It doesn't specify:
- Why the header carousel is mood-setting (not just "backdrops/posters/logos/trailers")
- How the Scoop becomes the emotional centerpiece (not a bonus toggle)
- Why "Ask about this show" isn't buried—it's a discovery launchpad
- How Explore Similar turns the user into a co-curator (not just "pick the ingredients")

The plan treats Detail as a data display. The PRD treats it as an *invitation to fall in love with a show*.

### 5. **Search Has No AI Voice—But That's a Design Choice, Not a Default**

**The misunderstanding:** The plan nails that "Search does not expose AI voice. It should remain a straightforward catalog search experience." ✓ Correct.

**But it missed the *why*:** Search is intentionally plain because **every other discovery surface is AI-powered**. The contrast makes the AI feel deliberate, not pervasive. Search is the control, the baseline, the "just get me the data" option. By the time a user reaches Ask or Alchemy, the AI voice is earned—they've chosen it.

The plan mentions this but doesn't emphasize it as a design principle. It treats Search as just another feature instead of as a *deliberate restraint* that makes the AI surfaces feel special.

---

## The Core Misunderstanding: Implementation vs. Specification

**In one sentence:** The agent planned *implementation* but missed *specification*.

**What that means:**

The plan is excellent at saying *how to build* (routes, tables, caching, error handling). It's incomplete at saying *what to build such that it feels right*.

- Implementation: "Store aiScoop with a 4-hour TTL." ✓
- Specification: "The Scoop should feel like a trusted friend's magazine review, opinionated and vivid, that helps the user decide if it's worth watching." ← Mostly missing.

- Implementation: "Concepts are 1–3 words, returned as a bullet list." ✓
- Specification: "Concepts are evocative ingredients that expose surprising similarities across genres while remaining grounded in the show's core feeling. Ordering matters. Axis diversity matters. Generic placeholders kill the magic." ← Deferred to docs.

- Implementation: "Parse showList from AI output and resolve titles to catalog items." ✓
- Specification: "Mentioned shows aren't just a data structure—they're a moment where the AI's taste overlaps with the user's curiosity. If the mapping fails, the moment breaks." ← Not captured.

---

## Why This Matters

A team executing this plan as written would ship a **1.0 that works but lacks soul**. It would:
- ✓ Let users build collections
- ✓ Auto-save correctly
- ✓ Isolate namespaces
- ✗ Produce mediocre AI recommendations
- ✗ Generate generic concepts
- ✗ Feel like a competent app, not a taste companion

Then the team would spend weeks in QA realizing that Ask feels impersonal, Scoop feels generic, and Alchemy recommendations feel disconnected from the user's actual taste. They'd iterate on prompts, refine tone, rebuild the concept quality bar. By 1.1, it would be better.

**But if the plan had embedded the spec along with the implementation**, that iteration would start pre-launch, in the prompt engineering phase. The team would know upfront: "Concepts must pass this rubric. Reasons must cite these concepts. Warmth is measured by this checklist."

---

## What Would Close These Gaps

The plan would be nearly perfect if Section 6 (AI Integration) expanded from ~2,500 words to ~4,000 words and added:

1. **A Shared Guardrails Module** — constants for domain, spoiler-safety, honesty, specificity. Every prompt inherits these.

2. **Tone Implementation Patterns** — extract warmth/joy/lightness into concrete phrasing examples. What does "light in dark moments" sound like in a Scoop? How does Ask avoid being prescriptive?

3. **Concept Quality Gate** — post-processing that validates concepts against the taxonomy, checks for genericness, enforces ordering and axis diversity.

4. **Recommendation Validation Rubric** — recs must cite which concepts they match, must be resolvable to real shows, must feel surprising but defensible. Include rejection logic.

5. **Acceptance Criteria Tied to Tests** — Section 9.4 should reference discovery_quality_bar.md. Test cases should validate tone, taste alignment, and specificity, not just "did the endpoint return JSON?"

The architecture is solid. The feature scope is complete. The data model is robust. The missing piece is **embedding product intent into the implementation spec**, not just deferring it to supporting docs.