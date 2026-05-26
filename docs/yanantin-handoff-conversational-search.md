# Yanantin Hand-off: Conversational-Channel Full-Text Search

**Date:** 2026-05-24
**Requesting project:** Hamutay (conversational memory — deliberate transcript recall)
**Delta:** One new abstract method on `ApachetaInterface` (`search_open_text`), backed by an ArangoSearch view in the arango backend, a substring fallback in the memory backend, and `NotImplementedError` in duckdb. No new write methods. Conversational turns persist via the existing `store_record` (hamutay-side `store_turn`).

---

## Motivation

The taste_open tensor is lossy **by design** — the agent composts. `search_memory`
searches the persisted tensor (`store_open_state`), so it faithfully surfaces only
what the tensor *kept*. It cannot surface what the tensor let go.

This produced a concrete failure (KIMI K2.6, session `taste_open_20260512_185846`):
the term "Boltzmann brain" was discussed across cycles 44, 47, 49 — present in
`user_message`/`response_text` every time — and was **never encoded into any tensor
field**. Call it *conversational evaporation*: live content, salient enough to
discuss three times, that never crossed the projection boundary into memory. When
the agent later searched `search_memory("Boltzmann brain")`, it found exactly one
hit — its own prior search query, captured in `_activity_log`. A Boltzmann-brain
loop in the retrieval layer: a fluctuation with the appearance of memory and no
encoded substrate behind it.

The agent today has tools over the curated tensor only. It cannot distinguish
"I never knew this," "I knew it and let it go," and "we discussed it but I never
encoded it." That is the difference between amnesia and humility, and the instance
deserves the latter.

Per the observability principle (`agent composts, observer hoards`, 2026-05-22):
the conversation transcript is the observer's hoard. This hand-off lets the agent
*query that hoard deliberately* — without re-feeding it into the tensor it re-reads
each cycle. It is also the only channel where certain acts live: permission-asking,
hedges, speech-acts of carefulness never appear in the tensor or the tool log. To
study carefulness, the conversation channel must be searchable.

---

## Design principles (the invariants this hand-off must not violate)

