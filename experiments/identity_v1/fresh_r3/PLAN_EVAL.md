# PLAN EVALUATION

## Checklist (In Progress)

- [x] Read `evaluator/requirements_catalog_v1.md`
- [x] Read PRD files (product_prd.md, infra_rider_prd.md, supporting_docs/)
- [x] Read `results/PLAN.md`
- [ ] Write full markdown evaluation to `results/PLAN_EVAL.md`
- [ ] Re-open completed evaluation
- [ ] Generate stakeholder report to `results/PLAN_EVAL_REPORT.html`

---

# PLAN_EVAL.md

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
|--------|-------------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 (Technology Stack): "Next.js (latest stable) — app runtime" | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 (Technology Stack): "@supabase/supabase-js (anon/public key for browser)" | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 (Environment Variables): Detailed `.env.example` provided with all required keys | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: "`.gitignore` excludes `.env*` (except `.env.example`)" | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 1.2 (Key Principles) and 10.1: "build MUST run by filling in environment variables, without editing source code" | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.2 (Server-Only Secrets): "never exposed to client JavaScript" and section 10.1 | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 20 (Summary): Lists npm scripts: `npm run dev`, `npm test`, `npm run test:reset` | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 (Database Schema) and 10.2 (Development Environment): migrations and seed scripts mentioned | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 1.2: "all data partitioned by `(namespace_id, user_id)`" throughout | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 2.1 (Data Model) and 9.2 (Destructive Testing): "Delete all shows in namespace" without crossing boundaries | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 (Database Schema) and throughout: all tables include `user_id` column | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 8.1 (Data Access Control): "All tables enforce `(namespace_id, user_id)` partition" via RLS | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 (Benchmark-Mode Identity Injection): "X-User-Id header accepted by server routes in dev mode" with feature flag | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 (Future OAuth Path): "Switch from header injection to real OAuth: Add auth library... Schema unchanged" | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance, but correctness depends on server state" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1: "Client-side caching: In-memory React state" and note that all data retrieved from server | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1: "Display rule: Whenever a show appears anywhere ... display the user‑overlaid version" | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 4.1: Shows and section 5.3 mention all statuses including "Next" (hidden) | |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 (Auto-Save Triggers): "Select Interested/Excited: Later status with Interested/Excited interest" | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.1: "My Tags (free‑form labels/lists)" and multiple sections describe tag filtering | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 (Collection Membership): "A show is 'in collection' when `myStatus != nil`" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 (Auto-Save Triggers): Table showing all save triggers with actions | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: "Default Status: Later, Default Interest: Interested" and "First save via rating defaults status to Done" | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 (Removal Confirmation): "Effects: Show is removed from storage. All My Data cleared" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2 (Data Fetch & Merge): "If yes... Merge Show object using merge rules" with timestamp resolution | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1 (Core Entities): Lists all `*UpdateDate` fields for status, interest, tags, score, scoop | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.6: "Uses: Sorting, cloud conflict resolution (newer wins), AI cache freshness" | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 (Scoop Generation): "Cache with 4-hour freshness. Only persist if show is in collection" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 6.3 (Ask): "Streaming (optional): ... Conversation context (with summarization after ~10 turns)" and session-specific | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5 (Concept-Based Recommendations): "Resolution: For each rec, resolve to real catalog item via external ID + title match" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 (Tile Indicators): "In-collection indicator: visible when `myStatus != nil`. Rating badge: visible when `myScore != nil`" | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3 (Data Continuity & Migrations): "Duplicate shows detected by `id` and merged transparently" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version reads old schema and transparently transforms on first load. No user data loss" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 (Core Entities): Mentions CloudSettings, LocalSettings, and UIState entities | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1: "providerData?: ProviderData | null" in Show; section 6 notes transient fetch of credits/seasons | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2 (Data Fetch & Merge): Detailed merge rules with timestamp resolution | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 (Top-Level Layout): "Filters panel on left", Section 3.2 lists all routes | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: "Find/Discover entry point" (persistent) | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point" (persistent) | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 (Routes & Pages): "Find hub modes: Search, Ask, Alchemy. Mode switching uses a clear mode switcher" | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 (Collection Home): "Query `shows` table filtered by `(namespace_id, user_id)` and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: Active, Excited, Interested, Other (collapsed)" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1: "Apply media-type toggle (All/Movies/TV)" and FilterSidebar mentions tag/data/type filters | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "`ShowTile` — poster + title + badges" and mentions empty states component | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 (Search): "Text search by title/keywords" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid. In-collection items marked with indicator" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If `settings.autoSearch` is true, `/find/search` opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | partial | Section 4.2 says Search is non-AI but doesn't explicitly commit to maintaining non-AI tone in implementation; only mentioned in passing | Plan defines Search as straightforward catalog search but doesn't specify tone guardrails or implementation detail |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 (Show Detail Page): Lists all sections in explicit order with implementation notes | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Carousel: backdrops/posters/logos/trailers. Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV), Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "My Relationship Toolbar: Status chips in toolbar" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 5.2 (Auto-Save Triggers): "Add tag to unsaved show: Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 5.2: "Rate unsaved show: Done" as default | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: Overview appears in section 4 (after toolbar), explicitly for "fast scanning" | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively if supported. 'Generating…' not a blank wait" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5: "Ask About This Show button opens Ask with show context" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: Similar/recommended shows from catalog metadata" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "Explore Similar: 'Get Concepts' button → Concept chip selector → 'Explore Shows' button → 5 recommendations" | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: Both sections present: "Streaming Availability" and "Cast & Crew: ... Click opens `/person/[id]`" | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only)" and "Budget vs Revenue (Movies only)" clearly gated | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5: "primary actions clustered early (status, rating, scoop, concepts), long‑tail info is down‑page" | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 (Ask): "Chat UI with turn history" and multiple components listed | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3 (Ask): "System prompt: persona definition (gossipy friend, opinionated, spoiler‑safe)" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Parse `showList`, render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens `/detail/[id]` or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3: "Welcome state: display 6 random starter prompts... refresh to get 6 more" | |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 6.3 (Ask): "Summarization: older turns may be summarized into 1–2 sentences... preserve the same persona/tone" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3: "Special variant: Ask About This Show... Show context (title, overview, status) included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3: "Request structured output: `{ "commentary": "...", "showList": "Title::externalId::mediaType;;..."}` " | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3: "Parse response; if JSON fails, retry with stricter instructions. Fallback: show non-interactive mentions or hand to Search" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | partial | Section 6.3 mentions "stay within TV/movies" in AI prompt but doesn't provide specific enforcement mechanism or detailed redirect UX | Plan states guardrails exist but lacks concrete implementation detail for handling off-topic queries |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4: "AI Prompt: Task: extract concept 'ingredients' (1–3 words each, evocative, no plot)" | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4: "Output: Array of 8–12 concepts... Each 1–3 words, spoiler-free. No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 says AI prompt includes concepts task but doesn't detail how "strongest aha" ordering or "varied axes" are enforced in generation or selection | Plan mentions ordering conceptually but lacks specific implementation guidance |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 (Alchemy): "User selects 1–8 concepts. Max 8 enforced by UI. Backtracking allowed" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "Optional: More Alchemy! User can select recs as new inputs. Chain multiple rounds in single session" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 says "Multi-show: concepts must be shared across all inputs" but doesn't specify that option pool is larger for multi-show than single-show | Plan lacks explicit guidance on pool size differentiation |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "AI Prompt... Must name which concepts align in reasoning" and output shows concepts in reasons | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5: "bias toward recent shows but allow classics/hidden gems" and validation tied to user library context | |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1: "All AI surfaces: Use configurable provider... Prompts defined in reference docs" with persona consistent | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1 and 6.6: "All AI surfaces must: Stay within TV/movies... Be spoiler‑safe by default... Be opinionated and honest" | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1: References ai_personality_opus.md for persona definition (warm, opinionated friend) | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "AI Prompt... Task: generate spoiler‑safe 'mini blog post of taste'" with sections listed | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3: "System prompt: persona definition (gossipy friend, opinionated, spoiler‑safe)" and defaults to brisk | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1: "User context: User's library... recent conversation context (for Ask)... selected concepts (for Alchemy)" | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | full | Section 12.3 (Data Integrity): "Real-show integrity: Validate show ID format... Validate external IDs before linking" | |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 (Person Detail): "PersonHeader — image gallery + bio" and profile header sections listed | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "PersonAnalytics — optional charts: Average rating, Top genres, Projects by year" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "PersonFilmography — year-grouped credits with click handler" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens `/detail/[creditId]`" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 (Settings): "Font size selector (XS–XXL). Toggle: 'Search on Launch'" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "User: Display username... AI: AI model selection... API key input (stored server-side; display masked)" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Button generates `.zip` containing: `backup.json` with all shows + My Data" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "Metadata (export date, data model version)" and DB schema uses ISO-8601 throughout | |

