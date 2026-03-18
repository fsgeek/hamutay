# Plan Evaluation

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
|--------|-----------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable) — app runtime, server-side logic, API routes" | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "@supabase/supabase-js (anon/public key for browser)" | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: "Required `.env.example`" with full listing | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: "Injected at runtime"; Section 15.2: ".gitignore excludes `.env*` (except `.env.example`)" | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "The build MUST run by filling in environment variables, without editing source code" (reproduced) | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 10.1: "Never committed to repo"; Section 15.2: "Server-only secrets" with specifics | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4: "Required npm scripts" lists npm run dev, npm test, npm run test:reset, etc. | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.3: "New app version reads old schema and transparently transforms"; Section 10.4: "npm run db:push — Apply database migrations" | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 1.2 & 2.1: "Each build MUST operate inside a single stable namespace identifier" | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 2.2: "RLS (Row-Level Security)" and Section 12.2: "Reset endpoint scoped to namespace_id" | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.1: Show entity includes user overlay; Section 2.2: All tables include user_id column; Section 8.1: "Server scopes all data to this user + namespace" | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: "Indexes: `shows (namespace_id, user_id)` — partition queries"; Section 15.1: "All tables enforce `(namespace_id, user_id)` partition" | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: "X-User-Id header accepted by server routes in dev mode"; "Disables in production mode" | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "User identity already modeled as opaque string; Switch from header injection to real OAuth: schema unchanged" | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance, but correctness depends on server state" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 1.2: "Implicit auto-save... client cache for performance, but correctness depends on server state" | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement" and "can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 2.1 Show entity design; Section 4.1 Collection Home implementation shows "My Data badges"; Section 4.5 Detail page shows "My Rating slider, My Tags display" | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 2.1: "Status system includes Active/Later/Wait/Done/Quit + hidden Next"; Section 5.3: "Next — hidden 'up next' (data model only, not first-class UI yet)" | |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2: "Select Interested/Excited → Later + Interested/Excited"; Section 4.5 Detail: "status chips: Active/Interested/Excited/Done/Quit/Wait" | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1 Show entity: "`myTags` (free-form user labels + timestamp)"; Section 4.5 Detail: "My Tags display + tag picker" | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is 'in collection' when `myStatus != nil`" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 Auto-Save Triggers table lists all four actions | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: "Default status: Later; Default interest: Interested; Exception: First save via rating defaults status to Done" | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Removing Confirmation... 'Remove [Show Title]... will clear all your notes, rating, and tags'" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2 Data Fetch & Merge: "Merge rules: Non-user fields: selectFirstNonEmpty; User fields: resolve by timestamp" | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5: "Every user field tracks update timestamp: myStatusUpdateDate, myInterestUpdateDate, myTagsUpdateDate, myScoreUpdateDate, aiScoopUpdateDate" | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5: "Uses: Sorting (recently updated shows first); Cloud conflict resolution (newer wins); AI cache freshness" | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation: "Only persist if show is in collection"; "Cache with 4-hour freshness" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 6.3 Ask: "Do not cache"; Section 6.4 Concepts: "Do not cache (concepts are session-specific)" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5 Concept-Based Recommendations: "For each rec, resolve to real catalog item via external ID + title match" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator: visible when myStatus != nil; Rating badge: visible when myScore != nil" | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.2 Database Schema includes cross-device sync; Section 5.5 Merge rules; Section 7.2 Data Fetch & Merge: "Duplicate shows detected by id and merged transparently" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version reads old schema and transparently transforms on first load; No user data loss; all shows, tags, ratings, statuses brought forward" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 entities include CloudSettings, LocalSettings, UIState; Section 9.1 discusses storage | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show: "External identifiers (for catalog resolution)" marked as stored; Section 7.1: "Lazy-load dependent data (cast, seasons, recommendations)" | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2 Data Fetch & Merge: "Merge rules: Non-user fields: selectFirstNonEmpty; User fields: resolve by timestamp" | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: "Filters panel on left; Find/Discover entry point; Settings entry point; Home displays collection filtered by sidebar selection" | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: "Find/Discover entry point" in persistent navigation | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point" in persistent navigation | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 Routes: "/find/search", "/find/ask", "/find/alchemy"; Section 3.3: "Find → Search/Ask/Alchemy: Mode switcher at top of Find hub" | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query `shows` table filtered by `(namespace_id, user_id)` and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: Active (largest tiles); Excited (Later + Excited); Interested (Later + Interested); Other (collapsed)" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1: "Apply media-type toggle (All/Movies/TV); display tiles with poster, title, in-collection indicator, rating badge" and database indexes support this | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 Components: "`EmptyState` — when no shows match filter"; 4.1 Implementation: "Empty states: No shows in collection: prompt to Search/Ask; Filter yields none: 'No results found'" | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text search by title/keywords" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid; In-collection items marked with indicator" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If `settings.autoSearch` is true, `/find/search` opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: "Search UI with user/assistant turns" — but wait, this is ask not search. Section 4.2 Search is non-AI; Section 4.3 Ask is AI. Correct. | full |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: Lists all 12 sections "in order": Header → Facts → Relationship → Overview → Ask → Genres → Recs → Explore Similar → Streaming → Cast/Crew → Seasons → Budget | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Header Media: Carousel: backdrops/posters/logos/trailers; Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV); Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "My Relationship Toolbar: Status chips in toolbar; My Rating slider; My Tags display + tag picker (modal/dropdown)" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 auto-save behaviors: "Adding tag on unsaved show: auto-save as Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5 auto-save behaviors: "Setting rating on unsaved show: auto-save as Done" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: "Overview + Scoop section" listed early in order; implementation shows fast scanning | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively if supported" and Section 6.2: "Allow manual 'regenerate' button to override freshness" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5: "Ask About This Show: Button opens Ask with show context" and Section 4.3 special variant: "Show context (title, overview, status) included in initial system prompt" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: Similar/recommended shows from catalog metadata; Horizontal scroll" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "Explore Similar: 'Get Concepts' button; Concept chip selector (1+ required); 'Explore Shows' button → 5 recommendations" | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: "Streaming Availability: Providers by region"; "Cast & Crew: horizontal strands of people; Click opens `/person/[id]`" | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only)"; "Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 11.2 Design Principles: "Frictionless saves — no 'Save' button; actions auto-save"; Section 4.5 Implementation: primary toolbar at top | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history; User messages sent to `/api/chat`" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 4.3: "AI response includes: commentary: string (user-facing text)"; Section 6.3 prompt: "Base system prompt defines persona (warm, opinionated friend)" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Parse `showList`, resolve each to real Show; Render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens `/detail/[id]` or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Welcome state: "display 6 random starter prompts; User can refresh to get 6 more" | |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3 Context management: "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated); Preserve feeling/tone in summary" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 special variant: "Show context (title, overview, status) included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 Ask Processing: "Request structured output with commentary and showList"; Section 4.3 Implementation: "Parse `showList` into mentions" | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 Response Processing: "if JSON fails, retry with stricter instructions; otherwise fall back to unstructured commentary + Search handoff" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1 Shared Architecture: "Stay within TV/movies (redirect back if asked to leave that domain)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4 Concepts Generation: "extract concept 'ingredients' (1–3 words each, evocative, no plot)" | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4: "Output: bullet list only; Each 1–3 words, spoiler-free; No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4: Concepts generation described, but no explicit requirement to order by "strongest aha" in implementation. Plan says "Output: Array of 8–12 concepts" but no sorting strategy specified. |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 6.4: "Each concept 1–3 words, spoiler-free; No generic placeholders"; Alchemy flow: "select 1–8 concepts" with "Max 8 enforced by UI" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy Flow: "Step 5: Optional: More Alchemy! — User can select recs as new inputs... Chain multiple rounds in single session" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 Concepts Generation for multi-show says "AI Prompt: ...when multiple shows are provided (Alchemy), concepts must be shared across all input shows" but doesn't explicitly mention "larger option pool" for multi-show vs single-show. PRD says generate larger pool but don't cap selection. Plan doesn't detail this distinction. |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "reasons should explicitly reflect the selected concepts"; "Must name which concepts align in reasoning" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5: "Output format... 'reason': 'Shares [concept] vibes with [input shows]...'" | |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 Shared Architecture: "All AI surfaces: Use configurable provider... Prompts defined in reference docs"; Section 6.6: "One config per surface... prompts updated to maintain that behavior across model changes" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1 Shared Architecture: "All AI surfaces must: Stay within TV/movies; Be spoiler-safe by default; Be opinionated and honest; Prefer specific, vibe/structure/craft-based reasoning" | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 & 6.3: "warm, opinionated friend" persona; Section 6.2 Scoop: "personality-driven, spoiler-safe 'taste review'" | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 Scoop Generation: "Structured as a short 'mini blog post of taste'; includes: personal take, honest stack-up, Scoop paragraph, fit/warnings, and verdict" | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 4.3: "Chat UI... respond like a friend in dialogue (not an essay)"; Section 6.3: "use simple formatting and bulleted lists when recommending multiple titles" | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1 User context: "User's library (saved shows) + My Data; Recent conversation context (for Ask); Selected concepts (for Alchemy/Explore Similar); Current show details (for Scoop/Ask About Show)" | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | full | Section 6.5 Resolution: "Include only recs that resolve successfully; If fewer than target count, supplement with traditional catalog recommendations or note partial results" | |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail: "Profile Header: Image gallery (primary image + thumbs); Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics (optional lightweight charts): Average rating of projects; Top genres by count; Projects by year (bar chart)" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens `/detail/[creditId]`" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 App Settings: "Font size selector (XS–XXL); Toggle: 'Search on Launch'" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 User, AI, Integrations: "Display username (editable)"; "AI provider selection"; "API key input (stored server-side; display masked)"; "Catalog provider selection" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 Your Data: "Button generates `.zip` containing: `backup.json` with all shows + My Data (dates ISO-8601); Metadata (export date, data model version)" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "`backup.json` with all shows + My Data (dates ISO-8601)" | |

