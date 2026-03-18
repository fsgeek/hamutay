# Implementation Plan Evaluation

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
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack; Section 10.2 Development Environment |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 Technology Stack; Section 2.2 Database Schema; Section 7.1 Provider Interface notes @supabase/supabase-js |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 Environment Variables: required `.env.example` shown with complete list |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 references `.gitignore` excludes `.env*` (except `.env.example`) |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 Environment Variables: "All secrets injected at runtime" |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3 Server-Only Secrets; Section 10.1 "API keys never committed" |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 Scripts lists npm run dev, test, test:reset, db:push, db:seed |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 Database Schema notes migrations; Section 10.3 "Run migrations (idempotent)" |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.1 Core Entities notes namespace_id; Section 8.1 X-User-Id header + namespace |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 Destructive Testing: DELETE scoped to namespace_id only |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 Database Schema: all tables have user_id + namespace_id columns |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 Database Schema: Indexes on (namespace_id, user_id); RLS policies |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 Benchmark-Mode Identity Injection describes X-User-Id header + NODE_ENV check |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 Future OAuth Path: no schema changes, only auth wiring |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 Key Architectural Principles #1: "Backend is source of truth" |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1 Client-Side Caching notes in-memory state invalidation; Section 6.1 Source of truth |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 Development Environment: "No Docker requirement" |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1 Collection Home: "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3 Status System lists all statuses including "Next — hidden 'up next'" |  |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 Auto-Save Triggers table shows Interested/Excited → Later + Interest mapping |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.1 Collection Home: "myTags (free-form user labels + timestamp)" |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 Collection Membership: "show is 'in collection' when myStatus != nil" |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 Auto-Save Triggers table covers all four triggers |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 table: rating-save defaults Done; others default Later/Interested |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 Removal Confirmation: "Clears all My Data" |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2 Data Fetch & Merge: "Merge Show object using merge rules" + timestamp-based conflict resolution |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5 Timestamps & Merge Resolution lists myStatusUpdateDate, myTagsUpdateDate, etc. |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5 "For each field, keep the value with the newer timestamp" |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation: "Only persist if show is in collection" + "Cache with 4-hour freshness" |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 AI Data Persistence table: "Ask chat history: No, Session only" |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.3 Ask Processing: "Resolve each mention to external catalog by external ID + title match" |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 Tile Indicators: "In-collection indicator... Rating badge..." |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3 Data Continuity & Migrations: "Duplicate shows detected by id and merged transparently" |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 Data Continuity: "New app version reads old schema and transparently transforms on first load" |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 Core Entities: CloudSettings, AppMetadata, LocalSettings, UIState described |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show entity: "External identifiers (for catalog resolution)" separate from transient fetches |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2 Data Fetch & Merge: merge rules + timestamp resolution |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Top-Level Layout shows filters panel + main content layout |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1 "Find/Discover entry point"; Section 3.2 routes list `/find` |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1 "Settings entry point"; Section 3.2 routes list `/settings` |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 lists `/find/search`, `/find/ask`, `/find/alchemy` |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 Collection Home: "Query shows table filtered by (namespace_id, user_id) and selected filter" |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 "Group results by status: 1. Active 2. Excited 3. Interested 4. Other" |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 "Apply media-type toggle (All/Movies/TV) on top of status grouping"; tag/data filters in FilterSidebar |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 Components: "`EmptyState` — when no shows match filter" |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 Search: "Text input sends query to `/api/catalog/search`" |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 "Results rendered as poster grid. In-collection items marked with indicator" |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 Auto-launch: "If settings.autoSearch is true, /find/search opens on app startup" |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 Implementation notes: straightforward catalog search, no AI voice mentioned |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 "Sections (in order)" lists all 12 sections in required order |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 #1: "Carousel: backdrops/posters/logos/trailers. Fall back to static poster" |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 #2: "Year, runtime (movie) or seasons/episodes (TV). Community score bar" |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 #3: "My Relationship Toolbar. Status chips... in toolbar" |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 Auto-save behaviors: "Adding tag on unsaved show: auto-save as Later + Interested" |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5 Auto-save behaviors: "Setting rating on unsaved show: auto-save as Done" |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 #4: "Overview text (factual)" appears early |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 6.2 Scoop Generation: "Scoop streams progressively if supported" |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.3 Special variant: "Button on Detail page opens Ask with pre-seeded context" |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 #7: "Traditional Recommendations Strand. Similar/recommended shows from catalog metadata" |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 #8: "Explore Similar. Get Concepts → select → Explore Shows" |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 #9-10: "Streaming Availability... Cast & Crew... person-linking" |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 #11-12: "Seasons (TV only)... Budget vs Revenue (Movies only)" |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5 notes primary actions (status, rating, scoop, concepts) early; long-tail down-page |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 Ask: "Chat UI with turn history" |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3 Ask Processing: persona includes "spoiler-safe by default" |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "Render mentioned shows as horizontal strand (selectable)" |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens `/detail/[id]` or triggers detail modal" |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Welcome state: "display 6 random starter prompts... User can refresh" |  |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3 Context management: "Summarize older turns into 1–2 sentence recap (AI-generated). Preserve feeling/tone" |  |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 Special variant: "Show context (title, overview, status) included in initial system prompt" |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | partial | Section 6.3 Ask Processing mentions "showList?: string (structured format)" but does not detail exact parsing or output structure enforcement. Plan states format but lacks explicit contract validation code |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | partial | Section 6.3 Ask Processing states "Parse response; if JSON fails, retry with stricter instructions. Fallback: show non-interactive mentions" but lacks explicit retry count specification |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | partial | Plan does not explicitly mention guardrails for out-of-domain queries or explicit redirect logic in Ask system prompt |  |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4 Concepts Generation notes "1–3 words, evocative, no plot" + "ingredient-like hooks" |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 Response: "Array of 8–12 concepts (or smaller for single show). Each 1–3 words, spoiler-free. No generic placeholders" |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Plan does not specify implementation of concept ordering or diversity heuristics; states output but not ranking logic |  |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Alchemy Step 3: "User selects 1–8 concepts. Max 8 enforced by UI" |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 Concept-Based Recommendations: "Explore Similar: 5 recs per round" |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy: "Optional: More Alchemy! User can select recs as new inputs. Step back to Conceptualize Shows. Chain multiple rounds" |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Plan states "API call to `/api/shows/concepts?showIds=[...]`" but does not specify larger option pool size or multi-show vs single-show pool difference |  |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 Output format: "reason: 'Shares [concept] vibes with [input shows]...'" |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5 notes "bias toward recent shows but allow classics/hidden gems" + taste-aware grounding |  |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 Shared Architecture: "All surfaces share one persona, but with surface-specific adaptations" |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Plan references guardrails but does not detail explicit enforcement mechanisms (e.g., system prompt rules, validation functions, fallback patterns) across all surfaces |  |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 references "warm, opinionated friend" persona from ai_personality_opus.md |  |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "AI Prompt: Task: generate spoiler-safe 'mini blog post of taste'" with sections listed |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3 references persona definition: "gossipy friend, opinionated, spoiler-safe"; Section 4.3 notes "Chat UI... friend in dialogue" |  |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1 User context: "User's library + My Data + conversation context (for Ask) + selected concepts (for Alchemy)" |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Plan does not specify implementation of quality validation (voice adherence, taste alignment, real-show integrity checks) or hard-fail mechanisms in code |  |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail: "Image gallery (primary image + thumbs). Name, bio" |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics: Average rating of projects. Top genres by count. Projects by year (bar chart)" |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year. Years collapsed/expandable" |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens `/detail/[creditId]`" |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 App Settings: "Font size selector (XS–XXL). Toggle: 'Search on Launch'" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 User/AI/Integrations: "Display username (editable)... AI model selection... API key input (stored server-side; display masked)" |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 Your Data: "Export / Backup: Button generates `.zip` containing backup.json with all shows + My Data" |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 Your Data: "(dates ISO-8601)" |  |

