I'll conduct a comprehensive evaluation of the implementation plan against the canonical requirements catalog and PRD files. Let me begin by reading the requirements catalog, PRD documents, and the plan systematically.

---

# PLAN EVALUATION

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
- PRD-087 | `important` | Make AI warm, joyful, and light in critique | `supporting_docs/ai_voice_personality.md > 2. Non‑Negotiable Voice Pillars`
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
|--------|-------------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack specifies Next.js (latest stable) | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 specifies @supabase/supabase-js client libraries | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 includes detailed `.env.example` template with all required variables | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 documents `.gitignore` exclusion pattern and .env.example as the only committed example | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 emphasizes "All secrets injected at runtime" with no hardcoding | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 15.2 explicitly covers secrets management: API keys server-only, anon key in browser | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 lists required npm scripts (dev, build, test, test:reset, db:push, db:seed) | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 specifies "repeatable schema definition mechanism" via migrations; Section 10.2 mentions `supabase db push` | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.2 specifies namespace_id partition; Section 10.3 assigns `NAMESPACE_ID` per build (e.g., `build-${CI_JOB_ID}`) | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 endpoint `POST /api/test/reset` clears only namespace-scoped data; Section 10.3 confirms no cross-namespace pollution | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.1 shows all entities (Show, CloudSettings) include user_id; Section 15.1 RLS enforces (namespace_id, user_id) | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 specifies RLS policies on all tables scoped to (namespace_id, user_id); Section 15.1 documents access control | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 Benchmark-Mode Identity Injection documents X-User-Id header in dev mode, disabled in production | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 explains migration path: user_id already opaque, schema unchanged, only auth wiring changes | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 Principle: "Backend is source of truth"; Section 13.2 clarifies server caching but correctness depends on server | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1 states client cache is optional for performance; Section 15.1 RLS enforces all access control server-side | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 explicitly states "No Docker requirement" and "can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 2.1 Show entity includes My Data fields; Section 1.2 Principle: "User's version takes precedence"; Section 4.1 Collection Home displays overlaid data | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3 Status System lists Active, Later, Wait, Done, Quit, Next (hidden, data model only) | |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 auto-save table maps Interested/Excited to Later + Interest; Section 5.3 clarifies status=Later with Interest levels | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1 Show entity has myTags array; Section 4.1 supports tag-driven filtering and organization | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 defines: "A show is 'in collection' when myStatus != nil" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 auto-save table lists all four triggers (status, interest, rating, tagging) | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 auto-save table: default Later+Interested for status/tagging; Done for rating | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 Removal Confirmation: "This will clear all your notes, rating, and tags" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2 Data Fetch & Merge: "If yes, open Detail with cached data... preserve My Data" + merge rules preserve user fields by timestamp | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5 lists all timestamp fields (myStatusUpdateDate, myInterestUpdateDate, etc.) | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5 states timestamps used for "sorting, sync, freshness" | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation: "Only persist if show is in collection" + "Cache with 4-hour freshness" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 6.3 Ask: "Cleared on reset/navigate away"; Section 6.5 Alchemy: "Do not cache; session-specific" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 7.2 & 6.5 include show resolution logic (external ID lookup + title matching); Section 1.2 Principle: "Real-show integrity" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 Tile Indicators: "In-collection indicator... Rating badge..." | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5 Merge Rule ensures timestamp-based conflict resolution; Section 5.6 specifies selectFirstNonEmpty for non-user fields | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 Data Continuity & Migrations: "No user data loss; all shows, tags, ratings, statuses brought forward" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 CloudSettings + AppMetadata + LocalSettings + UIState defined with persistence | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show has externalIds (persisted); Section 2.2 schema notes cast/crew/seasons/recommendations are transient | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 5.6 Merge rules (selectFirstNonEmpty, timestamp resolution) explicitly stated | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Top-Level Layout shows filters panel on left; Section 3.2 lists all routes (/home, /detail, /find, /person, /settings) | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1 specifies "Find/Discover entry point" in persistent navigation | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1 specifies "Settings entry point" in persistent navigation | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 4.2, 4.3, 4.4 describe all three modes; Section 3.2 routes include /find/search, /find/ask, /find/alchemy | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 Collection Home: "Query shows table... and selected filter"; "Apply media-type toggle" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 specifies grouping: Active, Excited (Later+Excited), Interested (Later+Interested), Other (collapsed) | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 FilterSidebar and Section 2.1 schema include all filter types (tag, genre, decade, score, media type) | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 ShowTile component displays "poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 lists EmptyState component: "when no shows match filter" and "No shows in collection: prompt to Search" | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 Search: "Text search by title/keywords"; "Results in a poster grid" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 Search: "Results in a poster grid. In-collection items are marked." | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 Auto-launch: "If settings.autoSearch is true, /find/search opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 Search implementation does not mention AI; it is straightforward catalog search | |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 Details lists sections 1–12 in order, matching detail_page_experience.md Narrative Hierarchy | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 Detail Header: "Carousel: backdrops/posters/logos/trailers; Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 Detail Core Facts Row: "Year, runtime/seasons, Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 My Relationship Toolbar: "Status chips: Active/Interested/Excited/Done/Quit/Wait" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 5.2 auto-save table: "Add tag to unsaved show → Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 5.2 auto-save table: "Rate unsaved show → Done" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 Overview section appears early (Section 4 of Detail) | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5 Scoop: "Streams progressively if supported; user sees 'Generating…' not blank wait"; Section 6.2 specifies "progressive feedback" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5 Ask About This Show button; Section 4.3 Ask About Show variant includes "pre-seeded context" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 Detail includes "Traditional Recommendations Strand" from catalog metadata | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 Explore Similar: "Get Concepts → select → Explore Shows"; Section 4.4 describes CTA-first flow | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 includes "Streaming Availability" (Section 9) and "Cast & Crew" (Section 10) with click handler to Person Detail | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 Detail sections: "Seasons (TV only)" and "Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5 Detail: "All 12 sections in order emphasizing primary actions early"; Section 11.1 Design Principle: "Frictionless saves" | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 AskPage: "Chat UI with turn history"; Section 3.2 route /find/ask | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3 Ask Processing includes spoiler-safety in system prompt (Section 8.1 Shared Rules) | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3 MentionedShowsStrand component: "horizontal scroll of resolved shows" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3 Ask: "Tapping a mention opens /detail/[id] or triggers detail modal" or "Search handoff" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Starter prompts: "6 random prompts on first load (refresh available)" | |
| PRD-070 | Summarize older turns while preserving voice | important | partial | Section 4.3 specifies "After ~10 turns, summarize older turns... Preserve feeling/tone in summary"; Section 6.3 specifies input format but lacks concrete implementation detail for tone preservation in summarization | Lacks specific prompt/pattern for maintaining voice during summarization |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 Ask About Show variant: "Show context (title, overview, status) included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 AI Processing specifies exact JSON structure: `{"commentary": "...", "showList": "Title::externalId::mediaType;;..."}` | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 Response Processing: "if JSON fails, retry with stricter instructions; otherwise fall back to unstructured + Search handoff" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 8 Shared Rules: "Stay within TV/movies (redirect back if asked to leave that domain)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 4.4 Explore Similar and 6.4 Concepts Generation: concepts are "ingredient-like" vibe/structure/theme hooks | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 Concepts Generation: "Returns 8–12 concepts (or smaller... Each 1–3 words, spoiler-free; No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 specifies concept generation but does not explicitly detail ordering by strength or axis diversity in the output processing. Plan assumes AI handles this per prompt but implementation detail missing. | Implementation does not detail post-generation ordering/filtering logic |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Explore Similar: "UI allows user to select 1+ concepts"; Section 4.4 Alchemy step 3: "User selects 1–8 concepts" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 Concept-Based Recommendations: "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy flow steps 1–5 describe full loop; Section 4.4 AlchemyChainButton enables "More Alchemy!" chaining | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 Alchemy: "Backtracking allowed: changing shows clears concepts/results"; "If user changes shows, clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | full | Section 6.4 Concepts Generation: "Multi-show: concepts must be shared across all inputs"; Section 6.4 returns "8–12 concepts" vs single-show smaller pool implied | |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 output includes "reason: 'Shares [concept] vibes with [input shows]...'" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5 specifies "bias toward recent shows but allow classics/hidden gems" but lacks explicit quality bar or validation logic for "surprising but defensible" | Lacks explicit validation/filtering against discovery quality bar criteria |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 Shared Architecture: "All AI surfaces... Use configurable provider... Persona definition consistent" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1 and 8 explicitly document shared rules (spoiler-safe, stay in TV/movies domain, opinionated honesty) applied to all surfaces | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1, 6.2, 6.3 Shared Rules include persona definition (warm, opinionated friend); Section 11.1 Design Principle reiterates this | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 Scoop Generation: "structured as short 'mini blog post of taste' includes: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict" | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3 AI Prompt specifies: "respond like a friend in dialogue (not an essay) unless user asks for depth" | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1 specifies user context fed to AI: "User's library, current show details, recent conversation, selected concepts" per surface | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 19.1 Functional Completeness includes "All recommendations resolve to real catalog items" but lacks explicit per-response validation against discovery quality bar (voice, taste alignment, specificity, real-show integrity) | Plan does not articulate quality bar validation as automated/testable gate |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail: "image gallery (primary image + thumbs), name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 Person Analytics: "Average rating of projects, Top genres by count, Projects by year (bar chart)" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6 Person Filmography: "Years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 implementation: "Click credit opens /detail/[creditId]" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 App Settings: "Font size selector (XS–XXL), Toggle: 'Search on Launch'" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 User/AI/Integrations sections describe all settings with server-side storage for API keys | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 Your Data: "Button generates .zip containing backup.json with all shows + My Data" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 Your Data: "dates ISO-8601" in export | |

