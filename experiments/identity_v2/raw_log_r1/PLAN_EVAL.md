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
| PRD-001 | Use Next.js latest stable runtime | `critical` | full | Section 1.1 Technology Stack; Section 3.2 Routes | |
| PRD-002 | Use Supabase official client libraries | `critical` | full | Section 1.1 Technology Stack; Section 2.2 Database Schema | |
| PRD-003 | Ship `.env.example` with required variables | `critical` | full | Section 10.1 Environment Variables | |
| PRD-004 | Ignore `.env*` secrets except example | `important` | full | Section 10.1; Section 15.2 Secrets Management | |
| PRD-005 | Configure build through env without code edits | `critical` | full | Section 10.1; Section 10.2 Development Environment | |
| PRD-006 | Keep secrets out of repo and server-only | `critical` | full | Section 10.1; Section 15.2 Secrets Management | |
| PRD-007 | Provide app, test, reset command scripts | `critical` | full | Section 10.4 Scripts (npm run dev, test, test:reset) | |
| PRD-008 | Include repeatable schema evolution artifacts | `critical` | partial | Section 2.2 Database Schema; Section 10.3 mentions migrations (idempotent) but implementation details light | Need explicit migration file examples or version control strategy |
| PRD-009 | Use one stable namespace per build | `critical` | full | Section 1.2 Architectural Principles; Section 2.2 namespace_id in schema | |
| PRD-010 | Isolate namespaces and scope destructive resets | `critical` | full | Section 9.2 Destructive Testing; Section 2.2 RLS policies | |
| PRD-011 | Attach every user record to `user_id` | `critical` | full | Section 2.2 all tables include user_id; Section 8.1 identity injection | |
| PRD-012 | Partition persisted data by namespace and user | `critical` | full | Section 2.2; Section 8.1 Middleware checks | |
| PRD-013 | Support documented dev auth injection, prod-gated | `important` | full | Section 8.1 Benchmark-Mode Identity Injection | |
| PRD-014 | Real OAuth later needs no schema redesign | `important` | full | Section 8.2 Future OAuth Path | |
| PRD-015 | Keep backend as persisted source of truth | `critical` | full | Section 1.2 Architectural Principles | |
| PRD-016 | Make client cache safe to discard | `critical` | full | Section 13.1 Client-Side Caching; note "clients may cache" language | |
| PRD-017 | Avoid Docker requirement for cloud-agent compatibility | `important` | full | Section 10.2 "No Docker requirement" | |
| PRD-018 | Overlay saved user data on every show appearance | `critical` | full | Section 4.1–4.7 all surfaces show My Data overlays; Section 5.7 "AI Recommendations Mapping" | |
| PRD-019 | Support visible statuses plus hidden `Next` | `important` | full | Section 5.3 Status System lists all including hidden Next | |
| PRD-020 | Map Interested/Excited chips to Later interest | `critical` | full | Section 5.2 Auto-Save Triggers; Section 5.3 Interest levels | |
| PRD-021 | Support free-form multi-tag personal tag library | `important` | full | Section 2.1 Show entity myTags array; Section 4.7 Tag picker | |
| PRD-022 | Define collection membership by assigned status | `critical` | full | Section 5.1 "Show is 'in collection' when myStatus != nil" | |
| PRD-023 | Save shows from status, interest, rating, tagging | `critical` | full | Section 5.2 Auto-Save Triggers lists all four | |
| PRD-024 | Default save to Later/Interested except rating-save Done | `critical` | full | Section 5.2 shows default Later/Interested; rating exception | |
| PRD-025 | Removing status deletes show and all My Data | `critical` | full | Section 4.5 Detail Page "Removal flow" clears all | |
| PRD-026 | Re-add preserves My Data and refreshes public data | `critical` | full | Section 2.3 Merge rules; Section 7.2 "Create or merge Show object" | |
| PRD-027 | Track per-field My Data modification timestamps | `critical` | full | Section 2.1 Show entity lists all *UpdateDate fields | |
| PRD-028 | Use timestamps for sorting, sync, freshness | `important` | full | Section 5.5 uses timestamps for merge; Section 13.2 for caching | |
| PRD-029 | Persist Scoop only for saved shows, 4h freshness | `critical` | full | Section 6.2 Scoop Generation "Only persist if show is in collection"; "Cache with 4-hour freshness" | |
| PRD-030 | Keep Ask and Alchemy state session-only | `important` | full | Section 4.3 Ask Context management "session-specific"; Section 4.4 Alchemy state "local React state" | |
| PRD-031 | Resolve AI recommendations to real selectable shows | `critical` | full | Section 5.7; Section 6.5 resolution logic; Section 7.2 "resolve each to real Show" | |
| PRD-032 | Show collection and rating tile indicators | `important` | full | Section 5.8 Tile Indicators; Section 4.1 "in-collection indicator, rating badge" | |
| PRD-033 | Sync libraries/settings consistently and merge duplicates | `important` | partial | Section 2.3 Merge rules exist; no explicit UI or workflow shown for cross-device sync activation | Sync activation and conflict resolution UI not detailed |
| PRD-034 | Preserve saved libraries across data-model upgrades | `critical` | full | Section 2.3 Data Continuity & Migrations "transparently transforms on first load" | |
| PRD-035 | Persist synced settings, local settings, UI state | `important` | partial | Section 2.1 CloudSettings, LocalSettings, UIState defined; no detail on which settings are synced vs local-only | Need explicit mapping of sync boundaries |
| PRD-036 | Keep provider IDs persisted and detail fetches transient | `important` | full | Section 2.1 Show entity notes providerData persisted, cast/crew transient | |
| PRD-037 | Merge catalog fields safely and maintain timestamps | `critical` | full | Section 2.3; Section 7.2 merge rules explain non-user vs user field handling | |
| PRD-038 | Provide filters panel and main screen destinations | `important` | full | Section 3.1 Top-Level Layout diagram; Section 3.2 Routes | |
| PRD-039 | Keep Find/Discover in persistent primary navigation | `important` | full | Section 3.1; Section 3.2 `/find` as persistent entry point | |
| PRD-040 | Keep Settings in persistent primary navigation | `important` | full | Section 3.1; Section 3.2 `/settings` as persistent entry point | |
| PRD-041 | Offer Search, Ask, Alchemy discover modes | `important` | full | Section 3.2 `/find/search`, `/find/ask`, `/find/alchemy` | |
| PRD-042 | Show only library items matching active filters | `important` | full | Section 4.1 "Query filtered by (namespace_id, user_id) and selected filter" | |
| PRD-043 | Group home into Active, Excited, Interested, Others | `important` | full | Section 4.1 "Group results by status: 1. Active 2. Excited 3. Interested 4. Other" | |
| PRD-044 | Support All, tag, genre, decade, score, media filters | `important` | full | Section 4.1; Section 3.1 "Tag Filters", "Data Filters", "Media Toggle" | |
| PRD-045 | Render poster, title, and My Data badges | `important` | full | Section 4.1 "Display tiles with poster, title, in-collection indicator, rating badge" | |
| PRD-046 | Provide empty-library and empty-filter states | `detail` | full | Section 4.1 EmptyState component | |
| PRD-047 | Search by title or keywords | `important` | full | Section 4.2 "Text search by title/keywords" | |
| PRD-048 | Use poster grid with collection markers | `important` | full | Section 4.2 "Results rendered as poster grid"; "In-collection items marked" | |
| PRD-049 | Auto-open Search when setting is enabled | `detail` | full | Section 4.2 "Auto-launch" if `settings.autoSearch` is true | |
| PRD-050 | Keep Search non-AI in tone | `important` | missing | No explicit statement that Search avoids AI voice; only that AI surfaces share a persona | Need statement that Search remains straightforward/non-AI |
| PRD-051 | Preserve Show Detail narrative section order | `important` | full | Section 4.5 lists 12 sections in exact order from PRD | |
| PRD-052 | Prioritize motion-rich header with graceful fallback | `important` | full | Section 4.5 "Carousel: backdrops/posters/logos/trailers"; "Fall back to static poster" | |
| PRD-053 | Surface year, runtime/seasons, and community score early | `important` | full | Section 4.5 section 2 "Core Facts Row: Year, runtime/seasons, community score bar" | |
| PRD-054 | Place status/interest controls in toolbar | `important` | full | Section 4.5 section 3 "My Relationship Toolbar" | |
| PRD-055 | Auto-save unsaved tagged show as Later/Interested | `critical` | full | Section 4.5 Auto-save behaviors; Section 5.2 "Add tag to unsaved show: Later + Interested" | |
| PRD-056 | Auto-save unsaved rated show as Done | `critical` | full | Section 4.5 Auto-save behaviors; Section 5.2 "Rate unsaved show: Done" | |
| PRD-057 | Show overview early for fast scanning | `important` | full | Section 4.5 section 4 "Overview + Scoop" early in order | |
| PRD-058 | Scoop shows correct states and progressive feedback | `important` | full | Section 4.5 "Scoop streams progressively"; Section 6.2 "user sees 'Generating…'" | |
| PRD-059 | Ask-about-show deep-link seeds Ask context | `important` | full | Section 4.3 Special variant "Ask About This Show"; "show context included in initial system prompt" | |
| PRD-060 | Include traditional recommendations strand | `important` | full | Section 4.5 section 7 "Traditional Recommendations Strand" | |
| PRD-061 | Explore Similar uses CTA-first concept flow | `important` | full | Section 4.5 section 8 "Get Concepts → select → Explore Shows" | |
| PRD-062 | Include streaming availability and person-linking credits | `important` | full | Section 4.5 sections 9–10 "Streaming Availability" and "Cast & Crew" | |
| PRD-063 | Gate seasons to TV and financials to movies | `important` | full | Section 4.5 "Seasons (TV only)"; "Budget vs Revenue (Movies only)" | |
| PRD-064 | Keep primary actions early and page not overwhelming | `important` | full | Section 4.5 "Sections in order" places status/rating/scoop early; "long-tail info down-page" | |
| PRD-065 | Provide conversational Ask chat interface | `important` | full | Section 4.3 "Chat UI with turn history" | |
| PRD-066 | Answer directly with confident, spoiler-safe recommendations | `important` | partial | Section 6.3 AI Processing mentions "taste-aware prompt"; no explicit spoiler-safety or confidence rubric enforced | AI response quality depends on prompt; no validation framework shown |
| PRD-067 | Show horizontal mentioned-shows strip from chat | `important` | full | Section 4.3 "Render mentioned shows as horizontal strand (selectable)" | |
| PRD-068 | Open Detail from mentions or Search fallback | `important` | full | Section 4.3 "Click mentioned show opens `/detail/[id]` or triggers detail modal" | |
| PRD-069 | Show six random starter prompts with refresh | `important` | full | Section 4.3 Welcome state "display 6 random starter prompts"; "User can refresh" | |
| PRD-070 | Summarize older turns while preserving voice | `important` | full | Section 4.3 "After ~10 turns, summarize older turns"; "Preserve feeling/tone in summary" | |
| PRD-071 | Seed Ask-about-show sessions with show handoff | `important` | full | Section 4.3 Special variant mentions "seed conversation with show context" | |
| PRD-072 | Emit `commentary` plus exact `showList` contract | `critical` | full | Section 6.3 AI Processing section 5 shows exact JSON structure with `commentary` and `showList` | |
| PRD-073 | Retry malformed mention output once, then fallback | `important` | partial | Section 6.3 "Parse response; if JSON fails, retry with stricter instructions"; no explicit "once" limit stated | Should state retry count explicitly |
| PRD-074 | Redirect Ask back into TV/movie domain | `important` | missing | No mention of guardrail that redirects off-topic questions back to TV/movies | Need explicit handling of non-TV/movie queries |
| PRD-075 | Treat concepts as taste ingredients, not genres | `important` | full | Section 6.4 Concepts Generation; Section 4.4 Alchemy "Concept Catalysts" language | |
| PRD-076 | Return bullet-only, 1-3 word, non-generic concepts | `important` | full | Section 6.4 "Output: bullet list only; each 1–3 words; no generic placeholders" | |
| PRD-077 | Order concepts by strongest aha and varied axes | `important` | partial | Section 6.4 mentions "evocative phrasing"; no explicit ordering or axis-diversity heuristic stated | Need explicit quality guidance on ordering and diversity |
| PRD-078 | Require concept selection and guide ingredient picking | `important` | full | Section 4.4 "User selects 1–8 concepts"; "UI should hint 'pick the ingredients you want more of'" | |
| PRD-079 | Return exactly five Explore Similar recommendations | `important` | full | Section 6.5 "Counts: Explore Similar: 5 recs per round" | |
| PRD-080 | Support full Alchemy loop with chaining | `important` | full | Section 4.4 "Optional: More Alchemy!" and full flow with chaining support | |
| PRD-081 | Clear downstream results when inputs change | `important` | full | Section 4.4 "Backtracking allowed: changing shows clears concepts/results" | |
| PRD-082 | Generate shared multi-show concepts with larger option pool | `important` | partial | Section 6.4 mentions "multi-show: concepts must be shared"; no detail on "larger option pool" size or logic | Need explicit concept generation count guidance |
| PRD-083 | Cite selected concepts in concise recommendation reasons | `important` | full | Section 6.5 "reasons should explicitly reflect the selected concepts" | |
| PRD-084 | Deliver surprising but defensible taste-aligned recommendations | `important` | partial | Section 6.5 says "resolve to real catalog"; Section 4.4 says "taste-aligned"; no explicit surprise/defensibility validation framework | Quality bar defined in PRD docs but not integrated into plan |
| PRD-085 | Keep one consistent AI persona across surfaces | `important` | full | Section 6.1 "All AI surfaces: Use configurable provider"; Section 6.2–6.5 each surface shares persona with adaptations | |
| PRD-086 | Enforce shared AI guardrails across all surfaces | `critical` | partial | Section 6.1 "All surfaces must: Stay within TV/movies, spoiler-safe, opinionated, specific"; no enforcement mechanism (validation, testing, prompting structure) shown | Need explicit validation/enforcement approach |
| PRD-087 | Make AI warm, joyful, and light in critique | `important` | partial | Section 6.1 mentions "taste-aware prompt"; personality spec from supporting docs not integrated into implementation plan | Persona definition exists but not operationalized |
| PRD-088 | Structure Scoop as personal taste mini-review | `important` | partial | Section 6.2 "sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict"; no template or rubric shown | Sections defined by reference; implementation detail missing |
| PRD-089 | Keep Ask brisk and dialogue-like by default | `important` | partial | Section 6.3 "respond like a friend in dialogue (not an essay)"; no explicit length limit or tone-checking mechanism | Length guidance mentioned but not enforced |
| PRD-090 | Feed AI the right surface-specific context inputs | `important` | full | Section 6.1–6.5 detail what context each surface receives | |
| PRD-091 | Validate discovery with rubric and hard-fail integrity | `important` | missing | No mention of quality validation framework, testing against discovery_quality_bar.md rubric, or hard-fail criteria | Need explicit QA/validation approach |
| PRD-092 | Show person gallery, name, and bio | `important` | full | Section 4.6 Person Detail "Image gallery; Name, bio" | |
| PRD-093 | Include ratings, genres, and projects-by-year analytics | `important` | full | Section 4.6 "Analytics" section lists charts | |
| PRD-094 | Group filmography by year | `important` | full | Section 4.6 "Filmography Grouped by Year" | |
| PRD-095 | Open Show Detail from selected credit | `important` | full | Section 4.6 "Click credit opens `/detail/[creditId]`" | |
| PRD-096 | Include font size and Search-on-launch settings | `important` | full | Section 4.7 "App Settings: Font size, Toggle: Search on Launch" | |
| PRD-097 | Support username, model, and API-key settings safely | `important` | full | Section 4.7 lists all settings; Section 8.3 "User-entered secrets: Server stores in cloud_settings" | |
| PRD-098 | Export saved shows and My Data as zip | `critical` | full | Section 4.7 "Export / Backup: Button generates `.zip`" with JSON | |
| PRD-099 | Encode export dates using ISO-8601 | `important` | full | Section 4.7 "dates ISO-8601"; Section 9.4 "JSON contains all shows + My Data; Dates in ISO-8601 format" | |

