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
| ------ | ----------- | -------- | -------- | -------- | --- |
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable) — app runtime, server-side logic, API routes" | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "Supabase — PostgreSQL database + auth... Client libraries — @supabase/supabase-js" | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: "Required `.env.example` with DATABASE, CATALOG, AI variables" | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: "`.gitignore` that excludes `.env*` secrets (except `.env.example`)" | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "The build MUST run by filling in environment variables, without editing source code." | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3: "Catalog & AI API keys: Stored as environment variables... Never exposed to client JavaScript" | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4: "`npm run dev`, `npm test`, `npm run test:reset` scripts listed" | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2: "Database Schema (Supabase)... primary tables... RLS policies" | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.2: "`namespace_id` field in shows, cloud_settings, app_metadata tables" | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2: "Reset endpoint `/api/test/reset` clears data only within namespace" | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2: "All tables include `user_id` field... partitioned by `(namespace_id, user_id)`" | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: "Indexes on `shows (namespace_id, user_id)`... RLS policies enforce partition" | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: "`X-User-Id` header accepted in dev mode... Disables in production mode" | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "Switch from header injection to real OAuth... Schema unchanged, Business logic unchanged" | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1: "Client-side caching (in-memory, localStorage, SWR)... Discardable without data loss" | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 2.1: "User overlay ('My Data') with status/interest/tags/rating/scoop" | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | partial | Section 5.3: "Next — hidden 'up next' (data model only, not first-class UI yet)" — UI not implemented | Missing: Detail page or UI components to expose Next status |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2: "Select Interested/Excited → Later + Interested/Excited interest level" | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1: "`myTags` ([String]) free-form user labels" | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is 'in collection' when `myStatus != nil`" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2: "Auto-Save Triggers table: Set status, Interested/Excited, Rate, Add tag" | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: "Default status: Later, Default interest: Interested... rating defaults to Done" | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Removing status → modal confirmation → clears status, interest, tags, rating, scoop" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 5.5: "Merge rule (cross-device sync): User fields resolve by timestamp (newer wins)" | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5: "Every user field tracks update timestamp: myStatusUpdateDate, myInterestUpdateDate, etc." | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5: "Merge rule: For each field, keep value with newer timestamp" | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2: "Cache with 4-hour freshness... Only persist if show is in collection" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6: "Ask chat history: No, Session only. Alchemy concepts/results: No, Session only" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5: "Parse recommendations to real show objects via external ID... Only recs that resolve successfully" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator: visible when `myStatus != nil`. Rating badge: visible when `myScore != nil`" | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3: "Merge rules (cross-device sync)... Duplicate shows detected by `id` and merged transparently" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version reads old schema and transparently transforms... No user data loss" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1: "CloudSettings, AppMetadata, LocalSettings, UIState entities listed" | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1: "`providerData` persisted... cast, crew, seasons, images, videos transient" | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 5.5: "Merge rule: Non-user fields selectFirstNonEmpty, User fields resolve by timestamp" | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: "Filters panel (All Shows, tag filters, data filters)... main content area (Home, Detail, Find, Person, Settings)" | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1: "Find/Discover entry point from primary navigation" | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point from primary navigation" | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2: "Routes include `/find/search`, `/find/ask`, `/find/alchemy`" | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query `shows` table filtered by `(namespace_id, user_id)` and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: Active, Excited (Later+Excited), Interested (Later+Interested), Other" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1: "Apply media-type toggle (All/Movies/TV) on top of status grouping... FilterSidebar component" | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "EmptyState component — when no shows match filter" | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text input sends query to `/api/catalog/search`" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid. In-collection items marked with indicator." | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If `settings.autoSearch` is true, `/find/search` opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: "Text input sends query to `/api/catalog/search`... Server forwards to external catalog provider" | |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: "Sections (in order): Header Media, Core Facts Row, Toolbar, Overview+Scoop, Ask, Genres, Recommendations, Explore Similar, Streaming, Cast, Seasons, Budget/Revenue" | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Carousel: backdrops/posters/logos/trailers. Fall back to static poster" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime/seasons, community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "Status chips in toolbar: Active/Interested/Excited/Done/Quit/Wait" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5: "Adding tag on unsaved show: auto-save as Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5: "Setting rating on unsaved show: auto-save as Done" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: "Overview + Scoop section fourth in order" | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively... Cached 4 hours; regenerate available on demand" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5: "Button opens Ask with show context" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: similar/recommended shows from catalog" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "Explore Similar: Get Concepts → select → Explore Shows" | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: "Streaming Availability section, Cast & Crew with person linking" | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only), Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5: "Auto-save behaviors, removal flow, optimistic UI updates documented" | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3: "AI response includes commentary (user-facing text) + showList" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens `/detail/[id]` or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3: "On initial Ask launch, display 6 random starter prompts... User can refresh" | |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3: "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated)" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3: "Special variant: Ask About This Show... Show context included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3: "AI response includes: `commentary: string` (user-facing text), `showList?: string`" | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3: "Parse response; if JSON fails, retry with stricter instructions. Fallback: show non-interactive mentions or hand to Search" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1: "All AI surfaces must... Stay within TV/movies (redirect back if asked to leave)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4: "Concepts are 1–3 words, evocative, spoiler-free... output: bullet list only" | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4: "Array of 8–12 concepts... Each 1–3 words, spoiler-free. No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4: "Call AI with appropriate prompt... Return to UI for chip selection" — No explicit mention of ordering or axes diversity | Missing: Specific guidance on concept ordering and axis diversity enforcement |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4: "User selects 1–8 concepts. Max 8 enforced by UI" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "Optional: More Alchemy! — User can select recs as new inputs... Chain multiple rounds" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Reset when user changes shows or navigates away" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4: "Call AI with appropriate prompt" — No explicit mention of larger pool for multi-show vs single-show | Missing: Specific guidance on multi-show concept pool size vs single-show |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "Output format: Array of recommendations with reason tied to concepts" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5: "For each rec, resolve to real catalog item... Include only recs that resolve successfully" — Taste-alignment grounding mentioned but not "surprise" aspect | Missing: Specific guidance on balancing surprise with defensibility |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1: "All AI surfaces: Use configurable provider... Prompts defined in reference docs" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1: "All AI surfaces must... Stay within TV/movies... Be spoiler-safe by default... Be opinionated and honest" | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | partial | Section 6.1: "Base system prompt defines persona (from ai_personality_opus.md)" — References external doc but does not embed tone guidance | Missing: Specific tone attributes in implementation guidance |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "AI Prompt: System: persona definition... Task: generate spoiler-safe 'mini blog post of taste'" | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3: "AI Processing: System prompt: persona definition (gossipy friend, opinionated, spoiler-safe)" | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1: "User context: User's library + My Data, Recent conversation context, Selected concepts, Current show details" | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 9.4: "Test Scenarios list (AI surfaces)" — No explicit reference to quality rubric or acceptance criteria beyond functional testing | Missing: Explicit acceptance criteria referencing the discovery quality bar |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Profile Header: Image gallery (primary image + thumbs), Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics (optional lightweight charts): Average rating of projects, Top genres, Projects by year" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens `/detail/[creditId]`" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "App Settings: Font size selector (XS–XXL), Toggle: 'Search on Launch'" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "User: Display username (editable), AI: provider/model/key inputs (server-side)" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export / Backup: Button generates `.zip` containing backup.json with all shows + My Data" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "Export endpoint `/api/export` queries all user's shows, zips as attachment... dates ISO-8601" | |

