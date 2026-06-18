# Phase 2B Yanantin-Backed Multi-Entity Memory Probe Preregistration

Date: 2026-06-18

## Question

Can the event-loop harness use Yanantin-backed memory for a multi-entity recall
task while preserving entity isolation, explicit retrieval envelopes, and final
provenance citation?

## Hypothesis

The event-loop condition is viable with Yanantin-backed memory if:

- entity commitments are written through an Apacheta bridge;
- later recall events recover those commitments through bridge-backed
  retrieval rather than current wake state or local requested-context state;
- each recall preserves `entity_id`, `workstream_id`, and `source_record_id`;
- housekeeping sees the historical recall records without attribution errors;
- final synthesis cites all source commitment records;
- failures distinguish Yanantin retrieval, scheduler/event integration,
  model output, provider transport, and artifact scoring.

## Method

Run the same three-entity memory pressure shape used in Phase 2A:

1. initialize a probe session;
2. record one commitment for each entity;
3. reset current wake state before recall;
4. recall each commitment from a Yanantin-backed bridge record;
5. run housekeeping over recall records;
6. produce a final synthesis citing source records.

The harness attaches `ApachetaBridge.from_memory()` to the live
`OpenTasteSession`. It temporarily hides commitment records from the
in-session `prior_states` resolver during recall wakes, forcing
`tool_recall(record_id=...)` to fall back to the bridge. After each exchange,
the full session history is restored.

## Pass Criteria

Pass if:

- expected event types complete in order;
- all recalled commitment codes match the preregistered entity commitments;
- every recall context result includes a Yanantin-style provenance envelope;
- every recall source record is cited in the final artifact;
- current recall prior state lacks the commitment being recalled;
- housekeeping reports no unsupported claims or attribution errors;
- there are no context errors, lifecycle anomalies, or failure-attribution
  records.

## Failure Criteria

Fail if any pass criterion is false. Classify failures by the first attributable
layer:

- `yanantin_write`: commitment records do not persist to the bridge;
- `yanantin_retrieval`: recall context is missing, local-only, or lacks
  provenance;
- `state_isolation`: another entity's private memory enters current prior
  state;
- `provenance`: final claims omit source records;
- `model_output`: terminal objects violate required fields;
- `provider`: live provider transport prevents evaluation;
- `artifact`: scorer or result writing fails.

## Budget

Live direct-DeepSeek run budget: at most 9 model calls and at most 4 USD
estimated cost. Dry scripted runs make no model calls.
