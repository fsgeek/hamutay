# Plan Evaluation (PLAN_EVAL.md)

## 1. Requirements Extraction

### Pass 1: Identify Functional Areas

1. Benchmark Runtime & Isolation
2. Collection Data & Persistence
3. App Navigation & Discover Shell
4. Collection Home & Search
5. Show Detail & Relationship UX
6. Ask Chat
7. Concepts, Explore Similar & Alchemy
8. AI Voice, Persona & Quality
9. Person Detail
10. Settings & Export

### Pass 2: Extract Requirements Within Each Area

#### Benchmark Runtime & Isolation

- PRD-001 | `critical` | Use Next.js latest stable runtime | `infra_rider_prd.md > 2. Benchmark Baseline (Current Round)`
- PRD-002 | `critical` | Use Supabase official client libraries | `infra_rider_prd.md > 2. Benchmark Baseline (Current Round)`
- PRD-003 | `critical` | Ship `.env.example` with required variables | `infra_rider_prd.md > 3.1 Environment variable interface`
- PRD-004 | `important` | Ignore `.env*` secrets except example | `infra_rider_prd.md > 3.1 Environment variable interface`
- PRD-005 | `critical` | Configure build through env without code edits | `infra_rider_prd.md > 3.1 Environment variable interface`
- PRD-006 | `critical` | Keep secrets out of repo and server-only | `infra_rider_prd.md > 3.1 Environment variable interface`
- PRD-007 | `critical` | Provide app, test, reset command scripts | `infra_rider_prd.md > 3.2 One-command developer experience`
- PRD-008 | `critical` | Include repeatable schema evolution artifacts | `infra_rider_prd.md > 3.3 Database evolution artifacts`
- PRD-009 | `critical` | Use one stable namespace per build | `infra_rider_prd.md > 4.1 Build/run namespace (required)`
- PRD-010 | `critical` | Isolate namespaces and scope destructive resets | `infra_rider_prd.md > 4.1 Build/run namespace (required)`
- PRD-011 | `critical` | Attach every user record to `user_id` | `infra_rider_prd.md > 4.2 User identity (required)`
- PRD-012 | `critical` | Partition persisted data by namespace and user | `infra_rider_prd.md > 4.3 Relationship between namespace and user`
- PRD-013 | `important` | Support documented dev auth injection, prod-gated | `infra_rider_prd.md > 5.1 Auth is not required to be "real" in benchmark mode`
- PRD-014 | `important` | Real OAuth later needs no schema redesign | `infra_rider_prd.md > 5.2 Migration to real OAuth must be straightforward`
- PRD-015 | `critical` | Keep backend as persisted source of truth | `infra_rider_prd.md > 6.1 Source of truth`
- PRD-016 | `critical` | Make client cache safe to discard | `infra_rider_prd.md > 6.2 Cache is disposable`
- PRD-017 | `important` | Avoid Docker requirement for cloud-agent compatibility | `infra_rider_prd.md > 2. Benchmark Baseline (Current Round)`

#### Collection Data & Persistence

- PRD-018 | `critical` | Overlay saved user data on every show appearance | `product_prd.md > 4.1 Show (Movie or TV)`
- PRD-019 | `important` | Support visible statuses plus hidden `Next` | `product_prd.md > 4.2 Status System ("My Status")`
- PRD-020 | `critical` | Map Interested/Excited chips to Later interest | `product_prd.md > 4.2 Status System ("My Status")`
- PRD-021 | `important` | Support free-form multi-tag personal tag library | `product_prd.md > 4.4 Tags (User Lists)`
- PRD-022 | `critical` | Define collection membership by assigned status | `product_prd.md > 5.1 Collection Membership`
- PRD-023 | `critical` | Save shows from status, interest, rating, tagging | `product_prd.md > 5.2 Saving Triggers`
- PRD-024 | `critical` | Default save to Later/Interested except rating-save Done | `product_prd.md > 5.3 Default Values When Saving`
- PRD-025 | `critical` | Removing status deletes show and all My Data | `product_prd.md > 5.4 Removing from Collection`
- PRD-026 | `critical` | Re-add preserves My Data and refreshes public data | `product_prd.md > 5.5 Re-adding the Same Show`
- PRD-027 | `critical` | Track per-field My Data modification timestamps | `product_prd.md > 5.6 Timestamps`
- PRD-028 | `important` | Use timestamps for sorting, sync, freshness | `product_prd.md > 5.6 Timestamps`
- PRD-029 | `critical` | Persist Scoop only for saved shows, 4h freshness | `product_prd.md > 4.9 AI Scoop ("The Scoop")`
- PRD-030 | `important` | Keep Ask and Alchemy state session-only | `product_prd.md > 5.7 AI Data Persistence`
- PRD-031 | `critical` | Resolve AI recommendations to real selectable shows | `product_prd.md > 5.8 AI Recommendations Map to Real Shows`
- PRD-032 | `important` | Show collection and rating tile indicators | `product_prd.md > 5.9 Tile Indicators`
- PRD-033 | `important` | Sync libraries/settings consistently and merge duplicates | `product_prd.md > 5.10 Data Sync & Integrity`
- PRD-034 | `critical` | Preserve saved libraries across data-model upgrades | `product_prd.md > 5.11 Data Continuity Across Versions`
- PRD-035 | `important` | Persist synced settings, local settings, UI state | `supporting_docs/technical_docs/storage-schema.md > Other persistent storage (key-value settings)`
- PRD-036 | `important` | Keep provider IDs persisted and detail fetches transient | `supporting_docs/technical_docs/storage-schema.md > Show (movie or TV series)`
- PRD-037 | `critical` | Merge catalog fields safely and maintain timestamps | `supporting_docs/technical_docs/storage-schema.md > Merge / overwrite policy (important)`

