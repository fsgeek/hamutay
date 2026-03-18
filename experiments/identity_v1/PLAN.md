# Implementation Plan

## Executive Summary

This document outlines a comprehensive implementation plan for a personal TV/movie companion app that enables users to build collections, organize with statuses/tags/ratings, and discover new entertainment through AI-powered features (Ask, Alchemy, Explore Similar) and traditional search.

The app must run on **Next.js + Supabase** per the benchmark baseline, with namespace isolation for multi-build safety and explicit user identity tracking. The implementation preserves user data across updates, maintains a consistent AI voice across all surfaces, and grounds all recommendations in real catalog items.

---

## 1. Architecture Overview

### 1.1 Technology Stack

**Frontend/Runtime:**
- **Next.js** (latest stable) — app runtime, server-side logic, API routes
- **React** — UI components
- **TypeScript** — type safety throughout

**Persistence:**
- **Supabase** — PostgreSQL database + auth (or dev-mode identity injection)
- **Client libraries** — @supabase/supabase-js (anon/public key for browser)

**AI Integration:**
- **Configurable provider** (OpenAI/Anthropic/etc. via environment variables)
- **API key stored server-side only** (environment or Supabase secure config)

**External Catalog:**
- **Configurable provider** (TMDB or equivalent via environment variables)
- **API key stored server-side only**

### 1.2 Key Architectural Principles

1. **Backend is source of truth** — clients cache for performance, but correctness depends on server state.
2. **Namespace isolation** — all data partitioned by `(namespace_id, user_id)` to prevent cross-build pollution.
3. **Implicit auto-save** — user actions (setting status, rating, tagging) trigger immediate save without explicit "Save" button.
4. **Conflict resolution by timestamp** — when the same field is edited on two devices, newer timestamp wins.
5. **Consistent AI voice** — all AI surfaces (Scoop, Ask, Alchemy, Explore Similar) share one persona with surface-specific adaptations.
6. **Real-show integrity** — every recommendation must resolve to a catalog item via external ID or deterministic title matching.

---

## 2. Data Model & Storage

### 2.1 Core Entities

#### Show
- **Catalog metadata** (title, year, genres, overview, posters, ratings, runtime/seasons, etc.)
- **User overlay ("My Data")**
  - `myStatus` (active/later/done/quit/wait/next + timestamps)
  - `myInterest` (excited/interested, applies only when status=later)
  - `myTags` (free-form user labels + timestamp)
  - `myScore` (user rating 0–10 or unrated + timestamp)
  - `aiScoop` (AI-generated personality description + timestamp + freshness)
- **External identifiers** (for catalog resolution)
- **Management fields** (creationDate, detailsUpdateDate, isTest flag)

#### CloudSettings (optional cross-device sync)
- `userName`, `aiApiKey`, `aiModel`, `catalogApiKey`
- `version` (epoch seconds for conflict resolution)

#### AppMetadata
- `dataModelVersion` (for migrations)

#### LocalSettings
- `autoSearch`, `fontSize`

#### UIState
- `hideStatusRemovalConfirmation`, `lastSelectedFilter`

### 2.2 Database Schema (Supabase)

**Primary tables:**
- `shows` (id, title, showType, externalIds, genres, overview, posterUrlString, backdropUrlString, logoUrlString, voteAverage, popularity, releaseDate, firstAirDate, lastAirDate, runtime, numberOfSeasons, numberOfEpisodes, episodeRunTime, seriesStatus, myStatus, myStatusUpdateDate, myInterest, myInterestUpdateDate, myTags, myTagsUpdateDate, myScore, myScoreUpdateDate, aiScoop, aiScoopUpdateDate, detailsUpdateDate, creationDate, isTest, namespace_id, user_id, created_at, updated_at)
- `cloud_settings` (id, user_id, namespace_id, userName, version, catalogApiKey, aiApiKey, aiModel, created_at, updated_at)
- `app_metadata` (namespace_id, dataModelVersion, created_at, updated_at)

**Indexes:**
- `shows (namespace_id, user_id)` — partition queries
- `shows (namespace_id, user_id, myStatus)` — filter by status
- `shows (namespace_id, user_id, myTags)` — filter by tag
- `shows (id, namespace_id, user_id)` — lookup by ID
- `cloud_settings (user_id, namespace_id)` — settings lookup

**RLS (Row-Level Security):**
- All tables scoped to `(namespace_id, user_id)` via RLS policies
- Client uses anon key; user_id injected via development header or auth session
- Server-side API routes use service-role key for admin operations (migrations, test resets)

### 2.3 Data Continuity & Migrations

**Upgrade behavior:**
- New app version reads old schema and transparently transforms on first load
- No user data loss; all shows, tags, ratings, statuses brought forward
- Automatic schema migration on app boot if `dataModelVersion` mismatch detected

**Merge rules (cross-device sync):**
- Non-user fields: prefer non-empty newer value
- User fields: resolve by `*UpdateDate` timestamp (newer wins)
- Duplicate shows detected by `id` and merged transparently

---

## 3. Application Structure & Navigation

### 3.1 Top-Level Layout

```
┌─────────────────────────────────────┐
│  Filters Panel  │  Main Content     │
├─────────────────────────────────────┤
│ • All Shows     │  [Home/Detail/    │
│ • Tag Filters   │   Find/Person/    │
│ • Data Filters  │   Settings]       │
│ • Media Toggle  │                   │
└─────────────────────────────────────┘
```

**Persistent navigation:**
- Filters panel on left (collapsible on mobile)
- Find/Discover entry point
- Settings entry point
- Home displays collection filtered by sidebar selection

### 3.2 Routes & Pages

