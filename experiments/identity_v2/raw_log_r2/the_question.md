# Reflection: What the Planning Agent Understood and Misunderstood

## What It Understood Well

### 1. **The Execution & Infrastructure Layer**
The agent grasped the benchmark requirements deeply. Namespace isolation, user identity scoping, dev-mode auth injection, destructive testing—these are all **correctly and thoroughly specified**. The agent understood that this isn't just a product problem; it's a build problem with specific constraints (Supabase, Next.js, environment-driven config, no Docker requirement). This is the hardest part of the spec to get right, and it did.

### 2. **Data Integrity as a Fundamental Principle**
The agent understood that "user's version takes precedence everywhere" is not a UX guideline—it's an **architectural constraint** that affects every layer:
- Timestamp-based conflict resolution
- Merge semantics that preserve user edits during catalog refreshes
- Upgrade safety without data loss
- Cross-device sync via "newer timestamp wins"

This is sophisticated. It shows the agent understood that the product's value depends on users never losing their data or having their edits silently overwritten.

### 3. **The Status & Interest System**
The auto-save rules, status system, and interest levels are **correctly modeled**:
- Rating unsaved show → Done
- Tagging unsaved show → Later + Interested
- Interested/Excited chips map to Later status
- Removal confirmation + clearing all My Data

The agent got the implicit saves right. This matters because it's the difference between "save button friction" and "feels natural."

### 4. **Show Detail as a Living Page**
The agent correctly understood that the Detail page is not just a display layer—it's a **discovery launchpad**. The narrative hierarchy (media carousel, facts, status/rating controls, Scoop, Ask-about-show, traditional recs, Explore Similar, cast/crew, seasons, etc.) is preserved exactly as specified. The agent understood that order matters and that primary actions (status, rating) should cluster early.

### 5. **Feature Completeness**
Every core feature is present: collection home with filtering, search, Ask, Alchemy, Explore Similar, Person Detail, export. Nothing was missed or collapsed into something else. The agent didn't try to simplify the product; it expanded the spec into implementation tasks.

---

## What It Fundamentally Misunderstood

### 1. **AI as a Specifiable Product (Not a Feature)**
**The Core Misunderstanding:**
The agent treated AI as a *feature to implement* (call the API, stream responses, cache results) rather than as a **specifiable product with measurable behavioral contracts**. 

**Evidence:**
- Identifies that AI should be "warm, joyful, opinionated" but provides zero acceptance criteria for measuring warmth or joy.
- States that Ask should be "brisk and dialogue-like" but has no mechanism to enforce response length, no decision tree for when to expand, no regression test.
- Acknowledges guardrails (spoiler-safe, TV/movies-only, non-generic concepts) as intentions but provides no enforcement points.
- Never references the discovery_quality_bar.md rubric, which exists specifically to make discovery *testable*.

**Why This Matters:**
The PRD explicitly frames AI as rebuild-able: "a new team should be able to reproduce the same emotional and tonal experience without needing to read prompts." The plan does the opposite—it assumes prompts will carry the emotional weight, with no way to verify they do.

This is the difference between:
- **What the agent did:** "Call the AI API, format the response, cache it."
- **What was needed:** "The AI must output X structure, Y tone must be measured by Z, fail hard if these criteria aren't met, and monitor continuously for drift."

### 2. **The Discovery Quality Bar as a Hard Constraint**
**The Core Misunderstanding:**
The agent treated discovery quality as something the AI would naturally provide if prompted well. It never integrated the discovery_quality_bar.md document into the acceptance criteria or acceptance testing.

**Evidence:**
- The requirements catalog includes PRD-091 ("Validate discovery with rubric and hard-fail integrity").
- The PRD document explicitly defines what "good discovery" looks like: 5 dimensions, a scoring rubric, passing thresholds.
- The plan has zero reference to this.
- Section 19 (Acceptance Criteria) lists functional tests but no discovery quality tests.

**Why This Matters:**
This is the most explicit "how do you know you're done?" document in the entire PRD set. By ignoring it, the plan has no way to detect or prevent:
- Concept generation drifting toward generic placeholders ("good writing" instead of "hopeful absurdity").
- Recommendations becoming safe picks instead of surprising-but-defensible taste-aligned gems.
- Ask becoming verbose instead of brisk.
- Scoop losing its gossipy, vivid voice.

The PRD literally provided an acceptance rubric with a scoring formula. The plan should have adopted it wholesale. Instead, the plan assumes quality will emerge from prompt design without verification.

### 3. **Voice as an Implementation Concern, Not Just a Prompt Concern**
**The Core Misunderstanding:**
The agent acknowledged the AI voice spec (warm, joyful, opinionated, spoiler-safe) but treated it as something prompts handle. It didn't ask: "How do we know the prompts actually produce this? How do we test it? How do we catch drift?"

