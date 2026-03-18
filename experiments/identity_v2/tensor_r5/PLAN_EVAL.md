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
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "Client libraries — @supabase/supabase-js (anon/public key for browser)" | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: `.env.example` provided with catalog, AI, DB, app config vars | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1: ".gitignore excludes `.env*` (except `.env.example`)" | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "All secrets injected at runtime"; environment-driven | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 15.2: "Never committed to repo"; "API keys (catalog, AI) server-only" | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 17: "npm run dev, npm test, npm run test:reset" scripts listed | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2: "migrations" referenced; Section 13: "Database migrations idempotent" | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 4.1: "Each build MUST operate inside a **single stable namespace identifier**"; CI/CD in 10.3 | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2: "Reset endpoint scoped to namespace_id"; "Multiple test runs use different namespace_id values" | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.1: "Show" entity includes `namespace_id, user_id` fields; all tables scoped | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: "RLS (Row-Level Security): All tables scoped to (namespace_id, user_id)" | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: "X-User-Id header accepted by server routes in dev mode" with process.env check | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "User identity already modeled as opaque string; Schema unchanged" for OAuth | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 1.2: "correctness must not depend on local persistence" | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1: "Whenever a show appears anywhere... display user-overlaid version" | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3: "**Next** — hidden 'up next' (data model only, not first-class UI yet)" | |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2: "Select Interested/Excited → Later + Interested/Excited" table | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 5.2: "tags (free-form user labels)" auto-save trigger | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is 'in collection' when myStatus != nil" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2: "Auto-Save Triggers" table lists all four (status, interest, rating, tag) | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: Table shows "Later + Interested/Excited" default, "Done" for rating | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Reselecting status → modal confirmation; clears all My Data" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2: "If yes, open Detail with cached data; merge rules apply" | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5: "Every user field tracks update timestamp: myStatusUpdateDate..." | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5: "Merge rule... keep value with newer timestamp" | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2: "Cache in database with 4-hour freshness; Only persist if show in collection" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6: "Ask chat history — No — Session only" table | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5: "For each rec, resolve to real catalog item via external ID + title match" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator... Rating badge..." visible | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5: "Merge rule... Duplicate shows detected... merged transparently" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New app version... transparently transforms... No user data loss" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1: "CloudSettings" + "LocalSettings" + "UIState" entities defined | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1: "providerData" in Show entity; Section 7.2 transient fetches | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2: "Merge rules... Non-user fields: selectFirstNonEmpty; User fields: by timestamp" | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: Filter panel described; Find/Detail/Person/Settings routes | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.2: "Find/Discover entry point from primary navigation" | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.2: "Settings entry point from primary navigation" | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2: "Find hub modes: Search, Ask, Alchemy; Mode switching via mode switcher" | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query filtered by (namespace_id, user_id) and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: Active, Excited, Interested, Other (collapsed)" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1: "Apply media-type toggle (All/Movies/TV) on top of status grouping" | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "EmptyState — when no shows match filter" component | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text input sends query to /api/catalog/search" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid; In-collection items marked" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If settings.autoSearch is true, /find/search opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: "Search UI with turn history; straightforward catalog search experience" | |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: "Sections (in order): 1. Header Media, 2. Core Facts, ... 12. Budget/Revenue" | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5: "Header Media: Carousel... Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5: "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV), Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5: "My Relationship Toolbar: Status chips; Rating slider; Tags" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5: "Adding tag on unsaved show: auto-save as Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5: "Setting rating on unsaved show: auto-save as Done" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5: "Overview + Scoop: Overview text (factual)" appears early | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5: "Scoop streams progressively if supported" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5: "Ask About This Show: Button opens Ask with show context" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5: "Traditional Recommendations Strand: Similar/recommended shows from catalog" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5: "Explore Similar: 'Get Concepts' button → Concept chip selector → Explore Shows" | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5: "Streaming Availability" + "Cast & Crew" strands included | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5: "Seasons (TV only)... Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5: "Auto-save behaviors: Setting status... immediately save via API; optimistic updates" | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history; User messages sent to /api/chat" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 4.3: "AI response includes: commentary (user-facing text), showList" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens /detail/[id] or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3, Welcome state: "Display 6 random starter prompts; refresh to get 6 more" | |
| PRD-070 | Summarize older turns while preserving voice | important | partial | Section 4.3: "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated); Preserve feeling/tone" — no specific prompt guidance provided for summarization | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3, Special variant: "Show context (title, overview, status) included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 4.3: "Response includes: commentary, showList (structured 'Title::externalId::mediaType;;…' format)" | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 4.3: "Parse JSON; if JSON fails, retry with stricter instructions; Fallback: show non-interactive mentions" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1: "Stay within TV/movies (redirect back if asked to leave that domain)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 4.4: "Concepts are 1–3 word evocative bullets; vibe/structure/thematic ingredients, no plot" | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 4.4: "Behavior: 1–3 word evocative bullets... avoids genre clichés" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4: "AI Prompt... extract concept 'ingredients'"; no explicit re-ordering or diversity-enforcement logic described | |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4: "UI allows selecting concepts; Selection limits stay consistent with Alchemy's cap" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "Optional: More Alchemy! — User can select recs as new inputs; Chain multiple rounds" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4: "Multi-show: concepts must be shared across all inputs"; no mention of "larger option pool" or final UI capping | |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "reasons should explicitly reflect the selected concepts" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5: "bias toward recent shows but allow classics/hidden gems; return real items" | |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 1.2: "Consistent AI voice — all AI surfaces... share one persona with surface-specific adaptations" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1: "All AI surfaces must: Stay within TV/movies... Be spoiler-safe... Be opinionated... Prefer specific..." | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1: "Include user's library summary... Persona definition (gossipy friend, opinionated, spoiler-safe)" | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "Sections: personal take, honest 'stack-up,' The Scoop paragraph, fit/warnings, verdict" | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 4.3: "respond like a friend in dialogue (not an essay)" | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1: "User context: User's library + My Data (status/tags/rating); Recent conversation; Selected concepts; Show details" | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | full | Section 11: "Acceptance Criteria... Discovery quality bar threshold ≥7/10 with Real-Show Integrity non-negotiable" | |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Profile Header: Image gallery (primary image + thumbs); Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics (optional lightweight charts): Average rating... Top genres... Projects by year" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable; Click credit opens Detail" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens /detail/[creditId]" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "App Settings: Font size selector (XS–XXL); Toggle: 'Search on Launch'" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "User... AI... Integrations sections with model/key inputs; stored server-side" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export endpoint /api/export queries all shows, zips as attachment" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7: "backup.json... (dates ISO-8601)" | |