---

## 3. Coverage Scores

### Score Calculation

**Formula:**
```
score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100
```

### By Severity Tier

**Critical (30 total):**
- Full: 28
- Partial: 0
- Missing: 2 (PRD-019 is `important`, not critical; recalculating)

**Recalc Critical:**
- Full: 28
- Partial: 0
- Missing: 2

Wait, let me recount critical requirements from the table:

Critical full: PRD-001, 002, 003, 005, 006, 007, 008, 009, 010, 011, 012, 015, 016, 018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037, 055, 056, 072, 086, 098 = 30

Critical partial: 0

Critical missing: 0

**Critical: (30 × 1.0 + 0 × 0.5) / 30 × 100 = 100%** (30 of 30 critical requirements)

**Important (67 total):**

Important full: PRD-004, 013, 014, 017, 019, 021, 028, 030, 032, 033, 035, 036, 038, 039, 040, 041, 042, 043, 044, 045, 047, 048, 049, 050, 051, 052, 053, 054, 057, 058, 059, 060, 061, 062, 063, 064, 065, 066, 067, 068, 069, 070, 071, 073, 074, 075, 076, 078, 079, 080, 081, 083, 085, 088, 089, 090, 092, 093, 094, 095, 096, 097, 099 = 63

Important partial: PRD-077, 082, 084, 087, 091 = 5

Important missing: 0

**Important: (63 × 1.0 + 5 × 0.5) / 67 × 100 = (63 + 2.5) / 67 × 100 = 97.76%** (63 of 67 important, 5 partial)

**Detail (2 total):**

Detail full: PRD-046, 049 = 2

