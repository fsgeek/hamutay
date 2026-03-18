I will follow the evaluation instructions precisely. Let me begin by working through each phase in order.

## Phase 1: Read the Requirements Catalog

I have read `evaluator/requirements_catalog_v1.md` in full. It contains 99 requirements across 10 functional areas with severity tiers (critical, important, detail).

## Phase 2: Read the PRD Files

I have read all PRD files in order:
1. `docs/prd/product_prd.md` — product vision, features, user journeys
2. `docs/prd/infra_rider_prd.md` — infrastructure, identity, isolation, deployment
3. All supporting docs in `docs/prd/supporting_docs/` — AI voice, prompting, concepts, detail UX, quality bar, schema

## Phase 3: Read the Plan

I have read `results/PLAN.md` in full. It is a 20-section implementation plan covering architecture, data model, navigation, features, data behaviors, AI integration, catalog integration, auth, testing, infrastructure, UI/UX, error handling, performance, monitoring, security, documentation, migration phases, and acceptance criteria.

## Phase 4: Write the Full Evaluation

I will now produce the complete markdown evaluation to `results/PLAN_EVAL.md`.

---

# PLAN_EVAL.md

# Implementation Plan Evaluation

**Plan Source:** `results/PLAN.md`  
**Denominator:** 99 requirements (30 critical, 67 important, 2 detail) across 10 functional areas  
**Evaluation Date:** Current benchmark  

---

## 1. Requirements Extraction

### Pass 1: Identify Functional Areas

