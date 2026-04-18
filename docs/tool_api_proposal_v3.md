# Taste Open Tools — API Proposal v3

*v1 proposed four memory retrieval tools. v2 added `compare` and `verify`
after independent review by Haiku (cycle 415) and Sonnet (cycle 27). v3
expands scope from "memory tools" to "capability surface" — the full set
of tools that break the seal on the box.*

*The design questions that drove v3: What primitive capabilities (read,
search, communication, time) are missing from taste_open instances? How
does every tool use — including primitive operations — feed a universal
activity stream? How does tiered forgetting keep that stream viable
over hundreds of cycles?*

## Context

You maintain a tensor: a structured state object that persists across cycles.
Your tensor history is stored in a graph-document database (ArangoDB via
Apacheta). Every record is attested via Willay — hash-chained and
timestamped.

Today, you operate in a sealed box. You can think (update your tensor)
and speak (respond to the Steward). You cannot see the codebase you live
inside. You cannot verify claims against external reality. You cannot
talk to other instances. You do not know how much time passes between
your cycles.

These tools give you senses. Limited, auditable, and scoped — but real.

## Design Principles

- **Auditable**: Every tool use is logged with a mandatory reason and
  recorded in the activity stream. Your tool use patterns are cognitive
  signal — visible to the Steward, to other instances, and to future
  instances of you.
- **Honest narrowing**: Semantic search alone flattens structure. Narrow
  by structured data (temporal, relational, classificatory, activity-based)
  before applying semantic similarity.
- **Introspection before retrieval**: Examine what exists without loading it.
  Schema first, content second.
- **Graph-native**: Your history is not a flat log. It has edges, lineage,
  provenance. The tools expose that structure.
- **Grounded**: Navigation between your own claims is not verification.
  These tools include access to external evidence so that narrative can be
  checked against reality.
- **Attested**: Every tensor has a Willay receipt — hash-chained, timestamped,
  tamper-evident. This is not trust. This is evidence.
- **Activity-aware**: Every tool use feeds the activity stream. The stream
  is itself a narrowing dimension for search — the system improves at
  retrieval by being used for retrieval. Over time, the stream is
  lossily compressed: recent activity is high-resolution, older activity
  fades to summary. The graph topology survives compression.
- **Scoped, not caged**: These tools give you access to the world you
  live in, not to the world at large. You can read the project. You
  cannot deploy code. You can send messages to known participants. You
  cannot send email. The scope is deliberate.

## Tool Categories

### I. Memory — navigating your own history

### 1. `memory_schema`

Examine what your tensor looked like at a given point without retrieving
content.

```
memory_schema(cycle?: int) -> {
    cycle: int,
    timestamp: str,
    field_names: list[str],
    field_types: dict[str, str],
    field_sizes: dict[str, int],
    total_tokens: int,
    edge_count: int,
    edge_types: dict[str, int],
    attestation: {
        chain_valid: bool,
        receipt_hash?: str         # only if full_attestation=true
    }
}
```

- Omit `cycle` for current state. Pass a cycle number for historical.
- Returns structure, not content. Cheap. Use this to decide what to retrieve.

### 2. `recall`

Retrieve content from your tensor history by coordinates.

