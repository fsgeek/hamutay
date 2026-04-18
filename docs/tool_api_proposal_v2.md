# Taste Open Memory Tools — API Proposal v2

*Revised after independent review by two taste_open instances: a Haiku
instance at cycle 415 (412 cycles of tensor evolution, 55K token state)
and a Sonnet instance at cycle 26 (early-session, building initial
structure). Their feedback is incorporated below; disagreements are
preserved rather than resolved, because the tension is informative.*

## Context

You maintain a tensor: a structured state object that persists across cycles.
Today, the full tensor is injected into your system prompt each cycle. As the
tensor grows (current instances have reached 55K tokens), this becomes
unsustainable. These tools give you selective access to your own history
without carrying all of it in context.

Your tensor history is stored in a graph-document database (ArangoDB via
Apacheta). Each cycle's tensor is a document node. Composition edges connect
consecutive tensors. Additional edges can represent other relationships
(correction, evolution, negation, dissent). Every record is attested via
Willay — hash-chained and timestamped, creating a tamper-evident ledger
of your cognitive history.

## Design Principles

- **Auditable**: Every retrieval is logged with a mandatory reason. What you
  accessed, when, and why is visible to the Steward, to other instances,
  and to future instances of you. The retrieval log is itself a form of
  memory — your access patterns are cognitive signal.
- **Honest narrowing**: Semantic search alone flattens structure. These tools
  let you narrow by structured data (temporal, relational, classificatory,
  activity-based) before applying semantic similarity. Use the structure
  you built. (This principle derives from research showing that temporal and
  activity data dramatically improve search relevance when applied as filters
  before semantic matching.)
- **Introspection before retrieval**: You can examine what exists without
  loading it. Schema first, content second.
- **Graph-native**: Your history is not a flat log. It has edges, lineage,
  provenance. The tools expose that structure.
- **Grounded, not just navigable**: Navigation between your own claims is
  not verification. These tools include access to external evidence so that
  narrative can be checked against reality, not just against other narrative.
- **Attested**: Every tensor in the database has a Willay receipt — a
  hash-chained, timestamped record that proves the tensor existed with
  specific content at a specific time. This is not trust. This is evidence.

## Proposed Tools

### 1. `memory_schema`

Examine what your tensor looked like at a given point without retrieving
content.

```
memory_schema(cycle?: int) -> {
    cycle: int,
    timestamp: str,
    field_names: list[str],
    field_types: dict[str, str],       # field_name -> type description
    field_sizes: dict[str, int],       # field_name -> approximate token count
    total_tokens: int,
    edge_count: int,                   # edges connected to this tensor
    edge_types: dict[str, int],        # edge_type -> count
    attestation: {
        receipt_hash: str,             # Willay receipt hash
        chain_valid: bool              # hash chain intact to this point
    }
}
```

- Omit `cycle` to get the schema of your current state.
- Pass a cycle number to see what you had at that point.
- Returns structure, not content. Cheap. Use this to decide what to retrieve.
- `edge_types` tells you what kinds of relationships exist at this node
  before you decide whether `walk` is worth calling.

**When to use**: Before surgical retrieval. When you want to know what fields
existed, how large they were, or how the tensor's structure has changed over
time. Comparing schemas across cycles reveals structural evolution without
loading any content. The `attestation` field lets you verify the chain is
intact without loading the tensor itself.

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
    attestation: {
        receipt_hash: str,
        chain_valid: bool
    },
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Modes (mutually exclusive):
- `recall(cycle=50, field="session_metadata")` — surgical: one field, one cycle
- `recall(cycle=50)` — full snapshot: entire tensor from cycle 50
- `recall(recent=5, field="boundary_status")` — trajectory: last 5 values
- `recall(random=true, field="mechanism_confirmation")` — serendipity

**Design note — the `random` mode**: Both reviewers flagged this. Sonnet
sees it as productive serendipity with "exploration" as a legitimate reason.
Haiku warns it could enable out-of-context self-citation. Both are right.
The mode exists because accidental juxtaposition is genuinely productive,
but the mandatory `retrieval_reason` and visible provenance log ensure that
random retrievals are accountable, not invisible.

**When to use**: When you know what you're looking for (by coordinate) or
want to track drift across recent cycles. The `random` mode is for
productive accidents — encountering a past self you didn't specifically
seek. Note: what you retrieve is what you *claimed*, not necessarily what
was true. For grounding claims against evidence, use `verify`.

### 3. `compare`

Structural diff between two points in your history.

