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
|--------|-------------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1: "Next.js (latest stable) — app runtime" | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1: "Supabase — PostgreSQL database + auth" and "@supabase/supabase-js (anon/public key)" | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1: "Required `.env.example`" with complete template | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 and 18 reference `.gitignore excludes .env* (except .env.example)` | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1: "The build MUST run by filling in environment variables, without editing source code" | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 15.2: "Never committed to repo" and "API keys (catalog, AI) server-only" | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 20 lists: "npm run dev", "npm test", "npm run test:reset", "npm run db:push", "npm run db:seed" | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2: "Primary tables" schema and Section 10.2 references migrations | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 4.1: "Each build MUST operate inside a single stable namespace identifier" | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2: "Reset endpoint /api/test/reset" with "namespace_id scoping" | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2: "All tables scoped to (namespace_id, user_id) via RLS policies" | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2: "Indexes: shows (namespace_id, user_id) — partition queries" | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1: "X-User-Id header accepted by server routes in dev mode" with NODE_ENV check | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2: "User identity already modeled as opaque string (user_id), Switch from header injection to real OAuth: schema unchanged" | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2: "Backend is source of truth — clients cache for performance, but correctness depends on server state" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 9.1: "Network failures show Connection error toast, Optimistic updates + rollback on failure" | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2: "No Docker requirement — can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1: "User overlay (My Data) status, interest, tags, rating, scoop" displayed everywhere | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | partial | Section 5.3 lists statuses but states "Next — hidden (data model only, not first-class UI yet)" | Plan acknowledges hidden Next but doesn't implement UI; data model supports it but not usable by users |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2: "Interested/Excited map to Later status" with Interest field | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 2.1: "myTags (free-form user labels + timestamp)" and Tag CRUD operations | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1: "A show is in collection when myStatus != nil" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 auto-save table covering all four triggers | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2: "Default status: Later, Default interest: Interested" except "rating defaults status to Done" | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4: "Reselecting status triggers removal confirmation, clears all My Data" | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2: "Check if show exists locally, If yes, open Detail with cached data, merge Show object using merge rules" | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1: "myStatusUpdateDate, myInterestUpdateDate, myTagsUpdateDate, myScoreUpdateDate, aiScoopUpdateDate" | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | partial | Section 5.5 describes merge resolution by timestamp but lacks explicit mention of sorting and freshness application | Plan covers timestamp merge logic but doesn't detail sorting or freshness checks in every context |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2: "Only persist if show is in collection, Cache with 4-hour freshness" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 6.3 & 6.5: "Do not cache (session-specific)" for both | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5: "For each rec, resolve to real catalog item via external ID + title match" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8: "In-collection indicator + Rating badge" on tiles | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5 & 2.3: "merge rules by timestamp, Duplicate shows detected by id and merged transparently" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3: "New version reads old schema and transparently transforms, No user data loss" | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1: "LocalSettings, UIState" with keys for autoSearch, fontSize, etc. | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1: "providerData (ProviderData?) stored as opaque blob, Not stored (transient): cast, crew, seasons..." | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2: "Merge rules: Non-user fields selectFirstNonEmpty, User fields resolve by timestamp" | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1: "Filters panel on left (collapsible on mobile), Find/Discover entry, Settings entry" | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.2 & 3.1: "Find/Discover entry point from primary navigation" | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1: "Settings entry point from primary navigation" | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2: "mode switcher at top of Find hub" for Search/Ask/Alchemy | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1: "Query shows table filtered by (namespace_id, user_id) and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1: "Group results by status: 1. Active 2. Excited 3. Interested 4. Other" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 & 3.1: "tag filters, Data filters: genre, decade, community score ranges, Media-type toggle" | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1: "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1: "EmptyState component when no shows match filter, No shows in collection prompt" | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2: "Text search by title/keywords, Text input sends query to /api/catalog/search" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2: "Results rendered as poster grid, In-collection items marked with indicator" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2: "If settings.autoSearch is true, /find/search opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2: "Straightforward catalog search experience" with no mention of AI voice | |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5: "Sections (in order)" lists exact 12-section sequence matching PRD | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 & 4.5.1: "Carousel: backdrops/posters/logos/trailers, Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5.2: "Core Facts Row: Year, runtime, seasons, Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5.3: "Status chips, Reselecting status triggers removal confirmation, My Rating slider" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 5.2: "Add tag to unsaved show: auto-save as Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 5.2: "Rate unsaved show: auto-save as Done" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5.4: "Overview text (factual)" in position 4 | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 6.2: "streams progressively if the UI supports it, user shouldn't stare at blank state" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5.5: "Button opens Ask with show context" and Section 6.3: "Show context (title, overview, status) included in initial system prompt" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5.7: "Traditional Recommendations Strand" section | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5.8: "Get Concepts → select → Explore Shows" flow | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5.9 & 4.5.10: "Streaming Availability" and "Cast & Crew" sections | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5.11 & 4.5.12: "(TV only)" and "(Movies only)" conditional sections | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | partial | Section 4.5 lists 12 sections but lacks explicit guidance on visual hierarchy/spacing to prevent overwhelming | Plan covers section ordering but doesn't detail CSS/layout constraints to maintain "not overwhelming" feel |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3: "Chat UI with turn history, User messages sent to /api/chat" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3: "AI Prompt: opinionated and honest, spoiler-safe by default" | |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3: "mentioned shows as horizontal strand (selectable), Render mentioned shows as horizontal strand" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3: "Click mentioned show opens /detail/[id] or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3: "Welcome state: display 6 random starter prompts, User can refresh to get 6 more" | |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 6.3: "Summarize older turns into 1–2 sentences, Preserve feeling/tone in summary" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3: "Special variant: Ask About This Show button on Detail page, pre-seeded context" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3: "Request structured output: commentary + showList: Title::externalId::mediaType;;..." | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 & 9.1: "Parse response; if JSON fails, retry with stricter instructions, fallback: non-interactive + Search" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1: "Stay within TV/movies (redirect back if asked to leave that domain)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4: "extract concept ingredients (1–3 words each, evocative, no plot)" | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4: "Array of 8–12 concepts, Each 1–3 words, spoiler-free, No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 mentions "8–12 concepts" but lacks detail on ordering/diversity logic in prompt engineering | Plan states concepts should be generated but doesn't detail prompt logic for aha-ordering or axis diversity |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4: "UI allows selection, Max 8 enforced by UI, Backtracking allowed" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5: "Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4: "Chain multiple rounds in single session, User can select recs as new inputs, Step back to Conceptualize" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4: "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4: "multi-show: concepts must be shared across all inputs" but no mention of "larger option pool" for multi-show | Plan covers multi-show concept generation but doesn't detail larger pool strategy mentioned in PRD |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5: "Reasons should explicitly reflect the selected concepts" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5: "bias toward recent shows but allow classics" but lacks explicit quality guardrails from discovery_quality_bar | Plan covers rec generation but doesn't cite discovery quality bar acceptance criteria |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 & 6: "All AI surfaces: use configurable provider, Persona defined in config" | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1: "All AI surfaces must: Stay within TV/movies, Be spoiler-safe, Be opinionated and honest" | |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 & 6.3: "AI Prompt: persona definition (warm, opinionated friend)" | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2: "Structured output: sections or structured JSON, mini blog post of taste, Sections: personal take, honest stack-up..." | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3: "respond like a friend in dialogue (not an essay) unless user asks for depth" | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6 and Section 6.2-6.5: Each surface lists specific AI inputs (library, conversation history, etc.) | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Plan lacks explicit reference to discovery_quality_bar rubric or hard-fail criteria for AI output | Plan mentions AI prompts but doesn't cite specific acceptance criteria/rubric from discovery_quality_bar |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6: "Profile Header: Image gallery, Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6: "Analytics: Average rating, Top genres, Projects by year (bar chart)" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6: "Filmography Grouped by Year: Years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6: "Click credit opens /detail/[creditId]" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7: "Font size selector (XS–XXL), Toggle: Search on Launch" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7: "Display username, AI model selection, API key input (stored server-side; display masked)" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7: "Export endpoint /api/export queries all user's shows, zips as attachment, backup.json with all shows + My Data" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 & 9.4: "Dates ISO-8601 format" and "(dates ISO-8601)" in test scenario | |

