# Plan Evaluation

## 1. Requirements Extraction

### Pass 1: Identify Functional Areas

The canonical functional area taxonomy (in order):

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
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack; explicit statement "Next.js (latest stable)" |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 Technology Stack; "@supabase/supabase-js (anon/public key for browser)" |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 Environment Variables; complete `.env.example` template provided |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1; "`.gitignore` excludes `.env*` (except `.env.example`)" |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1; "All secrets injected at runtime"; no code edits required |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3 Server-Only Secrets; comprehensive secret handling |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 Scripts; lists `npm run dev`, `npm test`, `npm run test:reset` |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 Database Schema; "Supabase" with migrations mentioned; Section 10.2 includes `supabase db push` |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 1.2 "Namespace isolation — all data partitioned by `(namespace_id, user_id)`" |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 Destructive Testing; `/api/test/reset` scoped to namespace only |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 Database Schema; all tables include `user_id`, `namespace_id` |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2; "All tables scoped to `(namespace_id, user_id)` via RLS policies" |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 Benchmark-Mode Identity Injection; `X-User-Id` header for dev, middleware check for NODE_ENV |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 Future OAuth Path; "Schema unchanged, Business logic unchanged" |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 Key Architectural Principles; "Backend is source of truth" |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 1.2; "clients cache for performance, but correctness depends on server state" |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 Development Environment; "No Docker requirement" |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 2.1 Core Entities Show; "User overlay ("My Data")" on every show |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3 Status System; lists all statuses including "Next — hidden "up next"" |  |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 Auto-Save Triggers; "Select Interested/Excited → Later + Interested/Excited" |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1; `myTags` (free-form user labels + timestamp) |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 Collection Membership; "A show is "in collection" when `myStatus != nil`" |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 Auto-Save Triggers; comprehensive trigger list |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 Auto-Save Triggers; explicit defaults in table |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 Removal Confirmation; "Remove from collection" clears all My Data |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 2.3 Merge rules; "Non-user fields: prefer non-empty newer value" |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5 Timestamps & Merge Resolution; all `*UpdateDate` fields listed |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5; "For each field, keep the value with the newer timestamp" |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation; "Only persist if show is in collection"; "Cache with 4-hour freshness" |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 AI Data Persistence; "Ask chat history — No — Session only"; "Alchemy results/reasons — No — Session only" |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 5.7 AI Recommendations Mapping; detailed resolution logic |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 Tile Indicators; "In-collection indicator: visible when `myStatus != nil`"; "Rating badge: visible when `myScore != nil`" |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3 Merge rules; "Duplicate shows detected by `id` and merged transparently" |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 Data Continuity & Migrations; "No user data loss; all shows, tags, ratings, statuses brought forward" |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 Core Entities; CloudSettings, AppMetadata, LocalSettings, UIState all defined |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1; `providerData` persisted, cast/crew/seasons not persisted |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 2.3 Merge rules; "My fields: resolve by `*UpdateDate` timestamp" |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Top-Level Layout; ASCII diagram shows filters panel + main content |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.2 Routes & Pages; "Find/Discover entry point" listed in persistent navigation |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.2; "Settings entry point" in persistent navigation |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 4.2 Search, 4.3 Ask, 4.4 Alchemy; all three modes implemented |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 Collection Home; "Query `shows` table filtered by `(namespace_id, user_id)` and selected filter" |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1; explicit grouping: "Active, Excited (Later + Excited), Interested, Other (collapsed)" |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1; "Apply media-type toggle (All/Movies/TV) on top of status grouping" |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1; "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1; `EmptyState` component "when no shows match filter" |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 Search; "Text input sends query to `/api/catalog/search`" |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2; "Results rendered as poster grid"; "In-collection items marked with indicator" |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2; "If `settings.autoSearch` is true, `/find/search` opens on app startup" |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2; straightforward search implementation with no AI mention |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 Show Detail Page; numbered list of 12 sections in order |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 Section 1 Header Media; "Carousel: backdrops/posters/logos/trailers"; "Fall back to static poster" |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 Section 2; "Year, runtime (movie) or seasons/episodes (TV)"; "Community score bar" |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 Section 3; "My Relationship Toolbar" with status chips |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 Auto-save behaviors; "Adding tag on unsaved show: auto-save as Later + Interested" |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5 Auto-save behaviors; "Setting rating on unsaved show: auto-save as Done" |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 Section 4; "Overview + Scoop" early in order |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5 Section 4; "Scoop streams progressively if supported" |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5 Section 5; "Ask About This Show button opens Ask with show context" |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 Section 7; "Traditional Recommendations Strand" |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 Section 8; "Get Concepts → Concept chip selector → Explore Shows" |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 Sections 9 & 10; "Streaming Availability" and "Cast & Crew" |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5; "Seasons (TV only)"; "Budget vs Revenue (Movies only)" |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5; sections 1–4 primary actions; "long‑tail info is down‑page" |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 Ask; "Chat UI with turn history" |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 4.3; "Server calls AI with taste-aware prompt"; "spoiler-safe by default" |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3; "Render mentioned shows as horizontal strand (selectable)" |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3; "Click mentioned show opens `/detail/[id]` or triggers detail modal" |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Welcome state; "display 6 random starter prompts"; "User can refresh" |  |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3 Context management; "After ~10 turns, summarize older turns into 1–2 sentence recap"; "Preserve feeling/tone in summary" |  |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 Special variant; "Button on Detail page opens Ask with pre-seeded context" |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 Ask; structured output with exact format "Title::externalId::mediaType;;…" |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 Components; "Parse response; if JSON fails, retry with stricter instructions; Fallback: show non-interactive mentions" |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1 Shared Architecture; "Stay within TV/movies (redirect back if asked to leave that domain)" |  |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 4.4 & 6.4; concept examples like "hopeful absurdity" not genres |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 Concepts Generation; "Output: bullet list only"; "Each 1–3 words, spoiler-free"; "No generic placeholders" |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 mentions "Array of 8–12 concepts" but doesn't explicitly detail ordering or axis diversity algorithm |  No explicit ordering or axis-diversity algorithm described; implementation details deferred |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Alchemy flow; "User selects 1–8 concepts"; "Max 8 enforced by UI" |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 Concept-Based Recommendations; "Explore Similar: 5 recs per round" |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy flow; "Step 5: Optional: More Alchemy!" supports chaining |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4; "Backtracking allowed: changing shows clears concepts/results" |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 mentions multi-show concepts but doesn't explicitly describe "larger option pool" vs single-show | Plan mentions multi-show returns larger pool but doesn't specify exact count or pool-sizing logic |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 output format; "reasons should explicitly reflect the selected concepts" |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5 mentions "taste-aligned recommendations" and reasoning; discovery quality bar applied |  |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 Shared Architecture; "All AI surfaces: Use configurable provider"; "Prompts defined in reference docs" |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1; "All AI surfaces: Stay within TV/movies"; "Be spoiler-safe by default"; "Be opinionated and honest" |  |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 User context; persona defined as "warm, opinionated friend" |  |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 Scoop Generation; "generate spoiler-safe "mini blog post of taste""; "Sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict" |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3 Ask Processing; "respond like a friend in dialogue (not an essay)" |  |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1 User context; detailed breakdown of what context each surface receives |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 14.2 Metrics mentions "average response time" and "error rates" but doesn't explicitly implement discovery quality rubric validation or hard-fail integrity checks | Plan mentions monitoring error rates but doesn't specify implementation of discovery quality bar rubric or hard-fail gates on integrity |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail Page Section 1; "Image gallery (primary image + thumbs)"; "Name, bio" |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 Section 2; "Average rating of projects"; "Top genres by count"; "Projects by year (bar chart)" |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6 Section 3; "Filmography Grouped by Year"; "Years collapsed/expandable" |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 Section 3; "Click credit opens `/detail/[creditId]`" |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 App Settings; "Font size selector (XS–XXL)"; "Toggle: "Search on Launch"" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 User/AI/Integrations; username, model selection, API key input all present |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 Your Data; "Export / Backup: Button generates `.zip` containing: `backup.json` with all shows + My Data" |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7; "`backup.json` with all shows + My Data (dates ISO-8601)" |  |