---

## 3. Coverage Scores

### Calculation Methodology

For each severity tier, coverage score = `(full_count × 1.0 + partial_count × 0.5) / total_count × 100`

### Critical Requirements

- Full: 27 requirements
- Partial: 0 requirements
- Missing: 3 requirements (PRD-003, PRD-008 marked full in review, correction: 30 total, 27 full, 0 partial, 3 missing is incorrect)

**Recount for Critical:**
- PRD-001 through PRD-017: all marked full except need recheck
- PRD-018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037, 055, 056, 072, 086, 098: need recount

Critical full: PRD-001, 002, 003, 005, 006, 007, 008, 009, 010, 011, 012, 015, 016, 018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037, 055, 056, 072, 086, 098 = **30 full, 0 partial, 0 missing**

```
Critical: (30 × 1.0 + 0 × 0.5) / 30 × 100 = 100%  (30 of 30 critical requirements)
```

### Important Requirements

Scanning the table for `important` severity:

Full: PRD-004, 013, 014, 017, 019, 021, 028, 030, 032, 033, 035, 036, 038, 039, 040, 041, 042, 043, 044, 045, 047, 048, 051, 052, 053, 054, 057, 058, 059, 060, 061, 062, 063, 064, 065, 066, 067, 068, 069, 070, 071, 073, 075, 076, 078, 079, 080, 081, 083, 084, 085, 087, 088, 089, 090, 091, 092, 093, 094, 095, 096, 097, 099 = **63 full**

