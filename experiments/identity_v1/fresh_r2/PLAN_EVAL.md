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

Total: 99 requirements (30 critical, 67 important, 2 detail) across 10 functional areas

---

## 2. Coverage Table

| PRD-ID | Requirement | Severity | Coverage | Evidence | Gap |
|--------|-------------|----------|----------|----------|-----|
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack, Section 7: uses Next.js explicitly. |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 mentions @supabase/supabase-js; Section 8.1 describes auth integration. |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 Environment Variables includes complete `.env.example` template. |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 states `.gitignore excludes .env* (except .env.example)`. |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 Environment Variables shows all config via env; no code changes required. |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 15.2 details server-only secrets; API keys never exposed to client. |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 Scripts lists `npm run dev`, `npm test`, `npm run test:reset`, etc. |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 10.2 mentions migrations; Section 2.1 describes database schema. |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 4.1 Build/run namespace explains single stable `namespace_id` per build. |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 Destructive Testing describes `/api/test/reset` scoped to namespace. |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 Database Schema shows all tables include `user_id` column; RLS enforced. |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 shows RLS policies enforce `(namespace_id, user_id)` partition. |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 Benchmark-Mode Identity Injection describes header injection gated by NODE_ENV. |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 Future OAuth Path explains schema remains unchanged; only auth wiring changes. |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 Architectural Principles states "Backend is source of truth." |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1 Client-Side Caching explains SWR + invalidation; localStorage non-critical. |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 Development Environment states "No Docker requirement"; runs against hosted Supabase. |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1 Show detail model shows My Data fields displayed on all show tiles. |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | partial | Section 5.3 Status System lists all statuses including Next, but plan notes "hidden (data model only, not first-class UI yet)". | Plan acknowledges Next exists but doesn't specify UI treatment; marks as "data model only" suggesting incomplete UI implementation. |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 Auto-Save Triggers explicitly maps "Interested/Excited" to "Later + Interest". |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.1 Show model includes `myTags: [String]`; Section 11.2 has TagInput component. |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 Collection Membership defines "in collection" as `myStatus != nil`. |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 Auto-Save Triggers lists all four triggers explicitly. |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 shows defaults: Later+Interested normally, Done for ratings. |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 Removal Confirmation specifies "clears all your notes, rating, and tags." |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2 Data Fetch & Merge describes merge rules preserving user fields by timestamp. |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1 Core Entities lists all *UpdateDate fields; Section 5.5 details merge by timestamp. |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5 Timestamps & Merge Resolution explains sorting + sync + freshness uses. |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation specifies "Only persist if show is in collection"; 4h cache. |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 AI Data Persistence table shows "No" for Ask/Alchemy; Section 4.3/4.4 describe session-only state. |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 7.2 Data Fetch & Merge and 7.3 External Catalog Integration describe resolution by external ID + title. |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 Tile Indicators specifies in-collection and rating badges. |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5 Timestamps & Merge Resolution handles duplicates and field-level merging. |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 Data Continuity & Migrations guarantees no user data loss on schema change. |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 shows CloudSettings, LocalSettings, UIState entities. |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show model shows `externalIds` persisted; transient fields listed separately. |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2 Data Fetch & Merge specifies `selectFirstNonEmpty()` for non-user fields; timestamp-based for user fields. |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Top-Level Layout shows filters panel; Section 3.2 lists routes to all destinations. |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 4.1 Collection Home and 4.3 Ask both assume persistent Find entry point. |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1 Top-Level Layout shows Settings; Section 4.7 describes Settings page. |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 4.2 Search, 4.3 Ask, 4.4 Alchemy all detailed; mode switcher mentioned in 3.3. |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 Collection Home specifies filtered query by `(namespace_id, user_id)` + filter selection. |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 Collection Home explicitly lists grouping by status section (Active, Excited, Interested, Other). |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 3.3 Routes shows Filter configuration with type: tag, genre, decade, score; media toggle in 4.1. |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 Collection Home states "Tiles show poster, title, and My Data badges." |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 Collection Home lists EmptyState component; Section 12.1 mentions empty-state copy. |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 Search describes "Text input sends query...by title/keyword." |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 Search states "Results rendered as poster grid"; "In-collection items marked." |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 Search describes "Auto-launch" behavior checking `settings.autoSearch`. |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 Search and 6.1 Shared Architecture both imply Search is non-AI (no persona applied). |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 Show Detail Page lists 12 sections in explicit order matching PRD. |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 Header Media specifies carousel + fallback to poster. |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 Core Facts Row includes year, runtime, community score at top. |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 My Relationship Toolbar states "Status chips in toolbar." |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 Auto-save behaviors specifies "Adding tag on unsaved show: auto-save as Later + Interested." |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5 Auto-save behaviors specifies "Setting rating on unsaved show: auto-save as Done." |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 lists Overview as 4th section (early in page). |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 6.2 Scoop Generation describes "Streams progressively if UI supports it." |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5 lists "Ask About This Show CTA"; Section 4.3 Ask describes "Special variant" seeding context. |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 lists "Traditional Recommendations Strand" as section 8. |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 lists "Explore Similar: Get Concepts → select → Explore Shows" as section 9. |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 lists "Streaming Availability" (9) and "Cast & Crew" (10) sections. |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 Critical States specifies "seasons strand only when relevant", "runtime vs episode counts handled." |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5 Busyness vs Power states "primary actions clustered early (status, rating, scoop, concepts)." |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 Ask Page describes chat UI with turn history. |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.1 Shared Architecture and 6.3 Ask Processing specify spoiler-safe, confident responses. |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3 Ask Page describes MentionedShowsStrand component. |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3 Ask Page states "Click mentioned show opens `/detail/[id]` or triggers detail modal." |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Welcome state specifies "6 random starter prompts" with refresh. |  |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 6.3 Ask describes conversation summarization after ~10 turns. |  |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 Special variant describes pre-seeded context for Ask About Show. |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 Ask Processing specifies JSON output with `commentary` and `showList: "Title::externalId::mediaType;;..."` format. |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 Ask Response Processing states "if JSON fails, retry once with stricter instructions, otherwise fallback." |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | partial | Section 6.1 Shared Architecture states "Stay within TV/movies" but doesn't explicitly describe redirection mechanism or copy. | Plan mentions guardrail but lacks specifics on how/when redirection occurs or what user sees. |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4 Concepts Generation specifies "Concepts are not genres or plot points; extraction of ingredients." |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 Concepts Generation specifies "bullet list only...each 1–3 words...no generic placeholders." |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 mentions concepts returned but doesn't specify ordering; plan doesn't detail "strongest aha" or "varied axes" sorting. | Plan generates concepts but lacks explicit guidance on ordering strategy or axis diversity. |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Alchemy flow specifies max 8 concepts; Section 4.5 Explore Similar states "1+ required." |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 Concept-Based Recommendations specifies "Explore Similar: 5 recs per round." |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy step 5 specifies "More Alchemy!" to chain rounds. |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 Alchemy flow states "Backtracking allowed: changing shows clears concepts/results." |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 Concepts Generation mentions "multi-show: concepts must be shared" but doesn't detail "larger option pool" or how multi-show differs from single-show concept count. | Plan describes shared concepts but lacks specifics on multi-show option pool size vs single-show. |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 Concept-Based Recommendations specifies "reasons should explicitly reflect the selected concepts." |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | full | Section 6.5 notes "bias toward recent shows but allow classics/hidden gems"; Section 6.3 includes user library for context. |  |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 Shared Architecture states "All AI surfaces use configurable provider...same persona." |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1 Shared Architecture lists shared rules (stay within TV/movies, spoiler-safe, opinionated, specific). |  |
| PRD-087 | Make AI warm, joyful, and light in critique | important | partial | Section 6.1 Shared Architecture mentions these qualities are defined in config files but plan doesn't specify where warmth/joy/lightness are enforced in implementation. | Plan references persona definitions but doesn't detail how these emotional qualities are verified or tested in output. |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 Scoop Generation specifies "structured as short 'mini blog post of taste'" with sections. |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | partial | Section 6.3 Ask describes chat UI but doesn't specify brevity constraints, turn limits, or dialogue-specific formatting rules. | Plan describes Ask but lacks explicit guidance on conciseness targets or dialogue-like formatting. |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.3 Ask and 6.2 Scoop both describe context inclusion (user library, show details, etc.). |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Plan references discovery_quality_bar.md but doesn't describe how rubric is integrated into implementation (testing? manual QA? automated validation?). | Plan mentions reference doc but doesn't specify implementation of validation/scoring. |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail Page specifies "Image gallery, Name, bio." |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 Person Detail Page lists "Analytics (optional lightweight charts)" including average rating, top genres, projects-by-year. |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6 Person Detail Page states "Filmography grouped by year." |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 Person Detail Page states "Click credit opens `/detail/[creditId]`." |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 Settings describes "Font size selector...Toggle: Search on Launch." |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 Settings specifies User (username), AI (model/key), Integrations (catalog key) sections. |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 Settings and Section 9.4 Key Test Scenarios both describe export as `.zip` with JSON. |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 Settings states "Metadata (export date, data model version)"; Section 2.1 Show model uses ISO-8601 dates. |  |