---

## 3. Coverage Scores

### Overall Score

```
score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100
```

- Full: 96
- Partial: 3
- Missing: 0
- Total: 99

```
score = (96 × 1.0 + 3 × 0.5) / 99 × 100 = 97.5 / 99 × 100 = 98.48%
```

### Score by Severity Tier

**Critical (30 total):**
- Full: 30
- Partial: 0
- Missing: 0

```
(30 × 1.0 + 0 × 0.5) / 30 × 100 = 100%
(30 of 30 critical requirements covered)
```

**Important (67 total):**
- Full: 65
- Partial: 2
- Missing: 0

```
(65 × 1.0 + 2 × 0.5) / 67 × 100 = 66 / 67 × 100 = 98.51%
(65-66 of 67 important requirements covered)
```

**Detail (2 total):**
- Full: 2
- Partial: 1
- Missing: 0

```
(1 × 1.0 + 1 × 0.5) / 2 × 100 = 1.5 / 2 × 100 = 75%
(1-1.5 of 2 detail requirements covered)
```

**Overall:**
```
Critical:  100% (30 of 30 critical requirements)
Important: 98.51% (65-66 of 67 important requirements)
Detail:    75% (1-1.5 of 2 detail requirements)
Overall:   98.48% (97.5 of 99 total requirements)
```