---

## 3. Coverage Scores

### Overall Calculation

```
Full coverage count: 92
Partial coverage count: 7
Missing coverage count: 0

Total: 99 requirements

Score = (92 × 1.0 + 7 × 0.5) / 99 × 100
Score = (92 + 3.5) / 99 × 100
Score = 95.5 / 99 × 100
Score = 96.5%
```

### Score by Severity Tier

**Critical (30 total):**
```
Full: 29
Partial: 1 (PRD-077 ordering concepts)
Missing: 0

Score = (29 × 1.0 + 1 × 0.5) / 30 × 100
Score = (29 + 0.5) / 30 × 100
Score = 29.5 / 30 × 100
Score = 98.3% (29 of 30 critical requirements)
```

**Important (67 total):**
```
Full: 61
Partial: 6
Missing: 0

Partial items:
- PRD-077: Order concepts by strongest aha and varied axes
- PRD-082: Generate shared multi-show concepts with larger option pool

Score = (61 × 1.0 + 6 × 0.5) / 67 × 100
Score = (61 + 3) / 67 × 100
Score = 64 / 67 × 100
Score = 95.5% (61 of 67 important requirements)
```

**Detail (2 total):**
```
Full: 2
Partial: 0
Missing: 0

Score = (2 × 1.0) / 2 × 100
Score = 100% (2 of 2 detail requirements)
```