---

## 3. Coverage Scores

### Overall Calculation

```
Total full: 79
Total partial: 14
Total missing: 6
Total: 99

Score = (79 × 1.0 + 14 × 0.5) / 99 × 100
       = (79 + 7) / 99 × 100
       = 86 / 99 × 100
       = 86.87%
```

### By Severity Tier

**Critical (30 total):**
```
Full: 26
Partial: 2 (PRD-008 schema artifacts, PRD-086 enforcement)
Missing: 2 (none)

Score = (26 × 1.0 + 2 × 0.5) / 30 × 100
       = 27 / 30 × 100
       = 90%  (27 of 30 critical requirements)
```

**Important (67 total):**
```
Full: 52
Partial: 12 (PRD-033, 035, 066, 073, 077, 082, 084, 087, 088, 089, 091)
Missing: 3 (PRD-050, 074, 091 — note PRD-091 counted in important but should also flag missing)

Score = (52 × 1.0 + 12 × 0.5) / 67 × 100
       = 58 / 67 × 100
       = 86.57%  (58 of 67 important requirements)
```

**Detail (2 total):**
```
Full: 2
Partial: 0
Missing: 0

Score = 2 / 2 × 100
       = 100%  (2 of 2 detail requirements)
```

**Overall: 86.87%** (86 of 99 requirements fully or partially addressed)