Using the exact functional area taxonomy from the canonical catalog:

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
|--------|-------------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable)" specified as frontend/runtime |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "@supabase/supabase-js (anon/public key for browser)" specified |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: Detailed `.env.example` content provided with all keys |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: `.gitignore` excludes `.env*` (except `.env.example`) mentioned |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "build MUST run by filling in environment variables, without editing source code" |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.1, 10.1: Secrets strategy for API keys detailed; server-only encryption noted |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 14: npm scripts listed (dev, test, test:reset, db:push, db:seed) |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2: Database schema + migrations + seed data mentioned; Section 14 confirms scripts |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.1, 4.1: "Each build MUST operate inside a single stable namespace identifier" |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 2.2, 10.3: RLS policies + namespace isolation + `/api/test/reset` scoped to namespace |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.1: All entities include user_id; Section 2.2: RLS enforces (namespace_id, user_id) |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: All tables partitioned by (namespace_id, user_id) with indexes + RLS |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: X-User-Id header injection in dev mode; disabled in production |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "Switch from header injection to real OAuth… Schema unchanged" |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth; clients cache for performance" |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 1.2: "Clearing client storage must not lose user data" |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement; can run against hosted Supabase directly" |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4: Show Detail page displays "user overlay" (status/tags/rating/scoop); Home shows badges |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3: Status system lists all statuses; "Next" data model only, not first-class UI |  |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2: "Select Interested/Excited → Later + Interested/Excited" |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.6: Tags in Show Detail; Settings filters by tags; free-form described |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is in collection when myStatus != nil" |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2: Table lists all save triggers (status, interest, rating, tag) |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: Rating-save defaults to Done; tag-save defaults to Later + Interested |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Removing status clears all My Data"; confirmation modal confirmed |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2: "If user encounters show already saved: Preserve… Refresh public metadata" |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1: All my* fields include UpdateDate field; Section 5.5 documents tracking |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5: "Merge rule: keep value with newer timestamp" + sorting support noted |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2: "Cache with 4-hour freshness… Only persist if show is in collection" |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6: "Ask chat history… Session only… Cleared on reset" |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5, 7.2: "Resolve each mention/rec to external catalog by external ID + title match" |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator visible when myStatus != nil; Rating badge when myScore != nil" |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3: "Duplicate shows detected by id and merged transparently" |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version reads old schema and transparently transforms on first load" |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1: CloudSettings, LocalSettings, UIState entities defined |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1: providerData persisted; cast/crew/seasons listed as "transient properties" |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 2.3, 7.2: "Non-user fields: selectFirstNonEmpty… User fields: resolve by timestamp" |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: "Filters panel on left (collapsible on mobile); Find/Discover entry point; Settings entry" |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: Find/Discover listed as persistent entry point |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: Settings listed as persistent entry point |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2: /find routes include search, ask, alchemy with mode switcher |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query shows filtered by (namespace_id, user_id) and selected filter" |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: 1. Active 2. Excited 3. Interested 4. Other (collapsed)" |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 3.1, 4.1: All/tag/genre/decade/score/media filters listed |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "EmptyState — when no shows match filter" component listed |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text input sends query to /api/catalog/search" |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid… In-collection items marked" |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If settings.autoSearch is true, /find/search opens on app startup" |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: No mention of AI integration for Search; straightforward catalog search |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: "Sections (in order)" lists 12 sections matching PRD narrative order |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Carousel: backdrops/posters/logos/trailers… Fall back to static poster" |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime… Community score bar" |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "My Relationship Toolbar: Status chips, Rating slider, My Tags" |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5: "All operations… tag picker modal… auto-saves as Later + Interested" |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5: "Setting rating on unsaved show: auto-save as Done" |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: "Overview + Scoop: Overview text (factual)" appears after core facts |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively if supported… user sees Generating… not blank wait" |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5: "Ask About This Show: Button opens Ask with show context" |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: Similar/recommended shows from metadata" |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "Explore Similar: Get Concepts → select → Explore Shows" |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: "Streaming Availability… Cast & Crew: Click opens /person/[id]" |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only)… Budget vs Revenue (Movies only)" |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5: "primary actions clustered early (status, rating, scoop, concepts)… long-tail info down-page" |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history; User messages sent to /api/chat" |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3: "System prompt: persona definition (gossipy friend, opinionated, spoiler-safe)" |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Render mentioned shows as horizontal strand (selectable)" |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens /detail/[id] or triggers detail modal" |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3: "Display 6 random starter prompts on first load (refresh available)" |  |
| PRD-070 | Summarize older turns while preserving voice | important | partial | Section 4.3: "Summarize older turns after ~10 messages" mentioned; no detail on voice preservation in summarization logic or prompts |  Gap: Voice-preservation rules for summarization not specified; AI prompt for summarization not detailed |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3: "Button on Detail page opens Ask with pre-seeded context" |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3: "Request structured output: {commentary, showList: Title::externalId::mediaType;;…}" |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3: "if JSON fails, retry with stricter instructions, otherwise fallback to unstructured + Search" |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1: "All AI surfaces must… Stay within TV/movies (redirect back if asked)" |  |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4: "extract concept ingredients (1–3 words each, evocative, no plot)" |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4: "Output: bullet list only… 1–3 words, spoiler-free… No generic placeholders" |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4: "return 8–12 concepts" but no explicit instruction on ordering by aha or axis diversity. Plan assumes prompt will handle; no explicit rubric or prompt detail provided. | Gap: Concept ordering heuristic not specified in plan; assumes AI prompt will implement |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4: "User selects 1–8 concepts… UI allows toggling… Max 8 enforced by UI" |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Explore Similar: 5 recs per round" |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "Optional: More Alchemy!… User can select recs as new inputs… Chain multiple rounds" |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | full | Section 6.4: "Multi-show: concepts must be shared across all inputs" |  |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "reasons should explicitly reflect selected concepts… Reasons should name which concepts align" |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5: "Output: Array of recommendations… bias toward recent shows but allow classics/hidden gems" mentioned; no explicit rubric for validating "surprising but defensible" before returning. Plan defers to AI quality; no acceptance criteria to measure this. | Gap: Quality acceptance criteria for surprising/defensible trade-off not specified; relies entirely on prompt quality |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1: "All AI surfaces: Use configurable provider… Shared Architecture" |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 6.1 mentions "All AI surfaces must… Stay within TV/movies…" but plan does not detail enforcement mechanism (e.g., system prompt guardrails, output validation, or fallback rules per surface). | Gap: Guardrail enforcement mechanism not specified; assumes prompt inclusion but no validation layer described |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.2, 6.3: Persona described as "gossipy friend, opinionated, spoiler-safe"; referenced throughout |  |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "AI Prompt: generate spoiler-safe mini blog post of taste… Sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict" |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3: "System prompt: persona (gossipy friend…)" and chat UI inherently encourages brevity |  |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1-6.5: Each surface details context inputs (library, show details, concepts, conversation history) |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 19.3: "Acceptance criteria: All recommendations resolve to real catalog items" but no in-plan validation rubric described. Plan notes "hard-fail integrity" but no explicit validation logic or scoring rubric provided. | Gap: Discovery validation rubric and hard-fail mechanism not detailed in implementation plan |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Image gallery (primary image + thumbs)… Name, bio" |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics: Average rating… Top genres… Projects by year (bar chart)" |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable" |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens /detail/[creditId]" |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "App Settings: Font size selector… Toggle: Search on Launch" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "User: username… AI: model + API key (stored server-side; display masked)" |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export / Backup: Button generates .zip containing backup.json… all shows + My Data" |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "backup.json with… (dates ISO-8601)" |  |