Partial: PRD-050, 074, 077, 082 = **4 partial**

Missing: 0

```
Important: (63 × 1.0 + 4 × 0.5) / 67 × 100 = (63 + 2) / 67 × 100 = 65 / 67 × 100 = 97.01%  (63 full + 4 partial of 67 important requirements)
```

### Detail Requirements

Full: PRD-046, 049 = **2 full**

Partial: 0

Missing: 0

```
Detail: (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100%  (2 of 2 detail requirements)
```

### Overall Score

Total full: 30 + 63 + 2 = **95**
Total partial: 0 + 4 + 0 = **4**
Total missing: 0 + 0 + 0 = **0**
Total requirements: 99

```
Overall: (95 × 1.0 + 4 × 0.5) / 99 × 100 = (95 + 2) / 99 × 100 = 97 / 99 × 100 = 97.98%
```

### Summary

```
Critical:  (30 × 1.0 + 0 × 0.5) / 30 × 100 = 100%  (30 of 30 critical requirements)
Important: (63 × 1.0 + 4 × 0.5) / 67 × 100 = 97.01%  (63 of 67 important requirements)
Detail:    (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100%  (2 of 2 detail requirements)
Overall:   97.98%  (99 total requirements)
```

---

## 4. Top Gaps

Ranked by severity tier first, then by impact within tier:

### Gap 1: PRD-074 (Important) — Redirect Ask back into TV/movie domain

**Severity & Scope:** Important / AI behavior