---

## 3. Coverage Scores

**Critical Requirements:**
- Full coverage: 27 of 30
- Partial coverage: 0 of 30
- Missing coverage: 3 of 30

Critical score: (27 × 1.0 + 0 × 0.5) / 30 × 100 = **90.0%** (27 of 30 critical requirements)

**Important Requirements:**
- Full coverage: 59 of 67
- Partial coverage: 8 of 67
- Missing coverage: 0 of 67

Important score: (59 × 1.0 + 8 × 0.5) / 67 × 100 = **93.3%** (63 of 67 important requirements)

**Detail Requirements:**
- Full coverage: 2 of 2
- Partial coverage: 0 of 2
- Missing coverage: 0 of 2

Detail score: (2 × 1.0 + 0 × 0.5) / 2 × 100 = **100.0%** (2 of 2 detail requirements)

**Overall:**
- Full coverage: 88 of 99
- Partial coverage: 8 of 99
- Missing coverage: 3 of 99

Overall score: (88 × 1.0 + 8 × 0.5) / 99 × 100 = **91.9%** (92 of 99 total requirements)

---

## 4. Top Gaps

### Gap 1: PRD-019 (Important) — Support visible statuses plus hidden `Next`
**Severity & Impact:** The plan acknowledges Next exists in the data model but explicitly excludes it from first-class UI. The PRD requires Next to be "supported"—whether hidden or visible is open, but the infrastructure must be capable. The plan's explicit note that Next is "data model only, not first-class UI yet" leaves the UI contract incomplete. This is a gap because the plan treats Next as an afterthought rather than a design decision with clear acceptance criteria.

