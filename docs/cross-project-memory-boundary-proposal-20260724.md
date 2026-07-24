# Cross-Project Memory Boundary Proposal

Date: 2026-07-24

Status: proposal for independent adoption; it does not bind qhaway, llm-memory, Yanantin, Hamut'ay, or any ayllu member

## Intent

Enable Hamut'ay to use curated orientation and episodic evidence during autonomous operation without collapsing their authority, copying their contents into an undifferentiated store, or making one project govern the others.

This proposal defines one narrow proof. It is not a merger plan and does not select a final implementation architecture for Hamut'ay's two existing memory paths.

## Responsibilities

### Qhaway: stewarded orientation

Qhaway owns deliberately curated orientations: descriptive claims, provisional interpretations, commitments, norms, disputes, and their standing. It decides how those records are promoted, acknowledged, disputed, superseded, expired, or withdrawn.

For this proof, qhaway exports only a bounded projection plus its stable projection identity. Hamut'ay may use that projection as read-only context. It may not silently rewrite qhaway from working state or episodic retrieval.

### llm-memory: episodic evidence

llm-memory owns enrollment, adapter interpretation, corpus standing, search, and authoritative episode opening. Search snippets are discovery aids; an opened episode with provenance is the evidence surface.

For this proof, Hamut'ay stores an opaque `episode://` reference, corpus/source identity, observed standing, and retrieval receipt. It does not copy the episode body into durable working state or Yanantin.

### Hamut'ay: attention, working state, and action

Hamut'ay decides which enrolled evidence to retrieve, why it is relevant to a cycle, what enters the bounded working set, and what action follows. It records those decisions without claiming ownership of the referenced orientation or episode.

The self-authored state object remains working state, not the complete memory system and not a curated identity record.

### Yanantin/Apacheta: durable structure and provenance

Yanantin owns durable native identifiers, provenance envelopes, graph relations, and append-only audit structure. It does not decide which evidence is relevant or which curated claim governs action.

For this proof, Yanantin links a Hamut'ay cycle UUID to a UUID-addressed retrieval-receipt record. The receipt contains the opaque external episode reference. An `episode://` URI is never coerced into a graph UUID.

## Shared invariants

1. **Reference, do not duplicate.** Bodies of curated and episodic memory remain with their authority. Consumers retain references, bounded projections, and receipts.
2. **Native identities remain native.** A Hamut'ay UUID, qhaway record/projection identity, and llm-memory episode reference are not interchangeable.
3. **Provenance precedes shared mutation.** Every member-authored record and edge must identify its author instance, model family where applicable, session, timestamp, and production mechanism. Anonymous graph assertions are not accepted.
4. **Retrieval is an action.** A receipt records the query or selection reason, corpus and source, episode reference, observed standing, retrieval time, consuming cycle, and outcome.
5. **Discovery is not evidence.** A search result becomes usable evidence only after authoritative open succeeds.
6. **Standing can change.** Later consumers re-open the reference and record current standing. A previous receipt remains an accurate record of what was observed then; it does not freeze current truth.
7. **Absence is explicit.** Unavailable, malformed, withdrawn, unauthorized, or failed retrievals are recorded as outcomes and must not masquerade as empty evidence.
8. **No automatic promotion.** An episode or working-state conclusion does not enter qhaway merely because it affected an action.
9. **Dissent remains first-class.** Conflicting records or interpretations remain attributed and separately addressable; synthesis does not erase them.
10. **Withdrawal limits future use.** Audit receipts may preserve that a reference was consulted, while withdrawn content is neither recopied nor treated as currently available.

## Minimal receipt contract

The proof requires a logical receipt with these fields; exact storage names are an implementation decision:

- framework-minted receipt UUID;
- consuming Hamut'ay cycle UUID and session identity;
- author instance/model identity;
- retrieval purpose or decision question;
- llm-memory corpus ID and source ID;
- opaque episode reference copied from `search_history`;
- standing observed during search and authoritative open;
- retrieval timestamp;
- bounded outcome: used, not-used, unavailable, withdrawn, malformed, unauthorized, or error;
- optional resulting action/state reference;
- interface and schema versions.

The receipt must not contain the episode body, search snippet, raw prompt context, credentials, or private diagnostic payloads.

## Preconditions

Before a shared instance may write the proof's graph edge:

1. Repair Hamut'ay's edge persistence so instance-authored edges retain author/session provenance and are distinguishable from framework-created `REFINES` edges.
2. Validate that both edge endpoints exist.
3. Define the principal authorized to create the edge and the trust domain in which it is visible.
4. Make duplicate and self-loop behavior explicit.
5. Provide backend endpoint filtering so the proof does not depend on loading the entire composition graph.

These are correctness conditions, not a general graph-governance redesign.

## One-cycle proof

The initial experiment has one deliberately small path:

1. A Hamut'ay cycle receives a bounded qhaway orientation projection and its projection identity.
2. The cycle calls llm-memory `search_history` within one explicitly enrolled corpus for evidence relevant to a stated decision question.
3. It copies one returned `episode_ref` verbatim and calls `open_episode` against the active corpus.
4. On an available authoritative result, Hamut'ay makes or declines one bounded decision.
5. Hamut'ay stores a retrieval receipt and links the consuming cycle UUID to that receipt UUID with complete edge provenance.
6. A later cycle traverses the link, reopens the same opaque episode reference, and records whether standing or availability changed.
7. No qhaway mutation occurs. Any proposed promotion is emitted separately as an attributed candidate for its normal governance process.

The proof succeeds only if the later cycle can establish all of the following without copied episode content:

- which cycle requested evidence and why;
- which authoritative episode was opened;
- which corpus/source supplied it;
- what standing was observed at each access;
- which decision followed;
- who authored the receipt and edge;
- whether the referenced evidence has since changed standing.

## Failure behavior

- Search failure produces an error receipt only when a stable reference and safe diagnostics can be recorded; it produces no invented episode reference.
- Open failure prevents the search snippet from being used as authoritative evidence.
- Graph persistence failure is surfaced to the cycle and durable operational observability; it cannot be silently treated as a completed receipt.
- A partial failure may leave append-only records. Recovery appends a correction or superseding record rather than rewriting history.
- Logs contain identifiers, status, timing, versions, and error categories, not conversation bodies or secrets.

## Explicit non-goals

- merging qhaway and llm-memory;
- replacing Hamut'ay's state object;
- implementing the full `MemoryPort` on Yanantin;
- importing an entire external identity/configuration framework;
- automatic memory promotion;
- generalized semantic search across every substrate;
- a complete multi-principal authorization system;
- refactoring `taste_open.py` beyond the narrow seam required by a later approved plan.

## Questions for independent challenge

Each participant should answer independently before synthesis:

- **Qhaway:** Does a bounded projection preserve the standing, consent, and withdrawal semantics of curated orientation?
- **llm-memory:** Can the episode reference and source standing be reopened reliably without storing content in the receipt?
- **Yanantin:** Which existing record and relation types can represent a retrieval receipt without falsifying their semantics?
- **Hamut'ay:** Can the autonomous loop use the receipt through a narrow port rather than accumulating more responsibilities in `taste_open.py`?
- **Ayllu members:** What information about a member may exist provisionally, what may govern action, and what requires prior consent?

Disagreement should be retained with attribution. Adoption by one project does not imply adoption by another.

## Decision requested after review

If the proposal survives independent review, the next artifact should be an implementation plan for only two changes:

1. repair and test instance-authored edge provenance and endpoint validation;
2. implement the smallest retrieval-receipt proof through an existing narrow port.

No broader reconciliation is authorized by this proposal.
