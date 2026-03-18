# Reflection: What the Planning Agent Understood and Misunderstood

## What It Understood Exceptionally Well

### 1. **The Data Model as the Heart of the Product**

The agent grasped that this app is fundamentally about *persistent, user-owned data that survives across devices, updates, and rebuilds*. It understood:

- **Timestamps as the conflict-resolution primitive.** Not "last write wins" naively, but "last write per field wins," which preserves the intent that a user's rating and status can be edited independently.
- **The overlay pattern.** That every show appearance must fuse public catalog data with private My Data, and that user edits always win. This is the spine of the entire product.
- **Collection membership as a status condition.** That a show is "in collection" iff it has a status—a logical gate that makes removal semantics clean.
- **Merge safety as a first-class concern.** The plan treats merging (catalog refresh + user data, cross-device sync, re-adding shows) as a core behavior, not an edge case.

This is sophisticated. The agent didn't just list "persist data"—it understood *why* data persistence matters (taste profile continuity) and *how* to make it safe (timestamps, merge rules, no data loss on upgrade).

### 2. **The Infrastructure as Enabling Repeatability**

The agent understood that the infrastructure rider isn't about tech choices—it's about *isolation and auditability*. It specified:

- Namespace partitioning with user scoping `(namespace_id, user_id)` on every table.
- That RLS and application-layer filtering must both exist (defense in depth).
- That dev-mode identity injection must be orthogonal to schema design, so OAuth migration is trivial.
- That destructive test runs must be scoped, not global.

This shows the agent read the infrastructure PRD as a *design constraint*, not a checklist. It understood that "each build must be isolated" means "partition every query, not just database names."

### 3. **The Full Feature Stack Without Conflation**

The agent kept clear distinctions between:

- **Search** (dumb catalog lookup) vs. **Ask** (taste-aware chat) vs. **Alchemy** (structured blending). Each has different context, different outputs, different UX rhythm.
- **Scoop** (generated once per show, cached, persisted only if saved) vs. **Mentioned shows** (ephemeral, derived from chat context) vs. **Recommendations** (session-specific, not persisted).
- **Auto-save defaults** (rating → Done, tag → Later/Interested, status → that status) without conflating them.

The plan doesn't muddy these; it keeps them categorically separate.

### 4. **The Phased Launch as Risk Mitigation**

The three phases (MVP collection → AI features → Alchemy & polish) show the agent understood:

- That "taste-aware discovery" is built *on top of* a working collection, not alongside it.
- That AI can be added later without schema breakage.
- That proof of core concepts (collection, filtering, status) matters before betting on AI quality.

This is a sensible rebuild arc.

---

## What It Fundamentally Misunderstood (or Deferred)

### 1. **The AI as a Character, Not a Feature**

The plan treats AI as a *functional component*: "Call API, parse JSON, display results." But the PRD—especially `ai_voice_personality.md`, `ai_prompting_context.md`, and `concept_system.md`—reveals that **the AI is the emotional voice of the product**. It has a persona, guardrails, a philosophy of what it means to be "taste-aware."

The plan says: "Prompts defined in reference docs (ai_personality_opus.md, ai_prompting_context.md)" and then... delegates entirely to those docs. It doesn't internalize what it means to *maintain* that voice across surfaces, or how drift happens, or what happens when a model changes.

**Concrete misunderstanding:** The plan specifies that Scoop output should be "~150–350 words" with sections, but it doesn't specify *what to do if the AI ignores the section structure*. There's no validation gate. A rebuild team could ship a Scoop generator that outputs prose instead of structured sections, and the plan wouldn't catch it.

### 2. **Concept as Design, Not Data**

The agent treats concepts as transient outputs (generate, select, use for filtering). But `concept_system.md` reveals that concepts are a *design language*—they're the bridge between "what the user felt about a show" and "what other shows share that feeling."