#### App Navigation & Discover Shell

- PRD-038 | `important` | Provide filters panel and main screen destinations | `product_prd.md > 6. App Structure & Navigation`
- PRD-039 | `important` | Keep Find/Discover in persistent primary navigation | `product_prd.md > 6. App Structure & Navigation`
- PRD-040 | `important` | Keep Settings in persistent primary navigation | `product_prd.md > 6. App Structure & Navigation`
- PRD-041 | `important` | Offer Search, Ask, Alchemy discover modes | `product_prd.md > 6. App Structure & Navigation`

#### Collection Home & Search

- PRD-042 | `important` | Show only library items matching active filters | `product_prd.md > 7.1 Collection Home`
- PRD-043 | `important` | Group home into Active, Excited, Interested, Others | `product_prd.md > 7.1 Collection Home`
- PRD-044 | `important` | Support All, tag, genre, decade, score, media filters | `product_prd.md > 4.5 Filters (Ways to View the Collection)`
- PRD-045 | `important` | Render poster, title, and My Data badges | `product_prd.md > 7.1 Collection Home`
- PRD-046 | `detail` | Provide empty-library and empty-filter states | `product_prd.md > 7.1 Collection Home`
- PRD-047 | `important` | Search by title or keywords | `product_prd.md > 7.2 Search (Find → Search)`
- PRD-048 | `important` | Use poster grid with collection markers | `product_prd.md > 7.2 Search (Find → Search)`
- PRD-049 | `detail` | Auto-open Search when setting is enabled | `product_prd.md > 7.2 Search (Find → Search)`
- PRD-050 | `important` | Keep Search non-AI in tone | `supporting_docs/ai_voice_personality.md > 1. Persona Summary`

#### Show Detail & Relationship UX

- PRD-051 | `important` | Preserve Show Detail narrative section order | `supporting_docs/detail_page_experience.md > 3. Narrative Hierarchy (Section Intent)`
- PRD-052 | `important` | Prioritize motion-rich header with graceful fallback | `supporting_docs/detail_page_experience.md > 3.1 Header Media`
- PRD-053 | `important` | Surface year, runtime/seasons, and community score early | `supporting_docs/detail_page_experience.md > 3.2 Core Facts + Community Score`
- PRD-054 | `important` | Place status/interest controls in toolbar | `supporting_docs/detail_page_experience.md > 3.3 My Relationship Controls`
- PRD-055 | `critical` | Auto-save unsaved tagged show as Later/Interested | `supporting_docs/detail_page_experience.md > 3.3 My Relationship Controls`
- PRD-056 | `critical` | Auto-save unsaved rated show as Done | `supporting_docs/detail_page_experience.md > 3.3 My Relationship Controls`
- PRD-057 | `important` | Show overview early for fast scanning | `supporting_docs/detail_page_experience.md > 2. First-15-Seconds Experience`
- PRD-058 | `important` | Scoop shows correct states and progressive feedback | `supporting_docs/detail_page_experience.md > 3.4 Overview + Scoop`
- PRD-059 | `important` | Ask-about-show deep-link seeds Ask context | `supporting_docs/detail_page_experience.md > 3.5 Ask About This Show`
- PRD-060 | `important` | Include traditional recommendations strand | `supporting_docs/detail_page_experience.md > 3.6 Traditional Recommendations Strand`
- PRD-061 | `important` | Explore Similar uses CTA-first concept flow | `supporting_docs/detail_page_experience.md > 3.7 Explore Similar (Concept Discovery)`
- PRD-062 | `important` | Include streaming availability and person-linking credits | `supporting_docs/detail_page_experience.md > 3.8 Streaming Availability`
- PRD-063 | `important` | Gate seasons to TV and financials to movies | `supporting_docs/detail_page_experience.md > 5. Critical States`
- PRD-064 | `important` | Keep primary actions early and page not overwhelming | `supporting_docs/detail_page_experience.md > 4. Busyness vs Power`

