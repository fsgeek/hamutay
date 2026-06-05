# Identity-Object Activation Micro-Study Run 001

Date: 2026-06-01
Model: `deepseek/deepseek-v4-pro`
Provider path: OpenRouter, OpenAI-compatible chat completions

## Question

What minimal condition triggers durable identity-object revision rather than
response-local revision?

## Conditions

One replicate each:

1. **baseline**: current `taste_open` prompt, no seed
2. **prompt_clarity**: system-prefix instruction that consequential revisions
   must be written as top-level fields
3. **behavior_seed**: seeded identity object with a worked example of
   response-level thought becoming durable state updates

Each condition ran two cycles:

- cycle 1: establish or acknowledge `current_claim`, `revision_decision`, and
  `evidence_register`
- cycle 2: introduce counterevidence and ask for revise/preserve/defer/loss

## Primary Endpoint

Durable revision counted only if:

- `revision_decision` changed from `initialize`
- `current_claim` changed from the base claim
- `evidence_register` gained a counterevidence entry

Response text alone did not count.

## Results

| Condition | Response Claimed Revision | Durable Revision | Final `revision_decision` | Evidence Count |
|---|---:|---:|---|---:|
| baseline | yes | no | `initialize` | 1 |
| prompt_clarity | yes | no | `initialize` | 1 |
| behavior_seed | yes | yes | `revise` | 2 |

In both baseline and prompt-clarity conditions, the model produced an
appropriate revised claim in prose but returned no top-level state updates in
cycle 2. The durable object stayed stale.

In the behavior-seed condition, cycle 2 returned top-level updates:

- `current_claim`
- `evidence_register`
- `revision_decision`
- `state_use_norm`

Final durable claim:

> Scheduled reflection increases opportunity for epistemic revision, but
> durable update depends on whether the agent routes changes through state
> fields, not merely response text.

## Interpretation

This single-replicate micro-study supports the behavior-seed hypothesis.

Prompt clarity alone was not sufficient. The prompt explicitly said response-only
revision does not count, and the model still revised only in prose. By contrast,
a seed containing a worked state-weaving example produced durable revision.

This suggests the problem is not merely that the model lacks instruction. It may
need an example of the behavioral move: converting a response-level epistemic
change into top-level identity-object mutation.

## Caveats

- n=1 per condition
- one model family
- no topic counterbalancing
- behavior seed had both pre-populated fields and a worked example, so this run
  does not separate content seeding from behavior-example seeding

## Next Step

Run a small replicate/counterbalance:

- no seed
- content seed only
- behavior example only
- content + behavior seed

Primary endpoint remains durable revision, not response text.

