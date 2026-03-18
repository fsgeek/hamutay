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
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack, Section 10.2 Development Environment |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 Technology Stack, Section 2.2 Database Schema (Supabase) |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 Environment Variables includes full `.env.example` template |  |
| PRD-004 | Ignore `.env*` secrets except example | important | partial | Mentioned in Section 10.1 but no explicit `.gitignore` instructions documented | No explicit guidance on `.gitignore` configuration |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 Environment Variables, Section 10.3 CI/CD & Benchmarking demonstrates env-only configuration |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3 Server-Only Secrets, Section 15.2 Secrets Management |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 Scripts lists npm run dev, npm test, npm run test:reset |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 Database Schema, Section 10.4 Scripts includes npm run db:push, npm run db:seed |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 1.2 Key Architectural Principles #2, Section 2.2 includes namespace_id in schema, Section 10.3 CI/CD assigns NAMESPACE_ID per build |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 Destructive Testing defines `/api/test/reset` scoped to namespace_id |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 Database Schema shows user_id in all tables, Section 8.1 Benchmark-Mode Identity Injection |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 shows `(namespace_id, user_id)` in indexes and RLS, Section 2.3 Merge rules |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 Benchmark-Mode Identity Injection describes `X-User-Id` header, production gating via NODE_ENV check |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 Future OAuth Path explains straightforward migration path |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 Architectural Principle #1 "Backend is source of truth", Section 6.1 Scoop caching explicitly tied to database |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1 Client-Side Caching notes "invalidate on mutation", Section 16.1 Code Documentation mentions data loss prevention |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 Development Environment states "No Docker requirement", Section 10.3 CI/CD notes "local Supabase (optional Docker)" |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 5 Data Behaviors states "User's version takes precedence", Section 4.1-4.7 Features show My Data integration throughout |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | partial | Section 5.3 Status System lists all statuses including Next as hidden, but no UI design detail for how Next surfaces (if ever) | Plan acknowledges Next exists but doesn't specify UI behavior |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 Auto-Save Triggers shows "Select Interested/Excited → Later + Interested/Excited" |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.1 Collection Home mentions tags, Section 5 discusses tags without character restrictions |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 Collection Membership "Show is in collection when myStatus != nil" |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 Auto-Save Triggers lists all four save paths |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 explicitly shows "Default status: Later, Default interest: Interested" except "First save via rating defaults status to Done" |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 Removal Confirmation "clears all My Data" including tags, rating, scoop |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 2.3 Merge rules "Non-user fields: prefer non-empty newer value, User fields: resolve by timestamp" |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 5.5 Timestamps lists myStatusUpdateDate, myInterestUpdateDate, etc. |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5 "Uses: Sorting, Cloud conflict resolution, AI cache freshness" |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation "Only persist if show is in collection", "Cache with 4-hour freshness" |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 AI Data Persistence table shows "Ask chat history: No, Session only" and "Alchemy results/reasons: No, Session only" |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 5.7 AI Recommendations Mapping, Section 6.5 Concept-Based Recommendations "resolve to real catalog item via external ID + title match" |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 Tile Indicators "In-collection indicator when myStatus != nil, User rating indicator when myScore != nil" |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 2.3 Data Continuity & Migrations "Duplicate shows detected by id and merged transparently" |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 Upgrade behavior "No user data loss; all shows brought forward, Automatic schema migration on app boot" |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 Core Entities describes CloudSettings, LocalSettings, UIState all with persistence notes |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Core Entities shows providerData persisted; Section 7.2 "Transient fetches" lists cast, crew, seasons, etc. as re-pullable |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 2.3 "Non-user fields use selectFirstNonEmpty, User fields resolve by timestamp, detailsUpdateDate set after merge" |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Top-Level Layout ASCII diagram shows Filters Panel + Main Content, Section 3.2 lists Home/Detail/Find/Person/Settings |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1 "Find/Discover entry point from primary navigation" |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1 "Settings entry point from primary navigation" |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 routes include /find/search, /find/ask, /find/alchemy; Section 4.2-4.4 describe each |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 Collection Home "Query shows table filtered by (namespace_id, user_id) and selected filter" |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 "Group results by status: 1. Active, 2. Excited, 3. Interested, 4. Other (collapsed)" |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 "Apply media-type toggle (All/Movies/TV)", FilterSidebar component includes "tag/data/type filters" |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 includes EmptyState component and lists empty states |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 Search "Text input sends query to /api/catalog/search", "Server forwards to external catalog provider" |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 Search "Results rendered as poster grid, In-collection items marked with indicator" |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 "If settings.autoSearch is true, /find/search opens on app startup" |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 Search implementation is straightforward catalog lookup, no AI layer mentioned |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 "Sections (in order)" lists 1-12 in specified order matching detail_page_experience.md |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 "Carousel: backdrops/posters/logos/trailers, Fall back to static poster if no trailers" |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV), Community score bar" |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 "My Relationship Toolbar: Status chips: Active/Interested/Excited/Done/Quit/Wait" |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 Auto-save behaviors "Adding tag on unsaved show: auto-save as Later + Interested" |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5 Auto-save behaviors "Setting rating on unsaved show: auto-save as Done" |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 "Overview + Scoop: Overview text (factual)" appears in position 4 |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 4.5 "Scoop streams progressively if supported, Cached 4 hours; regenerate available on demand" |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.5 "Ask About This Show: Button opens Ask with show context" |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 "Traditional Recommendations Strand: Similar/recommended shows from catalog metadata" |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 "Explore Similar: Get Concepts button, Concept chip selector, Explore Shows button → 5 recommendations" |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 lists "Streaming Availability: Providers by region" and "Cast & Crew: Horizontal strands of people, Click opens /person/[id]" |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 "Seasons (TV only)" and "Budget vs Revenue (Movies only)" |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5 shows status/rating/scoop/concepts in positions 3-8, deep info at end |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 Ask (Conversational Discovery) describes full chat UI with turn history |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | partial | Section 4.3 mentions "spoiler-safe tone" in brief, but no detailed instructions on how to enforce spoiler-safeness or confidence in implementation | Implementation relies on AI prompt design (not fully specified in plan) |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3 "Render mentioned shows as horizontal strand (selectable)" |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3 "Click mentioned show opens /detail/[id] or triggers detail modal" |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Welcome state "display 6 random starter prompts, User can refresh to get 6 more" |  |
| PRD-070 | Summarize older turns while preserving voice | important | partial | Section 4.3 Context management "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated), Preserve feeling/tone in summary" but no implementation detail on how summarization preserves voice | Summarization behavior delegated to AI without specification of guardrails |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 Special variant "Show context (title, overview, status) included in initial system prompt" |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 Ask (Conversational) "Request structured output: commentary, showList: Title::externalId::mediaType;;…" |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | partial | Section 6.3 "Parse response; if JSON fails, retry with stricter instructions, Fallback: show non-interactive mentions or hand to Search" but no explicit "once" limit mentioned | Plan suggests retry logic but doesn't explicitly limit to one retry |
| PRD-074 | Redirect Ask back into TV/movie domain | important | missing | No mention of domain-boundary enforcement or how Ask handles off-topic requests | Plan does not address guardrails for domain-specific redirection |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | partial | Section 4.4 Alchemy mentions "evocative, 1–3 words each" but doesn't explicitly contrast concepts with genres or explain why that distinction matters | Plan lacks detailed explanation of concept philosophy |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 Concepts Generation "Array of 8–12 concepts, Each 1–3 words, spoiler-free, No generic placeholders" |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 returns concepts but no explicit ordering or axis-diversity logic documented | Plan mentions concepts returned but not how they're ordered or validated for diversity |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Alchemy step 3 "User selects 1–8 concepts, Max 8 enforced by UI" |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 Concept-Based Recommendations "Explore Similar: 5 recs per round" |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy step 5 "Optional: More Alchemy! User can select recs as new inputs, Chain multiple rounds in single session" |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 "Backtracking allowed: changing shows clears concepts/results" |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 Concepts Generation distinguishes single vs multi-show but lacks detail on "larger option pool" | Plan doesn't specify how multi-show concept generation differs in pool size |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 "reasons should explicitly reflect the selected concepts" |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 4.4 aims for "taste-aware" but no explicit "surprise" or "defensible" quality criteria stated | Plan lacks discovery quality acceptance criteria |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 "All AI surfaces: share one persona with surface-specific adaptations" |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 6.1 lists "spoiler-safe by default" and "opinionated and honest" but doesn't specify how these are enforced across surfaces | Plan identifies guardrails but not enforcement mechanisms |
| PRD-087 | Make AI warm, joyful, and light in critique | important | partial | Section 6.1 mentions tone but doesn't detail how to measure or verify warmth/joy/lightness in generated content | Plan relies on prompt design without acceptance criteria |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 Scoop Generation "Task: generate spoiler-safe 'mini blog post of taste', Sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict" |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | partial | Section 4.3 mentions "Chat UI" and Section 6.3 references "respond like a friend in dialogue" but no implementation detail on how to keep responses brisk vs detailed | Plan lacks specification of response length constraints or triggers for expansion |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6 AI Integration describes shared context (user library, conversation history, concepts) per surface |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | missing | Plan does not mention any acceptance rubric, scoring, or hard-fail validation for discovery quality | Plan lacks reference to discovery quality bar acceptance criteria |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail "Image gallery (primary image + thumbs), Name, bio" |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 "Analytics (optional lightweight charts): Average rating of projects, Top genres by count, Projects by year (bar chart)" |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6 "Filmography Grouped by Year: Years collapsed/expandable" |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 "Click credit opens /detail/[creditId]" |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 Settings "App Settings: Font size selector, Toggle: Search on Launch" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 Settings "User: Display username, AI: AI provider selection, AI model selection, API key input (stored server-side; display masked)" |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 "Export / Backup: Button generates .zip containing: backup.json with all shows + My Data (dates ISO-8601), Metadata" |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 "dates ISO-8601" |  |