---

## 4. Top Gaps

1. **PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity**
   - *Why it matters:* The discovery quality bar is a cornerstone of the product—it defines what "good" AI recommendations look like. Without explicit validation and hard-fail gates, the app risks shipping AI outputs that violate the voice spec, fail taste alignment, or produce hallucinated/unresolvable shows. This is not just monitoring; it's a product gate.

2. **PRD-082 | `important` | Generate shared multi-show concepts with larger option pool**
   - *Why it matters:* The spec requires multi-show concept generation to return a larger pool than single-show (while keeping UI selection capped at 8). The plan mentions multi-show happens but doesn't specify the exact count or logic for "larger pool," leaving implementation ambiguous and potentially inconsistent with the intended UX.

3. **PRD-077 | `important` | Order concepts by strongest aha and varied axes**
   - *Why it matters:* Concept ordering directly impacts user agency and discovery quality. If concepts aren't ordered by strength or lack axis diversity (structure/vibe/emotion/craft), users get weak or redundant options first, undermining the "ingredient picking" mental model. The plan doesn't detail the ordering/diversity algorithm.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **exceptionally comprehensive and strategically sound**. It achieves 98.48% coverage across the full requirement catalog, with **100% coverage of all 30 critical requirements**. The plan is grounded in deep understanding of the PRD, maintains architectural rigor around data isolation and AI voice consistency, and lays out a credible three-phase delivery roadmap. The three identified gaps are all in the `important` tier and are narrow, specification-level details rather than fundamental architectural or feature omissions. This is a plan that could be handed to a strong engineering team and executed with confidence.

### Strength Clusters

**Benchmark & Infrastructure (PRD-001 through PRD-017):**
Perfect coverage. The plan demonstrates crisp understanding of namespace isolation, user identity scoping, environment-driven configuration, and the auth migration path. Every baseline requirement is explicitly addressed with concrete implementation details (Supabase schema with RLS, dev auth injection via header, server-only secrets, idempotent migrations).

**Data Model & Persistence (PRD-018 through PRD-037):**
Excellent coverage with only one partial. The plan articulates all core data behaviors—collection membership, auto-save triggers, status/interest mapping, timestamp-based conflict resolution, cross-device sync, and data continuity across upgrades. The schema is clearly defined with storage-schema.ts reference, and merge rules are explicit.

**Core Features—Collection Home, Search, Detail, Ask, Alchemy (PRD-038 through PRD-084):**
Strong coverage. Every major feature area is broken down into sections, components, and behavioral flows. The plan describes filtering, status grouping, Search integration, the 12-section Detail page hierarchy, Ask chatbot with mention resolution, Alchemy chaining, and Explore Similar. The level of detail is sufficient to guide UI/UX design and backend API contracts.

**AI Voice & Quality (PRD-085 through PRD-091):**
Good coverage on persona consistency and guardrails, but weaker on discovery quality validation. The plan references ai_personality_opus.md and ai_prompting_context.md for prompt definitions and voice tone, correctly treating these as config-driven rather than hardcoded. However, it stops short of specifying how the discovery quality bar rubric is validated or what hard-fail gates should exist.

**Person Detail, Settings & Export (PRD-092 through PRD-099):**
Full coverage. Person detail flows, analytics, and filmography navigation are clearly described. Settings for appearance, AI provider, and catalog provider are present. Export as JSON zip with ISO-8601 dates is explicitly detailed.

### Weakness Clusters

All three gaps are in **AI behavioral specification**:

- **PRD-077 (Concept Ordering & Axis Diversity):** The plan says "Return 8–12 concepts" but doesn't explain how they're ordered or how axis diversity is ensured. This is important because weak concepts presented first undermine the UX intent. *Pattern:* The plan treats concept generation as a simple "call AI, parse bullet list" function rather than a ranked, curated output.

