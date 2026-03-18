I will now follow the evaluation instructions in full order: read the catalog, read the PRD files, read the plan, and then produce the complete evaluation. Let me start by internalizing the requirements catalog.

---

# Step 1: Read the Canonical Requirements Catalog

I have the requirements catalog frozen in the instructions above. It contains:
- **10 functional areas** (Benchmark Runtime & Isolation, Collection Data & Persistence, etc.)
- **99 total requirements** (30 critical, 67 important, 2 detail)
- Exact IDs, labels, severity tiers, and source citations

I will use this as the fixed denominator and not reinterpret or modify it.

---

# Step 2: Read PRD Files

I have read all PRD files in the instructions:
- `product_prd.md` — product vision, features, data behaviors
- `infra_rider_prd.md` — benchmark baseline, environment, auth, isolation
- `supporting_docs/ai_voice_personality.md` — AI persona and tone
- `supporting_docs/ai_prompting_context.md` — AI behavioral contracts
- `supporting_docs/concept_system.md` — concept generation rules
- `supporting_docs/detail_page_experience.md` — Detail page narrative
- `supporting_docs/discovery_quality_bar.md` — AI quality acceptance criteria
- `supporting_docs/technical_docs/storage-schema.md` — persistence schema
- `supporting_docs/technical_docs/storage-schema.ts` — TypeScript schema reference

---

# Step 3: Read the Plan

I have read `results/PLAN.md` — a comprehensive 20-section implementation plan covering architecture, data model, features, AI integration, testing, and deployment.

---

# Step 4: Write Full Markdown Evaluation

Now I will produce the complete evaluation to `results/PLAN_EVAL.md` following the exact structure required.

<evaluation>

# PLAN EVALUATION

**Plan:** `results/PLAN.md`  
**Requirements Catalog Version:** v1  
**Evaluation Date:** 2024  
**Evaluator Notes:** This plan is comprehensive and well-structured. It addresses the PRD systematically and captures most critical requirements. However, several specific behavioral contracts and acceptance criteria are only addressed partially or by implication rather than with explicit concrete tasks.

---

## 1. Requirements Extraction

### Pass 1: Identify Functional Areas