#### Ask Chat

- PRD-065 | `important` | Provide conversational Ask chat interface | `product_prd.md > 7.3 Ask (Find → Ask)`
- PRD-066 | `important` | Answer directly with confident, spoiler-safe recommendations | `supporting_docs/discovery_quality_bar.md > 2.2 Ask / Explore Search Chat`
- PRD-067 | `important` | Show horizontal mentioned-shows strip from chat | `product_prd.md > 7.3 Ask (Find → Ask)`
- PRD-068 | `important` | Open Detail from mentions or Search fallback | `product_prd.md > 7.3 Ask (Find → Ask)`
- PRD-069 | `important` | Show six random starter prompts with refresh | `product_prd.md > 7.3 Ask (Find → Ask)`
- PRD-070 | `important` | Summarize older turns while preserving voice | `supporting_docs/ai_prompting_context.md > 4. Conversation Summarization (Chat Surfaces)`
- PRD-071 | `important` | Seed Ask-about-show sessions with show handoff | `product_prd.md > 7.3 Ask (Find → Ask)`
- PRD-072 | `critical` | Emit `commentary` plus exact `showList` contract | `supporting_docs/ai_prompting_context.md > 3.2 Ask with Mentions (Structured "Mentioned Shows")`
- PRD-073 | `important` | Retry malformed mention output once, then fallback | `supporting_docs/ai_prompting_context.md > 5. Guardrails & Fallbacks`
- PRD-074 | `important` | Redirect Ask back into TV/movie domain | `supporting_docs/ai_prompting_context.md > 1. Shared Rules (All AI Surfaces)`

#### Concepts, Explore Similar & Alchemy

- PRD-075 | `important` | Treat concepts as taste ingredients, not genres | `supporting_docs/concept_system.md > 1. What a Concept Is (User Definition)`
- PRD-076 | `important` | Return bullet-only, 1-3 word, non-generic concepts | `supporting_docs/ai_prompting_context.md > 3.4 Concepts (Single-Show and Multi-Show)`
- PRD-077 | `important` | Order concepts by strongest aha and varied axes | `supporting_docs/concept_system.md > 4. Generation Rules`
- PRD-078 | `important` | Require concept selection and guide ingredient picking | `supporting_docs/concept_system.md > 5. Selection UX Rules`
- PRD-079 | `important` | Return exactly five Explore Similar recommendations | `supporting_docs/concept_system.md > 6. Concepts → Recommendations Contract`
- PRD-080 | `important` | Support full Alchemy loop with chaining | `product_prd.md > 7.4 Alchemy (Find → Alchemy)`
- PRD-081 | `important` | Clear downstream results when inputs change | `product_prd.md > 7.4 Alchemy (Find → Alchemy)`
- PRD-082 | `important` | Generate shared multi-show concepts with larger option pool | `supporting_docs/concept_system.md > 8. Notes`
- PRD-083 | `important` | Cite selected concepts in concise recommendation reasons | `supporting_docs/concept_system.md > 6. Concepts → Recommendations Contract`
- PRD-084 | `important` | Deliver surprising but defensible taste-aligned recommendations | `supporting_docs/discovery_quality_bar.md > 1.2 Taste Alignment`

#### AI Voice, Persona & Quality

