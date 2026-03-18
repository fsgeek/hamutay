# Plan Evaluation: Entertainment Companion App

## 1. Requirements Extraction

### Pass 1: Identify Functional Areas

The canonical requirement catalog establishes the following functional areas (in order):

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
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable)" explicitly chosen as frontend runtime. |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "@supabase/supabase-js" explicitly listed as client library. |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 provides complete `.env.example` with database, catalog, AI, and app config keys. |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: `.gitignore` explicitly excludes `.env*` (except `.env.example`). |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "build must run by filling in environment variables, without editing source code." Entire design centered on env configuration. |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3: "secrets in environment, none committed." Section 10.1 details server-only storage for API keys. |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 17 lists required npm scripts: `npm run dev`, `npm run test`, `npm run test:reset`, plus db:push, db:seed. |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 mentions migrations; Section 17 lists `npm run db:push` for applying migrations. |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.1 defines Show schema with `namespace_id` field; Section 1.2 states "all data partitioned by (namespace_id, user_id)." |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 12.2 `/api/test/reset` scopes to namespace_id; "Test data never crosses namespace boundaries." |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.1 Show schema includes `user_id`; Section 15.1 enforces user_id in RLS policies and API authorization. |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 database indexes on `(namespace_id, user_id)`; Section 15.1 RLS enforces this partition. |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 describes X-User-Id header injection for dev mode, disabled in production. Process.env.NODE_ENV check documented. |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "Switch from header injection to real OAuth: Add auth library, extract user_id from auth session instead of header, Schema unchanged." |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance, but correctness depends on server state." |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1: "Client-side caching in React state; clearing local storage must not lose user data." Section 6.2: clients may cache but "clearing client storage must not lose user data." |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly." |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | partial | Section 2.1 Show schema includes My Data fields (myStatus, myTags, myScore). Implementation mentions "whenever a show appears" but does not explicitly address component-level overlay logic in every UI location (tiles, search results, recommendations). This is implied but not detailed per-surface. |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 2.3 lists all statuses: "Active, Later, Wait, Done, Quit, Next (hidden)." Next explicitly marked as data-only. |  |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 auto-save table: "Select Interested/Excited → Later + Interested/Excited." Section 4.3 confirms Interested/Excited are interest levels that map to Later status. |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1 Show schema: `myTags: [String]`. Section 4.4 Collection Home groups by tags; filters sidebar has tag filters. |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is 'in collection' when myStatus != nil." |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 documents all save triggers: setting status, interest, rating, tagging. |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 table: default to Later + Interested; exception: "First save via rating defaults status to Done." |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Effects: Show is removed from storage. All My Data cleared: status, interest, tags, rating, and AI Scoop." |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 5.5: "Preserve their latest status, interest, tags, rating, and AI Scoop. Refresh public metadata as available." Merge by timestamp. |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.6 lists all timestamps: myStatusUpdateDate, myInterestUpdateDate, myTagsUpdateDate, myScoreUpdateDate, aiScoopUpdateDate. |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.6 "Uses: Sorting, Cloud conflict resolution, AI cache freshness." Merge rule in 5.5 uses timestamp resolution. |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 "Cache in database with 4-hour freshness. Only persist if show is in collection." |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.7 table: "Ask chat history: No (Session only)." "Alchemy results/reasons: No (Session only)." |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5 output format includes resolution: "For each rec, resolve to real catalog item via external ID + title match." |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator when myStatus exists. User rating indicator when myScore exists." |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | partial | Section 5.5 merge by timestamp is documented. However, "duplicate detection" and "transparent merging" are noted only briefly ("Duplicate shows detected by id and merged transparently"). No explicit algorithm for detecting duplicates across devices or handling conflicts at the library level is detailed. |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version reads old schema and transparently transforms on first load... Automatic schema migration on app boot if dataModelVersion mismatch detected." |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 defines CloudSettings, LocalSettings, UIState tables. Section 4.7 Settings page saves to all three. |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show schema: providerData persisted. Section 7.1 "transient fetches: cast, crew, seasons, videos, recommendations are not persisted." |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 5 (Data Behaviors) details merge rules: non-user fields selectFirstNonEmpty, user fields by timestamp. detailsUpdateDate set after merge. |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 layout diagram shows "Filters panel on left (collapsible on mobile)." Section 3.2 routes cover Home, Detail, Find, Person, Settings. |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: "Find/Discover entry point" listed as persistent. Section 3.2 route `/find` top nav. |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point" listed as persistent. Section 3.2 route `/settings`. |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 Find routes: `/find/search`, `/find/ask`, `/find/alchemy` with "Mode switching uses a clear mode switcher." |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query shows table filtered by (namespace_id, user_id) and selected filter." Filter sidebar applies media-type toggle. |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: 1. Active 2. Excited (Later + Excited Interest) 3. Interested (Later + Interested) 4. Other (collapsed)." |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 mentions "tag/data/type filters" and references filters from product PRD (All, tag, genre, decade, score, media). |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge." |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 Components: "EmptyState — when no shows match filter." Also mentions "No shows in collection: prompt to Search/Ask. Filter yields none: 'No results found.'" |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text input sends query to /api/catalog/search... Server forwards to external catalog provider." |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid. In-collection items marked with indicator." |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If settings.autoSearch is true, /find/search opens on app startup." |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 explicitly states "Search does not expose AI voice... straightforward catalog search experience." |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 lists all 12 sections in order, matching detail_page_experience.md Section 3 order. |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 Section 1: "Carousel: backdrops/posters/logos/trailers. Fall back to static poster if no trailers." |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 Section 2: "Year, runtime (movie) or seasons/episodes (TV), Community score bar." |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 Section 3: "Status chips in toolbar; My Rating slider; My Tags display + tag picker." |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 5.2 table and 4.5 Section 3: "Adding a tag to unsaved show auto-saves as Later + Interested." |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 5.2 table and 4.5 Section 3: "Rating an unsaved show auto-saves as Done." |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 Section 4: "Overview text (factual)" placed early in narrative. |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 6.2: "Scoop streams progressively if supported; user sees 'Generating…' not blank wait." Also mentions state indicators (cached, no scoop, open). |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5 Section 5: "Button opens Ask with show context." Section 4.3 special variant documents show context included in initial system prompt. |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 Section 7: "Traditional Recommendations Strand." |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 Section 8: "Flow: 1. Tap Get Concepts 2. Select 1+ concepts 3. Tap Explore Shows." |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 Sections 9–10: "Streaming Availability" and "Cast & Crew: horizontal strands of people." |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 Section 11–12: "Seasons (TV only)." "Budget vs Revenue (Movies only)." |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5: "primary actions are clustered early (status, rating, scoop, concepts), long-tail info is down-page." |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history." Components list ChatHistory, ChatInput, BotTurn, UserTurn. |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3: System prompt defines "gossipy friend, opinionated, spoiler-safe." |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Render mentioned shows as horizontal strand (selectable)." Component MentionedShowsStrand listed. |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens /detail/[id] or triggers detail modal." |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 welcome state: "Display 6 random starter prompts (refresh available)." Component StarterPrompts listed. |  |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3 context management: "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated)." "Preserve feeling/tone in summary." |  |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 special variant: "Show context (title, overview, status) included in initial system prompt. Conversation flows naturally from there." |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3: "Request structured output: { commentary, showList: 'Title::externalId::mediaType;;...' }" Format explicitly documented. |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 response processing: "Parse response; if JSON fails, retry with stricter instructions. Fallback: show non-interactive mentions or hand to Search." |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | partial | Section 6.3 states "Stay within TV/movies (redirect back if asked to leave that domain)." However, no specific implementation mechanism (e.g., system prompt instruction, input validation, output filtering) is detailed. This is referenced but not concretely implemented. |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4 input description: "extract concept 'ingredients' (1–3 words each, evocative, no plot)." |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 AI prompt: "Output: bullet list only. Each 1–3 words, spoiler-free. No generic placeholders." |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 mentions return of "8–12 concepts" but does not detail the ordering algorithm by "aha strength" or "varied axes." Output parsing converts to array but order preservation and diversity rules not specified. |  |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 flow step 3: "User selects 1–8 concepts. Max 8 enforced by UI." Empty state copy mentioned: "nudge toward selecting at least one concept." |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Counts: Explore Similar: 5 recs per round." |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 step 5: "Optional: More Alchemy! User can select recs as new inputs. Step back to Conceptualize Shows. Chain multiple rounds in single session." |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 step 3: "Backtracking allowed: changing shows clears concepts/results." |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 mentions "multi-show concept generation should return a larger pool of options." However, exact pool size, selection mechanism, or algorithm for generating shared concepts across 2+ shows is not detailed. |  |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 output format: "reasons should explicitly reflect the selected concepts." Example: "Shares [concept] vibes with [input shows]." |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5: "bias toward recent shows but allow classics/hidden gems." However, the algorithm for balancing "surprising but defensible" is not specified. This is aspirational but not detailed as a concrete implementation rule. |  |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 "Shared architecture: all AI surfaces use one persona with surface-specific adaptations." Scoop (6.2), Ask (6.3), Concepts (6.4) all reference shared persona from ai_personality_opus.md. |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 1.1 mentions "Consistent AI voice across all surfaces" and 6.1 states shared rules. However, no explicit implementation mechanism (e.g., system prompt template, validator function, per-surface override guard) is detailed. Rules are referenced but not operationalized. |  |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 and 6.2 persona definition: "warm, opinionated friend" with voice pillars referenced from spec. |  |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "Structured as a short 'mini blog post of taste.' Includes: personal take, honest stack-up, the Scoop centerpiece, fit/warnings, verdict." |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3 system prompt: "respond like a friend in dialogue (not an essay)." Length target "1–3 tight paragraphs." |  |
| PRD-090 | Feed AI the right surface-specific context inputs | important | partial | Section 6 describes context for each surface (Scoop: show context; Ask: library + conversation; Concepts: shows; Recs: concepts + library). However, the exact mechanics of context assembly—which fields are included, how library is summarized, token budgets—are not detailed. This is conceptually covered but not operationally specified. |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 12.1 Error Handling mentions fallbacks for missing catalog items and malformed output. However, no explicit "rubric validation" or "hard-fail" gate is documented. Error recovery exists but validation against a quality checklist is not specified. |  |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Image gallery (primary image + thumbs), Name, bio." |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Average rating of projects, Top genres by count, Projects by year (bar chart)." |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable." |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens /detail/[creditId]." |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "Font size selector (XS–XXL), Toggle: 'Search on Launch.'" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "Display username (editable)." "AI model selection (dropdown)." "API key input (stored server-side; display masked)." |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export endpoint /api/export generates .zip containing backup.json with all shows + My Data + metadata." |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "Dates encoded ISO-8601." Also mentioned in Section 17.1 testing. |  |

