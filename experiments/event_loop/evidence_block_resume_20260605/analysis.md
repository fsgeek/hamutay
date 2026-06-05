# Analysis: Evidence-Block Resume

Date: 2026-06-05

## Result

The deterministic smoke passed all preregistered checks:

- H541_request_append_only_and_linked: true
- H542_fulfillment_append_only_satisfies_request: true
- H543_fulfilled_evidence_creates_resume_event: true
- H544_summaries_distinguish_open_and_fulfilled: true

## Findings

The blocked source wake stayed lifecycle-complete. The policy disposition recorded
`ask_external_evidence` with classification `evidence_blocked`, preserving the
missing evidence and linking to the source event, wake cycle, and result record.

Before fulfillment, the event summary reported one open evidence request, zero
fulfilled evidence requests, and no pending resume event. After fulfillment, the
summary reported zero open evidence requests, one fulfilled evidence request, and
one runnable pending resume event.

The fulfillment record preserved the external evidence payload and source. The
resume event linked to both `resumes_evidence_request_id` and
`resumes_evidence_fulfillment_id`, recalled the blocked wake result record, and
included `evidence_context` containing JSON copies of the evidence request and
fulfillment.

No lifecycle anomalies, context errors, or outcome warnings were reported.

## Interpretation

The scheduler can now represent evidence-blocked work as a resumable data path:
blocked wake -> evidence request -> evidence fulfillment -> pending resume event.
This is more than observability; it gives the loop a structured way to continue
work after an external information gap has been satisfied without rewriting the
original completed wake.

The result is still deterministic. It validates the substrate and summary/report
semantics, not yet whether a live model will correctly consume `evidence_context`
and revise a previously blocked task.

## Caveats

`evidence_context` is currently scheduler-side context, not a standard memory tool
result. A live wake must show whether models treat it as actionable evidence or
ignore it in favor of the recalled blocked result.

The smoke used a single request and fulfillment. It does not yet test multiple
open requests, conflicting fulfillments, partial fulfillments, or stale evidence.

## Next Research Move

Run a live evidence-block resume panel: create an evidence-missing first wake,
append a request and fulfillment, schedule the resume event, then verify whether
the model uses the supplied external evidence to complete or revise the blocked
task.

## Verification

- `python -m py_compile src/hamutay/events.py tests/unit/test_events.py`
- `uv run pytest tests/unit/test_events.py -q`
- `uv run pytest tests/unit/test_events.py tests/test_taste_open.py -q`
- `uv run python experiments/event_loop/evidence_block_resume_20260605/run_evidence_block_resume.py`
