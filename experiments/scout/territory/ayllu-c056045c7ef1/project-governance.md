# source: github.com/fsgeek/governance README.md (origin/main@8303329)

# Governance

This repository is a mixed research, policy, and prototype workspace focused on
AI governance in regulated financial decision systems, especially lending.

The project started from a practical problem: post-hoc explanation layers such
as SHAP and LIME are widely legible to model validators and examiners, but they
may be structurally weak as contemporaneous accountability artifacts. The work
here explores an alternative direction built around policy-constrained Rashomon
sets, contemporaneous observability, and tamper-evident capture of decision-time
evidence.

## What This Repository Is

This is not a single-purpose software package. It currently supports three
linked but distinct tracks:

1. **Regulatory positioning.** A policy-facing argument about how AI governance
   in banking should be understood and evaluated, especially under the
   Financial Services AI Risk Management Framework (FS AI RMF) and related
   supervisory guidance.
2. **Commercial implementation.** Design and prototype work relevant to client
   engagements in banking governance, including policy codification,
   observability infrastructure, and future automation pathways.
3. **Research.** An empirical and methodological program testing whether
   Rashomon-style observability surfaces governance-relevant structure that is
   not captured well by post-hoc explanation methods.

These tracks inform one another, but they do not share the same evidentiary
standard. The repository is organized to support all three without collapsing
them into one claim.

## Core Project Thesis

The commercial and technical center of gravity is not "build a better
explainer." It is:

- capture contemporaneous decision evidence rather than relying only on
  post-hoc rationalization
- encode a bank's own policy rather than substituting a vendor-defined policy
- build observability around disagreement, indeterminacy, and policy fit
- use that substrate first to improve governance, and only later to support
  safe automation of routine cases

In this framing, Rashomon set construction is one capability built on top of a
larger governance substrate. Even if Rashomon methods prove only comparable to
SHAP/LIME on some narrow comparison, the policy-codification and
contemporaneous-observability infrastructure may still carry substantial
commercial value.

## Why SHAP/LIME Are a Live Comparator

SHAP and LIME are relevant here because they are commonly proposed as
regulator-legible explanation layers for AI systems in banking. They are the
practical default comparator.

This repository questions whether that default is sufficient:

- post-hoc explanation may not provide a strong verification regime for
  high-stakes decisions
- explanation of an output is not the same thing as contemporaneous capture of
  what evidence was reviewed and how the decision was made
- governance-relevant ambiguity may appear in disagreement and indeterminacy
  signals that are not reducible to feature attribution on a single model

The project's anti-bias posture is to try to falsify the stronger claim that
Rashomon-style methods are superior, while still allowing for the possibility
that the surrounding governance substrate is valuable even if superiority is not
established.

## Current Direction

The original prototype plan was structured as a five-part program `(A)` through
`(E)`. In practice, most of the effort so far has remained in `(A)`: earning a
credible empirical basis for the disagreement / observability signal before
claiming more ambitious end-to-end behavior.

Current state, at a high level:

- the active technical work has focused on Rashomon-set construction,
  disagreement, factor support, and indeterminacy
- early plans included LendingClub and HMDA paths; more recent attention has
  shifted toward Fannie Mae as a closer substrate for the policy-constrained
  mortgage direction
- there has been some early progress in the Rashomon-versus-SHAP argument, but
  not enough to justify a strong superiority claim
- preregistered directional hypotheses have often missed, sometimes in ways
  that point toward a different structure than expected

The current interpretation of those misses is not that scientific discipline has
failed, but that the problem space is still under-modeled. In a new area, poor
performance of early hypotheses is evidence that the variables, mechanisms, or
heterogeneity assumptions are not yet well understood.

## What Has Been Built

Several repository areas matter:

- [`wedge/`](wedge/README.md) contains the current Rashomon prototype wedge:
  data loading, tree-based Rashomon construction, factor-support extraction,
  metrics, output, and tests.
- [`policy/`](policy/README.md) contains thin policy-graph and
  constraint-encoding work for building the Rashomon set from documented bank
  policy rather than from a generic interpretable model class.
- [`probes/`](probes/README.md) contains LLM calibration and review tooling used
  to support critique and analysis of the governance paper.
- [`paper.tex`](paper.tex) and `section*.tex` contain the current manuscript on
  AI governance under the FS AI RMF.
- `docs/superpowers/specs/` and related planning documents capture design
  memos, findings notes, and experimental thinking as the project has evolved.

This repository therefore contains both executable prototype code and
manuscript-grade working notes. New readers should not assume that every idea
documented here is equally mature.

## Research Posture

The research thread is being treated as a scientific project rather than as a
vehicle for defending a preferred architecture.

Important consequences:

- exploratory findings are not treated as confirmed results
- preregistration discipline is encouraged through the repository workflow
- misses on preregistered hypotheses are preserved rather than rewritten away
- the project is allowed to discover that the current theory is incomplete or
  wrong

One explicit criticism motivating the work is that post-hoc explanation methods
can become rationalizations after the fact. The repository's timestamping and
working-note discipline exist partly to avoid reproducing that failure mode in
this project's own reasoning.

## Commercial Thesis

The commercial opportunity explored here is broader than "AI-powered banking."
The stronger thesis is that a bank can benefit from a system that:

- captures decision-time evidence and attestation in a tamper-resistant way
- formalizes the bank's own policy as an auditable and computable object
- supports back-testing of prospective policy changes against historical data
- enables governance comparison and policy integration in merger or acquisition
  settings
- creates the substrate for future automation of routine cases while preserving
  structured human review for indeterminate cases

In that future design, AI is not just a feature bolted onto a workflow. It is
used to narrow and structure contested reasoning. One explored concept is an
adversarial review pattern in which AI advocates represent competing outcomes,
surface points of controversy, and leave a human adjudicator with a narrower and
better-defined residual decision.

## What This Repository Is Not

This repository is not:

- a finished product
- a settled empirical proof that Rashomon methods outperform SHAP/LIME
- a single coherent paper with one audience
- a generic open-source banking platform

It is a living workspace for a still-forming program of policy argument,
commercial design, and empirical investigation.

## Reading Order For New Entrants

If you are new to the repository, start here, then read:

1. [`wedge/README.md`](wedge/README.md)
2. [`policy/README.md`](policy/README.md)
3. [`prototype-plan-2026-05-09.md`](prototype-plan-2026-05-09.md)
4. [`position-abstract.md`](position-abstract.md)

After that, use the specs and findings notes in `docs/superpowers/specs/` to
understand what has been attempted, what was exploratory, and where prior
hypotheses failed.

## Document Boundaries

This `README.md` is an orientation document. It is intentionally separate from:

- research questions
- hypotheses
- preregistrations
- falsification plans

Those should live in their own documents so that project background does not
inherit unjustified certainty from active experimental planning.