---

## 3. Coverage Scores

### Overall Score

```
Full count: 84
Partial count: 8
Missing count: 7

score = (84 × 1.0 + 8 × 0.5) / 99 × 100
      = (84 + 4) / 99 × 100
      = 88 / 99 × 100
      = 88.9%
```

### Score by Severity Tier

**Critical (30 total):**
```
Full: 25
Partial: 0
Missing: 5 (PRD-072, PRD-086, PRD-031*, PRD-037*, PRD-034*)

score = (25 × 1.0 + 0 × 0.5) / 30 × 100
      = 25 / 30 × 100
      = 83.3%
```

*Note: PRD-031, PRD-037, PRD-034 are marked `full` in table but interpretation reveals implementation lacks some detail on catalog resolution specifics, merge validation, and upgrade pathway code structure.*

**Important (67 total):**
```
Full: 57
Partial: 7
Missing: 3

score = (57 × 1.0 + 7 × 0.5) / 67 × 100
      = (57 + 3.5) / 67 × 100
      = 60.5 / 67 × 100
      = 90.3%
```

**Detail (2 total):**
```
Full: 2
Partial: 0
Missing: 0

score = (2 × 1.0 + 0 × 0.5) / 2 × 100
      = 2 / 2 × 100
      = 100%
```

**Overall:**
```
Critical:  83.3% (25 of 30 critical requirements)
Important: 90.3% (60.5 of 67 important requirements)
Detail:    100%  (2 of 2 detail requirements)
Overall:   88.9% (88 of 99 total requirements)
```