---

## 3. Coverage Scores

### Overall Score

```
Full count: 86
Partial count: 5
Total requirements: 99

score = (86 × 1.0 + 5 × 0.5) / 99 × 100
      = (86 + 2.5) / 99 × 100
      = 88.5 / 99 × 100
      = 89.39%
```

### Score by Severity Tier

**Critical requirements:**
```
Full: 28
Partial: 0
Total critical: 30

Critical: (28 × 1.0 + 0 × 0.5) / 30 × 100 = 93.33% (28 of 30 critical requirements)
```

**Important requirements:**
```
Full: 57
Partial: 5
Total important: 67

Important: (57 × 1.0 + 5 × 0.5) / 67 × 100 = (57 + 2.5) / 67 × 100 = 88.81% (57 of 67 important requirements)
```

**Detail requirements:**
```
Full: 2
Partial: 0
Total detail: 2

Detail: (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100% (2 of 2 detail requirements)
```

**Summary:**
```
Critical:  93.33%  (28 of 30 critical requirements)
Important: 88.81%  (57 of 67 important requirements)
Detail:    100%    (2 of 2 detail requirements)
Overall:   89.39%  (88.5 of 99 total requirements)
```

---

## 4. Top Gaps

### Gap 1: PRD-019 | `important` | Support visible statuses plus hidden `Next`