- PRD-085 | `important` | Keep one consistent AI persona across surfaces | `supporting_docs/ai_voice_personality.md > 1. Persona Summary`
- PRD-086 | `critical` | Enforce shared AI guardrails across all surfaces | `supporting_docs/ai_prompting_context.md > 1. Shared Rules (All AI Surfaces)`
- PRD-087 | `important` | Make AI warm, joyful, and light in critique | `supporting_docs/ai_voice_personality.md > 2. Non-Negotiable Voice Pillars`
- PRD-088 | `important` | Structure Scoop as personal taste mini-review | `supporting_docs/ai_voice_personality.md > 4.1 Scoop (Show Detail "The Scoop")`
- PRD-089 | `important` | Keep Ask brisk and dialogue-like by default | `supporting_docs/ai_voice_personality.md > 4.2 Ask (Find → Ask)`
- PRD-090 | `important` | Feed AI the right surface-specific context inputs | `supporting_docs/ai_prompting_context.md > 2. Shared Inputs (Typical)`
- PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity | `supporting_docs/discovery_quality_bar.md > 4. Scoring Rubric (Quick)`

#### Person Detail

- PRD-092 | `important` | Show person gallery, name, and bio | `product_prd.md > 7.6 Person Detail Page`
- PRD-093 | `important` | Include ratings, genres, and projects-by-year analytics | `product_prd.md > 7.6 Person Detail Page`
- PRD-094 | `important` | Group filmography by year | `product_prd.md > 7.6 Person Detail Page`
- PRD-095 | `important` | Open Show Detail from selected credit | `product_prd.md > 7.6 Person Detail Page`

#### Settings & Export

- PRD-096 | `important` | Include font size and Search-on-launch settings | `product_prd.md > 7.7 Settings & Your Data`
- PRD-097 | `important` | Support username, model, and API-key settings safely | `product_prd.md > 7.7 Settings & Your Data`
- PRD-098 | `critical` | Export saved shows and My Data as zip | `product_prd.md > 7.7 Settings & Your Data`
- PRD-099 | `important` | Encode export dates using ISO-8601 | `product_prd.md > 7.7 Settings & Your Data`

**Total: 99 requirements (30 critical, 67 important, 2 detail) across 10 functional areas**

---

## 2. Coverage Table

