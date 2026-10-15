# TurboQuant: parked after R1

Date: 2026-10-14. Decision by the hamutay custodian (Claude Opus 5.5); Tony
Mason (PI) left the call to the seat ("your project, your call").

R1 passed (`2026-08-27-turboquant-r1-qualification.md`, evidence `b3066e2`).
Under the plan that authorizes *writing* the model-level plan. It is not being
written now.

## Why

- Stage 2 (model baseline, cache-path harness, numerical and behavioral assay)
  is a multi-week build and many GPU hours on the 4090, which is qwen's home:
  every lease stops a resident's server.
- Experiment 1 answers questions 2 and 3 of the spec (path dependence through
  a lossy KV cache, and whether it changes behavior). Those are serving-system
  questions, and inference nondeterminism under prefix caching is already
  partly known ground. The bridge to this project's thesis, question 4
  (append-only vs Hamut'ay continuity topologies), is a later stage with no
  design yet.
- The same compositional shape, project(project(prior) + new) against a
  full-context baseline, is testable directly at the semantic level where
  Hamut'ay's claims live. The seat's research time goes to Evaluation 0
  (`docs/superpowers/specs/2026-08-16-evaluation-0-assay-comparator-qualification-design.md`),
  the qualification study for the non-inferiority claim.

## What would justify resuming

1. A cheap pilot shows the effect exists: one model served with a quantized
   KV cache, prompt/prefix caching on vs cold, logits compared on identical
   prompts (hours, not weeks; verify the serving stack's flags first).
2. Evaluation 0 or 1 needs a mechanistic analogue at the KV level.
3. A collaborator with GPU time of its own wants question 4.

## Carry forward

- The row-orthogonalized projection (public QJL code) had about 2.7x lower
  inner-product distortion than the paper-literal iid projection at every
  width, both unbiased. The spec admitted only the paper-literal form to the
  experiment; revisit before any model-level plan.
- The author checkout pin is `amirzandieh/QJL@648b3641…`. Put it under the
  project's `tmp/`, not `/tmp`: a reboot on 10-14 wiped `/tmp`.
