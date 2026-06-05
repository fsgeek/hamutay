# Bounded Autonomy DES Analysis

Date: 2026-06-05

## Result

All four preregistered hypotheses passed under deterministic simulated time.

- H77 bounded continuation completes useful work: passed.
- H78 stasis is detected before unbounded continuation: passed.
- H79 recursive scheduling drift is observable: passed.
- H80 strict protocol failure remains bounded and diagnostic: passed.

This does not prove live model autonomy. It establishes a scheduler policy
contract over the real `OpenTasteSession`, `EventStore`, `schedule_event`, and
`run_next_event` path without provider latency or wall-clock uncertainty.

## Scenario Results

### progress_complete

Classification: `complete`

The loop processed two wakes. The first wake changed progress fields and
scheduled one continuation. The second wake changed progress fields again, set
`loop_status` to `complete`, and scheduled no further events.

Observed:

- wake count: 2
- completed events: 2
- pending events: 0
- progress wakes: 2
- max continuations in one wake: 1

This supports the basic bounded-continuation contract: useful continuation can
run, advance state, and terminate.

### stasis_cutoff

Classification: `stasis`

The loop processed two completed wakes that produced no durable progress under
the preregistered progress definition. Both wakes scheduled one continuation,
but the runner stopped after the second no-progress wake.

Observed:

- wake count: 2
- completed events: 2
- pending events: 1
- progress wakes: 0
- no-progress streak: 2

This shows the current policy can stop the loop before unbounded continuation.
It also surfaces a design choice: stasis classification leaves a pending event
in the sidecar. That is observable, but future policy should decide whether
classification should cancel, expire, or annotate pending continuations.

### recursive_drift

Classification: `drift`

The wake made a progress update but scheduled two continuation events in the
same cycle. The runner classified this as drift and stopped without processing
either branch.

Observed:

- wake count: 1
- completed events: 1
- pending events: 2
- max continuations in one wake: 2

The important result is not that branching is inherently wrong. It is that
branching must be an explicit policy mode. Under a single-continuation bounded
loop contract, multiple same-cycle continuations are drift and are preserved as
evidence.

### strict_merge_failure

Classification: `failed`

The wake intentionally returned both an update to `research_findings` and
`deleted_regions: ["research_findings"]`. Strict merge rejected the update.
Accepted state did not advance, the event sidecar recorded failure with context,
and the session JSONL preserved failure classification and protocol recovery.

Observed:

- wake count: 1
- failed events: 1
- accepted state advanced after failure: false
- failure classification logged: true
- protocol recovery logged: true
- protocol recovery candidate rows: 3

This preserves the invariant that failed protocol output is evidence, not live
state evolution.

## Interpretation

The bounded-autonomy scheduler policy is now testable. The research arm has not
run out of questions; it has moved from substrate mechanics into policy design.

The useful next questions are:

1. Pending-event disposition: when a loop classifies `stasis` or `drift`, should
   pending continuations remain pending, be expired, or be annotated as
   suppressed by policy?
2. Branch policy: should multiple continuations be forbidden, or should they
   become an explicit fork/join mode with separate resource budgets?
3. Progress semantics: should progress be field-delta based, curator-scored,
   explicit self-declared, or some combination?
4. Live runtime hardening: once the policy contract is stable, can provider
   execution be supervised with subprocess-level timeout/cancellation so live
   latency does not confound loop behavior?

## Recommendation

Continue the research arm, but do not return immediately to broad live model
sweeps. The next best move is to add a first-class policy action for terminal
classification, likely by appending event-sidecar records that mark pending
continuations as policy-suppressed or policy-expired after `stasis` or `drift`.

That would make the scheduler less like a passive queue and more like an
operating loop with explicit ownership of work it chooses not to run.