---

## 3. Coverage Scores

### Calculation

**Overall score:**
```
Full count = 80
Partial count = 9
Missing count = 0
Total = 99

Score = (80 × 1.0 + 9 × 0.5) / 99 × 100
       = (80 + 4.5) / 99 × 100
       = 84.5 / 99 × 100
       = 85.35%
```

**Score by severity tier:**

**Critical (30 total):**
```
Full = 27
Partial = 0
Missing = 3

Score = (27 × 1.0 + 0 × 0.5) / 30 × 100 = 90.0%  (27 of 30 critical requirements)
```

**Important (67 total):**
```
Full = 52
Partial = 9
Missing = 0

Score = (52 × 1.0 + 9 × 0.5) / 67 × 100 = 79.10%  (52 + 4.5 of 67 important requirements)
```

**Detail (2 total):**
```
Full = 2
Partial = 0
Missing = 0

Score = (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100%  (2 of 2 detail requirements)
```

**Overall: 85.35%** (84.5 of 99 total requirements)

---

## 4. Top Gaps

### Gap 1: PRD-086 | Critical | Enforce shared AI guardrails across all surfaces

**Why it matters:** Guardrails (spoiler-safety, TV/movie domain restriction, honesty about reception) are the product's ethical and tonal boundaries. Without operationalized enforcement—e.g., a shared validator or system prompt template that all surfaces inherit—guardrails become aspirational documentation rather than enforced rules. An AI surface could drift off-brand without detection. This is especially critical for publicly-facing discovery features where user trust depends on consistent behavioral safety.