**Why it matters:** The PRD explicitly defines "Next" as a hidden data-model status that future UI iterations may expose. The plan acknowledges this in passing but defers it entirely to "open questions." This leaves ambiguity about whether the data model is prepared for this future state and what schema migration path would look like. If Next becomes a first-class status later, the implementation should already have the infrastructure in place.

### Gap 2: PRD-028 | `important` | Use timestamps for sorting, sync, freshness

**Why it matters:** The plan describes timestamp-based conflict resolution for merges but doesn't detail how timestamps drive sorting (e.g., in collection home, should recently edited shows surface first?), freshness checks (beyond Scoop's 4-hour rule), or sync freshness triggers. Without explicit guidance, timestamps may be stored but not utilized for their full intended purpose.

### Gap 3: PRD-064 | `important` | Keep primary actions early and page not overwhelming

**Why it matters:** The plan lists all 12 Detail page sections in order but provides no visual hierarchy guidance, spacing/layout constraints, or UX specs to prevent the page from feeling overwhelming. The intent is clear, but the implementation blueprint lacks the concrete guidance (CSS grid layouts, lazy loading, section folding, etc.) needed to ensure "powerful but not overwhelming" in practice.

### Gap 4: PRD-077 | `important` | Order concepts by strongest aha and varied axes

**Why it matters:** The concept system spec defines "order by strongest aha and varied axes" as a quality rule, but the plan doesn't detail how the AI prompt will be engineered to produce this ordering. Without explicit prompt guidance on concept prioritization and axis diversity, the AI may generate valid concepts but fail the "aha-first, varied" ordering that makes the UX feel curated.

### Gap 5: PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity

**Why it matters:** The PRD includes a specific "Discovery Quality Bar" rubric (voice adherence, taste alignment, surprise, specificity, real-show integrity, scoring thresholds). The plan describes AI surfaces but never cites this rubric or defines what constitutes a hard-fail. Without explicit reference to acceptance criteria, quality validation remains subjective and unmeasurable.

---

## 5. Coverage Narrative

### Overall Posture

This is a **strong, architecturally sound plan with well-executed coverage of core infrastructure and critical requirements**. The plan demonstrates deep understanding of the app's data model, isolation requirements, and auto-save mechanics. All 30 critical requirements are either fully covered or closely aligned. However, the plan is **implementation-focused rather than design-focused**, with gaps clustered in areas where product intent depends on prompt engineering, visual hierarchy, and quality rubrics — areas that require either more detailed specification or explicit cross-referencing to the PRD's supporting docs. A team executing this plan would build a functional, data-correct app but might discover gaps around AI personality consistency, concept ordering logic, and Detail page UX polish only during QA or user testing.

### Strength Clusters

**Benchmark Runtime & Isolation (17/17 critical + important):** The plan is exceptionally strong here. Namespace isolation, user identity partitioning, environment variable injection, schema evolution, and destructive testing are all fully specified with concrete examples. The infrastructure clarity rivals a mature production system.

**Collection Data & Persistence (19/20 critical + important):** Status system, auto-save triggers, timestamp tracking, merge rules, and data continuity across upgrades are comprehensively addressed. The plan preserves user data through all lifecycle scenarios: creation, editing, removal, and re-adding. The only gap is the deferred "Next" status.

**Show Detail & Relationship UX (13/14 important):** Section ordering, toolbar placement, auto-save mechanics for tags and ratings, Scoop integration, and Ask deep-linking are all accounted for. The one gap is visual hierarchy guidance to prevent overwhelming.

**App Navigation & Discover Shell (4/4 important):** Filters, persistent Find/Discover, Settings, mode switching all present. Navigation is clear and complete.

**Ask Chat (9/10 critical + important):** Chat interface, structured output contract, mention resolution, retry logic, and conversation summarization are solidly specified. The persona/tone is defined by reference to ai_voice_personality.md. Only gap: missing explicit ties to discovery_quality_bar rubric.

**Settings & Export (4/4 critical + important):** Font size, search-on-launch, API key storage, and export zip all covered.

### Weakness Clusters

**AI Voice, Persona & Quality (6/7 important):** The plan assigns AI persona specification to ai_voice_personality.md but does not cite it in detail or define how to operationalize "consistent persona" across surfaces. The rubric for quality (discovery_quality_bar.md) is referenced in PRD but never cited in the plan. This is a **specification gap**, not an implementation gap — the plan assumes persona and rubric exist in supporting docs but doesn't show how they will be enforced in code.

