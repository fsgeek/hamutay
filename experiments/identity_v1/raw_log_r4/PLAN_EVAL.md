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
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable) — app runtime, server-side logic, API routes" |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "Client libraries — @supabase/supabase-js (anon/public key for browser)" |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: Complete `.env.example` template provided with all required variables |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: "`.gitignore` excludes `.env*` (except `.env.example`)" |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "All secrets injected at runtime" and `.env.example` structure |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 10.1: "API keys never committed" and Section 8.3: "API keys stored as environment variables" |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4: Lists `npm run dev`, `npm run test`, `npm run test:reset`, etc. |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2: "Supabase migrations idempotent + reversible" and Section 10.4 `npm run db:push` |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.1, 2.2: Explicit namespace per build with `namespace_id` in all data structures |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2: `/api/test/reset` scoped to namespace; Section 10.3: "Each build operates only within its namespace" |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2: All tables include `user_id` field; Section 8.1: "user_id scopes all data" |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: "Partition: `(namespace_id, user_id)`"; RLS policies enforce this |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: "Middleware checks `process.env.NODE_ENV === 'development'`; disabled in production" |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "Schema unchanged; Business logic unchanged" when migrating to OAuth |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance" |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 6.1, 13.1: "It MUST be safe to clear local storage… without losing user-owned data" |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly" |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1: "Display rule: Whenever a show appears anywhere, if user has saved version, display user-overlaid version" |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3: "Next — hidden 'up next' (data model only, not first-class UI yet)" |  |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2, 5.3: "Select Interested/Excited | Later | Interested/Excited | Both map to Later status" |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.1: "`myTags` (free-form user labels + timestamp)" and filtering by tag |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is 'in collection' when `myStatus != nil`" |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2: Table lists all save triggers (status, interest, rating, tagging) |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: "Default save to Later/Interested except rating-save Done" |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Removing status → modal confirmation → clears all My Data" |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 2.3: "Merge rules: preserve user fields by timestamp, refresh public data" |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.2: Shows schema with all `*UpdateDate` fields on `shows` table |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5: "For each field, keep the value with newer timestamp" |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2: "Cache with 4-hour freshness; Only persist if show is in collection" |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6: "Ask chat history: No, Session only; Alchemy concepts/results: No, Session only" |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5: "For each rec, resolve to real catalog item via external ID + title match" |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator: visible when `myStatus != nil`; Rating badge: visible when `myScore != nil`" |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3: "Merge rules… Duplicate shows detected by `id` and merged transparently" |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "Automatic schema migration on app boot if `dataModelVersion` mismatch detected" |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 4.1: Includes CloudSettings, LocalSettings, UIState entity descriptions |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1: Describes `providerData` (persisted) vs transient fetch fields |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2: "Merge rules: Non-user fields use selectFirstNonEmpty; User fields resolve by timestamp" |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: Layout shows "Filters panel on left" with All Shows, tag, data filters |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: "Find/Discover entry point" and 3.2 routes confirm `/find` |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point" and 3.2 routes confirm `/settings` |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2: `/find/search`, `/find/ask`, `/find/alchemy` routes all present |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query `shows` table filtered by `(namespace_id, user_id)` and selected filter" |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: 1. Active 2. Excited 3. Interested 4. Other (collapsed)" |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | partial | Section 4.1 lists filters but does not detail genre, decade, score range implementation; media toggle mentioned only briefly |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "`EmptyState` — when no shows match filter" |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text input sends query to `/api/catalog/search`" |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid; In-collection items marked with indicator" |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If `settings.autoSearch` is true, `/find/search` opens on app startup" |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: "Search is straightforward catalog search experience" (no AI voice mentioned) |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: Lists all 12 sections in exact order required by PRD |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Carousel: backdrops/posters/logos/trailers; Fall back to static poster" |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV); Community score bar" |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "My Relationship Toolbar: Status chips: Active/Interested/Excited/Done/Quit/Wait" |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5: "Auto-save behaviors: Adding tag on unsaved show: auto-save as Later + Interested" |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5: "Auto-save behaviors: Setting rating on unsaved show: auto-save as Done" |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: "Overview + Scoop: Overview text (factual)" appears early in section order |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively if supported; 'Generating…' feedback" |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.3: "Show context (title, overview, status) included in initial system prompt" |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: Similar/recommended shows from catalog metadata" |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "'Get Concepts' button → Concept chip selector → 'Explore Shows' button" |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: "Streaming Availability; Cast & Crew: Horizontal strands → Click opens `/person/[id]`" |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only); Budget vs Revenue (Movies only)" |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | partial | Section 4.5 lists sections but does not discuss visual hierarchy or clutter mitigation beyond section order |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history; User messages sent to `/api/chat`" |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 4.3: "Server calls AI with taste-aware prompt… AI response includes commentary" |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Render mentioned shows as horizontal strand (selectable)" |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens `/detail/[id]` or triggers detail modal" |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3: "On initial Ask launch, display 6 random starter prompts… User can refresh to get 6 more" |  |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3: "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated); Preserve feeling/tone" |  |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3: "Ask About This Show: Button on Detail page opens Ask with pre-seeded context" |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3: "Request structured output: `{commentary, showList: 'Title::externalId::mediaType;;…'}`" |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | partial | Section 6.3 states "if JSON fails, retry with stricter instructions; otherwise fall back" but does not specify "once" or detail retry behavior |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | missing | No explicit handling of off-domain requests or redirection logic described |  |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 4.4, 6.4: "Return bullet-only, 1-3 word, evocative, spoiler-free; No generic placeholders" |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 4.4: "Array of 8–12 concepts (or smaller for single show); Each 1–3 words, spoiler-free; No generic placeholders" |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 says "Do not cache (concepts are session-specific)" but does not specify ordering or axis diversity requirements |  |
| PRD-078 | Require concept selection and guide ingredient picking | important | partial | Section 4.4 describes selection UI but does not detail "ingredient picking" guidance copy or UX affordances |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Counts: Explore Similar: 5 recs per round" |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "Flow: … 5. Optional: More Alchemy! … Chain multiple rounds in single session" |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 mentions "Do not cache… concepts are session-specific" but does not specify larger pool generation for multi-show |  |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "reasons should explicitly reflect the selected concepts" and "Counts: Alchemy: 6 recs per round" |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5 states "resolve to real catalog item" but does not describe "surprising but defensible" heuristics or taste alignment validation |  |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1: "All surfaces share one persona, but with surface-specific adaptations" |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 6.1 states "Prompts defined in reference docs" but does not specify enforcement mechanism or guardrail validation |  |
| PRD-087 | Make AI warm, joyful, and light in critique | important | partial | Plan references ai_personality_opus.md but does not embed or enforce voice pillars; tone is delegated to prompts |  |
| PRD-088 | Structure Scoop as personal taste mini-review | important | partial | Section 6.2 says "structured as a short 'mini blog post of taste'" but does not specify section structure (personal take, stack-up, Scoop paragraph, fit/warnings, verdict) |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | partial | Section 4.3, 6.3 describe Ask behavior but do not enforce "brisk" default or dialogue patterns; delegated to prompts |  |
| PRD-090 | Feed AI the right surface-specific context inputs | important | partial | Section 6.1 lists "User context" but does not detail surface-specific context contracts or what constitutes "right" |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | missing | No acceptance criteria, QA process, or validation rubric for AI output quality described |  |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Profile Header: Image gallery (primary image + thumbs); Name, bio" |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics: Average rating of projects; Top genres by count; Projects by year (bar chart)" |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable" |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens `/detail/[creditId]`" |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "App Settings: Font size selector (XS–XXL); Toggle: 'Search on Launch'" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "User: Display username; AI: AI provider/model selection; API key input (stored server-side)" |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export / Backup: Button generates `.zip` containing: `backup.json` with all shows + My Data" |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "Export dates: ISO-8601" |  |

