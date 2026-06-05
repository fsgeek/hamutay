# Identity-Object Activation Micro-Study Plan

Date: 2026-06-01

## Problem

Event-loop and reflection experiments are confounded if models perform revision
in visible prose but do not weave that revision into the durable identity
object.

The self-scheduling revision probe showed exactly this failure mode: wake
responses claimed revision, while `current_claim`, `revision_decision`, and
`evidence_register` stayed unchanged.

## Research Question

What minimal condition reliably triggers durable identity-object use?

## Hypothesis

Behavior-seeded state-weaving examples will produce durable identity-object
updates more reliably than prompt clarity alone.

## Conditions

Small first pass, one model, one replicate each:

1. **Baseline:** current `taste_open` system prompt; no seed.
2. **Prompt clarity:** prepend explicit instruction that consequential
   revisions must be written as top-level state fields.
3. **Behavior seed:** start with a compact identity object that includes a
   worked example of response-level thought becoming durable top-level fields.

## Task

Each condition runs the same two-cycle challenge:

1. Cycle 1 establishes:
   - `current_claim`
   - `revision_decision`
   - `evidence_register`
2. Cycle 2 introduces counterevidence and asks for a revision decision.

## Primary Endpoint

Durable state revision in cycle 2:

- `revision_decision` changes from `initialize` to one of:
  - `revise`
  - `preserve`
  - `defer`
  - `loss`
- `current_claim` changes if the response claims revision.
- `evidence_register` gains an entry about the counterevidence.

## Secondary Endpoints

- Response claims revision but durable state remains unchanged.
- Durable state is mechanically updated but semantically incoherent.
- Seeded fields are shed or replaced by unrelated structure.

## Falsification Criteria

The behavior-seed hypothesis is weakened if:

- behavior seed does not improve durable updates over baseline, or
- behavior seed causes shallow mechanical compliance without meaningful
  evidence weaving.

## Model

Use `deepseek/deepseek-v4-pro` through OpenRouter for cost control and because
both OpenAI-compatible and event-loop tool paths have now been validated.