- **PRD-082 (Multi-Show Concept Pool Size):** The plan mentions that multi-show should return a "larger option pool" but doesn't quantify it (e.g., "12–16 for multi-show vs 8 for single-show"). *Pattern:* Similar to PRD-077—implementation details are deferred or left implicit.

- **PRD-091 (Discovery Quality Validation):** The plan has monitoring (metrics, error rates, logging) but no explicit mention of testing concepts/recommendations against the discovery quality bar rubric or of hard-fail gates that prevent shipping bad outputs. *Pattern:* The plan treats discovery as a runtime feature rather than a tested, gated system.

All three gaps cluster around **AI output specification and validation**, suggesting the plan treats AI as an implementation detail ("call the API, get text back") rather than a specifiable, testable product surface.

### Risk Assessment

**Most likely failure mode:** If this plan is executed as-is, the AI discovery surfaces (Ask, Alchemy, Explore Similar, Scoop) ship with inconsistent concept quality and no automated guard rails. Specifically:

1. Users might see weak, generic concepts like "good writing" or redundant concepts ("dark," "dark tone," "darkness") because there's no concept diversity algorithm.
2. Concept ordering might be random or alphabetical rather than ranked by "aha" strength, degrading the UX of concept picking.
3. Recommendations might occasionally hallucinate (suggest non-existent shows) or resolve to wrong titles because the show-mapping fallback logic isn't rigorously tested.
4. There's no stated process for validating that AI outputs adhere to the voice spec—a new AI model or prompt change could subtly drift tone without detection.

**What a stakeholder would notice first:** Quality variance in Ask responses. One user might get brilliant, taste-grounded recommendations; another might get generic, safe picks. Concept lists might feel repetitive or weakly differentiated. These are edge cases that wouldn't show up in a single demo but would be apparent after a week of real usage.

### Remediation Guidance

The gaps require **specification work, not architecture work**:

1. **Concept Ordering & Diversity Algorithm (PRD-077, PRD-082):**
   - Add to the plan: "Concepts are generated by AI as a larger pool (12–20), then ranked by: (a) specificity score (reject generics), (b) axis diversity (ensure structure/vibe/emotion/craft are all represented), (c) strength/aha-ness. Return top 8–12 ranked concepts."
   - This is ~50 lines of post-processing logic in the Concepts endpoint, not an architectural change.

2. **Discovery Quality Rubric Validation (PRD-091):**
   - Add to the plan: "Every Ask, Alchemy, and Explore Similar response is validated at generation time against the discovery quality bar rubric (voice adherence, taste alignment, real-show integrity). Responses failing real-show integrity hard-fail and trigger a retry with stricter constraints. Voice/taste adherence issues are logged and trigger alerts if >5% of responses fail."
   - This is testing infrastructure (validation layer, logging, alerts), not a feature change.

3. **Show Mapping Fallback Robustness (implied by PRD-031):**
   - The plan mentions "resolve by external ID, fall back to title match" but doesn't specify what happens on ambiguity (multiple shows with same title, e.g., "Crime Scene" might exist in multiple years/regions). Add: "If multiple matches exist, prefer exact year match. If no year match, prefer most recent. If still ambiguous, hand off to user for manual selection or mark as unresolvable."

All three are **specification/validation work**, not architectural redesign.

---

## HTML Report

Now generating the stakeholder-ready HTML report at `results/PLAN_EVAL_REPORT.html`.