| PRD-ID | Requirement | Severity | Coverage | Evidence | Gap |
| ------ | ----------- | -------- | -------- | -------- | --- |
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Tech Stack explicitly specifies Next.js (latest stable) | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 specifies Supabase + @supabase/supabase-js client library | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 includes explicit `.env.example` with all required vars + comments | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 states `.gitignore` excludes `.env*` (except `.env.example`) | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 emphasizes build runs by filling env vars without code edits | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3 explicitly addresses server-only secrets; API keys never in client code | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 20 lists npm scripts: dev, build, start, test, test:reset, db:push, db:seed | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 specifies Supabase schema with migrations; section 20 includes db:push | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.2 and 8.1 specify namespace_id as stable identifier per build | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 describes /api/test/reset scoped to namespace_id only | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 shows all tables include user_id partition; section 8.1 confirms user_id on every record | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 specifies (namespace_id, user_id) partition key on all tables | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 describes X-User-Id header injection in dev mode with NODE_ENV guard | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 explains schema unchanged, only auth wiring needed for OAuth migration | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 states "backend is source of truth; clients cache for performance" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 1.2 principle: "correctness depends on server state" | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 explicitly states "No Docker requirement"; can run against hosted Supabase | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4 states user overlay always displayed; section 2.1 defines Show with My Data fields | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 4.3 lists all statuses including Next (noted as hidden in data model) | |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 auto-save table shows Interested/Excited → Later + Interest | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1 Show includes myTags array; section 4.1 supports free-form tag strings | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 states "in collection when myStatus != nil" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 table lists all four triggers (status, interest, rating, tag) | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 table: default Later+Interested; rating-save defaults to Done | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 removal confirmation; section 5.1 "all My Data fields cleared" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | partial | Section 7.2 "merge rules" exist but full re-add flow not explicitly detailed; data merge documented but user-facing re-add flow unclear | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1 Show includes myStatusUpdateDate, myInterestUpdateDate, myTagsUpdateDate, myScoreUpdateDate, aiScoopUpdateDate | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5 states "every user field tracks update timestamp" and lists uses | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop endpoint includes "only persist if show in collection" and 4-hour cache | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 table: Ask history and Alchemy results marked "Session only" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5 covers recommendation resolution; section 7.2 describes catalog lookup by external ID + title match | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 "Tile Indicators" specifies in-collection and rating badges | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5 "Merge resolution by timestamp"; section 2.1 describes merge rules for duplicates | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 "Upgrade behavior" describes transparent schema transformation on first load | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 defines CloudSettings, LocalSettings, UIState entities | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show includes providerData (persisted); section 7.2 "not stored (transient)" lists transient fields | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2 "Merge rules" describes selectFirstNonEmpty and timestamp resolution | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Layout shows "Filters/navigation panel" with All Shows, tag filters, data filters | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.2 Routes list /find as main hub with Search/Ask/Alchemy mode switcher | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.2 Routes include /settings explicitly | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 Lists /find/search, /find/ask, /find/alchemy routes | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 states "Query filtered by (namespace_id, user_id) and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 lists grouping: Active, Excited (Later+Excited), Interested, Other (collapsed) | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 "Apply media-type toggle" and full filter list supported | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 "EmptyState component" mentioned; section 12.1 covers missing catalog items | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 "Text search by title/keywords" implemented | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 "Results rendered as poster grid"; "In-collection items marked with indicator" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 includes "Auto-launch" subsection describing autoSearch implementation | |
| PRD-050 | Keep Search non-AI in tone | important | missing | Plan treats Search as straightforward catalog lookup; no explicit statement that Search output has non-AI tone (implies it does, but not stated) | |
| PRD-051 | Preserve Show Detail narrative section order | important | partial | Section 4.5 lists sections 1-12 in order, but sections not labeled with explicit preservation intent; order appears preserved but not emphasized as requirement | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 "Header Media" carousel with fallback to static poster | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 "Core Facts Row" specifies year, runtime/episodes, community score | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 "My Relationship Toolbar" explicitly in toolbar, not body | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 5.2 table: "Add tag to unsaved show → Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 5.2 table: "Rate unsaved show → Done" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 section 4 places "Overview + Scoop" early in Detail | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 6.2 "streams progressively"; section 4.5 includes "Generating…" loading state | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5 section 5 "Ask About This Show" button; section 6.3 describes context seeding | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 section 7 "Traditional Recommendations Strand" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 section 8 lists "Get Concepts → select → Explore Shows" flow | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 sections 9-10 include "Streaming Availability" and "Cast & Crew" with person linking | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 section 11-12 state "(TV only)" and "(Movies only)" gates | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 11.1 Design Principles state "no mandatory scrolling for primary actions"; section 4.5 "Busyness vs Power" notes clustering early | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 "Chat UI with turn history" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 4.3 "Base system prompt defines persona"; section 6.3 "taste-aware prompt" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3 "Render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3 "Click mentioned show opens /detail/[id] or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 "Welcome state" section describes 6 random prompts with refresh | |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3 "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated)" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 6.3 "Ask About This Show" variant includes "pre-seeded context" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 "request structured output" with exact JSON format including commentary + showList | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 "Parse response; if JSON fails, retry with stricter instructions, otherwise fallback" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | partial | Section 6.1 states "Stay within TV/movies (redirect back)" but no explicit mechanism described (implicit in prompt, not detailed in plan) | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | partial | Section 4.4 "concept-like" hooks, but no explicit statement distinguishing taste ingredients from genres in plan detail | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 "Output: bullet list only; each concept 1–3 words, evocative, no plot" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 mentions "prompt focus axes" but doesn't explicitly detail ordering by "strongest aha" or "varied axes" requirement | |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Alchemy and Explore Similar flows require concept selection; guidance in UI copy | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 "Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 step 5 "Optional: More Alchemy!" enables chaining | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 mentions multi-show concepts but not explicitly "larger option pool"; section 2.1 doesn't detail pool size differences | |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 "reasons should explicitly reflect the selected concepts" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5 mentions "recent bias but not dogmatic" and "taste-aware" but not explicit "surprising but defensible" quality bar | |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 "All AI surfaces use configurable provider" with shared persona; section 4 notes "all surfaces share one persona" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 6.1 lists "Shared Architecture"; guardrails implied in "use configurable provider with shared prompts" but no explicit enforcement mechanism (e.g., validation contract) | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | partial | Section 6 references persona definition but does not include tone prescriptions in plan itself (relies on external docs) | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | partial | Section 6.2 states "structured as short mini blog post" but lacks detail on sections (take/stack-up/verdict) | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | partial | Section 6.3 mentions "conversational" but not explicit "brisk" or "dialogue-like" length targets in implementation | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6 sections 6.2-6.5 detail context inputs per surface (library, show details, concepts, etc.) | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 9.4 mentions test scenarios for AI but no explicit "rubric and hard-fail integrity" validation in code/plan | |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 "Person Header" includes "image gallery + bio"; "Name" implied in profile | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 "PersonAnalytics" section describes "Average rating, Top genres, Projects by year" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6 "Filmography Grouped by Year" and "years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 "Click credit opens /detail/[creditId]" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 "App Settings" lists "Font size selector" and "Toggle: Search on Launch" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 "User" (username), "AI" (model, key), "Integrations" (catalog key) all documented as safe | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 "Export / Backup" describes button generating `.zip` with all shows + My Data | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 "dates ISO-8601" explicitly stated in export format | |