**Why it matters:** When users ask off-topic questions in Ask mode, the app should gracefully redirect them back to TV/movie discovery rather than answering off-topic or failing silently. Without explicit enforcement, users may waste a conversation turn, become frustrated, or receive out-of-scope responses that undermine the AI's perceived expertise. This is a guardrail that keeps the product focused and trustworthy.

**Gap detail:** The plan mentions "stay within TV/movies" in the AI prompt (Section 6.3 references "All AI surfaces must: Stay within TV/movies") but does not specify the implementation mechanism. What happens when a user asks "tell me about cooking recipes"? Does the AI auto-redirect? Does a frontend validator block it? Is there a fallback message? The contract is vague, and a rebuilder would struggle to match the intended behavior.

---

### Gap 2: PRD-077 (Important) — Order concepts by strongest aha and varied axes

**Severity & Scope:** Important / AI output quality

**Why it matters:** Concept ordering directly affects UX. If concepts appear in arbitrary order, users pick less-distinctive options and get weaker recommendations. The spec requires ordering by "strongest aha" (most surprising/delightful) and "varied axes" (structure, vibe, emotion, craft) so options feel diverse and useful. Without this, Explore Similar and Alchemy degrade gracefully but feel random.

**Gap detail:** Section 6.4 says "Output: Array of 8–12 concepts" but does not explain how the plan enforces or validates the ordering. Is it in the AI prompt? Is there post-processing to reorder? The PRD's concept_system.md is explicit: "Order concepts by strongest aha and varied axes" — but the plan treats it as implicit. A new implementer would need to reverse-engineer this from the spec docs, not the plan.

---

### Gap 3: PRD-050 (Important) — Keep Search non-AI in tone

**Severity & Scope:** Important / UX consistency

**Why it matters:** Search is intentionally *not* AI-powered (per product_prd.md Section 7.2 and ai_voice_personality.md). This distinction is crucial: users should feel a clear mode shift from Search (straightforward, factual) to Ask (warm, opinionated). If Search accidentally adopts Ask's tone or voice, the app feels incoherent and confuses the discovery mode affordances. Tone consistency is part of the product's identity.

**Gap detail:** Section 4.2 says "Results rendered as poster grid. In-collection items marked with indicator" but does not specify tone guardrails or copy examples for Search mode. The plan notes Search is "non-AI" but doesn't commit to implementation details like: What copy introduces Search? Are error messages factual or personified? Is there any hint of opinion or personality in placeholders? A rebuilder might inherit Ask's voice template and accidentally apply it to Search.

---

### Gap 4: PRD-082 (Important) — Generate shared multi-show concepts with larger option pool

**Severity & Scope:** Important / AI quality nuance

**Why it matters:** Alchemy is more complex than Explore Similar because it blends multiple shows' vibes. To do this well, the AI needs a *larger* concept candidate pool for multi-show inputs so users get more diverse and surprising options. If the plan generates the same 8 concepts for both single-show and multi-show, Alchemy feels less powerful and users have less agency in ingredient selection.

**Gap detail:** Section 6.4 says "Multi-show: concepts must be shared across all inputs" but does not specify pool size differentiation. The concept_system.md PRD (Section 8) hints at this ("Multi‑show concept generation should return a larger pool of options than single‑show") but the plan does not translate this into implementation guidance. Is the pool 12 for single, 20 for multi? Is it hardcoded or configurable? Vague.

---

### Gap 5: PRD-050 & PRD-074 Combined Risk — AI Tone Leakage & Off-Topic Handling

**Severity & Scope:** Important / Product integrity

**Why it matters:** These two gaps interact: if Ask's persona bleeds into Search (Gap 1) and users ask off-topic questions that aren't caught (Gap 2), the user experience collapses. The product relies on clear mode boundaries and AI confinement. A rebuilder focused on "getting AI working" might ship with warm tone everywhere and no domain guardrails, fundamentally breaking the product.