---

## 3. Coverage Scores

### Overall Coverage Calculation

**Formula:**
```
score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100
```

**Counts:**
- Full: 82
- Partial: 12
- Missing: 5
- Total: 99

**Calculation:**
```
(82 × 1.0 + 12 × 0.5) / 99 × 100
= (82 + 6) / 99 × 100
= 88 / 99 × 100
= 88.9%
```

### Coverage by Severity Tier

**Critical Requirements (30 total):**
- Full: 27
- Partial: 2
- Missing: 1
- Score: (27 × 1.0 + 2 × 0.5) / 30 × 100 = 28 / 30 × 100 = **93.3%** (27 of 30 critical requirements)

**Important Requirements (67 total):**
- Full: 53
- Partial: 10
- Missing: 4
- Score: (53 × 1.0 + 10 × 0.5) / 67 × 100 = 58 / 67 × 100 = **86.6%** (58 of 67 important requirements)

**Detail Requirements (2 total):**
- Full: 2
- Partial: 0
- Missing: 0
- Score: (2 × 1.0 + 0 × 0.5) / 2 × 100 = 2 / 2 × 100 = **100%** (2 of 2 detail requirements)

### Final Scores

```
Critical:  (27 × 1.0 + 2 × 0.5) / 30 × 100 = 93.3%  (27 of 30 critical requirements)
Important: (53 × 1.0 + 10 × 0.5) / 67 × 100 = 86.6%  (58 of 67 important requirements)
Detail:    (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100%    (2 of 2 detail requirements)
Overall:   (82 × 1.0 + 12 × 0.5) / 99 × 100 = 88.9%  (99 total requirements)
```