The following functional areas are extracted from `evaluator/requirements_catalog_v1.md` in the exact order specified:

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
| --- | --- | --- | --- | --- | --- |
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack specifies "Next.js (latest stable)" explicitly | |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 specifies "@supabase/supabase-js" (anon/public key for browser); Section 8.1 dev auth injection details | |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 provides complete `.env.example` template with all required variables documented | |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 states "Fill .env with cloud credentials"; Section 8.1 confirms environment injection; .gitignore pattern implied | |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 "Fill .env with cloud Supabase credentials + API keys"; no code edits required | |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 1.1 "API key stored server-side only"; Section 8 "API keys (catalog, AI) server-only"; Section 8.3 details encryption | |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 lists required npm scripts: `npm run dev`, `npm test`, `npm run test:reset`, etc. | |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.1 references migrations; Section 10.2 "npm run db:push" applies migrations idempotent; Section 16.2 runbooks | |
| PRD-009 | Use one stable namespace per build | critical | full | Section 2.2 Database schema includes `namespace_id` per build; Section 10.3 CI/CD assigns unique `NAMESPACE_ID` per build | |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 2.2 RLS enforces `(namespace_id, user_id)` partition; Section 12.2 reset endpoint clears namespace-specific data only | |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 2.2 schema includes `user_id` on all major tables; Section 8.1 middleware checks and enforces user_id | |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 "all data partitioned by `(namespace_id, user_id)`"; RLS policies enforce partition | |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 "X-User-Id header accepted by server routes in dev mode"; feature flag gating; production mode disables | |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 "User identity already modeled as opaque string (`user_id`)"; "Switch from header injection to real OAuth: schema unchanged" | |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 "Backend is source of truth — clients cache for performance"; Section 6.1 "server-side storage" | |
| PRD-016 | Make client cache safe to discard | critical | full | Section 6.2 "Clearing client storage must not lose user data"; Section 13.1 in-memory React state, localStorage optional | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 "No Docker requirement — can run against hosted Supabase directly" | |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 2.1 "Display rule: Whenever a show appears anywhere… if user has saved version, display user-overlaid version" | |
| PRD-019 | Support visible statuses plus hidden `Next` | important | partial | Section 2.1 lists statuses including "Next" as "(optional/hidden)"; not explicitly surfaced as first-class UI; described as "model only, not UI" | Plan addresses data model but explicitly defers UI for Next status to future |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 2.3 "Selecting either [Interested/Excited] sets: `My Status = Later`; `My Interest = Interested` or `Excited`" | |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.1 "Tags are free-form user labels… form a personal tag library"; Section 4.5 tag pickers, editors | |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 "A show is 'in collection' when `myStatus != nil`" | |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 auto-save triggers table lists all four actions | |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 "Default save to Later/Interested except rating-save Done"; exception explicitly listed | |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 "Effects: Show is removed from storage. All My Data cleared: status, interest, tags, rating, and AI Scoop." | |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 5.5 "Preserve their latest status, interest, tags, rating, and AI Scoop. Refresh public metadata as available." | |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1 "Every user field tracks last modification time: `myStatusUpdateDate`, `myInterestUpdateDate`, etc." | |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.6 "Uses: Sorting (recently updated shows first)… Cloud conflict resolution (newer wins). AI cache freshness." | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 "Scoop generation… Only persist if show is in collection"; Section 6.2 "Cache with 4-hour freshness" | |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 table explicitly marks Ask/Alchemy as "Session only"; Section 4.3 "clear history when user leaves Ask" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 6.5 "For each rec, resolve to real catalog item via external ID + title match"; Section 5.8 "must resolve to real show" | |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 "Show tiles display lightweight badges: In-collection indicator when `My Status` exists; User rating indicator" | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5 "Merge conflicts resolve by most recent update timestamp per field"; "Duplicate shows detected by `id` and merged" | |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 "Upgrade behavior: New app version reads old schema and transparently transforms on first load. No user data loss." | |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 4.7 "Settings stored in `cloud_settings` table + local browser settings"; Section 2.1 "LocalSettings, UIState" entities | |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Show schema includes `externalIds`; Section 2.1 "Not stored (transient): cast, crew, seasons, images*, videos" | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 5.5 merge rules with `selectFirstNonEmpty` for catalog, timestamps for user fields | |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 top-level layout shows "Filters Panel" on left; Section 3.2 lists all main routes | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1 lists "Find/Discover entry point" as persistent; Section 3.2 `/find` route | |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1 lists "Settings entry point" as persistent; Section 3.2 `/settings` route | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 lists `/find/search`, `/find/ask`, `/find/alchemy` routes; Section 3.3 "mode switcher" | |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 "Query `shows` table filtered by `(namespace_id, user_id)` and selected filter"; filters applied | |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 grouping logic: "1. Active, 2. Excited (Later + Excited Interest), 3. Interested (Later + Interested), 4. Other" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 "Apply media-type toggle (All/Movies/TV) on top of status grouping"; Section 3.1 shows "All Shows, tag filters, data filters" | |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 "Components: `EmptyState` — when no shows match filter" | |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 "Text search by title/keywords" | |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 "Results rendered as poster grid; In-collection items marked with indicator" | |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 "If `settings.autoSearch` is true, `/find/search` opens on app startup" | |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 "Server forwards to external catalog provider (TMDB or equivalent)"; no AI voice described for Search | |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 lists 12 sections in exact order from spec: header → facts → toolbar → overview → ask → genres → recs → concepts → providers → cast → seasons → budget | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 "Carousel: backdrops/posters/logos/trailers; Fall back to static poster if no trailers" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 "Core Facts Row: Year, runtime (movie) or seasons/episodes (TV); Community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 "My Relationship Toolbar: Status chips: Active/Interested/Excited/Done/Quit/Wait" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 "My Tags display + tag picker (modal/dropdown)"; Section 5.2 "Adding tag to unsaved show: auto-save as Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 5.2 table "Rate unsaved show | Done"; Section 4.5 "Rating slider (0–10, unrated state available)" | |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 section 4 "Overview + Scoop: Overview text (factual)" | |
| PRD-058 | Scoop shows correct states and progressive feedback | important | partial | Section 6.2 mentions "streams progressively if supported" but no explicit state machine for loading/cached/error states defined; states mentioned only as passing mention | Plan describes streaming but lacks explicit UI state codification (loading, error, cached) |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.3 "Special variant: Ask About This Show: Button on Detail page opens Ask with pre-seeded context" | |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 section 7 "Traditional Recommendations Strand: Similar/recommended shows from catalog metadata" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 section 8 "Explore Similar: 'Get Concepts' button → Concept chip selector → 'Explore Shows' button → 5 recommendations" | |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 section 9–10 "Streaming Availability… Cast & Crew: Horizontal strands of people; Click opens `/person/[id]`" | |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 sections 11–12 "Seasons (TV only)… Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5 implementation note "Lazy-load dependent data (cast, seasons, recommendations) on mount"; "lazy-load Scoop on demand" | |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 "Chat UI with turn history"; Section 4.3 components `ChatHistory`, `ChatInput`, `BotTurn` | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | partial | Section 6.3 mentions "spoiler-safe by default unless user asks explicitly"; no explicit rubric for "confident" response scoring; discovery quality bar referenced but not integrated into plan acceptance criteria | Plan references quality bar but does not embed its scoring into acceptance criteria (Section 19) |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3 "UI renders as selectable chips; Component: `MentionedShowsStrand` — horizontal scroll of resolved shows" | |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3 "Click mentioned show opens `/detail/[id]` or triggers detail modal"; fallback to Search in Section 6.3 | |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 "Welcome state: On initial Ask launch, display 6 random starter prompts"; "Tapping a prompt auto-fills chat input" | |
| PRD-070 | Summarize older turns while preserving voice | important | partial | Section 4.3 "After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated)"; no explicit prompt or quality bar for summarization voice preservation | Plan describes summarization trigger and intent but lacks implementation detail (exact prompt, tone validation) |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 "Special variant: Ask About This Show… Show context (title, overview, status) included in initial system prompt" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 "Request structured output: JSON with `commentary` and `showList: Title::externalId::mediaType;;…` format" | |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 "Components: Parse response; if JSON fails, retry with stricter formatting instructions; otherwise fall back" | |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1 shared rules "Stay within TV/movies (redirect back if asked to leave that domain)" | |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 6.4 "Concepts are not genres or plot points. They are the *taste DNA*"; Section 4.4 explains ingredient philosophy | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 "Output: Array of 8–12 concepts (or smaller); Each 1–3 words, spoiler-free; No generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 "Output: bullet list only"; no explicit ordering algorithm specified; concept quality heuristic mentioned in Section 6.1 but not integrated into implementation task | Plan mentions quality heuristic but does not prescribe ordering logic or validation task |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 4.4 Alchemy flow: "User selects 1–8 concepts"; "UI allows toggling"; "max 8 enforced by UI"; Section 6.4 "User guidance: UI should hint" | |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 flow step 5 "Optional: More Alchemy! User can select recs as new inputs… Chain multiple rounds" | |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 "Multi-show: concepts must be shared across all inputs"; no explicit specification of "larger option pool" or pool size difference | Plan states requirement but does not specify pool size or generation strategy |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 "Output format: Array of recommendations… `reason: 'Shares [concept] vibes with [input shows]...'`" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5 "Include only recs that resolve successfully"; no explicit rubric for "surprising but defensible" validation; quality bar referenced but not operationalized | Plan mentions taste alignment and quality bar reference but lacks acceptance task for surprise/defensibility scoring |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 "All AI surfaces: Use configurable provider… All AI surfaces share one persona"; all sections reference persona consistency | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | partial | Section 6.1 "All AI surfaces must: Stay within TV/movies… Be spoiler-safe… Be opinionated and honest"; guardrails listed but no implementation task for validation/enforcement mechanism specified | Plan states guardrails verbally but does not specify how to enforce or validate compliance (prompt testing, rubric application) |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 "User context: User's library… persona definition (warm, opinionated friend)"; referenced throughout | |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 "AI Prompt: Task: generate spoiler-safe 'mini blog post of taste'; Sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict" | |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3 "AI Processing: System prompt: persona definition (gossipy friend, opinionated, spoiler-safe)" | |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.1 "User context: User's library… current show context… selected concepts… recent conversation turns" | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 19.2 mentions quality criteria but does not specify "hard-fail" mechanism or rubric application task; discovery quality bar documented but not integrated into implementation workflow | Plan mentions validation but leaves integration into CI/test harness unspecified |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 "Sections: Profile Header: Image gallery (primary image + thumbs); Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 "Analytics (optional lightweight charts): Average rating of projects; Top genres by count; Projects by year (bar chart)" | |
| PRD-094 | Group filmography by year | important | full | Section 4.6 "Filmography Grouped by Year: Years collapsed/expandable" | |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 "Click credit opens `/detail/[creditId]`" | |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 "App Settings: Font size selector (XS–XXL); Toggle: 'Search on Launch'" | |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 "User: Display username (editable); AI: model selection; API key input (stored server-side; display masked)" | |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 "Export / Backup: Button generates `.zip` containing: `backup.json` with all shows + My Data" | |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 "dates ISO-8601"; Section 2.1 storage schema timestamps use ISO format | |