**Main routes:**
- `/` — Home (collection browser)
- `/detail/[id]` — Show Detail page
- `/find` — Find/Discover hub (Search/Ask/Alchemy mode switcher)
- `/find/search` — Search results (external catalog)
- `/find/ask` — Conversational AI discovery
- `/find/alchemy` — Concept-blending discovery
- `/person/[id]` — Person Detail page
- `/settings` — Settings & Your Data

**API routes (server-side):**
- `/api/shows` — list/search shows (filtered by namespace/user)
- `/api/shows/[id]` — get/update/delete show
- `/api/shows/[id]/scoop` — generate/get AI Scoop
- `/api/shows/[id]/concepts` — generate concepts
- `/api/recommendations/similar` — concept-based recommendations
- `/api/recommendations/alchemy` — alchemy recommendations
- `/api/chat` — Ask conversational endpoint
- `/api/catalog/search` — external catalog search
- `/api/catalog/show/[id]` — fetch external show details
- `/api/person/[id]` — fetch person details
- `/api/export` — export user data as JSON zip
- `/api/auth/identity` — dev-mode user identity injection (test-only)
- `/api/test/reset` — clear all data for namespace (test-only)

### 3.3 Navigation Patterns

**Home → Detail:**
- Click any show tile in collection

**Home → Find:**
- Click "Find/Discover" top nav

**Find → Search/Ask/Alchemy:**
- Mode switcher at top of Find hub

**Detail → Ask About Show:**
- "Ask about this show" button seeds Ask with show context

**Detail → Explore Similar:**
- Get Concepts → select → Explore Shows

**Detail → Cast/Crew → Person:**
- Click any person tile → Person Detail

**Person → Detail:**
- Click any credit in filmography

**Settings → Export:**
- "Export My Data" generates `.zip` with JSON

---

## 4. Core Features

### 4.1 Collection Home

**Purpose:** Display library organized by status.

**Implementation:**
- Query `shows` table filtered by `(namespace_id, user_id)` and selected filter
- Group results by status:
  1. Active (largest tiles)
  2. Excited (Later + Excited Interest)
  3. Interested (Later + Interested)
  4. Other (collapsed): Wait, Quit, Done, unclassified Later
- Apply media-type toggle (All/Movies/TV) on top of status grouping
- Display tiles with poster, title, in-collection indicator, rating badge

**Components:**
- `CollectionHome` — main container
- `StatusSection` — renders one status group
- `ShowTile` — poster + title + badges
- `FilterSidebar` — tag/data/type filters
- `EmptyState` — when no shows match filter

**State management:**
- React Context or Zustand for current filter selection
- Client-side caching of collection list (invalidate on mutation)

### 4.2 Search

**Purpose:** Find shows in external catalog.

**Implementation:**
- Text input sends query to `/api/catalog/search`
- Server forwards to external catalog provider (TMDB or equivalent)
- Results rendered as poster grid
- In-collection items marked with indicator
- Click result opens `/detail/[id]` (or fetches details, creates Show if needed)

**Components:**
- `SearchPage` — main container
- `SearchInput` — text field + clear button
- `SearchResults` — grid of show tiles
- `SearchEmpty` — "no results" or "try searching"

**Auto-launch:**
- If `settings.autoSearch` is true, `/find/search` opens on app startup
- Implement as route middleware or explicit navigation on mount

### 4.3 Ask (Conversational Discovery)

**Purpose:** Natural-language discovery grounded in user taste.

