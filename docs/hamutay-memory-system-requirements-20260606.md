# Hamut'ay Memory System Requirements

Date: 2026-06-06

## Purpose

This document captures Hamut'ay's requirements for the memory system it needs
from Yanantin/Llika/Apacheta.

Hamut'ay's core problem is working-set management for bounded-context
transformers. The memory system should therefore not be treated as generic RAG
over old text. It should be an episodic, provenance-rich, graph-addressable
substrate that helps a transformer inspect what information exists, retrieve
bounded working material, preserve uncertainty, bind recall to scheduled
cognition, and audit what was retrieved, ignored, or lost.

## Architectural Position

The identity/work-state object is not the memory system.

The state object should carry the active working set: current commitments,
open questions, declared losses, retrieval intentions, relation state, and
short pointers. It should not be forced to carry the whole archive, the whole
index, or every detail that might matter later.

The memory substrate should carry durable episodes, provenance, indexes,
semantic/episodic maps, graph edges, evidence records, and recall surfaces.

## Core Requirements

### 1. Episodic Records

Each meaningful cycle, event, tool result, artifact, evidence request,
fulfillment, scorer result, repair, and state transition should be storable as
an episode with structured metadata.

Minimum episode facets:

- who: instance, model, session, author, provider, tool, or scorer;
- what: artifact, state fields, claims, evidence, action, decision, or result;
- when: cycle, event time, logical clock, scheduled time, causal order;
- where: project, run, file, tool surface, memory collection, or context site;
- why: goal, evidence request, retrieval reason, policy rationale, hypothesis;
- how: protocol path, provider path, tool path, validation path, repair path,
  scorer path.

The clock is not incidental. Hamut'ay needs temporal and causal structure, not
only semantic similarity.

### 2. Map Before Recall

The model needs a cheap way to inspect what exists before loading content.

The memory system should expose map/schema calls that can return:

- available records and collections;
- top-level fields;
- field sizes or token estimates;
- episode summaries;
- timestamps and cycles;
- graph neighborhoods;
- claim/evidence/status indexes;
- declared-loss markers;
- confidence or limitation status;
- available retrieval handles.

This lets the model choose what to retrieve instead of flooding the working set
with full records.

### 3. Multiple Retrieval Modes

Hamut'ay needs more than semantic search.

Required retrieval modes:

- exact record recall;
- cycle recall;
- field-level recall;
- temporal window recall;
- graph walk from a known record;
- adjacency/context expansion from a known record;
- semantic search constrained by episodic facets;
- evidence-request and fulfillment recall;
- claim/status recall;
- "what changed since X?" recall;
- unresolved/open-item recall;
- random or serendipitous recall where explicitly requested.

Semantic search should be one mode inside a larger episodic retrieval system,
not the whole system.

### 4. Model-Participatory Indexing

The transformer should be able to participate in shaping future recall.

It should be able to attach or request metadata such as:

- this may matter later;
- recall this if X happens;
- this supersedes that;
- this contradicts that;
- this remains unresolved;
- this was declared lost;
- this is evidence for or against claim Y;
- this belongs to goal Z;
- this should be revisited after event E;
- this should not be loaded unless specifically relevant.

The model should not have unchecked authority to corrupt durable memory, but it
should be a first-class participant in indexing, tagging, retrieval requests,
and loss declarations.

### 5. Provenance And Audit

Every stored and retrieved item must carry provenance.

Storage provenance should include:

- source record ID;
- author/instance ID;
- model;
- provider/protocol path;
- tool or terminal surface;
- cycle and timestamp;
- source file or artifact path when applicable;
- validation and repair status;
- scorer or judge path where applicable.

Retrieval provenance should include:

- retrieval tool;
- query or coordinate;
- retrieval reason supplied by the model or caller;
- cycle/event when retrieved;
- records returned;
- fields returned;
- detail level returned;
- records intentionally omitted or truncated;
- context budget used where available.

The system must make it possible to audit what information was available, what
was actually shown to the model, and what the model did with it.

### 6. Loss And Confidence Tracking

Memory must represent uncertainty and loss explicitly.

Required status concepts:

- supported;
- invalidated;
- uncertain;
- open;
- partial;
- conflicting;
- stale;
- superseded;
- contaminated;
- unscoreable;
- declared lost.

The system should track these at the claim/evidence level where possible, not
only at the document level.