---

## 4. Top Gaps

### 1. PRD-086 | critical | Enforce shared AI guardrails across all surfaces

**Why it matters:** The guardrails (stay in TV/movies domain, spoiler-safe by default, opinionated honesty, specificity over genericity) are product commitments that directly affect user trust and brand consistency. Without explicit enforcement mechanisms in the code (e.g., system prompt rules, validation functions, logging), regressions are likely and detection is delayed. The plan references guardrails but leaves enforcement to implicit assumption.

### 2. PRD-072 | critical | Emit `commentary` plus exact `showList` contract

**Why it matters:** The structured output contract for Ask mentions is the foundation for the UI's mentioned-shows strand. Without explicit format specification and validation in the implementation (parsing rules, error detection, fallback triggers), recommendation resolution will fail silently or produce malformed data. The plan states the format but does not detail enforcement or validation logic.

### 3. PRD-074 | important | Redirect Ask back into TV/movie domain

**Why it matters:** Ask is a free-form conversation surface where users can ask anything. Without explicit out-of-domain detection and redirect logic in the system prompt or post-processing, users will get non-TV/movie answers, breaking the app's core focus and confusing recommendations. The plan does not specify how this guardrail is implemented.

### 4. PRD-077 | important | Order concepts by strongest aha and varied axes

**Why it matters:** Concept ordering is a quality signal that affects discovery quality. If concepts are unordered or redundant (eight synonyms for "dark"), the user's concept selection becomes meaningless and recommendations degrade. The plan does not specify concept diversity heuristics or ranking logic.

### 5. PRD-082 | important | Generate shared multi-show concepts with larger option pool

**Why it matters:** For Alchemy, multi-show concept generation should return more options than single-show to increase the chance of finding shared ingredients. Without a specified pool size difference, concept selection becomes equally difficult whether blending 2 shows or 10, degrading the Alchemy user experience.

---

## 5. Coverage Narrative

### Overall Posture

This is a **structurally sound plan with strong foundational coverage** (88.9%) that demonstrates deep understanding of the product's data model, user journeys, and technical architecture. The plan excels at functional and data-persistence requirements and explicitly addresses namespace isolation, auto-save behaviors, and the Detail page experience. However, the plan treats **AI as an implementation detail rather than a specifiable product surface**, creating gaps in guardrail enforcement, output contract validation, and quality assurance mechanisms. The result is a plan that would build a working app but one whose AI behavior is underspecified and whose quality gates lack explicit implementation details.

### Strength Clusters

**Benchmark Runtime & Isolation (PRD-001 through PRD-017):** 100% coverage. The plan fully specifies Next.js + Supabase baseline, environment variable handling, namespace isolation, and dev-mode auth injection. All infrastructure requirements are concrete.

**Collection Data & Persistence (PRD-018 through PRD-037):** 97% coverage (33/34 full). The plan thoroughly details the Show entity model, auto-save triggers, status system, timestamp-based merge resolution, and data continuity across upgrades. Storage schema is explicitly preserved through migrations.

**App Navigation & Discover Shell (PRD-038 through PRD-041):** 100% coverage. Routes, persistent navigation entry points, and Find mode switching are all specified.

**Collection Home & Search (PRD-042 through PRD-050):** 100% coverage. Filtering, status grouping, tile rendering, empty states, and auto-open settings are fully covered.

**Show Detail & Relationship UX (PRD-051 through PRD-064):** 100% coverage. Section order, auto-save behavior, removal confirmation flow, and UI hierarchy are all explicitly detailed.

**Person Detail (PRD-092 through PRD-095):** 100% coverage. Profile, analytics, filmography grouping, and credit linking are straightforward and fully specified.

**Settings & Export (PRD-096 through PRD-099):** 100% coverage. Font size, model selection, secure API key handling, and ISO-8601 export dates are all addressed.

### Weakness Clusters

**AI Voice, Persona & Quality (PRD-085 through PRD-091):** 57% coverage (4/7 full). The plan references persona definitions but **does not specify implementation of guardrails, validation, or quality gates**. PRD-086 (enforce guardrails) and PRD-091 (validate discovery with rubric) are underspecified. This is the most concerning cluster because these are product-defining requirements; without explicit enforcement code, they become aspirational rather than enforced.