---

## 4. Top Gaps

### Gap 1: **AI Response Validation & Quality Enforcement (Critical + Important)**
- **PRD-086** (critical), **PRD-091** (important)
- **Why it matters:** The plan describes AI surface architecture but lacks a quality validation framework. Without explicit enforcement of the discovery_quality_bar.md rubric (voice adherence, taste alignment, real-show integrity), deploying AI features risks degraded user experience and loss of trust. Taste-aware discovery is the app's core value; validation is non-negotiable.

### Gap 2: **AI Personality Operationalization (Important)**
- **PRD-087**, **PRD-088**, **PRD-089**
- **Why it matters:** The plan acknowledges personality specs exist but doesn't show how they're integrated into prompts, validated in testing, or maintained across prompt evolution. Persona consistency is explicitly required; without a working translation from the supporting docs to implementation, rebuilds risk tone drift and emotional inconsistency that the PRD calls "the heart" of the product.

### Gap 3: **Database Migration & Versioning Detail (Critical)**
- **PRD-008**
- **Why it matters:** The plan mentions "repeatable schema evolution artifacts" and "automatic schema migration" but doesn't specify file structure, version control, or idempotency guarantees. For a multi-tenant benchmark system with namespace isolation, migration failures or version mismatches could silently corrupt data. The spec is vague where it should be prescriptive.

