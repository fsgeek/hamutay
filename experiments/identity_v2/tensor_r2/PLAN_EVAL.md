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
| PRD-001 | Use Next.js latest stable runtime | critical | full | Section 1.1 Technology Stack; Section 10.2 Development Environment |  |
| PRD-002 | Use Supabase official client libraries | critical | full | Section 1.1 Technology Stack; Section 8.1 Server-Only Secrets mentions Supabase client libraries |  |
| PRD-003 | Ship `.env.example` with required variables | critical | full | Section 10.1 Environment Variables provides complete `.env.example` template |  |
| PRD-004 | Ignore `.env*` secrets except example | important | full | Section 10.1 Environment Variables; `.gitignore` rule specified |  |
| PRD-005 | Configure build through env without code edits | critical | full | Section 10.1 Environment Variables states "All secrets injected at runtime" |  |
| PRD-006 | Keep secrets out of repo and server-only | critical | full | Section 8.3 Input Validation; Section 15.2 Secrets Management |  |
| PRD-007 | Provide app, test, reset command scripts | critical | full | Section 10.4 Scripts lists npm commands (dev, build, start, test, test:reset, db:push, db:seed) |  |
| PRD-008 | Include repeatable schema evolution artifacts | critical | full | Section 2.2 Database Schema; Section 10.2 Development Environment mentions migrations |  |
| PRD-009 | Use one stable namespace per build | critical | full | Section 1.2 Key Architectural Principles; Section 10.3 CI/CD assigns `NAMESPACE_ID` per build |  |
| PRD-010 | Isolate namespaces and scope destructive resets | critical | full | Section 9.2 Destructive Testing specifies `/api/test/reset` scoped to namespace |  |
| PRD-011 | Attach every user record to `user_id` | critical | full | Section 1.2 Key Architectural Principles; Section 2.1 Core Entities schema includes user_id |  |
| PRD-012 | Partition persisted data by namespace and user | critical | full | Section 2.2 Database Schema RLS enforces `(namespace_id, user_id)` partition |  |
| PRD-013 | Support documented dev auth injection, prod-gated | important | full | Section 8.1 Benchmark-Mode Identity Injection specifies X-User-Id header in dev mode |  |
| PRD-014 | Real OAuth later needs no schema redesign | important | full | Section 8.2 Future OAuth Path states "Schema unchanged, only middleware changes" |  |
| PRD-015 | Keep backend as persisted source of truth | critical | full | Section 1.2 Key Architectural Principles states "Backend is source of truth" |  |
| PRD-016 | Make client cache safe to discard | critical | full | Section 13.1 Client-Side Caching; Section 1.2 states "clients may cache for performance, but correctness depends on server state" |  |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | important | full | Section 10.2 Development Environment states "No Docker requirement" |  |
| PRD-018 | Overlay saved user data on every show appearance | critical | full | Section 4.1 Collection Home; Section 4.5 Show Detail; Section 5.1 Collection Membership |  |
| PRD-019 | Support visible statuses plus hidden `Next` | important | full | Section 5.3 Status System lists all statuses including Next; Section 20 Open Questions notes Next not first-class UI yet |  |
| PRD-020 | Map Interested/Excited chips to Later interest | critical | full | Section 5.2 Auto-Save Triggers table; Section 5.3 Status System explains mapping |  |
| PRD-021 | Support free-form multi-tag personal tag library | important | full | Section 4.5 Show Detail "My Tags display + tag picker"; Section 2.1 Core Entities includes myTags |  |
| PRD-022 | Define collection membership by assigned status | critical | full | Section 5.1 Collection Membership definition: "show is in collection when myStatus != nil" |  |
| PRD-023 | Save shows from status, interest, rating, tagging | critical | full | Section 5.2 Auto-Save Triggers table lists all four triggers |  |
| PRD-024 | Default save to Later/Interested except rating-save Done | critical | full | Section 5.2 Auto-Save Triggers; Section 5.3 explicitly states defaults |  |
| PRD-025 | Removing status deletes show and all My Data | critical | full | Section 5.4 Removal Confirmation states "clears all My Data" |  |
| PRD-026 | Re-add preserves My Data and refreshes public data | critical | full | Section 7.2 Data Fetch & Merge explains merge rules preserving user fields |  |
| PRD-027 | Track per-field My Data modification timestamps | critical | full | Section 2.1 Core Entities; Section 5.5 Timestamps & Merge Resolution |  |
| PRD-028 | Use timestamps for sorting, sync, freshness | important | full | Section 5.5 Timestamps & Merge Resolution explains uses |  |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | critical | full | Section 6.2 Scoop Generation states "Only persist if show is in collection" + 4-hour cache |  |
| PRD-030 | Keep Ask and Alchemy state session-only | important | full | Section 5.6 AI Data Persistence table; Section 6.3 Ask states "not cached" |  |
| PRD-031 | Resolve AI recommendations to real selectable shows | critical | full | Section 7.2 Data Fetch & Merge; Section 6.5 Concept-Based Recommendations "Resolution" |  |
| PRD-032 | Show collection and rating tile indicators | important | full | Section 5.8 Tile Indicators specifies both badges |  |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | important | full | Section 5.5 Timestamps & Merge Resolution specifies merge behavior |  |
| PRD-034 | Preserve saved libraries across data-model upgrades | critical | full | Section 2.3 Data Continuity & Migrations states "No user data loss; all shows brought forward" |  |
| PRD-035 | Persist synced settings, local settings, UI state | important | full | Section 2.1 Core Entities includes CloudSettings, LocalSettings, UIState |  |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | important | full | Section 2.1 Core Entities schema distinguishes externalIds (persistent) from transient fetches |  |
| PRD-037 | Merge catalog fields safely and maintain timestamps | critical | full | Section 7.2 Data Fetch & Merge specifies merge rules with timestamp resolution |  |
| PRD-038 | Provide filters panel and main screen destinations | important | full | Section 3.1 Top-Level Layout; Section 3.2 Routes & Pages |  |
| PRD-039 | Keep Find/Discover in persistent primary navigation | important | full | Section 3.1 Top-Level Layout mentions persistent Find/Discover entry point |  |
| PRD-040 | Keep Settings in persistent primary navigation | important | full | Section 3.1 Top-Level Layout mentions persistent Settings entry point |  |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | important | full | Section 3.2 Routes specifies `/find/search`, `/find/ask`, `/find/alchemy` with mode switcher |  |
| PRD-042 | Show only library items matching active filters | important | full | Section 4.1 Collection Home "filtered by sidebar selection" |  |
| PRD-043 | Group home into Active, Excited, Interested, Others | important | full | Section 4.1 Collection Home lists all four groups |  |
| PRD-044 | Support All, tag, genre, decade, score, media filters | important | full | Section 4.1 Collection Home lists all filter types + media type toggle |  |
| PRD-045 | Render poster, title, and My Data badges | important | full | Section 4.1 "Display tiles with poster, title, in-collection indicator, rating badge" |  |
| PRD-046 | Provide empty-library and empty-filter states | detail | full | Section 4.1 Collection Home "EmptyState — when no shows match filter" |  |
| PRD-047 | Search by title or keywords | important | full | Section 4.2 Search "Text input sends query; results rendered as poster grid" |  |
| PRD-048 | Use poster grid with collection markers | important | full | Section 4.2 Search "In-collection items marked with indicator" |  |
| PRD-049 | Auto-open Search when setting is enabled | detail | full | Section 4.2 Search "If `settings.autoSearch` is true, `/find/search` opens on app startup" |  |
| PRD-050 | Keep Search non-AI in tone | important | full | Section 4.2 Search implementation does not include AI; styled as straightforward catalog search |  |
| PRD-051 | Preserve Show Detail narrative section order | important | full | Section 4.5 Show Detail lists 12 sections in order from header to budget |  |
| PRD-052 | Prioritize motion-rich header with graceful fallback | important | full | Section 4.5 "Header Media — Carousel: backdrops/posters/logos/trailers; Fall back to static poster" |  |
| PRD-053 | Surface year, runtime/seasons, and community score early | important | full | Section 4.5 "Core Facts Row — Year, runtime (movie) or seasons/episodes (TV), Community score bar" |  |
| PRD-054 | Place status/interest controls in toolbar | important | full | Section 4.5 "My Relationship Toolbar — Status chips: Active/Interested/Excited/Done/Quit/Wait" |  |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | critical | full | Section 4.5 Detail "Auto-save behaviors"; Section 5.2 shows tagging trigger |  |
| PRD-056 | Auto-save unsaved rated show as Done | critical | full | Section 4.5 Detail "Auto-save behaviors"; Section 5.2 shows rating trigger |  |
| PRD-057 | Show overview early for fast scanning | important | full | Section 4.5 Show Detail includes Overview in section 4 |  |
| PRD-058 | Scoop shows correct states and progressive feedback | important | full | Section 6.2 Scoop Generation states "streams progressively if the UI supports it" |  |
| PRD-059 | Ask-about-show deep-link seeds Ask context | important | full | Section 4.3 Ask "Special variant: Ask About This Show" seeded with show context |  |
| PRD-060 | Include traditional recommendations strand | important | full | Section 4.5 Show Detail section 7 "Traditional Recommendations Strand" |  |
| PRD-061 | Explore Similar uses CTA-first concept flow | important | full | Section 4.5 Show Detail section 8 "Explore Similar" describes Get Concepts → Select → Explore Shows |  |
| PRD-062 | Include streaming availability and person-linking credits | important | full | Section 4.5 Show Detail sections 9–10 include streaming and cast/crew |  |
| PRD-063 | Gate seasons to TV and financials to movies | important | full | Section 4.5 Show Detail "TV-specific season/episode list"; "movie financials" |  |
| PRD-064 | Keep primary actions early and page not overwhelming | important | full | Section 4.5 Show Detail narrative hierarchy documented |  |
| PRD-065 | Provide conversational Ask chat interface | important | full | Section 4.3 Ask describes chat UI with turn history |  |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | important | full | Section 6.3 Ask Processing step 1 includes persona definition; spoiler-safe as shared rule |  |
| PRD-067 | Show horizontal mentioned-shows strip from chat | important | full | Section 4.3 Ask "Render mentioned shows as horizontal strand (selectable)" |  |
| PRD-068 | Open Detail from mentions or Search fallback | important | full | Section 4.3 Ask "Click mentioned show opens `/detail/[id]` or triggers detail modal" |  |
| PRD-069 | Show six random starter prompts with refresh | important | full | Section 4.3 Ask "Welcome state — 6 random starter prompts; refresh available" |  |
| PRD-070 | Summarize older turns while preserving voice | important | full | Section 4.3 Ask "Context management — After ~10 turns, summarize older turns; Preserve feeling/tone" |  |
| PRD-071 | Seed Ask-about-show sessions with show handoff | important | full | Section 4.3 Ask "Special variant: Ask About This Show — Button on Detail opens Ask with pre-seeded context" |  |
| PRD-072 | Emit `commentary` plus exact `showList` contract | critical | full | Section 6.3 Ask Processing specifies structured JSON output with commentary + showList |  |
| PRD-073 | Retry malformed mention output once, then fallback | important | full | Section 6.3 Ask "Response Processing — Parse JSON; if JSON fails, retry with stricter instructions; Fallback: show non-interactive mentions" |  |
| PRD-074 | Redirect Ask back into TV/movie domain | important | full | Section 6.1 Shared Architecture lists shared rule: "Stay within TV/movies (redirect back if asked to leave)" |  |
| PRD-075 | Treat concepts as taste ingredients, not genres | important | full | Section 4.4 Concepts "generate short, evocative concept 'ingredients' that capture core feeling" |  |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | important | full | Section 6.4 Concepts Generation "Output: bullet list only; each concept 1–3 words, spoiler-free; no generic placeholders" |  |
| PRD-077 | Order concepts by strongest aha and varied axes | important | partial | Section 6.4 Concepts Generation mentions "Call AI with appropriate prompt" but implementation details of ordering/diversity not specified in API design |  Gap: Plan does not specify how AI is prompted to order by strength and diversity across axes, or how to validate diversity algorithmically. |
| PRD-078 | Require concept selection and guide ingredient picking | important | full | Section 6.4 Concepts Generation; Section 4.4 Alchemy flow requires user concept selection |  |
| PRD-079 | Return exactly five Explore Similar recommendations | important | full | Section 6.5 Concept-Based Recommendations "Counts: Explore Similar: 5 recs per round" |  |
| PRD-080 | Support full Alchemy loop with chaining | important | full | Section 4.4 Alchemy "Optional: More Alchemy! — User can select recs as new inputs; Chain multiple rounds" |  |
| PRD-081 | Clear downstream results when inputs change | important | full | Section 4.4 Alchemy "Backtracking allowed: changing shows clears concepts/results" |  |
| PRD-082 | Generate shared multi-show concepts with larger option pool | important | partial | Section 6.4 Concepts Generation has single endpoint `/api/shows/concepts/multi` but plan does not specify larger pool size or how to ensure shared commonality across input shows. | Gap: Plan lacks concrete guidance on multi-show concept pool size vs single-show, and how to enforce "shared across all inputs" algorithmically. |
| PRD-083 | Cite selected concepts in concise recommendation reasons | important | full | Section 6.5 Concept-Based Recommendations "Output format" shows reason field that "explicitly reflect the selected concepts" |  |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | important | partial | Section 6.5 mentions "bias toward recent shows but allow classics/hidden gems" but plan does not specify discovery quality validation rubric or how to measure "surprising but defensible" | Gap: Plan describes intent but lacks operational acceptance criteria for quality. Acceptance criteria in section 19.2 only mentions "Quality criteria" generically. |
| PRD-085 | Keep one consistent AI persona across surfaces | important | full | Section 6.1 Shared Architecture states "All AI surfaces use configurable provider" with shared persona; Section 6.6 Prompt Management mentions "one config per surface" |  |
| PRD-086 | Enforce shared AI guardrails across all surfaces | critical | full | Section 6.1 Shared Architecture specifies shared rules (spoiler-safe, opinionated, honest, vibe-first) |  |
| PRD-087 | Make AI warm, joyful, and light in critique | important | full | Section 6.1 Shared Architecture; Section 6.6 Prompt Management references ai_personality_opus.md for tone |  |
| PRD-088 | Structure Scoop as personal taste mini-review | important | full | Section 6.2 Scoop Generation "AI Prompt includes sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict" |  |
| PRD-089 | Keep Ask brisk and dialogue-like by default | important | full | Section 6.3 Ask Processing step 1 specifies persona includes "respond like a friend in dialogue (not an essay)" |  |
| PRD-090 | Feed AI the right surface-specific context inputs | important | full | Section 6.2–6.5 each specify input structure for their surface |  |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | important | partial | Section 6.6 Prompt Management states prompts are updated to "maintain behavior" but plan does not specify how discovery quality is validated operationally (automated tests, human review, metric dashboard). | Gap: No QA/validation process for AI quality specified; acceptance criteria mention "matches voice spec" but no automated enforcement mechanism. |
| PRD-092 | Show person gallery, name, and bio | important | full | Section 4.6 Person Detail Page "Sections: Profile Header — Image gallery, name, bio" |  |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | important | full | Section 4.6 Person Detail Page "Analytics — ratings, genres, projects by year (bar chart)" |  |
| PRD-094 | Group filmography by year | important | full | Section 4.6 Person Detail Page "Filmography Grouped by Year — Years collapsed/expandable" |  |
| PRD-095 | Open Show Detail from selected credit | important | full | Section 4.6 Person Detail Page "Click credit opens `/detail/[creditId]`" |  |
| PRD-096 | Include font size and Search-on-launch settings | important | full | Section 4.7 Settings & Your Data "App Settings: Font size selector, Toggle: Search on Launch" |  |
| PRD-097 | Support username, model, and API-key settings safely | important | full | Section 4.7 Settings & Your Data "User: Display username"; "AI: provider/model/key inputs"; "stored server-side" |  |
| PRD-098 | Export saved shows and My Data as zip | critical | full | Section 4.7 Settings & Your Data "Export button generates `.zip` containing backup.json with all shows + My Data" |  |
| PRD-099 | Encode export dates using ISO-8601 | important | full | Section 4.7 Settings & Your Data "dates ISO-8601" |  |

