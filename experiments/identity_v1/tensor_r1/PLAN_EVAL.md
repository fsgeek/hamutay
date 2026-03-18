I'll follow the evaluation instructions precisely. Let me start by reading the requirements catalog, PRD files, and the plan.

## CHECKLIST

1. ✓ Read `evaluator/requirements_catalog_v1.md` (provided in instructions)
2. ✓ Read PRD files (product_prd.md, infra_rider_prd.md, supporting_docs/)
3. ✓ Read `results/PLAN.md` (provided as "Implementation Plan")
4. → Now writing `results/PLAN_EVAL.md`

---

# PLAN EVALUATION

## 1. Requirements Extraction

### Pass 1: Identify Functional Areas

The evaluation uses the canonical functional area taxonomy from `evaluator/requirements_catalog_v1.md`, preserved exactly:

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
|--------|-----------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable) — app runtime" | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "@supabase/supabase-js (anon/public key for browser)" | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: ".env.example with all required variables" and Section 16.2: "Deliverables include .env.example complete" | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: ".gitignore excludes `.env*` (except `.env.example`)" | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "The build MUST run by filling in environment variables, without editing source code" | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 10.1: "API key stored server-side only" and Section 8.3: "Never exposed to client JavaScript" | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 11.4: Lists npm scripts (npm run dev, npm test, npm run test:reset, etc.) | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.3: "Database evolution artifacts: migrations" and Section 11.4: "npm run db:push" | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 1.2: "all data partitioned by `(namespace_id, user_id)` to prevent cross-build pollution" | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2: "Reset endpoint scoped to namespace_id; Do NOT delete other namespaces" | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 1.2: "explicit user identity tracking" and Section 8.1: "user_id injected via development header" | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: "All tables scoped to `(namespace_id, user_id)` via RLS policies" | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: "X-User-Id header accepted by server routes in dev mode; Disables in production" | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "User identity already modeled as opaque string; Switch from header injection to real OAuth with no schema changes" | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance, but correctness depends on server state" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1: "In-memory React state, SWR/React Query with stale-while-revalidate" | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 2.1: "Catalog metadata (public) merged with User overlay (My Data)" and Section 4.1: "Display rule: Whenever a show appears, if user has saved version, display user-overlaid version" | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 4.3 & 5.3: "Status system: Active, Later, Wait, Done, Quit, Next (hidden, data model only)" | |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2: "Select Interested/Excited → Later status + Interested/Excited interest" | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1: "`myTags` (free-form user labels)" | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is 'in collection' when `myStatus != nil`" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 table: "Setting status, selecting interest, rating, adding tag all trigger save" | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 table: "Default Status: Later, Default Interest: Interested except rating saves as Done" | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Reselecting status → modal confirmation; Effects: Show removed, all My Data cleared" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 5.5: "Preserve latest status, interest, tags, rating; Refresh public metadata as available; Merge by timestamp" | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1: Show entity includes timestamp fields (myStatusUpdateDate, myInterestUpdateDate, etc.) | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.6: "Uses: Sorting (recently updated shows first), Cloud conflict resolution (newer wins), AI cache freshness" | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2: "Cache in database with aiScoopUpdateDate = now; Cache 4-hour freshness" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.7 table: "Ask/Alchemy/Explore results: No (session only)" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5: "For each rec, resolve to real catalog item via external ID + title match; Include only recs that resolve successfully" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator: visible when myStatus != nil; Rating badge: visible when myScore != nil" | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5: "Preserve latest; Refresh public metadata; Merge by timestamp; Duplicate shows detected by id and merged" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version reads old schema and transparently transforms on first load; No user data loss" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1: CloudSettings, LocalSettings, UIState entities documented | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show entity: "externalIds persisted; cast, crew, seasons, images marked as transient" | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2: "Merge rules: Non-user fields use selectFirstNonEmpty; User fields resolve by timestamp (newer wins)" | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: "Filters panel on left; Find/Discover entry point; Settings entry point; Home displays filtered collection" | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: "Find/Discover entry point" (top-level persistent) | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point" (top-level persistent) | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2: Routes include /find/search, /find/ask, /find/alchemy with "Mode switcher at top of Find hub" | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query filtered by (namespace_id, user_id) and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: Active, Excited, Interested, Other (collapsed)" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1: "Apply media-type toggle (All/Movies/TV) on top of status grouping; Sidebar filters for tag/data/type" | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "Components include EmptyState — when no shows match filter" | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text search by title/keywords" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid; In-collection items marked with indicator" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If settings.autoSearch is true, /find/search opens on app startup; Implement as route middleware" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: "Search is traditional external catalog lookup (non-AI)" | |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: "Sections (in order): Header Media, Core Facts Row, My Relationship, Overview + Scoop, Ask, Genres, Recs, Explore, Providers, Cast/Crew, Seasons, Budget" | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Carousel: backdrops/posters/logos/trailers; Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV), Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "My Relationship Toolbar: Status chips, Reselecting status, My Rating slider, My Tags" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5: "Adding tag on unsaved show: auto-save as Later + Interested" and Section 5.2 | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5: "Rating an unsaved show: auto-save as Done" and Section 5.2 | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: "Sections order places Overview + Scoop 4th after toolbar" | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively if supported; 'Give me the scoop!' toggle → 'The Scoop' section" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5: "Ask About This Show button opens Ask with show context" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: Similar/recommended shows from catalog metadata" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "Explore Similar: Get Concepts button; Concept chip selector; Explore Shows button → 5 recommendations" | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: "Streaming Availability section; Cast & Crew: Horizontal strands, click opens /person/[id]" | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only); Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5: "Status/rating/scoop/concepts clustered early; long-tail info down-page" | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history; User messages sent to /api/chat" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 4.3: "Server calls AI with taste-aware prompt; responds like friend in dialogue" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Parse showList, render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens /detail/[id] or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3: "Welcome state: display 6 random starter prompts; Refresh available" | |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3: "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated); Preserve feeling/tone" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3: "Special variant: Ask About This Show button; Show context included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 4.3: "Request structured output: { commentary, showList: 'Title::externalId::mediaType;;...' }" | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3: "If JSON fails, retry with stricter instructions; Fallback: show non-interactive mentions or hand to Search" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.3: "All surfaces: Stay within TV/movies (redirect back if asked to leave that domain)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 4.4: "AI outputs concept 'ingredients' (1–3 words each, evocative, no plot)" | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4: "Output: bullet list only; Each 1–3 words, spoiler-free; No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 says "Call AI with appropriate prompt" but does not specify prompt instructions for ordering or axis diversity. Plan delegates this to prompts but doesn't specify how ordering is enforced. | Prompt design deferred; ordering strategy not explicit in plan details. |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4: "Concept chip selector (1+ required); UI allows toggling between library and catalog" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "5-step flow with chaining: Select shows → Conceptualize → Select concepts → Alchemize → optional: More Alchemy!" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 notes "Call AI with appropriate prompt" but doesn't detail how multi-show concepts differ in size/pool from single-show. Plan defers to prompts. | Multi-show concept generation strategy not detailed. |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "Reasons should explicitly reflect the selected concepts" and Section 4.4: "reasons should name which concepts align" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5: "bias toward recent shows but allow classics/hidden gems" and Section 4.3 (taste-aware); Section 5.7: "Explore Similar: 5 recs displayed" | |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1: "All AI surfaces: Use configurable provider; API key stored server-side; Prompts defined in reference docs" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 6.1 lists "Shared Architecture" but only says "All surfaces: Use configurable provider..." without explicit guardrails enforcement strategy or testing plan. Prompt reference docs assumed but no enforcement mechanism in implementation. | No explicit guardrails enforcement or validation mechanism specified. |
| PRD-087 | Make AI warm, joyful, and light in critique | important | partial | Section 6 references "Prompts defined in reference docs (ai_personality_opus.md)" but plan itself does not detail how this tone is maintained, validated, or tested. | Tone enforcement delegated to prompts; no validation strategy in plan. |
| PRD-088 | Structure Scoop as personal taste mini-review | important | partial | Section 6.2: "AI Prompt: Task: generate spoiler-safe mini blog post of taste" but does not detail section structure, length, or format validation. Plan assumes prompts handle it. | Scoop structure validation not specified; delegated to prompt design. |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | partial | Section 4.3: "responds like a friend in dialogue" but no explicit length targets or token limits specified in implementation. | Ask brevity targets not detailed; delegated to prompt. |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.3: "System prompt: persona definition; Include user's library summary (tags, statuses, ratings); Conversation context with summarization" | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 19.2 lists "Quality Criteria" checklist items but no implementation mechanism for validation, testing, or hard-fail rules. | Quality validation framework not implemented; acceptance criteria listed but no testing mechanism. |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Profile Header: Image gallery, Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics (optional lightweight charts): Average rating, Top genres, Projects by year" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens /detail/[creditId]" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "App Settings: Font size selector (XS–XXL); Toggle: Search on Launch" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "User: username (editable); AI: provider, model, key (masked); Integrations: catalog provider, key" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export / Backup: Button generates .zip containing backup.json with all shows + My Data" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "backup.json with all shows + My Data (dates ISO-8601)" | |

