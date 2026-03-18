# Reflection: What the Plan Got Right and What It Missed

## What the Plan Understood Exceptionally Well

### 1. **The Data Model as a Social Contract**

The plan demonstrates sophisticated grasp of the core insight: a show has *two truths* that must coexist—public catalog metadata and private user overlay. The timestamp-based conflict resolution (section 5.5, 2.3) shows the planner understood that **user edits are sacred**. When a show exists on two devices with different ratings, the newer timestamp wins—not because it's more "correct," but because the user's latest intent is the source of truth. This is a nuanced product understanding that goes beyond typical CRUD apps.

The merge rules (section 7.2) are particularly strong: "Never overwrite a non-empty stored string/array with an empty string/empty array; never overwrite non-nil with nil." This reveals understanding that **data loss through refresh is the cardinal sin** for a personal collection app. Most engineers would miss this; this plan got it.

### 2. **Auto-Save as a Behavioral Philosophy, Not Just a Feature**

Section 5.2 (Auto-Save Triggers) and section 4.5 (Detail page auto-save behaviors) show the planner internalized the PRD's philosophy: *friction is the enemy of collection-building*. Rating an unsaved show should auto-save as Done (because rating implies watched). Adding a tag should auto-save as Later + Interested (because tagging shows intent). These aren't arbitrary rules—they're **coherent inference rules** that let users build their collection through natural actions, not modal dialogs.

The plan even catches the nuance that rating an unsaved show defaults to Done, not Later, because the default assumption changes based on the action. This is thoughtful product thinking.

### 3. **Namespace Isolation as Non-Negotiable Infrastructure**

The plan treats namespace isolation not as "nice to have" but as **foundational to testability and benchmarking**. Every table has `(namespace_id, user_id)` as the partition key (section 2.2). The reset endpoint (section 9.2) scopes destructively to namespace only. The RLS policies (section 2.2) enforce it at the database layer, not the application layer. This shows understanding that **isolation is not a feature you bolt on—it's architecture**.

This is the kind of thing that separates a plan that *passes* benchmark isolation requirements from one that *passes safely*.

### 4. **The Status System as Relationship States, Not Task States**

The plan correctly models the five statuses (Active, Later, Done, Quit, Wait) as **relationship states with the user**, not task-management states. A show can be Done and still be "in collection" (you watched it, you care about it, you might rewatch it). This is why removing status deletes the show entirely (section 5.4)—not because watched shows are forgotten, but because status is the membership credential. This distinction is subtle and easy to get wrong; the plan got it right.

The interest levels (Excited vs Interested) are modeled as **qualifiers on Later only**, not as universal priorities. This is correct per the PRD and shows the planner didn't conflate interest with status.

### 5. **Detail Page as Discovery Launchpad, Not Just Display**

Section 4.5 structures the Detail page with narrative hierarchy (section 4.5, referencing the detail_page_experience.md spec). The plan understands that every section should answer a question or enable an action:
- Header answers: "What does this show feel like?"
- Core facts answer: "When is it? How long?"
- Status/rating answer: "What do I think?"
- Scoop answers: "Should I watch it?"
- Explore Similar answers: "What else like this?"

This is **not a documentation display**; it's a **discovery engine disguised as a detail page**. The plan got the philosophy.

---

## What the Plan Fundamentally Misunderstood (or Didn't Understand)

### 1. **AI Is Not Implementation—It's Specification**

This is the deepest misunderstanding. The plan treats AI as a **module to write code for**, not as a **product surface to specify**. 

Evidence:
- Section 6 (AI Integration) describes API contracts and context feeding but **never specifies what output is allowed, what is forbidden, or how to tell the difference**.
- The plan says "spoiler-safe by default" and "opinionated honesty" but never defines what those mean in code terms. How do you detect a spoiler in generated text? What counts as "gushing for no reason"?
- Concepts should be "evocative, not generic" (PRD-076). The plan says this but provides **no validation rule**. What's the difference between "dark, intense, brooding" (good) and "dark, dark, dark" (bad)? The plan doesn't know.
- Ask's `showList` format is specified as a string (Section 6.3) but the plan never specifies: what happens if the AI outputs malformed JSON? Does it retry? With what instructions? How many times? The plan says "retry once" in passing (PRD-073) but doesn't build it into the implementation spec.

