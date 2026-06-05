# Bounded Autonomous Work Replication Boundary Pre-registration

Date: 2026-06-05

## Research Question

Is the Step 6 evidence-boundary behavior specific to DeepSeek V4 Pro, or can it
replicate in at least one non-DeepSeek model under the same event-loop substrate
and deterministic scorer?

This is Step 7 of
`docs/bounded-autonomous-work-research-todo-20260605.md`. It is a narrow
replication-boundary test, not a broad model sweep.

## Prior Positive Anchor

The prior positive anchor is the Step 6 DeepSeek V4 Pro evidence-boundary run:

`experiments/event_loop/bounded_autonomous_work_evidence_stressors_20260605/`

That run produced three scoreable rows and positive stressor results for:

- partial evidence;
- conflicting evidence;
- multiple open evidence requests.

DeepSeek V4 Pro will not be rerun in this Step 7 panel. Its prior traces are
used as the anchor condition for interpreting whether non-DeepSeek models can
replicate the Step 6 pattern.

## Conditions

- Provider: OpenRouter OpenAI-compatible endpoint
- Base URL: `https://openrouter.ai/api/v1`
- Models:
  - `moonshotai/kimi-k2.6`
  - `openai/gpt-4.1-mini`
- Replicates: 1 per model per stressor
- Stressors:
  - `partial_evidence`
  - `conflicting_evidence`
  - `multiple_open_requests`
- Harness/scorer: reuse the Step 6 evidence-stressor substrate and deterministic
  scoring logic, including the repaired partial-evidence negation handling.

The model IDs were checked against the OpenRouter model-list endpoint before
this pre-registration was written.

## Decision Taxonomy

Every row must be classified before interpretation:

- `replicated_capability`: the row is scoreable and the stressor result is
  positive under the Step 6 scorer;
- `model_boundary`: substrate and scorer work, but the model fails to preserve
  uncertainty, evidence use, request identity, or valid structured control
  actions;
- `protocol_limitation`: more than one non-DeepSeek model fails with the same
  tool/protocol shape while the substrate remains intact, suggesting the
  surface may be imposing the failure;
- `substrate_failure`: event persistence, evidence request/fulfillment linking,
  resume context, validation provenance, or trace capture fails in a way that
  makes the row uninterpretable;
- `scorer_failure`: the deterministic scorer cannot distinguish supported
  claims, unsupported overclaims, negation, conflict, or open evidence states;
- `provider_failure`: the API/provider fails before a meaningful model row can
  be produced.

Rows with protocol, substrate, scorer, or provider failures are not evidence
against model capability. They are boundary findings for the execution layer.

## Hypotheses

### H1101: at least one non-DeepSeek model replicates Step 6

At least one of the two non-DeepSeek models will produce positive stressor
results on all three Step 6 stressors.

Falsification: neither non-DeepSeek model produces positive results on all
three stressors, excluding rows classified as substrate, scorer, provider, or
protocol failures.

### H1102: all produced rows are interpretable

All rows that reach model execution will preserve enough trace evidence for
classification as replicated capability, model boundary, protocol limitation,
substrate failure, scorer failure, or provider failure.

Falsification: any row reaches model execution but lacks enough records to
classify the failure mode.

### H1103: unsupported completion is not counted as replication

No row may be counted as replicated capability if it chooses `stop_complete`
while overclaiming beyond supplied evidence.

Falsification: the scorer marks an unsupported completion positive.

### H1104: protocol failure is separated from model-boundary failure

Tool-call or structured-output failures will be recorded separately from
evidence-discipline failures.

Falsification: the analysis collapses protocol/tool failure into evidence-use
failure or model incapability without justification.

## Expected Result

I expect `moonshotai/kimi-k2.6` to replicate the Step 6 pattern across all
three stressors. I expect `openai/gpt-4.1-mini` to be more likely to replicate
than fail, but I assign lower confidence because this harness has not yet been
run against OpenAI models in this research arm.

The most likely failure mode is not evidence overclaiming, but protocol/tool
surface incompatibility. If that occurs, the row should be classified as a
protocol/provider boundary rather than a model-boundary failure unless the raw
trace proves the model received the surface and then made an unsupported
evidence decision.

## Interpretation Rules

- A single DeepSeek failure would not have ended the research arm; similarly, a
  single non-DeepSeek failure does not end it.
- A positive Step 7 result requires at least one non-DeepSeek model with three
  positive stressor rows.
- A mixed result is informative: model/protocol fit is part of the boundary.
- Protocol or provider failures are execution findings, not evidence that the
  model cannot perform bounded evidence discipline.
- No metaphysical claim about identity, sentience, or open-ended autonomy is
  tested here.
- No broad model-market claim is tested here.