Declared losses are load-bearing. Forgetting should be visible when it affects
future cognition.

### 7. Event-Loop Integration

Memory must work with scheduled cognition.

Required event-loop affordances:

- bind a future wake to a result record;
- resume with specific records, fields, or evidence fulfillments;
- retrieve unresolved evidence requests;
- retrieve all fulfillments for a request;
- retrieve what changed since the last wake;
- retrieve prior policy dispositions;
- retrieve prior declared losses;
- schedule or support "call me when this evidence arrives";
- preserve whether requested context was delivered, missing, truncated, or
  failed.

Hamut'ay's event loop should be able to treat memory records as first-class
inputs to future cognition.

### 8. Context-Budget Awareness

Retrieval should support bounded payloads and selectable detail.

Required detail levels:

- map only;
- provenance only;
- field schema;
- selected fields;
- excerpt;
- structured summary;
- full record;
- graph neighborhood;
- compressed bundle.

The response should make truncation explicit and should expose enough metadata
for the model to ask for the next layer of detail.

### 9. Conflict-Aware Recall

The memory system must not silently collapse disagreement.

When records conflict, retrieval should expose:

- conflicting claims;
- source records;
- timestamps/cycles;
- authors/providers;
- confidence/status;
- declared losses;
- scorer or validation context;
- whether the conflict is resolved, unresolved, or superseded.

Returning a blended answer without surfacing conflict is a memory failure for
Hamut'ay's purposes.

### 10. Stable IDs And Addressability

Hamut'ay needs durable, stable, public-facing IDs that work across tools.

Requirements:

- external record IDs should be stable and recallable;
- internal graph IDs may differ but conversion must be explicit;
- public recall should support the ID shape Hamut'ay tools expect;
- graph traversal can use internal IDs where needed;
- result rows, event logs, hypothesis ledgers, and memory tools should point to
  the same durable records without ambiguity.

ID shape is a systems contract, not a presentation detail.

## Required Tool Surfaces

At minimum, Hamut'ay needs tool surfaces equivalent to:

- `memory_schema`: inspect available structure without loading full content;
- `recall`: retrieve by record, cycle, field, or bounded coordinate;
- `find`: goal-focused search over semantic and episodic facets;
- `walk`: graph traversal from a known record;
- `compare`: compare records, claims, or states;
- `open_items`: retrieve unresolved questions, evidence requests, declared
  losses, and pending commitments;
- `what_changed`: retrieve deltas since a cycle, event, or record;
- `retrieval_log`: inspect what was retrieved, why, and when.

Tool names may change, but the capabilities are required.

## Minimum Viable Memory

A first useful version for Hamut'ay should support:

1. storing event-loop episodes with who/what/when/where/why/how metadata;
2. recalling exact records by stable public ID;
3. inspecting record schemas before content recall;
4. finding records by semantic query plus temporal/status filters;
5. retrieving unresolved evidence requests and fulfillments;
6. graph-walking from an event/result record to related evidence and follow-up
   wakes;
7. recording retrieval reason and retrieval provenance;
8. exposing conflicts and declared losses;
9. returning bounded payloads with explicit truncation;
10. producing audit logs sufficient to reconstruct what the model saw.

## Non-Goals

- Do not treat flat vector search as sufficient.
- Do not force the identity/work-state object to be the whole memory system.
- Do not hide retrieval failures or truncation.
- Do not collapse conflicts into a synthesized answer without exposing the
  underlying disagreement.
- Do not treat missing provenance as acceptable for research use.
- Do not require broad claims about AI identity or autonomy to justify the
  memory substrate.

## Research Questions Enabled

Once the substrate exists, Hamut'ay can test:

- whether model-participatory working-set management improves evidence use;
- whether models retrieve better when given map-before-recall tools;
- whether episodic facets improve over flat semantic search;
- whether declared-loss tracking reduces unsupported claims;
- whether scheduled recall improves long-horizon task continuity;
- whether self-curated state plus episodic memory outperforms self-curated
  state alone;
- whether different models use the memory substrate differently;
- whether error-correction agents can detect and repair retrieval or
  evidence-use failures.

## Summary Requirement

The memory system Hamut'ay needs is:

> an episodic, provenance-rich, graph-addressable memory substrate that lets the
> model inspect the map, request bounded recall, preserve uncertainty, bind
> memory to scheduled events, and audit what was retrieved or ignored.