**Evidence:**
- Sections 6.1–6.6 describe AI surfaces (Scoop, Ask, Concepts, Recs) but never specify output validation, parsing, or tone checks.
- No mention of logging concept outputs to detect weak concepts.
- No mention of auditing Ask response lengths.
- No mention of comparing generated Scoops against the "mini blog post" structure requirement.
- Summarization (PRD-070) is stated as happening "after ~10 turns" but no summarization prompt template is provided, no guidance on preserving tone.

**Why This Matters:**
The PRD distinguishes between different kinds of specifications:
- **Voice spec** (ai_voice_personality.md) — describes who the AI is and why.
- **Behavioral contract spec** (ai_prompting_context.md) — describes what input/output looks like.
- **Quality bar spec** (discovery_quality_bar.md) — describes how to test whether the contract is met.

The plan integrated the voice spec (acknowledged it) but never connected it to the contract and quality specs. This is the planning equivalent of writing a job description without interview questions or success metrics.

### 4. **"Prompt Management" as Invisible Infrastructure**
**The Core Misunderstanding:**
The agent mentioned prompts exist, that they're in config files, and that they evolve over time. But it never specified:
- What the prompts actually say (obviously, this is a prompt engineering job).
- How they're tested.
- What constraints they must satisfy.
- How you detect when a prompt has drifted off-brand.

**Evidence:**
Section 6.6 says:
> "Prompts defined in config files (not hardcoded). One config per surface. System message + user message templates with placeholders."

But then provides zero guidance on:
- How Ask summarization preserves voice (mentioned in PRD-070, ignored in plan).
- What the Scoop prompt structure is (PRD says: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict—plan says this once, never again).
- How concept generation validates that outputs are 1–3 words, evocative, non-generic (never specified).
- What the concept-based recommendation reason format is (needs to "explicitly reflect the selected concepts"—how is this enforced?).

**Why This Matters:**
Prompts aren't code; you can't unit test them. But you *can* specify what they must produce and then audit the output. The plan never does this. It's like saying "we'll have good prompts" without defining what "good" means.

### 5. **Turn Summarization as Invisible Token Management**
**The Core Misunderstanding:**
The agent stated that summarization happens after ~10 turns (PRD-070) but treated it as an implementation detail, not a behavioral contract.

**Evidence:**
Section 4.3 says:
> "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated). Preserve feeling/tone in summary (not generic 'system summary' voice)."

Then never again specifies:
- What the summarization prompt is.
- What "preserving feeling/tone" looks like in practice.
- How you test that a summary is gossipy vs. sterile.
- What happens if the summary loses the voice.

**Why This Matters:**
Summarization is critical for keeping Ask conversations grounded while managing token depth. But if the summarization prompt is generic ("provide a brief recap of the conversation"), the persona evaporates. The PRD flags this explicitly: "summaries must preserve the same persona/tone as the chat surface." The plan acknowledges the requirement but provides zero guidance on how to satisfy it. This is a trap waiting to be sprung in the first user test.

---

## The Pattern Underlying These Misunderstandings

The agent understood **product architecture and feature mechanics** but fundamentally misunderstood **product experience as a measurable, testable, regression-preventable thing**.

Put another way:
- **Understood:** "The app needs a collection, a status system, auto-save, AI surfaces, and discovery."
- **Misunderstood:** "The experience of using the AI matters as much as the fact that it exists, and experience is something you specify, measure, and defend against regression."

This gap shows up most clearly in AI surfaces because:
1. **AI surfaces are hard to specify.** You can't write test cases for "warm tone" the way you can for "display poster + title + badges." So it's tempting to skip specification and just "prompt it well."
2. **The PRD made this explicit.** By including ai_voice_personality.md, ai_prompting_context.md, and discovery_quality_bar.md, the PRD was saying: "Experience is part of the spec. Here are the tools to make it testable." The plan should have integrated these documents as acceptance criteria.
3. **The plan had permission to be vague.** Infrastructure and data modeling have hard constraints (Supabase, namespaces, RLS). AI surfaces don't. So the agent took the path of least resistance and deferred to "prompt design will handle this."

---

## What This Means for the Team

**If the team builds to this plan without addressing the AI gaps:**
- The app will work. Collections will persist. Status systems will function. Ask will return recommendations.
- But Ask will feel like a competent chatbot, not a friend.
- Concepts will include weak options that the PRD explicitly forbids.
- Recommendations will be safe instead of taste-aware and surprising.
- Scoop will be competent but generic.
- No one will notice until QA or early users start asking: "Where's the personality?"

**To fix it:**
The team doesn't need to rebuild the plan. It needs to:
1. Adopt the discovery_quality_bar.md rubric as acceptance criteria.
2. Write explicit behavioral contracts for each AI surface (output structure, length limits, tone checks).
3. Specify summarization prompts.
4. Add validation and monitoring hooks.
5. Create golden sets of known-good outputs for regression testing.

This is 2–3 days of planning work, not a rearchitecture. But it's the difference between a good app and an app that feels right.