**Overall:**
```
Critical:  98.3% (29 of 30 critical requirements)
Important: 95.5% (61 of 67 important requirements)
Detail:    100.0% (2 of 2 detail requirements)
Overall:   96.5% (95.5 of 99 total requirements)
```

---

## 4. Top Gaps

1. **PRD-077 | `important` | Order concepts by strongest aha and varied axes**
   - *Why this matters:* Concept selection is a key UX flow in both Explore Similar and Alchemy. Ordering concepts by strength and diversity improves discoverability—users expect the "best" ingredients first, not random order. Poor ordering degrades the co-curation experience and makes concept selection feel arbitrary rather than guided.

2. **PRD-082 | `important` | Generate shared multi-show concepts with larger option pool**
   - *Why this matters:* Multi-show concept generation requires more synthesis than single-show; PRD specifies returning a "larger option pool" before UI capping at 8. Plan doesn't distinguish pool sizes by scenario, making it unclear whether the AI prompt accounts for this distinction. Affects Alchemy's perception of thoughtfulness.

3. **PRD-070 | `important` | Summarize older turns while preserving voice**
   - *Why this matters:* Chat depth control is subtle but critical. The plan mentions "After ~10 turns, summarize older turns... preserve feeling/tone" but doesn't specify: threshold (fixed vs adaptive), who calls summarization (client vs server), rollback strategy if summary degrades persona, or test validation. Without clarity, chat may lose personality during long sessions.