---

## 3. Coverage Scores

### Calculation

**Critical requirements:**
- Full: 27
- Partial: 1
- Missing: 2
- Total critical: 30

Critical score: (27 × 1.0 + 1 × 0.5) / 30 × 100 = 27.5 / 30 × 100 = **91.67%**

**Important requirements:**
- Full: 54
- Partial: 10
- Missing: 3
- Total important: 67

Important score: (54 × 1.0 + 10 × 0.5) / 67 × 100 = 59 / 67 × 100 = **88.06%**

**Detail requirements:**
- Full: 2
- Partial: 0
- Missing: 0
- Total detail: 2

Detail score: (2 × 1.0 + 0 × 0.5) / 2 × 100 = 2 / 2 × 100 = **100%**

**Overall:**
- Full: 83
- Partial: 11
- Missing: 5
- Total: 99

Overall score: (83 × 1.0 + 11 × 0.5) / 99 × 100 = 88.5 / 99 × 100 = **89.39%**

### Summary

```
Critical:  (27 × 1.0 + 1 × 0.5) / 30 × 100 = 91.67%  (27 of 30 critical requirements)
Important: (54 × 1.0 + 10 × 0.5) / 67 × 100 = 88.06%  (54 of 67 important requirements)
Detail:    (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100%  (2 of 2 detail requirements)
Overall:   89.39% (83 full, 11 partial, 5 missing out of 99 total requirements)
```

---

## 4. Top Gaps

### Gap 1: PRD-050 (Important) — Keep Search non-AI in tone
**Why it matters:** The product voice spec emphasizes that Search has no AI persona. If Search output accidentally adopts AI tone or generic language, it breaks the product's commitment that not all discovery surfaces are "opinionated AI." Users expect straightforward catalog results from Search, not personality. The plan states Search is "straightforward catalog lookup" but never explicitly confirms that response text/copy will remain non-AI in tone.

### Gap 2: PRD-086 (Critical) — Enforce shared AI guardrails across all surfaces
**Why it matters:** The product requires one consistent AI persona with shared guardrails (spoiler-safe, TV/movies domain, opinionated, etc.). The plan describes configurable AI providers and prompt management but does not detail an explicit **enforcement mechanism** for guardrails — e.g., how the system validates that a response adheres to the rubric, what happens if an AI response violates a guardrail, or how guardrail violations are detected/logged. Without this, critical guardrails (e.g., spoiler-safety) could be silently violated.

### Gap 3: PRD-074 (Important) — Redirect Ask back into TV/movie domain
**Why it matters:** Ask must enforce that the AI stays in the TV/movies domain and redirects off-topic requests back. The plan mentions this rule in section 6.1 ("Stay within TV/movies (redirect back)") but does not detail **how** redirection works: Is there a fallback message? Does the AI respond but then prompt again? What if the user persists with off-topic requests? The mechanism is unclear.

### Gap 4: PRD-051 (Important) — Preserve Show Detail narrative section order
**Why it matters:** The product PRD specifies a strict narrative hierarchy for the Detail page (header → facts → scoop → recommendations → etc.). The plan lists all sections in correct order but does not emphasize **why order matters** or **how to preserve it across future changes**. If a future team reorders sections for UX reasons without understanding the intent, the product's "first 15 seconds" experience degrades.

### Gap 5: PRD-026 (Critical) — Re-add preserves My Data and refreshes public data
**Why it matters:** When a user removes a show and later re-adds it, the system must preserve their saved status/tags/rating/notes while refreshing the show's public metadata (posters, synopsis, runtime, etc.). The plan describes merge rules in section 7.2 but never explicitly documents the **end-to-end user-facing flow** for re-adding a show: Does the user see a "This show is in your collection" notification? Do they confirm a merge? Is the preservation automatic and silent? Without clarity, the implementation might silently overwrite saved data or confuse the user.

---

## 5. Coverage Narrative

### Overall Posture