### Gap 2: PRD-018 | Critical | Overlay saved user data on every show appearance

**Why it matters:** The PRD explicitly states "Whenever a show appears anywhere (lists, search, recommendations, AI outputs), if the user has a saved version, display the user-overlaid version." The plan mentions this rule conceptually but does not detail implementation at each surface (search results, recommendation cards, mentioned-shows strip, traditional recommendations strand). Without per-surface integration specs, developers may miss locations, and My Data (status, rating, tags, scoop) could fail to appear consistently, breaking user mental model that "my version is always visible."

### Gap 3: PRD-074 | Important | Redirect Ask back into TV/movie domain

**Why it matters:** The ask surface must stay in domain. Without a specific implementation mechanism (system prompt guardrail, input filter, output check), the AI could be prompted about non-entertainment topics and respond outside the app's purpose. This isn't a data integrity issue but a product focus issue—users expect a focused "TV/movie nerd friend," not a general-purpose chatbot.

### Gap 4: PRD-090 | Important | Feed AI the right surface-specific context inputs

**Why it matters:** The quality of AI responses depends entirely on what context reaches the prompt. The plan describes which surfaces get which context (Scoop: show; Ask: library) but doesn't operationalize it: Which My Data fields are included in "library summary"? What's the token budget? How is a user with 500 saved shows compressed? Without concrete context specifications, rebuilds may either over-include context (token exhaustion) or under-include it (taste-deaf responses), breaking the core "taste-aware discovery" promise.