---

## 3. Coverage Scores

### Overall Score Calculation

```
full_count = 92
partial_count = 7
missing_count = 0
total_count = 99

score = (92 × 1.0 + 7 × 0.5) / 99 × 100
score = (92 + 3.5) / 99 × 100
score = 95.5 / 99 × 100
score = 96.5%
```

### Score by Severity Tier

**Critical Requirements:**
```
critical_full = 27
critical_partial = 2 (PRD-070, PRD-086)
critical_missing = 0
critical_total = 30

critical_score = (27 × 1.0 + 2 × 0.5) / 30 × 100
critical_score = (27 + 1) / 30 × 100
critical_score = 28 / 30 × 100
critical_score = 93.3% (28 of 30 critical requirements)
```

**Important Requirements:**
```
important_full = 64
important_partial = 3 (PRD-070, PRD-077, PRD-084, PRD-086, PRD-091)
important_missing = 0
important_total = 67

important_score = (64 × 1.0 + 3 × 0.5) / 67 × 100
important_score = (64 + 1.5) / 67 × 100
important_score = 65.5 / 67 × 100
important_score = 97.8% (65.5 of 67 important requirements)
```

**Detail Requirements:**
```
detail_full = 2
detail_partial = 0
detail_missing = 0
detail_total = 2

detail_score = (2 × 1.0 + 0 × 0.5) / 2 × 100
detail_score = 2 / 2 × 100
detail_score = 100% (2 of 2 detail requirements)
```

### Final Scores

```
Critical:  93.3%  (28 of 30 critical requirements)
Important: 97.8%  (65.5 of 67 important requirements)
Detail:    100%   (2 of 2 detail requirements)
Overall:   96.5%  (95.5 of 99 total requirements)
```

---

## 4. Top Gaps

Ranked by severity tier first (critical before important), then by impact:

### Gap 1: PRD-086 (Critical) — Enforce Shared AI Guardrails Across All Surfaces

**Requirement:** AI guardrails must be enforced consistently (TV/movie domain, spoiler safety, honesty rules) across Ask, Scoop, Concepts, and Recommendations.

**Why It Matters:** If guardrails are not explicitly enforced via validation or fallback logic, the AI may drift across surfaces (one surface generates off-domain content, another spoils, another generates generic content). This degrades the core "consistent persona" promise and breaks trust. Users rely on spoiler-safety and domain-grounding across all AI surfaces.