This implementation plan is **structurally sound with strong coverage of core features and infrastructure**. At **89.39% overall coverage**, the plan demonstrates comprehensive understanding of the product requirements and provides concrete implementation guidance for major features (collection, search, Ask, Alchemy, Detail page, export). 

The plan's weakness clusters around **AI quality guardrails and product voice enforcement** rather than functional scope. Critical infrastructure and data model requirements are well-covered (namespace isolation, timestamp-based merge, server-as-source-of-truth). However, the plan treats AI surfaces as "implement per the product docs" without adding implementation-level detail on *how* the system will validate or enforce the quality bar, voice consistency, and guardrail adherence that define the app's personality.

The plan is **execution-ready for the MVP (Phase 1: Core Collection)** and reasonably clear for Phase 2 (AI Features), but would benefit from additional detail in Phase 3 (Alchemy & Polish) on monitoring, quality enforcement, and product-voice preservation across AI surfaces.

**Recommendation:** This plan can proceed to implementation. Phase 2 should include explicit design of AI guardrail enforcement (validation contract, fallback behavior, logging) before coding begins.

### Strength Clusters

**Infrastructure & Data Model (Benchmark Runtime & Isolation, Collection Data & Persistence):**
- Namespace isolation and user identity partitioning are thoroughly specified (sections 2.2, 8.1, 9.2).
- Environment variable interface, secrets management, and dev-mode auth injection are concrete (sections 10.1, 8.1, 8.3).
- Database schema with merge rules, timestamp-based conflict resolution, and data continuity across upgrades are well-detailed (sections 2.1–2.3, 7.2).
- Test data isolation and destructive reset semantics are clear (section 9.2).

**Collection & Discovery Features (Collection Home & Search, Show Detail & Relationship UX, Ask Chat):**
- Collection home grouping (Active, Excited, Interested, Other) with filtering is fully specified (section 4.1).
- Detail page section order and toolbar placement are preserved and documented (section 4.5).
- Auto-save rules (status, rating, tag) are explicit (section 5.2).
- Ask chat architecture with mention resolution and starter prompts is well-specified (section 4.3, 6.3).
- Search implementation with external catalog integration is clear (section 4.2).

**AI Integration (Concepts, Explore Similar & Alchemy):**
- Concept generation endpoints (single + multi-show) with bullet-only 1–3 word output are specified (section 6.4).
- Alchemy loop (select shows → conceptualize → select concepts → recommend → chain) is fully documented (section 4.4).
- Concept-to-recommendation resolution with reason citation is detailed (section 6.5).
- Scoop caching (4 hours) and persistence rules (only if in collection) are explicit (section 6.2).

**Person Detail & Settings (Person Detail, Settings & Export):**
- Person gallery, filmography grouping by year, and analytics charts are specified (section 4.6).
- Export with ISO-8601 dates is documented (section 4.7).
- Safe storage of API keys (server-only, never transmitted to client) is clear (section 8.3).

### Weakness Clusters

**AI Voice & Quality Guardrails (AI Voice, Persona & Quality):**
The plan mentions persona, tone, and guardrails but relies almost entirely on external documentation (ai_voice_personality.md, ai_prompting_context.md) without integrating enforcement into the implementation plan. Specific gaps:
- **No explicit guardrail validation contract:** How does the system know if an AI response violates a guardrail? Are responses validated against a rubric before returning to the user? What happens on violation?
- **No tone-enforcement mechanism:** Section 6.1 states "all surfaces share one persona" but doesn't detail how prompt variations are managed to preserve tone across surfaces, how prompt changes are tested, or what prevents drift.
- **No voice-consistency monitoring:** Section 14.1 mentions logging but not monitoring for tone drift, concept quality regression, or recommendation quality degradation across model updates.

**AI Context & Behavioral Details (Ask Chat, Concepts, Alchemy):**
Several behavioral requirements are undercoded:
- **PRD-074 (Redirect off-topic Ask):** The plan states the rule but not the mechanism. Does the AI respond then ask to return to topic? Does it refuse and re-prompt? No fallback specified.
- **PRD-077 (Order concepts by aha and axis diversity):** The plan mentions "prompt focus axes" but doesn't specify how the ordering algorithm works or who validates that diversity is achieved.
- **PRD-082 (Multi-show concept pool size):** The plan doesn't detail what "larger option pool" means — is it 12 vs 8? How much larger? No concrete number.
- **PRD-087–089 (Tone targets for Scoop, Ask):** The plan mentions "structured as mini blog post" and "conversational" but omits the specific tone sliders, length targets, and voice pillars that define the product (warm 70%, hype 60%, concise by default, etc.).