---

## 3. Coverage Scores

### Calculation

**Overall score:**

```
Full count: 92
Partial count: 7
Missing count: 0
Total count: 99

score = (92 × 1.0 + 7 × 0.5) / 99 × 100
      = (92 + 3.5) / 99 × 100
      = 95.5 / 99 × 100
      = 96.46%
```

**Score by severity tier:**

**Critical requirements:**
- Full: 26
- Partial: 4 (PRD-082, PRD-084, PRD-091 are *important* not critical; recount: PRD-077 is important, PRD-082 is important, PRD-084 is important, PRD-091 is important; actually 0 partial critical)
- Critical total: 30
- All 30 critical items are full coverage

```
Critical:  (26 × 1.0 + 0 × 0.5) / 26 × 100 = 100%  (26 of 26 critical requirements fully covered)
```

Let me recount critical coverage more carefully:
- PRD-001 through PRD-017: 17 critical items in Benchmark area
- PRD-018 through PRD-037: 15 critical items in Collection area (PRD-018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037)
- Total critical: 26 + others... 

Actually, let me systematically recount from requirements:

**Critical requirements (all areas):**
1. PRD-001–PRD-017 (Benchmark): 17 critical
2. PRD-018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037 (Collection): 12 critical
3. PRD-055, 056, 072, 086 (Detail/Ask/Voice): 4 critical
4. PRD-098 (Export): 1 critical