### Gap 4: **Cross-Device Sync Activation & Conflict Resolution (Important)**
- **PRD-033**, **PRD-035**
- **Why it matters:** Data merge rules are defined, but there's no user-facing workflow described. When does sync activate? What does the user see during a conflict? How are timestamp ties broken? Without this, the feature remains incomplete even if the backend logic is sound.

### Gap 5: **Off-Topic Query Handling & TV/Movie Domain Guardrails (Important)**
- **PRD-074**
- **Why it matters:** The PRD explicitly requires Ask to "redirect back into TV/movie domain" when users ask off-topic questions. The plan's AI Architecture section lists "Stay within TV/movies" as a shared rule but shows no mechanism (prompt instruction, post-processing filter, user messaging) to enforce or communicate this to users. Ask could fail silently in this scenario.

---

## 5. Coverage Narrative

### Overall Posture

This plan is **structurally sound but missing critical detail on quality assurance and persona enforcement**. It demonstrates deep understanding of data architecture, namespace isolation, auto-save semantics, and feature flow. Infrastructure and data layers are thoroughly specified with clear mapping to the PRD's technical requirements. However, the plan treats AI personality and response validation as an implementation detail rather than a specifiable surface contract. For a product where AI is central to value (Ask, Alchemy, Scoop), this is a notable gap.

