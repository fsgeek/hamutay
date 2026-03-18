# Reflection on the Planning Agent's Understanding

## What It Understood Well

### 1. **Data Model Coherence**
The agent grasped the core insight that *user edits must be preserved across all refresh boundaries*. The timestamp-based conflict resolution, the `selectFirstNonEmpty` pattern for catalog fields, and the concept of "My Data" as an immutable overlay—these show deep understanding of the tension between "fresh catalog metadata" and "user's personal relationship to the show."

This is genuinely hard to get right. Many apps either lose user edits during refresh or prevent refreshing altogether. The plan nails it.

### 2. **Namespace Isolation as a Primitive**
The agent understood that namespace isolation isn't just infrastructure theater—it's a *testability requirement*. The plan uses it as the foundation for repeatable benchmarks, destructive testing, and multi-tenant safety. This is sophisticated thinking about what "benchmark-friendly" actually means.

### 3. **The "Auto-Save Without Friction" Principle**
The plan correctly identified that the PRD's implicit promise ("save shows from tagging, rating, interest selection") requires *no explicit Save button*. The default values (Later+Interested for tags, Done for rating) and the auto-trigger logic show the agent understood this isn't just UX polish—it's a core product behavior that shapes the entire data model.

### 4. **Taste-Aware as a Constraint on Every Surface**
The plan recognized that "taste-aware discovery" isn't a feature—it's an architectural requirement. Every AI surface (Ask, Alchemy, Explore Similar) must receive the user's library as context. The plan threads this through all feature specs, not as an afterthought.

## What It Fundamentally Misunderstood

### 1. **The AI Voice as a *Specifiable* Product Surface (Not Just Aspirational)**

**What the agent did:** Referenced the AI personality docs (ai_personality_opus.md) and listed the surfaces (Scoop, Ask, Alchemy), but then treated AI voice as a *prompt engineering problem* to be solved later.

**What it missed:** The PRD is saying the voice IS the product. It's not "implement Ask, then tune the prompts until it feels right." The voice is a *acceptance criterion*. 

The plan documents that Scoop should be "~150–350 words with clear sections" but doesn't say *how* that's enforced (is there a token counter that rejects long outputs?). It says Ask should be "brisk and dialogue-like" but doesn't specify how you know a response is brisk (word count? sentence structure validation?).

The agent treated these as "guidelines for the prompt" rather than "measurable product requirements." This shows up in the evaluation as gaps in PRD-086 (enforce guardrails) and PRD-091 (validate output against quality bar).

### 2. **The "Concept" as a Specialized Vocabulary, Not Just AI Output**

**What the agent did:** Treated concepts as "1–3 word AI-generated bullets" and left it at that. Specified concept selection UX, concept-based recs, multi-show concept blending.

**What it missed:** The PRD is saying concepts are the *user's taste language*. They're not just recommendations—they're how the user learns to think about what they like. 

The distinction between "good characters" (generic) and "hopeful absurdity" (specific) isn't a prompt tuning problem—it's a *semantic design* problem. The plan doesn't articulate what makes a concept "aha-worthy" vs. "placeholder-y" in implementable terms. It doesn't describe how you avoid a situation where every show gets "great writing, good story, compelling" and concepts become meaningless.

The discovery quality bar (referenced in the PRD) has a concrete definition: **specificity over genericity, diversity across axes, ordered by strength**. The plan mentions this exists but doesn't integrate it into the concept generation pipeline or validation.

### 3. **The "Status System" as a Behavioral Model, Not Just a Database Field**

**What the agent did:** Mapped all six statuses (Active, Later, Wait, Done, Quit, Next), defined interest levels, specified the removal flow.

**What it missed:** Status is meant to *reveal the user to themselves*. The grouping on Collection Home (Active prominent, Excited, Interested, Other collapsed) isn't arbitrary—it's a reflection hierarchy. Active shows you what you're *doing*. Excited shows you what you *want* next. Interested shows the long tail of "maybe someday."