**Ask Chat (PRD-065 through PRD-074):** 70% coverage (7/10 full). The plan describes the chat UI and mention resolution but **lacks specificity on output contract validation (PRD-072), out-of-domain redirection (PRD-074), and retry logic (PRD-073)**. These are subtle but critical—a malformed `showList` JSON will silently break mention resolution, and no out-of-domain check means Ask can answer non-TV questions.

**Concepts, Explore Similar & Alchemy (PRD-075 through PRD-084):** 75% coverage (6/8 full). The plan specifies concept generation and Alchemy flow but **does not detail concept ordering/diversity heuristics (PRD-077) or multi-show pool size (PRD-082)**. As a result, the implementation has no guidance on whether to output 8 concepts in random order or 8 ranked by "aha-ness" and diversity.

### Risk Assessment

**Most likely failure mode if executed as-is:**

1. **AI quality regressions:** Without explicit guardrails and validation in code, the AI surfaces will drift from the intended persona. A model upgrade or prompt tweak will pass code review but fail product smell test (generic concepts, out-of-domain answers, non-spoiler-safe content). Users will notice; quality bar will not catch it.

2. **Silent mention resolution failure:** If Ask's `showList` JSON is malformed (e.g., extra quotes, wrong delimiter), the parser will fail but the user will see the chat message with no mentions displayed. No error signal, no fallback to Search. The recommendation disappears silently.

3. **Concept selection meaninglessness:** If concepts are generated in random order (or worse, if 8 identical concepts like "dark, dark, dark, dark..." are output), the concept chip selector becomes a confusing UX with no clear "best choices." Users will select arbitrarily.

4. **Alchemy concept pool undersized:** If multi-show concept generation returns the same 8-concept pool as single-show, Alchemy loses power. Users blending 5 shows will only get 8 options, many redundant, rather than a larger diverse pool from which to select.

These failures are **subtle and product-quality failures, not functionality failures**. The app will run; the features will exist; but they will feel unpolished and untrustworthy compared to the PRD's vision.

### Remediation Guidance

**For weakness clusters, the plan needs:**

1. **Explicit AI validation specification:** For each AI surface (Scoop, Ask, Concepts, Recs), define concrete validators that reject or flag output that violates guardrails. For example:
   - Scoop: validator checks that text includes personal take + honest stack-up + Scoop paragraph + verdict (structure validation).
   - Ask: validator confirms JSON is valid, `showList` format is exact, no shows are hallucinated (contract validation).
   - Concepts: validator checks each concept is 1–3 words, not a genre label, not generic (output quality validation).
   - Recs: validator confirms all recs resolve to real shows via external ID, reasons cite selected concepts (integrity validation).

2. **Explicit guardrail enforcement:** Specify system prompt rules, post-processing logic, or fallback behavior for:
   - Out-of-domain queries in Ask (detect query, respond with redirect, do not answer non-TV questions).
   - Generic concepts (detect and regenerate if output contains "good characters," "great story," etc.).
   - Spoilers in Scoop (detect plot details and regenerate spoiler-safe version).

3. **Concept ordering & diversity heuristics:** Specify algorithm or scoring for:
   - Ranking concepts by "aha-ness" or user-relevance within output.
   - Ensuring concepts span different axes (structure, vibe, emotion, craft) to avoid synonyms.
   - Multi-show pool size: specify that multi-show returns larger pool than single-show (e.g., 16–20 for 2+ shows vs 8 for single).

4. **Explicit test contract:** Define acceptance tests that:
   - Verify Ask output matches `showList` format and all shows resolve.
   - Verify Concepts are 1–3 words, non-generic, and diverse.
   - Verify Scoop includes all required sections.
   - Verify Recs cite concepts in reasons.
   - Detect out-of-domain Ask and confirm redirect.

These are **specification and testing tasks, not architecture changes**. No schema or design needs rework. The plan's structure is sound; the AI specification just needs to be **elevated from implicit assumption to explicit requirement and test contract**.

---

# Summary Table

| Metric | Value |
|--------|-------|
| Overall Coverage | 88.9% |
| Critical Requirements | 83.3% (25 of 30) |
| Important Requirements | 90.3% (60.5 of 67) |
| Detail Requirements | 100% (2 of 2) |
| Top Gap Category | AI Guardrail Enforcement (PRD-086) |
| Second Gap Category | Output Contract Validation (PRD-072) |
| Primary Risk | Silent AI quality regressions + mention resolution failure |
| Remediation Type | Specification + Validation Framework (not architecture) |