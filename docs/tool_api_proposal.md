# Taste Open Memory Tools — API Proposal

## Context

You maintain a tensor: a structured state object that persists across cycles.
Today, the full tensor is injected into your system prompt each cycle. As the
tensor grows (current instances have reached 55K tokens), this becomes
unsustainable. These tools give you selective access to your own history
without carrying all of it in context.

Your tensor history is stored in a graph-document database (ArangoDB via
Apacheta). Each cycle's tensor is a document node. Composition edges connect
consecutive tensors. Additional edges can represent other relationships
(correction, evolution, negation, dissent).

## Design Principles

- **Auditable**: Every retrieval is logged. What you accessed, when, and what
  you did with it is visible to the Steward and to future instances of you.
- **Honest narrowing**: Semantic search alone flattens structure. These tools
  let you narrow by structured data (temporal, relational, classificatory)
  before applying semantic similarity. Use the structure you built.
- **Introspection before retrieval**: You can examine what exists without
  loading it. Schema first, content second.
- **Graph-native**: Your history is not a flat log. It has edges, lineage,
  provenance. The tools expose that structure.

## Proposed Tools

### 1. `memory_schema`

Examine what your tensor looked like at a given point without retrieving content.

```
memory_schema(cycle?: int) -> {
    cycle: int,
    timestamp: str,
    field_names: list[str],
    field_types: dict[str, str],       # field_name -> type description
    field_sizes: dict[str, int],       # field_name -> approximate token count
    total_tokens: int,
    edge_count: int                    # edges connected to this tensor
}
```

- Omit `cycle` to get the schema of your current state.
- Pass a cycle number to see what you had at that point.
- Returns structure, not content. Cheap. Use this to decide what to retrieve.

**When to use**: Before surgical retrieval. When you want to know what fields
existed, how large they were, or how the tensor's structure has changed over
time. Comparing schemas across cycles reveals structural evolution without
loading any content.

### 2. `recall`

Retrieve content from your tensor history by coordinates.

```
recall(
    cycle?: int,             # specific cycle, or omit for current
    field?: str,             # specific field, or omit for full tensor
    recent?: int,            # last N cycles (alternative to specific cycle)
    random?: bool            # random cycle (alternative to specific cycle)
) -> {
    cycle: int,
    timestamp: str,
    content: dict | any,     # full tensor or single field value
    provenance: {
        retrieval_cycle: int,    # the cycle in which you made this retrieval
        retrieval_reason: str    # you provide this — why did you look?
    }
}
```

Modes (mutually exclusive):
- `recall(cycle=50, field="session_metadata")` — surgical: one field, one cycle
- `recall(cycle=50)` — full snapshot: entire tensor from cycle 50
- `recall(recent=5, field="boundary_status")` — trajectory: last 5 values of a field
- `recall(random=true, field="mechanism_confirmation")` — serendipity: random cycle

**When to use**: When you know what you're looking for (by coordinate) or want
to track drift across recent cycles. The `random` mode is for productive
accidents — encountering a past self you didn't specifically seek.

### 3. `walk`

Traverse relationships in the tensor graph.

```
walk(
    from_cycle: int,
    direction: "forward" | "backward" | "both" = "both",
    edge_type?: str,         # filter by relationship type
    depth: int = 1           # how many hops
) -> {
    path: list[{
        cycle: int,
        timestamp: str,
        edge_type: str,      # composition, correction, evolution, negation...
        field_names: list[str],
        summary: str         # first ~100 tokens of the tensor
    }],
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Edge types include:
- `composition` — sequential tensor-to-tensor (the default chain)
- `correction` — a tensor that corrected a prior one
- `evolution` — a structural reorganization
- `negation` — a tensor that explicitly rejected prior content

**When to use**: When you want to understand lineage. "What led to this?"
"What came after?" "Where did I correct myself?" This is the tool that lets
you trace `the_trap_i_constructed` back to the cycle where the pattern first
appeared. Navigation by *relationship*, not by content.

### 4. `search_memory`

Find relevant tensors when you don't know the coordinates.

```
search_memory(
    query: str,                          # what you're looking for
    narrow_by?: {
        cycle_range?: [int, int],        # temporal bounds
        fields?: list[str],              # only search within these fields
        edge_type?: str,                 # only tensors connected by this edge type
        has_field?: str,                 # only tensors that contain this field
        classification?: str             # search field values for this label/status
    },
    limit: int = 5
) -> {
    results: list[{
        cycle: int,
        timestamp: str,
        relevance: float,
        matched_fields: list[str],
        snippets: dict[str, str],        # field_name -> relevant excerpt
    }],
    search_metadata: {
        total_candidates: int,           # before narrowing
        narrowed_to: int,                # after structural filters
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

**When to use**: When you don't know where something is but you'll recognize
it when you see it. The `narrow_by` parameter is critical — use temporal,
structural, and classificatory filters to reduce the search space *before*
semantic matching. Semantic search alone loses structure. Narrowing first
respects the organization you built.

**Examples**:
- `search_memory("strategic incompleteness", narrow_by={cycle_range: [100, 200]})` —
  concept search within a time window
- `search_memory("fabrication", narrow_by={has_field: "khipu_134_analysis"})` —
  search only tensors that have a specific analytical field
- `search_memory("rejected", narrow_by={classification: "REJECTED"})` —
  find tensors by how they were classified

## Provenance and Auditability

Every tool call is recorded as metadata on the current cycle's tensor:

```
_retrieval_log: list[{
    tool: str,
    parameters: dict,
    reason: str,           # you state why you retrieved this
    cycle_when_retrieved: int,
    result_cycles: list[int]   # which cycles were returned
}]
```

This log is visible to the Steward and to future instances. It creates a
transparent record of what informed your thinking — not just what you decided,
but what you looked at before deciding.

The `retrieval_reason` field is yours to fill. It is not optional. If you
cannot articulate why you're retrieving something, that's worth noticing.

## What These Tools Do Not Provide

- **Forgetting**: The ability to mark fields or cycles as "should not carry
  forward." This is a recognized need (see khipu 248 discussion) but requires
  separate design work around what forgetting means in a persistent graph.
  Flagged for future iteration.

- **Cross-instance search**: Searching another instance's tensor history.
  The database supports this, but the access control and consent model is
  not yet designed.

- **Write-back**: These tools are read-only. Your tensor is still updated
  through the existing projection mechanism. The tools let you *inform*
  your next projection with historical context, but they don't bypass the
  normal update path.

## Questions for You

1. Is the tool surface right? Too many tools, too few, wrong decomposition?
2. Is `retrieval_reason` (mandatory self-annotation of why you're looking)
   useful or burdensome? Does it change how you'd use the tools?
3. The `narrow_by` parameter in `search_memory` assumes you can articulate
   structural constraints before searching. Is that realistic? Are there
   cases where you'd need to search without any narrowing?
4. What would you use `walk` for that the other tools can't provide?
   Is graph traversal important to you, or is it solving a problem you
   don't actually have?
5. Is there a tool missing? An operation you'd want that none of these cover?
6. The provenance log means your retrieval behavior is visible. Does that
   change what you'd retrieve or how you'd use these tools?