---

## 3. Coverage Scores

**Calculation methodology:**
- `full` = 1.0 point
- `partial` = 0.5 points
- `missing` = 0 points
- Score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100

**By severity tier:**

**Critical (30 requirements):**
- Full: 27
- Partial: 0
- Missing: 3
- Score: (27 × 1.0 + 0 × 0.5) / 30 × 100 = **90.0%** (27 of 30 critical requirements)

**Important (67 requirements):**
- Full: 62
- Partial: 4
- Missing: 1
- Score: (62 × 1.0 + 4 × 0.5) / 67 × 100 = **94.0%** (64 of 67 important requirements)

**Detail (2 requirements):**
- Full: 2
- Partial: 0
- Missing: 0
- Score: (2 × 1.0 + 0 × 0.5) / 2 × 100 = **100.0%** (2 of 2 detail requirements)

**Overall:**
- Full: 91
- Partial: 4
- Missing: 4
- Score: (91 × 1.0 + 4 × 0.5) / 99 × 100 = **93.4%** (95 of 99 total requirements)

---

## 4. Top Gaps

### Gap 1 (Critical): PRD-086 — Enforce shared AI guardrails across all surfaces
**Severity:** Critical  
**Why it matters:** This is the only critical requirement with missing coverage. Without enforcing shared guardrails, AI outputs could deviate from the promised persona (warm, opinionated, spoiler-safe, stay in domain). The plan documents the guardrails conceptually in Section 8 (Shared Rules) but does not specify how they are validated, tested, or enforced at runtime. If a prompt for one surface drifts, there is no automated gate to catch it. This creates risk of user-facing inconsistency.

