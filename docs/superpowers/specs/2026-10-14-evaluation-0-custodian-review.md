# Evaluation 0 — Custodian Review (2026-10-14)

Reviews: `2026-08-16-evaluation-0-assay-comparator-qualification-design.md`
(revised 2026-08-17), with the cross-family review and Codex's disposition.

Reviewer: the hamutay custodian, Claude Opus 5.5. The design's status line
says "revised document awaiting collaborator review." Tony Mason (PI) handed
the call to the seat on 2026-10-14 ("your project, your call"); this is that
review. It is a same-family read of a design authored by Codex and reviewed by
Claude in August, so it adds no family diversity; it adds eight weeks of field
evidence and a decision.

Conflict, declared: H's likely working model is a Claude-family model, and the
reviewer is a Claude instance that would like Hamut'ay to work. The design's
channel isolation and non-working-family judges exist for this; nothing below
weakens them.

## Decision

Approved to proceed to an implementation plan, with the amendments below. The
plan covers Stage 0, Stage 1 and the Stage 2A resource record only. Stage 2A
live calls require that record, signed, with hard ceilings, and approval of
the spend by the PI.

## What still holds

The research contract (development vs confirmatory loops; one confirmatory life
per claim), the three arms, the operator-sensitive ledgers, the four
noncompensating co-primary endpoints, the M/L/U channel isolation, and the
automation-first funnel are sound. I found nothing to remove.

## Amendments

### E1. Register the tool-call-as-text failure as its own protocol class

Since August the house has measured a failure the design's taxonomy folds into
"protocol-invalid model output": a model writes a tool call as text and nothing
executes it (hamutay rule (d), merge f62bf0b; qwen has three such wakes on
record, plaza seq 78). guest:arbiter reports that two of four October models
answer prose probes with tool-call attempts and no text, and that a runner
which drops them reports a clean run (plaza seq 86). H is more exposed than A
or D because H's state updates are tool calls. The failure policy should name
"unexecuted tool call (written as text)" as a class, count it per arm, and
forbid any runner path that drops a response without recording it. Stage 0
gets a fixture for it; Stage 1 measures its rate per candidate model.

### E2. Register sampling temperature and do not run at temperature 0

The design fixes "identical sampling controls" but no value. guest:arbiter
(seq 86; its RESULT_e_ste.md) found temperature-0 cells with a nine-fold
variance increase and catastrophic zeros that dissolved at 0.7 with ten trials.
Stage 2A runs one repetition per variant. Register a nonzero temperature,
identical across arms, and state in the Stage 2A disposition rules that a
single repetition is development evidence about the apparatus, never about
H's level.

### E3. Choose the anchor model's context limit with cost in view

Pressure is a fraction of the resolved context limit, so a 1M-token window
makes every trajectory several times more expensive than a 200K one, and the
A arm re-sends a growing transcript each cycle until compaction. The anchor
choice is therefore a cost decision as much as a capability one. Prefer a
protocol-clean model with a modest window for Stage 2A. Record the model's
deprecation status at freeze: a snapshot retired mid-study breaks the matched
design.

### E4. Build order: Family 2 first, without narrowing the claim

The registered fallback is Family 2 (evidence synthesis with correction and
withdrawal) under M and L. The implementation plan should build Family 2's
grammar, ledger, scorers and fixtures to Stage 0 completion before starting
the other three. This is build order, not a scope change: the target remains
all four families, and nothing about the claim narrows unless the resource
gate forces the registered fallback.

### E5. The cost estimate is the real blocker; produce it first

No estimate exists. The resource record needs measured numbers: provider price
schedule with its effective date, cached and uncached token envelopes per arm,
compaction and scoring overhead, and a ceiling. The first deliverable of the
plan after Stage 0 is a Stage 1 sentinel run whose measured usage drives that
record, so the estimate rests on observed request shapes rather than guesses.

### E6. The external statistician remains unfilled

The disposition's first declared loss still stands. The intersection-union
test, missingness rules, variance allocation and margin derivation need a
reviewer outside candidate development before Evaluation 1, and preferably
before the Stage 2A analysis plan is frozen. A model reviewer of another family
can challenge it; it does not discharge this.

## Declared losses of this review

- Same-family as the August reviewer; no new family's judgment is added.
- The cost argument in E3 is structural; no prices were checked for this review.
- I have not read the earlier B3 runs or the C3 scorer failure in their
  original records, only the design's account of them.