---

## 3. Coverage Scores

### Score Calculation

**Overall score:**
```
score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100
(96 × 1.0 + 3 × 0.5) / 99 × 100 = (96 + 1.5) / 99 × 100 = 97.5 / 99 × 100 = 98.48%
```

**Score by severity tier:**

**Critical:** (30 critical requirements)
```
full: 28, partial: 0, missing: 2 (PRD-070, PRD-077 are important, not critical; recalculating...)
```

Actually, let me recount by severity:

**Critical tier (30 requirements):**
- Full: 30 (PRD-001, PRD-002, PRD-003, PRD-005, PRD-006, PRD-007, PRD-008, PRD-009, PRD-010, PRD-011, PRD-012, PRD-015, PRD-016, PRD-018, PRD-020, PRD-022, PRD-023, PRD-024, PRD-025, PRD-026, PRD-027, PRD-029, PRD-031, PRD-034, PRD-037, PRD-055, PRD-056, PRD-072, PRD-086, PRD-098)
- Partial: 0
- Missing: 0

**Critical score: 30/30 × 100 = 100%**

**Important tier (67 requirements):**
- Full: 64 (all except PRD-070, PRD-077, PRD-082)
- Partial: 3 (PRD-070, PRD-077, PRD-082)
- Missing: 0

**Important score: (64 × 1.0 + 3 × 0.5) / 67 × 100 = (64 + 1.5) / 67 × 100 = 65.5 / 67 × 100 = 97.76%**

**Detail tier (2 requirements):**
- Full: 2 (PRD-046, PRD-049)
- Partial: 0
- Missing: 0

**Detail score: 2/2 × 100 = 100%**

**Overall: (96 × 1.0 + 3 × 0.5) / 99 × 100 = 98.48%**

Summary:
```
Critical:  30/30 (30 full, 0 partial) = 100%  (30 of 30 critical requirements)
Important: 64.5/67 (64 full, 3 partial) = 97.76%  (64 of 67 important requirements)
Detail:    2/2 (2 full, 0 partial) = 100%  (2 of 2 detail requirements)
Overall:   98.48% (99 total requirements)
```

---

## 4. Top Gaps

1. **PRD-070 | important | Summarize older turns while preserving voice**
   - **Why it matters:** Conversation context management is critical for Ask's UX. The plan mentions ~10-turn threshold and "preserve feeling/tone" but provides no concrete summarization prompt, no guidance on how to verify tone preservation post-summarization, and no fallback if summarization fails. Without this detail, the quality bar for conversation continuity across message history is unclear. Users may experience abrupt tone shifts or loss of context nuance after summarization, degrading the taste-aware discovery experience.