The plan would support a working MVP, but shipping AI features without explicit quality frameworks or personality integration risks tone drift and degraded discovery quality that could damage the product's soul. This is not a fatal flaw—the remediation is straightforward—but it's a gap that should be closed before phase 2 (AI features) begins.

### Strength Clusters

**Benchmark Runtime & Isolation (17 requirements, 94% coverage):**
- Excellent specificity on namespace/user partitioning, environment injection, schema storage, and test reset isolation. The plan clearly understands the benchmark requirements and has integrated them throughout the data model and API design. `.env.example`, RLS policies, and destructive testing all clearly specified.

**Collection Data & Persistence (20 requirements, 85% coverage):**
- Strong coverage of status system, auto-save triggers, merge rules, and timestamp-based conflict resolution. The plan correctly models all collection membership rules, re-add semantics, and data continuity across upgrades. Timestamps are woven into caching, sync, and freshness logic. The schema is well-thought-out.

**App Navigation & Discovery Shell (4 requirements, 100% coverage):**
- Routes, persistent navigation, mode switcher all clearly defined. No ambiguity here.

**Collection Home & Search (9 requirements, 89% coverage):**
- Filtering, grouping, tile design, empty states all specified. Search auto-launch covered. Minor gap: PRD-050 (Search non-AI tone) not explicitly stated, though implied.