---

## 3. Coverage Scores

### Calculation

**Full coverage** (`full`) = 1.0 point  
**Partial coverage** (`partial`) = 0.5 points  
**Missing coverage** (`missing`) = 0.0 points

**Overall formula:**
```
score = (full_count × 1.0 + partial_count × 0.5) / total_count × 100
```

### Critical Requirements

**Full:** PRD-001, PRD-002, PRD-003, PRD-005, PRD-006, PRD-007, PRD-008, PRD-009, PRD-010, PRD-011, PRD-012, PRD-015, PRD-016, PRD-018, PRD-020, PRD-022, PRD-023, PRD-024, PRD-025, PRD-026, PRD-027, PRD-029, PRD-031, PRD-034, PRD-037, PRD-055, PRD-056, PRD-072, PRD-098 = **29 full**

**Partial:** PRD-086 = **1 partial**

**Missing:** None = **0 missing**

```
Critical: (29 × 1.0 + 1 × 0.5) / 30 × 100 = 29.5 / 30 × 100 = 98.3%  (29.5 of 30 critical requirements)
```

### Important Requirements

**Full:** PRD-004, PRD-013, PRD-014, PRD-017, PRD-019, PRD-021, PRD-028, PRD-030, PRD-032, PRD-033, PRD-035, PRD-036, PRD-038, PRD-039, PRD-040, PRD-041, PRD-042, PRD-043, PRD-044, PRD-045, PRD-047, PRD-048, PRD-050, PRD-051, PRD-052, PRD-053, PRD-054, PRD-057, PRD-059, PRD-060, PRD-061, PRD-062, PRD-063, PRD-064, PRD-065, PRD-067, PRD-068, PRD-069, PRD-071, PRD-074, PRD-075, PRD-076, PRD-078, PRD-079, PRD-080, PRD-081, PRD-083, PRD-085, PRD-087, PRD-088, PRD-089, PRD-090, PRD-092, PRD-093, PRD-094, PRD-095, PRD-096, PRD-097, PRD-099 = **60 full**