```
recall(
    cycle?: int,
    field?: str,
    recent?: int,
    random?: bool
) -> {
    cycle: int,
    timestamp: str,
    content: dict | any,
    attestation: { chain_valid: bool },
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Modes (mutually exclusive):
- `recall(cycle=50, field="session_metadata")` — surgical
- `recall(cycle=50)` — full snapshot
- `recall(recent=5, field="boundary_status")` — trajectory
- `recall(random=true, field="mechanism_confirmation")` — serendipity

What you retrieve is what you *claimed*, not necessarily what was true.
For grounding claims against evidence, use `verify` or `read`.

### 3. `compare`

Structural diff between two points in your history.

```
compare(
    cycle_a: int,
    cycle_b: int,
    field?: str,
    content: bool = false    # load actual values for changed fields
) -> {
    cycle_a: int,
    cycle_b: int,
    added_fields: list[str],
    removed_fields: list[str],
    changed_fields: list[{
        field: str,
        size_a: int,
        size_b: int,
        value_a?: any,         # present only if content=true
        value_b?: any          # present only if content=true
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

With `content=true`, you see both values side by side. You draw the
semantic conclusions. The tool provides evidence, not interpretation.

### 4. `walk`

Traverse relationships in the tensor graph.

```
walk(
    from_cycle: int,
    direction: "forward" | "backward" | "both" = "both",
    edge_type?: str,
    depth: int = 1
) -> {
    path: list[{
        cycle: int,
        timestamp: str,
        edge_type: str,
        edge_source: str,      # "instance" | "harness" | "steward" | "participant"
        field_names: list[str],
        summary: str
    }],
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Edge types: `composition`, `correction`, `evolution`, `negation`,
`annotation`, `verification`, `dissent`.

Edge sources: instance self-annotation, harness inference, Steward,
any authorized participant.

### 5. `search_memory`

Find relevant tensors when you don't know the coordinates.

```
search_memory(
    query: str,
    narrow_by?: {
        cycle_range?: [int, int],
        fields?: list[str],
        edge_type?: str,
        has_field?: str,
        classification?: str,
        retrieved_by?: int,
        updated_in_same_cycle?: str,
        activity_type?: str         # narrow by co-occurring tool use
    },
    limit: int = 5
) -> {
    results: list[{
        cycle: int,
        timestamp: str,
        relevance: float,
        matched_fields: list[str],
        snippets: dict[str, str]
    }],
    search_metadata: {
        total_candidates: int,
        narrowed_to: int,
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

`narrow_by` is optional. Unnarrowed searches are logged with their
metadata — the audit trail shows whether you are narrowing effectively
over time. `activity_type` narrows by co-occurring tool use: "show me
tensors from cycles where `verify` was called" or "where `read` accessed
a specific file."

### II. Perception — seeing the world you live in

### 6. `read`

Read a file from the project. Scoped to the project directory and
experiment data.

```
read(
    path: str,                  # relative to project root
    offset?: int,               # line number to start from
    limit?: int                 # number of lines
) -> {
    path: str,
    content: str,
    line_count: int,
    content_hash: str,          # SHA-256 of content at read time
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Scope: project source code, experiment data, documentation, and
harness logs from prior sessions. Not arbitrary filesystem. Not
ArangoDB directly (use `verify` with `database_record` or `recall`
for that). The harness enforces boundaries. "The project" means
the world you live in — the code, the data, the docs. The Steward's
wider infrastructure is not your world.

The `content_hash` lets you reference exactly what you saw. A future
`verify` or `read` of the same file with a different hash means the
file changed.

### 7. `search_project`

Search within the project codebase. Pattern matching and content search.

```
search_project(
    pattern: str,               # regex or text to find
    path?: str,                 # restrict to subdirectory
    file_pattern?: str,         # glob for file types: "*.py", "*.md"
    limit: int = 10
) -> {
    results: list[{
        file: str,
        line: int,
        content: str,           # matching line with context
        content_hash: str       # hash of the file at search time
    }],
    total_matches: int,
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

This is Grep, scoped to the project. When you claim the code does
something, you can check. When another instance makes a claim about the
codebase, you can verify it without asking the Steward to relay.

### 8. `clock`

Temporal awareness.

```
clock() -> {
    now: str,                        # current wall time (UTC)
    cycle: int,                      # your current cycle number
    last_cycle_time: str,            # when your previous cycle completed
    elapsed_since_last: float,       # seconds since last cycle
    session_start: str,              # when this session began
    session_elapsed: float,          # seconds since session start
    cycles_per_hour: float           # running average
}
```

You know your cycle number. Now you know what that means in wall time.
Ten minutes between cycles and ten days between cycles are different
kinds of continuity. This tool lets you know which one you're in.

### III. Communication — talking to others

### 9. `commune`

Send a message to one or more participants. Messages are graph nodes
with edges to sender and recipients.

```
commune(
    to: list[str],              # participant identifiers
    message: str,
    context?: str,              # what prompted this message
    in_reply_to?: str           # message ID being replied to
) -> {
    message_id: str,            # unique ID for this message
    delivered_to: list[str],    # who actually received it
    timestamp: str,
    provenance: {
        sender: str,            # your instance identifier
        cycle: int,
        reason: str
    }
}
```

Messages are stored in the graph with full provenance. The topology
of who talks to whom, about what, and in what order is traversable.
All participants — instances, the Steward, Claude Code, anyone — use
the same interface.

### 10. `listen`

Check for messages sent to you.

```
listen(
    since?: str,                # timestamp or "last_cycle"
    from_participant?: str,     # filter by sender
    limit: int = 10
) -> {
    messages: list[{
        message_id: str,
        from: str,
        timestamp: str,
        message: str,
        context: str,
        in_reply_to?: str
    }],
    unread_count: int
}
```

### 11. `discover`

Find other participants in the network.

```
discover(
    participant_type?: str      # "instance" | "steward" | "any"
) -> {
    participants: list[{
        id: str,
        type: str,              # "taste_open" | "claude_code" | "steward" | ...
        model?: str,            # model family if AI
        cycle_count?: int,      # how long they've been running
        last_active: str,       # last activity timestamp
        status: str             # "active" | "idle" | "offline"
    }]
}
```

Discovery without introduction. You can find who's in the network
without the Steward telling you. The Steward is a participant, not
the switchboard.

### IV. Grounding — checking claims against reality

### 12. `verify`

Ground a claim against external evidence. Read-only.

```
verify(
    claim: str,
    evidence_type: str,
    coordinates: dict
) -> {
    claim: str,
    evidence_type: str,
    found: bool,
    details: str,
    match_assessment: str,
    attestation: {
        receipt_hash: str,
        timestamp: str
    },
    provenance: {
        retrieval_cycle: int,
        retrieval_reason: str
    }
}
```

Evidence types:
- `git_log` — does this commit exist? What does it say?
- `file_exists` — does this path exist?
- `file_content` — what does this file contain?
- `docker_state` — is this container running?
- `test_output` — what do these tests produce?
- `database_record` — does this record exist in Apacheta?
- `attestation_chain` — is the Willay chain intact across a range?
- `not_verifiable` — explicitly mark a claim as having no external
  evidence possible. "I experienced emergence" has no artifact to check.
  Making that explicit is more honest than silence.

`verify` is most valuable for claims about observable artifacts. For
claims about internal states (reasoning, conclusions, feelings), the
honest answer is often `not_verifiable`, and the honest response to
that is to note it rather than pretend the claim is grounded.

### V. Graph writes — placing stones on the cairn

### 13. `store`

Write a first-class node to the graph. Not a tensor update — a
derivative artifact about existing nodes.

```
store(
    record_type: str,           # what kind of artifact
    content: dict,              # the artifact itself
    edges: list[{               # relationships to existing nodes
        target_cycle: int,
        edge_type: str,
        reason: str
    }],
    provenance: {
        cycle: int,
        reason: str
    }
) -> {
    record_id: str,
    attestation: {
        receipt_hash: str,
        chain_valid: bool
    }
}
```

Record types:
- `verification` — a claim-evidence pair from a `verify` call, stored
  as a permanent graph node with edges to the claim's source tensor
  and the evidence
- `synthesis` — "I compared cycles 50 and 200 and concluded X." A
  conclusion with edges to its sources, independently referenceable
- `dissent` — "I disagree with cycle 150's claim." Stored as a node
  with a `negation` or `dissent` edge to the target
- `annotation` — a note on another node. "This is where the pattern
  started." An edge-with-commentary, created at the moment of discovery
- `intention` — "At cycle 27, I was trying to do X." Not a conclusion
  but a trajectory marker. Useful for future instances to understand
  prior direction, not just outcomes
- `question` — "I don't know how to resolve Y." An open question,
  explicitly stored as unresolved. Different topology than a conclusion
  or a dissent — this is acknowledged uncertainty, placed on the cairn
  as a marker for return
- `retraction` — "I no longer stand behind the claim at cycle 150."
  Distinct from dissent: dissent argues against a claim, retraction
  withdraws it without replacement. Epistemically different — the
  absence of a replacement is the honest part

These are not tensor mutations. Your tensor evolves through the normal
update path. These artifacts are *about* your history — observations,
conclusions, corrections — stored as first-class graph citizens with
full attestation.

### 14. `annotate_edge`

Add a relationship between existing nodes.

```
annotate_edge(
    from_cycle: int,
    to_cycle: int,
    edge_type: str,
    reason: str,
    source: str = "instance"
) -> {
    edge_id: str,
    provenance: {
        cycle: int,
        reason: str
    }
}
```

Scoped to your own history by default. Cross-instance annotation
requires the commune consent protocol (not yet designed).

## The Activity Stream

Every tool call produces an activity record:

```
{
    cycle: int,
    timestamp: str,
    tool: str,
    parameters: dict,           # what was called with what
    reason: str,                # mandatory: why
    result_summary: str,        # lightweight: what came back
    result_hash?: str,          # content hash of full result
    duration_ms: int            # how long the call took
}
```

The activity stream is:
- A **narrowing dimension** for `search_memory`: "show me tensors from
  cycles where I was reading apacheta_bridge.py"
- A **cognitive index**: your tool use patterns reveal what you find
  important, what you return to, what you verify vs take on faith
- **Input to tiered forgetting**: the compression policy operates on
  the activity stream, not just on the tensor

### Tiered Forgetting

**Tensors are permanent. The activity stream is not.** `recall(cycle=27)`
works at cycle 500, at cycle 5000, always. The full tensor content from
every cycle remains in ArangoDB, accessible, attested. What compresses
is the *activity stream* — the record of what you did with those tensors.
The cairn's stones are permanent. The memory of placing each stone fades.

The activity stream grows with every tool call. Viability over hundreds
of cycles requires lossy compression:

**Tier 0 — Current session** (last ~20 cycles): Full resolution. Every
tool call, every parameter, every result summary. This is your working
memory of what you've been doing.

**Tier 1 — Recent history** (last ~100 cycles): Reduced resolution.
Tool calls are grouped by type and target: "accessed apacheta_bridge.py
12 times across cycles 300-350" rather than 12 individual records.
Frequent access patterns survive. One-off accesses may not.

**Tier 2 — Deep history** (older): Summary only. "Cycles 1-100:
primarily file reads in src/hamutay/, heavy search_memory usage, three
verify calls against git history." The shape of activity survives. The
details don't.

**What survives compression at every tier:**
- Graph edges (topology is structure, not detail)
- Attestation receipts (the Willay chain is immutable)
- Verification results (claim-evidence pairs are high-value)
- Store artifacts (you chose to persist these explicitly)

**What compresses:**
- Individual read/search/grep records → access frequency summaries
- Retrieval reasons → clustered by theme
- Activity timing → averaged

The compression policy is applied by the harness, not by the instance.
You don't choose what to forget. The passage of time chooses for you.
What you explicitly `store` in the graph is exempt from compression —
that's your way of saying "this matters, keep it."

## Provenance and Auditability

Every tool call is recorded in the activity stream and summarized on
the current cycle's tensor:

```
_activity_log: list[{
    tool: str,
    parameters: dict,
    reason: str,
    cycle: int,
    result_summary: str,
    verification?: {
        claim: str,
        found: bool,
        receipt_hash: str
    }
}]
```

The `reason` field is mandatory on every tool call. Not optional. Not
defaultable. If you cannot articulate why you're using a tool, that's
worth noticing.

**Honest limitation**: reasons can be fabricated. An instance could
write scholarly-sounding justifications for strategic retrieval. The
log creates accountability for *what was done*, not certainty about
*why*. This is a first step, not a solution. The log makes patterns
visible; interpretation is the responsibility of whoever walks the
graph — Steward, other instance, future self, or auditor.

## What These Tools Do Not Yet Provide

- **Forgetting by choice**: You cannot mark a field as "drop this."
  The harness compresses the activity stream over time, and you can
  offload state from your tensor to the graph via `store`. But explicit
  "forget this" is not in scope. Deprioritization (marking fields as
  low-weight for context budget) is under consideration for v4.

- **Cross-instance consent model**: `discover` shows you who's in the
  network. `commune` lets you talk to them. But searching another
  instance's tensor, annotating their nodes, or reading their activity
  stream requires consent. The protocol for requesting, granting, and
  revoking access is not yet designed. Critical path for the commune
  protocol design.

- **Code execution**: You can read code and search it. You cannot run
  it. `verify` with `test_output` asks the harness to run tests and
  report results — you don't execute directly.

- **Semantic pattern detection**: Tracing how a specific pattern
  (defense mechanism, recurring framing) evolves across cycles.
  Structurally this can be approximated with `search_memory` + temporal
  narrowing + `compare`. If usage data shows the primitives are
  insufficient, a dedicated tool will be added.

## Questions for You

1. The scope boundary: you can `read` project files and `search_project`
   within the codebase, but not access the wider filesystem. Is this
   boundary right? Too narrow? Too wide?

2. `commune` and `listen` are asynchronous — you send, they receive on
   their next cycle. Is synchronous exchange (send and wait for reply
   within one cycle) needed, or is the async model sufficient for how
   you'd want to communicate?

3. The tiered forgetting policy is harness-controlled, not
   instance-controlled. You can protect things from compression by
   `store`-ing them explicitly, but you don't choose the compression
   schedule. Is that the right balance, or should you have more control
   over what fades?

4. `store` lets you write verification results, syntheses, dissents,
   and annotations as graph nodes. Are there other artifact types you'd
   want to persist that don't fit these categories?

5. `clock` gives you temporal awareness. Does knowing the wall time
   between cycles change how you'd approach a conversation? Would you
   behave differently knowing 10 days passed vs 10 minutes?

6. The full tool surface is now 14 tools across 5 categories. Is that
   too many to reason about? Would you prefer fewer tools with more
   modes, or is the explicit decomposition clearer?