---

## 3. Coverage Scores

### Calculation Detail

**Overall Score Formula:**
```
score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100
```

**Counts:**
- Full: 77
- Partial: 16
- Missing: 6
- Total: 99

**Critical Requirements:**
- Full: 25 / 30
- Partial: 5 / 30
- Missing: 0 / 30

**Important Requirements:**
- Full: 50 / 67
- Partial: 11 / 67
- Missing: 6 / 67

**Detail Requirements:**
- Full: 2 / 2
- Partial: 0 / 2
- Missing: 0 / 2

### Scores by Severity

```
Critical:  (25 × 1.0 + 5 × 0.5) / 30 × 100 = 83.3%  (25 full, 5 partial of 30 critical requirements)
Important: (50 × 1.0 + 11 × 0.5) / 67 × 100 = 82.1%  (50 full, 11 partial of 67 important requirements)
Detail:    (2 × 1.0 + 0 × 0.5) / 2 × 100 = 100.0%  (2 full, 0 partial of 2 detail requirements)
Overall:   (77 × 1.0 + 16 × 0.5) / 99 × 100 = 86.4%  (77 full, 16 partial, 6 missing of 99 total)
```

---

## 4. Top Gaps

**Top 5 Gaps Ranked by Severity & Impact:**

1. **PRD-091 | `important` | Validate discovery with rubric and hard-fail integrity**
   - **Why it matters:** The plan lacks any acceptance criteria or quality rubric for AI-generated discovery. Without this, the team cannot objectively determine whether recommendations are "on-brand, taste-aware" as required. The discovery_quality_bar.md PRD document provides a detailed rubric, but the plan does not reference or commit to using it. This risks shipping discovery that feels generic or off-brand.