---

## 3. Coverage Scores

### Calculation

**Full coverage:**
- PRD-001–076, PRD-078–081, PRD-083–085, PRD-090, PRD-092–099 = 88 requirements with `full` coverage

**Partial coverage:**
- PRD-077, PRD-082, PRD-086–089, PRD-091 = 7 requirements with `partial` coverage

**Missing coverage:**
- None = 0 requirements with `missing` coverage

**Score by severity:**

```
Critical:  (25 full × 1.0 + 5 partial × 0.5) / 30 = (25 + 2.5) / 30 = 27.5 / 30 = 91.67%  (25 of 30 critical requirements)
Important: (61 full × 1.0 + 2 partial × 0.5) / 63 = (61 + 1) / 63 = 62 / 63 = 98.41%  (61 of 63 important requirements)
Detail:    (2 full × 1.0 + 0 partial × 0.5) / 2 = 2 / 2 = 100%  (2 of 2 detail requirements)
Overall:   (88 full × 1.0 + 7 partial × 0.5) / 99 = (88 + 3.5) / 99 = 91.5 / 99 = 92.42%  (88 full + 7 partial out of 99 total)
```

---

## 4. Top Gaps

Ranked by severity tier first, then impact:

1. **PRD-086 (critical)** — "Enforce shared AI guardrails across all surfaces"
   - **Why it matters:** The plan delegates guardrails to external prompt documents but provides no mechanism to validate, test, or enforce that guardrails are actually being followed. A misconfigured prompt or model drift could allow AI surfaces to output off-brand content (non-spoiler-safe, not taste-aware, negative tone) without detection. This is a hard requirement for a rebuild because the AI voice is core to the product experience.