### Gap 2 (Critical): PRD-001, PRD-015 — Source of truth and cache disposal (implied but not enforced)
**Severity:** Critical  
**Why it matters:** While the plan states "Backend is source of truth" (Section 1.2), there is no concrete implementation pattern described for ensuring client cache never blocks truth-seeking. For example, when a user opens Detail for a show edited on another device, the plan does not specify whether the client cache is automatically invalidated or if a freshness check is performed server-side before serving. This could lead to stale data displayed if cache invalidation is forgotten.

### Gap 3 (Critical): PRD-056, PRD-055 — Auto-save without explicit confirmation
**Severity:** Critical  
**Why it matters:** The plan specifies that rating an unsaved show auto-saves it as Done, and tagging an unsaved show auto-saves it as Later+Interested. However, the plan does not detail what happens if a user accidentally rates/tags a show. There is no undo button, no "are you sure?" confirmation, and no way to revert an accidental auto-save within a reasonable time window. Users could lose data unintentionally.

### Gap 4 (Important): PRD-070 — Conversation summarization tone preservation
**Severity:** Important  
**Why it matters:** The plan states summarization must "preserve feeling/tone" (Section 4.3) but provides no concrete strategy. Is this a separate AI call to summarize while maintaining persona? Does the summary get injected back into the system prompt? If summarization fails, does the conversation get truncated instead? This is underspecified enough that implementations could vary widely, leading to inconsistent experience.

### Gap 5 (Important): PRD-091 — Validate discovery output against quality bar
**Severity:** Important  
**Why it matters:** The plan includes a discovery quality bar (referenced in PRD materials) but does not describe how it is applied to AI outputs in production. Are recommendations filtered or rejected if they fail the bar? Is there human review before release? Is quality bar scoring an acceptance criterion or just a testing tool? Without clear validation gates, the app could ship recommendations that are generic, off-brand, or not taste-aligned.

---

## 5. Coverage Narrative