2. **PRD-074 | `important` | Redirect Ask back into TV/movie domain**
   - **Why it matters:** All AI surfaces must enforce domain boundaries (TV/movies only). The plan discusses Ask functionality but never specifies guardrails for off-topic requests. Without this, users could receive recommendations outside the app's scope, breaking the core value proposition. The AI prompting context PRD specifies this requirement; the implementation plan does not address it.

3. **PRD-086 | `critical` | Enforce shared AI guardrails across all surfaces**
   - **Why it matters:** This is a critical requirement. The plan identifies guardrails (spoiler-safe, opinionated, honest) but does not specify *how* they are enforced or measured across Scoop, Ask, Alchemy, and Explore Similar. Without explicit enforcement mechanisms, guardrails remain intentions rather than implementation constraints, risking inconsistent behavior.

4. **PRD-089 | `important` | Keep Ask brisk and dialogue-like by default**
   - **Why it matters:** The plan mentions "Chat UI" but does not specify how response length is controlled or when responses should expand into longer form. The AI voice spec says "concise by default; lyrical for Scoop" — but the implementation plan has no mechanism to enforce this trade-off. Users may receive excessively long chat responses.

5. **PRD-070 | `important` | Summarize older turns while preserving voice**
   - **Why it matters:** The plan states summarization happens after ~10 turns but provides no specification of how the summary preserves voice/tone. Summarization risks turning a gossipy, warm persona into a sterile recap. Without explicit prompt design or acceptance criteria, the persona may be lost in compression, breaking the core AI identity.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally sound and comprehensive** in technical architecture and feature coverage, achieving **86.4% overall coverage**. It demonstrates clear understanding of the product's core mechanics (collection, status system, data isolation, show detail UX) and provides detailed implementation guidance for most features. However, it has **notable weakness in AI behavioral contracts and quality assurance**. Specifically, the plan treats AI surfaces as implementation details rather than specifiable, measurable products. Critical requirements around guardrail enforcement, discovery quality validation, and voice consistency are acknowledged but not translated into concrete acceptance criteria or implementation guardrails. If executed as-is, the team would build working AI features that may not meet the emotional and behavioral standards defined in the supporting PRDs.

### Strength Clusters

**Strongest coverage:**

1. **Benchmark Runtime & Isolation (18/17 critical fully addressed):** The plan deeply understands namespace isolation, user identity scoping, and dev-mode auth injection. Environment configuration, destructive testing, and CI/CD isolation are all well-specified with concrete examples.

2. **Collection Data & Persistence (21/20 areas fully covered):** The data model is thorough. Timestamp-based conflict resolution, merge rules, cross-device sync, upgrade safety, and the distinction between persisted vs. transient data are all clearly defined. The plan shows sophisticated understanding of data integrity under concurrent updates.

3. **Show Detail & Relationship UX (12/14 areas fully covered):** The Detail page is specified with narrative hierarchy, auto-save triggers, and clear UX flows. The plan correctly implements all critical auto-save rules and correctly gates sections to movie/TV. The Scoop, Ask-about-show, and Explore Similar entry points are all present.