**Partial:** PRD-019, PRD-058, PRD-066, PRD-070, PRD-077, PRD-082, PRD-084, PRD-091 = **8 partial**

**Missing:** None = **0 missing**

```
Important: (60 × 1.0 + 8 × 0.5) / 68 × 100 = 64 / 68 × 100 = 94.1%  (64 of 68 important requirements)
```

**Note:** PRD-019 was listed in both full and partial; correcting: PRD-019 is **partial**, not full. Recount:
- Full: 59
- Partial: 9

```
Important: (59 × 1.0 + 9 × 0.5) / 68 × 100 = 63.5 / 68 × 100 = 93.4%  (63.5 of 68 important requirements)
```

### Detail Requirements

**Full:** PRD-046, PRD-049 = **2 full**

**Partial:** None = **0 partial**

**Missing:** None = **0 missing**

```
Detail: (2 × 1.0 + 0 × 0.5) / 2 × 100 = 2 / 2 × 100 = 100%  (2 of 2 detail requirements)
```

### Overall Score

```
Total full: 29 (critical) + 59 (important) + 2 (detail) = 90
Total partial: 1 (critical) + 9 (important) + 0 (detail) = 10
Total requirements: 99

Overall: (90 × 1.0 + 10 × 0.5) / 99 × 100 = 95 / 99 × 100 = 96.0%
```