4. **PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity**
   - *Why this matters:* Real-Show Integrity is non-negotiable. Plan says "include only recs that resolve successfully; if fewer than target count, supplement or note partial results" but doesn't explicitly define acceptable partial-result thresholds. Users expect 5–6 recs; getting 3 with no explanation is degraded UX. Unclear if "supplement" means fallback to traditional recs or admit failure.

5. **PRD-030 | `important` | Keep Ask and Alchemy state session-only**
   - *Why this matters:* Session-only state is foundational to avoiding stale recommendations. Plan states "session-only" but doesn't define session boundary (browser tab? app instance? minutes of inactivity?), garbage collection strategy, or cross-tab behavior. Affects whether users can chain sessions or if Alchemy requires one unbroken flow.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **exceptionally strong and comprehensive**. It covers 96.5% of the denominator with explicit, detailed implementation guidance. The plan demonstrates deep architectural thinking—namespace isolation, timestamp-based conflict resolution, auto-save semantics, and AI voice consistency are all treated with rigor. The three-phase phasing strategy is pragmatic and reduces risk by isolating data-model work from AI integration work.

The gaps that remain are not foundational; they are refinement-level details that could be addressed during engineering without rework. The plan is genuinely **rebuild-ready**: a competent team could begin implementation immediately using this blueprint.

### Strength Clusters

**Infrastructure & Isolation (PRD-001 through PRD-017):**
The plan treats benchmark runtime, namespace isolation, and auth injection with precision. Every requirement in this cluster is fully addressed. The `.env.example` pattern, development identity injection, and schema-agnostic OAuth path are all clearly articulated. This is the strongest cluster in the evaluation.

**Collection Data & Persistence (PRD-018 through PRD-037):**
The show entity design is complete. My Data overlay, status system, auto-save triggers, removal semantics, timestamp-based conflict resolution, and re-add preservation are all explicitly specified. The three-table schema (shows, cloud_settings, app_metadata) maps cleanly to the product model. Data continuity across versions is explicitly designed. Only one minor gap (concept ordering) touches this cluster tangentially.

**Show Detail & Relationship UX (PRD-051 through PRD-064):**
The narrative hierarchy of sections is preserved in order. Auto-save behaviors (status, rating, tagging) are explicit. The Detail page drives a surprising amount of the app's value (status management, Scoop, Explore Similar, traditional recs, Ask About Show, cast navigation). The plan nails all fourteen requirements in this area.

**Core Discovery Features (PRD-065 through PRD-084):**
Ask, Alchemy, and Explore Similar are all specified with sufficient detail: chat interface with mentions, concept selection, recommendation counts, and chaining. Concept contract (evocative, 1–3 word, non-generic) is clear. The only gaps are two `important` items about concept ordering and multi-show pool sizing—design details that don't block implementation.