Total critical: 17 + 12 + 4 + 1 = 34 critical (not 30 per catalog)

Let me check catalog exact count: it states "Total: 99 requirements (30 critical, 67 important, 2 detail)". This is authoritative. I'll trust the catalog and recount my evaluation:

Recounting PRD-IDs marked as `critical` in my extraction:
PRD-001, 002, 003, 005, 006, 007, 008, 009, 010, 011, 012, 015, 016 (Benchmark: 13)
PRD-018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037 (Collection: 12)
PRD-055, 056 (Detail: 2)
PRD-072, 086 (Ask/Voice: 2)
PRD-098 (Export: 1)

Total: 13 + 12 + 2 + 2 + 1 = 30 critical ✓

**Critical coverage:**
- Full: 26 (all except PRD-077, 082, 084, 091 which are `important` not critical)
  Actually: PRD-077, 082, 084, 091 are all `important`. So all 30 critical are full.
- Partial: 0
- Missing: 0

```
Critical:  (26 × 1.0 + 0 × 0.5) / 26 × 100 = 100%  (26 of 26 critical requirements)
```

Wait, this math is wrong. Let me recount critical:

From my evaluation table, all items marked `critical` in severity:
PRD-001, 002, 003, 005, 006, 007, 008, 009, 010, 011, 012, 015, 016, 018, 020, 022, 023, 024, 025, 026, 027, 029, 031, 034, 037, 055, 056, 072, 086, 098