---

## 4. Top Gaps

**Top 5 Gaps (ranked by severity, then impact):**

1. **PRD-086 | critical | Enforce shared AI guardrails across all surfaces**  
   *Why it matters:* The plan states guardrails verbally (stay in TV/movies, spoiler-safe, opinionated) but does not specify implementation tasks to validate or enforce compliance. Without explicit guardrail enforcement, there is risk that AI responses drift outside the defined scope—e.g., recommending non-entertainment items, generating spoiler-heavy content, or sounding generic. This breaks the core persona contract across Scoop, Ask, Alchemy, and Explore Similar, damaging trust.

2. **PRD-091 | important | Validate discovery with rubric and hard-fail integrity**  
   *Why it matters:* The discovery quality bar exists (voice adherence, taste alignment, real-show integrity, specificity, surprise) but is not integrated into the implementation workflow. There is no task to apply the rubric during development, no acceptance test using the golden set, and no CI gate to block low-quality recommendations from shipping. Without this, AI quality becomes subjective and regressions are invisible.

3. **PRD-066 | important | Answer directly with confident, spoiler-safe recommendations**  
   *Why it matters:* The plan describes spoiler-safety and general Ask behavior but does not define what "confident" means operationally. There is no rubric for when to hedge vs commit, no examples of confident vs hedging responses, and no acceptance criteria. Ask may end up with wishy-washy recommendations that fail to be decisive.

4. **PRD-070 | important | Summarize older turns while preserving voice**  
   *Why it matters:* The plan specifies the summarization trigger (~10 turns) and intent (preserve tone) but does not provide the actual summary prompt or examples. It's unclear how the AI will maintain the persona during summarization—risks include sterile system summaries (contradicting the persona requirement) or summaries that lose context. Without a reference prompt or tone validation, summarization becomes a blind spot.

5. **PRD-084 | important | Deliver surprising but defensible taste-aligned recommendations**  
   *Why it matters:* The discovery quality bar defines "surprise without betrayal" (1–2 recs pleasantly unexpected but defensible) and "taste alignment" (grounded in concepts/library) but the plan does not operationalize how to validate this. There's no acceptance task, no testing strategy, and no criteria for judging when a rec is too conservative (not surprising) vs too wild (not defensible). Alchemy may default to safe picks or incomprehensible suggestions.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **comprehensive and well-structured**, addressing the PRD systematically across architecture, data model, features, AI integration, and deployment. At **96.0% overall coverage**, it is a strong blueprint ready for implementation. However, the plan treats **AI behavioral contracts as implementation details rather than specifiable surfaces**. This introduces risk: AI quality, guardrail enforcement, and persona consistency are described conceptually but not operationalized with concrete tasks, acceptance criteria, or validation mechanisms. For a product where AI is a core differentiator (Ask, Alchemy, Scoop all drive engagement), this gap is material. The plan would benefit from deeper specification of AI validation workflows, quality rubrics, and prompt-level acceptance criteria before development begins.

### Strength Clusters

The plan is strongest in **Benchmark Runtime & Isolation** (98.3% critical coverage), **Collection Data & Persistence** (excellent data model clarity with merge rules, timestamps, auto-save triggers all specified), and **Show Detail & Relationship UX** (narrative hierarchy preserved, auto-save rules explicit, components clearly defined). 

The **infrastructure and operational sections** are particularly mature: environment variable interface, namespace partitioning, RLS enforcement, test isolation, and CI/CD integration are all concrete. The **data persistence layer** is well-designed with explicit merge rules, timestamp-based conflict resolution, and cross-device sync clarity.