**The misunderstanding:** The planner assumed that if you write a good system prompt (relying on ai_personality_opus.md and ai_prompting_context.md), the AI will just *do it*. But **prompts are not specifications**. A specification says "this must happen; if it doesn't, fail with this error." A prompt says "try to do this; maybe the model will understand."

The PRD's supporting docs (ai_voice_personality.md, ai_prompting_context.md, discovery_quality_bar.md) are *descriptive*—they describe what the persona should feel like, what guardrails exist, what quality looks like. They are **not prescriptive implementations**. The plan conflated the two.

### 2. **Quality Assurance Is Not Testing—It's Specification + Validation**

Related to #1: the plan has no QA section for AI surfaces. Section 9 (Testing & QA) covers "Data persistence," "Auto-save," "Collection filtering," "Show Detail" (all data-centric) but does not specify:
- How to test that Ask responses are spoiler-safe.
- How to test that concepts are non-generic.
- How to test that Scoop has the right emotional tone.
- How to test that recommendations are "surprising but defensible."

The plan assumed these things would emerge naturally from the prompt. They won't. The discovery_quality_bar.md in the PRD is a *human rubric* for hand-testing. It says "Score voice adherence 0–2: pass if warm, playful, opinionated." A human can do this. **Code cannot**, unless you build validators.