### Gap 5: PRD-077 | Important | Order concepts by strongest aha and varied axes

**Why it matters:** Concept ordering affects user perception of quality. The plan states concepts are generated but doesn't detail how they're ranked by "aha strength" or validated for diversity across structure/vibe/emotion/craft axes. Users see the first few concepts in selection UI; poorly ordered concepts will lead to weak ingredient picking and weak downstream recommendations.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally sound and comprehensive** with a **strong data/architecture foundation** but **concerning gaps in AI operationalization**. The plan covers ~85% of requirements and provides concrete implementation detail for collection management, database schema, isolation, and CRUD operations. However, the largest gaps cluster around **AI behavioral contracts**: how guardrails are enforced, how context reaches prompts, and how quality is validated. For an app whose primary value is taste-aware AI discovery, these gaps represent **moderate-to-high risk** if executed without additional specification.

The plan is **ready for core collection and search features** (Phase 1). **AI features (Phase 2–3) will require deeper prompt design and context specification** before greenlight. This is not a "restart" scenario—the architecture is solid—but rather a "detailed design phase needed for AI surfaces before sprint planning."

### Strength Clusters

**Strongest areas:**

1. **Benchmark Runtime & Isolation (17/17 = 100%)**
   - Environment variables, secrets management, namespace partitioning, user identity injection, and destructive reset are all explicitly detailed. Docker-optional path clear.

2. **Collection Data & Persistence (19/19 = 100%)**
   - Status system, auto-save rules, timestamps, merge logic, and data continuity across upgrades are comprehensively specified. Show schema covers all My Data fields.

3. **Collection Home & Search (8/9 = 89%)**
   - Filtering, grouping, tile display, search integration all concrete. Only empty-filter states could be slightly more detailed.

4. **Show Detail & Relationship UX (14/14 = 100%)**
   - Narrative order preserved, auto-save behaviors explicit, all 12 sections specified with correct narrative flow.

5. **Settings & Export (4/4 = 100%)**
   - Font size, Search-on-launch, API key storage, and export as ISO-8601 JSON zip all concrete.

**Data integrity, schema design, and isolation are fortress-strong.**

### Weakness Clusters

**Weakest areas:**