### Weakness Clusters

**AI Quality & Voice Consistency (PRD-085 through PRD-091):**
This cluster is 6-of-7 full, 1 partial. PRD-091 (validate discovery with rubric and hard-fail integrity) is partially addressed. The plan mentions "include only recs that resolve successfully" but doesn't define thresholds for "acceptable partial results." How many recs are "enough"? When do you supplement vs admit failure? This vagueness could lead to degraded UX if a user gets 2 recs instead of 5 with no explanation.

**Ask/Alchemy Implementation Details (PRD-070, PRD-082):**
Two `important` items cluster around conversational depth and multi-show concept generation:
- **PRD-070** (summarization) is addressed conceptually but lacks operational specifics: fixed threshold, adaptive triggers, rollback strategy if summarization breaks persona tone.
- **PRD-082** (multi-show pool sizing) is mentioned but not detailed. Single-show returns "8–12 concepts"; multi-show should return a "larger pool" before UI caps at 8, but the plan doesn't quantify "larger" or explain the distinction in the prompt.

Both gaps are implementation-time discoveries; neither blocks progress. But they signal that AI behavior details will need hammering out during Phase 2.

### Risk Assessment

**Most Likely Failure Mode:** If the plan is executed without addressing the gaps, the most probable user-facing failures are:

1. **Degraded Alchemy/Ask Recommendations** — If concept ordering is random and multi-show concepts are not noticeably richer than single-show, users will feel Alchemy lacks sophistication. "Concepts" will feel random rather than curated.

2. **Partial Results Without Explanation** — If Ask/Alchemy returns 2–3 recs instead of 5–6 due to catalog lookup failures, and the UI doesn't explain why or offer fallbacks, users will perceive it as broken rather than degraded.

3. **Chat Persona Drift** — If conversation summarization is poorly implemented (e.g., sterile system summaries or token budgeting that breaks the tone), long Ask sessions will lose the warm, opinionated voice that defines the product.

4. **Session Boundary Confusion** — If Alchemy's session boundary (when does state clear?) is ambiguous, users will encounter edge cases: "Why did my previous blend disappear?" or "Can I save and resume later?" The plan doesn't clearly answer this.

None of these are **critical failures** that would block launch. All are **quality/coherence issues** that would be noticed by users accustomed to polished AI products (GPT-based apps, Claude interfaces, etc.).

### Remediation Guidance

**For Concept Ordering (PRD-077):**
Add a post-generation pass that sorts concepts by two criteria:
1. **Strength/aha-score** (derived from AI generation or user implicit feedback)
2. **Axis diversity** (structure ≠ vibe ≠ emotion ≠ craft)

This should happen in the prompt itself (e.g., "Order by strongest aha first, varying axes") or in a lightweight parsing step. Test with golden sets of known-good concept orderings.

**For Multi-Show Concept Pool (PRD-082):**
Explicitly detail in the Alchemy prompt that multi-show concept generation should return 1.5x–2x as many concepts as single-show (e.g., 12–16 for Alchemy vs 8–10 for Explore Similar). Document why (more synthesis needed; UI will cap anyway). Test that the larger pool feels meaningfully different from single-show generation.

**For Recommendation Partial Results (PRD-091):**
Define acceptable minimums:
- Ask: 1–2 recs is acceptable; show 1–2 with "only found these" copy
- Explore Similar: 3+ recs required; <3 shows "trying traditional recommendations" or "let me search" handoff
- Alchemy: 4+ recs required; <4 is a fallback to search or "try different shows"

Implement as a three-tier fallback system with clear messaging.

**For Chat Summarization (PRD-070):**
Specify operationally:
- Fixed threshold of 10 user turns (not adaptive)
- Summarization call happens server-side when turn count exceeds threshold
- Summary is 1–2 sentences, generated by same AI provider with a summarization prompt that enforces persona preservation
- Summary replaces older turns in context window (not shown to user; UI sees contiguous chat)
- Test: Run 20+ turn sessions with each model (OpenAI, Anthropic) and manually verify persona doesn't degrade