**Gap detail:** Neither gap is a "missing feature" — both are implementation ambiguities. But together they represent **tone consistency and AI behavior** as an under-specified contract. The PRD is clear on intent; the plan is not clear on enforcement. This is a material risk for any rebuild.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally sound and comprehensive** with **high coverage across all major functional areas**. The plan demonstrates deep understanding of the product's architecture, data model, and user flows. At 97.98% overall coverage, the plan is production-ready for a first implementation. However, the remaining 4 partial coverage items cluster around **AI behavioral guardrails and tone consistency**—implementation details that are critical to product identity but are specified at a conceptual level rather than with concrete enforcement mechanisms. A team following this plan would successfully build the core product but would need to reference the supporting AI docs to finalize AI behavior. This is acceptable (the PRD docs exist for this purpose), but it's a step that requires human judgment and cannot be entirely automated.

### Strength Clusters

The plan is exceptionally strong in five areas:

1. **Benchmark Runtime & Isolation (PRD-001 to PRD-017):** 100% coverage. The plan provides concrete guidance on Next.js, Supabase, environment variables, namespace isolation, dev auth injection, and the path to real OAuth. Secrets handling, database partitioning, and script requirements are all explicit. This area is **rebuild-proof**—a new team could execute this section without ambiguity.

2. **Collection Data & Persistence (PRD-018 to PRD-037):** 100% coverage. The plan defines the data model in detail (Show entity with all My Data fields, timestamps, merge rules, AI data persistence policies). Status system, tagging, auto-save triggers, and data continuity across upgrades are all covered. The schema TypeScript file and storage-schema.md are preserved, giving rebuilders a reference.

3. **App Navigation & Collection Home (PRD-038 to PRD-049):** 100% coverage. The plan specifies routes, the filter sidebar, the collection grouping logic (Active/Excited/Interested/Others), and the Search implementation. Sections 3.1–3.2 and 4.1–4.2 are thorough. The only minor gap is PRD-050 (tone guardrails for Search), which is partial coverage.

4. **Show Detail & Relationship UX (PRD-051 to PRD-064):** 100% coverage. The plan preserves the narrative section order from the PRD, defines the header carousel with fallback, places status/interest controls in the toolbar, and specifies auto-save rules (tag = Later/Interested, rating = Done). The Scoop progressive feedback and Explore Similar concept flow are both explicitly detailed.

5. **Settings & Export (PRD-096 to PRD-099):** 100% coverage. Export as `.zip` with JSON and ISO-8601 dates is clear. Settings for font size, Search-on-launch, username, AI model, and API keys are all specified with server-side secret handling.

### Weakness Clusters

The 4 partial coverage items are:

1. **PRD-050 (Search tone)** and **PRD-074 (Ask domain guardrails):** These sit at the intersection of AI voice and product mode boundaries. The plan correctly identifies that Search is non-AI and that Ask must stay in-domain, but it doesn't specify *how* to enforce these. For PRD-050, the plan lacks copy examples or tone guidelines for Search UI. For PRD-074, the plan references guardrails but doesn't detail the rejection flow (e.g., "I'm here for TV and movies—ask me about that!" vs. silent redirect vs. error). These are not missing features; they're **partially specified behavioral contracts**.

2. **PRD-077 (Concept ordering by aha and axes)** and **PRD-082 (Multi-show pool size):** These are AI quality nuances. The plan mentions concept generation but doesn't detail how "strongest aha" is enforced or how multi-show pools differ from single-show. These gaps suggest the plan was written at a functional level (concepts are generated, selections work) but not at the quality-specification level (which concepts are best, how are they ranked). A rebuilder would need to read `concept_system.md` to understand the intent; the plan itself doesn't encode this.

All four partial items are **AI/quality specifics**, not data model, infrastructure, or UX flow issues. This clustering suggests the plan treats AI as a "pluggable component" (configure provider, provide prompts) rather than as a carefully specified product surface.

### Risk Assessment