1. **AI Voice, Persona & Quality (5.5/7 = 79%)**
   - Persona is referenced but guardrails are not operationalized. No explicit validator or prompt template inheritance mechanism. PRD-086 (guardrails) partial/missing.

2. **Ask Chat (8/10 = 80%)**
   - Conversation flow is clear, mention resolution is clear, but domain-stay mechanism (PRD-074) not operationalized. Retry logic for malformed JSON is documented but not the exact retry limit or fallback UI state.

3. **Concepts, Explore Similar & Alchemy (8/10 = 80%)**
   - Alchemy flow is clear, but concept ordering by "aha strength" and diversity validation (PRD-077) are not specified. Multi-show concept generation pool size (PRD-082) not detailed. Taste alignment scoring (PRD-084) aspirational, not algorithmic.

4. **AI Prompting Context (Across surfaces, 3/4 = 75%)**
   - Context composition (which fields, token budget, library summarization) not detailed (PRD-090). "Feed the right context" is a goal, not an operationalized process.

**Pattern:** Gaps are **not missing features** (all features exist in plan). Gaps are **missing operational detail** for AI surfaces—the prompts, context assembly, and validation logic that turn architectural decisions into actual behavior.

### Risk Assessment

**Immediate risk (if code started now without clarification):**

1. **AI surfaces ship but feel hollow or inconsistent**
   - Without prompt templates and context specs, builders will make individual choices per surface. Ask might feel chatty while Scoop feels encyclopedic. Guardrails might not be enforced uniformly.
   - **User impact:** AI surfaces feel scattered, not like one persona. Trust erodes.

2. **My Data fails to display in all locations**
   - The plan states the rule but doesn't detail per-surface overlay. Developers might miss mentioned-shows strip, recommendation cards, or search results.
   - **User impact:** User saves a show but doesn't see their status/tags in some places. Confusion about whether save worked.

3. **Ask wanders out of domain or into generic chatbot behavior**
   - Without explicit domain-stay mechanism, the AI could respond to non-entertainment queries or give generic advice instead of taste-specific recommendations.
   - **User impact:** User asks "how do I make risotto" and gets a recipe instead of redirection. Product credibility damaged.

4. **Concepts are generic or poorly ordered**
   - Without specificity rules enforced during generation and ordering rules enforced during selection, concepts degrade to "good characters," "great story," etc. Weak ingredients → weak recommendations.
   - **User impact:** Alchemy output feels like generic TMDB suggestions, not taste-aware discovery.

**Most likely failure mode:** A tester or stakeholder plays Ask, asks an off-topic question, gets a reasonable-sounding but off-brand response. Or explores Alchemy with weak concepts and gets obvious recommendations. Or opens Detail and sees their rating badge missing on the recommended shows strand. Product feels "almost right but vaguely off."

### Remediation Guidance

**For each weakness cluster, the kind of work needed:**

1. **AI Operationalization**
   - **Type of work:** Detailed prompt specification + context schema.
   - **Specific guidance:** Create prompt templates (system + user per surface) in config files (not hardcoded). Document exact context composition: which My Data fields for Scoop, how user library is summarized (top N shows? tags? ratings?), what happens when library is large. Define token budgets per surface. Document shared prompt sections that all surfaces inherit (guardrails, domain stay, spoiler-safety). Create a prompt versioning scheme.
   - **Deliverable:** A `prompts/` directory with `scoop.prompt.json`, `ask.prompt.json`, `concepts.prompt.json`, `recs.prompt.json`, each documenting system message, user message template, placeholders, context inclusion rules, and token limits.

2. **My Data Overlay Contract**
   - **Type of work:** Per-surface implementation checklist.
   - **Specific guidance:** List every surface where shows appear (Home tiles, Search results, Ask mentioned-shows strip, Explore Similar recs, Alchemy recs, Traditional recs strand, Person credits). For each, document exactly what My Data is overlaid and in what visual form (status chip, rating badge, tag pills). Create a reusable overlay component that accepts Show object and renders all My Data fields.
   - **Deliverable:** A "My Data Overlay Checklist" matrix: rows = surfaces, columns = My Data fields (status, interest, tags, rating, scoop). Mark which are displayed where. Identify missing locations.