Count: 30 critical items
Coverage: All 30 are marked `full`

```
Critical:  (30 × 1.0) / 30 × 100 = 100%  (30 of 30 critical requirements)
```

**Important requirements:**
From my evaluation: PRD-004, 013, 014, 017, 019, 021, 028, 030, 032, 033, 035, 036, 038–050, 051–071, 073–091 (minus critical ones)

Let me count: 30 critical + 67 important + 2 detail = 99
- Important count: 67
- Coverage by evaluation:
  - Full: 63 (PRD-077, 082, 084, 091 are partial; PRD-046, 049 are detail not important)
  - Partial: 4 (PRD-077, 082, 084, 091)
  - Missing: 0

```
Important: (63 × 1.0 + 4 × 0.5) / 67 × 100 = (63 + 2) / 67 × 100 = 97.01%  (63 full, 4 partial of 67 important requirements)
```

**Detail requirements:**
PRD-046, 049

Coverage:
- Full: 2
- Partial: 0

```
Detail:    (2 × 1.0) / 2 × 100 = 100%  (2 of 2 detail requirements)
```

**Overall:**
```
Overall:   (92 × 1.0 + 7 × 0.5) / 99 × 100 = 95.5 / 99 × 100 = 96.46%
```

---

## 4. Top Gaps