The plan doesn't explain *why* status/interest grouping matters beyond UI organization. It doesn't describe what the app is trying to teach the user (that intention matters, that priority is real, that you can be intentional about your time). It treats status as "a data field to filter on" rather than "a mirror of intentionality."

This manifests in missing a critical gap: **what happens to "Later+Interested" shows after you finish watching?** The plan says you set Done, but doesn't describe the transition experience or what nudges you to move between statuses. It's mechanically correct but emotionally missing.

### 4. **"Taste-Aware" as Requiring a Different Kind of Explainability**

**What the agent did:** Specified that recommendations include reasons (e.g., "Shares hopeful absurdity vibes with Schitt's Creek"), and that Ask mentions shows with context.

**What it missed:** Taste-aware recommendations create a *contract*: if the app recommends something, it's supposed to feel personal, grounded in *my* collection and *my* taste, not generic.

The plan doesn't articulate the failure mode: if Alchemy returns a show that you've already rated poorly, or that contradicts your tags, users feel gaslit ("the app didn't understand me"). The plan specifies that recs must "resolve to real catalog items" (real-show integrity) but not that recs must be *coherent with the user's own data*.

This should be in the validation pipeline: before returning an Alchemy rec, check that it's not already in the user's collection, and that it doesn't contradict strong signals (e.g., if you rated a show "Quit," don't recommend its spiritual sequel without explanation).

### 5. **Auto-Save as Requiring Undo / Error Recovery**

**What the agent did:** Specified auto-save triggers and defaults.

**What it missed:** Auto-save *removes ceremony from intentional saves* but creates ceremony in *unintentional ones*. The plan has no undo, no grace period, no "oops" recovery.

Rating a show by accident (fat-finger on the rating slider) instantly saves it as Done. Tagging a show with a typo auto-saves as Later+Interested. The plan acknowledges this in the evaluation feedback ("Gap 3: Auto-save without explicit confirmation") but doesn't fix it in the plan itself.

This isn't a minor UX polish—it's a trust failure. Users will stop interacting with status/rating/tags if they're afraid of accidents.

### 6. **"Spoiler-Safe by Default" as Requiring Active Content Analysis**

**What the agent did:** Added spoiler-safety to the shared AI rules ("Stay spoiler-safe unless user explicitly requests").

**What it missed:** How does the app *know* if something is a spoiler? The plan assumes the AI prompt is enough, but spoiler-safety requires active detection:
- Does "the show has a twist ending" count as a spoiler?
- Does mentioning the final season count?
- What about character deaths that drive the plot?

The plan doesn't specify a spoiler rubric or validation gate. It treats it as a prompt guideline rather than a *content policy*. This is especially important for Scoop, where the AI is generating original prose—it could easily slip into plot territory without realizing.

## The Meta-Level Pattern

The agent excelled at **structural specification** (routes, data model, API contracts, namespacing) but struggled with **behavioral specification** (what does it feel like to use this? What's the user learning? What's the failure mode if the AI drifts?).

This makes sense given the planning context: the agent was given a PRD that is itself split into two types of documents:
- **Functional PRD** (product_prd.md): "What does the app do?" — very concrete
- **Emotional PRD** (ai_personality_opus.md, philosophy_opus.md): "What does the app feel like?" — aspirational

The agent mapped the functional PRD into code structure extremely well. But it didn't carry the emotional/behavioral PRD forward into the implementation plan. It listed the docs as references ("see ai_personality_opus.md") rather than translating them into measurable acceptance criteria, validation gates, and failure modes.

**The biggest miss:** The plan says "AI voice must be consistent" and "concepts must be specific" but nowhere does it say *how you measure that* or *what happens if you fail*. A proper implementation plan would include:
- Automated validation gates (concept word count, specificity checkers, spoiler keyword filters)
- Human review checkpoints (before Phase 2, QA runs golden scenarios against quality bar)
- Monitoring/alerting for voice drift (log concepts, flag ones tagged "generic," alert on repeated low-quality mentions)
- Undo/recovery patterns (undo for auto-save, grace period for accidental tags)

These aren't separate from the plan—they're part of making the plan real.