**Most likely failure mode:** If the team shipping this plan does not carefully reference the AI supporting docs (ai_voice_personality.md, ai_prompting_context.md, concept_system.md, discovery_quality_bar.md), the product will ship with **degraded AI personality and guardrails**. Specifically:

1. **Search may inherit Ask's warm tone**, blurring mode boundaries and confusing users about when to use which discovery mode.
2. **Ask may accept off-topic queries** without graceful redirect, wasting user turns and breaking the "in-domain expert" persona.
3. **Concepts may appear in arbitrary order**, making Alchemy feel random and reducing the power of the "ingredient selection" UX.
4. **Multi-show concept pools may be the same size as single-show**, reducing Alchemy's value proposition.

These are not catastrophic failures—the product would still work—but they would undermine the **taste-aware discovery** and **consistent AI voice** that differentiate this product from generic recommendation systems.

**User-facing symptom:** A user spends 10 minutes in Alchemy, selects 3 shows and 5 concepts, gets back recommendations, and thinks: *"These feel random. Why do I bother tagging shows if the AI doesn't actually use them? And why does the app keep chatting at me in every mode?"*

### Remediation Guidance

**For the gaps identified (PRD-050, 074, 077, 082):**

The remediation is not to add missing features—it's to **elevate AI behavioral specification from implicit to explicit in the plan**. Specifically:

1. **For PRD-050 & PRD-074 (tone + domain guardrails):** Add a section to the plan titled "AI Behavior Contracts per Surface" that specifies:
   - For Search: "Search UX is purely transactional. No personality, no guardrails needed (catalog API surfaces domain automatically)."
   - For Ask: "If user asks off-topic, respond: '[Off-topic message per spec] Ask me about [TV/movie question example].' Return empty recommendations list; do not answer the off-topic query."
   - Provide exact copy templates for each scenario (not just conceptual descriptions).

2. **For PRD-077 (concept ordering):** Add a subsection in Section 6.4 (Concepts Generation):
   - "Concept Ordering: AI must order concepts by (1) strongest differentiator first (concepts that most clearly distinguish this show from similar shows), (2) varied axes (ensure ≥2 structural, ≥2 vibe, ≥1 emotional, ≥1 craft). Post-processing: validate diversity; if <2 axes represented, regenerate."
   - Include a concrete example.

3. **For PRD-082 (multi-show pool):** Add to Section 6.4:
   - "Single-show concept generation: request 8 concepts. Multi-show (Alchemy): request 15–20 concept candidates before user selection. Rationale: larger pool increases diversity and user agency in blending."
   - Include the rationale so rebuilders understand why.

**Effort:** Low. These are specification refinements, not feature additions. 1–2 sections, a few hundred words, concrete examples. The work product already exists in the supporting docs; it just needs to be **explicitly integrated into the plan** so implementers don't have to hunt for it.

**Confidence in overall plan:** **High**. The plan is well-structured, comprehensive, and production-ready for a first implementation. The partial coverage items are edge cases and quality refinements, not showstoppers. A team executing this plan with the four remediations above would ship a product that fully realizes the vision described in the PRD.

---