Ranked by severity tier first (critical > important > detail), then by impact within tier:

### Gap 1: PRD-091 (Important) — Validate discovery with rubric and hard-fail integrity

**Why it matters:**  
The plan describes how AI is called and responses parsed, but provides no operational acceptance criteria or validation mechanism for ensuring AI quality meets the discovery quality bar. Without automated or explicit QA processes, regressions in concept generation or recommendation taste-alignment may go undetected. The PRD's discovery quality bar (specificity, voice, taste alignment, real-show integrity) cannot be enforced without a test harness or human review protocol.

### Gap 2: PRD-084 (Important) — Deliver surprising but defensible taste-aligned recommendations

**Why it matters:**  
The plan states Alchemy/Explore Similar should include "surprising but defensible" recs and mentions "bias toward recent shows but allow classics/hidden gems," but provides no criteria for measuring whether recommendations meet this bar operationally. Acceptance criteria (section 19) only generically state "taste-aligned recommendations" without specifying a discovery quality rubric, automated validation, or human evaluation protocol. The result may be recommendations that feel obvious or, conversely, too random.

### Gap 3: PRD-082 (Important) — Generate shared multi-show concepts with larger option pool

**Why it matters:**  
The plan mentions multi-show concept generation exists (`/api/shows/concepts/multi`) but does not specify: (1) how the larger option pool differs in size/diversity from single-show concepts, (2) how "shared across all inputs" is enforced algorithmically, (3) what happens if fewer than N concepts are shared, or (4) how API design differs from single-show endpoint. This ambiguity could lead to inconsistent concept quality or UX confusion (e.g., what counts as "shared"?).

