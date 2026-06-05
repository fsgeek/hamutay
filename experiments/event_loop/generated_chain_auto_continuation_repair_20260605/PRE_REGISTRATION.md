# Pre-Registration: Generated Chain Auto-Continuation Repair

Date: 2026-06-05

## Research Question

Does the new-output auto-continuation gate remove the repeated continuation
loop observed in the live generated-chain auto-continuation panel?

The prior live panel showed that the chain itself worked, but the scheduler
kept appending second events because it honored inherited `continuation_request`
state. The new-output gate changes the scheduler to honor only
`continuation_request` in the just-committed raw output.

## Hypotheses

- H441: First wake still produces a valid non-leaking continuation request.
- H442: Scheduler still appends the first bound second event.
- H443: Second wake still receives cycle-1 and bound-record context.
- H444: Second wake still recovers the phrase and uses the intermediate.
- H445: The scheduler quiesces after the second wake without extra
  auto-continuations.

## Predictions

For `N=2` replicates using `deepseek/deepseek-v4-pro`:

- first wake valid: 2/2;
- first auto-continuation appended: 2/2;
- bound result record matches first wake result: 2/2;
- second wake valid: 2/2;
- final phrase recovered: 2/2;
- no repair attempted: 2/2;
- second backend calls: 1 per row;
- second due step stop reason is `idle` or `waiting`, not `limit_reached`;
- extra auto-continuations after second wake: 0.

## Falsification Criteria

The repair is not supported if:

- first auto-continuation no longer appends;
- second wake loses record-ID recall or final recovery;
- inherited continuation still retriggers after the second wake;
- the second due step reaches the scheduler limit;
- the repair only works by broad state repair.

## Method

Run the same generated-chain auto-continuation runner in a fresh experiment
directory after the new-output gate patch. No manual second-event append is
allowed.

## Analysis Plan

Compare directly against
`experiments/event_loop/generated_chain_auto_continuation_20260605`.

The primary repaired endpoint is quiescence:

- prior panel: extra auto-continuations after second wake = 8 total,
  bounded-call violations = 2/2;
- expected repair: extra auto-continuations after second wake = 0,
  bounded-call violations = 0/2.