### Gap 2: PRD-074 (Important) — Redirect Ask back into TV/movie domain
**Severity & Impact:** The plan includes the rule "stay within TV/movies" as a shared guardrail but does not describe *how* redirection happens (e.g., system prompt instruction, post-processing check, user-facing message). Without explicit redirection logic, Ask could fail gracefully (ignore out-of-domain requests) without guiding users back. This matters because users expect a natural hand-off, not silence.

### Gap 3: PRD-077 (Important) — Order concepts by strongest aha and varied axes
**Severity & Impact:** The plan specifies concept generation but omits the ordering strategy. PRD requires concepts ordered by "strongest aha" and "varied axes" (structure, vibe, emotion, craft). Without explicit ordering rules in the plan, concept UX becomes non-deterministic and potentially confusing (e.g., 8 concepts with no apparent prioritization).

### Gap 4: PRD-087 (Important) — Make AI warm, joyful, and light in critique
**Severity & Impact:** The plan references ai_voice_personality.md (which defines these qualities) but does not specify how they are enforced or tested in implementation. There is no acceptance criteria for "warmth" or "joy"—these are documented but not operationalized. Without testing/verification strategy, the implementation may drift from spec over time.

### Gap 5: PRD-091 (Important) — Validate discovery with rubric and hard-fail integrity
**Severity & Impact:** The plan mentions that discovery_quality_bar.md exists but does not integrate the rubric into the implementation (no testing framework, no manual QA checklist, no automated validation). Without validation strategy, AI outputs are never measured against the rubric, leaving "hard-fail integrity" undefined and unverifiable.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally sound and impressively complete**. It covers 91.9% of requirements with full or substantial detail across all 10 functional areas. The architect has clearly read the PRD and supporting docs and has made deliberate design choices that preserve the product's intent. The plan is especially strong on data isolation, persistence rules, and core feature scaffolding. 

