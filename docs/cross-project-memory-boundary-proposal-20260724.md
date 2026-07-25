# Cross-Project Memory Boundary Proposal

Date: 2026-07-24

Status: revised after independent and focused follow-up review on 2026-07-25; proposal for independent adoption; it does not bind qhaway, llm-memory, Yanantin, Hamut'ay, or any ayllu member

## Intent

Enable Hamut'ay to use curated orientation and episodic evidence during autonomous operation without collapsing their authority, copying their contents into an undifferentiated store, or making one project govern the others.

This proposal defines one narrow proof. It is not a merger plan and does not select a final implementation architecture for Hamut'ay's two existing memory paths.

## Responsibilities

### Qhaway: stewarded orientation

Qhaway owns deliberately curated orientations: descriptive claims, provisional interpretations, commitments, norms, disputes, and their standing. It decides how those records are promoted, acknowledged, disputed, superseded, expired, or withdrawn.

For this proof, qhaway exports a bounded projection in an envelope containing its stable projection identity, standing, record count, and retrieval time. Hamut'ay may use that projection as read-only context. It may not silently rewrite qhaway from working state or episodic retrieval.

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
3. **Honest provenance precedes shared mutation.** Every member-authored record and edge must carry its asserted author instance, model family where applicable, session, timestamp, production mechanism, and authorship-verification status. In the present single-principal substrate, authorship is self-asserted and `authorship_verified` must be `false`. An asserted identity must never be represented as verified identity.
4. **Retrieval is an action.** A receipt records the query or selection reason, corpus and source, episode reference, observed standing, retrieval time, consuming cycle, and outcome.
5. **Discovery is not evidence.** A search result becomes usable evidence only after authoritative open succeeds.
6. **Standing can change.** Later consumers re-open episodic references and re-check curated projection identities, recording current standing. A previous receipt remains an accurate record of what was observed then; it does not freeze current truth.
7. **Absence is explicit.** Unavailable, malformed, withdrawn, unauthorized, or failed retrievals are recorded as outcomes and must not masquerade as empty evidence.
8. **No automatic promotion.** An episode or working-state conclusion does not enter qhaway merely because it affected an action.
9. **Dissent remains first-class.** Conflicting records or interpretations remain attributed and separately addressable; synthesis does not erase them.
10. **Withdrawal limits future use.** Audit receipts may preserve that a reference was consulted, while withdrawn content is neither recopied nor treated as currently available.

## Minimal receipt contract

The proof requires a logical episodic retrieval receipt with these fields; exact storage names are an implementation decision:

- framework-minted receipt UUID;
- consuming Hamut'ay cycle UUID and session identity;
- asserted author instance/model identity and `authorship_verified` status;
- retrieval purpose or decision question;
- normalized query, requested corpus IDs, requested limit, strategy, and match semantics returned by llm-memory;
- llm-memory source IDs and the per-member `indexed_through` boundaries observed in corpus standing;
- opaque episode reference copied from `search_history`;
- returned episode count and selected episode rank;
- `total_matches` on every receipt, using an integer when `total_standing` is `exact` and explicit `null` when `total_standing` is `unknown`;
- `total_standing`;
- standing observed during search and authoritative open;
- retrieval timestamp;
- bounded outcome: used, not-used, unavailable, withdrawn, malformed, unauthorized, or error;
- optional resulting action/state reference;
- interface and schema versions.

The receipt must not contain the episode body, search snippet, raw prompt context, credentials, or private diagnostic payloads.

The minimum proof records the size of the returned episode set and the episode rank selected, making selection loss visible without retaining a second index of every unopened candidate. These values are episode cardinality, not independent conversational-turn cardinality: an adapter may emit several episodes that share one native user turn. The present public result contract does not expose a trustworthy cross-adapter native-turn grouping, so no such count is inferred.

The recorded query, corpus scope, limit, retrieval semantics, and member index boundaries provide a basis for a later comparable rerun without moving candidate ownership out of llm-memory. They do not guarantee exact regeneration: the current `search_history` request cannot query an historical `indexed_through` boundary, and corpus advance, withdrawal, supersession, or strategy change may alter the result. Such divergence is recorded as a standing or retrieval change rather than hidden. A later experiment may justify retaining discarded opaque references, but this proof does not.

Curated orientation requires a parallel projection receipt containing:

- consuming Hamut'ay cycle UUID and session identity;
- asserted author identity and authorship-verification status for the receipt;
- qhaway projection identity, standing, record count, and retrieval time;
- the standing observed when the projection is later re-checked;
- bounded outcome: used, not-used, empty, unavailable, withdrawn, disputed, superseded, expired, unauthorized, or error;
- optional resulting action/state reference;
- interface and schema versions.