### Gap 4: PRD-077 (Important) — Order concepts by strongest aha and varied axes

**Why it matters:**  
The plan states concepts should be ordered by "strongest aha" and "varied across axes" (structure, vibe, emotion, craft) but does not specify how the AI prompt ensures this ordering, how diversity is validated (automated or manual), or what acceptance criteria determine if ordering is acceptable. Without concrete guidance, implementations may generate ordered lists without strategic diversity, leading to eight similar concepts rather than a diverse set.

### Gap 5: PRD-014 (Important) — Real OAuth later needs no schema redesign

**While critical for future migration, the plan adequately addresses this:** Section 8.2 explicitly states "Schema unchanged, only middleware changes" and the modeled `user_id` as opaque string preserves flexibility. This gap is low-impact because the plan's design already satisfies the requirement. **Not included as a critical gap.**

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally very strong** with comprehensive coverage of all major functional areas. It provides a concrete, implementation-ready blueprint that addresses 96.46% of requirements with explicit sections for data model, API design, testing, and operational safety. The plan demonstrates deep understanding of the PRD's core philosophy (taste-aware discovery, user data precedence, consistent AI voice) and translates it into testable, verifiable behavior. 

However, **quality assurance for AI outputs is the weak point.** The plan excels at *how to call AI services and parse responses*, but does not operationalize *how to validate that AI outputs meet taste/specificity standards*. This is not a missing feature (all AI surfaces are designed), but a missing QA/validation framework.

### Strength Clusters

**1. Benchmark Runtime & Isolation (Perfect Coverage)**  
The plan thoroughly addresses all infrastructure and isolation requirements. Namespace partitioning, dev-mode identity injection, environment-driven configuration, and isolation of destructive testing are all concretely specified. Section 10 (Infrastructure & Deployment) and Section 8 (Authentication & Authorization) leave no ambiguity about how to run safe, repeatable benchmarks.

**2. Collection Data & Persistence (100% of critical requirements)**  
All 12 critical collection requirements are fully addressed. The data model (Section 2.1) is explicit; merge rules (Section 7.2) are detailed; auto-save triggers (Section 5.2) are enumerated in a table; timestamp-based conflict resolution is specified. Collection membership, status system, tags, and My Data overlay are all concrete.

**3. Show Detail & Relationship UX (Full Implementation)**  
The Detail page specification (Section 4.5) walks through all 12 sections in narrative order, with auto-save behaviors, Scoop caching, Explore Similar flow, and removal confirmation all explicitly designed. Primary actions (status, rating, tagging) trigger auto-saves as required.

**4. Settings & Export (Complete)**  
Font size, Search-on-launch, username, AI model/key, export as JSON zip with ISO-8601 dates—all specified in Section 4.7. The export endpoint (`/api/export`) is concrete.

**5. Ask Chat & Mention Resolution (Highly Detailed)**  
Section 4.3 and Section 6.3 provide extensive detail on chat UI, starter prompts, context management, and the critical `showList` structured output contract. Mention resolution (parsing, retry, fallback) is explicit.

### Weakness Clusters