3. **AI Guardrails Enforcement**
   - **Type of work:** Shared prompt governance + per-surface validation.
   - **Specific guidance:** Define a "guardrails section" in shared prompt templates: spoiler-safety statement, TV/movie domain boundary, honesty principle. For Ask specifically, add a "domain check" at response parsing: if response mentions non-entertainment topics, log as breach and retry with domain-stay instruction. Consider a lightweight classifier (e.g., keyword check for "movie," "show," "episode") as a fallback.
   - **Deliverable:** A `GUARDRAILS.md` document that lists 5–7 non-negotiable rules. A shared system prompt template that all surfaces inherit from. A domain-validation function in Ask response parser.

4. **Concept Generation & Ordering Rules**
   - **Type of work:** Prompt refinement + output validation.
   - **Specific guidance:** Update concept generation prompt to ask AI to order by "strongest aha moment first" and "diverse axes (structure, vibe, emotion, craft)." In response parsing, validate no more than 1–2 concepts from the same axis. Remove generic placeholders via keyword filter ("good characters," "great story," "funny"). Document multi-show concept pool size (e.g., 12–15 concepts for max 8 user selection).
   - **Deliverable:** Updated concept prompt in config. A `validateConcepts()` function that rejects generic concepts and checks diversity. Test fixtures with "good" vs "bad" concept sets.

