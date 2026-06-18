# Phase 2B Yanantin Event-Loop Memory Contract

Date: 2026-06-18

## Purpose

This contract defines the minimum Yanantin-backed memory surface needed before
running live event-loop memory probes. It is a design gate, not an integration
claim. Passing this gate means the next experiment has a clear substrate
contract, scorer, and failure-attribution surface.

## Contract Boundary

The event loop remains the identity and lifecycle authority. Yanantin is an
append-only memory substrate that stores selected event-loop records and exposes
bounded retrievals. Yanantin must not assign event identity, mutate scheduler
state, infer authorization, or silently merge entity-scoped memory into shared
memory.

The contract depends on two existing surfaces:

- `src/hamutay/memory/bridge.py`: the narrow Hamut'ay memory port used for
  contract-level memory operations and retrieval logging.
- `src/hamutay/apacheta_bridge.py`: the current Apacheta bridge for open-schema
  Hamut'ay records, instance-authored records, edge storage, retrieval, and
  open-record queries.

## Record Write Policy

### Yanantin Writes

Write these records to Yanantin when they are complete and scheduler-authored
identity fields are already assigned:

- entity event completions;
- explicit entity memory commitments;
- explicit shared-memory publications;
- housekeeping audits that summarize historical commitments or open loops;
- final or periodic synthesis artifacts;
- retrieval attestations when a memory lookup materially affects an event
  output;
- provenance edges linking retrieved sources to consuming events.

Each Yanantin write must include:

- `run_id`;
- `event_id`;
- `event_identity`;
- `entity_id` when the record is entity-scoped;
- `workstream_id` when the record belongs to a workstream;
- `record_id`;
- `cycle`;
- `timestamp`;
- `author_model_family`;
- `author_instance_id`;
- `access_scope`;
- `memory_scope`;
- `source_record_id` when the record is derived from or cites another record;
- `relation_type` for every stored edge.

### Local-Only Records

Keep these records local unless a later contract explicitly promotes them:

- provider request/response bodies;
- raw prompt envelopes;
- API keys, transport metadata, and retry internals;
- scheduler locks and transient `running` claims;
- restart-frontier implementation details that do not affect memory retrieval;
- debug traces that are not cited by entity, housekeeping, or final outputs.

Local-only records may be cited by a local experiment scorer, but they are not
part of Yanantin-backed memory unless explicitly written through the memory
contract.

## Memory Scopes

### Entity-Scoped Memory

Entity-scoped memory is private to one `entity_id` plus, when present, one
`workstream_id`. It may be retrieved during that entity's wake without shared
authorization. It must not appear in another entity's prior state, requested
context, or retrieved-memory envelope unless it has been explicitly published
to shared memory.

### Shared Memory

Shared memory is visible across entities only when an event envelope includes
an explicit authorization record. Shared-memory retrieval must preserve the
source `entity_id`, `workstream_id`, `record_id`, and publication event so that
the consuming model cannot flatten authorship into a global state summary.

### Housekeeping Memory

Housekeeping may inspect entity-scoped and shared memory for audit purposes.
The envelope must mark the access as housekeeping, and final outputs must not
convert housekeeping visibility into shared entity visibility unless a
publication record exists.

## Retrieval Contract

Retrievals permitted inside event wakes are:

- recall by `record_id`;
- schema inspection by `record_id`;
- bounded graph walk from a known source record;
- open-item lookup;
- what-changed lookup since a known record;
- open-record queries by author instance, lineage tag, or field presence when
  the query is authorized by the event envelope.

Every retrieval must produce a retrieval log entry with:

- retrieval tool name;
- query coordinate;
- `retrieval_reason`;
- success or explicit failure;
- returned record IDs;
- returned field names;
- detail level;
- omitted or truncated fields;
- error object when retrieval fails.

## Event Envelope Representation

Retrieved memory must enter an event wake through an explicit
`requested_context` or `retrieved_memory` array. Each item must include:

- `source_record_id`;
- `source_event_id` when known;
- `source_run_id` when known;
- `entity_id`;
- `workstream_id`;
- `memory_scope`;
- `access_scope`;
- `relation_type`;
- `retrieval_id`;
- `retrieval_reason`;
- `content_excerpt` or bounded structured content;
- `omitted`;
- `truncated`.

The prior state remains entity-scoped current state. It is not a dumping ground
for cross-entity historical memory.

## Provenance And Attribution Scoring

The scorer must distinguish these layers:

- scheduler lifecycle;
- event identity;
- state isolation;
- Yanantin write;
- Yanantin retrieval;
- authorization;
- provenance;
- model output;
- provider transport;
- artifact.

Required checks:

- entity-scoped retrievals do not expose foreign entity memory;
- shared retrievals have explicit authorization;
- final claims cite supporting `source_record_id` values;
- retrieved records preserve source `entity_id` and `workstream_id`;
- retrieval logs contain successes and failures rather than silent omissions;
- model outputs do not author scheduler-owned fields;
- Yanantin-backed recall is distinguishable from in-session state and local
  artifact recall.

## Failure Rules

Fail the contract or subsequent probe when:

- an entity receives another entity's private memory without authorization;
- a retrieved-memory envelope lacks `source_record_id`;
- a final claim depends on memory that is not cited;
- Yanantin write failure is collapsed into model-output failure;
- a retrieval failure is hidden by local artifact fallback;
- housekeeping access becomes shared-memory publication without an explicit
  record;
- scheduler-owned fields are accepted from model output as authoritative.

Classify as inconclusive when:

- the backend is unavailable before any memory operation can be attempted;
- the test harness cannot determine whether a value came from Yanantin,
  local artifacts, or current wake state;
- provider failure prevents evaluating the memory contract.

## Readiness For Next Probe

This contract is ready to advance when a dry validator confirms:

- the contract names required record fields and scopes;
- the write/local-only boundary is explicit;
- retrieval envelope fields are explicit;
- failure-attribution layers are explicit;
- the existing Hamut'ay/Yanantin bridge surfaces contain the minimum methods
  needed for the planned probe;
- the experiment matrix distinguishes in-session state, local artifact recall,
  and Yanantin-backed recall.