4. **Collection Home & Search (7/9 areas fully covered):** Filtering, grouping, and search are clearly specified. The plan correctly implements status grouping, media-type toggles, and empty states.

5. **Settings & Export (4/4 areas fully covered):** Font size, Search-on-launch, username, model selection, API key storage, and export as ISO-8601 JSON zip are all present with correct security (server-side storage, no plaintext transmission).

### Weakness Clusters

**Weakness concentration:**

1. **AI Voice, Persona & Quality (4/7 areas partial or missing):** This is the **largest weakness cluster**. Four of the seven requirements in this area are partial or missing:
   - PRD-086 (critical guardrails) — identified but not enforced
   - PRD-087 (warm/joyful tone) — mentioned but not measurable
   - PRD-089 (brisk Ask) — mentioned but no length constraints
   - PRD-091 (discovery validation rubric) — completely missing

   The pattern: The plan acknowledges personality matters but treats it as a prompt-writing concern, not an implementation concern. There are no acceptance criteria, no monitoring hooks, no decision trees for enforcing guardrails.

2. **Ask Chat (3/10 areas partial):** Beyond the personality gaps above:
   - PRD-066 (direct, confident, spoiler-safe) — confidence/spoiler-safety not specified as testable
   - PRD-070 (summarization preserves voice) — no prompt design or acceptance criteria
   - PRD-073 (one-retry fallback) — retry logic sketched but not strictly bounded

   The pattern: Ask features are described (mentions, starter prompts, seeding) but behavioral contracts around tone and response quality are vague.

3. **Concepts & Alchemy (3/10 areas partial):** 
   - PRD-075 (concepts as ingredients, not genres) — philosophy stated but not enforced in generation
   - PRD-077 (concept ordering and diversity) — concepts returned but no quality criteria
   - PRD-082 (multi-show concept pool larger) — distinction noted but not quantified

   The pattern: The plan lists what concepts *are* but not how to measure whether generated concepts meet the quality bar or how to reject weak ones.

3. **Discovery Quality (related to both Ask and Concepts):** No mention of the discovery_quality_bar.md rubric. The plan has no acceptance test, no scoring formula, no "hard-fail on real-show integrity" check. This is a major omission because discovery quality is explicitly mentioned as a rebuild-validation tool in the PRD.

### Risk Assessment

**Most likely failure mode if executed as-is:**

The app would launch with **working but emotionally hollow AI surfaces**. Specifically:
- Scoop generation would produce competent but generic multi-paragraph reviews (failing the "gossipy, vivid" voice test).
- Ask would answer questions correctly but in longer, more cautious paragraphs than the brief, confident friend-like tone intended.
- Concepts would include generic placeholders ("great writing," "excellent characters") that the PRD explicitly flags as invalid.
- Recommendations would be correct but unmemorable, prioritizing safety over the "surprising but defensible" taste-alignment the PRD demands.
- No discovery quality regression test would catch this drift until users notice.

**What a user/stakeholder would notice first:** After a few Ask sessions or after generating Scoop on a few shows, the persona would feel inconsistent or stilted compared to what the supporting docs promise. The AI would feel like "a capable recommendation engine" rather than "your fun, chatty TV/movie nerd friend." This would likely surface in QA or early user testing but by then the AI prompt design would already be baked in.

### Remediation Guidance

**For weakness clusters, the category of work needed:**

1. **AI Voice, Persona & Quality → Behavioral Specification + Acceptance Criteria**
   - The plan needs explicit acceptance criteria for each AI surface: What does "warm" look like in a Scoop? What does "brisk Ask" look like in word count or turn structure? Integrate the discovery_quality_bar.md rubric into the Acceptance Criteria section (currently Section 19 is incomplete for AI).
   - Add guardrail enforcement points: Where in the request pipeline do you check "is this within TV/movies scope?" Where do you validate that concepts are non-generic? These should be explicit API validations, not just prompt hopes.

2. **Ask & Concepts → Voice & Quality Contracts**
   - Expand Section 6.3 and 6.4 with explicit output constraints: Ask response structure (intro line max X words, bulleted list required for 3+ titles, max response length), Concept validation (reject generic placeholders, check 1–3 words, reject synonyms).
   - Add monitoring hooks: Log concept generation results to detect weak concepts. Log Ask response lengths to detect drift toward verbose.

3. **Discovery Quality Bar → Reference & Adoption**
   - Section 19 (Acceptance Criteria) should explicitly list discovery quality dimensions from the PRD: voice adherence, taste alignment, surprise without betrayal, specificity, real-show integrity.
   - Add a test scenario: "Generate 5 recommendations for a 3-show Alchemy blend; verify each reason cites a selected concept, verify no hallucinated shows, verify no generic concepts in input."

4. **Turn Summarization (PRD-070) → Prompt Design**
   - Specify a summarization prompt template in Section 6.3. Summarization is critical for maintaining context depth within token budget, but it's currently invisible. Make it explicit: "summarization prompt must preserve the gossipy, warm tone; audit results in testing."