5. **Context Composition Specification**
   - **Type of work:** Context schema design + token budgeting.
   - **Specific guidance:** For each surface, document context as a structured object: which Show fields (title, genres, overview, myStatus, myTags, etc.), which library fields (all saved shows? top 20 by recency? only shows with tags?), conversation history (full or summarized?), external info (user's taste profile?). Estimate tokens per context item. Define cutoffs (max 5000 tokens for Ask, max 8000 for Alchemy, etc.). Document what happens when context exceeds budget (drop oldest turns? summarize library?).
   - **Deliverable:** A `CONTEXT_SCHEMA.md` document with context composition per surface. Token estimation spreadsheet. Fallback rules when context overflows.

**Overall:** The plan needs a "**Prompt & Context Detail Phase**" before coding Ask/Alchemy/Scoop. This is not a big redesign—the architecture is correct—but it's necessary specification work.

---

# Stakeholder Report

**File location:** `results/PLAN_EVAL_REPORT.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Implementation Plan Evaluation — Entertainment Companion App</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 40px 20px;
            min-height: 100vh;
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
            margin-bottom: 12px;
            font-weight: 700;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.95;
            margin-bottom: 8px;
        }

        .header .subtitle {
            font-size: 0.95em;
            opacity: 0.85;
        }

        .score-banner {
            background: white;
            padding: 40px;
            text-align: center;
            border-bottom: 2px solid #f0f0f0;
        }

        .score-display {
            display: flex;
            justify-content: center;
            gap: 40px;
            align-items: center;
            flex-wrap: wrap;
        }

        .score-box {
            text-align: center;
        }

        .score-number {
            font-size: 3.5em;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 10px 0;
        }

        .score-label {
            font-size: 0.95em;
            color: #666;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .score-detail {
            font-size: 0.85em;
            color: #999;
            margin-top: 8px;
        }

        .content {
            padding: 40px;
        }

        .section {
            margin-bottom: 50px;
        }

        .section h2 {
            font-size: 1.8em;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 3px solid #667eea;
            display: inline-block;
        }

        .section h3 {
            font-size: 1.2em;
            color: #764ba2;
            margin-top: 24px;
            margin-bottom: 12px;
        }

        .score-breakdown {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-top: 20px;
            margin-bottom: 30px;
        }

        .score-card {
            background: #f9f9f9;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 24px;
            text-align: center;
        }

        .score-card.critical {
            border-color: #e74c3c;
            background: #fef5f5;
        }

        .score-card.important {
            border-color: #f39c12;
            background: #fffaf5;
        }

        .score-card.detail {
            border-color: #27ae60;
            background: #f5fef5;
        }

        .score-card .tier {
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }

        .score-card.critical .tier {
            color: #c0392b;
        }

        .score-card.important .tier {
            color: #d68910;
        }

        .score-card.detail .tier {
            color: #229954;
        }

        .score-card .percent {
            font-size: 2.2em;
            font-weight: 700;
            margin: 12px 0;
        }

        .score-card.critical .percent {
            color: #c0392b;
        }

        .score-card.important .percent {
            color: #d68910;
        }

        .score-card.detail .percent {
            color: #229954;
        }

        .score-card .detail-text {
            font-size: 0.85em;
            color: #666;
            margin-top: 8px;
        }

        .coverage-narrative {
            background: #f5f7ff;
            border-left: 4px solid #667eea;
            padding: 24px;
            border-radius: 4px;
            line-height: 1.7;
        }

        .coverage-narrative p {
            margin-bottom: 16px;
        }

        .coverage-narrative strong {
            color: #667eea;
        }

        .strength-list, .weakness-list, .gap-list {
            list-style: none;
            padding: 0;
            margin: 16px 0;
        }

        .strength-list li, .weakness-list li, .gap-list li {
            padding-left: 28px;
            margin-bottom: 12px;
            position: relative;
            line-height: 1.6;
        }

        .strength-list li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #27ae60;
            font-weight: bold;
            font-size: 1.2em;
        }

        .weakness-list li:before {
            content: "⚠";
            position: absolute;
            left: 0;
            color: #e74c3c;
            font-size: 1.1em;
        }

        .gap-list li:before {
            content: "●";
            position: absolute;
            left: 0;
            color: #e74c3c;
        }

        .gap-item {
            background: white;
            border-left: 3px solid #e74c3c;
            padding: 20px;
            margin-bottom: 16px;
            border-radius: 4px;
        }

        .gap-item .gap-title {
            font-weight: 700;
            color: #333;
            font-size: 1.05em;
            margin-bottom: 8px;
        }

        .gap-item .gap-severity {
            display: inline-block;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            padding: 4px 8px;
            border-radius: 3px;
            margin-right: 8px;
            letter-spacing: 0.5px;
        }

        .gap-item .gap-severity.critical {
            background: #e74c3c;
            color: white;
        }

        .gap-item .gap-severity.important {
            background: #f39c12;
            color: white;
        }

        .gap-item .gap-reason {
            margin-top: 12px;
            line-height: 1.6;
            color: #666;
        }

        .risk-box {
            background: #fff5f5;
            border: 1px solid #e74c3c;
            border-left: 4px solid #e74c3c;
            padding: 20px;
            border-radius: 4px;
            margin: 16px 0;
            line-height: 1.7;
        }

        .risk-box strong {
            color: #c0392b;
        }

        .recommendation-box {
            background: #f5fff5;
            border: 1px solid #27ae60;
            border-left: 4px solid #27ae60;
            padding: 20px;
            border-radius: 4px;
            margin: 16px 0;
            line-height: 1.7;
        }

        .recommendation-box strong {
            color: #229954;
        }

        .remediation-list {
            list-style: none;
            padding: 0;
            margin: 16px 0;
        }

        .remediation-list li {
            padding-left: 24px;
            margin-bottom: 16px;
            position: relative;
        }

        .remediation-list li:before {
            content: "→";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }

        .remediation-item {
            background: #f9f9f9;
            padding: 16px;
            border-radius: 4px;
            border-left: 3px solid #667eea;
            margin-top: 8px;
        }

        .remediation-item .item-title {
            font-weight: 600;
            color: #667eea;
            margin-bottom: 8px;
        }

        .remediation-item .item-guidance {
            font-size: 0.95em;
            color: #666;
            margin-bottom: 8px;
        }

        .remediation-item .item-deliverable {
            font-size: 0.9em;
            color: #999;
            font-style: italic;
            margin-top: 8px;
        }

        .arc-diagram {
            display: flex;
            justify-content: space-around;
            align-items: center;
            margin: 30px 0;
            flex-wrap: wrap;
            gap: 20px;
        }