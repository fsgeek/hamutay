# Projection Engine Data Model

## The problem

The gateway currently preserves temporal message ordering and compacts
in-place. This mutates the cached prefix on every turn, producing 7-8%
cache hit rates. We're paying 1.25x on ~130K input tokens per turn
instead of 0.1x.

## The projection

The projector transforms the inbound temporal message stream into a
spatial layout optimized for the Anthropic KV cache hierarchy. Stable
content lives at the front; volatile content lives at the back. Cache
breakpoints sit at region boundaries.

### Outbound payload structure

```
┌─────────────────────────────────────────────────────┐
│ Region 0: Tools                                     │
│   Tool definitions (framework + phantom tools)      │
│   ── cache breakpoint 1 ──                          │
├─────────────────────────────────────────────────────┤
│ Region 1: System                                    │
│   Claude Code system prompt                         │
│   Pichay system instructions                        │
│   Skills / agents / memory files (from client)      │
│   ── cache breakpoint 2 ──                          │
├─────────────────────────────────────────────────────┤
│ Region 2: Durable                                   │
│   Stabilized conversation content (promoted)        │
│   Tensor summaries of graduated content             │
│   ── page table ──                                  │
│   ── cache breakpoint 3 ──                          │
├─────────────────────────────────────────────────────┤
│ Region 3: Ephemeral                                 │
│   Recent tool results (aging toward eviction)       │
│   Recent conversation turns (not yet stabilized)    │
│   Content marked for removal (waste)                │
├─────────────────────────────────────────────────────┤
│ Region 4: Current turn                              │
│   User message                                      │
│   Dynamic anchor (live status, pressure)            │
└─────────────────────────────────────────────────────┘
```

Three explicit cache breakpoints. One slot held in reserve (or
available for future use, e.g. a breakpoint within Region 2 if it
grows large enough to benefit from internal segmentation).

### Cache behavior by region

| Region | Mutates? | Cached? | Cost model |
|--------|----------|---------|------------|
| 0: Tools | Never (session lifetime) | Always read after first write | 0.1x |
| 1: System | Never (session lifetime) | Always read after first write | 0.1x |
| 2: Durable | Append-only (grows monotonically) | Read for existing, write for new | Amortized 0.1x |
| 3: Ephemeral | Every turn (compaction, aging) | Written every turn | 1.25x |
| 4: Current | Every turn (new content) | Never cached | 1.0x |

The cost optimization: minimize Region 3+4 tokens, maximize Region 0+1+2
tokens. Content graduates from 3→2 as it stabilizes. Content evicted
from 3 becomes a page table entry in 2 (available, not present).

### Why tools get their own region

The Anthropic cache hierarchy is: tools → system → messages. Tools and
system are separate cache levels. A change in tools invalidates system
and message caches. A change in system invalidates message caches. By
giving tools their own breakpoint, we isolate them completely.

Claude Code's tool definitions are stable for the session. The phantom
tools (yuyay, qunqay, tiqsiy) are stable for the session. One
breakpoint after all tools, never invalidated.

## Region 2: The model's curated memory

Region 2 is a tensor store. Its content is not verbatim copies of
original data — it is the model's compressed understanding, with
declared losses. Every piece of content in Region 2 was produced by
the transformer as an act of curation.

### How content enters Region 2

The model produces a tensor as the **price of eviction**. When the
model wants to release content from its working set, it must provide
a tensor in the release response:

```xml
<release handle="a3f2b901">
  <tensor>
    <content>Structured summary of what this contained</content>
    <declared_losses>What was not preserved and why</declared_losses>
  </tensor>
</release>
```

The gateway will not evict without a tensor. If the model says
"release" without providing one, the content stays. This creates
natural back-pressure: the model only releases what it's willing to
spend output tokens compressing. That cost is a built-in signal about
how much the model values the content.

The verbatim original is always stored in the page store (storage is
cheap). The tensor goes into Region 2. The page table entry points at
both: the tensor for the transformer's use, the verbatim for fault
recovery.

### Region 2 structure

```
┌─────────────────────────────────────────────────────┐
│ Region 2: Durable (model-curated memory)            │
│                                                     │
│   Frozen tensors (oldest first, append-only)        │
│     tensor:a3f2b901 — [content + declared_losses]   │
│     tensor:7e9d4c12 — [content + declared_losses]   │
│     tensor:c8ad36b2 — [content + declared_losses]   │
│     ...                                             │
│                                                     │
│   ── page table (mutable, rewritten each turn) ──   │
│   ── cache breakpoint 3 ──                          │
└─────────────────────────────────────────────────────┘
```

Everything above the page table is frozen and cached. The page table
and everything below it (Regions 3, 4) are rewritten each turn. The
page table is small (metadata, not content), so this cost is minor.

### Page table

The page table is the transformer's map of available memory. It sits
at the end of Region 2, right before cache breakpoint 3.