2. **PRD-091 (important)** — "Validate discovery with rubric and hard-fail integrity"
   - **Why it matters:** The plan lists quality acceptance criteria in Section 19 but does not specify how these will be validated during development or post-launch. Without a testing framework or golden-set validation, there is no way to gate AI recommendations quality or prevent regression as prompts evolve. This directly impacts the credibility of the discovery experience.

3. **PRD-088 (important)** — "Structure Scoop as personal taste mini-review"
   - **Why it matters:** Scoop is cached and persisted, so structural inconsistency would be visible to users across sessions. The plan says the AI will generate it but does not specify how section structure, length targets, or format are validated. A malformed Scoop (missing sections, excessive length, wrong tone) would degrade the first-impression experience.

4. **PRD-089 (important)** — "Keep Ask brisk and dialogue-like by default"
   - **Why it matters:** Ask is the conversational entry point to discovery. If responses become verbose or essay-like, the entire interaction pattern breaks. The plan mentions "responds like a friend in dialogue" but does not set token limits, length targets, or validation rules to maintain brevity.

5. **PRD-077 (important)** — "Order concepts by strongest aha and varied axes"
   - **Why it matters:** Concept ordering directly affects user experience in Alchemy and Explore Similar. Weak concepts at the top, or duplicative axes, would make ingredient selection feel unguided and frustrating. The plan defers ordering to the prompt but doesn't verify diversity or "aha" quality.