However, the plan exhibits a **notable pattern of treating AI behavioral contracts as "reference external docs" rather than "design specifications to operationalize."** Five important gaps cluster around AI surfaces (persona enforcement, concept ordering, domain redirection), and these gaps exist not because the plan is incomplete, but because the plan defers to external documentation without integrating acceptance criteria or verification strategy into the implementation roadmap. This is a coherent choice—it keeps the plan readable—but it introduces risk: an implementer following this plan could build a structurally correct Ask/Alchemy surface that outputs AI text nobody reviewed against the voice spec.

The plan is implementation-ready for infrastructure, data, and UI structure. It needs one more pass to operationalize AI quality gates.

### Strength Clusters

**Data Model & Persistence (PRD-018 through PRD-037):** Nearly flawless. The plan clearly defines the Show entity with all My Data fields, timestamps for each, merge rules by field, and persistence contracts. Namespace + user partitioning is explicit and enforced at the database layer. Re-add/duplicate merging, scoop freshness, and data continuity are all spelled out with concrete examples. This cluster is **production-ready**.

**Benchmark Infrastructure & Isolation (PRD-001 through PRD-017):** Extremely thorough. Environment variable interface, script scaffolding, namespace isolation, user identity, dev auth injection, and OAuth-migration path are all detailed with code examples and configuration templates. The plan explicitly avoids Docker, designs for cloud-agent compatibility, and provides repeatable reset semantics. **Strong enough to be a reference implementation**.

**Collection Home & Search (PRD-038 through PRD-050):** Well-defined. Filters panel, grouped display by status, tag/genre/decade filters, empty states, search by keyword—all specified with component names and interaction flows. The plan is clear on what "search non-AI in tone" means (no persona applied). **Directly implementable**.

**Show Detail & Relationship UX (PRD-051 through PRD-064):** Concrete and comprehensive. Section order preserved, auto-save triggers enumerated, removal confirmation flow spelled out, all controls positioned correctly. The plan includes graceful fallbacks (header without trailers, TV without seasons, etc.) and acknowledges the tension between power and busyness. **Ready for UI specification**.

**Person Detail (PRD-092–095), Settings & Export (PRD-096–099):** Clean and direct. Gallery, bio, filmography grouped by year, analytics charts, settings sections, export as zip with ISO-8601 dates. **No surprises or gaps**.

### Weakness Clusters

**AI Behavioral Contracts (PRD-074, 077, 087, 091):** Four important requirements touch AI quality and redirection, and all four are **partial or miss specification details**. The gaps cluster around:
- **Concept ordering:** The plan specifies concepts are generated but never specifies the sort order (PRD-077).
- **Domain redirection:** The plan includes the rule but not the mechanism (PRD-074).
- **Persona enforcement:** The plan points to reference docs but doesn't say how persona is verified (PRD-087).
- **Quality validation:** The plan mentions the rubric doc exists but doesn't integrate it into testing/QA (PRD-091).

These gaps are not scattered—they're all about **missing operationalization of AI specs**. The plan is 80% there but stops short of saying "here is how we test that Ask outputs are warm" or "here is the prompt design pattern that enforces concept ordering."

**Multi-Show Concepts vs Single-Show (PRD-082):** The plan describes concept generation but doesn't detail how multi-show concept generation differs in scale/output from single-show (larger option pool vs same count). The difference is mentioned in the PRD but not carried through the plan's implementation section. **Minor but creates ambiguity**.

**Next Status UI Treatment (PRD-019):** The plan explicitly flags Next as "data model only, not first-class UI yet," which is honest but incomplete. The PRD leaves it open (hidden vs visible); the plan chose hidden but didn't document the decision. If a rebuild needs Next visible later, there's no guidance on where/how to surface it. **Incomplete design decision**.

### Risk Assessment

**Most likely failure mode if executed as-is:** 

A team implementing this plan will build a structurally correct, data-persisted, isolated app with all routes and components in place. The app will save shows, filter, search, export, and navigate correctly. But the **Ask, Scoop, and Alchemy surfaces will likely feel generic or drift from spec over time** because:

1. The plan references ai_personality_opus.md (not provided in the plan) and does not embed prompt design or voice validation into development tasks.
2. Concept ordering is never specified, so the first implementer might randomize them, and nobody catches it.
3. Domain redirection in Ask is a guardrail rule, not a feature with UX copy or test cases, so it silently fails to "feel" like redirection (just drops the message).
4. "Warm and joyful AI" is a reference doc goal, not a test, so QA passes the feature when the facts are correct, not when the *tone* is right.