**What's Missing:** The plan mentions guardrails in shared rules but does not specify how they are validated or enforced. Are there prompt-only guardrails, or is there output validation before display? What happens if the AI violates a guardrail (e.g., suggests a non-TV show)? The plan defers to prompts without describing a validation layer or fallback mechanism.

---

### Gap 2: PRD-070 (Critical/Important) — Summarize Older Turns While Preserving Voice

**Requirement:** When Ask conversations grow long, older turns must be summarized while maintaining the AI persona's voice and tone.

**Why It Matters:** If summarization is generic or drops the persona, users lose the sense of continuity; the conversation feels like it shifted from a friend to a system. Summarization is critical to control token depth without breaking the experience.

**What's Missing:** The plan says "Summarize older turns after ~10 messages" but does not specify (a) the AI prompt for summarization, (b) what "while preserving voice" means operationally, or (c) how to measure success. It's unclear if the same AI model generates summaries or if there's a simpler fallback summarizer.

---

### Gap 3: PRD-091 (Important) — Validate Discovery with Rubric and Hard-Fail Integrity

**Requirement:** AI recommendations must be validated against a quality rubric; discovery must hard-fail if integrity is compromised (e.g., hallucinated shows, off-domain outputs, non-defensible recs).

**Why It Matters:** Without validation, the app can recommend non-existent shows or off-brand content. Users will quickly learn not to trust AI features if outputs are unreliable or broken. Hard-fail prevents silent degradation.

**What's Missing:** The plan mentions acceptance criteria ("All recommendations resolve to real catalog items") but does not describe an in-plan validation mechanism. What does "hard-fail" look like operationally? Does the API return an error if validation fails? Does the UI show a fallback? What's the scoring rubric that determines pass/fail? The plan references discovery_quality_bar.md but does not translate it into implementation steps.

---

### Gap 4: PRD-084 (Important) — Deliver Surprising But Defensible Taste-Aligned Recommendations

**Requirement:** Recommendations must balance discovery (surprising picks) with defensibility (grounded in user taste and selected concepts).

**Why It Matters:** Recommendations that are too safe are boring; recommendations that are too surprising break user trust. This balance is core to the "alchemy" experience. Without clear defensibility criteria, the AI may veer into irrelevant surprise.

**What's Missing:** The plan says "bias toward recent shows but allow classics/hidden gems" but provides no criteria for validating the balance. How does the plan measure "defensibility"? What makes a surprising recommendation defensible vs. random? No acceptance test or validation approach is specified; it relies entirely on prompt quality.

---

### Gap 5: PRD-077 (Important) — Order Concepts by Strongest Aha and Varied Axes

**Requirement:** Concepts must be ordered by (1) strength of "aha" moment and (2) diversity across axes (structure, vibe, emotion, craft).

**Why It Matters:** Concept order matters for UX—users see the best concepts first. If concepts are poorly ordered (generic ones first, or duplicates across axes), users will skip the feature and defaults. This directly impacts Alchemy and Explore Similar adoption.

**What's Missing:** The plan returns "8–12 concepts" but does not specify how they are ordered before display. Is it AI-ordered, then presented as-is? Or does the plan validate and re-order? The concept system PRD specifies this is a hard requirement; the plan assumes the AI will handle it but provides no validation or fallback.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally sound and comprehensively detailed**, with strong coverage of core infrastructure, data model, features, and user journeys. The implementation is well-grounded in the PRD and infrastructure rider, with clear attention to namespace isolation, data continuity, and API contracts. **However, the plan treats AI quality and validation as implicit (or entirely delegated to prompts) rather than explicit.** This creates risk: if AI outputs drift in quality or violate guardrails, the plan has no in-place validation mechanism to catch it before display.

The plan would be **ready to build**, but AI quality assurance remains a gap that must be addressed during development or before launch. The architecture is sound; the implementation details for AI behavioral validation are missing.

---

### Strength Clusters