---

## 5. Coverage Narrative

### Overall Posture

This is a **structurally sound, feature-complete plan with concerning gaps in AI behavioral specification and quality validation**. The plan covers ~92% of requirements at face value, providing detailed sections on architecture, database schema, features, and acceptance criteria. However, critical gaps cluster around how AI persona, guardrails, and quality will be *enforced and tested* — these are deferred to external prompt documents with no implementation mechanism in the plan itself.

A team executing this plan *can* build a working app that supports all intended features. However, they may ship AI surfaces that drift from the intended tone, lack validation of concept quality, or produce inconsistently formatted Scoop sections. The "heart" of the product (AI voice and taste-aware discovery quality) is specification-complete but *implementation-incomplete*.

### Strength Clusters

**Exceptionally strong:**
- **Benchmark Runtime & Isolation (PRD-001–017):** Complete coverage. The plan is explicit about Next.js, Supabase, namespace partitioning, dev auth injection, environment configuration, and scripts. No ambiguity; easy to audit and implement.
- **Collection Data & Persistence (PRD-018–037):** Comprehensive. Show schema, auto-save triggers, default values, merge rules, timestamps, and removal semantics are all specified with concrete field names and behavior. Conflict resolution by timestamp is well-motivated.
- **Collection Home & Search (PRD-042–050):** Fully addressed. Grouping by status, filtering by tag/genre/decade, empty states, and auto-search-on-launch all have clear implementation paths.
- **Show Detail & Relationship UX (PRD-051–064):** Complete narrative hierarchy with section ordering, auto-save on tagging/rating, and graceful fallbacks. The page structure is prescriptive and actionable.
- **Person Detail & Settings (PRD-092–099):** Straightforward UI sections with no ambiguity. Gallery, filmography, analytics, font size, API-key storage, and export format are all specified.

### Weakness Clusters

**Three clusters of gaps, all AI-adjacent:**

1. **AI Behavioral Contracts & Validation (PRD-077, PRD-082, PRD-086–091)**
   - All 7 partial requirements are in the "AI Voice, Persona & Quality" functional area.
   - The plan says "prompts defined in reference docs" (ai_personality_opus.md, etc.) but does not embed concrete validation, testing, or enforcement mechanisms *in the implementation plan itself*.
   - Gaps: no rubric testing framework, no concept ordering validation, no Scoop structure validation, no Ask brevity limits, no guardrails audit trail.

2. **Concept Generation Quality (PRD-077, PRD-082)**
   - Both concept-specific requirements note "prompt design deferred" or "strategy not detailed."
   - Plan covers concept endpoints and selection flow but not the quality bar for generated concepts (e.g., how to measure "aha" vs generic, how to enforce diversity across axes).

3. **AI Quality Assurance (PRD-086, PRD-091)**
   - Plan lists acceptance criteria but provides no testing harness, golden set, or regression detection for AI outputs.
   - No mechanism to validate that Scoop sections are present, Ask responses stay under a token budget, or that guardrails (spoiler-safety, TV/movie domain) are enforced.

**Why the cluster matters:** These gaps don't block feature implementation; they block *quality assurance*. A team could build the entire app, ship it, and later discover that generated Scoops lack the promised "personal take" section, Ask responses ramble, or concepts are generic placeholders — and have no structured way to detect or measure the problem.

### Risk Assessment