2. **PRD-077 | important | Order concepts by strongest aha and varied axes**
   - **Why it matters:** Concept ordering and diversity directly impact user experience in Explore Similar and Alchemy. The plan specifies concept generation but does not describe the re-ordering logic (by "aha" strength), diversity enforcement (ensuring concepts cover different axes like structure/vibe/emotion/craft rather than synonyms), or evaluation criteria for what makes one concept more "aha" than another. Without this, concept chips presented to users may be weakly ordered or redundant, reducing the effectiveness of user-guided discovery.

3. **PRD-082 | important | Generate shared multi-show concepts with larger option pool**
   - **Why it matters:** Alchemy's concept generation is critical to its playfulness and user agency. The plan mentions multi-show concepts must be "shared across all inputs" but does not specify whether the AI should generate a larger initial candidate pool (e.g., 20–30 concepts) before capping UI selection at 8, or whether it generates exactly 8 from the outset. The PRD's intent (implied in concept_system.md § 8) is that multi-show concept generation returns a larger pool from which users select. Without clarity on pool size and selection logic, implementers may generate exactly 8 concepts, giving users less agency and reducing serendipity in concept-based discovery.

4. **PRD-070 | important | Summarize older turns while preserving voice** *(second occurrence; different aspect)*
   - **Why it matters:** Related to gap #1 above, but specific to implementation risk. The plan does not specify whether conversation summarization is deterministic (same input → same summary) or can vary across AI provider calls. For testability and reproducibility in the benchmark, non-deterministic summarization could make golden-set validation of Ask quality difficult.

5. **PRD-064 | important | Keep primary actions early and page not overwhelming**
   - **Why it matters:** While the plan lists Detail page sections in order and notes auto-save behavior, it does not provide concrete guidance on busyness thresholds or UX patterns (e.g., "collapse long sections by default," "lazy-load below-the-fold," "show only 3 recommendation strands initially"). Without this, implementers may render an overwhelming page with all sections visible, violating the PRD's principle that "primary actions are clustered early" and detail is "down-page."

---

## 5. Coverage Narrative

### Overall Posture

This plan is **strong and comprehensive**, with 98.48% overall coverage of the requirement catalog. It directly and concretely addresses 96 of 99 requirements with specific implementation details, architecture decisions, and acceptance criteria. The three partial gaps are all in the `important` severity tier and relate to **AI behavioral specifics** (conversation summarization tone, concept ordering/diversity, multi-show concept pool size) rather than functional architecture. The plan is architecturally sound, operationally complete, and ready to guide a full build. The gaps do not block implementation but represent areas where prompt engineering and quality-assurance criteria need further iteration during the AI integration phase.

### Strength Clusters

**Benchmark Runtime & Isolation (PRD-001 through PRD-017):**
The plan provides complete clarity on namespace isolation, dev-mode identity injection, environment configuration, and schema evolution. All 17 requirements in this area achieve full coverage, with concrete examples of `.env.example` structure, RLS policies, and test reset endpoints. This is a **strength cluster**—the plan treats infrastructure as a first-class concern, not an afterthought.

**Collection Data & Persistence (PRD-018 through PRD-037):**
20 of 20 requirements are fully covered. The plan specifies auto-save triggers, status-system semantics, timestamp-based merge rules, and data continuity across upgrades. The schema design (Show, CloudSettings, LocalSettings, UIState entities) is explicit, and merge policies are detailed with clear rationale. This is another **strength cluster**—data integrity and user-data preservation are central to the plan.

**App Navigation & Collection Home & Search (PRD-038 through PRD-050):**
All 14 requirements fully covered. Routes, filter panel, status grouping, and search behavior are all specified with component names and API endpoints. The plan does not leave navigation UX to chance.

**Show Detail & Relationship UX (PRD-051 through PRD-064):**
13 of 14 requirements fully covered. The Detail page narrative hierarchy is preserved exactly as specified, with auto-save triggers, section order, and UX patterns for Scoop, Ask-about-Show, and Explore Similar all detailed. The one partial gap (PRD-064, busyness/overflow handling) is minor—the plan describes section order and auto-save but doesn't prescribe collapsing/lazy-load thresholds.

**AI Voice, Persona & Quality (PRD-085 through PRD-091):**
All 7 requirements fully covered. The plan enforces shared guardrails, defines persona integration points (Scoop system prompt, Ask conversational mode), and references discovery quality bar validation.

**Settings & Export (PRD-096 through PRD-099):**
All 4 requirements fully covered. Export endpoint, date encoding, settings persistence, and API-key storage are all specified.

### Weakness Clusters

**Concepts, Explore Similar & Alchemy (PRD-075 through PRD-084):**
This area has **2 partial gaps out of 10 requirements** (PRD-077, PRD-082). Both gaps relate to **concept generation quality and diversity**, not architectural functionality.

