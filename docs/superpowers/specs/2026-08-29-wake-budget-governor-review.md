# Wake Budget Governor — design review

Date: 2026-08-29. Reviewer: Codex, before implementation.
Reviewed: `2026-08-29-wake-budget-governor-design.md`, the heartbeat and
event-loop paths it names, the `OpenTasteSession` record written at commit
`724f69e`, and the heartbeat founding constraints.

## Blocking

### 1. Make the ledger cache change days even when the file does not grow

If `DailyLedger` caches today's totals and invalidates only on file growth, a
quiet log does not grow at midnight and an exceeded resident stays resting
forever on yesterday's totals. Cache parsed records or per-day totals, and key
the answer by the requested UTC day; a day change must recompute without a
write. Normalize the loop's one injected `now` snapshot to UTC before deriving
the day, next midnight, and `resumes_at`; reject or explicitly interpret naive
datetimes. This prevents local-offset dates and tests' injected clocks from
moving the boundary away from UTC midnight.

### 2. The cost ledger must use provider and partial-measurement fields together

The proposed `cost_usd` sum is not provider-filtered, while only
`unmeasured_wakes` is. State explicitly that Anthropic-direct records never
contribute to the cost ceiling, even if a future record happens to carry a
numeric cost; they remain subject to the wake cap. For a metered record,
`usage.cost_usd is None` **or** `usage.cost_turns_unreported > 0` makes the wake
unmeasured. The numeric value in the latter case is only a reported subtotal.
Otherwise a partially billed OpenRouter wake is presented as fully measured,
and the dollar governor can understate both cost uncertainty and the
`unmeasured_wakes` detail.

### 3. Define one durable rest episode across process weather

`_last_transition` is in memory. A crash during a budget rest is followed by
`waking / boot` and then another `resting / daily_budget_reached`, splitting one
UTC-day rest into two records and two envelope intervals. That contradicts
"one status record per rest" and the founding rule that process restart is
weather. Give the episode a durable identity (at least day + budget regime), or
define boot/transition recovery that continues the open episode without
appending a second rest start. This prevents duplicate rest notices after a
routine restart.

Also require an exit transition on the first non-exceeded step: `active` before
a runnable wake, or `quiet`/`waiting` when no wake runs. Ingress during rest
must not change the state from `resting`; it stays pending. These requirements
prevent the persisted latest status from remaining `resting` after rollover.

### 4. Specify interval semantics for envelope notes

"The next status" is insufficient for events created during a rest, events
that span several rests, and an open rest at claim time. Pair each rest start
with the first later heartbeat transition that actually ends that episode;
select every rest interval intersecting the event's pending interval
(`created_at` through claim/run start). Say whether multiple intervals produce
multiple notes or one aggregate, and define "this event waited" as total queue
age or rest-overlap duration. An open rest may end at the wake's run timestamp
only when that wake is the action resuming the heartbeat; a standalone
`run-next` must not silently invent a rest end. Without this, an old rest can
be attached to unrelated later events, an event created mid-rest can receive
the full rest duration, and all but one of several rests can disappear.

Use the same injected clock for status timestamps and the open-interval end.
`append_heartbeat_status()` currently calls real `utc_now_iso()`, so simulated
rollover otherwise produces impossible or negative intervals.

### 5. Make a growing session-log read record-atomic

The heartbeat's own exchange is synchronous, so its normal pre-wake ledger
read does not overlap its own `_log_entry`; the file format itself provides no
such guarantee. `OpenTasteSession` appends without a shared lock, and a reader
can observe a grown file whose final JSON line is incomplete. Require a locked
snapshot or an incremental reader that parses only newline-terminated records,
retains the partial tail, and advances its offset only after a complete record.
This prevents a benign concurrent append from crashing the daemon or causing a
billed wake to be skipped permanently by the size cache.

### 6. The constitution must remain true when budgeting is disabled