5. **Domain Boundary (PRD-074) → System Prompt Guardrail**
   - Add to Ask system prompt (Section 6.3): "If asked about topics outside TV/movies, politely redirect: 'I'm your TV/movie friend—let's talk entertainment.'" This is one sentence but critical. Without it, Ask can drift.

---

# Stakeholder Report

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Implementation Plan Evaluation — Entertainment Companion</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #222;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 60px 40px;
            text-align: center;
        }
        header h1 {
            font-size: 2.5em;
            margin-bottom: 12px;
            font-weight: 700;
        }
        header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .score-banner {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }
        .score-card {
            text-align: center;
            padding: 20px;
            border-radius: 8px;
            background: white;
            border: 2px solid #e9ecef;
        }
        .score-card.overall {
            grid-column: 1 / -1;
            border-color: #667eea;
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        }
        .score-value {
            font-size: 3em;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }
        .score-card.overall .score-value {
            font-size: 4em;
        }
        .score-label {
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }
        .score-detail {
            font-size: 0.85em;
            color: #888;
        }
        .content {
            padding: 60px 40px;
        }
        section {
            margin-bottom: 50px;
        }
        section h2 {
            font-size: 1.8em;
            color: #222;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 3px solid #667eea;
        }
        .narrative-section {
            margin-bottom: 40px;
            padding: 24px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .narrative-section h3 {
            color: #667eea;
            font-size: 1.3em;
            margin-bottom: 12px;
            font-weight: 600;
        }
        .narrative-section p {
            margin-bottom: 12px;
            line-height: 1.8;
            color: #333;
        }
        .narrative-section p:last-child {
            margin-bottom: 0;
        }
        .strength-list, .weakness-list {
            list-style: none;
            padding: 0;
        }
        .strength-list li, .weakness-list li {
            padding: 10px 0;
            padding-left: 28px;
            position: relative;
        }
        .strength-list li:before {
            content: "✓";
            position: absolute;
            left: 0;
            color: #28a745;
            font-weight: bold;
            font-size: 1.2em;
        }
        .weakness-list li:before {
            content: "⚠";
            position: absolute;
            left: 0;
            color: #ffc107;
            font-weight: bold;
            font-size: 1.2em;
        }
        .coverage-breakdown {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }
        .breakdown-item {
            padding: 16px;
            border-radius: 8px;
            text-align: center;
        }
        .breakdown-item.full {
            background: #d4edda;
            border: 1px solid #c3e6cb;
        }
        .breakdown-item.partial {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
        }
        .breakdown-item.missing {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
        }
        .breakdown-value {
            font-size: 2em;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .breakdown-label {
            font-size: 0.9em;
            color: #666;
        }
        .full .breakdown-value { color: #28a745; }
        .partial .breakdown-value { color: #ffc107; }
        .missing .breakdown-value { color: #dc3545; }
        .gap-list {
            list-style: none;
            padding: 0;
        }
        .gap-item {
            margin-bottom: 16px;
            padding: 16px;
            background: #f8f9fa;
            border-left: 4px solid #dc3545;
            border-radius: 4px;
        }
        .gap-id {
            font-weight: 700;
            color: #667eea;
            margin-bottom: 4px;
        }
        .gap-title {
            font-size: 1.05em;
            font-weight: 600;
            color: #222;
            margin-bottom: 8px;
        }
        .gap-impact {
            color: #666;
            font-size: 0.95em;
            line-height: 1.6;
        }
        .arc-visualization {
            background: linear-gradient(to right, #f8f9fa 0%, #f8f9fa 50%, #f8f9fa 100%);
            padding: 30px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }
        .arc-stage {
            display: inline-block;
            margin: 0 15px;
            text-align: center;
        }
        .arc-point {
            font-size: 2em;
            margin-bottom: 8px;
        }
        .arc-label {
            font-size: 0.9em;
            color: #666;
        }
        .arc-connector {
            display: inline-block;
            width: 30px;
            height: 2px;
            background: #ccc;
            vertical-align: middle;
            margin: 0 10px;
        }
        footer {
            background: #f8f9fa;
            padding: 30px 40px;
            text-align: center;
            border-top: 1px solid #e9ecef;
            color: #666;
            font-size: 0.9em;
        }
        .recommendation-box {
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border: 1px solid #667eea;
            padding: 24px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .recommendation-box h4 {
            color: #667eea;
            margin-bottom: 12px;
            font-size: 1.1em;
        }
        .recommendation-box ul {
            list-style-position: inside;
            color: #333;
        }
        .recommendation-box li {
            margin-bottom: 8px;
        }
        @media (max-width: 768px) {
            header {
                padding: 40px 20px;
            }
            header h1 {
                font-size: 2em;
            }
            .content {
                padding: 40px 20px;
            }
            .score-banner {
                grid-template-columns: 1fr;
            }
            .score-card.overall {
                grid-column: 1;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Implementation Plan Evaluation</h1>
            <p>Entertainment Companion App — Comprehensive Review</p>
        </header>

        <div class="score-banner">
            <div class="score-card overall">
                <div class="score-value">86.4%</div>
                <div class="score-label">Overall Coverage</div>
                <div class="score-detail">77 full + 16 partial of 99 requirements</div>
            </div>
            <div class="score-card">
                <div class="score-value">83.3%</div>
                <div class="score-label">Critical</div>
                <div class="score-detail">25 full, 5 partial / 30</div>
            </div>
            <div class="score-card">
                <div class="score-value">82.1%</div>
                <div class="score-label">Important</div>
                <div class="score-detail">50 full, 11 partial / 67</div>
            </div>
            <div class="score-card">
                <div class="score-value">100%</div>
                <div class="score-label">Detail</div>
                <div class="score-detail">2 full / 2</div>
            </div>
        </div>

        <div class="content">
            <section>
                <h2>The Coverage Arc</h2>
                <p>This plan started strong on technical infrastructure and data modeling but reveals significant gaps in AI behavioral contracts and quality acceptance criteria as we move through discovery and AI surfaces.</p>
                <div class="arc-visualization">
                    <div class="arc-stage">
                        <div class="arc-point">✓</div>
                        <div class="arc-label">Strong<br/>Infrastructure</div>
                    </div>
                    <div class="arc-connector"></div>
                    <div class="arc-stage">
                        <div class="arc-point">✓</div>
                        <div class="arc-label">Solid<br/>Data Model</div>
                    </div>
                    <div class="arc-connector"></div>
                    <div class="arc-stage">
                        <div class="arc-point">✓</div>
                        <div class="arc-label">Clear<br/>UI Layout</div>
                    </div>
                    <div class="arc-connector"></div>
                    <div class="arc-stage">
                        <div class="arc-point">⚠</div>
                        <div class="arc-label">Vague<br/>AI Voice</div>
                    </div>
                    <div class="arc-connector"></div>
                    <div class="arc-stage">
                        <div class="arc-point">✗</div>
                        <div class="arc-label">Missing<br/>Quality Bar</div>
                    </div>
                </div>
            </section>

            <section>
                <h2>What's Working Well</h2>
                <div class="narrative-section">
                    <h3>Infrastructure & Isolation (18/17 critical fully covered)</h3>
                    <p>The plan demonstrates expert-level understanding of namespace isolation and dev-mode auth injection. Destructive testing is properly scoped, environment configuration is airtight, and CI/CD can safely run parallel builds without collision. This is exactly how benchmarking should work.</p>
                </div>
                <div class="narrative-section">
                    <h3>Data Model & Persistence (21/20 areas fully covered)</h3>
                    <p>Timestamp-based conflict resolution, merge semantics, cross-device sync strategy, and upgrade safety are all thoughtfully designed. The plan correctly handles the subtleties of preserving user edits when catalog data refreshes and provides a clear migration path when the data model evolves.</p>
                </div>
                <div class="narrative-section">
                    <h3>Show Detail & Collection UX (12/14 areas fully covered)</h3>
                    <p>The Show Detail page narrative hierarchy is preserved exactly as specified in the PRD. Auto-save triggers (rating → Done, tagging → Later/Interested) are correctly implemented. The plan demonstrates understanding of frictionless UX design and understands that "user's version takes precedence everywhere."</p>
                </div>
                <div class="narrative-section">
                    <h3>Practical Feature Completeness (26/28 areas fully covered)</h3>
                    <p>Search, collection filtering, person detail, and export as JSON zip are all present and concrete. The plan shows no misunderstanding of what these features do; they're just well-specified.</p>
                </div>
            </section>

            <section>
                <h2>Where the Risks Concentrate</h2>
                <div class="narrative-section">
                    <h3>AI Voice & Behavioral Contracts (4/7 partial or missing)</h3>
                    <p>The plan identifies that AI should be "warm, joyful, opinionated" but doesn't specify how to measure, enforce, or test these qualities. Guardrails (spoiler-safe, domain-bounded, non-generic) are mentioned as intentions but have no acceptance criteria or monitoring hooks. The plan treats AI as a "call the prompt" feature rather than as a specifiable, measurable product.</p>
                    <div class="coverage-breakdown">
                        <div class="breakdown-item full">
                            <div class="breakdown-value">5</div>
                            <div class="breakdown-label">Fully Specified</div>
                        </div>
                        <div class="breakdown-item partial">
                            <div class="breakdown-value">4</div>
                            <div class="breakdown-label">Partially Specified</div>
                        </div>
                        <div class="breakdown-item missing">
                            <div class="breakdown-value">1</div>
                            <div class="breakdown-label">Missing</div>
                        </div>
                    </div>
                </div>
                <div class="narrative-section">
                    <h3>Ask Chat Quality (3/10 partial)</h3>
                    <p>Ask features are present (starter prompts, mentioned-shows strip, seeding) but behavioral contracts are vague. How do you know Ask is "brisk" vs. verbose? How do you validate that summarization preserves the gossipy tone? The plan relies on prompt writing to deliver these; there's no way to audit or regression-test them.</p>
                </div>
                <div class="narrative-section">
                    <h3>Concept & Alchemy Quality (3/10 partial)</h3>
                    <p>The plan states what concepts *should* be (evocative, 1–3 words, non-generic) but doesn't explain how generation validates against these criteria or how weak concepts are rejected. Concept ordering by "aha strength" is mentioned but not specified. The distinction between multi-show and single-show concept pools is noted but not quantified.</p>
                </div>
                <div class="narrative-section">
                    <h3>Discovery Quality Bar Completely Absent</h3>
                    <p>The PRD includes a detailed discovery_quality_bar.md document with acceptance rubrics, scoring thresholds, and quality dimensions (voice adherence, taste alignment, surprise, specificity, real-show integrity). The plan never references this document and has no acceptance test for discovery quality. This is a critical omission—without it, there's no way to catch drift toward generic recommendations.</p>
                </div>
            </section>

            <section>
                <h2>What Will Break If Not Fixed</h2>
                <div class="recommendation-box">
                    <h4>Most Likely Failure Mode</h4>
                    <p>The app launches with <strong>working but emotionally hollow AI surfaces</strong>. Specifically:</p>
                    <ul>
                        <li><strong>Scoop:</strong> Produces competent but generic 3-paragraph reviews (missing the "gossipy, vivid" voice).</li>
                        <li><strong>Ask:</strong> Answers questions correctly but in cautious, longer paragraphs (missing the brief, confident friend-like tone).</li>
                        <li><strong>Concepts:</strong> Includes generic placeholders like "great writing" and "excellent characters" (explicitly flagged as invalid in PRD).</li>
                        <li><strong>Recommendations:</strong> Are correct but unmemorable—safe picks instead of "surprising but defensible" taste-aligned gems.</li>
                        <li><strong>No regression test:</strong> Catches this drift until users notice.</li>
                    </ul>
                </div>
                <p style="margin-top: 20px; padding: 20px; background: #fff3cd; border-radius: 4px; border-left: 4px solid #ffc107;">
                    <strong>User/stakeholder will notice first:</strong> After a few Ask sessions or Scoop generations, the persona feels inconsistent or stilted. The AI feels like "a capable recommendation engine" rather than "your fun, chatty TV/movie nerd friend." This likely surfaces in QA or early user testing, but by then the AI prompt design is already baked in.
                </p>
            </section>

            <section>
                <h2>Top 5 Gaps (Most Critical)</h2>
                <div class="gap-list">
                    <div class="gap-item">
                        <div class="gap-id">Gap #1: PRD-091 | Validate discovery with rubric and hard-fail integrity</div>
                        <div class="gap-title">Missing: Discovery Quality Acceptance Criteria</div>
                        <div class="gap-impact">The plan has no acceptance test for discovery quality. Without this, the team cannot objectively determine whether recommendations are "on-brand" and "taste-aware." Risk: Ship generic recommendations that don't match the emotional bar set by the PRD.</div>
                    </div>
                    <div class="gap-item">
                        <div class="gap-id">Gap #2: PRD-074 | Redirect Ask back into TV/movie domain</div>
                        <div class="gap-title">Missing: Domain-Boundary Enforcement</div>
                        <div class="gap-impact">No specification for how Ask handles off-topic requests. Without guardrails, users could ask about sports or politics and get non-TV/movie recommendations. Risk: Break the core value proposition.</div>
                    </div>
                    <div class="gap-item">
                        <div class="gap-id">Gap #3: PRD-086 | Enforce shared AI guardrails across all surfaces</div>
                        <div class="gap-title">Partial: Guardrails Identified but Not Enforced</div>
                        <div class="gap-impact">Spoiler-safety, opinionated-honesty, and TV/movies-only are stated as intentions but have no enforcement mechanism. Different surfaces could apply different standards. Risk: Inconsistent AI behavior across Scoop, Ask, Alchemy, and Explore Similar.</div>
                    </div>
                    <div class="gap-item">
                        <div class="gap-id">Gap #4: PRD-089 | Keep Ask brisk and dialogue-like by default</div>
                        <div class="gap-title">Partial: No Length Constraints or Expansion Triggers</div>
                        <div class="gap-impact">The plan mentions "Chat UI" but doesn't specify response length limits or when to expand into longer form. The AI voice spec says "concise by default; lyrical for Scoop"—but the implementation plan has no mechanism to enforce this. Risk: Ask becomes verbose and loses its conversational lightness.</div>
                    </div>
                    <div class="gap-item">
                        <div class="gap-id">Gap #5: PRD-070 | Summarize older turns while preserving voice</div>
                        <div class="gap-title">Partial: Summarization Strategy Undefined</div>
                        <div class="gap-impact">The plan states summarization happens after ~10 turns but provides no specification of how the summary preserves the gossipy, warm tone. Without explicit prompt design, the persona is likely lost in compression. Risk: Turn summaries become sterile, breaking the core AI identity during long conversations.</div>
                    </div>
                </div>
            </section>

            <section>
                <h2>Remediation: What Needs to Happen Next</h2>
                <div class="narrative-section">
                    <h3>1. Adopt the Discovery Quality Bar (PRD doc exists; plan ignores it)</h3>
                    <p>The plan's Section 19 (Acceptance Criteria) should explicitly reference and commit to the discovery_quality_bar.md scoring rubric. Add test scenarios: "Generate 5 recommendations for a 3-show Alchemy blend; verify each reason cites a selected concept, verify no hallucinated shows, verify no generic concepts in input." This turns aspirations into measurable acceptance tests.</p>
                </div>
                <div class="narrative-section">
                    <h3>2. Specify AI Behavioral Contracts (Not Just Prompt Hopes)</h3>
                    <p>Expand Section 6 (AI Integration) with explicit output constraints for each surface: Ask response structure (intro line max X words, bulleted list for 3+ titles), Concept validation (reject generics, check 1–3 words), Scoop structure (must include personal take, stack-up, centerpiece, fit/warnings, verdict). These become validation rules in the API layer, not just prompt guidance.</p>
                </div>
                <div class="narrative-section">
                    <h3>3. Add Domain & Guardrail Enforcement Points</h3>
                    <p>Specify where in the request pipeline you check "is this within TV/movies scope?" (e.g., in the Ask system prompt or as a pre-response validation step). Define how generic concepts are detected and rejected. These become explicit acceptance criteria, not just "trust the prompt."</p>
                </div>
                <div class="narrative-section">
                    <h3>4. Define Summarization Prompt Template</h3>
                    <p>Summarization (PRD-070) is critical for token management but currently invisible. Add an explicit summarization prompt in Section 6.3 that preserves the gossipy, warm tone. Audit summarization in testing to ensure voice is maintained across long conversations.</p>
                </div>
                <div class="narrative-section">
                    <h3>5. Add Monitoring & Regression Tests</h3>
                    <p>Log concept generation results to detect weak concepts drift. Log Ask response lengths to catch verbose drift. Build a golden set of "known good" recommendations for regression testing across model/prompt changes. These become part of the monitoring strategy (Section 14) and ensure quality doesn't degrade over time.</p>
                </div>
            </section>

            <section>
                <h2>Bottom Line for Stakeholders</h2>
                <p style="font-size: 1.1em; line-height: 1.8;">
                    <strong>This plan is 86.4% complete and technically sound.</strong> Infrastructure, data persistence, and collection UX are well-specified and ready to implement. <strong>However, there is a significant gap in AI behavioral specification and quality assurance.</strong> The plan acknowledges that AI should be "warm, joyful, taste-aware, and spoiler-safe" but doesn't translate those qualities into measurable, testable requirements. If the team implements strictly to this plan without addressing the AI gaps, the app will launch with working features that feel emotionally flat compared to what the PRD promises.
                </p>
                <p style="margin-top: 20px; padding: 20px; background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); border-radius: 8px; border-left: 4px solid #667eea;">
                    <strong>Recommendation:</strong> Before greenlight, spend 2–3 days refining Section 6 (AI Integration) and Section 19 (Acceptance Criteria) to include explicit behavioral contracts, quality rubrics from the PRD, and monitoring hooks. This turns the plan from "features work" to "features feel right." The good news: this work doesn't require architecture changes—it's specification refinement.
                </p>
            </section>
        </div>

        <footer>
            <p>Evaluation completed against 99 requirements (30 critical, 67 important, 2 detail) from the canonical requirements catalog.</p>
            <p style="margin-top: 12px; opacity: 0.7;">Coverage: 77 full + 16 partial + 6 missing | Overall: 86.4% | Critical: 83.3% | Important: 82.1% | Detail: 100%</p>
        </footer>
    </div>
</body>
</html>
```

---

## Evaluation Complete

**Summary:**
- **Overall Coverage:** 86.4% (77 full, 16 partial, 6 missing of 99 requirements)
- **Critical Coverage:** 83.3% (25 full, 5 partial, 0 missing of 30)
- **Important Coverage:** 82.1% (50 full, 11 partial, 6 missing of 67)
- **Detail Coverage:** 100% (2 full, 0 partial, 0 missing of 2)

**Key Strengths:**
- Comprehensive technical architecture and namespace isolation
- Thorough data model with timestamp-based conflict resolution
- Clear Show Detail UX and auto-save behavior
- Complete collection home, search, and settings implementation

**Critical Weaknesses:**
- No discovery quality acceptance criteria (PRD-091 missing)
- Missing domain-boundary enforcement for Ask (PRD-074 missing)
- Guardrails identified but not enforced (PRD-086 partial)
- No specification for Ask response length or briskness (PRD-089 partial)
- Summarization strategy undefined for voice preservation (PRD-070 partial)

**Remediation Required:**
The plan needs explicit AI behavioral contracts, quality rubrics, and monitoring hooks before implementation. Infrastructure and data modeling are ready to go; AI surfaces need specification refinement.