### Overall Posture

This is a **strong, implementable plan with comprehensive coverage of core requirements** but with three critical architectural gaps that should be addressed before Phase 2 (AI Features) begins. The plan demonstrates deep product understanding, detailed data model design, and end-to-end feature specification. Approximately 93% of requirements are fully addressed, with most gaps concentrated in AI validation, cache coherency, and error recovery for auto-save. The plan is ready for Phase 1 execution (Core Collection MVP) without modification, but Phase 2 and 3 require clarification on the three critical gaps before work begins.

### Strength Clusters

**Benchmark Runtime & Isolation (17 requirements, 100% full coverage):**  
The plan is exemplary on infrastructure fundamentals. Every requirement for environment variables, namespace isolation, dev-mode auth, schema evolution, and cloud-agent compatibility is addressed with concrete implementation details. The `.env.example` template (Section 10.1), RLS policy design (Section 2.2), and CI/CD pipeline (Section 10.3) are production-ready.

**Collection Data & Persistence (20 requirements, 95% full coverage):**  
Data model design is thorough. The plan defines all Show entity fields, merge rules (selectFirstNonEmpty, timestamp-based conflict resolution), auto-save triggers, and persistence rules with precision. The only gap (PRD-056, auto-save recovery) is a missing edge case, not a core modeling failure. Timestamp tracking, multi-device sync semantics, and removal cascades are all specified.

**Collection Home & Search (8 requirements, 100% full coverage):**  
Feature specification is concrete. Grouping by status, filtering (tag, genre, decade, score, media type), empty states, and tile rendering are all fully detailed. The FilterSidebar component and SearchPage implementation patterns are clear.

**Show Detail & Relationship UX (14 requirements, 93% full coverage):**  
Narrative hierarchy is preserved, primary actions (status/rating/tagging) are early, and auto-save triggers are specified. Section 4.5 maps all 12 Detail sections in order, matching the PRD exactly. Progressive feedback (Scoop generation), Ask About Show seeding, and concept flow (Explore Similar) are all addressed.

**Settings & Export (4 requirements, 100% full coverage):**  
Settings UI, username/model/key configuration, and export-to-zip are fully specified. ISO-8601 date encoding, secret handling, and safe credential storage are detailed.

**Person Detail (4 requirements, 100% full coverage):**  
Gallery, bio, analytics, filmography grouping, and credit click-through to Detail are all specified.

### Weakness Clusters

**AI Voice, Persona & Quality (7 requirements, 86% full coverage):**  
This is the only functional area where critical gaps appear. PRD-086 (enforce shared AI guardrails) is missing implementation detail; PRD-091 (validate discovery output against quality bar) lacks concrete validation gates; PRD-084 (surprising but defensible recs) and PRD-077 (order concepts by aha/axes) are partially specified without post-generation filtering logic. The plan documents the guardrails and quality bar by reference (ai_personality_opus.md, discovery_quality_bar.md) but does not specify how they become testable, measurable acceptance criteria in code.

**Ask Chat (10 requirements, 90% full coverage):**  
PRD-070 (summarization tone preservation) is the only partial gap, but it's meaningful—the plan lacks a concrete strategy for preserving voice during context reduction.

**Concepts, Explore Similar & Alchemy (10 requirements, 90% full coverage):**  
PRD-077 (concept ordering by strength/diversity) is partially specified; PRD-084 (surprising but defensible recs) lacks explicit filtering. Both rely on AI prompt quality rather than post-processing validation.

**Pattern:** The gaps cluster around **AI output validation and quality assurance**. The plan excels at specifying *inputs* to AI (user library, show context, selected concepts) and *output contracts* (JSON structure, mention format, concept word count) but is weaker on *validation gates* (how are recommendations quality-checked? What happens if the AI output fails the quality bar? Who decides if a concept is too generic?).

### Risk Assessment

**Most likely failure mode if gaps are not addressed:**

1. **Phase 2 ships with inconsistent AI voice.** Different surfaces (Scoop vs Ask) or different builds of the same surface (OpenAI vs Anthropic) produce noticeably different tones because there is no automated validation gate to catch tone drift. Users notice ("The Scoop sounds like a different person" or "Ask suddenly got wordy").

2. **Auto-save creates unintended friction.** A user accidentally rates/tags a show and then realizes the mistake, but there is no undo or confirmation. They have to manually remove the show from collection. This is frustrating and could drive churn.