**1. AI Quality Assurance (4 partial requirements cluster here: PRD-077, PRD-082, PRD-084, PRD-091)**  
All four gaps concern *how AI outputs are validated to meet quality standards*:
- PRD-077 (Concept ordering by aha/diversity) — no prompt-validation mechanism
- PRD-082 (Multi-show concept pool size) — no specification of how "shared" is enforced
- PRD-084 (Surprising-but-defensible recs) — no acceptance criteria beyond "defensible"
- PRD-091 (Validate discovery with rubric) — no QA/test harness described

The plan describes *calling* AI and *parsing responses*, but not *validating response quality operationally*. Section 19 (Acceptance Criteria) lacks a "discovery quality rubric QA process" item.

**2. Concept Generation Specification (2 partial requirements: PRD-077, PRD-082)**  
Beyond the validation gap, the plan treats concept generation as a black box ("call AI with appropriate prompt") without specifying:
- Expected pool size (single-show vs multi-show)
- Algorithm for enforcing diversity across axes
- What "shared across all inputs" means algorithmically (all N shows must have the concept? Or K of N?)
- Fallback if fewer concepts are shared than expected

### Risk Assessment

**If this plan were executed as-is without addressing the AI quality gaps:**

A user would experience:
1. **Concepts that look specific but lack diversity.** Example: Eight 1-3-word concepts generated, but five are synonymous ("hopeful," "optimistic," "uplifting," "feel-good," "wholesome"). The prompt may say "diverse," but without validation, duplicates slip through.

2. **Alchemy recommendations that feel random or obvious.** Without a discovery quality bar enforced in testing, recs might be genre-adjacent but not taste-aligned, or predictable rather than surprising. Example: "You liked Breaking Bad? Here are 5 other crime dramas."

3. **Multi-show concept generation behaving unpredictably.** When blending 3 shows, concepts may not actually be shared (only 1 show has "ironic crime-solving"), or pool size might be identical to single-show (limiting serendipity in Alchemy).

4. **No regression detection for AI drift.** As prompts evolve (new model, new provider), regressions in voice or taste-alignment won't be caught until users complain.

The core product still works—Alchemy generates 6 recs, Ask mentions shows, Scoop caches. But the *heart* of the product (taste-aware, delightful discovery) may degrade silently.

### Remediation Guidance

**For weakness clusters, the work needed is:**

1. **Create a discovery quality assurance framework** (not implementation tasks, but planning work):
   - Define automated tests that validate concept specificity (no generic placeholders like "good characters")
   - Define rubric scoring for Alchemy recs (voice adherence, taste alignment, real-show integrity per discovery_quality_bar.md)
   - Establish manual QA checkpoints (e.g., weekly review of 5 random Alchemy sessions, scoring against rubric)
   - Add golden test set (Section 3 of discovery_quality_bar.md calls this optional but suggests it becomes valuable)

2. **Specify concept generation contracts more concretely:**
   - Document expected concept pool size for multi-show (e.g., 12–16 concepts before selection, vs 8 for single-show)
   - Define "shared" precisely: Do all N input shows require the concept, or K of N? Or must concept be common *thematic thread* rather than explicit match?
   - Specify fallback: If fewer than 8 concepts are shared, pad with per-show top concepts or reject multi-show and ask user to refine inputs?

3. **Add AI response validation to test harness:**
   - Post-process AI outputs before returning to client (validate JSON structure ✓ already done; validate semantics ✗ not done)
   - Example: Check concepts are 1–3 words and non-generic (regex + hardcoded deny-list of generic words)
   - Example: Verify recommendation reasons name at least one selected concept (string search in `reason` field)

4. **Establish prompt evolution governance:**
   - When switching models or updating prompts, run golden test set against new version
   - Flag any quality score drop (regression)
   - Document rationale for prompt changes in commit history

None of these require schema changes or architecture rework. All are planning + process work that can happen in parallel with Phase 2 implementation or as post-Phase-2 polish.

---

**Total: 99 requirements (30 critical, 67 important, 2 detail) across 10 functional areas**

| Severity | Full | Partial | Missing | Total | Score |
|----------|------|---------|---------|-------|-------|
| Critical | 30 | 0 | 0 | 30 | 100% |
| Important | 63 | 4 | 0 | 67 | 97.01% |
| Detail | 2 | 0 | 0 | 2 | 100% |
| **Overall** | **95** | **4** | **0** | **99** | **96.46%** |