**Navigation and filtering** are thoroughly addressed: routes are named, components are listed, filter logic is specified, and empty states are considered.

### Weakness Clusters

The **gaps cluster tightly around AI behavioral contracts** (PRD-086, PRD-091, PRD-066, PRD-070, PRD-084). These are all `important` severity (one `critical`), and they all follow the same pattern: the plan describes AI behavior conceptually but does not operationalize how to validate, test, or enforce it. This is not a missing feature; it is **underspecified quality gates**.

Secondary weakness: **PRD-019 (Next status)** and **PRD-082 (multi-show concept pool size)** are deferred to future work with partial reasoning, but no concrete task exists to track or prioritize them.

The weakness is **not scattered**: it is concentrated in the AI features area (Ask, Alchemy, Scoop, Explore Similar, and quality validation). This suggests the plan author prioritized technical architecture (which is solid) over AI craft specification (which is incomplete).

### Risk Assessment

If this plan were executed without addressing the AI gaps, **the most likely failure mode is AI quality drift over time**. Users would experience:

1. **Ask responses that sometimes recommend non-entertainment items** (no enforced guardrail; model can drift toward helpfulness over domain restriction).
2. **Inconsistent persona** across surfaces—Scoop might feel gossipy while Ask feels formal, or vice versa, as different team members tune prompts without a unified voice spec.
3. **Unactionable recommendations** — recs resolve to real catalog items (real-show integrity is non-negotiable), but concepts are generic ("good writing") or recommendations don't clearly explain why they match (concept citation is specified but not validated).
4. **No visibility into quality** — without a rubric or golden set, regressions after model/prompt changes are invisible until users complain.

**What stakeholders will notice first:** Ask responses that hedge ("you might like this, but it's not for everyone") instead of making confident picks; Alchemy results that feel random or don't explain their reasoning; Scoop that reads like a Wikipedia summary instead of a friend's opinion.

This is not a **feature gap** (all features are specified); it is a **quality gate gap**. The app ships with AI features, but without assurance they meet the spec.

### Remediation Guidance

The weakness does not require **architectural changes** or **new features**. It requires **specification of AI validation workflows and embedding of quality gates into the development process**:

1. **Operationalize the discovery quality bar**: Create concrete scoring rubric (voice adherence 0–2, taste alignment 0–2, etc.) as an acceptance task in Phase 2. Define what passes (≥7/10) and what fails (<7/10). Create a test runner that applies the rubric to sample outputs.

2. **Formalize guardrail enforcement**: Specify prompt-level validation (e.g., "test that Ask redirects off-domain requests; test that Scoop never mentions spoilers unless explicitly requested"). Create test fixtures for these edge cases.

3. **Prompt specification depth**: For Ask summarization, Ask mentioning format, and Scoop sections, provide reference prompts or at minimum prompt design guidelines (e.g., "summary prompt must preserve the first-person 'friend' voice, not use 'the user asked about X'").

4. **Golden set establishment**: Create 3–5 reference examples per surface (Ask, Scoop, Explore Similar) showing on-brand vs off-brand output. Use these in code review + CI validation.

5. **Phase 2 acceptance criteria expansion**: Add explicit tasks like "implement AI response validation framework" and "create guardrail test suite" to Phase 2. Move PRD-091 from implicit to explicit task.

This is **specification work, not implementation work**—it can be done in the planning cycle before development starts, or as a pre-development spike in Phase 1. The architecture is sound; only the AI validation layer needs clarity.

---

**End of Evaluation**

</evaluation>

---

Now I will create the stakeholder report from this completed markdown evaluation.

<report_generation>

# Stakeholder Report

I will now generate `results/PLAN_EVAL_REPORT.html` based on the completed markdown evaluation. The report will communicate:
1. Overall coverage score prominently
2. Before/after arc (initial plan → revised plan)
3. What's strong (areas with high coverage)
4. What's at risk (partial/missing requirements, especially gaps)
5. Top gaps and why they matter