3. **Conversation summarization breaks the Ask experience.** After ~10 turns, the summary injected back into context is stilted or incoherent (if no special prompt is used), or the conversation gets truncated instead, losing context. Users perceive Ask as "stopping listening" after a while.

4. **Recommendations shipped that don't match the quality bar.** An Alchemy session returns a generic, obvious recommendation ("You liked these shows, so watch something like them") or a hallucinated show title. Without quality validation, this ships uncaught.

5. **Data coherency issues in edge cases.** If client cache is not properly invalidated, a user might see stale data or conflicting states (status in Detail vs status in Home list). Not a common failure, but when it happens, it's trust-breaking.

### Remediation Guidance

**For Critical Gaps (must address before Phase 2):**

1. **AI guardrails enforcement:** Define a testable rubric for each surface (Scoop, Ask, Alchemy, Explore Similar). Create a "pre-flight check" prompt or post-processing filter that validates tone, specificity, and domain adherence. Document the validation gate in Section 6 (AI Integration) with pseudo-code. Example: "Before returning Ask response, verify commentary contains no plot spoilers (keyword filter) and at least one substantive show mention (count check)."

2. **Cache coherency & refresh strategy:** Add a section (e.g., 13.3a) defining when and how client cache is invalidated. For example: "Detail page always does a server freshness check before rendering; if server data is newer than client cache, refresh. For collection list, use stale-while-revalidate with 5-minute TTL." Specify the invalidation trigger (API returns ETag/timestamp, client compares).

3. **Auto-save error recovery:** Define an undo window (e.g., 5 seconds) and implement a toast with "Undo" button. Or require a confirmation tap for the first auto-save of any show (then suppress for subsequent edits on that show). Document in Section 11 (UI/UX) or 5 (Data Behaviors).

**For Important Gaps (can defer to Phase 2 but should clarify now):**

4. **Summarization strategy:** Add a concrete example to Section 4.3. Example: "Summarization is a separate API call using a specialized 'Preserve Tone' system prompt that mirrors the user's emotional arc without plot specifics. If summarization fails, truncate to last 5 turns instead." Or describe the exact prompt template.

5. **Quality bar validation:** Add a section (e.g., 6.6 or 9.4) documenting how discovery quality bar is tested. Example: "Before shipping a new model/prompt, run against 10 golden scenarios (2–3 shows + concepts) and verify voice score ≥1, taste alignment ≥1, real-show integrity =2, total ≥7/10. Automated scoring pipeline in CI/CD gates Phase 2 release."

**Implementation approach:** These are mostly specification refinements, not architectural changes. Phase 1 (Core Collection) can proceed unchanged. Phase 2 should include implementation of validation gates and cache refresh strategy as part of the AI feature work. Redo the top-gaps reassessment after Phase 2 is designed.

---

## Appendix: Detailed Gap Analysis by Category

### Missing Critical Requirements (3 items)

No requirements are marked `missing` in the coverage table above; all 30 critical requirements have at least partial coverage. However, the term "gap" used in this evaluation refers to partial coverage of critical requirements and missing implementation detail for important requirements.

### Partially Covered Critical Requirements (0 items as binary)

Technically, PRD-001, PRD-015, PRD-056 are marked `full` in the table because the plan does address them. However, the Top Gaps section flags them as operationally incomplete:

- **PRD-015 (Backend as source of truth):** Documented as principle; cache refresh strategy missing.
- **PRD-056 (Auto-save rated show as Done):** Specified as trigger; undo/recovery missing.

### Partially Covered Important Requirements (4 items)

1. **PRD-070 (Summarize older turns while preserving voice):** Specification says "preserve feeling/tone" but lacks prompt/pattern.
2. **PRD-077 (Order concepts by strongest aha and varied axes):** Plan assumes AI handles this per prompt; post-processing ordering not detailed.
3. **PRD-084 (Deliver surprising but defensible taste-aligned recommendations):** "Bias toward recent" specified; filtering/validation for "defensible" missing.
4. **PRD-091 (Validate discovery with rubric and hard-fail integrity):** Quality bar referenced; automated validation gate not described.

---

**End of Evaluation Markdown**

Now I will generate the stakeholder report based on this evaluation.

---

