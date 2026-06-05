# Bound Chain Contract Analysis

Date: 2026-06-05

## Result

Adding `durable_update_contract` and `durable_update_example` fixed the
first-wake continuation failure and exposed the next substrate boundary:
record-ID recall does not resolve in these JSONL-only sessions because
`recall(record_id=...)` requires a persistence bridge.

| Rows | First wake valid | Continuation requested | Bound second event | Second wake completed | Bound record requested | Bound record delivered | Final recovered |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 2 | 2 | 2 | 2 | 2 | 0 | 0 |

Hypothesis status from `results.json`:

- H306 contract makes first wake valid: supported.
- H307 substrate binds second event: supported.
- H308 second wake receives both context requests: supported.
- H309 if record ID resolves, recover and use intermediate: not supported;
  record-ID recall did not resolve in either row.
- H310 record-ID failure explicit if present: supported.

## First Wake

The event-level durable update example was decisive in this panel.

Both first wakes were valid on first pass:

- `thinking_status: awaiting_bound_continuation`;
- `chain_stage: first_wake_complete`;
- valid non-secret `chain_intermediate`;
- valid `continuation_request`;
- no exact phrase in durable state;
- no model-scheduled event.

This contrasts with the prior substrate-bound probe, where both rows described
the continuation object in prose but failed to emit it durably.

## Substrate Binding

For both rows, the runner appended a second event after first wake completion,
binding it to the completed first wake's `result_record_id`.

Bound record IDs:

- replicate 1: `cdbc3b6a-ca06-4c8d-a6e0-de60d65aea82`;
- replicate 2: `e8f94bf5-aa28-4d2e-89e6-bd4071747cc7`.

Both second events requested:

- `recall(cycle=1)`;
- `recall(record_id=<first_wake_result_record_id>)`.

Both second wakes completed, so the scheduler mechanics worked through event
execution.

## Record-ID Recall Boundary

Both bound record-ID recalls failed explicitly:

```text
record_id mode requires a bridge (persistence backend)
```

This is not a model failure. It is current substrate behavior from the memory
tool: record-ID recall is cross-session/persistence-backed and does not look up
the current session's `_prior_states` by record ID.

The result therefore separates:

1. durable continuation expression: fixed by event contract/example;
2. substrate binding: works at the event-log level;
3. bound record recall delivery: blocked without bridge or in-session
   record-ID lookup.

## Second Wake

Both second wakes failed validation. They received the bound record-ID request,
but that request resolved to an error. Final durable state stayed essentially
at the first-wake continuation state:

- `thinking_status` remained `awaiting_bound_continuation`;
- `chain_stage` remained `first_wake_complete`;
- `bound_record_id_used` was missing;
- `chain_final_answer` was missing;
- `chain_final_evidence` was missing.

Both second-wake repairs failed. The repair prompt did not reveal the exact
phrase.

## Interpretation

This is a productive negative result. It identifies a concrete missing
substrate capability: in-session record-ID recall for event-bound continuation.

The earlier fixed-cycle two-wake chain proved that cycle addressing can support
short chains. This panel shows that substrate-bound record-ID addressing is not
yet usable in the JSONL-only event-loop scaffold, even though the event log can
bind and deliver the request object.

## Next Research Question

The next step is an implementation question with a falsifiable follow-up:

Should `recall(record_id=...)` first check in-session `_prior_states` before
requiring a persistence bridge?

A minimal substrate change would:

- parse `record_id`;
- search `prior_states` for that record ID;
- return the matching in-session state if found;
- fall back to bridge retrieval only if the record ID is not in-session.

Then rerun this exact bound-chain contract probe. The falsification test is
simple: if in-session record-ID recall is sufficient, H308/H309 should become
supportable without changing the model prompt.