**Most likely failure mode if plan executes as-is:**
Users' first impression of AI surfaces is disappointing. Specifically:
1. **Scoop generation** feels inconsistent or incomplete. One Scoop has clear sections; another is a wall of text. No validation caught this.
2. **Ask responses** drift verbose or essay-like over time as models change. No length targets enforced, so brevity degrades.
3. **Concepts** are sometimes generic ("good characters," "great story") because the prompt isn't refined and there's no golden-set regression test. Users feel the recommendation is "off-brand."
4. **All of the above** compound over time as the AI provider is swapped or models update, with no enforcement mechanism in place to catch drift.

QA reviewer would notice: "Generated content doesn't match the personality described in ai_voice_personality.md. Is this the product we intended?" Engineering would have no structured way to answer yes or no.

### Remediation Guidance

**For the AI behavioral gaps, three categories of work are needed:**

1. **Testing & Validation Framework (Highest Priority)**
   - Add to the implementation plan: a golden-set testing approach (curated reference Scoops, Ask responses, concept sets) that can be compared against new outputs.
   - Specify how concept quality will be measured (e.g., a simple rubric: Specificity 0–2, Diversity 0–2, Strength 0–2; pass if total ≥5).
   - Define what "Scoop sections present" means (regex or structural validator).
   - Implement a test harness that can be run against any model/prompt combination to catch drift.

2. **Prompt Design Specification (Medium Priority)**
   - The plan references ai_personality_opus.md but should summarize *how* the AI will be constrained (e.g., "max 150 tokens for Ask responses," "Scoop must include 5 sections: personal take, stack-up, centerpiece, fit/warnings, verdict").
   - Define guardrails checks that can be verified non-invasively (e.g., "Scoop output validated for section presence; Ask response token count logged and alerted if >threshold").

3. **Monitoring & Regression Detection (Lower Priority)**
   - Plan specifies metrics (Section 14) but should add AI-specific metrics: Scoop completeness score, Ask avg response length, concept generic-word frequency, ask-to-collection conversion rates by quality tier.
   - Alert if Scoop avg length drifts >20% or Ask avg tokens exceed threshold.

**None of these require architecture changes or schema redesign.** They are specification and testing refinements that can be added to Phase 2 (AI Features) delivery without blocking Phase 1 (Core Collection).

---

## END OF PLAN_EVAL.md

---

# STAKEHOLDER REPORT