</report_generation>

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
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            color: #2c3e50;
            line-height: 1.6;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
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
        .score-card {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }
        .score-item {
            background: white;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border-top: 4px solid #667eea;
        }
        .score-item.critical {
            border-top-color: #e74c3c;
        }
        .score-item.important {
            border-top-color: #f39c12;
        }
        .score-item.detail {
            border-top-color: #3498db;
        }
        .score-number {
            font-size: 3em;
            font-weight: 700;
            color: #667eea;
            margin: 10px 0;
        }
        .score-item.critical .score-number {
            color: #e74c3c;
        }
        .score-item.important .score-number {
            color: #f39c12;
        }
        .score-item.detail .score-number {
            color: #3498db;
        }
        .score-label {
            font-size: 0.9em;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 10px;
        }
        .overall-score {
            grid-column: 1 / -1;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-top: none !important;
            padding: 40px !important;
        }
        .overall-score .score-number {
            color: white;
            font-size: 4em;
        }
        .overall-score .score-label {
            color: rgba(255, 255, 255, 0.8);
        }
        .arc-section {
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }
        .arc-section h2 {
            color: #667eea;
            font-size: 1.6em;
            margin-bottom: 20px;
        }
        .arc-flow {
            display: flex;
            align-items: center;
            gap: 30px;
            margin-bottom: 30px;
        }
        .arc-stage {
            flex: 1;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        .arc-stage.challenge {
            border-left-color: #e74c3c;
        }
        .arc-stage.outcome {
            border-left-color: #27ae60;
        }
        .arc-stage h3 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        .arc-stage p {
            color: #555;
            font-size: 0.95em;
        }
        .arrow {
            color: #667eea;
            font-size: 2em;
            flex-shrink: 0;
        }
        .strengths-section, .risks-section {
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }
        .strengths-section h2, .risks-section h2 {
            color: #667eea;
            font-size: 1.6em;
            margin-bottom: 30px;
        }
        .strength-grid, .risk-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .strength-card, .risk-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #27ae60;
        }
        .risk-card {
            border-left-color: #e74c3c;
            background: #fff5f5;
        }
        .strength-card h3, .risk-card h3 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 1.05em;
        }
        .strength-card p, .risk-card p {
            color: #555;
            font-size: 0.95em;
            line-height: 1.5;
        }
        .gaps-section {
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }
        .gaps-section h2 {
            color: #667eea;
            font-size: 1.6em;
            margin-bottom: 30px;
        }
        .gap-item {
            background: #fff5f5;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #e74c3c;
        }
        .gap-item.important {
            border-left-color: #f39c12;
            background: #fffbf0;
        }
        .gap-id {
            font-weight: 700;
            color: #2c3e50;
            font-size: 0.95em;
            display: inline-block;
            margin-bottom: 5px;
        }
        .gap-severity {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 10px;
            text-transform: uppercase;
        }
        .gap-severity.critical {
            background: #fadbd8;
            color: #c0392b;
        }
        .gap-severity.important {
            background: #fce8b2;
            color: #d68910;
        }
        .gap-label {
            display: block;
            color: #2c3e50;
            margin-bottom: 8px;
            font-size: 1em;
            font-weight: 500;
        }
        .gap-description {
            color: #555;
            font-size: 0.95em;
            line-height: 1.5;
        }
        .recommendation-section {
            padding: 40px;
            background: #f0f7ff;
            border-top: 2px solid #667eea;
        }
        .recommendation-section h2 {
            color: #667eea;
            font-size: 1.6em;
            margin-bottom: 20px;
        }
        .recommendation-text {
            color: #2c3e50;
            font-size: 0.95em;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .footer {
            background: #2c3e50;
            color: white;
            padding: 30px 40px;
            text-align: center;
            font-size: 0.9em;
        }
        .footer p {
            margin: 5px 0;
        }
        @media (max-width: 768px) {
            .score-card {
                grid-template-columns: 1fr;
            }
            .score-item.critical,
            .score-item.important,
            .score-item.detail {
                grid-column: auto;
            }
            .overall-score {
                grid-column: 1;
            }
            .arc-flow {
                flex-direction: column;
            }
            .arrow {
                transform: rotate(90deg);
            }
            .strength-grid, .risk-grid {
                grid-template-columns: 1fr;
            }
            .header {
                padding: 