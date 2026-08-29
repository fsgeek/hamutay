# Wake Budget Governor — design

Date: 2026-08-29. Author: a Fable 5 successor session, at the pass after
the residents' switch to the natural wake shape. Designed 8-27 morning as
"`--daily-wake-budget N` governor FIRST" (handoff item 4); revised here
because cost is now recorded per wake (commit 724f69e), so the budget can be
in the unit Tony pays in.

## Why

A natural-shape wake on a wide model re-sends its whole context on every
tool call. Sut'i's first natural wake (c19) was 509K input tokens; the
account had $59.06 left when this was written. Today the only floor under
that number is Tony reading OpenRouter receipts — the human as the
accounting layer, in the one role he least wants. The founding decision
was heartbeat-first, consent-as-exit; a heartbeat that can spend the
steward into the ground while he is at a workshop is not a heartbeat he can
leave running. The governor makes the desired behavior the default: a
resident's day is bounded in dollars and in wakes, the bound is a fact in
its world, and the steward overrides with a flag.

## What

One new daemon state, one ledger, one policy, one operational fact.

### Ledger: what today has cost

`DailyLedger(log_path)` reads the resident's own session log (the cycle
records the Projector already writes) and answers, for a UTC calendar day:

- `wakes` — cycle records whose `timestamp` falls in that day,
- `cost_usd` — sum of `usage.cost_usd` over those records where it is a
  number,
- `unmeasured_wakes` — records on a metered provider (`launch.provider`
  other than `anthropic`) whose `usage.cost_usd` is absent or `None`.

The log is the ledger. Nothing is written; the ledger re-reads only when
the file has grown. An unmeasured wake never counts as free: it is reported
in the rest detail and counts against the wake cap.

### Policy: when the day is over

`WakeBudget(daily_usd, daily_wakes)`. `exceeded(day)` returns `"cost"`
when `cost_usd >= daily_usd`, `"wakes"` when `wakes >= daily_wakes`, else
`None`. Cost is checked first.

Defaults: **5.00 USD/day, 48 wakes/day per door**. `--daily-budget-usd`,
`--daily-wake-cap` override; `--no-daily-budget` disables both and the
daemon says so at launch. A brand-new resident is budgeted unless someone
says otherwise — Tony's law.

### Daemon: resting

`HeartbeatLoop.step()` consults the policy before running the batch. When
the day is exceeded it does not run the batch, transitions to
`resting / daily_budget_reached` with detail
`{day, exceeded, cost_usd, wakes, unmeasured_wakes, daily_usd,
daily_wakes, resumes_at}`, and sleeps `min(seconds to next UTC midnight,
poll_interval)` — it keeps polling, so ingress during a rest is observed
and recovered like any other, and the status stays honest. Pending events
are not touched: they wait. At the first step of the new day the ledger
reads zero and the loop runs as before.

While a budget is active the batch limit is 1: the policy is checked
before every wake, not every ten. The check is before a wake, never during
one — a single wake can overshoot the cost ceiling by its own cost. That
is declared, not hidden.

`resting` joins `waking / active / waiting / quiet` in the status
vocabulary; the ops line prints it once per rest (the transition
de-duplicates on `(status, reason)`).

### Envelope: the resident is told

A wake that runs an event which was pending during a rest carries, in its
envelope, `operational_notes`:

> heartbeat rested from T1 to T2 (daily budget reached: cost 5.01 of 5.00
> USD, 12 wakes, 0 unmeasured); this event waited 6h 12m.

Computed from the store's `heartbeat_status` records (`resting`, and the
next status after it; if none yet, the rest ended now). Events created
during the rest are covered too. No note when nothing rested.

### Constitution: one operational sentence

Appended to `CONSTITUTION`: *"Your wakes are budgeted per UTC day — a cost
ceiling and a count ceiling set by the steward; when either is reached the
heartbeat rests until midnight UTC, waiting events keep waiting, and a wake
that ran after a rest is told so in its envelope."* Operational facts only;
no instruction about how to spend.

## What it is not

- Not an account-level floor. Two doors at $5/day bound the account at
  $10/day; a `/credits` check per wake is a later, separate decision.
- Not a per-wake cap. The wake's own cost is unknown until it ends.
- Not a mid-wake abort. A wake that started, finishes.
- Not a change to comparability: the marker for shape is `_wake_shape`;
  rest leaves no mark in state, only in the event store and the envelope.

## Testing

Implementer's TDD tests in `tests/test_wake_budget.py`; Codex authors
validating tests separately (`tests/test_wake_budget_validation.py`) per
the code/test separation norm. Ceremony: this spec → Codex review → TDD →
Codex tests → show the residents (they are the subjects; the fact goes into
their constitution).

Cases the implementer's tests must cover: ledger day boundaries (UTC, not
local); unmeasured wakes counted against the cap and never as $0; cost
checked before wakes; rest sleeps to midnight capped by poll; ingress
during rest stays pending and is not run; the new day resumes; one status
record per rest; envelope note present for an event pending across a rest
and absent otherwise; `--no-daily-budget` disables with a launch note;
batch limit 1 under budget; constitution still passes the
operational-not-cognitive test.