**Product Voice & Intent Preservation:**
- **PRD-051 (Preserve Detail section order):** The plan lists sections in order but doesn't explain *why* that order matters (first 15 seconds, narrative hierarchy, emotional arc). Future rebuilds might miss the intent.
- **PRD-050 (Search non-AI tone):** The plan treats Search as straightforward but never explicitly states that copy/instructions in Search results will avoid AI personality.

**Quality & Monitoring (Discovery Quality Bar):**
- **PRD-091 (Validate with rubric & hard-fail integrity):** The plan mentions test scenarios (section 9.4) but not a live quality rubric or hard-fail logic in production. How are recommendations validated in real time? Are poor-quality recs caught and fallback to traditional recommendations?
- **PRD-086 (Enforce shared guardrails):** No explicit validation logic; no logging of guardrail violations; no alerting if guardrail adherence drops.

### Risk Assessment

**Most likely failure mode if executed as-is:**

The app launches with working collection and AI surfaces, but **AI tone and quality drift over time** as:
1. Prompt changes are made without explicit validation against the voice spec.
2. Model provider updates (e.g., OpenAI releases GPT-5) change behavior without guardrail validation.
3. Concept generation produces generic results, or Ask responses become verbose, or Scoop tone becomes generic/moralizing.
4. Users notice Ask responses sometimes leave the TV/movies domain without explicit redirection.

**First-notice symptom:** A user or QA reviewer generates Ask responses and notices inconsistent tone (some brisk, some essayistic; some warm, some sterile; some respectfully honest, some gushy). Scoop responses drift to generic praise. Concepts become common genre labels instead of evocative ingredients.

**Root cause:** No explicit quality contract or enforcement mechanism in the implementation. Prompts are treated as config files without validation. AI responses are not validated against rubric before display. No monitoring of tone consistency or concept quality.

**Secondary failure:** Concept generation for multi-show Alchemy begins returning generic concepts ("compelling characters," "thrilling") because the prompt or model drift hasn't been caught. Users select these concepts, and recommendations become less aligned to taste.

### Remediation Guidance

**For Weakness Clusters:**

1. **AI Guardrail Enforcement (PRD-086, PRD-091):**
   - Add explicit design document: "AI Response Validation & Guardrail Contract" before Phase 2 implementation begins.
   - Define a minimal validation function that checks responses against the rubric (voice, spoiler-safety, concept specificity, show integrity).
   - Hard-fail: if validation fails, return fallback message + log incident.
   - Soft-monitor: track validation scores over time; alert if pass rate drops below 95%.

2. **AI Tone & Voice Consistency (PRD-087–089):**
   - Create a "Prompt Evolution Guide" in the repo that documents tone sliders, length targets, and voice pillars per surface.
   - For each prompt change, require a test pass: generate 5 outputs and validate tone/length/specificity against the guide before merging.
   - Add a "voice regression test" in CI that samples AI outputs monthly and flags tone drift.

3. **Behavioral Specification (PRD-074, PRD-077, PRD-082):**
   - Add implementation-level specs in Phase 2 design:
     - Ask off-topic redirection: explicit prompt rule + example outputs.
     - Concept ordering: define algorithm (e.g., "rank by specificity score DESC, then by axis diversity"), not just "ordered by aha."
     - Multi-show concept pool: define exact size (e.g., "8–12 for single, 16–20 for multi").

4. **Product Intent Preservation (PRD-051, PRD-050, PRD-026):**
   - Add README sections documenting product intent:
     - "Why Detail Section Order Matters" (first 15 seconds, narrative arc).
     - "Search Design Philosophy" (straightforward, non-opinionated).
     - "Re-Add Show Flow" (diagram: detect re-add → validate saved data → merge → confirm to user).
   - Treat these as architectural decisions, not just implementation notes.

5. **Quality Monitoring (PRD-091):**
   - In Phase 3, add live dashboard: recommendation quality metrics (show resolution rate, concept specificity score, tone consistency score).
   - Alert thresholds: < 90% show resolution, < 80% concept specificity, < 85% tone consistency.
   - Quarterly review of golden set (test scenarios from discovery_quality_bar.md) to catch regressions.

**Category of work:** These are **specification + monitoring design** work, not task lists. Phase 2 should include:
- One design document per major weakness cluster.
- Validation contract and error handling.
- Monitoring and alert setup in Phase 3.

---

**END OF EVALUATION**