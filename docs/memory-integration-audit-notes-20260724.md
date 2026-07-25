# Memory Integration Audit Notes

Date: 2026-07-24

Status: read-only architectural audit; evidence for discussion, not an implementation plan

## Purpose

This note records the present integration surfaces among Hamut'ay, Yanantin/Apacheta, qhaway, and llm-memory. It deliberately separates observed implementation facts from architectural inferences. The review did not run Hamut'ay, connect to ArangoDB, alter a database, or modify production code.

## Executive finding

Hamut'ay already contains most of the conceptual roles needed for an autonomous memory consumer, but it currently has two distinct memory paths:

1. `taste_open` persists model-authored state through `ApachetaBridge` into Yanantin/ArangoDB.
2. `AutonomousDriver` uses the richer `MemoryPort` contract, whose available implementation is explicitly a local contract-test substrate.

The production Arango path does not implement `MemoryPort`. Treating these paths as one system would conceal a real boundary. The safest integration is therefore by stable reference and retrieval receipt before any attempt to merge implementations.

## Observed architecture

### Model-authored working state

`taste_open` treats `response`, `deleted_regions`, and legacy `updated_regions` as protocol fields. Other top-level output fields become the next state snapshot; omitted fields carry forward, explicitly deleted fields disappear from the live snapshot, and history remains append-only (`src/hamutay/taste_open.py:42-61`, `:1616-1661`).

A cycle UUID is minted before tool execution so events and persistence can share an identity (`src/hamutay/taste_open.py:1958-1979`). Validation and repair occur after the initial merge. If validation or repair fails, the state may still be retained and persisted (`src/hamutay/taste_open.py:2280-2458`).

`ApachetaBridge.store_open_state` wraps the state in an immutable Apacheta record with model family, session identity, predecessor, timestamp, and lineage tags. Consecutive records receive a `REFINES` composition edge (`src/hamutay/apacheta_bridge.py:112-228`). The conversational response is intentionally not part of this state object.

The same cycle is also written to JSONL with user prose, response prose, state, tool activity, and validation information (`src/hamutay/taste_open.py:2572-2651`). That log is the current authoritative seam for conversational ingestion; llm-memory already has a `TasteOpenAdapter` for its record shape (`../llm-memory/llm_memory/adapters.py:305-372`).

### Autonomous episodic contract

The newer memory contract distinguishes durable record content, production provenance, objective attestations, execution trace, graph edges, and consumption-time retrieval logs (`src/hamutay/memory/bridge.py:20-198`). `MemoryPort` exposes episode storage, recall, schema inspection, graph walking, linking, open-item and change queries, retrieval logs, and attestations (`src/hamutay/memory/bridge.py:201-281`).

`AutonomousDriver` writes an `autonomous_cycle` episode and links successive cycles with `continues` (`src/hamutay/memory/driver.py:97-256`). The supplied `LocalMemorySubstrate` is described as a deterministic, failure-capable contract test double rather than proof of production behavior (`src/hamutay/memory/bridge.py:1-7`, `:284`). No production Yanantin adapter implements this complete port today.

## Identities, edges, and time

### Identity

The caller mints the state UUID before persistence. The bridge mints UUIDs for instance-authored stored records and controls their model/session provenance, preventing the caller from forging those fields (`src/hamutay/apacheta_bridge.py:195-284`; `src/hamutay/tools/graph.py:27-72`).

llm-memory episode references use enrollment/source identity, adapter tokens and versions, and a content digest. The current `TasteOpenAdapter` does not carry Hamut'ay's state UUID into the episode contract (`../llm-memory/llm_memory/adapters.py:305-372`; `../llm-memory/llm_memory/contract.py:161-236`). Consequently, the same cycle can be addressable in both systems without a durable mapping between those identities.

### Edges

The installed Apacheta composition relations are `COMPOSES_WITH`, `CORRECTS`, `REFINES`, `BRIDGES`, `BRANCHES_FROM`, `DOES_NOT_COMPOSE_WITH`, `DISSENTS_FROM`, `CONFIRMS`, `DENIES`, and `DEPENDS_ON`. Framework-created cycle edges use `REFINES`; instance annotations may select any installed relation (`src/hamutay/apacheta_bridge.py:183-225`, `:286-309`; `src/hamutay/tools/graph.py:23`, `:75-131`).

`annotate_edge` validates required values, UUID syntax, and relation membership. It does not validate endpoint existence, ownership, session membership, duplicates, or self-loops (`src/hamutay/tools/graph.py:75-131`). More importantly, the bridge creates annotated edges without supplying model/session provenance or an authorship marker, so an instance-authored annotation is not durably distinguishable from a framework-authored edge (`src/hamutay/apacheta_bridge.py:286-309`).

This is an implementation defect for any shared graph: provenance is necessary before an instance's graph assertion can be evaluated, disputed, or withdrawn.

### Time and filtering