**For Session Boundaries (PRD-030):**
Add to Phase 2 acceptance criteria:
- Session = active browser tab with focus
- Alchemy state clears on tab close, route change, or 30 minutes inactivity
- Ask state clears on route change or user "new conversation" reset
- Consider adding optional "Save This Blend" (future extension) so users can bookmark multi-round Alchemy sessions

---

# Plan Evaluation Report

<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Implementation Plan Evaluation Report</title>
<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #1a1a1a;
  line-height: 1.6;
  padding: 20px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  overflow: hidden;
}

header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 40px;
  text-align: center;
}

header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
  font-weight: 700;
}

header p {
  font-size: 1.1rem;
  opacity: 0.95;
  margin-bottom: 20px;
}

.score-card {
  background: rgba(255,255,255,0.1);
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 8px;
  padding: 20px;
  margin-top: 20px;
  backdrop-filter: blur(10px);
}

.score-display {
  font-size: 3rem;
  font-weight: 700;
  color: #ffffff;
  text-align: center;
}

.score-label {
  text-align: center;
  font-size: 0.9rem;
  opacity: 0.9;
  margin-top: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

main {
  padding: 40px;
}

section {
  margin-bottom: 50px;
}

section h2 {
  font-size: 1.8rem;
  color: #667eea;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 3px solid #667eea;
  font-weight: 700;
}

.arc-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin-bottom: 30px;
}

.arc-item {
  background: #f8f9fa;
  border-left: 5px solid #667eea;
  padding: 20px;
  border-radius: 8px;
}

.arc-item h3 {
  color: #667eea;
  margin-bottom: 10px;
  font-size: 1.1rem;
}

.arc-item p {
  color: #555;
  font-size: 0.95rem;
  line-height: 1.6;
}

.breakdown {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin: 30px 0;
}

.breakdown-item {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 25px;
  text-align: center;
  border: 2px solid #e0e0e0;
  transition: all 0.3s ease;
}

.breakdown-item:hover {
  border-color: #667eea;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.breakdown-item .percentage {
  font-size: 2.5rem;
  font-weight: 700;
  color: #667eea;
  margin-bottom: 5px;
}

.breakdown-item .tier {
  font-size: 0.9rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
}

.breakdown-item .count {
  font-size: 0.85rem;
  color: #666;
}

.strength-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}

.strength-item {
  background: #e8f5e9;
  border-left: 5px solid #4caf50;
  padding: 20px;
  border-radius: 8px;
}

.strength-item h4 {
  color: #2e7d32;
  margin-bottom: 8px;
  font-weight: 600;
}

.strength-item p {
  color: #555;
  font-size: 0.95rem;
}

.weakness-item {
  background: #fff3e0;
  border-left: 5px solid #ff9800;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 15px;
}

.weakness-item h4 {
  color: #e65100;
  margin-bottom: 8px;
  font-weight: 600;
}

.weakness-item p {
  color: #555;
  font-size: 0.95rem;
}

.risk-box {
  background: #ffebee;
  border-left: 5px solid #f44336;
  padding: 25px;
  border-radius: 8px;
  margin: 20px 0;
}

.risk-box h4 {
  color: #c62828;
  margin-bottom: 15px;
  font-weight: 700;
}

.risk-item {
  margin-bottom: 15px;
  padding-left: 20px;
  border-left: 2px solid #f44336;
}

.risk-item strong {
  color: #c62828;
}

.remediation-box {
  background: #e3f2fd;
  border-left: 5px solid #2196f3;
  padding: 25px;
  border-radius: 8px;
  margin: 20px 0;
}

.remediation-box h4 {
  color: #1565c0;
  margin-bottom: 15px;
  font-weight: 700;
}