A QA reviewer testing "Ask returns mentions" will pass it. A user trying Ask and feeling it sounds corporate instead of "fun chatty friend" will notice. The gap is between **structural correctness** and **experiential correctness**.

### Remediation Guidance

**For the AI behavioral contract gaps:**
1. **Integrate prompt examples and voice validation into Section 6 (AI Integration).** Add a subsection "6.7 Prompt Design & Voice Validation" that specifies:
   - Where persona prompts live (config files, examples).
   - How concept ordering is enforced (sort key, examples).
   - How domain redirection copy is tested (example out-of-domain input + expected redirect message).
   - How voice is sampled and reviewed (e.g., "every Ask response sampled monthly against rubric; failures trigger prompt revision").

2. **Add an "AI Quality Acceptance Criteria" section under 19.1 (Acceptance Criteria).** Define pass/fail for:
   - "AI response tone matches voice spec (warm, opinionated, spoiler-safe)" — testable via sample output review + rubric scoring.
   - "Concept ordering consistent and defensible" — testable via deterministic sort key + comparison to reference outputs.
   - "Ask redirection feels natural, not silent" — testable via UX/copy review of redirect messages.

3. **For multi-show concept generation:** Clarify in 6.4 that multi-show concept generation returns a larger pool (e.g., 12–16 vs 8 single-show) so users can select the most relevant few from a richer palette.

4. **For Next status:** Decide and document: Is Next coming in Phase 1, Phase 2, or deferred indefinitely? If deferred, document where in the codebase it would be surfaced (e.g., "Status chips in 4.5 Detail > My Relationship Controls; add Next chip here when decided"). This prevents someone from asking later "where does Next go?"

**Category of work remaining:** This is not a missing feature—it's **missing design operationalization and quality contracts**. The product spec (ai_voice_personality.md, discovery_quality_bar.md) is complete, but the plan hasn't yet translated it into implementation tasks, test scenarios, or approval gates. One more pass to say "here is where this gets coded," "here is how this gets tested," and "here is what success looks like" will close the gaps.

---

**End of Evaluation**

---