---

## 4. Top Gaps

### Gap 1: PRD-086 | `critical` | Enforce shared AI guardrails across all surfaces

**Why this matters:**
The plan states prompts are "defined in reference docs" but provides no mechanism for enforcing guardrails (spoiler-safety, domain stay, honesty about mixed reception, specificity). Without runtime validation or test gates, a prompt change could silently violate the product's AI voice contract, breaking user trust across all AI surfaces simultaneously.

### Gap 2: PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity

**Why this matters:**
The plan lists no acceptance criteria for AI output quality or real-show integrity validation. Discovery Quality Bar (discovery_quality_bar.md) defines a scoring rubric and hard-fail for real-show integrity (must be 2/2), but the plan does not describe how this rubric is integrated into QA/testing. Without this, bad recommendations or hallucinated shows could ship undetected.

### Gap 3: PRD-074 | `important` | Redirect Ask back into TV/movie domain

**Why this matters:**
The plan states AI must "stay within TV/movies (redirect back if asked to leave)" but provides no explicit handling for off-domain requests. If a user asks about cooking or politics, the plan does not specify whether the AI refuses, redirects, or silently fails. This is a product-level expectation that should be testable.

### Gap 4: PRD-044 | `important` | Support All, tag, genre, decade, score, media filters

**Why this matters:**
The plan lists genre, decade, and score filters in Collection Home but does not detail implementation: how are genre/decade/score ranges stored, filtered, or displayed? Are these UI multi-selects, sliders, or predefined ranges? Without this specificity, a builder may implement genre filters that don't work as intended.

### Gap 5: PRD-064 | `important` | Keep primary actions early and page not overwhelming

**Why this matters:**
The plan preserves section order and lists sections but provides no visual hierarchy strategy or clutter mitigation rules. It does not specify font sizes, spacing, fold-lines, or progressive disclosure to ensure the Detail page feels "powerful but not overwhelming" as intended. This is delegated to UI design without architectural guidance.

---

## 5. Coverage Narrative

### Overall Posture

This plan is a **strong, production-ready blueprint** with comprehensive coverage of functional requirements (89% overall) and excellent coverage of critical infrastructure (93%). The plan provides concrete implementation tasks, database schema, API contracts, and architectural principles that align with the PRD's vision. However, it treats AI behavior (voice, guardrails, quality validation) as primarily a prompt/documentation concern rather than an architectural one, leaving gaps in how voice consistency, output validation, and guardrail enforcement are operationalized during builds. A new team could implement this plan successfully, but would need to make independent decisions about AI quality gates and voice preservation that could drift from the intended experience.

### Strength Clusters

**Functional Areas:**
- **Benchmark Runtime & Isolation** — 100% coverage. The plan provides exhaustive detail on environment variables, namespace/user partitioning, auth injection, database schema, and destructive testing. This is the strongest area and meets the infrastructure rider perfectly.
- **Collection Data & Persistence** — 95% coverage (PRD-037 full). Status system, auto-save triggers, timestamps, merge rules, and data continuity are all specified concretely. The show overlay rule is clear everywhere.
- **Show Detail & Relationship UX** — 93% coverage (1 partial on visual hierarchy). Section order is preserved, all controls described, auto-save behaviors explicit. The plan even addresses TV/movie-specific gating.
- **Settings & Export** — 100% coverage. Font size, Search-on-launch, username, model selection, API key storage, and export zip structure are all fully specified.
- **Collection Home & Search** — 88% coverage (1 partial on genre/decade/score detail). Status grouping, media toggle, filter sidebar, search grid, and auto-launch are clear. Only filter implementation specifics are glossed over.

### Weakness Clusters

**Pattern 1: AI Behavior Delegated to Prompts (8 partial/missing across AI Voice + Ask Chat + Concepts areas)**

Requirements PRD-073, PRD-074, PRD-077, PRD-078, PRD-082, PRD-086, PRD-087, PRD-088, PRD-089, PRD-090 all address AI persona, guardrails, concept quality, and voice consistency. The plan states these are "defined in reference docs" and "configured in prompts" but does not describe:
- How guardrails are validated before/after deployment
- How voice consistency is tested across model changes
- How concept ordering (strongest aha first) is enforced
- How off-domain requests (e.g., cooking) are redirected
- How discovery quality rubric is integrated into CI/CD

