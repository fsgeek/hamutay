# Evidence-Block Resume Pre-registration

Date: 2026-06-05

## Research Question

Can the Hamut'ay event-loop sidecar turn an `ask_external_evidence`
policy disposition into a resumable blocked-work record, then create a pending
resume event once external evidence arrives?

This is a deterministic substrate question. It follows the live
policy-boundary disposition panel, where evidence-blocked model output was
captured as a first-class `policy_disposition`.

## Motivation

The scheduler can now observe that a wake is evidence-blocked. The next control
loop capability is management of that blocked work:

- preserve what evidence was missing;
- record that the work is blocked without altering the completed wake;
- accept later evidence as an append-only fulfillment;
- create a resume event bound to the original blocked wake and fulfillment.

This moves the loop from "notice blocked work" to "manage blocked work".

## Hypotheses

### H541: evidence request records are append-only and linked

Given an `ask_external_evidence` disposition with missing evidence, the sidecar
will append an `evidence_request` record linked to the source event,
disposition, and result record.

Falsification: the request is not append-only, lacks source linkage, or loses
the missing evidence list.

### H542: evidence fulfillment is append-only and satisfies the request

Given an evidence request, the sidecar will append an `evidence_fulfillment`
record containing supplied evidence and mark the request as fulfilled in the
summary without changing the original completed wake.

Falsification: fulfillment mutates lifecycle status, loses evidence content, or
cannot be associated with the request.

### H543: fulfilled evidence can create a resume event

Given a fulfilled evidence request, the substrate will create a pending resume
event whose requested context includes the blocked wake record and the evidence
fulfillment record.

Falsification: no resume event is created, the resume event lacks evidence
context, or it is not linked to the original evidence request.

### H544: summaries distinguish open and fulfilled evidence requests

`summarize_event_log` will report evidence request counts, open/fulfilled
counts, and recent request/fulfillment records separately from lifecycle
statuses.

Falsification: open and fulfilled requests collapse into ordinary idle,
lifecycle status counts are polluted, or summary data omits request state.

## Conditions

This experiment is deterministic and substrate-only.

Flow:

1. Create a completed wake.
2. Append an `ask_external_evidence` policy disposition with one missing
   evidence item.
3. Build an evidence request from that disposition.
4. Append evidence fulfillment with an external source payload.
5. Build and append a resume event that includes context for:
   - the blocked wake result record;
   - the evidence fulfillment record.

## Primary Measures

- evidence request count
- open evidence request count before fulfillment
- fulfilled evidence request count after fulfillment
- request linkage to source event, disposition, and result record
- fulfillment linkage to evidence request
- fulfillment payload preservation
- resume event pending status
- resume event requested context
- lifecycle status counts
- lifecycle anomaly count

## Expected Results

I expect all hypotheses to pass. The most likely design issue is the shape of
resume context: current requested-context validation only supports memory-tool
requests, so the first implementation may need a sidecar-specific context
record or a small extension to event context validation.