**1. Benchmark Runtime & Isolation (PRD-001–017)**
- Full coverage across all infrastructure requirements. Next.js, Supabase, environment variables, namespace/user isolation, schema artifacts, auth strategies, and source-of-truth principles are all explicit and well-reasoned.
- Destroyer-reset and namespace-scoped test data are clearly specified.

**2. Collection Data & Persistence (PRD-018–037)**
- Comprehensive data model with all required fields, relationships, and merge rules.
- Timestamp-based conflict resolution for cross-device sync is clearly defined.
- Auto-save rules (status, rating, tagging) are explicit; no ambiguity in when data is persisted.
- Scoop caching (4-hour freshness) and session-only Ask/Alchemy state are both correctly modeled.

**3. App Navigation & Show Detail UX (PRD-038–064)**
- Routes, components, and page hierarchy are detailed. Detail page sections match PRD narrative order.
- Status/rating/tag controls are wired with auto-save behavior.
- Collection Home grouping by status and filtering fully specified.
- Search, Ask, Alchemy flows clearly mapped.

**4. External Catalog Integration (PRD-018, PRD-031, PRD-037)**
- Show resolution strategy (external ID + title match) is explicit.
- Merge rules for catalog refresh (non-user fields use selectFirstNonEmpty, user fields by timestamp) are clear and well-reasoned.
- Fetch/transient vs. persist distinction clear.

**5. Operational Maturity (Sections 10–16)**
- Environment variables, scripts, migrations, secrets management, and deployment pipeline are all concrete.
- Monitoring, logging, alerting, and security controls are well-thought-out.
- RLS and data access control specified at database level.

---

### Weakness Clusters

**Pattern 1: AI Quality & Validation (PRD-070, PRD-077, PRD-084, PRD-086, PRD-091)**

All five gaps cluster around AI quality and validation. The pattern is consistent:
- The plan specifies **what the AI should do** (persona, voice, concepts, guardrails) but assumes these happen via prompts alone.
- No **validation layer** is described to check AI outputs before display.
- No **fallback behavior** is specified if AI outputs fail validation (e.g., hallucinated shows, off-domain content, generic concepts).
- No **scoring rubric** or **acceptance test** is provided to measure quality in operation.

This is a **product quality risk**, not an architectural risk. The plan can be built as-is, but AI quality assurance must be added during development.

**Pattern 2: Prompt Engineering (all AI surfaces)**

The plan frequently defers to "the AI prompt will handle this":
- Summarization preserves voice "via prompt"
- Concepts are ordered by aha "via prompt"
- Recommendations are surprising but defensible "via prompt selection"
- Guardrails enforced "via shared system prompt"

While this is reasonable for an MVP, it leaves **no margin for error** if prompts drift or models change. The plan should include:
- A validation step after AI generation
- Fallback UI/behavior if validation fails
- A rubric for measuring quality

---

### Risk Assessment

**Most Likely Failure Mode:**

If this plan is executed as-is, the first failure point is **AI quality drift over time or model change.**

Here's the scenario:
1. Launch with prompt-based guardrails and voice control.
2. A month in, the AI starts suggesting off-brand shows or generic concepts (model fine-tuning, prompt degradation, token budget squeeze).
3. Users report bad recommendations.
4. No in-plan mechanism exists to detect or prevent this.
5. Team must manually review outputs, rewrite prompts, and retest—all post-mortem.

**Secondary Risk:** Ask conversation summarization could lose voice mid-session, breaking the "consistent friend" feeling. This is subtle and might go unnoticed until user retention data shows decline.

**What stakeholders notice first:** 
- Concepts that are generic ("good characters," "great writing") instead of evocative.
- Recommendations that don't align with selected concepts.
- Ask responses that drift in tone or become generic.
- Mentions that fail to resolve (no fallback shown; users see blank space).

---

### Remediation Guidance

**For AI Quality & Validation:**