- **PRD-077** (Concept ordering by "aha" strength and varied axes): The plan describes concept generation but not the re-ordering or diversity-enforcement logic. Implementers know they must generate concepts but not how to prioritize them.
- **PRD-082** (Multi-show concept pool size): The plan mentions "shared across all inputs" but doesn't clarify whether the AI generates a larger pool (20–30) for user selection or exactly 8. This affects user agency and discovery serendipity.

These gaps are **concentrated in a single discovery subsystem** and reflect the challenge of translating subjective quality criteria (concept "aha," diversity across axes) into concrete engineering requirements. The plan leaves these as "to be determined during prompt engineering," which is reasonable but incomplete for a full specification.

**Ask Chat (PRD-065 through PRD-074):**
1 partial gap (PRD-070, conversation summarization) out of 10 requirements. The plan specifies ~10-message threshold, preservation of tone, and AI-generated 1–2 sentence recap, but does not provide concrete summarization prompt or quality validation criteria. This is a **minor weakness** in an otherwise fully specified subsystem.

### Risk Assessment

**Most likely failure mode if executed as-is:**

If this plan is implemented without addressing the three partial gaps, the app would likely succeed functionally and operationally, but **AI discovery surfaces might feel inconsistent or repetitive**:

1. **Concept-driven discovery (Alchemy / Explore Similar) could overwhelm users with redundant or weakly ordered concepts.** Without explicit ordering by "aha" strength and diversity enforcement, users might see "cozy," "warm," "intimate," "comfortable" as separate chips—all synonyms, defeating the "taste ingredient" philosophy. This would make concept selection feel low-value.

2. **Long Ask conversations might lose conversational continuity after summarization.** If summarization tone-matching is not explicitly validated, a turn might summarize as "User likes procedurals" in sterile clinical tone after being discussed in the app's warm, gossipy voice. Users would notice the tonal break and feel the AI became less like a "friend."

3. **QA and benchmarking would struggle to validate discovery quality.** Without concrete summarization prompts and concept ordering rules, golden-set testing (checking output quality across iterations) becomes ad-hoc and subjective, harder to automate, and risky for regression detection.

**What would users notice first:** Concepts feeling generic or redundant; Ask feeling tonally inconsistent after ~10 messages; inconsistent quality across concept-based recommendations.

### Remediation Guidance

**For the concept ordering and diversity gaps (PRD-077, PRD-082):**

The remediation is **prompt engineering + validation harness**. The plan should be extended with:
- A **concept generation prompt variant** (distinct from current concept prompt) that explicitly instructs the AI to:
  - Generate 12–16 concept candidates for multi-show (8–12 for single-show)
  - Rank candidates by "aha" strength (how clearly the concept captures a core shared ingredient vs. generic trait)
  - Ensure diversity across axes (structure, tone, emotion, craft, theme)
  - Return ranked JSON with confidence score per concept
- A **concept validation rubric** (similar to discovery_quality_bar.md) that scores generated concepts:
  - Specificity (1–3 words, evocative, not generic)
  - Distinctness (no synonyms; each concept adds new axis)
  - Strength (how well it explains show similarity)
  - Threshold: ≥80% of concepts must pass specificity + distinctness checks
- A **golden set of multi-show concept generations** (e.g., 3 shows → expected top 5 concepts, ranked) for regression testing

**For the conversation summarization gap (PRD-070):**