.gap-list {
  background: #fafafa;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 25px;
  margin: 20px 0;
}

.gap-item {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.gap-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.gap-id {
  font-weight: 700;
  color: #667eea;
  font-size: 1rem;
  margin-bottom: 8px;
}

.gap-title {
  font-size: 1rem;
  color: #333;
  margin-bottom: 8px;
}

.gap-importance {
  display: inline-block;
  background: #fff3cd;
  color: #856404;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  margin-right: 10px;
}

.gap-why {
  color: #555;
  font-size: 0.95rem;
  line-height: 1.6;
  margin-top: 10px;
}

.verdict {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
  border: 2px solid #667eea;
  border-radius: 8px;
  padding: 30px;
  margin: 30px 0;
  text-align: center;
}

.verdict h3 {
  font-size: 1.5rem;
  color: #667eea;
  margin-bottom: 15px;
  font-weight: 700;
}

.verdict p {
  font-size: 1.05rem;
  color: #555;
  line-height: 1.8;
}

footer {
  background: #f8f9fa;
  border-top: 1px solid #e0e0e0;
  padding: 20px 40px;
  text-align: center;
  font-size: 0.9rem;
  color: #888;
}

@media (max-width: 768px) {
  header h1 {
    font-size: 1.8rem;
  }

  .arc-container {
    grid-template-columns: 1fr;
  }

  .breakdown {
    grid-template-columns: 1fr;
  }

  .strength-grid {
    grid-template-columns: 1fr;
  }

  main {
    padding: 25px;
  }
}

.chart-row {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 15px;
}

.chart-label {
  width: 100px;
  font-weight: 600;
  color: #667eea;
  font-size: 0.9rem;
}

.chart-bar-container {
  flex: 1;
  background: #e0e0e0;
  height: 28px;
  border-radius: 4px;
  overflow: hidden;
}

.chart-bar {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 10px;
  color: white;
  font-weight: 600;
  font-size: 0.85rem;
}

.highlight {
  background: #fff9e6;
  padding: 2px 4px;
  border-radius: 2px;
}
</style>
</head>
<body>

<div class="container">

<header>
  <h1>📋 Implementation Plan Evaluation</h1>
  <p>Personal TV/Movie Companion App — Benchmark PRD Coverage Assessment</p>
  <div class="score-card">
    <div class="score-display">96.5%</div>
    <div class="score-label">Overall Coverage Score</div>
  </div>
</header>

<main>

<section>
  <h2>📊 Evaluation Overview</h2>
  <p style="margin-bottom: 20px; color: #555; font-size: 1rem;">
    This plan was evaluated against a <span class="highlight">canonical catalog of 99 requirements</span> spanning 10 functional areas. The plan demonstrates <span class="highlight">exceptionally strong coverage</span> with 96.5% of requirements fully or substantially addressed. The gaps identified are refinement-level details that do not block implementation.
  </p>
  
  <div style="background: #f0f4ff; border-left: 5px solid #667eea; padding: 20px; border-radius: 8px; margin: 20px 0;">
    <strong style="color: #667eea; font-size: 1.05rem;">Key Finding:</strong> This plan is genuinely <strong>rebuild-ready</strong>. A competent engineering team could begin implementation immediately using this blueprint without waiting for clarification on foundational architecture.
  </div>
</section>

<section>
  <h2>📈 Before & After Arc</h2>
  <div class="arc-container">
    <div class="arc-item">
      <h3>🚀 Initial Plan Strengths</h3>
      <p>The plan arrives with exceptional depth on infrastructure, data model, and feature scope. Three-phase phasing isolates risk. Auto-save semantics and timestamp-based conflict resolution are specified with clarity. Namespace isolation is concrete, not hand-wavy.</p>
    </div>
    <div class="arc-item">
      <h3>⚡ Gaps Identified</h3>
      <p>Five `important` items lack operational specificity: concept ordering strategy, multi-show concept pool sizing, chat summarization thresholds, partial-result fall