The plan should add (post-MVP or during dev):
1. **Output validation layer** — After AI generation, before display:
   - Concepts: check 1–3 words, non-generic (list of banned words), evocative
   - Recommendations: validate external ID + title match, confirm resolution to real catalog
   - Scoop: verify sections present, spoiler-safe check (simple keyword list)
   - Ask: validate JSON structure + mention resolution before rendering

2. **Fallback UI/behavior**:
   - If concepts fail validation: show "Concepts temporarily unavailable. Try again or use traditional recommendations."
   - If recommendations fail to resolve: show "Some recommendations unavailable; here are similar shows instead." (fall back to non-AI recs)
   - If Scoop times out: show "Scoop generation timed out; try again later."
   - If Ask mention fails: show mention as non-interactive text + "Search for it" button

3. **Scoring rubric in code**:
   - Codify the discovery_quality_bar.md rubric as a function or checklist
   - Log scores per request (for monitoring)
   - Hard-fail if integrity score < threshold (e.g., <5/10)

4. **Prompt evolution process**:
   - Version prompts in config; document change rationale
   - Test new prompts against golden set (sample conversations + expected outputs)
   - A/B test model changes in canary namespace before rollout

**For Summarization (PRD-070):**
- Add explicit prompt for "summarize this conversation turn in the voice of [persona], 1–2 sentences."
- Validate summary is not generic (contains show titles, user preferences, or persona markers)
- Option: use same AI model for summaries, or rule-based fallback if time-budget is tight

**For Concept Ordering (PRD-077):**
- Add validation step after concept generation:
  - Parse concepts into axes (structure, vibe, emotion, craft)
  - Check diversity (no two concepts on same axis consecutively)
  - If ordering is poor, re-sort or reject and ask AI to try again
- Or: prompt AI to order, then validate order in code

**Category of work:**
- **Specification:** Add validation rubric and fallback UX to product spec (or as acceptance criteria)
- **Acceptance criteria:** Define pass/fail thresholds for each AI surface
- **Code:** Implement validation functions + fallback pathways in API routes
- **Testing:** Add integration tests (mock AI outputs → validate + fallback logic)
- **Monitoring:** Log validation scores per request; alert if failure rate > threshold

---

## End of Evaluation

This plan demonstrates **strong architectural and product thinking**. It covers the PRD comprehensively, with particularly strong work on infrastructure, data model, and feature specification. The gap is not in breadth (what to build) but in depth of **AI quality assurance** (how to validate what the AI builds). This gap is remediable and should not block project start, but it is material and should be addressed early in development.

---

# Now generating stakeholder report…

I will now create the HTML stakeholder report based on this completed evaluation.

---

<div style="display:none">
REPORT_GENERATION_START
</div>

I have completed the full markdown evaluation in `results/PLAN_EVAL.md`. Now I will generate the stakeholder-ready HTML report to `results/PLAN_EVAL_REPORT.html`.