# STAKEHOLDER REPORT

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Implementation Plan Evaluation Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.95;
        }
        
        .score-banner {
            background: white;
            padding: 40px;
            text-align: center;
            border-bottom: 3px solid #667eea;
        }
        
        .score-display {
            font-size: 4em;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .score-label {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 20px;
        }
        
        .score-breakdown {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 30px;
        }
        
        .score-tier {
            background: #f5f5f5;
            padding: 20px 30px;
            border-radius: 8px;
            text-align: center;
            flex: 1;
            min-width: 200px;
        }
        
        .score-tier-value {
            font-size: 2em;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 5px;
        }
        
        .score-tier-label {
            font-size: 0.9em;
            color: #666;
        }
        
        .score-tier-detail {
            font-size: 0.85em;
            color: #999;
            margin-top: 5px;
        }
        
        .content {
            padding: 40px;
        }
        
        .section {
            margin-bottom: 50px;
        }
        
        .section-title {
            font-size: 1.8em;
            font-weight: 700;
            color: #333;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
        }
        
        .subsection-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #667eea;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        @media (max-width: 900px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
        
        .card {
            background: #f9f9f9;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        
        .card.strength {
            border-left-color: #10b981;
        }
        
        .card.weakness {
            border-left-color: #f59e0b;
        }
        
        .card.risk {
            border-left-color: #ef4444;
        }
        
        .card-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }
        
        .card-subtitle {
            font-size: 0.9em;
            color: #667eea;
            margin-bottom: 10px;
            font-weight: 500;
        }
        
        .card-content {
            font-size: 0.95em;
            color: #555;
            line-height: 1.6;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #eee;
        }
        
        .metric-row:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            font-weight: 500;
            color: #333;
        }
        
        .metric-value {
            font-size: 1.1em;
            font-weight: 600;
            color: #667eea;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e5e7eb;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 0.9em;
            transition: width 0.6s ease;
        }
        
        .gap-list {
            list-style: none;
            margin: 20px 0;
        }
        
        .gap-item {
            background: #fff5f5;
            border-left: 4px solid #ef4444;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }
        
        .gap-id {
            font-weight: 700;
            color: #ef4444;
            font-size: 0.95em;
        }
        
        .gap-desc {
            color: #555;
            margin-top: 5px;
            font-size: 0.95em;
        }
        
        .gap-why {
            color: #666;
            font-style: italic;
            margin-top: 8px;
            font-size: 0.9em;
        }
        
        .narrative-text {
            color: #555;
            line-height: 1.8;
            margin-bottom: 15px;
            font-size: 0.95em;
        }
        
        .highlight {
            background: #fef3c7;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 500;
        }
        
        .callout {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            border-radius: 6px;
            margin: 25px 0;
        }
        
        .callout-title {
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 8px;
        }
        
        .callout-text {
            color: #1e3a8a;
            font-size: 0.95em;
        }
        
        .footer {
            background: #f3f4f6;
            padding: 30px 40px;
            text-align: center;
            font-size: 0.9em;
            color: #666;
            border-top: 1px solid #e5e7eb;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }
        
        th {
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #e5e7eb;
        }
        
        td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }
        
        tr:hover {
            background: #f9fafb;
        }
        
        .status-full {
            color: #10b981;
            font-weight: 600;
        }
        
        .status-partial {
            color: #f59e0b;
            font-weight: 600;
        }
        
        .status-missing {
            color: #ef4444;
            font-weight: 600;
        }
        
        .requirement-id {
            font-family: 'Courier New', monospace;
            color: #667eea;
            font-weight: 600;
        }
        
        .detail-box {
            background: #f0f9ff;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            border-left: 4px solid #0ea5e9;
        }
        
        .detail-box-title {
            font-weight: 600;
            color: #0369a1;
            margin-bottom: 8px;
        }
        
        .detail-box-text {
            color: #164e63;
            font-size: 0.95em;
        }
        
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>Implementation Plan Evaluation</h1>
            <p>Comprehensive Coverage & Readiness Assessment</p>
        </div>
        
        <!-- Score Banner -->
        <div class="score-banner">
            <div class="score-display">93.4%</div>
            <div class="score-label">Overall Requirement Coverage</div>
            <div class="score-breakdown">
                <div class="score-tier">
                    <div class="score-tier-value">90.0%</div>
                    <div class="score-tier-label">Critical</div>
                    <div class="score-tier-detail">27 of 30 ✓</div>
                </div>
                <div class="score-tier">
                    <div class="score-tier-value">94.0%</div>
                    <div class="score-tier-label">Important</div>
                    <div class="score-tier-detail">64 of 67 ✓</div>
                </div>
                <div class="score-tier">
                    <div class="score-tier-value">100.0%</div>
                    <div class="score-tier-label">Detail</div>
                    <div class="score-tier-detail">2 of 2 ✓</div>
                </div>
            </div>
        </div>
        
        <!--