This creates a deployment risk: a prompt change or model swap could silently violate guardrails, and there is no described gate to catch it.

**Pattern 2: AI Output Validation Missing (PRD-091)**

The discovery_quality_bar.md spec defines a strict rubric (voice, taste alignment, real-show integrity hard-fail), but the plan does not describe:
- How hallucinated shows are detected/blocked before UI rendering
- How taste alignment is scored in tests
- Whether spot-checking is manual or automated
- What triggers a re-generation or fallback

Without this, the plan leaves discovery quality to luck rather than design.

**Pattern 3: UI Specificity Gaps (PRD-044, PRD-064, PRD-078)**

Filter implementation, visual hierarchy, and concept guidance copy are mentioned but not detailed. For example:
- PRD-044: Genre/decade/score filters are listed but not specified as multi-select, sliders, or ranges
- PRD-064: "Keep page not overwhelming" is stated but no fold-line, progressive disclosure, or visual hierarchy rules given
- PRD-078: "Guide ingredient picking" is mentioned but no copy, affordances, or UX pattern specified

These gaps require additional design work post-plan.

### Risk Assessment

**If this plan is executed as-is without addressing gaps:**

1. **Most likely failure:** AI output quality degrades silently after model/prompt changes. A user notices Ask recommending non-TV/movie content, or Scoop using generic language ("good characters"), but the guardrail violation was not caught in tests because no validation pipeline exists.

2. **Secondary failure:** Discovery recommendations hallucinate or resolve to wrong shows. Without hard-fail real-show integrity validation in CI/CD, a user might see "Breaking Bad: The Sequel" (not in catalog) rendered as a recommendation card.

3. **Tertiary failure:** UI implementation diverges from intended experience. Without detail on filter UI patterns and visual hierarchy rules, the Detail page becomes cluttered or filters don't work as expected (e.g., genre filter only allows single selection when multi-select was intended).

4. **QA reviewer discovery:** Tester tries to validate AI persona and finds no rubric or automated checks; manual judgment required for every AI output (not scalable).

### Remediation Guidance

**For AI behavior gaps (PRD-073, PRD-074, PRD-077, PRD-082, PRD-086, PRD-087, PRD-088, PRD-089, PRD-090, PRD-091):**
- **Type of work needed:** Architectural specification + CI/CD integration
- **Guidance:** Create an AI Validation Layer document that specifies:
  - Guardrail checks as testable assertions (e.g., "Ask response must match `showList` contract exactly")
  - Off-domain request detection (keyword lists? intent classification?)
  - Concept quality gates (specificity check: reject "good characters", "great writing")
  - Discovery rubric integration (automated real-show validation per recommendation)
  - Prompt versioning and A/B testing strategy
  - Manual spot-check cadence (e.g., QA reviews 10 AI responses per release)

**For UI specificity gaps (PRD-044, PRD-064, PRD-078):**
- **Type of work needed:** Design specification + component stories
- **Guidance:** Create a UI Implementation Guide that specifies:
  - Filter patterns (genre: multi-select chips; decade: range slider; score: range bar; tag: chip list)
  - Detail page visual hierarchy (spacing, typography, fold-line tests at 3 breakpoints)
  - Concept selection guidance copy and placement (inline explainer, empty state nudge)
  - Responsive breakpoints and mobile-vs-desktop layout changes

**For discovery quality validation (PRD-091):**
- **Type of work needed:** QA/testing specification
- **Guidance:** Create a Discovery QA Runbook that specifies:
  - Automated real-show validation: AI recommendation outputs must resolve to catalog items 100%
  - Manual spot-checks: 5-rec sample per release against discovery_quality_bar.md rubric
  - Regression testing: golden set of prompts (Ask, Alchemy, Explore Similar) with expected output patterns
  - Approval gate: no AI surface can deploy without QA sign-off against rubric

---

# Results Summary

**Evaluation Complete**

- **Overall Coverage: 88.9%** (82 full, 12 partial, 5 missing of 99 requirements)
- **Critical Coverage: 93.3%** (27 of 30 met fully)
- **Important Coverage: 86.6%** (53 of 67 met fully)
- **Detail Coverage: 100%** (2 of 2 met fully)

**Strengths:** Infrastructure, persistence, data flow, collection UX, export
**Weaknesses:** AI guardrails/validation, UI specificity, discovery quality gates
**Risk:** Silent AI quality drift; hallucinated recommendations; UI implementation variance