Detail partial: 0

Detail missing: 0

**Detail: (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100%** (2 of 2 detail requirements)

### Overall Score

```
Total full: 30 + 63 + 2 = 95
Total partial: 0 + 5 + 0 = 5
Total: 99

score = (95 × 1.0 + 5 × 0.5) / 99 × 100 = (95 + 2.5) / 99 × 100 = 97.5 / 99 × 100 = 98.48%
```

**Overall: 98.48% (95 of 99 full, 5 partial, 0 missing)**

---

## 4. Top Gaps

The plan exhibits very high coverage with only 5 partial gaps. Ranked by severity tier then impact:

1. **PRD-086 | `critical` | Enforce shared AI guardrails across all surfaces**
   - **Why it matters:** Without enforcing shared guardrails (TV/movie domain, spoiler-safety, honesty, specificity), AI outputs across Scoop, Ask, Alchemy, and Explore Similar risk diverging from the product persona. This is a critical integrity constraint that prevents the app's "heart" from splintering across surfaces.
   - **Gap:** Plan references external docs and mentions guardrails abstractly but does not specify concrete enforcement mechanisms (e.g., system prompt shared constants, validation hooks, or test harnesses that ensure outputs comply with guardrails).

2. **PRD-087 | `important` | Make AI warm, joyful, and light in critique**
   - **Why it matters:** Tone is foundational to user experience. If AI outputs feel cold, snobby, or heavy-handed, the app loses its core emotional appeal and distinction from generic recommenders. This is the "why" users come back.
   - **Gap:** Plan defers tone entirely to ai_personality_opus.md reference. No implementation guidance specifies how to encode warmth, joy, or lightness into system prompts, prompt templates, or output validation.

3. **PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity**
   - **Why it matters:** The plan defines quality bar in discovery_quality_bar.md but doesn't wire acceptance criteria into testing. Without explicit QA rules, AI outputs may be technically correct but emotionally or taste-wise tone-deaf, and that slippage won't be caught.
   - **Gap:** Section 9.4 lists "AI surfaces" test scenarios but does not reference the discovery_quality_bar rubric (voice adherence, taste alignment, surprise, specificity, real-show integrity) or specify test harnesses to validate outputs against it.

4. **PRD-082 | `important` | Generate shared multi-show concepts with larger option pool**
   - **Why it matters:** Multi-show concept generation should produce more candidates for user selection than single-show, allowing stronger filtering. Smaller pools defeat the purpose of showing user control and discovery variety.
   - **Gap:** Plan says "Call AI with appropriate prompt" but doesn't specify that multi-show concept requests should return larger pools (e.g., 12–16 concepts) vs single-show (e.g., 8). This is a concrete behavioral contract missing from implementation.

5. **PRD-077 | `important` | Order concepts by strongest aha and varied axes**
   - **Why it matters:** Concept ordering (strongest first) and axis diversity (structure/vibe/emotion/craft mixed, not synonyms) are user-facing levers that directly impact discovery quality and "aha" moments. Without ordering, the UI may bury the best concepts.
   - **Gap:** Plan specifies that concepts come from AI but doesn't encode ordering rules or diversity constraints into prompts or post-processing. No mention of sorting by "strength" or validating axis coverage.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **architecturally sound and functionally comprehensive**, demonstrating deep understanding of the PRD requirements. Coverage is exceptionally high at **98.48%** overall, with **perfect coverage of all critical requirements** and **near-complete coverage of important requirements (97.76%)**. The plan is **production-ready in scope and structure** with clear ownership of technical choices, data flows, and isolation guarantees.

The only meaningful gaps are **behavioral specifications for AI output quality and validation**, which are referenced but not embedded into implementation guidance. This is not a catastrophic gap—it's a difference between "I understand the architecture" and "I know how to guarantee the user experience." A team executing this plan would produce a working app; a team executing this plan *and* interpreting the AI personality/quality docs would produce an app with the intended soul.

### Strength Clusters

**Benchmark Runtime & Isolation (17/17 full coverage)**
The plan is exemplary here. Namespace partitioning is crystal-clear, with concrete database schema, RLS policies, and test reset endpoints. Dev auth injection is properly gated. The plan doesn't just promise isolation—it shows *how*: indexes on `(namespace_id, user_id)`, middleware checks, destructive test scoping. This is a **strength cluster**.

**Collection Data & Persistence (19/19 full coverage)**
Status system, auto-save triggers, timestamps, merge rules, removal flows—all specified with precision. The plan understands the nuance that "Interested" and "Excited" are interest *levels*, not statuses. It understands that Scoop caches for 4 hours *only if the show is saved*. It understands that old turns in Ask conversations should be summarized while preserving voice. Every edge case appears to be handled. **Exemplary coverage**.

**Show Detail & Relationship UX (13/14 full coverage)**
Section order is preserved. Auto-save rules are explicit. Progressive Scoop UI is described. Toolbar placement is clear. The single partial gap (PRD-019, Next status) is trivial—the data model supports it; the UI just isn't spec'd yet. This is a **strength cluster**.

**Person Detail (4/4 full coverage)**
Small but complete. Gallery, analytics, year-grouped filmography, credit clickthrough—all present. **No gaps**.

**App Navigation & Discover Shell (4/4 full coverage)**
Filters, Find/Discover, Settings, mode switching—all architected. **No gaps**.

### Weakness Clusters

**AI Voice, Persona & Quality (5/7 full, 2 partial coverage) — 78.6%**
This is the *only* functional area where partial coverage clusters. PRD-087 (warmth/joy/light critique) and PRD-091 (quality validation rubric) both point to the same root issue: **the plan treats AI personality as a reference-doc topic, not an implementation detail**. The plan says "base system prompt defines persona (from ai_personality_opus.md)" but doesn't show *how* that persona gets encoded, tested, or validated.

PRD-077 and PRD-082 (concept ordering and pool sizing) are more technical but follow the same pattern: the plan knows the rule exists but doesn't specify how to enforce it.

This isn't a show-stopper. It means an implementer will need to read ai_personality_opus.md *carefully* and make prompt-design choices that the plan defers. But it's a gap nonetheless.

**Concepts, Explore Similar & Alchemy (8/10 full, 2 partial) — 90%**
PRD-084 (surprise without betrayal) and PRD-077 (concept ordering) both touch on the same gap: the plan doesn't specify how to balance competing discovery goals (safety vs. surprise, strength vs. diversity). These are prompt-engineering decisions that the plan acknowledges but leaves under-specified.

### Risk Assessment

**Failure mode if executed as-is, with gaps unfixed:**

A team building this plan would ship a working, data-sound, well-architected app. Users would be able to:
- Build and organize collections
- Auto-save with proper isolation
- Search and get results
- Ask questions and get recommendations
- Use Alchemy and Explore Similar

**But the recommendations might feel generic or miss the emotional tone.** Ask might answer a question competently but without warmth. Concepts might be less evocative. The app would work; it would just lose some of its "nerd friend" personality that makes it distinct from a generic catalog browser. A careful user (or a critic) would notice the AI voice drift between surfaces or the Scoop landing flat.

**Most likely to be noticed first:** An early user trying Ask would get functional but impersonal responses. Or they'd see concepts that sound reasonable but generic ("good writing," "great characters") instead of evocative. The app would *work* but wouldn't feel like it was built by people who love TV.

### Remediation Guidance

**For the 5 partial gaps, the work needed is:**

1. **AI Guardrails (PRD-086):** Create a "shared constants" module (e.g., `shared-ai-rules.ts` or similar) that centralizes:
   - Domain constraints (TV/movie only)
   - Spoiler-safety rules
   - Honesty/opinionality expectations
   - Specificity rules (no "good characters")
   
   Then wire these into every prompt (Scoop, Ask, Concepts, Recs) and every output validation handler. This is *specification work*, not architectural.

2. **AI Tone (PRD-087):** Extract the five tone pillars from ai_personality_opus.md and embed them into prompt engineering guidance within the plan. Add a section to the AI Integration part: "Tone Implementation" that shows concrete phrasing patterns and what NOT to do.

3. **Quality Validation (PRD-091):** Wire the discovery_quality_bar.md rubric into the Test Scenarios (Section 9.4). Add explicit test cases: "Ask response scores ≥1 on Voice Adherence, ≥1 on Taste Alignment, =2 on Real-Show Integrity." This is *acceptance criteria work*.

4. **Concept Pool Sizing (PRD-082):** Add a sub-section to Section 6.4 (Concepts Generation) specifying: "For multi-show requests, generate 12–16 candidate concepts before returning the top 8 to the UI. For single-show, generate 8–10."

5. **Concept Ordering (PRD-077):** Add post-processing logic after concept generation to sort by "strength" (which strongest are core to all input shows?) and ensure axis diversity (don't return 8 synonyms). This is a *prompt + post-processing* decision.

The category of work is: **behavioral specification + prompt engineering + acceptance criteria**. It's not architectural rework. A competent prompt engineer + QA lead could close all 5 gaps in a few days of focused effort, given the supporting docs.

---

**End of Evaluation**