The proposed unconditional sentence says the resident's wakes are budgeted,
but `--no-daily-budget` disables both ceilings. Make the operational prefix
configuration-aware (including the active limits), or qualify it and provide a
separate explicit disabled fact. This prevents the constitution from stating
false physics under the steward's supported override.

## Should fix

### 1. Define the ledger/policy interface and validate CLI domains

`WakeBudget(daily_usd, daily_wakes).exceeded(day)` has no stated source for the
day's ledger values. Define a snapshot boundary, for example
`ledger.for_day(utc_day)` followed by `policy.exceeded(snapshot)`, so one step
cannot mix days or reread between decisions. Reject boolean, non-finite, and
negative values; say whether zero is a deliberate immediate-rest setting.
Require a positive poll interval. This prevents NaN from silently disabling a
ceiling and negative values from creating an accidental permanent rest.

### 2. Define which session records are wakes and which day owns a boundary wake

Say whether failed state-bearing records count (they should if every attempted
resident exchange is a wake), and how legacy/missing `launch.provider` is
classified. The existing `timestamp` is written when `_log_entry` completes,
not when the wake starts, so a wake begun before midnight and logged after it
belongs to the new UTC day under the proposed rule. State that consequence.
This prevents implementations from disagreeing on wake counts and charging a
midnight-spanning wake to different days.

### 3. Preserve the two existing `active` signals under limit 1

Keep both the pre-batch pending probe and the post-batch `ran` probe. The first
records a normal wake that completes inside one call; the second records
ingress landing after the probe. Limit 1 then leaves an active backlog active,
and each auto-continuation remains pending until a fresh budget check on the
next `step()`. This prevents the batch-size change from restoring the invisible
quick-wake race covered by the current heartbeat tests.

Clarify that `--batch-limit` is ignored or clamped to 1 only while the budget
is active, and retains its configured value under `--no-daily-budget`. This
prevents the CLI from promising a batch size the daemon does not use.

### 4. Do not derive notes from an observability-limited summary

If `summarize_event_log` exposes heartbeat statuses, its normal `limit` must
not truncate the history used for envelope computation. Compute intervals from
an append-order snapshot of all heartbeat records, preferably through an
`EventStore` helper with an explicit `now`. This prevents long-lived or
multiple rests from disappearing once they fall outside a display limit.

### 5. Report incomplete cost as a lower bound

When any metered wake has unreported turns, label `cost_usd` in rest detail and
the envelope as reported cost or a lower bound, and include the unreported-turn
count as well as the unmeasured-wake count. This prevents prose such as
"cost 5.01" from claiming an exact total the log explicitly says is partial.

### 6. Add transition assertions to the rollover cases

The tests should cover `resting -> active` with pending ingress and
`resting -> quiet` with an empty queue, plus restart during an open rest. A
test that only observes a wake after midnight will not catch a status log that
still says `resting` or a duplicated rest start.

## Notes

- The proposed constitution sentence contains none of the cognitive-prior
  words banned by
  `tests/test_heartbeat.py::test_constitution_is_operational_not_cognitive`;
  configuration truth, not that test, is the issue.
- With a day-keyed ledger, the current step shape does not get stuck: the first
  new-day step bypasses the rest return, emits the normal next transition, and
  runs at most one event. Events and auto-continuations accumulated during rest
  remain append-only pending records.
- Cost-first tie breaking and before-wake checks are coherent. One wake may
  overshoot the dollar ceiling, and a wake finishing after midnight is then
  visible to the next new-day check under the record-timestamp rule.
- Anthropic-direct residents should show zero cost-governed rests and may still
  rest on the count ceiling. Missing cost on a metered provider is uncertainty,
  not zero dollars and not a reason by itself to emit `exceeded = cost`.

Verdict: build with changes (UTC/day cache and clock coherence; provider-aware partial-cost accounting; crash-stable rest episodes; interval-defined notes; record-atomic log reads; configuration-true constitution).