The current path records cycle number, creation timestamp, edge ordering, and—in the local memory substrate—a process-local sequence. It does not provide `valid_from`, `valid_to`, `effective_at`, `as_of`, or another bitemporal model.

Arango open-record queries filter by exact author identity, lineage tag, or top-level field and sort by provenance timestamp. In-session memory search can bound inclusive cycle ranges and then filter by field and substring (`src/hamutay/tools/memory.py:730-903`). These are useful temporal narrowing mechanisms, but creation order is not yet semantic standing or effective time.

Graph traversal currently obtains the composition graph and filters endpoints in Python for each hop (`src/hamutay/apacheta_bridge.py:346-375`). This will not preserve the intended bounded-search advantage at large corpus sizes without backend endpoint and temporal predicates.

## Existing integration seams

### Qhaway

`OpenTasteSession.system_prompt_prefix` is the cleanest seam for a budgeted, read-only projection of curated orientation (`src/hamutay/taste_open.py:1577-1584`, `:1712-1736`). `continuity_curator_context` is a secondary seam explicitly presented as non-authoritative context (`src/hamutay/taste_open.py:1603-1611`, `:2168-2180`).

Inference: qhaway's curated map should remain outside the freely mutable state object. Hamut'ay may retain the projection version or selection receipt, but copying curated claims into model-authored state would flatten their distinct authority and provenance.

### llm-memory

The existing JSONL adapter is the strongest immediate seam for episodic prose. Hamut'ay state UUIDs and llm-memory `episode://` references should remain native identities in their respective systems.

Inference: a bridge should record an explicit mapping or reference node rather than coercing an episode URI into a UUID. The episodic body should be reopened from llm-memory when needed instead of copied into the graph.

### Yanantin/Apacheta

Yanantin already supplies durable record identities, provenance envelopes, append-only composition relations, and Arango persistence. It is consequently the natural substrate for relationships and audit structure, but not the authority that decides which evidence enters a working set or which orientation governs action.

## Additional operational risks

- Resuming a JSONL session rebuilds in-process prior state, but CLI construction does not restore the bridge's prior UUID or prior session identity. Graph continuity can therefore break across restart (`src/hamutay/taste_open.py:1779-1827`, `:2842-2854`; `src/hamutay/apacheta_bridge.py:163-168`).
- Arango and JSONL timestamps are generated separately and are close rather than identical (`src/hamutay/taste_open.py:2139`, `:2188-2204`, `:2597-2600`).
- A bridge persistence exception is non-fatal; JSONL can continue while the graph view becomes partial (`src/hamutay/taste_open.py:2186-2195`).
- Backend cross-session queries do not exclude the current session, so combined searches may duplicate records already present in process (`src/hamutay/tools/memory.py:312-379`, `:859-903`).
- The installed access-control interface presently acts as a hook rather than meaningful per-principal enforcement. Multi-member graph mutation therefore requires an authorization design as well as provenance.

## Conclusion

The useful next step is not to add more branches to `taste_open.py` or to declare one memory implementation canonical. It is to define a narrow cross-project boundary in which Hamut'ay consumes curated projections and episodic references, records why they affected action, and lets Yanantin retain the resulting identities and relationships. The accompanying boundary proposal specifies that experiment.

## Independent-review addendum (2026-07-25)

Claude (Opus 5) independently reviewed this audit and the boundary proposal in `docs/cross-project-memory-boundary-review-20260725.md`. Verification of that review produced three additional present-state findings:

- Yanantin's source tests require `ProvenanceEnvelope.authorship_verified` to exist, default to `False`, remain immutable on a default envelope, and never be set `True` by an agent-reachable Yanantin path (`../yanantin/tests/red_bar/test_single_principal_accretion.py:60-131`). Hamut'ay's currently installed Yanantin/Tiksi environment does not expose that field. A proof cannot honestly persist authorship verification status until dependency compatibility is resolved.
- llm-memory currently enrolls one Codex rollout file and one Claude project-history directory. Five Claude project-history directories exist on this machine, so the current corpus is reciprocal but not machine-complete. Expanding enrollment is deferred from the boundary proof.
- The two enrolled sources express different scopes: Codex enrollment uses the normalized machine identity directly, while Claude enrollment uses UUIDv5 under that machine UUID with the logical collector name `claude-code:qhaway`; its locator is one project-history directory (`../llm-memory/docs/superpowers/plans/2026-07-24-reciprocal-claude-codex-memory.md:14-20`, `:68-90`). Both are stable for their present sources, but machine-wide Codex history and project-scoped Claude history should not be treated as equivalent coverage. Reconciliation belongs to a later corpus-enrollment design.

The review also identifies a qhaway observability gap: an empty projection is not, by itself, distinguishable from an unavailable projection. The revised proposal therefore requires a projection envelope with standing, record count, projection identity, and retrieval time before curated orientation participates in the proof.