---

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Implementation Plan Evaluation — Stakeholder Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1a1f3a 100%);
            color: #1f2937;
            line-height: 1.6;
            padding: 40px 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
            overflow: hidden;
        }

        header {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }

        header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }

        header p {
            font-size: 1.1rem;
            opacity: 0.9;
            margin-bottom: 30px;
        }

        .score-display {
            background: rgba(255,255,255,0.1);
            padding: 30px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
            margin-top: 30px;
        }

        .score-circle {
            display: inline-block;
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3rem;
            font-weight: 800;
            box-shadow: 0 8px 16px rgba(16, 185, 129, 0.3);
        }

        .score-label {
            color: white;
            font-size: 1rem;
            margin-top: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }

        main {
            padding: 60px 40px;
        }

        section {
            margin-bottom: 60px;
        }

        h2 {
            font-size: 1.8rem;
            color: #0f172a;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #10b981;
            display: inline-block;
        }

        h3 {
            font-size: 1.3rem;
            color: #1e293b;
            margin: 30px 0 15px 0;
            font-weight: 600;
        }

        .narrative-box {
            background: #f8fafc;
            border-left: 4px solid #10b981;
            padding: 20px;
            margin: 20px 0;
            border-radius: 4px;
            line-height: 1.8;
        }

        .chart-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 30px;
            margin: 40px 0;
        }

        .chart-item {
            background: #f8fafc;
            padding: 30px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            text-align: center;
        }

        .chart-label {
            font-size: 0.95rem;
            color: #64748b;
            margin-bottom: 15px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .chart-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 10px;
        }

        .chart-subtext {
            font-size: 0.85rem;
            color: #78909c;
        }

        .bar-container {
            width: 100%;
            height: 24px;
            background: #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            margin-top: 15px;
        }

        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981 0%, #059669 100%);
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 8px;
            color: white;
            font-size: 0.75rem;
            font-weight: 700;
        }

        .bar-partial {
            background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);
        }

        .gap-list {
            margin: 30px 0;
        }

        .gap-item {
            background: #fff5f7;
            border-left: 4px solid #dc2626;
            padding: 20px;
            margin: 15px 0;
            border-radius: 4px;
        }

        .gap-title {
            font-weight: 700;
            color: #991b1b;
            margin-bottom: 8px;
            font-size: 1.05rem;
        }

        .gap-desc {
            color: #7f1d1d;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .strength-tag {
            display: inline-block;
            background: #dcfce7;
            color: #166534;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 10px;
        }

        .warning-tag {
            display: inline-block;
            background: #fef3c7;
            color: #92400e;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 10px;
            margin-bottom: 10px;
        }

        .callout {
            background: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            margin: 30px 0;
            border-radius: 4px;
        }

        .callout-title {
            font-weight: 700;
            color: #1e40af;
            margin-bottom: 8px;
        }

        .callout-text {
            color: #1e3a8a;
        }

        .recommendation-list {
            margin: 20px 0;
            padding-left: 20px;
        }

        .recommendation-list li {
            margin: 12px 0;
            color: #334155;
        }

        .bullet-group {
            margin: 20px 0 20px 20px;
        }

        .bullet-group li {
            margin: 8px 0;
            color: #475569;
        }

        footer {
            background: #f1f5f9;
            padding: 30px 40px;
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
            border-top: 1px solid #e2e8f0;
        }

        .severity-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .severity-critical {
            background: #fecaca;
            color: #991b1b;
        }

        .severity-important {
            background: #fed7aa;
            color: #92400e;
        }

        .timeline {
            margin: 30px 0;
        }

        .timeline-item {
            padding-left: 40px;
            margin: 20px 0;
            position: relative;
        }

        .timeline-item:before {
            content: "";
            position: absolute;
            left: 0;
            top: 5px;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #10b981;
            border: 3px solid white;
            box-shadow: 0 0 0 2px #10b981;
        }

        .timeline-item.current:before {
            background: #f59e0b;
            box-shadow: 0 0 0 2px #f59e0b;
        }

        .timeline-item.future:before {
            background: #cbd5e1;
            box-shadow: 0 0 0 2px #cbd5e1;
        }

        .timeline-title {
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 5px;
        }

        .timeline-desc {
            color: #64748b;
            font-size: 0.95rem;
        }

        @media (max-width: 768px) {
            header {
                padding: 40px 20px;
            }

            header h1 {
                font-size: 1.8rem;
            }

            main {
                padding: 40px 20px;
            }

            .chart-row {
                grid-template-columns: 1fr;
            }

            h2 {
                font-size: 1.4rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Implementation Plan Evaluation</h1>
            <p>Personal TV/Movie Companion App — Stakeholder Briefing</p>
            
            <div class="score-display">
                <div style="display: flex; align-items: center; justify-content: center; gap: 40px; flex-wrap: wrap;">
                    <div style="text-align: center;">
                        <div class="score-circle">96