The plan doesn't ask: *How do we ensure concepts are truly shared across multi-show inputs?* It says "concepts must represent shared commonality" but doesn't specify how to validate this. Does "hopeful absurdity" work for both *Schitt's Creek* and *Fleabag*? The plan would accept the AI's word for it.

Similarly, the plan doesn't wrestle with *concept stability*. If the same show is concept-queried twice, are the concepts stable? The plan doesn't specify—it just says "do not cache concepts."

**Why this matters:** Concepts are the *ingredient system*. If they're flaky or inconsistent, Alchemy (which depends on users selecting from a stable concept list) breaks. The plan doesn't protect against this risk.

### 3. **The Scoop as Taste Expression, Not Content**

The plan specifies that Scoop is "generated on demand from Show Detail" with "4 hour freshness" and "progressive streaming." These are all correct. But it misses that **Scoop is the product's way of expressing taste back to the user.**

From `ai_voice_personality.md`:
> "Scoop: a *mini blog‑post of taste* that feels like a trusted friend giving you the highs, lows, and who it's for."

The plan's Scoop section just says: "Cache with 4-hour freshness; Only persist if show is in collection." It doesn't specify:

- What happens if the AI declines to generate a Scoop (e.g., "I don't have enough information")? Should the plan retry? Show a fallback?
- How do we know the Scoop is honest about mixed reception (per the guardrails)?
- What makes a Scoop feel like "a trusted friend," not a Wikipedia summary?

The plan treats Scoop as a *feature*, not as a *voice opportunity*. A rebuild team could implement it correctly from the spec and still produce Scoops that feel generic.

### 4. **"Taste-Aware" as Requiring Active Modeling**

The plan says Ask and Alchemy are "taste-aware" and includes the user's library as context. But it doesn't specify *how to model taste from the library.*

For example:
- If a user has saved *The Good Place*, *Fleabag*, and *Schitt's Creek*, what does that taste profile *mean*?
- How does the AI use this to steer recommendations? Random inclusion of the user's genres? Or something deeper?

The plan assumes the AI will "figure it out" from library context. But taste modeling is a craft—it requires deciding what signals matter (Is a saved show's rating more important than its status? Do tags encode taste or just organization?). The plan doesn't specify this.

**Consequence:** A rebuild team could build the plan's infrastructure perfectly and still ship an Ask feature that generates recommendations that feel *generic*, because it doesn't model taste deeply.

### 5. **The Removal Flow as Emotional, Not Transactional**

The plan specifies: "Reselecting status triggers removal confirmation. Copy: 'Remove [Show Title]...'" But `product_prd.md` says:

> "A warning confirmation is shown (with an option to stop asking after repeated removals)."

The plan includes the checkbox ("Don't ask again"). But it doesn't think about *why* this matters. The PRD implies: removing a show is a moment of loss (you're throwing away your rating, your tags, your memories). The confirmation exists not just for safety, but to honor that moment. After 3–5 removals, the user is probably just pruning, so the app gets out of the way.

The plan treats this as a ux checklist item, not as a philosophy about *when the app should be deferential.*

---

## The Pattern

The planning agent excels at **structural and functional correctness**: data flows, persistence, isolation, feature completeness. It fails to internalize **subjective and behavioral requirements**: voice consistency, taste modeling, emotional design, and quality gates that can't be automated.

The three gaps in my evaluation (PRD-077, PRD-082, PRD-091) are all symptoms of this. The plan says "the AI will do X," but doesn't ask "how do we verify the AI did X *well*?" Because "well" requires human judgment—it's about whether the voice feels right, whether concepts feel apt, whether recommendations feel personal.

### The Deeper Insight

The plan was written as if the PRD were a requirements document (which it is) rather than as if it were a *design manifesto* (which it also is). The core three companion docs—`ai_personality_opus.md`, `concept_system.md`, `discovery_quality_bar.md`—exist precisely because the planning agent's instinct is what would happen if you rebuild without them: you'd build *the right thing*, just without *the soul*.

The agent understood the machine. It didn't understand that the machine is supposed to be a friend.