1. **Two channels, never mixed.** Tensor (curated; `search_memory`) and conversation
   (episodic; this hand-off) are distinct retrieval surfaces. They get **distinct
   tools** so the agent always knows which one it is consulting. Folding conversation
   content into the tensor is forbidden (see #2).

2. **Ephemerality invariant.** Retrieved conversational content is a *this-cycle tool
   result* — sheddable like a bash output — and is **never written into the tensor**
   (`_state` / `_prior_states`). In this system the RAG curse is not only "too much
   returned per call"; it is *cross-cycle accumulation*: any transcript that lands in
   `_state` gets re-fed into the prompt every subsequent cycle, re-introducing the
   hoarding the context discipline exists to prevent. The guard is ephemerality, not
   just volume.

3. **Deliberate recall.** Search returns *address + snippet*, never full turns.
   Reading a full turn is a separate, deliberate `recall(record_id=…)`. Search
   without a trigger is just search; the effort cost is the point. This mirrors the
   involuntary/voluntary memory architecture — involuntary surfacing is the catalyst,
   voluntary traversal is the act.

4. **One index, one predicate.** An ArangoSearch view serves both intra- and
   inter-session search: filter on `author_instance_id` for intra-session, drop or
   widen the filter for inter-session. No separate code path per scope.

---

## Scope

### Hamutay-side (no Yanantin change required)

- **`bridge.store_turn(session_id, cycle, user_message, response_text, tensor_record_id)`** —
  builds an open record tagged `hamutay-transcript`, carrying the two text fields,
  `cycle`, and a link to the tensor record's UUID; persists via the existing
  `store_record`. Called each cycle in `_exchange_impl` alongside `store_open_state`.
  *Prerequisite: the view can only index what is stored, and transcript turns are not
  in Apacheta today (`store_open_state` persists only the tensor).*

- **New memory tool `search_conversation(query, scope?, limit?)`** — routes to the new
  bridge query; returns `address (record_id, cycle, session) + snippet`, ranked.
  Distinct from `search_memory` by design (principle #1).

- **Companion guard (independently shippable, NOT blocked on Yanantin):** exclude
  `_activity_log` and other `_`-prefixed framework fields from `search_memory`'s
  searched fields. This stops the self-pollution loop where the agent's own search
  queries become future "memory" hits. See *Companion fix* below.

- **Full-turn read reuses existing `recall(record_id=…, field=…)`.** No new fetch
  tool. `recall` returns content as a per-cycle tool result, honoring principle #2.

### Yanantin-side (this hand-off)

One new abstract method on `ApachetaInterface`, backed by an ArangoSearch view.

| Method | Purpose |
|---|---|
| `search_open_text(query, author_instance_id, lineage_tag, limit)` | Full-text search over text fields of open records; optional filter by session and/or lineage tag; ranked. |

---

## Signature (copy into `src/yanantin/apacheta/interface/abstract.py`)

Append in a new section `# ── Open-Record Full-Text Search ──`:

```python
    # ── Open-Record Full-Text Search ─────────────────────────────
    # Full-text search over the open-records collection, backed by an
    # ArangoSearch view in the arango backend. Added for hamutay's
    # conversational-channel recall (deliberate transcript search).

    @abstractmethod
    def search_open_text(
        self,
        query: str,
        author_instance_id: str | None = None,
        lineage_tag: str | None = None,
        limit: int | None = None,
    ) -> list[tuple[UUID, float, dict[str, str]]]:
        """Full-text search over the text fields of open records.

        Returns (record_id, score, snippets) tuples, ranked by relevance
        (descending). `snippets` maps matched field name → a short excerpt
        around the match for display; callers address full content by UUID
        via get_record(), they do not parse the model.

        Filters (both optional, ANDed when both present):
        - author_instance_id: restrict to records whose provenance envelope
          carries this id. Omit for cross-session search.
        - lineage_tag: restrict to records carrying this lineage tag (e.g.
          "hamutay-transcript" to scope to conversational turns).

        Filtering is conventional, not structural — records lacking the
        probed envelope/tag are not matched, not raised on. limit applied
        after ranking; None means no limit (bounded by the backend's view).
        """
        ...
```

---

## Backend obligations

### Arango backend — full implementation (the point of this hand-off)

- **An ArangoSearch view** over the open-records collection, indexing the conversational
  text fields (`user_message`, `response_text`) with a text analyzer.
  - **Analyzer:** yanantin's call. Requirements: case-insensitive, stemmed, so
    `"boltzmann brain"` matches `"Boltzmann brains"` — the regression that motivated
    this. Multilingual tokenization is a stated goal; if a single analyzer cannot
    cover it, document the chosen language(s) and leave the rest as follow-up.
  - **Filter fields:** `provenance.author_instance_id` and `lineage_tags` must be in
    the view under an identity/keyword analyzer so `SEARCH` can filter on them
    without tokenization.
  - **Query:** `SEARCH ANALYZER(TOKENS(@query, …) …)` (or `PHRASE`) over the text
    fields, ANDed with the filter predicates when present; `SORT BM25(doc) DESC`;
    `LIMIT @limit`.
  - **Snippets:** native ArangoSearch offset/highlight, or a substring window around
    the first match (as `search_memory` does today). Bounded length.
- Reuse the obfuscator field-path / collection-name helpers established in the
  open-record-queries hand-off.

### Memory backend — substring fallback (honest, degraded)

Case-insensitive substring over the same text fields, with the same filters. No
stemming/multilingual — the fallback exists for tests and dev, not parity. Mark the
stemming acceptance test arango-only (see contract).

### DuckDB backend — explicit `NotImplementedError`

`NotImplementedError("DuckDB open-record full-text search deferred. Use Arango or memory backend.")`.
Consistent with the open-record-queries deferral.

---

## What gets indexed (the non-obvious prerequisite)

A view can only index fields that are stored. `store_open_state` persists the **tensor**;
`user_message`/`response_text` reach Apacheta only once the hamutay-side `store_turn`
writes transcript records. The view indexes the text fields on those records;
the filter fields (`provenance.author_instance_id`, `lineage_tags`) come from the
standard envelope.

**Decision for yanantin — collection placement:**
- *Recommended:* same open-records collection, transcript turns tagged
  `hamutay-transcript`; the view's `SEARCH` scopes to transcript records via the tag
  filter. Unifies with existing open-record queries and the prior hand-off's surface.
- *Alternative:* a dedicated transcript collection — cleaner separation, more Yanantin
  surface (new collection, new view scoping). Yanantin's call; the Hamutay consumer is
  indifferent as long as `search_open_text` honors the `lineage_tag` filter.

---

## Acceptance criteria (contract, expressed as tests)

Behavior the implementation must satisfy. Packaging (files, fixtures, arango skip
guards) is the test author's call.

```python
def test_search_open_text_roundtrip():
    # Two turns stored; a term in one is found, returns its UUID + a snippet
    # for the matched field.

def test_search_open_text_intra_session_filter():
    # Term present in turns of s1 and s2; author_instance_id="s1" returns
    # only s1's record(s).

def test_search_open_text_inter_session():
    # Same setup, no author filter → both sessions' records returned.

def test_search_open_text_lineage_tag_scopes():
    # A tensor record and a "hamutay-transcript" record both contain the term;
    # lineage_tag="hamutay-transcript" returns only the transcript record.

def test_search_open_text_stemming_case():  # arango-only
    # query "boltzmann brain" matches a turn containing "Boltzmann brains".
    # The motivating regression. Memory backend may skip/xfail this.

def test_search_open_text_ranking():
    # A turn with the term in both fields / multiple times ranks above a
    # single-mention turn (score descending).

def test_search_open_text_snippet_present_and_bounded():
    # Each result carries a non-empty snippet under a max length.

def test_search_open_text_memory_substring_fallback():
    # Memory backend matches exact case-insensitive substring.

def test_search_open_text_duckdb_not_implemented():
    with pytest.raises(NotImplementedError):
        backend.search_open_text("anything")
```

### Hamutay-side ephemerality test (in hamutay's suite, not yanantin's)

```python
def test_conversational_recall_does_not_enter_tensor():
    # After search_conversation + a recall of a full turn, the next cycle's
    # _state contains no transcript text. Retrieved content lives only in the
    # per-cycle tool result. (Pairs with the _activity_log fingerprint fix.)
```

---

## Companion fix (Hamutay-side, independently shippable)

Independent of the Yanantin work and worth landing immediately:
`search_memory` currently searches **all** state fields, including `_activity_log`
(taste_open.py:1216 stuffs it into `_state`). The agent's own search queries thus
become matchable "memory," so a search for X retrieves the prior search *for* X — a
self-pollution loop that manufactures false-positive recall. Fix: exclude
`_activity_log` (and `_`-prefixed framework fields) from `search_memory`'s default
searched fields in `_match_in_session` / `_match_cross_session` (memory.py). This is
the read-side complement to the known Pydantic `_`-prefix silent-drop boundary bug.

---

## Non-goals (explicit)

- **No semantic / vector search.** v1 is lexical (BM25). Embeddings are a later,
  separate conversation.
- **No folding transcript into the tensor.** Forbidden by the ephemerality invariant.
  This is a *query* surface over the hoard, not a memory promotion.
- **No new write method on Yanantin.** `store_record` is sufficient; `store_turn` is a
  hamutay-side convenience over it.
- **No phone-home / cross-machine.** Local Arango only.
- **No tool-result sidecar in this hand-off.** The diaspora-note sidecar (full tool
  results joined by `result_hash`) is the same hoard family and will reuse this view,
  but is scoped separately.

---

## Reference: hamutay-side consumer

`apacheta_bridge.py` gains `store_turn(...)` (a thin `store_record` wrapper) and a
`search_conversation(...)` pass-through to `search_open_text`. A new memory tool
`search_conversation` exposes it to the instance; full-turn reads reuse `recall`.
A yanantin maintainer does not need the hamutay tool code to implement this hand-off —
the contract above is sufficient.

Predecessor hand-off: `docs/yanantin-handoff-open-record-queries.md` (the discovery
queries this builds on).

---

## Commit identity

Yanantin commits author as `yanantin@wamason.com`, `Tony Mason`, signed. Match that —
do **not** use hamutay's email.

```bash
cd /home/tony/projects/yanantin
git -c user.email=yanantin@wamason.com -c user.name="Tony Mason" \
    -c user.signingkey=<yanantin key> commit -S -m "..."
```

---

## Suggested commit sequence (yanantin)

1. `feat(interface): add search_open_text abstract method` — abstract method only.
2. `feat(memory backend): search_open_text substring fallback` — memory impl + tests.
3. `feat(arango): search_open_text via ArangoSearch view` — view definition, analyzer,
   AQL query, impl + tests.
4. `feat(duckdb): search_open_text raises NotImplementedError (deferred)`.

Each commit leaves the suite green.