**Implementation:**
- Chat UI with turn history
- User messages sent to `/api/chat` with:
  - `userMessage: string`
  - `namespace_id`, `user_id` (from auth)
  - `userLibrary?: Show[]` (user's saved shows, optional)
  - `conversationContext: Turn[]` (recent turns, older ones summarized)
  - `mentionedShowsFromPreviousTurns?: string[]` (to avoid duplicates)
- Server calls AI with taste-aware prompt:
  - Include user's saved shows + My Data for context
  - Base system prompt defines persona (from ai_personality_opus.md)
  - Summarize older turns after ~10 messages to control token depth
- AI response includes:
  - `commentary: string` (user-facing text)
  - `showList?: string` (structured "Title::externalId::mediaType;;…" format)
- Parse `showList`, resolve each to real Show via external catalog lookup
- Render mentioned shows as horizontal strand (selectable)
- Click mentioned show opens `/detail/[id]` or triggers detail modal

**Special variant: Ask About This Show**
- Button on Detail page opens Ask with pre-seeded context
- Show context (title, overview, status) included in initial system prompt
- Conversation flows naturally from there

**Components:**
- `AskPage` — main container
- `ChatHistory` — turn list
- `ChatInput` — message input + send button
- `BotTurn` — renders bot message + mentioned shows strand
- `UserTurn` — renders user message
- `StarterPrompts` — 6 random prompts on first load (refresh available)
- `MentionedShowsStrand` — horizontal scroll of resolved shows

**Welcome state:**
- On initial Ask launch, display 6 random starter prompts (from ai_personality_opus.md)
- User can refresh to get 6 more
- Tapping a prompt auto-fills chat input

**Context management:**
- Maintain session turns in-memory (React state or URL params)
- After ~10 turns, summarize older turns into 1–2 sentence recap (AI-generated)
- Preserve feeling/tone in summary (not generic "system summary" voice)
- Clear history when user leaves Ask or resets conversation

### 4.4 Alchemy (Concept Blending Discovery)

**Purpose:** Structured discovery via multi-show concept blending.

**Flow:**
1. **Select Starting Shows**
   - User picks 2+ shows from library + global catalog
   - UI allows toggling between "My Library" and "Search Catalog"
   - Selected shows displayed as chip list with remove buttons

2. **Conceptualize Shows**
   - API call to `/api/shows/concepts?showIds=[...]` with 2+ show IDs
   - Server calls AI with multi-show concept prompt
   - Returns 8–12 concepts (evocative, 1–3 words each)
   - UI renders as selectable chips

3. **Select Concept Catalysts**
   - User selects 1–8 concepts
   - Max 8 enforced by UI
   - Backtracking allowed: changing shows clears concepts/results

4. **ALCHEMIZE!**
   - API call to `/api/recommendations/alchemy` with:
     - `selectedShowIds: string[]`
     - `selectedConcepts: string[]`
   - Server calls AI with concept-based recommendation prompt
   - Returns 6 recommendations with reasons tied to concepts
   - Parse recommendations to real show objects via external ID

5. **Optional: More Alchemy!**
   - User can select recs as new inputs
   - Step back to Conceptualize Shows
   - Chain multiple rounds in single session

**Components:**
- `AlchemyPage` — main container
- `AlchemySelectShows` — show picker (library + search)
- `AlchemyShowChips` — selected shows display
- `AlchemyConceptualize` — calls concept API + renders chips
- `AlchemyRecommendations` — grid of recs with reasons
- `AlchemyChainButton` — "More Alchemy!" to loop back

**State:**
- Local React state for selected shows, concepts, results
- Reset when user changes shows or navigates away

### 4.5 Show Detail Page

**Purpose:** Single source of truth for a show + personal relationship + discovery launchpad.

**Sections (in order):**
1. **Header Media**
   - Carousel: backdrops/posters/logos/trailers
   - Fall back to static poster if no trailers
   
2. **Core Facts Row**
   - Year, runtime (movie) or seasons/episodes (TV)
   - Community score bar
   
3. **My Relationship Toolbar**
   - Status chips: Active/Interested/Excited/Done/Quit/Wait
   - Reselecting status triggers removal confirmation
   - My Rating slider (0–10, unrated state available)
   - My Tags display + tag picker (modal/dropdown)

4. **Overview + Scoop**
   - Overview text (factual)
   - "Give me the scoop!" toggle → "The Scoop" section
   - Scoop streams progressively if supported
   - Cached 4 hours; regenerate available on demand
   - Only persists if show is in collection

5. **Ask About This Show**
   - Button opens Ask with show context

6. **Genres + Languages**
   - Genre list
   - Spoken/original language codes

7. **Traditional Recommendations Strand**
   - Similar/recommended shows from catalog metadata
   - Horizontal scroll

8. **Explore Similar**
   - "Get Concepts" button
   - Concept chip selector (1+ required)
   - "Explore Shows" button → 5 recommendations

9. **Streaming Availability**
   - Providers by region (if available)

10. **Cast & Crew**
    - Horizontal strands of people
    - Click opens `/person/[id]`

11. **Seasons (TV only)**
    - Season selector (expandable)
    - Episode list per season (lazy load)

12. **Budget vs Revenue (Movies only)**
    - Bar chart or text display

**Implementation:**
- Fetch show by ID from `/api/shows/[id]`
- If not in collection, fetch external details via `/api/catalog/show/[id]`
- Lazy-load dependent data (cast, seasons, recommendations) on mount
- Cache Scoop via API endpoint with freshness check (4 hours)

**Components:**
- `DetailPage` — main container
- `DetailHeader` — media carousel + facts row
- `DetailMyData` — status/interest/rating/tags controls
- `DetailScoop` — AI Scoop display + toggle
- `DetailAskButton` — navigate to Ask with context
- `DetailRecommendations` — traditional recs strand
- `DetailExploreSimilar` — concepts → recs flow
- `DetailCastCrew` — people horizontal strands
- `DetailSeasons` — TV-specific season/episode list
- `DetailProviders` — streaming availability
- `DetailBudgetRevenue` — movie financials

**Auto-save behaviors:**
- Setting status: immediately save via API
- Setting rating on unsaved show: auto-save as Done
- Adding tag on unsaved show: auto-save as Later + Interested
- All operations show optimistic UI updates + error recovery

**Removal flow:**
- Reselect active status → confirmation modal
- "Remove from collection" clears all My Data
- Optional: "Don't ask again" checkbox (tracked in UIState)

### 4.6 Person Detail Page

**Purpose:** Talent profiles with filmography.

**Sections:**
1. **Profile Header**
   - Image gallery (primary image + thumbs)
   - Name, bio

2. **Analytics (optional lightweight charts)**
   - Average rating of projects
   - Top genres by count
   - Projects by year (bar chart)

3. **Filmography Grouped by Year**
   - Years collapsed/expandable
   - Click credit opens `/detail/[creditId]`
   - Show type indicated (movie/tv)

**Implementation:**
- Fetch person details from `/api/person/[id]`
- Server forwards to catalog provider (credits, images, bio)
- Lazy-load filmography on mount
- Cache person data standard TTL

**Components:**
- `PersonPage` — main container
- `PersonHeader` — image gallery + bio
- `PersonAnalytics` — optional charts
- `PersonFilmography` — year-grouped credits with click handler

### 4.7 Settings & Your Data

**App Settings:**
- Font size selector (XS–XXL)
- Toggle: "Search on Launch"

**User:**
- Display username (editable)

**AI:**
- AI provider selection (dropdown: OpenAI, Anthropic, etc.)
- AI model selection (dropdown: gpt-4, claude-3-opus, etc.)
- API key input (stored server-side; display masked)

**Integrations:**
- Catalog provider selection
- API key input (stored server-side; display masked)

**Your Data:**
- **Export / Backup:** Button generates `.zip` containing:
  - `backup.json` with all shows + My Data (dates ISO-8601)
  - Metadata (export date, data model version)
- **Import / Restore:** (noted as open question; not implemented yet)

**Implementation:**
- Settings stored in `cloud_settings` table + local browser settings
- Font size stored locally (applies immediately)
- Export endpoint `/api/export` queries all user's shows, zips as attachment
- API key updates go to secure server endpoint; never transmitted to client

**Components:**
- `SettingsPage` — main container
- `AppSettingsSection` — font size, search on launch
- `UserSection` — username
- `AISection` — model/key inputs
- `IntegrationsSection` — catalog provider
- `YourDataSection` — export button + import placeholder

---

## 5. Data Behaviors & Business Rules

### 5.1 Collection Membership
- A show is "in collection" when `myStatus != nil`
- All My Data fields cleared when status removed

### 5.2 Auto-Save Triggers

| Action | Default Status | Default Interest | Notes |
|--------|---|---|---|
| Set status to Active/Done/Quit/Wait | That status | — | Not applicable |
| Select Interested/Excited | Later | Interested/Excited | Both map to Later status |
| Rate unsaved show | Done | — | Rating implies watched |
| Add tag to unsaved show | Later | Interested | Convenience default |

### 5.3 Status System

- **Active** — currently watching
- **Later** — saved for later; paired with Interest
- **Wait** — paused/waiting
- **Done** — completed
- **Quit** — abandoned
- **Next** — hidden "up next" (data model only, not first-class UI yet)

Interest levels (only for Later status):
- **Excited** — high priority
- **Interested** — normal priority

### 5.4 Removal Confirmation
- Reselecting status → modal confirmation
- Copy: "Remove [Show Title] from your collection? This will clear all your notes, rating, and tags."
- Buttons: "Cancel" / "Remove"
- Optional checkbox: "Don't ask again" (persisted in UIState)

### 5.5 Timestamps & Merge Resolution

Every user field tracks update timestamp:
- `myStatusUpdateDate`, `myInterestUpdateDate`, `myTagsUpdateDate`, `myScoreUpdateDate`, `aiScoopUpdateDate`

Merge rule (cross-device sync):
- For each field, keep the value with the newer timestamp
- If no timestamp, use `updated_at` from database row
- This ensures user edits always win

### 5.6 AI Data Persistence

| Data | Persisted? | Freshness | Trigger |
|---|---|---|---|
| AI Scoop | Yes (if in collection) | 4 hours | On demand from Detail |
| Ask chat history | No | Session only | Cleared on reset/navigate away |
| Alchemy concepts/results | No | Session only | Cleared on navigate away |
| Mentioned shows strip | No | Session only | Derived from chat |

### 5.7 AI Recommendations Mapping
- AI outputs title + external ID (optional) + media type
- Server looks up external catalog by external ID (if provided)
- Falls back to title match (case-insensitive, first non-ambiguous match)
- If found, rec becomes selectable Show; if not, shown non-interactive or handed to Search

### 5.8 Tile Indicators
- In-collection indicator: visible when `myStatus != nil`
- Rating badge: visible when `myScore != nil`

---

## 6. AI Integration

### 6.1 Shared Architecture

**All AI surfaces:**
- Use configurable provider (OpenAI, Anthropic, etc. via environment variable)
- API key stored server-side (environment variable or secure Supabase config)
- Client never sees API key
- Prompts defined in reference docs (ai_personality_opus.md, ai_prompting_context.md)

**User context:**
- User's library (saved shows) + My Data (status/tags/rating)
- Recent conversation context (for Ask)
- Selected concepts (for Alchemy/Explore Similar)
- Current show details (for Scoop/Ask About Show)

### 6.2 Scoop Generation

**Endpoint:** `POST /api/shows/[id]/scoop`

**Input:**
- Show ID
- (Optional) User's library for taste context

**AI Prompt:**
- System: persona definition (warm, opinionated friend)
- Task: generate spoiler-safe "mini blog post of taste"
- Sections: personal take, honest stack-up, Scoop paragraph, fit/warnings, verdict
- Output length: ~150–350 words

**Response:**
- Structured output (sections or single markdown text)
- Cache with 4-hour freshness
- Only persist if show is in collection

**Implementation:**
- Call AI provider with system + user prompt
- Parse response (markdown or structured JSON)
- Cache in database with `aiScoopUpdateDate` = now
- On subsequent Detail loads within 4 hours, return cached version
- Allow manual "regenerate" button to override freshness

### 6.3 Ask (Conversational)

**Endpoint:** `POST /api/chat`

**Input:**
- `userMessage: string`
- `namespace_id`, `user_id` (from auth)
- `conversationHistory: Turn[]` (recent turns, older summarized)
- `userLibrary?: Show[]` (saved shows for context)

**AI Processing:**
1. System prompt: persona definition (gossipy friend, opinionated, spoiler-safe)
2. Include user's library summary (tags, statuses, ratings) if available
3. Conversation context (with summarization after ~10 turns)
4. User message
5. Request structured output:
   ```json
   {
     "commentary": "...",
     "showList": "Title::externalId::mediaType;;Title2::externalId::mediaType;;..."
   }
   ```

**Response Processing:**
1. Parse JSON
2. Extract `commentary` for display
3. Parse `showList` into mentions
4. Resolve each mention to external catalog by external ID + title match
5. Return user-facing turn with resolvable show objects

**Components:**
- Parse response; if JSON fails, retry with stricter instructions
- Fallback: show non-interactive mentions or hand to Search

**Streaming (optional):**
- If provider supports streaming, stream `commentary` progressively for UX
- Accumulate until `showList` JSON is complete

### 6.4 Concepts Generation

**Endpoints:**
- `POST /api/shows/concepts` (single show)
- `POST /api/shows/concepts/multi` (multi-show)

**Input:**
- Single show ID or array of show IDs
- User's library (for taste context, optional)

**AI Prompt:**
- System: persona (taste-aware, opinionated)
- Task: extract concept "ingredients" (1–3 words each, evocative, no plot)
- Multi-show: concepts must be shared across all inputs
- Output: bullet list only

**Response:**
- Array of 8–12 concepts (or smaller for single show)
- Each 1–3 words, spoiler-free
- No generic placeholders

**Implementation:**
- Call AI with appropriate prompt
- Parse bullet list into string array
- Return to UI for chip selection
- Do not cache (concepts are session-specific)

### 6.5 Concept-Based Recommendations

**Endpoints:**
- `POST /api/recommendations/similar` (Explore Similar)
- `POST /api/recommendations/alchemy` (Alchemy)

**Input:**
- `selectedShowIds: string[]` (1+ for Explore Similar, 2+ for Alchemy)
- `selectedConcepts: string[]` (user's selected concept filters)
- `userLibrary?: Show[]` (for taste context)

**AI Prompt:**
- System: persona (thrilled friend sharing gold)
- Task: recommend real shows tied to selected concepts
- Must name which concepts align in reasoning
- Output: structured list with show info + reason

**Output format:**
- Array of recommendations:
  ```json
  {
    "title": "Show Name",
    "externalId": "123",
    "mediaType": "tv|movie",
    "reason": "Shares [concept] vibes with [input shows]..."
  }
  ```

**Counts:**
- Explore Similar: 5 recs per round
- Alchemy: 6 recs per round

**Resolution:**
- For each rec, resolve to real catalog item via external ID + title match
- Include only recs that resolve successfully
- If fewer than target count, supplement with traditional catalog recommendations or note partial results

### 6.6 Prompt Management

**Storage:**
- Prompts defined in config files (not hardcoded)
- One config per surface (scoop.prompt, ask.prompt, concepts.prompt, recs.prompt)
- System message + user message templates with placeholders

**Evolution:**
- Versioning tracked via commit (not in-app versioning)
- Prompt changes can be A/B tested by deploying to canary namespace
- No UI for prompt editing (prompts are product, not user-configurable)

**Documentation:**
- Reference docs (ai_personality_opus.md, ai_prompting_context.md) describe intended behavior
- Prompts updated to maintain that behavior across model changes

---

## 7. External Catalog Integration

### 7.1 Provider Interface

**Configurable via environment:**
- `CATALOG_PROVIDER` (e.g., "tmdb")
- `CATALOG_API_KEY` (stored server-side)

**Required catalog endpoints:**
- Search shows by title/keyword
- Fetch show details by external ID (full metadata + images)
- Fetch person details (bio, images, credits)
- Fetch recommendations for a show
- Fetch similar shows

### 7.2 Data Fetch & Merge

**On search result click:**
1. Check if show exists locally by ID
2. If yes, open Detail with cached data
3. If no, fetch full details from catalog
4. Create or merge Show object using merge rules
5. Open Detail with fresh data

**Merge rules:**
- Non-user fields: `selectFirstNonEmpty(newValue, oldValue)`
  - Never overwrite non-empty with empty
  - Never overwrite non-nil with nil
- User fields: resolve by timestamp (newer wins)
- Set `detailsUpdateDate = now` after merge

**Background refresh:**
- Optionally refresh details on Detail page load (with stale-while-revalidate pattern)
- Don't block rendering; update in background

### 7.3 Image Handling

**Poster, backdrop, logo:**
- Store full renderable URLs in database
- External catalog returns URL paths; server constructs full URLs
- Logo selection: if multiple exist, choose "best" deterministically (e.g., highest rating with preference for English)

**Gallery on Person Detail:**
- Fetch full image list from catalog
- Render as thumbnail strip + lightbox modal

---

## 8. Authentication & Authorization

### 8.1 Benchmark-Mode Identity Injection (Development)

**For local/benchmark testing:**
- `X-User-Id` header accepted by server routes in dev mode
- Value: stable string or UUID (e.g., "test-user-123")
- Server scopes all data to this user + namespace

**For cloud benchmarks:**
- Similar header injection or environment-provided user ID
- Namespace ID also provided/injected per build

**Implementation:**
- Middleware checks `process.env.NODE_ENV === "development"` or explicit feature flag
- Extracts `X-User-Id` from headers
- Sets `req.userId` for downstream routes
- Disables in production mode (requires real auth)

### 8.2 Future OAuth Path

**Design for easy migration:**
- User identity already modeled as opaque string (`user_id`)
- API routes already accept `user_id` from middleware
- Switch from header injection to real OAuth:
  - Add auth library (NextAuth.js, Supabase Auth, etc.)
  - Extract `user_id` from auth session instead of header
  - Schema unchanged
  - Business logic unchanged

### 8.3 Server-Only Secrets

**Catalog & AI API keys:**
- Stored as environment variables or Supabase secure config
- Never exposed to client JavaScript
- Only used by server API routes
- Client code calls `/api/catalog/search`, not external API directly

**User-entered secrets (optional settings):**
- If user enters AI key in Settings UI:
  - Server stores in `cloud_settings` table (secure column, encrypted at rest)
  - Client never sees plaintext
  - Server uses stored key for that user's AI calls
- This is optional for the MVP; not required for launch

---

## 9. Testing & QA

### 9.1 Test Data & Isolation

**Namespace isolation:**
- Each test run operates within a single `namespace_id`
- Multiple test runs use different `namespace_id` values
- Test data never crosses namespace boundaries

**User isolation:**
- Each test creates a default user or receives a test user ID
- Partition: `(namespace_id, user_id)`

### 9.2 Destructive Testing

**Reset endpoint:** `POST /api/test/reset`

**Input:**
- `namespace_id` (from middleware)
- `includeMetadata` flag (optional)

**Behavior:**
- Delete all shows in namespace
- Optionally delete cloud_settings, metadata
- Do NOT delete other namespaces

**Usage:**
- Called before/after each test suite
- Allows repeatable test runs without global teardown

### 9.3 Test Fixtures

**Create in migrations or seed scripts:**
- Sample shows (movies + TV) with full metadata
- Pre-configured user library (shows with various statuses/tags/ratings)
- Person records with filmographies

**Seedable per namespace:**
- `npm run test:seed` populates test data into current namespace
- `npm run test:reset` clears test data

### 9.4 Key Test Scenarios

**Data persistence:**
- Create show, set status, refresh page → status persists
- Rate show, navigate away, return → rating persists
- Add tag, export data → tag in export

**Auto-save:**
- Rate unsaved show → auto-saved as Done
- Add tag to unsaved show → auto-saved as Later + Interested
- Set status → immediately queryable

**Collection filtering:**
- Filter by status → correct shows displayed
- Filter by tag → tagged shows displayed
- Filter by media type → correct types displayed

**AI surfaces:**
- Ask question → response includes mentions
- Ask with library → response grounded in saved shows
- Explore Similar → 5 recs generated with reasons
- Alchemy with 3 shows + concepts → 6 recs generated

**Show Detail:**
- Open unsaved show → Detail renders
- Rate it → auto-saves
- Set status → indicator updated
- Generate Scoop → cached 4 hours
- Get Concepts → selectable chips
- Explore Shows → 5 recs displayed

**Export:**
- Export user data → `.zip` created with JSON backup
- JSON contains all shows + My Data
- Dates in ISO-8601 format

---

## 10. Infrastructure & Deployment

### 10.1 Environment Variables

**Required `.env.example`:**
```
# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=<public-key>
SUPABASE_SERVICE_ROLE_KEY=<service-key>  # Server-only

# Catalog Provider
CATALOG_PROVIDER=tmdb
CATALOG_API_KEY=<api-key>  # Server-only

# AI Provider
AI_PROVIDER=openai
OPENAI_API_KEY=<api-key>  # Server-only
# OR
ANTHROPIC_API_KEY=<api-key>  # Server-only

# App Config
NODE_ENV=development|production
NEXT_PUBLIC_APP_NAME=Entertainment Companion
```

**Comments:**
- Anon key used by browser; service key for server only
- API keys never committed
- All secrets injected at runtime

### 10.2 Development Environment

**Local Supabase (optional Docker):**
```bash
npm install -g supabase
supabase start
supabase db push  # Apply migrations
npm run dev
```

**Cloud Supabase:**
```bash
# Fill .env with cloud credentials
npm run dev
```

**No Docker requirement** — can run against hosted Supabase directly

### 10.3 CI/CD & Benchmarking

**Build pipeline:**
1. Checkout code
2. Fill `.env` with cloud Supabase credentials + API keys
3. Assign unique `NAMESPACE_ID` per build (e.g., `build-${CI_JOB_ID}`)
4. Run migrations (idempotent)
5. Seed test data (optional)
6. Run test suite with namespace isolation
7. Generate benchmark report
8. Clean up test namespace (via `/api/test/reset`)

**Isolation guarantee:**
- Each build operates only within its namespace
- No collision with other concurrent builds
- Data automatically partitioned by namespace + user

### 10.4 Scripts

**Required npm scripts:**
```bash
npm run dev          # Start development server
npm run build        # Build for production
npm start            # Start production server
npm test             # Run test suite
npm run test:reset   # Clear test data for namespace
npm run db:push      # Apply database migrations
npm run db:seed      # Seed test fixtures
npm run export-data  # Manual export endpoint test
```

---

## 11. UI/UX Specifications

### 11.1 Design Principles

1. **User's version takes precedence** — My Data always visible and editable
2. **Frictionless saves** — no "Save" button; actions auto-save
3. **Taste-aware discovery** — all AI grounded in user's library
4. **Spoiler-safe by default** — no plot spoilers unless requested
5. **Opinionated AI** — honest about mixed reception, not generic praise

### 11.2 Component Hierarchy

**Layout:**
- `App` → `Layout` → `FilterSidebar` + `MainContent`
- `MainContent` → route-specific pages

**Reusable components:**
- `ShowTile` — poster + title + badges
- `StatusChips` — Active/Interested/Excited/Done/Quit/Wait selector
- `RatingSlider` — 0–10 rating control
- `TagInput` — add/remove tags modal
- `ConceptChips` — selectable concept list
- `ShowRecommendationCard` — rec with reason
- `LoadingState` — skeleton/spinner
- `ErrorState` — error message + retry

### 11.3 Responsive Design

**Mobile-first:**
- Sidebar collapses/slides on mobile
- Tiles stack vertically on small screens
- Detail page sections stack; media carousel full width
- Modals for tag/status/rating pickers

**Tablet/Desktop:**
- Sidebar visible; collapsible
- 2–3 column grid for show tiles
- Detail page sidebar-aware layout
- Horizontal strands scrollable

### 11.4 Dark Mode (Optional)

- Support system preference detection
- Toggle in Settings
- All colors carefully chosen for contrast

### 11.5 Accessibility

- Semantic HTML (nav, main, section, article)
- ARIA labels for interactive elements
- Keyboard navigation (tab, arrow keys, enter)
- Color contrast ≥ WCAG AA
- Alt text for all images

---

## 12. Error Handling & Recovery

### 12.1 Client-Side Errors

**Network failures:**
- Show "Connection error" toast
- Retry button for failed requests
- Optimistic updates + rollback on failure

**AI timeouts:**
- "Generation taking longer than expected" message
- Cancel button
- Fall back to non-AI alternative (e.g., traditional recs for Explore Similar)

**Missing catalog items:**
- Show placeholder "Not found in catalog"
- Offer "Search for it" handoff
- Don't block user from proceeding

### 12.2 Server-Side Errors

**Database:**
- Connection pool exhaustion → queue requests, retry with backoff
- Constraint violations → user-friendly message (e.g., "You've already rated this show")
- Transaction conflicts → retry with exponential backoff

**External catalog:**
- Rate limiting → cache aggressively, queue requests
- Timeout → return cached data or partial results
- Not found → user-facing "Show not in catalog"

**AI provider:**
- Rate limiting → queue in memory or database, retry later
- Timeout → show "Generation timed out" + allow manual retry
- Quota exceeded → admin alert + graceful degradation (disable AI features)

### 12.3 Data Integrity

**Duplicate detection:**
- On merge, detect shows with same ID
- Keep newer timestamp's version
- Log conflict for monitoring

**Missing foreign keys:**
- Person IDs in credits validated against person records
- Show IDs in recommendations validated against show catalog
- Remove invalid references on query

---

## 13. Performance & Caching

### 13.1 Client-Side Caching

**In-memory React state:**
- Collection list (invalidate on mutation)
- Detail page data (invalidate on navigation)
- Chat history (session-specific)

**Browser localStorage (optional):**
- Last selected filter
- Font size preference
- UI state (collapsed sections, etc.)

**SWR/React Query (recommended):**
- Stale-while-revalidate for collection list
- Automatic retry on background refetch failures
- Configurable TTL per endpoint

### 13.2 Server-Side Caching

**Database query optimization:**
- Indexes on `(namespace_id, user_id)` for filtering
- Indexes on status/tags for grouping
- Query planning for joins (cast, seasons, recommendations)

**API response caching:**
- Scoop: 4-hour cache (or until manual regenerate)
- Catalog details: 24-hour cache (refresh on Detail load in background)
- Recommendations: session-specific (don't cache across sessions)

**CDN for static content:**
- Images (poster, backdrop, logo, profile pics) cached with long TTL
- Served from CDN if available

### 13.3 AI Caching

**Scoop:**
- Cache per show: `(namespace_id, show_id)` → scoop text + timestamp
- Invalidate after 4 hours or on user request
- Only cache if show is in collection

**Concepts/Recs:**
- Do not cache (session-specific, user controls seed selection)
- But log commonly generated concepts for monitoring

### 13.4 Lazy Loading

**Detail page:**
- Load media carousel + core facts immediately
- Lazy-load cast, seasons, recommendations on scroll
- Lazy-load Scoop on demand (toggle)

**Collection list:**
- Load visible tiles first
- Infinite scroll or pagination for long lists
- Load My Data (status, tags, rating) immediately; detailed metadata lazy

---

## 14. Monitoring & Analytics

### 14.1 Logging

**Server-side:**
- All API requests logged (timestamp, user_id, namespace_id, endpoint, status, duration)
- AI API calls logged (model, tokens used, latency)
- External catalog calls logged (provider, query, results, latency)
- Database errors logged with stack trace
- Namespace reset operations logged

**Client-side:**
- Error stack traces sent to server for aggregation
- User actions optionally logged (save show, rate, tag) for analytics
- No sensitive data in logs (no full user library)

### 14.2 Metrics

**Key metrics:**
- Daily active users
- Weekly additions to collection
- Status/rating/tag update frequency
- AI surface usage (Ask sessions, Alchemy rounds, Explore Similar calls)
- AI cache hit rate (Scoop)
- Average response time (Detail page, Search, Ask, Alchemy)
- Error rates (catalog lookup failures, AI timeouts)
- Namespace collision attempts (should be 0)

### 14.3 Alerting

**Critical:**
- Database connection pool exhaustion
- Catalog provider down
- AI provider down or rate-limited
- Namespace isolation breach (data access across namespaces)

**Warnings:**
- High AI latency (>10s)
- High error rate (>5%)
- Catalog lookup failures (>1%)

---

## 15. Security Considerations

### 15.1 Data Access Control

**Row-Level Security (Supabase RLS):**
- All tables enforce `(namespace_id, user_id)` partition
- Client using anon key cannot access other users' data
- Server using service key can access any namespace (for admin operations)

**API route authorization:**
- Every API route checks middleware-provided `user_id`
- Queries always filtered by `(namespace_id, user_id)`
- No implicit trust of route parameters (e.g., user_id in URL)

### 15.2 Secrets Management

**Environment variables:**
- Never committed to repo
- `.gitignore` excludes `.env*` (except `.env.example`)
- Injected at build time or runtime

**Database secrets:**
- Anon key exposed to browser (limited permissions)
- Service key server-only
- API keys (catalog, AI) server-only

**User-entered secrets:**
- If user enters AI key in Settings, stored encrypted server-side
- Never transmitted back to client
- Used only by server for that user's requests

### 15.3 Input Validation

**User input:**
- Tag names: trim, max length 50 chars, alphanumeric + spaces
- Show search: trim, max length 100 chars
- Chat messages: trim, max length 2000 chars
- Rating: 0–10 or unrated (enum)
- Status: one of valid enum values (active, later, done, etc.)

**External input:**
- Catalog results: validate show ID format before storing
- AI responses: validate JSON structure before parsing
- Person credits: validate external IDs before linking

### 15.4 Rate Limiting

**API routes:**
- Catalog search: 10 requests/minute per user
- Chat (Ask): 5 messages/minute per user
- Scoop generation: 3/hour per show per user
- Export: 1/hour per user

**External providers:**
- Respect catalog provider rate limits
- Queue AI requests if exceeding quota
- Implement exponential backoff for retries

---

## 16. Documentation & Knowledge Transfer

### 16.1 Code Documentation

**In-source:**
- JSDoc comments on API route handlers
- Component prop types documented
- Complex logic (merge rules, conflict resolution) explained
- Database schema comments in migration files

**README:**
- Setup instructions (local + cloud)
- Architecture overview
- Key design decisions + rationale
- Troubleshooting common issues

### 16.2 API Documentation

**OpenAPI/Swagger spec (optional but recommended):**
- Auto-generated from route handlers
- Endpoint signatures, request/response examples
- Rate limits, error codes

**Runbook for operators:**
- How to reset a test namespace
- How to diagnose common issues
- How to manually clear cache
- Alerting runbooks (what to do if AI provider is down)

### 16.3 Design & Product Docs

**Preserved in repo:**
- Product PRD (product_prd.md)
- Infrastructure rider (infra_rider_prd.md)
- AI voice & personality (ai_voice_personality.md)
- AI prompting guide (ai_prompting_context.md)
- Concept system spec (concept_system.md)
- Detail page experience (detail_page_experience.md)
- Discovery quality bar (discovery_quality_bar.md)
- Storage schema (storage-schema.md, storage-schema.ts)

**Development notes:**
- Prompt evolution decisions
- Model choice rationale (why OpenAI vs Anthropic, if applicable)
- Migration notes (what changed from previous data model)

---

## 17. Migration & Launch Phases

### 17.1 Phase 1: Core Collection (MVP)

**Deliverables:**
- Show CRUD (create, read, update, delete)
- Status/interest/tags/rating system
- Collection home with filtering
- Show Detail page (without AI)
- Search external catalog
- Data persistence + isolation

**Scope:**
- No AI features
- No Alchemy, Ask, Explore Similar
- No Person Detail
- No export/import
- Basic UI (functional, not polished)

**Success criteria:**
- User can build collection
- Data persists across sessions
- Namespace isolation verified
- Tests pass

### 17.2 Phase 2: AI Features (Traditional + Ask)

**Deliverables:**
- Scoop generation (AI text) + caching
- Ask conversational surface
- Explore Similar with concepts
- AI mention resolution (mentioned shows)
- Person Detail page
- Export/backup

**Scope:**
- Traditional recommendations (non-AI) functional
- Ask works; mentions parse and resolve
- Concepts generation (single + multi-show)
- Recommend based on concepts

**Success criteria:**
- AI responses match tone/voice spec
- Mentions resolve to real shows
- Scoop caches correctly
- Ask grounded in user library
- Export produces valid JSON zip

### 17.3 Phase 3: Alchemy & Polish

**Deliverables:**
- Alchemy full flow (select shows → concepts → recs → chain)
- UI polish (animations, responsive design)
- Performance optimization (caching, lazy load)
- Monitoring & alerting
- Documentation complete

**Scope:**
- Alchemy recs map to real shows
- Concept selection UX smooth
- All surfaces responsive mobile + desktop
- Error handling robust
- Logging in place

**Success criteria:**
- Alchemy chain-able across multiple rounds
- Mobile UX functional
- Error rates <1%
- Benchmark runs repeatable + isolated
- Knowledge transfer complete

---

## 18. Open Questions & Future Extensions

**From PRD:**
- Should "Next" become a first-class status in UI? (model supports it; UI to be designed)
- Should named custom lists be supported beyond tags?
- Should generating Scoop on unsaved show implicitly save it?
- Should "Unrated" be explicit state vs nil?
- Import/Restore from export zip (Settings mentions; not yet implemented)
- Save/share Alchemy sessions as reusable blends?
- Expose `myStatus` filters in sidebar?

**Implementation notes:**
- Above features can be added post-MVP without schema changes
- Most require only UI additions + optional backend endpoints
- None require fundamental architecture changes

---

## 19. Acceptance Criteria

### 19.1 Functional Completeness

- [ ] User can create collection (save shows with status/tags/rating)
- [ ] Collection persists across sessions and device resets
- [ ] Namespace + user isolation prevents data leakage
- [ ] Status system complete (all statuses + interest levels)
- [ ] Filtering (status, tags, media type) works
- [ ] Detail page displays all sections + My Data controls
- [ ] Search external catalog functional
- [ ] Ask generates taste-aware responses + resolves mentions
- [ ] Explore Similar generates 5 concept-based recs
- [ ] Alchemy generates 6 recs from multi-show blending + chaining works
- [ ] Scoop generation + 4-hour caching
- [ ] Person Detail page functional with filmography
- [ ] Export produces valid JSON zip
- [ ] All timestamps tracked correctly for conflict resolution

### 19.2 Quality Criteria

- [ ] AI responses match voice/personality spec
- [ ] Concept generation produces specific, not generic concepts
- [ ] All recommendations resolve to real catalog items
- [ ] Error handling user-friendly + informative
- [ ] Performance acceptable (Detail load <2s, Search results <1s)
- [ ] Mobile UI responsive and usable
- [ ] Accessibility meets WCAG AA

### 19.3 Data Integrity

- [ ] User edits never overwritten by catalog refresh
- [ ] Duplicate shows merged correctly
- [ ] Namespace isolation cannot be breached
- [ ] Foreign key references validated

### 19.4 Operational

- [ ] All secrets in environment, none committed
- [ ] `.env.example` complete + documented
- [ ] Database migrations idempotent + reversible
- [ ] Test reset endpoint clears namespace-specific data only
- [ ] Logging captures critical events
- [ ] Benchmarks repeatable + isolated

---

## 20. Summary

This implementation plan provides a complete blueprint for building a personal TV/movie companion app grounded in:

1. **Clear product vision** — user-centered collection, taste-aware discovery, consistent AI voice
2. **Technical rigor** — namespace isolation, timestamp-based conflict resolution, server-as-source-of-truth
3. **Operational clarity** — environment-driven configuration, repeatable test/deploy cycles, comprehensive monitoring
4. **Rebuild readiness** — preserved design decisions documented, AI personality specified, schema migrations planned

The architecture prioritizes **data integrity**, **user privacy**, and **taste-aware personalization**. All three PRD documents (product, infrastructure, supporting specs) are integrated throughout to ensure no requirement is missed and no assumption is implicit.

Implementation should proceed in three phases:
1. **Core collection** (MVP) — data model + UI fundamentals
2. **AI features** — Scoop, Ask, Explore Similar, export
3. **Alchemy & polish** — full feature set + performance/UX refinement

Each phase builds on the previous with no breaking changes to the data model or architecture.