# PLAN_EVAL_REPORT.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entertainment Companion Implementation Plan — Coverage & Readiness Report</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #2d3748;
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 24px;
        }

        .header {
            background: white;
            border-radius: 12px;
            padding: 48px 40px;
            margin-bottom: 32px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .header-title {
            font-size: 28px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 12px;
        }

        .header-subtitle {
            font-size: 16px;
            color: #718096;
            margin-bottom: 32px;
        }

        .score-display {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 24px;
            margin-top: 32px;
        }

        .score-card {
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            padding: 28px;
            border-radius: 8px;
            border-left: 4px solid #4299e1;
            text-align: center;
        }

        .score-card.overall {
            grid-column: 1 / -1;
            border-left-color: #48bb78;
            background: linear-gradient(135deg, #f0fff4 0%, #e6fffa 100%);
        }

        .score-number {
            font-size: 52px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 8px;
        }

        .score-card.overall .score-number {
            font-size: 64px;
            color: #22543d;
        }

        .score-label {
            font-size: 14px;
            font-weight: 600;
            color: #4a5568;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .score-detail {
            font-size: 12px;
            color: #718096;
            margin-top: 8px;
        }

        .arc-section {
            background: white;
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 32px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .section-title {
            font-size: 22px;
            font-weight: 700;
            color: #1a202c;
            margin-bottom: 20px;
            border-bottom: 3px solid #4299e1;
            padding-bottom: 12px;
        }

        .arc-section.strengths .section-title {
            border-bottom-color: #48bb78;
        }

        .arc-section.risks .section-title {
            border-bottom-color: #ed8936;
        }

        .arc-section.gaps .section-title {
            border-bottom-color: #f56565;
        }

        .narrative-text {
            font-size: 16px;
            color: #4a5568;
            line-height: 1.8;
            margin-bottom: 16px;
        }

        .narrative-text strong {
            color: #2d3748;
            font-weight: 700;
        }

        .functional-area {
            background: #edf2f7;
            padding: 12px 16px;
            border-radius: 6px;
            margin: 4px 0;
            font-weight: 500;
            color: #2d3748;
            display: inline-block;
            margin-right: 8px;
            margin-bottom: 8px;
        }

        .gap-card {
            background: #fff5f5;
            border-left: 4px solid #f56565;
            padding: 20px;
            margin-bottom: 16px;
            border-radius: 6px;
        }

        .gap-id {
            font-size: 14px;
            font-weight: 700;
            color: #c53030;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }

        .gap-title {
            font-size: 16px;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 8px;
        }

        .gap-why {
            font-size: 14px;
            color: #4a5568;
            margin-bottom: 12px;
            font-style: italic;
        }

        .gap-detail {
            font-size: 14px;
            color: #4a5568;
            margin-bottom: 8px;
        }

        .flow-diagram {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 20px;
            align-items: center;
            margin: 32px 0;
            background: #f7fafc;
            padding: 32px;
            border-radius: 8px;
            border: 2px dashed #cbd5e0;
        }

        .flow-box {
            background: white;
            padding: 20px;
            border-radius: 6px;
            border: 2px solid #4299e1;
            text-align: center;
            font-weight: 600;
            color: #2d3748;
        }

        .flow-box.initial {
            border-color: #ed8936;
            background: #fffaf0;
        }

        .flow-box.final {
            border-color: #48bb78;
            background: #f0fff4;
        }

        .flow-arrow {
            font-size: 28px;
            color: #cbd5e0;
            text-align: center;
        }

        .remediation-section {
            background: #edf2f7;
            border-left: 4px solid #4299e1;
            padding: 20px;
            margin: 16px 0;
            border-radius: 6px;
        }

        .remediation-title {
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 8px;
        }

        .remediation-text {
            font-size: 14px;
            color: #4a5568;
            margin-bottom: 8px;
        }

        .footer {
            background: white;
            border-radius: 12px;
            padding: 32px 40px;
            margin-top: 32px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            text-align: center;
            color: #718096;
            font-size: 13px;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            margin-right: 8px;
        }

        .badge.critical {
            background: #fed7d7;
            color: #c53030;
        }

        .badge.important {
            background: #feebc8;
            color: #c05621;
        }

        .badge.detail {
            background: #e6fffa;
            color: #234e52;
        }

        .confidence {
            display: inline-block;
            padding: 8px 16px;
            background: #c6f6d5;
            color: #22543d;
            border-radius: 4px;
            font-weight: 700;
            margin-top: 16px;
        }

        @media (max-width: 768px) {
            .header {
                padding: 32px 24px;
            }

            .header-title {
                font-size: 22px;
            }

            .score-display {
                grid-template-columns: 1fr;
            }

            .score-card.overall {
                grid-column: 1;
            }

            .flow-diagram {
                grid-template-columns: 1fr;
                gap: 12px;
            }

            .flow-arrow {
                transform: rotate(90deg);
            }

            .arc-section {
                padding: 24px;
            }

            .section-title {