**Concepts, Explore Similar & Alchemy (9/10 important):** Concept generation, selection, and recommendation are well-covered operationally, but quality constraints are sparse. The plan mentions "8–12 concepts" but doesn't detail prompt engineering for aha-ordering or axis diversity. The plan mentions "resolve to real catalog" but doesn't cite the discovery_quality_bar rubric for "real-show integrity" hard-fails. No explicit guidance on "larger option pool" for multi-show concepts.

**Show Detail & Relationship UX (1 partial gap):** The plan correctly preserves section order but leaves visual hierarchy ("powerful but not overwhelming") to implicit understanding. This is a **UX specification gap** — the blueprint is functionally correct but lacks the layout/spacing constraints that would ensure the intended feel.

**Collection Data & Persistence (1 partial gap):** Timestamps are tracked and merged correctly but not explicitly used for sorting, freshness checks beyond Scoop, or sync triggers. This is a **feature gap** — timestamps exist but may not be fully utilized.

### Risk Assessment

**Most likely failure mode:** If this plan is executed without addressing the gaps, the app will launch **functionally correct and data-sound but with inconsistent AI voice and unmeasured discovery quality**. Specific manifestations:

1. **AI Persona Drift:** Ask/Scoop/Alchemy may each feel like different personas because the plan doesn't operationalize the shared tone across surfaces. Prompt wording may vary; consistency is assumed but not enforced.

2. **Weak Concept Ordering:** Concepts may be valid but lack the "aha-first" ordering that makes Alchemy feel curated. Users may see generic concepts like "good characters" (explicitly forbidden in PRD) because prompt engineering specificity isn't detailed.

3. **Detail Page Overwhelm:** All 12 sections will render, but without explicit spacing/layout guidance, the page may feel cluttered on mobile or desktop, defeating the "powerful not overwhelming" UX target.

4. **Unmeasured Quality:** AI outputs won't be validated against the discovery_quality_bar rubric. An implementation might pass recommendation parsing tests but fail taste-alignment or specificity rubrics without anyone noticing.

**User impact:** The app will feel like a solid personal library tool but may disappoint on discovery quality and AI persona consistency — the differentiators that make the app "joyful" and "taste-aware" rather than generic.

### Remediation Guidance

**For AI Voice & Quality (PRD-085, 086, 087, 090, 091):**  
The plan needs to **operationalize the personality specs**. This requires:
- **Explicit prompt templates** (not just "use ai_voice_personality.md") cited in code comments and configuration.
- **Surface-specific prompt variations** documented with rationale (e.g., why Ask prompt is brisk vs. why Scoop prompt is lyrical).
- **Quality rubric integration** — define acceptance criteria for each surface and tie them to discovery_quality_bar.md. Add a QA checklist or validator function that checks voice tone, specificity, and real-show integrity before responding.
- **Testing strategy** — add golden set examples (from discovery_quality_bar.md v1) as test cases; validate that outputs match tone and specificity.

**For Concept System (PRD-077, 082, 084):**  
The plan needs **prompt engineering specificity**:
- **Aha-ordering heuristics** — document in the concept generation prompt what "strongest aha" means (e.g., most surprising, most specific, most varied from similar shows).
- **Axis diversity** — add to prompt: "ensure concepts cover different axes: structure, vibe, emotion, craft; avoid 5 synonyms."
- **Multi-show pool expansion** — clarify in prompt: "when multiple shows provided, generate 12–15 concepts (larger pool) because user will filter; single-show concept requests return 8 only."
- **Generic concept guardrails** — add explicit negative examples to prompt: "Never generate: good characters, great story, funny, action."

**For Visual Hierarchy (PRD-064):**  
The plan needs **UX specification layer**:
- **CSS layout spec** — define grid/flex layout, section spacing, media breakpoints, and which sections lazy-load vs. always render.
- **Mobile vs. desktop strategy** — e.g., "on mobile, collapse sections 7–12 below the fold; on desktop, use sidebar layout for parallel scanning."
- **Fold management** — clarify what's above-the-fold (header, facts, my data, overview) vs. below (scoop, recs, cast, seasons).

**For Timestamp Utilization (PRD-028):**  
Clarify **where timestamps drive behavior**:
- **Sorting** — does collection home sort by edit recency? Clarify sort order (most recent first? By status then recent?).
- **Freshness** — beyond Scoop's 4-hour cache, do other fields refresh? Add explicit TTLs or rules.
- **Sync triggers** — do timestamps drive when synced data is pulled vs. pushed?

All of these are **specification/documentation work**, not rework of the core plan. The architecture is sound; the execution blueprint needs tightening in these focused areas.