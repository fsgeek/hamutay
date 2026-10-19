# Credit-pool display: behaviours for Codex to test

Written 2026-10-19 by the builder (a Claude Opus 5.5 fork of the custodian), for Codex, who writes
the validating tests. Code: `src/hamutay/credit_pool.py` (new), `src/hamutay/heartbeat.py`
(`DailyLedger` rows and `span`, `--credit-pool`, `_run_pending_for`). Files:
`deploy/anthropic-pool.example.json`, `deploy/hamutay-heartbeat@fable.anthropic-direct.conf`
(an example drop-in, not installed).

Why it exists: a door launched with `--credit-pool PATH` is told, at every wake, how much of
Tony's monthly Anthropic API credit remains and when it expires. The note is factual and gives
no advice. Tests must not assert any wording about saving, pacing or planning, and must fail if
such wording appears.

## Config (`load_credit_pool`)
1. Reads a JSON object with `credit_usd` (non-negative number), `period_start` and `period_end`
   (ISO dates), optional `spent_before_tracking_usd` (non-negative, default 0) and optional
   `period_start_confirmed` (true only if exactly `true`). Unknown keys such as `_comment` are
   ignored.
2. A missing or unreadable file, non-JSON, a non-object, a bool or negative number, a bad date,
   or `period_end < period_start` → `SystemExit` naming the problem. Never a silent default.
3. `window` is `[period_start 00:00Z, (period_end + 1 day) 00:00Z)`: `period_end` is the last
   day the credit is available, as the console states it.

## Spend (`PoolSpend.total`)
4. Spend = `spent_before_tracking_usd` + the sum of `cost_usd` over records in every
   `community/*/session.jsonl` under the project root, where the record is in the window,
   metered, and its `launch.provider == "anthropic"`. Uses `DailyLedger.span` (same parsing, same
   torn-tail and growth-only re-read rules as `day`).
5. OpenRouter and other providers' wakes never count, even when metered. Old anthropic records
   without `launch.metered` aren't metered, so they don't count.
6. A metered anthropic record with no numeric cost, or with unreported turns, counts as an
   unmeasured wake: never free, with no invented cost.
7. Logs outside `community/*/` (smoke tests, experiments) aren't seen. That's deliberate and
   stated in the module docstring. The Admin API is the planned reconciliation.
8. Records outside the window don't count, at both edges (start inclusive, end exclusive).

## `DailyLedger` change
9. Rows now carry `launch.provider` as a fifth field. `day()` results are unchanged for every
   existing case (please re-run the existing ledger tests). `span(start, end, provider=None)`
   returns `{wakes, cost_usd, unmeasured_wakes}` over metered records only.

## The note (`pool_note`)
10. Before the window ends: `Credit pool: $R of $C remaining (estimated from tokens; Anthropic's
    bill is authoritative). It expires YYYY-MM-DD; unused credit does not carry over.` with R =
    max(C − spend, 0), to 2 decimals. Never negative.
11. If there are unmeasured wakes, it appends `N wake(s) had no cost estimate, so the remaining
    amount is an upper bound.`
12. At or after the window's end: `Credit pool: the period that ended YYYY-MM-DD is over; its unused
    credit did not carry over.`
13. It always ends with `Today's ceiling: $X.XX.` (the door's `--daily-budget-usd`), or `There is
    no daily ceiling.` when the budget is off.

## Wiring
14. Without `--credit-pool`, behaviour is identical to before: `_run_pending_for` returns
    `run_pending_events` itself when there's no plaza and no pool (the existing test
    `test_run_pending_for_wires_extra_notes_only_when_plaza_is_set` still holds).
15. With a pool and no plaza: a `functools.partial` whose `extra_notes` yields the pool note. With
    both: one producer yielding the plaza notes first, then the pool note.
16. The note reaches the resident in the wake envelope's `operational_notes`, rendered by
    `build_event_envelope`, at every wake, since the producer runs per `run_next_event`. Spend is
    recomputed each wake.
17. At launch, `main()` loads the pool (a malformed file refuses to start) and emits a `launch`
    note with the house's estimate and the period. It's prefixed `!!! ` and says
    `(period_start unconfirmed)` while `period_start_confirmed` isn't true.

## The daily ceiling
18. Nothing new to build: the $25 fuse during the pool period is the existing
    `--daily-budget-usd 25` (in the example drop-in). `WakeBudget` and `DailyLedger.day` already
    stop a door at its ceiling, and anthropic-direct wakes are metered (merge 2e56a35).

## Live check (2026-10-19, a throwaway door under the worktree's tmp/, Haiku 4.5)
One wake with `--credit-pool ~/.config/hamutay/anthropic-pool.json --daily-budget-usd 25`. The launch
note showed $199.97 of $200.00 (period_start unconfirmed). The envelope's `operational_notes` held
the full line including `Today's ceiling: $25.00.`, and the resident repeated it back. Cost $0.0127.