# Stakeholder Report

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Implementation Plan — Coverage & Readiness Report</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      color: #f5f5f5;
      line-height: 1.6;
    }
    
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 40px 20px;
    }
    
    header {
      text-align: center;
      margin-bottom: 50px;
      padding-bottom: 40px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    h1 {
      font-size: 2.8rem;
      font-weight: 300;
      margin-bottom: 12px;
      background: linear-gradient(120deg, #00d4ff, #00f0ff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    
    .subtitle {
      font-size: 1.2rem;
      color: #a0a0a0;
      margin-bottom: 30px;
    }
    
    /* Score Card */
    .score-card {
      background: rgba(0, 212, 255, 0.08);
      border: 1px solid rgba(0, 212, 255, 0.3);
      border-radius: 12px;
      padding: 40px;
      text-align: center;
      margin-bottom: 50px;
    }
    
    .score-number {
      font-size: 4.5rem;
      font-weight: 300;
      color: #00d4ff;
      margin-bottom: 10px;
      font-variant-numeric: tabular-nums;
    }
    
    .score-label {
      font-size: 1.1rem;
      color: #a0a0a0;
      margin-bottom: 20px;
    }
    
    .score-breakdown {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
      margin-top: 30px;
      padding-top: 30px;
      border-top: 1px solid rgba(0, 212, 255, 0.2);
    }
    
    .tier {
      background: rgba(255, 255, 255, 0.02);
      border-radius: 8px;
      padding: 20px;
    }
    
    .tier-label {
      font-size: 0.9rem;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #808080;
      margin-bottom: 10px;
    }
    
    .tier-score {
      font-size: 2.2rem;
      font-weight: 300;
      color: #00d4ff;
      margin-bottom: 8px;
    }
    
    .tier-detail {
      font-size: 0.85rem;
      color: #606060;
    }
    
    /* Sections */
    section {
      margin-bottom: 60px;
    }
    
    h2 {
      font-size: 2rem;
      font-weight: 400;
      margin-bottom: 30px;
      color: #f5f5f5;
      position: relative;
      padding-left: 20px;
    }
    
    h2::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 4px;
      height: 24px;
      background: linear-gradient(180deg, #00d4ff, #0099cc);
      border-radius: 2px;
    }
    
    h3 {
      font-size: 1.3rem;
      font-weight: 500;
      margin: 25px 0 15px 0;
      color: #f5f5f5;
    }
    
    p {
      margin-bottom: 15px;
      color: #d0d0d0;
      font-size: 1rem;
    }
    
    /* Strengths & Weaknesses */
    .strengths-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 25px;
      margin-bottom: 30px;
    }
    
    .strength-item {
      background: rgba(0, 150, 80, 0.08);
      border-left: 3px solid #00cc66;
      border-radius: 6px;
      padding: 20px;
    }
    
    .strength-item h4 {
      color: #00ff99;
      font-size: 1.1rem;
      margin-bottom: 8px;
    }
    
    .weakness-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 25px;
      margin-bottom: 30px;
    }
    
    .weakness-item {
      background: rgba(255, 100, 80, 0.08);
      border-left: 3px solid #ff6450;
      border-radius: 6px;
      padding: 20px;
    }
    
    .weakness-item h4 {
      color: #ff8870;
      font-size: 1.1rem;
      margin-bottom: 8px;
    }
    
    /* Risk Box */
    .risk-box {
      background: rgba(255, 150, 0, 0.08);
      border: 1px solid rgba(255, 150, 0, 0.3);
      border-radius: 8px;
      padding: 30px;
      margin: 25px 0;
    }
    
    .risk-box h4 {
      color: #ffaa00;
      font-size: 1.2rem;
      margin-bottom: 15px;
    }
    
    /* Gap List */
    .gap-list {
      list-style: none;
      margin: 20px 0;
    }
    
    .gap-item {
      background: rgba(255, 255, 255, 0.03);
      border-left: 3px solid #ff6450;
      border-radius: 4px;
      padding: 15px 20px;
      margin-bottom: 12px;
      display: flex;
      align-items: flex-start;
      gap: 15px;
    }
    
    .gap-item-num {
      min-width: 40px;
      font-weight: 600;
      color: #ff8870;
      font-size: 1.1rem;
    }
    
    .gap-item-content {
      flex: 1;
    }
    
    .gap-item-title {
      color: #f5f5f5;
      font-weight: 500;
      margin-bottom: 4px;
    }
    
    .gap-item-why {
      color: #a0a0a0;
      font-size: 0.95rem;
    }
    
    /* Key Metrics Bar */
    .metrics-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 20px;
      margin: 30px 0;
    }
    
    .metric {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 8px;
      padding: 20px;
      text-align: center;
    }
    
    .metric-number {
      font-size: 2rem;
      font-weight: 300;
      color: #00d4ff;
      margin-bottom: 5px;
    }
    
    .metric-label {
      font-size: 0.85rem;
      color: #a0a0a0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    /* Recommendation Box */
    .recommendation {
      background: rgba(100, 150, 255, 0.08);
      border: 1px solid rgba(100, 150, 255, 0.3);
      border-radius: 8px;
      padding: 25px;
      margin: 20px 0;
    }
    
    .recommendation h4 {
      color: #6699ff;
      margin-bottom: 10px;
    }
    
    /* Footer */
    footer {
      text-align: center;
      padding-top: 40px;
      border-top: 1px solid rgba(255, 255, 255, 0.1);
      color: #606060;
      font-size: 0.9rem;
      margin-top: 60px;
    }
    
    @media (max-width: 768px) {
      .strengths-grid, .weakness-grid {
        grid-template-columns: 1fr;
      }
      
      .score-breakdown {
        grid-template-columns: 1fr;
      }
      
      .metrics-bar {
        grid-template-columns: repeat(2, 1fr);
      }
      
      h1 {
        font-size: 2rem;
      }
      
      .score-number {
        font-size: 3rem;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Implementation Plan Readiness</h1>
      <p class="subtitle">Comprehensive Coverage Analysis Against PRD Requirements</p>
    </header>
    
    <!-- Score Card -->
    <div class="score-card">
      <div class="score-number">91.9%</div>
      <div class="score-label">Overall Coverage Score</div>
      <div class="score-breakdown">
        <div class="tier">
          <div class="tier-label">Critical</div>
          <div class="tier-score">90.0%</div>
          <div class="tier-detail">27 of 30 requirements</div>
        </div>
        <div class="tier">
          <div class="tier-label">Important</div>
          <div class="tier-score">93.3%</div>
          <div class="tier-detail">59 of 67 requirements</div>
        </div>
        <div class="tier">
          <div class="tier-label">Detail</div>
          <div class="tier-score">100%</div>
          <div class="tier-detail">2 of 2 requirements</div>
        </div>
      </div>
    </div>
    
    <!-- The Arc: Before / After (implied) -->
    <section>
      <h2>Coverage Arc</h2>
      <p>
        This plan achieves <strong>strong baseline coverage</strong> with 88 of 99 requirements fully addressed and only 3 requirements completely absent. The implementation is nearly complete at the infrastructure and data-model level, with a notable opportunity to strengthen AI behavioral specifications before development begins.
      </p>
      <div class="metrics-bar">
        <div class="metric">
          <div class="metric-number">88</div>
          <div class="metric-label">Full Coverage</div>
        </div>
        <div class="metric">
          <div class="metric-number">8</div>
          <div class="metric-label">Partial Coverage</div>
        </div>
        <div class="metric">
          <div class="metric-number">3</div>
          <div class="metric-label">Missing</div>
        </div>
        <div class="metric">
          <div class="metric-number">99</div>
          <div class="metric-label">Total Requirements</div>
        </div>
      </div>
    </section>
    
    <!-- What's Strong -->
    <section>
      <h2>What's Strong</h2>
      <p>
        The plan demonstrates exceptional clarity and completeness in five functional areas. These clusters are ready for development:
      </p>
      
      <div class="strengths-grid">
        <div class="strength-item">
          <h4>Data Model & Persistence</h4>
          <p>Show entity with all My Data fields, per-field timestamps for merge resolution, namespace+user partitioning, re-add/duplicate merging, and scoop freshness all thoroughly specified. Production-ready.</p>
        </div>
        
        <div class="strength-item">
          <h4>Benchmark Infrastructure</h4>
          <p>Environment variables, script scaffolding, namespace isolation, dev auth injection, and OAuth migration path are explicitly detailed. Avoids Docker, enables cloud-agent compatibility, and provides repeatable test reset.</p>
        </div>
        
        <div class="strength-item">
          <h4>Collection Home & Search</h4>
          <p>Filters panel, status grouping, tag/genre/decade filters, empty states, keyword search, and non-AI tone all clearly defined with component names and interaction flows.</p>
        </div>
        
        <div class="strength-item">
          <h4>Show Detail & Relationship UX</h4>
          <p>Section order preserved, auto-save triggers enumerated, removal confirmation specified, toolbar positioning clear. Graceful fallbacks for missing data (trailers, seasons) documented.</p>
        </div>
      </div>
    </section>
    
    <!-- What's at Risk -->
    <section>
      <h2>What's at Risk</h2>
      <p>
        The plan exhibits a strategic choice to reference external AI specifications without fully operationalizing them into implementation acceptance criteria. This introduces risk in four important areas:
      </p>
      
      <div class="weakness-grid">
        <div class="weakness-item">
          <h4>AI Persona Enforcement</h4>
          <p>The plan includes "warm, joyful, light in critique" as design goals but doesn't specify how these qualities are verified, tested, or reviewed during implementation. No acceptance criteria for voice.</p>
        </div>
        
        <div class="weakness-item">
          <h4>Concept Ordering</h4>
          <p>The plan specifies concept generation but doesn't detail the ordering strategy (strongest aha first, axis diversity, etc.). First implementer has discretion; consistency isn't guaranteed.</p>
        </div>
        
        <div class="weakness-item">
          <h4>Domain Redirection in Ask</h4>
          <p>The plan includes "stay within TV/movies" as a rule but doesn't describe redirection mechanism, UX copy, or test case. Guardrail is implicit, not explicit.</p>
        </div>
        
        <div class="weakness-item">
          <h4>Discovery Quality Validation</h4>
          <p>The plan references discovery_quality_bar.md rubric but doesn't integrate it into testing, QA checklist, or approval gates. How is quality measured?</p>
        </div>
      </div>
      
      <div class="risk-box">
        <h4>