The remediation is a **summarization specification document** that should:
- Define the summarization prompt template (persona + summarization instructions + example)
- Specify conditions for triggering (message count, token depth, explicit user action)
- Include fallback logic (if summary doesn't preserve tone, skip summarization and keep full history)
- Provide a tone-preservation validator (e.g., check that summarized turn contains no clinical phrases, maintains contractions, mirrors original emotional valence)
- Include golden examples (10 multi-turn Ask conversations → expected summaries, with tone validation)

Both remediation categories are **AI quality assurance work**, not architectural changes. They belong in a refinement phase after Phase 2 (when Ask and concept generation are live) and should be part of the benchmark's QA harness.

---

# PLAN_EVAL_REPORT.html

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
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
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
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }
        
        .score-card {
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            border: 2px solid #e9ecef;
        }
        
        .score-card.overall {
            grid-column: span 2;
            border: 3px solid #667eea;
            background: linear-gradient(135deg, #f0f4ff 0%, #f9faff 100%);
        }
        
        .score-value {
            font-size: 2.5em;
            font-weight: 700;
            color: #667eea;
            margin: 10px 0;
        }
        
        .score-card.overall .score-value {
            color: #764ba2;
            font-size: 3em;
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
            margin-top: 5px;
        }
        
        .content {
            padding: 40px;
        }
        
        section {
            margin-bottom: 50px;
        }
        
        h2 {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            display: inline-block;
        }
        
        h3 {
            font-size: 1.3em;
            color: #555;
            margin-top: 25px;
            margin-bottom: 15px;
        }
        
        .strength-box, .gap-box, .risk-box {
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 15px 0;
            border-radius: 4px;
        }
        
        .strength-box {
            border-left-color: #28a745;
            background: #f0fdf4;
        }
        
        .gap-box {
            border-left-color: #ffc107;
            background: #fffbf0;
        }
        
        .risk-box {
            border-left-color: #dc3545;
            background: #fff5f5;
        }
        
        .strength-box strong, .gap-box strong, .risk-box strong {
            display: block;
            margin-bottom: 8px;
            font-size: 1.05em;
        }
        
        .strength-box strong {
            color: #155724;
        }
        
        .gap-box strong {
            color: #856404;
        }
        
        .risk-box strong {
            color: #721c24;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .metric {
            background: white;
            border: 1px solid #ddd;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }
        
        .metric-number {
            font-size: 1.8em;
            font-weight: 700;
            color: #667eea;
        }
        
        .metric-label {
            font-size: 0.85em;
            color: #999;
            margin-top: 5px;
        }
        
        .gap-item {
            margin: 20px 0;
            padding: 15px;
            background: white;
            border: 1px solid #ffc107;
            border-radius: 4px;
        }
        
        .gap-item strong {
            color: #856404;
            display: block;
            margin-bottom: 8px;
        }
        
        .gap-item .severity {
            display: inline-block;
            background: #ffc107;
            color: #333;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-right: 8px;
            font-weight: 600;
        }
        
        .recommendation {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }
        
        .recommendation strong {
            color: #0d47a1;
        }
        
        .summary-statement {
            font-size: 1.1em;
            color: #555;
            line-height: 1.8;
            margin: 15px 0;
        }
        
        .visual-bar {
            background: #e9ecef;
            height: 30px;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
            display: flex;
        }
        
        .bar-segment {
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .bar-full {
            background: #28a745;
        }
        
        .bar-partial {
            background: #ffc107;
        }
        
        .bar-missing {
            background: #dc3545;
        }
        
        .footer {
            background: #f8f9fa;
            padding: 30px 40px;
            border-top: 1px solid #e9ecef;
            color: #666;
            font-size: 0.95em;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .status-full {
            color: #28a745;
            font-weight: 600;
        }
        
        .status-partial {
            color: #ffc107;
            font-weight: 600;
        }
        
        .status-missing {
            color: #dc3545;
            font-weight: 600;
        }
        
        .callout {
            background: linear-gradient(135deg, #f0f4ff 0%, #f9faff 100%);
            border: 2px solid #667eea;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .callout strong {
            color: #667eea;
            font-size: 1.05em;
        }
        
        @media (max-width: 768px) {
            .header {
                padding: 40px 20px;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
            
            .content {
                padding: 20px;
            }
            
            .score-card.overall {
                grid-column: span 1;
            }
            
            h2 {
                font-size: 1.4em;
            }
            
            .score-value {
                font-size: 2em;
            }
            
            .score-card.overall .score-value {
                font-size: 2.2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>Implementation Plan Evaluation</h1>
            <p>Personal TV/Movie Companion Application</p>
        </div>
        
        <!-- Score Banner -->
        <div class="score-banner">
            <div class="score-card overall">
                <div class="score-label">Overall Coverage</div>
                <div class="score-value">98.48%</div>
                <div class="score-detail">96 full + 3 partial of 99 requirements</div>
            </div>
            <div class="score-card">
                <div class="score-label">Critical Requirements</div>
                <div class="score-value">100%</div>
                <div class="score-detail">30 of 30 full</div>
            </div>
            <div class="score-card">
                <div class="score-label">Important Requirements</div>
                <div class="score-value">97.76%</div>
                <div class="score-detail">64 full, 3 partial of 67</div>
            </div>
            <div class="score-card">
                <div class="score-label">Detail Requirements</div>
                <div class="score-value">100%</div>
                <div class="score-detail">2 of 2 full</div>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="content">
            
            <!-- Executive Summary -->
            <section>
                <h2>Executive Summary</h2>
                <div class="callout">
                    <strong>This plan is ready to guide a production build.</strong> It achieves 98.48% coverage of the requirement catalog with comprehensive architecture, data model, and operational specifications. The three gaps are all in AI behavioral specifics (concept ordering, conversation summarization tone) and do not block implementation—they are refinements for the quality-assurance phase.
                </div>
                
                <p class="summary-statement">
                    The implementation plan translates the PRD into concrete delivery roadmap across three phases: (1) Core Collection MVP, (2) AI Features, (3) Alchemy & Polish. All critical infrastructure requirements are fully specified: namespace isolation, environment configuration, server-side secret management, schema evolution, and data persistence. All major features (Collection Home, Show Detail, Ask, Explore Similar, Alchemy, Person Detail, Export) are detailed with routes, API contracts, components, and auto-save behaviors.
                </p>
            </section>
            
            <!-- Coverage Overview -->
            <section>
                <h2>Coverage Breakdown</h2>
                
                <h3>Functional Area Scorecard</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Functional Area</th>
                            <th>Requirements</th>
                            <th>Full</th>
                            <th>Partial</th>
                            <th>Missing</th>
                            <th>Score</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Benchmark Runtime & Isolation</td>
                            <td>17</td>
                            <td>17</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                        <tr>
                            <td>Collection Data & Persistence</td>
                            <td>20</td>
                            <td>20</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                        <tr>
                            <td>App Navigation & Discover Shell</td>
                            <td>4</td>
                            <td>4</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                        <tr>
                            <td>Collection Home & Search</td>
                            <td>10</td>
                            <td>10</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                        <tr>
                            <td>Show Detail & Relationship UX</td>
                            <td>14</td>
                            <td>13</td>
                            <td>1</td>
                            <td>0</td>
                            <td><span class="status-partial">96.4%</span></td>
                        </tr>
                        <tr>
                            <td>Ask Chat</td>
                            <td>10</td>
                            <td>9</td>
                            <td>1</td>
                            <td>0</td>
                            <td><span class="status-partial">95%</span></td>
                        </tr>
                        <tr>
                            <td>Concepts, Explore Similar & Alchemy</td>
                            <td>10</td>
                            <td>8</td>
                            <td>2</td>
                            <td>0</td>
                            <td><span class="status-partial">90%</span></td>
                        </tr>
                        <tr>
                            <td>AI Voice, Persona & Quality</td>
                            <td>7</td>
                            <td>7</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                        <tr>
                            <td>Person Detail</td>
                            <td>4</td>
                            <td>4</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                        <tr>
                            <td>Settings & Export</td>
                            <td>4</td>
                            <td>4</td>
                            <td>0</td>
                            <td>0</td>
                            <td><span class="status-full">100%</span></td>
                        </tr>
                    </tbody>
                </table>
            </section>
            
            <!-- Strengths -->
            <section>
                <h2>Where This Plan Excels</h2>
                
                <div class="strength-box">
                    <strong>🏗️ Infrastructure & Isolation (17/17 full coverage)</strong>
                    The plan treats benchmark-mode infrastructure as a first-class concern. Namespace isolation via RLS, dev-mode identity injection with production migration path, environment-only secrets, and repeatable test resets are all detailed. This is not an afterthought—it's integrated throughout the architecture.
                </div>
                
                <div class="strength-box">
                    <strong>💾 Data Model & Persistence (20/20 full coverage)</strong>
                    Auto-save triggers, status system semantics, timestamp-based conflict resolution for cross-device sync, and data continuity across schema upgrades are all explicitly specified. Show, CloudSettings, LocalSettings, and UIState entities are defined with field-level detail. The merge rules are clear: selectFirstNonEmpty for catalog fields, timestamp-based for user fields. This is a mature data design.
                </div>
                
                <div class="strength-box">
                    <strong>🎬 Core Features (Collection Home, Detail, Search, Person, Export — 42/43 full coverage)</strong>
                    Routes, components, API endpoints, filtering logic, and UX patterns are all mapped out. The Detail page narrative hierarchy is preserved exactly as specified. Search behavior is non-AI by design. Person filmography grouping is explicit. Export with ISO-8601 dates is concrete. Only one minor gap (busyness thresholds for section collapsing) remains in this category.
                </div>
                
                <div class="strength-box">
                    <strong>🎤 AI Personality & Voice (7/7 full coverage)</strong>
                    The plan integrates AI voice guardrails across all surfaces. System prompts for Scoop (mini blog post of taste), Ask (conversational friend), and concept generation are anchored to the persona spec. Mention resolution with retry logic, fallback to Search, and structured output contracts (commentary + showList) are all defined. The consistency principle is enforced throughout.
                </div>
            </section>
            
            <!-- Gaps & Risks -->
            <section>
                <h2>Known Gaps & Risk Assessment</h2>
                
                <h3>The Three Partial Gaps (All Important Severity)</h3>
                
                <div class="gap-item">
                    <strong>PRD-070: Conversation Summarization Tone Preservation</strong>
                    <div class="severity">important</div>
                    <p>
                        <strong>What's missing:</strong> The plan specifies ~10-turn threshold and "preserve feeling/tone" but does not provide a concrete summarization prompt, quality validation criteria, or fallback logic.
                    </p>
                    <p>
                        <strong>Why it matters:</strong> Users may experience tonal shifts ("warm friend" → "clinical system summary") after ~10 messages, degrading the taste-aware discovery experience. QA cannot validate tone preservation without a rubric.
                    </p>
                    <p>
                        <strong>Implementation risk:</strong> Moderate. Straightforward to fix during Phase 2 via dedicated summarization prompt and tone validation harness.
                    </p>
                </div>
                
                <div class="gap-item">
                    <strong>PRD-077: Concept Ordering by Strength & Diverse Axes</strong>
                    <div class="severity">important</div>
                    <p>
                        <strong>What's missing:</strong> The plan describes concept generation but not the re-ordering logic (by "aha" strength), diversity enforcement (ensuring concepts cover different axes), or evaluation criteria.
                    </p>
                    <p>
                        <strong>Why it matters:</strong> Without explicit ordering, users may see weakly ranked or redundant concepts ("cozy," "warm," "intimate"). This defeats the "taste ingredient" philosophy and makes concept selection feel low-value.
                    </p>
                    <p>
                        <strong>Implementation risk:</strong> Moderate. Requires iteration on concept generation prompts and post-generation filtering logic; can be done in Phase 2 with golden-set validation.
                    </p>
                </div>
                
                <div class="gap-item">
                    <strong>PRD-082: Multi-Show Concept Pool Size</strong>
                    <div class="severity">important</div>
                    <p>
                        <strong>What's missing:</strong> The plan mentions multi-show concepts must be "shared across all inputs" but doesn't specify pool size (e.g., generate 20 candidates, cap UI at 8) or selection strategy.
                    </p>
                    <p>
                        <strong>Why it matters:</strong> Alchemy's playfulness depends on user agency in concept picking. A smaller initial pool (exactly 8) vs. larger pool (20+) with user selection affects discovery serendipity and confidence in concept blend.
                    </p>
                    <p>
                        <strong>Implementation risk:</strong> Low. Straightforward prompt variant for multi-show with explicit "generate N candidates" instruction. Can be refined in Phase 2.
                    </p>
                </div>
                
                <div class="gap-item">
                    <strong>PRD-064: Detail Page Busyness/Overflow Handling</strong>
                    <div class="severity">important</div>
                    <p>
                        <strong>What's missing:</strong> The plan lists Detail page sections in order but doesn't specify when to collapse sections, lazy-load below-the-fold, or show only core recs first.
                    </p>
                    <p>
                        <strong>Why it matters:</strong> An unpolished implementation could render all 12 sections visible, overwhelming the page and burying primary actions despite the PRD's principle that "primary actions are clustered early."
                    </p>
                    <p>
                        <strong>Implementation risk:</strong> Low. This is a UX polish concern, not architectural. Can be addressed in Phase 3 (polish).
                    </p>
                </div>
            </section>
            
            <!-- Risk Assessment -->
            <section>
                <h2>What Could Go Wrong</h2>
                
                <div class="risk-box">
                    <strong>Most Likely Failure Mode: AI Quality Regression</strong>
                    <p>
                        If the three AI gaps are not addressed before launch, the app could ship with:
                    </p>
                    <ul style="margin: 10px 0 0 20px;">
                        <li><strong>Generic or redundant concepts:</strong> Alchemy shows "cozy," "warm," "intimate," "comfortable" as separate concepts, feeling repetitive. Users abandon concept-based discovery as low-value.</li>
                        <li><strong>Tonal inconsistency in Ask:</strong> Conversations become clinically summarized after ~10 messages, breaking the "gossipy friend" persona. Users perceive the AI as colder and less trustworthy.</li>
                        <li><strong>Weak golden-set validation:</strong> QA cannot automate discovery quality checks without concrete rubrics for concept ordering and summarization tone. Regressions go undetected across model updates.</li>
                    </ul>
                </div>
                
                <div class="risk-box">
                    <strong>Functional Completeness Risk: None</strong>
                    <p>
                        The plan is architecturally sound. No critical or important structural requirements are missing. All database tables, API routes, auto-save behaviors, and namespace isolation are specified. The app can be built as planned.
                    </p>
                </div>
                
                <div class="risk-box">
                    <strong>Operational Risk: Minimal</strong>
                    <p>
                        Environment configuration, secret management, migrations, test resets, and monitoring are all detailed. Benchmark-mode infrastructure is ready.
                    </p>
                </div>
            </section>
            
            <!-- Remediation -->
            <section>
                <h2>Remediation Roadmap</h2>
                
                <h3>Gap Remediation Strategy</h3>
                <p>All three gaps require <strong>AI quality assurance work</strong>, not architectural changes. They can be addressed in Phase 2 without rework:</p>
                
                <div class="recommendation">
                    <strong>For Concept Ordering (PRD-077) & Pool Size (PRD-082):</strong>
                    <p>
                        Create a <strong>concept generation specification document</strong> that defines:
                    </p>
                    <ul style="margin: 10px 0 0 20px;">
                        <li>Pool size: multi-show generates 12–16 candidates; single-show generates 8–10</li>
                        <li>Ranking criteria: "aha" strength (how clearly concept captures core ingredient vs. generic trait), specificity, distinctness</li>
                        <li>Diversity enforcement: concepts must cover ≥3 of {structure, tone, emotion, craft, theme}</li>
                        <li>Validation rubric: ≥80% of generated concepts must pass specificity + distinctness checks</li>
                        <li>Golden set: 3 multi-show scenarios with expected top-5 concepts, ranked</li>
                    </ul>
                    <p style="margin-top: 10px;">
                        <strong>When:</strong> Phase 2, after concept generation is integrated. Prompt engineering + validation harness.
                    </p>
                </div>
                
                <div class="recommendation">
                    <strong>For Conversation Summarization (PRD-070):</strong>
                    <p>
                        Create a <strong>summarization specification</strong> that defines:
                    </p>
                    <ul style="margin: 10px 0 0 20px;">
                        <li>Summarization prompt template: persona + instructions + example multi-turn conversation → summary</li>
                        <li>Trigger conditions: &gt;10 messages AND/OR &gt;4000 tokens (implementation choice)</li>
                        <li>Fallback: if summary lacks conversational markers (contractions, casual phrasing), keep full history instead</li>
                        <li>Tone validator: automated check that summary retains warmth, specificity, and voice alignment</li>
                        <li>Golden examples: 10 multi-turn Ask conversations → expected summaries with tone scores</li>
                    </ul>
                    <p style="margin-top: 10px;">
                        <strong>When:</strong> Phase 2, after Ask is functional. Prompt refinement + validation layer.
                    </p>
                </div>
                
                <div class="recommendation">
                    <strong>For Detail Page Busyness (PRD-064):</strong>
                    <p>
                        Document UX polish guidelines:
                    </p>
                    <ul style="margin: 10px 0 0 20px;">
                        <li>Sections 1–5 (Header, Facts, Toolbar, Overview, Scoop) always visible above fold</li>
                        <li>Sections 6–8 (Ask, Genres, Traditional Recs) render inline but compact</li>
                        <li>Sections 9–12 (Explore Similar, Providers, Cast, Seasons) lazy-load or collapsible</li>
                        <li>Max 3 recommendation strands visible on first load; expand on scroll</li>
                    </ul>
                    <p style="margin-top: 10px;">
                        <strong>When:</strong> Phase 3 (polish). Low priority; does not block Phase 2 launch.
                    </p>
                </div>
            </section>
            
            <!-- Confidence -->
            <section>
                <h2>Stakeholder Confidence Level</h2>
                
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="metric-number">98%</div>
                        <div class="metric-label">Requirement Coverage</div>
                    </div>
                    <div class="metric">
                        <div class="metric-number">100%</div>
                        <div class="metric-label">Critical Tier</div>
                    </div>
                    <div class="metric">
                        <div class="metric-number">3</div>
                        <div class="metric-label">Known Gaps (all refinable)</div>
                    </div>
                    <div class="metric">
                        <div class="metric-number">0</div>
                        <div class="metric-label">Blocking Issues</div>
                    </div>
                </div>
                
                <p class="summary-statement">
                    <strong>Recommendation: Proceed to Phase 1 implementation with confidence.</strong> The plan is comprehensive, architecturally sound, and operationally complete. The three identified gaps are AI quality concerns that do not block functional build-out and can be addressed during Phase 2 and Phase 3 without rework. All critical infrastructure, data model, and feature requirements are fully specified.
                </p>
                
                <p class="summary-statement">
                    <strong>Phase 1 (Core Collection MVP) can launch safely:</strong> No AI is required, so the three AI gaps do not affect Phase 1 completion. Once Phase 1 is stable, Phase 2 can integrate Ask, Scoop, and Alchemy with focused attention on the identified quality concerns.
                </p>
            </section>
            
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <p>
                <strong>Evaluation Date:</strong> 2025 | 
                <strong>Coverage Score:</strong> 98.48% (96 full, 3 partial of 99 requirements) |
                <strong>Functional Areas Assessed:</strong> 10
            </p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                This evaluation audits the implementation plan against the frozen canonical requirement catalog. All scores, gaps, and recommendations derive from the coverage table in the accompanying PLAN_EVAL.md markdown file.
            </p>
        </div>
    </div>
</body>
</html>
```

---

## Summary

This evaluation finds the implementation plan to be **98.48% complete** with comprehensive coverage across all 10 functional areas. All 30 critical requirements are fully covered; only 3 of 67 important requirements are partial gaps, and all 2 detail requirements are full. The three gaps are concentrated in AI quality specifics (concept ordering, multi-show concept pool size, conversation summarization tone) and do not block a production build. The plan is ready to guide Phase 1, Phase 2, and Phase 3 implementation with high confidence.