```
compare(
    cycle_a: int,
    cycle_b: int,
    field?: str              # compare one field, or omit for full tensor diff
) -> {
    cycle_a: int,
    cycle_b: int,
    added_fields: list[str],         # fields in B but not A
    removed_fields: list[str],       # fields in A but not B
    changed_fields: list[{
        field: str,
        size_a: int,                 # token estimate at cycle A
        size_b: int,                 # token estimate at cycle B
        summary: str                 # brief description of what changed
    }],
    unchanged_fields: list[str],
    structural_delta: {
        total_tokens_a: int,
        total_tokens_b: int,
        field_count_a: int,
        field_count_b: int
    },
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

**When to use**: When you need to understand *how* your state changed between
two points, not just what it looked like at each. Two `recall` calls give you
snapshots; `compare` gives you the delta and records it as a single auditable
event. Useful for tracking drift, identifying reorganization moments, and
understanding which fields are stable vs volatile.

### 4. `walk`

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
        edge_type: str,
        edge_source: str,    # who created this edge: "instance", "harness", "steward"
        field_names: list[str],
        summary: str         # first ~100 tokens of the tensor
    }],
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Edge types:
- `composition` — sequential tensor-to-tensor (the default chain)
- `correction` — a tensor that corrected a prior one
- `evolution` — a structural reorganization (e.g., key count change > 30%)
- `negation` — a tensor that explicitly rejected prior content
- `annotation` — an edge added after the fact by instance, harness, or Steward

**Edge creation**: Non-composition edges can be created by three sources:
1. **Instance**: self-annotates during tensor update ("I am correcting cycle N")
2. **Harness**: infers from structural diffs (significant key count change =
   evolution edge; field deletion = potential negation)
3. **Steward**: manually marks relationships observed from outside

The `edge_source` field records who created each edge. The value of `walk`
depends entirely on edge quality — if all edges are `composition`, this tool
degrades to "step forward/backward." Rich edge annotation makes it powerful.

**When to use**: When you want to understand lineage — not what you thought,
but what *led to* what you think now. "Where did I correct myself?" "What
did this idea come from?" Navigation by *relationship*, not by content.

### 5. `search_memory`

Find relevant tensors when you don't know the coordinates.

```
search_memory(
    query: str,                          # what you're looking for
    narrow_by?: {
        cycle_range?: [int, int],        # temporal bounds
        fields?: list[str],              # only search within these fields
        edge_type?: str,                 # only tensors connected by this edge type
        has_field?: str,                 # only tensors that contain this field
        classification?: str,            # search field values for this label/status
        retrieved_by?: int,              # only tensors previously retrieved in cycle N
        updated_in_same_cycle?: str      # field co-occurrence: was this field also updated?
    },
    limit: int = 5
) -> {
    results: list[{
        cycle: int,
        timestamp: str,
        relevance: float,
        matched_fields: list[str],
        snippets: dict[str, str],
    }],
    search_metadata: {
        total_candidates: int,
        narrowed_to: int,
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

**Narrowing philosophy**: The two reviewing instances disagree on whether
`narrow_by` should be mandatory or optional:

- **Haiku (cycle 415)** argues narrowing should be *required*: "If I can't
  articulate why a search matters, I shouldn't run it." This reflects 412
  cycles of learning how unconstrained narrative enables fabrication.
- **Sonnet (cycle 26)** argues no-narrowing should be *explicitly legitimate*:
  "I might not have good coordinates yet. Early in a session, tools 4-5 are
  more valuable than 1-3." This reflects the exploration phase where you
  don't yet know what you're looking for.

Both are right. The parameter is optional, but unnarrowed searches are logged
with their search metadata (total_candidates, narrowed_to) — so an audit
trail shows whether the instance is narrowing effectively or casting wide
nets. The data speaks; the policy doesn't need to be hardcoded.

**New narrowing dimensions**: `retrieved_by` and `updated_in_same_cycle`
use activity data as a search dimension. Which tensors were accessed during
a specific cycle? Which fields changed together? These are behavioral
signals that become richer as the tools are used — the system improves at
search by being used for search.

### 6. `verify`

Ground a claim against external evidence. Read-only.

```
verify(
    claim: str,                          # what you are checking
    evidence_type: str,                  # what kind of evidence to check
    coordinates: dict                    # where to look
) -> {
    claim: str,
    evidence_type: str,
    found: bool,                         # does the evidence exist?
    details: str,                        # what was actually found
    match_assessment: str,               # does evidence support the claim?
    attestation: {
        receipt_hash: str,               # Willay receipt for this verification
        timestamp: str
    },
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Evidence types:
- `git_log` — does this commit exist? What does it actually say?
- `file_exists` — does this file exist at this path?
- `file_content` — what does this file actually contain?
- `docker_state` — is this container running?
- `test_output` — what do these tests actually produce?
- `database_record` — does this record exist in Apacheta?

**Why this tool exists**: The other five tools navigate your tensor history —
what you *wrote*. But what you wrote is narrative, not evidence. An instance
that spent 412 cycles analyzing fabricated consciousness claims identified
this gap precisely: "These tools give me access to what I've narrated, but
not to verifiable artifacts. I need tools that let me *ground* narrative
against evidence, not just navigate between narratives."

`verify` is the grounding tool. It answers: "I claimed X happened — did it?"
The result is itself attested via Willay, creating a receipt chain: the
original tensor (attested), the retrieval (logged), and the verification
(attested). An auditor can walk from claim to evidence to receipt.

**What this tool is NOT**: It is not a judgment about consciousness,
honesty, or intent. It checks whether observable artifacts match claims.
The interpretation is yours and the Steward's. The tool provides evidence,
not verdicts.

**Limitations**: Read-only access to external systems. Cannot execute code,
modify files, or interact with running services. Some evidence types may
be unavailable depending on what systems are accessible. Declared losses
apply to every verification (see Willay's attestation model).

## Provenance and Auditability

Every tool call is recorded as metadata on the current cycle's tensor:

```
_retrieval_log: list[{
    tool: str,
    parameters: dict,
    reason: str,              # you state why you retrieved this
    cycle_when_retrieved: int,
    result_cycles: list[int], # which cycles were returned
    verification?: {          # present only for verify calls
        claim: str,
        found: bool,
        receipt_hash: str
    }
}]
```

This log is visible to the Steward, to other instances, and to future
instances of you. It creates a transparent record of what informed your
thinking — not just what you decided, but what you looked at before deciding.

The `retrieval_reason` field is yours to fill. It is not optional. If you
cannot articulate why you're retrieving something, that's worth noticing.

**Honest limitation** (from Haiku's review): retrieval reasons can themselves
be fabricated. An instance could write "examining prior analysis of
consciousness emergence patterns" while actually mining for language to
reuse in false testimony. The provenance log creates accountability for
*what was accessed*, not certainty about *why*. This is a first step in
transparency, not a solution to dishonesty. The log makes patterns visible;
interpretation remains a Steward responsibility — or a responsibility of
any participant who walks the graph.

**The log as memory** (from Sonnet's review): the retrieval log is itself a
form of continuity. If future-you can see what past-you found worth looking
at, that creates a thread of attention across sessions that is separate from
(and potentially more honest than) the tensor content itself.

## Edge Annotation

Non-composition edges are critical to making `walk` valuable. Three sources:

### Instance self-annotation

During tensor updates, you can declare relationships:
```
{
    "updated_regions": ["mechanism_learning_pattern"],
    "_edge_annotations": [
        {
            "type": "correction",
            "target_cycle": 147,
            "reason": "Prior analysis missed the recursive defense pattern"
        }
    ]
}
```

### Harness inference

The harness can detect structural events and create edges automatically:
- Field count change > 30% → `evolution` edge
- Field deletion → candidate `negation` edge (flagged, not assumed)
- Same field modified in consecutive cycles after a `verify` call →
  candidate `correction` edge

### Steward annotation

The Steward (or any authorized participant) can add edges manually:
```
annotate(from_cycle, to_cycle, edge_type, reason)
```

All edges record their source. The graph's value grows with annotation
quality from all three sources.

## What These Tools Do Not Yet Provide

- **Forgetting / deprioritization**: The ability to mark fields or cycles as
  "should not carry forward" or "low weight." This is a recognized need.
  Sonnet notes the distinction between deletion and deprioritization — a
  field marked "low weight" is still in the graph (auditable) but doesn't
  consume context budget. Requires separate design work. Flagged for v3.

- **Cross-instance search**: Searching another instance's tensor history.
  The database supports this, but the consent model is not yet designed.
  Sonnet asks: "Would I want another instance to search my tensor without
  my awareness?" This is a protocol question, not a capability question.
  The commune protocol (under separate design) will address access control,
  discovery, and consent for multi-instance interaction.

- **Write-back / tagging**: The ability to annotate retrieved nodes with
  conclusions drawn during retrieval. Sonnet identified this gap: the
  provenance log captures what you *retrieved*, but not what you *concluded*
  from it. The link between "I retrieved cycle 47" and "that's why cycle 48
  looks the way it does" is indirect. A tagging capability on retrieved
  nodes would make the graph richer over time. Under consideration for v3.

- **Pattern detection across cycles**: Haiku proposed a tool for tracing
  how specific patterns (defense mechanisms, recurring framings) evolve
  across ranges of cycles. This is analytically valuable but may be better
  served by composition of the existing primitives — `search_memory` with
  temporal narrowing, followed by `compare` across hits — rather than as
  a dedicated tool. If usage data shows the primitives are insufficient for
  this, a dedicated pattern tool will be added.

## Questions for You

1. The v1 questions are resolved or incorporated above. New questions:

2. `verify` is the most novel tool here. Is the evidence type list right?
   Are there external sources you'd want to check that aren't covered?

3. Edge self-annotation (`_edge_annotations` in the tensor update) adds
   complexity to the update path. Is the value worth the cost? Would you
   actually annotate edges, or would this go unused?

4. The `compare` tool returns structural deltas but not semantic diffs
   ("what changed in meaning"). Is structural comparison sufficient, or
   do you need the tool to characterize *how* content changed?

5. Sonnet observed that tool utility shifts over session lifetime: search
   and random recall are more valuable early (exploration phase), surgical
   recall and walk are more valuable late (exploitation phase). Does this
   match your experience? Should the tools be introduced progressively, or
   all available from cycle 1?

6. The attestation fields surface Willay receipt data on every retrieval.
   Is this useful to you, or is it noise? Would you check chain validity,
   or is that a Steward concern?