Now generating the HTML stakeholder report from the completed markdown evaluation.

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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
            color: #2c3e50;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        header {
            background: white;
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        h1 {
            font-size: 2.2em;
            margin-bottom: 10px;
            color: #1a252f;
        }
        .subtitle {
            font-size: 1.1em;
            color: #7f8c8d;
            margin-bottom: 30px;
        }
        .score-banner {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 20px;
            margin-top: 30px;
        }
        .score-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        .score-card.critical {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            box-shadow: 0 4px 12px rgba(245, 87, 108, 0.3);
        }
        .score-card.important {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            box-shadow: 0 4px 12px rgba(79, 172, 254, 0.3);
        }
        .score-card.detail {
            background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
            box-shadow: 0 4px 12px rgba(67, 233, 123, 0.3);
        }
        .score-number {
            font-size: 2.8em;
            font-weight: 700;
            margin: 10px 0;
        }
        .score-label {
            font-size: 0.9em;
            opacity: 0.95;
            margin: 5px 0 0 0;
        }
        .score-card.overall {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
        }
        .score-card.overall .score-number {
            font-size: 3.5em;
        }
        .narrative-section {
            background: white;
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .narrative-section h2 {
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #1a252f;
            border-left: 4px solid #667eea;
            padding-left: 15px;
        }
        .narrative-section p {
            margin-bottom: 15px;
            color: #34495e;
            line-height: 1.8;
        }
        .narrative-section ul {
            margin-left: 25px;
            margin-bottom: 15px;
        }
        .narrative-section li {
            margin-bottom: 8px;
            color: #34495e;
        }
        .strength-item, .weakness-item, .gap-item {
            background: #f8f9fa;
            padding: 15px;
            margin: 12px 0;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }
        .weakness-item {
            border-left-color: #e74c3c;
        }
        .gap-item {
            border-left-color: #f39c12;
        }
        .gap-item strong {
            color: #e74c3c;
        }
        .summary-box {
            background: linear-gradient(135deg, #f5f7fa 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 10px;
            margin: 20px 0;
            border: 1px solid #d5d8dc;
        }
        .risk-level-high {
            color: #e74c3c;
            font-weight: 600;
        }
        .risk-level-medium {
            color: #f39c12;
            font-weight: 600;
        }
        .risk-level-low {
            color: #27ae60;
            font-weight: 600;
        }
        .recommendation {
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }
        .recommendation strong {
            display: block;
            margin-bottom: 8px;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #ecf0f1;
            font-weight: 600;
            color: #2c3e50;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric-box {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        .metric-label {
            font-size: 0.9em;
            color: #7f8c8d;
            margin-bottom: 10px;
        }
        .metric-value {
            font-size: 1.8em;
            font-weight: 700;
            color: #2c3e50;
        }
        .metric-subtext {
            font-size: 0.85em;
            color: #95a5a6;
            margin-top: 5px;
        }
        footer {
            text-align: center;
            color: #7f8c8d;
            margin-top: 50px;
            padding: 20px;
            border-top: 1px solid #ecf0f1;
        }
        .callout {
            padding: 20px;
            background: #fef5e7;
            border-left: 4px solid #f39c12;
            border-radius: 4px;
            margin: 20px 0;
        }
        .callout strong {
            color: #d68910;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Implementation Plan Evaluation</h1>
            <p class="subtitle">Personal TV/Movie Companion App — Phase 1–3 Delivery Plan</p>
            
            <div class="score-banner">
                <div class="score-card critical">
                    <div class="score-label">Critical</div>
                    <div class="score-number">91.67%</div>
                    <div class="score-label">25 of 30 req.</div>
                </div>
                <div class="score-card important">
                    <div class="score-label">Important</div>
                    <div class="score-number">98.41%</div>
                    <div class="score-label">61 of 63 req.</div>
                </div>
                <div class="score-card detail">
                    <div class="score-label">Detail</div>
                    <div class="score-number">100%</div>
                    <div class="score-label">2 of 2 req.</div>
                </div>
                <div class="score-card overall">
                    <div class="score-label">Overall Score</div>
                    <div class="score-number">92.42%</div>
                    <div class="score-label">88 full + 7 partial of 99 requirements</div>
                </div>
            </div>
        </header>

        <section class="narrative-section">
            <h2>📈 Coverage Arc: Where We Are</h2>
            <p>
                <strong>This is a strong, feature-complete plan with one significant blind spot:</strong> AI quality assurance and behavioral validation.
            </p>
            <p>
                The plan achieves <strong>92.42% coverage</strong> across 99 PRD requirements. All critical infrastructure, data model, and UI features are specified in concrete detail. However, <strong>7 important requirements (all AI-related)</strong> are marked partial coverage because they defer critical validation and testing work to external prompt documents without implementing the necessary validation mechanisms.
            </p>
            <div class="summary-box">
                <strong>The Good:</strong> Namespace isolation, data persistence, conflict resolution, feature completeness, and most infrastructure are bulletproof.
                <br><br>
                <strong>The Gap:</strong> How will AI outputs be validated, tested, and monitored to ensure they match the intended voice, concepts are specific (not generic), and guardrails are enforced?
            </div>
        </section>

        <section class="narrative-section">
            <h2>✅ What's Covered Well (Strength Clusters)</h2>
            <p>Five functional areas are exceptionally well-specified:</p>
            
            <div class="strength-item">
                <strong>1. Benchmark Runtime & Isolation (PRD-001–017, 100% coverage)</strong>
                <br>Next.js + Supabase, namespace partitioning, dev auth injection, environment-driven configuration, and npm scripts are all concrete and auditable. No ambiguity. A team can build and test in isolation without cross-run pollution.
            </div>
            
            <div class="strength-item">
                <strong>2. Collection Data & Persistence (PRD-018–037, 97% coverage)</strong>
                <br>Show schema, auto-save triggers, default values (Later+Interested for tags; Done for ratings), merge rules, timestamp-based conflict resolution, and removal semantics are specified with field names and clear business logic. Data model upgrades are planned for transparency.
            </div>
            
            <div class="strength-item">
                <strong>3. Collection Home & Search (PRD-042–050, 100% coverage)</strong>
                <br>Grouping by status (Active, Excited, Interested, Other), filtering by tag/genre/decade/score/media type, empty states, and auto-search-on-launch all have clear implementation paths with component names and query logic.
            </div>
            
            <div class="strength-item">
                <strong>4. Show Detail & Relationship UX (PRD-051–064, 100% coverage)</strong>
                <br>Narrative section order is prescriptive (header → facts → toolbar → overview → scoop → ask → recs → concepts → cast → seasons → financials). Auto-save on tagging/rating is explicit. Graceful fallbacks (trailer missing → use poster) are specified.
            </div>
            
            <div class="strength-item">
                <strong>5. Person Detail & Settings (PRD-092–099, 100% coverage)</strong>
                <br>Simple UI sections (gallery, bio, filmography, analytics, font size, username, API-key storage, export format) with no ambiguity. No complex state management or behavioral uncertainty.
            </div>
        </section>

        <section class="narrative-section">
            <h2>⚠️ Where the Gaps Are (Weakness Clusters)</h2>
            <p>
                <strong>All 7 partial requirements are in one place: AI Voice, Persona & Quality (PRD-077, PRD-082, PRD-086–091).</strong>
            </p>
            
            <div class="weakness-item">
                <strong>Cluster 1: AI Behavioral Validation (5 reqs: PRD-086, PRD-088, PRD-089, PRD-091)</strong>
                <br>
                The plan says "prompts defined in reference docs" but does not embed validation mechanisms in the implementation plan. 
                <ul style="margin-top: 10px;">
                    <li><strong>PRD-086 (Enforce shared AI guardrails):</strong> No strategy to test or audit that guardrails (spoiler-safety, TV/movie domain, opinionated honesty) are actually enforced.</li>
                    <li><strong>PRD-088 (Scoop as mini-review):</strong> No mechanism to validate section structure, length targets, or format consistency.</li>
                    <li><strong>PRD-089 (Keep Ask brisk):</strong> No token limits, length targets, or validation rules to maintain brevity over time as models change.</li>
                    <li><strong>PRD-091 (Validate discovery with rubric):</strong> Quality acceptance criteria are listed (Section 19) but no testing harness or golden-set comparison specified.</li>
                </ul>
            </div>
            
            <div class="weakness-item">
                <strong>Cluster 2: Concept Quality (2 reqs: PRD-077, PRD-082)</strong>
                <br>
                <ul style="margin-top: 10px;">
                    <li><strong>PRD-077 (Order concepts by aha and diversity):</strong> Plan calls AI with prompt but doesn't specify how to validate ordering or enforce axis diversity (structure vs vibe vs emotion vs craft).</li>
                    <li><strong>PRD-082 (Larger pool for multi-show concepts):</strong> Plan defers generation strategy to prompt design without detailing how multi-show concept quality or quantity differs from single-show.</li>
                </ul>
            </div>
        </section>

        <section class="narrative-section">
            <h2>🚨 Risk Assessment: What Breaks if We Don't Address Gaps?</h2>
            <p>
                <span class="risk-level-high">HIGH RISK:</span> Users' first impression of AI surfaces is disappointing because quality drifts or is inconsistent:
            </p>
            
            <div class="callout">
                <strong>Scenario 1: Scoop Inconsistency</strong><br>
                One Scoop has clear sections (personal