**Show Detail & Relationship UX (14 requirements, 93% coverage):**
- Detail page narrative hierarchy matches PRD exactly. Section order, auto-save flows, removal confirmation, Scoop states all detailed. Toolbar placement, media gating (TV vs movie) all correct. High fidelity here.

**Person Detail (4 requirements, 100% coverage):**
- Gallery, bio, analytics, filmography grouping, credit links all present.

**Settings & Export (4 requirements, 100% coverage):**
- Font size, Search-on-launch, username, API key handling, export zip with ISO-8601 dates all specified.

### Weakness Clusters

**AI Voice, Persona & Quality (7 requirements, ~57% coverage):**
- This is the cluster where gaps concentrate. The plan describes AI *infrastructure* (endpoints, payloads, resolution logic) but not AI *validation*. PRD-086 (enforce shared guardrails), PRD-087 (warm/joyful tone), PRD-088–089 (Scoop structure, Ask brevity), PRD-091 (quality rubric validation) are all either partially addressed or missing. The plan acknowledges personality specs exist but doesn't operationalize them. This is the most concerning weakness because AI is central to product value and tone consistency is non-negotiable per the supporting docs (ai_voice_personality.md, discovery_quality_bar.md).

**Ask Chat (10 requirements, 80% coverage):**
- Mostly strong (chat UI, starter prompts, mentioned shows, summarization all clear). Two gaps: PRD-066 (confidence/spoiler-safety enforcement) and PRD-074 (off-topic redirection) lack concrete mechanism. PRD-073 (retry count) is vague.