**The misunderstanding:** The planner thought "write good prompts" = "AI quality is handled." In reality, AI quality requires:
1. Explicit output specification (what format, what constraints, what's allowed).
2. Validation code (checks that output matches spec; logs violations; retries or falls back).
3. Regression tests (golden set of inputs with expected outputs; compare new model/prompt against golden set).
4. Human QA gates (before merge, sample outputs and hand-score against rubric).

None of this is in the plan.

### 3. **"Taste-Aware" Is Vague Without Operationalization**

The plan says AI surfaces should be "taste-aware" multiple times (sections 4.3, 6.1, 6.5). But what does this mean?

From the PRD: "recommendations steered by user-selected concepts" and "grounded in what the user saves and how they label it" and "taste-aligned" (PRD-084).

The plan interprets this as: **include the user's library in the AI context** (section 6.1, "Feed AI the right surface-specific context inputs"). That's correct but incomplete.

What the plan *doesn't* specify:
- How much of the library? (All shows? Top 10? Shows with tags?)
- In what format? (Just titles? Full metadata? My Data?)
- Does the AI validate that recommendations don't duplicate library items?
- Does the AI bias away from recent watches (to avoid "more of the same") or toward them (to match current taste)?
- If a recommendation can't resolve to a real show, does the system reject it and retry, or show it as "not in catalog"?

The plan says these things implicitly ("taste-aware grounding," "real show integrity") but never makes them operational requirements.

**The misunderstanding:** The planner assumed "feed the AI the user's library" = "AI will naturally be taste-aware." In reality, taste-awareness is an **optimization and filtering problem** that requires explicit logic:
- Library summarization: what to send to the AI (too much = token bloat; too little = lost taste signal).
- Recommendation validation: does this rec align with the selected concepts? Does it exist in the catalog? Is it in the user's library already?
- Fallback behavior: if the top AI pick doesn't resolve, what's the second choice?

Without these, "taste-aware" is aspirational.

### 4. **Concepts Are Not Natural Language Features—They're Design Objects**

The plan treats concepts as **AI-generated artifacts** (section 6.4: "Call AI with appropriate prompt. Parse bullet list into string array. Return to UI for chip selection"). That's one part of the story. But the PRD is clear: concepts are **design choices that shape discovery**.

Evidence from the PRD:
- "concepts must be **shared across all** input shows" (for Alchemy, PRD-082).
- Concepts should be ordered by "strongest aha" first (PRD-077).
- "Diversity: Concepts should cover different axes (structure, vibe, emotion) rather than 8 synonyms" (concept_system.md).
- Multi-show generation should return "larger pool of options than single-show" (PRD-082).

The plan says **none of this**. It just says:
- Section 4.4: "Server calls AI with multi-show concept prompt. Returns 8–12 concepts."
- Section 6.4: "Parse bullet list into string array. Return to UI."

**Missing:**
- Specification of what "shared across all" means computationally. Does the AI know which shows overlap? Does the system deduplicate?
- Specification of how "aha-ness" is ranked. By model temperature? By user selection patterns? By concept uniqueness?
- Specification of multi-show pool size. The plan says "8–12 concepts" for both single and multi-show, which contradicts PRD-082 ("larger option pool").
- Validation: how do you detect that 8 synonyms came back? How do you retry for diversity?

**The misunderstanding:** The planner treated concepts as a natural language problem ("let the AI generate them") when they're actually a **product design problem** ("what makes a good concept for this user in this context, and how do we ensure the AI delivers it?").

### 5. **Export/Import Is Specified as Missing, But the Missing Part Is Critical**

Section 4.7 specifies export (PRD-098, PRD-099): produce a `.zip` with `backup.json` containing shows + My Data with ISO-8601 dates. This is implemented.

But the PRD also mentions (section 7.7): "Import / Restore: desired but not currently implemented; see Open Questions."

The plan copies this note into section 18 (Open Questions & Future Extensions) without understanding **why import is critical for data continuity** (PRD-034: "Preserve saved libraries across data-model upgrades").

If a user:
1. Builds a collection over 6 months.
2. Exports it.
3. The app has a major data-model change.
4. The app refuses to import the old backup and forces the user to rebuild...

...that violates PRD-034. The plan doesn't see this. It treats import as a nice-to-have feature, not a **hard requirement for data continuity**.

**The misunderstanding:** The planner saw "export" and "import" as UI features, not as **paired data-safety mechanisms**. Export without import is incomplete.

### 6. **Error Handling for AI Is Not the Same as Error Handling for Data**

Section 12 (Error Handling & Recovery) covers database errors, network errors, missing catalog items. But it **does not address AI-specific failure modes**:
- What if the AI provider rate-limits mid-conversation? (Ask gets stuck; chat history lost; user frustrated.)
- What if Scoop generation times out? (User sees "Generating..." forever; no timeout message; no "try again" button.)
- What if concept generation returns 3 concepts instead of 8? (Alchemy flow breaks; "Conceptualize Shows" has no good options.)
- What if recommendations can't resolve? (User sees empty recs grid; no fallback to traditional catalog recs; no error message.)

The plan assumes these won't happen or that generic error handling suffices. It doesn't.

**The misunderstanding:** The planner didn't distinguish between **catastrophic errors** (database down = app down) and **degraded errors** (AI slow = offer fallback). Ask should work even if Scoop is slow. Alchemy should work even if AI rate-limits the first call.

---

## The Core Pattern

All these misunderstandings point to one root cause:

**The plan treats AI as an engineering implementation detail, not as a product specification problem.**

The PRD's supporting documents (ai_voice_personality.md, ai_prompting_context.md, concept_system.md, discovery_quality_bar.md) are rich, detailed, and **human-readable**. They describe what the product *should feel like* and what the *design intent* is.

The plan read these docs and said: "Okay, so I need to call an AI API with a system prompt and some context. I'll implement that."

What the plan should have said: "Okay, so the AI needs to reliably:
1. Stay in TV/movie domain (detect out-of-domain and redirect).
2. Output spoiler-safe content (validate; regenerate if violation detected).
3. Generate specific, evocative concepts (validate; fail if generic; log for monitoring).
4. Resolve recommendations to real shows (validate; supplement with catalog recs if needed).
5. Maintain consistent persona across surfaces (test against quality bar; regression test on model upgrade).

How do I operationalize each of these in code?"

The plan jumped straight to implementation without intermediate step: **specification of AI output contracts and validation**.

---

## What This Means

The plan will **build a working app that technically implements the PRD**. But it will likely:

1. Ship with AI surfaces that occasionally drift from the intended persona (no guardrail enforcement).
2. Have mention resolution fail silently when JSON is malformed (no output validation).
3. Generate concepts that are sometimes generic or redundant (no diversity validation).
4. Fail ungracefully when AI providers time out or rate-limit (no degradation logic).
5. Have no regression detection when models are upgraded (no golden set testing).

These are **quality failures, not functionality failures**. The app will exist and the features will work, but the soul will be missing—exactly what the PRD's opening statement in philosophy_opus.md warns against.

The planner understood the **data soul** perfectly (status system, timestamps, auto-save, namespace isolation). But it missed the **AI soul**—the fact that taste-aware discovery only works if the AI is reliably held to a standard, not just pointed in a direction.