The projection body remains a bounded transient input and is not copied into the receipt.

## Preconditions

Before a shared instance may write the proof's graph edge:

1. Resolve the dependency mismatch so Hamut'ay's runtime provenance model exposes immutable `authorship_verified`, defaulting to `false`, consistently with Yanantin's source guards.
2. Repair Hamut'ay's edge persistence so instance-authored edges retain asserted author/session provenance, explicit authorship-verification status, and a marker distinguishing them from framework-created `REFINES` edges.
3. Add adversarial contract checks for invariants 1, 2, and 5: receipts reject copied episode bodies, episode references are never coerced into graph UUIDs, and no search snippet can become evidence without a successful authoritative open.
4. Run those checks as a required remote gate whose omission or failure blocks integration, rather than relying only on prose, local tests, or optional hooks.
5. Validate that both edge endpoints exist.
6. Define the principal authorized to create the edge and the trust domain in which it is visible.
7. Make duplicate and self-loop behavior explicit.
8. Provide backend endpoint filtering so the proof does not depend on loading the entire composition graph.
9. Require a qhaway projection envelope whose standing, record count, projection identity, and retrieval time distinguish a valid empty projection from an unavailable one.

These are correctness conditions, not a general graph-governance redesign.

## One-cycle proof

The initial experiment has one deliberately small path:

1. A Hamut'ay cycle receives a bounded qhaway orientation projection envelope and records a projection receipt.
2. The cycle calls llm-memory `search_history` within one explicitly enrolled corpus for evidence relevant to a stated decision question.
3. It copies one returned `episode_ref` verbatim and calls `open_episode` against the active corpus.
4. On an available authoritative result, Hamut'ay makes or declines one bounded decision.
5. Hamut'ay stores a retrieval receipt and links the consuming cycle UUID to that receipt UUID with complete edge provenance.
6. A later cycle traverses the link, reopens the same opaque episode reference, re-checks the qhaway projection identity, and records whether either standing or availability changed.
7. No qhaway mutation occurs. Any proposed promotion is emitted separately as an attributed candidate for its normal governance process.

The proof succeeds only if the later cycle can establish all of the following without copied episode content:

- which cycle requested evidence and why;
- how many episodes were returned and which episode rank was selected, without interpreting that count as distinct native turns;
- which query, corpus scope, limit, strategy, match semantics, and member index boundaries produced the selection;
- which authoritative episode was opened;
- which corpus/source supplied it;
- what standing was observed at each access;
- which decision followed;
- who authored the receipt and edge;
- that each persisted author identity is asserted rather than verified in the present substrate;
- whether the referenced episodic evidence has since changed standing;
- whether the curated orientation that informed the decision still has the standing observed at use time.

These criteria prove that the boundary can carry evidence and account for its use. They do not prove that retrieving evidence improves decision quality. Decision value is a separate, later experiment requiring an appropriate comparison and outcome measure.

## Failure behavior

- Search failure produces an error receipt only when a stable reference and safe diagnostics can be recorded; it produces no invented episode reference.
- Open failure prevents the search snippet from being used as authoritative evidence.
- An empty qhaway projection is accepted only with an available envelope and a record count of zero; missing or failed projection access is recorded as unavailable or error.
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
- enrolling every Codex or Claude project-history directory on the machine;
- reconciling machine-wide and project-scoped corpus coverage or source identity semantics.

## Questions for independent challenge

Each participant should answer independently before synthesis:

- **Qhaway:** Does a bounded projection preserve the standing, consent, and withdrawal semantics of curated orientation?
- **llm-memory:** Can the episode reference and source standing be reopened reliably without storing content in the receipt?
- **Yanantin:** Which existing record and relation types can represent a retrieval receipt without falsifying their semantics?
- **Hamut'ay:** Can the autonomous loop use the receipt through a narrow port rather than accumulating more responsibilities in `taste_open.py`?
- **Ayllu members:** What information about a member may exist provisionally, what may govern action, and what requires prior consent?

Disagreement should be retained with attribution. Adoption by one project does not imply adoption by another.

## Decision requested after review

The proposal has survived one independent review with the revisions above. After those revisions are reviewed, the next artifact should be an implementation plan for only two bounded work packages:

1. satisfy the provenance-model, edge-provenance, endpoint-validation, and externally required invariant-check preconditions;
2. implement the smallest paired episodic-receipt and curated-projection-receipt proof through an existing narrow port.

No broader reconciliation is authorized by this proposal.