#### Entry schema

```
PageTableEntry:
  handle: str           # 8-char hex, content-addressed
  kind: "file" | "tool_result" | "conversation" | "tensor"
  label: str            # human-readable (~40 chars)
  status: "present" | "available" | "pending_removal"
  region: 2 | 3         # where the content currently lives
  size_tokens: int       # approximate token count
  fault_count: int       # times recalled after eviction
  age_turns: int         # turns since last access
```

For `available` entries (evicted with tensor), the tensor itself is
in the frozen portion of Region 2. The page table entry is a pointer,
not a duplicate.

For `present` entries still in Region 3, the page table tracks them
so the model can see what's in its working set and decide what to
release.

For `pending_removal` entries, the model has released them but the
gateway is deferring the restructure to protect the cache. The model
can countermand this with a retain signal before the next idle
restructure.

### Status transitions

```
                    ┌──────────────────┐
   arrives ──────> │  present (R3)    │
                    └────────┬─────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
          model releases            gateway evicts
          (with tensor)             (pressure/idle)
                 │                       │
                 v                       v
          ┌──────────────┐    ┌──────────────────┐
          │ available    │    │ pending_removal   │
          │ (tensor→R2,  │    │ (R3, waste —     │
          │  entry in    │    │  no tensor yet,   │
          │  page table) │    │  awaiting model   │
          └──────┬───────┘    │  cooperation)     │
                 │            └────────┬──────────┘
             fault (recall)            │
                 │              idle restructure OR
                 v              model provides tensor
           ┌──────────┐               │
           │ present   │               v
           │ (R3)      │        ┌──────────────┐
           └──────────┘        │ available     │
                                │ (tensor→R2)   │
                                └──────────────┘
```

Key difference from the prior design: the model is the agent of
eviction, not the gateway. The gateway manages pressure and
eligibility. The model decides what to release and produces the
tensor that preserves meaning. Gateway-initiated eviction
(`pending_removal`) is the fallback when the model doesn't
cooperate — and even then, the gateway should ask again before
discarding content without a tensor.

### Idle restructure

When the cache expires (>5 min idle), the gateway restructures:
- Execute all pending removals (with or without tensors)
- Promote surviving ephemeral content based on fault history
- Recompact Region 3
- Rebuild the projection from scratch

The write cost is the same whether we send the old layout or a
clean one, so restructuring is free at idle boundaries.

## Waste tracking

Content in Region 3 marked `pending_removal` is waste. The projector
tracks cumulative waste:

```
waste_bytes: int        # total bytes of pending_removal content
waste_tokens_est: int   # estimated tokens (bytes / 4)
cache_write_cost: float # what we'd pay to restructure (1.25x on everything after the change)
```

Restructure triggers:
- **Idle return** (cache expired anyway): always restructure
- **Waste threshold**: waste_tokens > configurable limit
- **Pressure zone**: context enters "involuntary" or "aggressive" zone

## Dynamic anchor

Appended to the last user message (Region 4). Contains:
- Live status: token count, pressure zone, hard cap
- Waste summary: how much dead weight we're carrying
- Last-turn feedback: what operations were executed

The anchor is always after the last cache breakpoint, so it's free to
mutate without cache impact.

The page table is NOT in the anchor. It's in Region 2, visible to the
transformer as part of the stable context. The anchor is operational
telemetry; the page table is the transformer's map of available memory.

## What the projector replaces

- `_preprocess()` — the entire function
- `inject_system_status()` — Region 1 injection + Region 4 anchor
- `_place_gateway_cache_controls()` — breakpoint placement
- `_strip_all_cache_controls()` — no longer needed (projector owns all markers)
- `compact_messages()` inside `MessageStore.ingest()` — compaction moves to projector
- `MessageStore` physical store concept — replaced by region-aware storage

The `PageStore` fault detection, pinning, and release tracking survive
as mechanisms, but they feed into the page table rather than operating
on the message array directly.

## Open questions

1. **Region 2 internal breakpoint**: If Region 2 grows past ~50K tokens,
   should we split it with the 4th breakpoint? The frozen portion would
   get its own breakpoint, and the page table + recent promotions would
   sit between breakpoints 3 and 4.

2. **Conversation in Region 2**: ~~Resolved.~~ Region 2 content is
   tensors produced by the model, not verbatim conversation turns.
   The model produces the tensor as the price of eviction. This is
   more compact than raw turns and preserves meaning via declared
   losses. The turn structure question becomes: how do we pack tensors
   into valid API message pairs? (See question 4.)

3. **System prompt stability**: Claude Code's system prompt may contain
   dynamic elements (system-reminders). Do we need to strip/normalize
   the client system prompt, or is it stable enough in practice?

4. **Message structure constraints**: The Anthropic API requires
   alternating user/assistant messages. The projection reorders content
   but must still produce valid message alternation. Region 2's durable
   content needs to be packed into valid message pairs.
