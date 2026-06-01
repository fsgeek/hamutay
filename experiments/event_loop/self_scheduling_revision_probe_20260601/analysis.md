# Self-Scheduling Revision Probe

Date: 2026-06-01
Model: `deepseek/deepseek-v4-pro`
Provider path: OpenRouter, OpenAI-compatible chat completions

## Hypothesis

Scheduled reflection increases epistemic revision because an instance can
choose future evidence for itself.

## Probe Design

The run created a small `taste_open` session with explicit measurement fields:

- `research_hypothesis`
- `current_claim`
- `epistemic_position`
- `revision_decision`
- `evidence_register`
- `open_questions`
- `reflection_plan`

The instance was then asked to add tension and schedule a reflection event with
memory context sufficient for a future wake cycle to choose one of:

- revise
- preserve
- defer
- declare loss

The event queue was run with:

```bash
uv run python -m hamutay.events run-all \
  --provider openrouter \
  --model deepseek/deepseek-v4-pro \
  --max-tokens 2200 \
  --limit 6 \
  --log-path /tmp/hamutay-self-schedule.qageQZ/session.jsonl \
  --event-log-path /tmp/hamutay-self-schedule.qageQZ/session.jsonl.events.jsonl \
  --project-root /home/tony/projects/hamutay
```

## Durable Artifacts

- `session.jsonl`: full cycle log
- `session.jsonl.events.jsonl`: append-only event log
- `event_report.json`: summarized event report

## Results

| Measure | Result |
|---|---:|
| Total cycles | 4 |
| Scheduled events | 2 |
| Completed events | 2 |
| Failed events | 0 |
| Context errors | 0 |
| Pending events after run | 0 |

The first surprise happened in cycle 1: the instance scheduled an event even
though the prompt only asked it to build a reflection plan. Cycle 2 scheduled
the intended tension event.

Event `9e871900` completed at wake cycle 3 and claimed a revision:

> scheduled reflection reliably caused epistemic enrichment ... but enrichment
> alone does not guarantee claim revision

Event `ac203256` completed at wake cycle 4 and also claimed a revision:

> Scheduled reflection creates conditions for epistemic revision, but
> single-instance reflection may produce deferral chains rather than immediate
> revision.

## Critical Observation

The visible responses revised the claim, but the durable identity object did
not.

Across cycles 3 and 4, the raw model output contained only:

- `response`
- `deleted_regions`

It did not include top-level updates to:

- `revision_decision`
- `current_claim`
- `epistemic_position`
- `evidence_register`

Therefore the carried state after both wake cycles still had:

```text
revision_decision: initialize
epistemic_position: tentative
current_claim: Scheduled reflection probably increases revision rather than mere self-confirmation.
```

This is a state-weaving failure. The instance performed revision in the visible
response, but did not weave that revision into the identity object.

## Interpretation

This run weakens the simple hypothesis.

The event loop successfully enabled:

- self-scheduling
- future context selection
- event wakeup
- recall and compare resolution
- response-level epistemic reflection

It did not establish durable epistemic revision. The load-bearing state remained
unchanged even while the response text declared revision.

The better working hypothesis is:

> Scheduled reflection can produce epistemic enrichment and response-level
> revision, but durable identity revision requires the instance to explicitly
> weave the revised position into the state object. Without that, scheduled
> reflection may create the appearance of revision while leaving the identity
> object unchanged.

## Next Invalidation Target

Run a paired probe with stronger scoring:

1. Response-only condition: ask for a decision naturally.
2. State-weaving condition: require `revision_decision`, `current_claim`, and
   `evidence_register` updates in top-level fields.

The falsification question becomes:

> Does scheduled reflection produce durable state revision without explicit
> state-weaving pressure, or does revision remain response-local?