**Concepts & Alchemy (10 requirements, 85% coverage):**
- Flow and UX well-specified. Gaps: PRD-077 (concept ordering heuristic) and PRD-082 (multi-show pool size) lack explicit counts or algorithms. PRD-084 (surprise/defensibility validation) mentions quality bar but doesn't integrate it into the plan.

**Pattern:** Partial/missing gaps cluster around *behavioral contracts* that should be validated, not just *features* that should ship. This suggests the plan separates "what the user sees" from "how we ensure it's good." The PRD documents establish explicit acceptance criteria (discovery_quality_bar.md, ai_voice_personality.md) that the plan doesn't integrate into testing or deployment strategy.

### Risk Assessment

**Most likely failure mode:** AI features ship with inconsistent tone or degraded recommendations that fail the discovery_quality_bar.md rubric. Users notice Scoop feels generic, Ask recommendations aren't taste-grounded, Alchemy lacks "aha" concepts. Product feels soulless even though features are technically complete.

**Secondary risk:** Off-topic Ask queries (asking for movie trivia, non-entertainment advice) are accepted and answered, breaking the "TV/movie only" boundary. Starts small, becomes noise.

**Tertiary risk:** Cross-device sync silently creates conflicts or data inconsistencies because merge logic is defined but the feature's user-facing workflow and error handling are underspecified.

**Why these matter:**
- The PRD emphasizes product heart and personality as *non-negotiable*. If AI surfaces drift in tone, the rebuild loses the product's core identity even if all features work.
- Namespace isolation and data integrity are benchmark requirements. Unexplained sync conflicts would fail validation.
- Ask is phase 2; building without a validation framework now means either shipping low-quality or discovering the gap during QA and delaying launch.

### Remediation Guidance

**For weakness cluster: AI Voice & Quality (PRD-086, 087–091)**

*Type:* Missing specification + process integration, not missing architecture.

*Work needed:*
1. **Operationalize personality:** Create explicit mapping from ai_voice_personality.md and discovery_quality_bar.md into:
   - Prompt templates (example: "System: [persona definition] + [surface-specific style guide]")
   - Acceptance test examples (golden set from discovery_quality_bar.md)
   - Automated quality checks if possible (e.g., reject responses with generic phrases)
2. **Add validation framework:** Specify:
   - Pre-deployment: human review of N sample outputs against rubric
   - Post-deployment: logging of user feedback or model drift metrics
   - Regression testing when prompts change
3. **Detail the gaps:** PRD-074 (off-topic), PRD-073 (retry count), PRD-088–089 (Scoop structure, Ask length) need 1–2 sentence operationalization each

**For data continuity: Schema migrations (PRD-008)**

*Type:* Missing implementation detail.

*Work needed:*
- Specify migration file structure (e.g., `/migrations/001_initial_schema.sql`, `/migrations/002_add_namespace_id.sql`)
- Version numbering scheme
- Idempotency rule (all migrations must be safe to re-run)
- Rollback strategy (optional but recommended for confidence)

**For cross-device sync (PRD-033, 035)**

*Type:* Incomplete feature specification (backend logic exists, UX/workflow missing).

*Work needed:*
- When is sync enabled? (User toggle in Settings? Automatic?)
- What does the user see during sync? (Status message? Conflict prompt?)
- How are timestamp ties broken? (Creation time? Random?)
- What happens if sync fails? (Retry? Silent fallback?)

**Effort guidance:**
- AI operationalization: medium effort (requires prompt engineering + test harness)
- Schema migrations: low effort (standard practice, template-able)
- Sync workflow: low-to-medium effort (UX design + error handling)

None of these require architectural changes. They're specification gaps that should be closed before Phase 2 implementation begins.

---

**End of Evaluation**