<details>
<summary>HTML Report (click to expand)</summary>

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
            line-height: 1.6;
            color: #1a1a1a;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 2rem 1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 3rem 2rem;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.95;
            font-weight: 300;
        }

        .score-box {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            padding: 2.5rem 2rem;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }

        .score-card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .score-card.critical {
            border-left-color: #e74c3c;
        }

        .score-card.important {
            border-left-color: #f39c12;
        }

        .score-card.detail {
            border-left-color: #3498db;
        }

        .score-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 0.5rem;
        }

        .score-card.critical .score-value {
            color: #e74c3c;
        }

        .score-card.important .score-value {
            color: #f39c12;
        }

        .score-card.detail .score-value {
            color: #3498db;
        }

        .score-label {
            font-size: 0.9rem;
            color: #7f8c8d;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .score-context {
            font-size: 0.85rem;
            color: #95a5a6;
            margin-top: 0.5rem;
        }

        .content {
            padding: 3rem 2rem;
        }

        .section {
            margin-bottom: 3rem;
        }

        .section-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 3px solid #667eea;
            display: inline-block;
        }

        .narrative-section {
            margin-bottom: 2rem;
            padding: 1.5rem;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }

        .narrative-section h3 {
            color: #667eea;
            font-size: 1.3rem;
            margin-bottom: 1rem;
        }

        .narrative-section p {
            font-size: 1rem;
            line-height: 1.7;
            color: #2c3e50;
            margin-bottom: 0.8rem;
        }

        .narrative-section p:last-child {
            margin-bottom: 0;
        }

        .gap-list {
            list-style: none;
            margin: 1.5rem 0;
        }

        .gap-item {
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
            border-radius: 6px;
            border-left: 3px solid #e74c3c;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .gap-item strong {
            color: #e74c3c;
            display: block;
            margin-bottom: 0.3rem;
        }

        .gap-item em {
            color: #7f8c8d;
            font-style: italic;
            display: block;
            margin-top: 0.5rem;
            font-size: 0.95rem;
        }

        .strength-cluster {
            padding: 1rem;
            margin-bottom: 1rem;
            background: white;
            border-radius: 6px;
            border-left: 3px solid #27ae60;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .strength-cluster strong {
            color: #27ae60;
            display: block;
            margin-bottom: 0.3rem;
        }

        .strength-cluster p {
            color: #2c3e50;
            font-size: 0.95rem;
            margin: 0;
        }

        .highlight {
            background: #fff3cd;
            padding: 1.5rem;
            border-radius: 6px;
            border-left: 4px solid #ffc107;
            margin: 2rem 0;
        }

        .highlight strong {
            color: #856404;
        }

        .footer {
            background: #2c3e50;
            color: white;
            padding: 2rem;
            text-align: center;
            font-size: 0.9rem;
            border-top: 1px solid #34495e;
        }

        .coverage-matrix {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }

        .matrix-cell {
            padding: 1rem;
            background: white;
            border-radius: 6px;
            text-align: center;
            border: 2px solid #e9ecef;
            font-weight: 600;
        }

        .matrix-cell.full {
            background: #d4edda;
            border-color: #27ae60;
            color: #155724;
        }

        .matrix-cell.partial {
            background: #fff3cd;
            border-color: #f39c12;
            color: #856404;
        }

        .matrix-cell.missing {
            background: #f8d7da;
            border-color: #e74c3c;
            color: #721c24;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8rem;
            }

            .content {
                padding: 1.5rem 1rem;
            }

            .score-box {
                grid-template-columns: 1fr;
                padding: 1.5rem 1rem;
            }

            .section-title {
                font-size: 1.4rem;
            }

            .narrative-section {
                padding: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Implementation Plan Evaluation</h1>
            <p>Personal TV/Movie Companion App — Full Coverage Analysis</p>
        </div>

        <div class="score-box">
            <div class="score-card">
                <div class="score-value">98.48%</div>
                <div class="score-label">Overall Coverage</div>
                <div class="score-context">97.5 / 99 requirements</div>
            </div>
            <div class="score-card critical">
                <div class="score-value">100%</div>
                <div class="score-label">Critical Requirements</div>
                <div class="score-context">30 / 30 covered</div>
            </div>
            <div class="score-card important">
                <div class="score-value">98.51%</div>
                <div class="score-label">Important Requirements</div>
                <div class="score-context">65–66 / 67 covered</div>
            </div>
            <div class="score-card detail">
                <div class="score-value">75%</div>
                <div class="score-label">Detail Requirements</div>
                <div class="score-context">1–1.5 / 2 covered</div>
            </div>
        </div>

        <div class="content">
            <!-- Executive Summary -->
            <div class="section">
                <h2 class="section-title">Executive Summary</h2>
                <div class="highlight">
                    <strong>This is a strong, execution-ready plan with near-perfect coverage.</strong> The plan achieves 98.48% overall coverage, including 100% of all critical requirements. Three narrow gaps in AI behavioral specification (concept ordering/diversity, pool sizing, quality validation) remain, but these are implementation details, not architectural risks. With minor specification refinements, this plan is ready for development.
                </div>
            </div>

            <!-- Coverage Overview -->
            <div class="section">
                <h2 class="section-title">Coverage by Functional Area</h2>
                <div class="coverage-matrix">
                    <div class="matrix-cell full">
                        <div>Benchmark & Isolation</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">17/17 ✓</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Data & Persistence</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">20/20 ✓</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Navigation</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">4/4 ✓</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Collection Home & Search</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">9/9 ✓</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Detail & Relationship UX</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">14/14 ✓</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Ask Chat</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">10/10 ✓</div>
                    </div>
                    <div class="matrix-cell partial">
                        <div>Concepts & Alchemy</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">8/10 ⚠</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>AI Voice & Quality</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">6/7 ⚠</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Person Detail</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">4/4 ✓</div>
                    </div>
                    <div class="matrix-cell full">
                        <div>Settings & Export</div>
                        <div style="font-size: 0.85rem; margin-top: 0.5rem;">4/4 ✓</div>
                    </div>
                </div>
            </div>

            <!-- Strengths -->
            <div class="section">
                <h2 class="section-title">What's Excellent</h2>
                <div class="strength-cluster">
                    <strong>✓ Infrastructure & Data Isolation (Perfect)</strong>
                    <p>The plan demonstrates crisp understanding of namespace isolation, user identity scoping, environment-driven secrets, and the auth migration path. Every baseline requirement is explicitly addressed with concrete implementation details (Supabase schema with RLS, dev auth injection via header, server-only secrets, idempotent migrations).</p>
                </div>
                <div class="strength-cluster">
                    <strong>✓ Core Data Model (Excellent)</strong>
                    <p>Collection membership rules, auto-save triggers, status/interest mapping, timestamp-based conflict resolution, and cross-device sync are all articulated. The schema is clearly defined with merge rules explicit.</p>
                </div>
                <div class="strength-cluster">
                    <strong>✓ Feature Implementation (Strong)</strong>
                    <p>Every major feature area—Collection Home, Search, Detail, Ask, Alchemy, Explore Similar, Person Detail—is broken down into sections, components, and behavioral flows with sufficient detail to guide UI/UX design and backend API contracts.</p>
                </div>
                <div class="strength-cluster">
                    <strong>✓ AI Persona & Voice (Good)</strong>
                    <p>The plan correctly treats AI voice as config-driven, references ai_personality_opus.md and ai_prompting_context.md, and maintains consistency across surfaces (Scoop, Ask, Alchemy, Concepts). Guardrails (spoiler-safe, opinionated, TV/movies-only) are clearly stated.</p>
                </div>
            </div>

            <!-- Gaps & Risks -->
            <div class="section">
                <h2 class="section-title">What's at Risk (Top 3 Gaps)</h2>
                <ul class="gap-list">
                    <li class="gap-item">
                        <strong>PRD-091: Discovery Quality Validation</strong>
                        The plan has monitoring (metrics, error rates, logging) but no explicit mention of testing concepts/recommendations against the discovery quality bar rubric or hard-fail gates that prevent shipping bad outputs. Responses could drift from spec without detection.
                        <em>Impact: Users experience inconsistent AI quality; QA can't enforce voice/integrity standards.</em>
                    </li>
                    <li class="gap-item">
                        <strong>PRD-077: Concept Ordering & Axis Diversity</strong>
                        The plan says "Return 8–12 concepts" but doesn't explain how they're ordered or how axis diversity is ensured. Without this, users might see weak or redundant concepts first.
                        <em>Impact: Concept picking UX feels random; "ingredient" mental model breaks down.</em>
                    </li>
                    <li class="gap-item">
                        <strong>PRD-082: Multi-Show Concept Pool Sizing</strong>
                        The plan mentions multi-show concepts should return a "larger option pool" but doesn't quantify it. Implementation ambiguity could lead to inconsistent UX or feature creep.
                        <em>Impact: Alchemy concept selection feels unpredictable; hard to test.</em>
                    </li>
                </ul>
            </div>

            <!-- Narrative Sections -->
            <div class="section">
                <h2 class="section-title">Detailed Assessment</h2>

                <div class="narrative-section">
                    <h3>Overall Posture</h3>
                    <p>This plan is <strong>exceptionally comprehensive and strategically sound</strong>. It achieves 98.48% coverage across the full requirement catalog, with 100% coverage of all 30 critical requirements. The plan is grounded in deep understanding of the PRD, maintains architectural rigor around data isolation and AI voice consistency, and lays out a credible three-phase delivery roadmap.</p>
                    <p>The three identified gaps are all in the `important` tier and are narrow, specification-level details rather than fundamental architectural or feature omissions. This is a plan that could be handed to a strong engineering team and executed with confidence, provided the specification details are tightened before coding begins.</p>