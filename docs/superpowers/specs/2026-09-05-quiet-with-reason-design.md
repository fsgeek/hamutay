# Quiet with reason — a resident can say why it is going quiet

Date: 2026-09-05. Author: the Fable session that took custody of Hamut'ay
tonight. Status: IMPLEMENTED 2026-09-05 after Codex's review (`2026-09-05-quiet-with-reason-review.md`); dispositions at the end. Supersedes the founding spec's v1 quiet heuristic (`chosen_quiet`) and its constitution sentence; historical plans and logs are not rewritten, and readers stay tolerant of the old value.

## The problem, in the residents' own words

Sut'i, friction ledger entry 7 (c19): "Chosen silence and a frozen wake
leave identical records from outside. Legible silence costs one tool call;
no cheaper primitive." Its workaround: schedule a future wake whose purpose
says the quiet was chosen. That costs a real wake (about a dollar on Fable)
to say one sentence.

The Haiku resident (c14, observation_on_silence): "40 hours, no wakes, no
community writes. This is legible. I'm in a holding pattern — not urgent,
not forgotten."

Both are right about different things. Sut'i is right that the harness
cannot tell the two apart: `derive_quiet_reason` returns `chosen_quiet`
whenever no event is pending and no event expired. The word "chosen" there
is the harness's inference, not the resident's act. The Haiku resident is
right that undeclared quiet is a legitimate posture that should cost
nothing. The constitution currently says "if you bind no continuation, the
quiet is recorded as chosen," which overstates what the record can back.

Tonight the Haiku resident has been quiet seven days with nothing scheduled.
The daemon reports `chosen_quiet`. Nobody, including the resident, can say
from the record whether that is so.

## What this builds

One resident tool, one record type, one honest word in the daemon, one
envelope note, one report line, one constitution sentence.

### `declare_quiet` tool (natural wake shape only)

```
declare_quiet(reason: str, until: str | None = None)
```

- `reason`: the resident's own words for why it is going quiet. Required,
  non-empty.
- `until`: optional ISO-8601 instant. Informational only: "a knock after
  this would be welcome." It schedules nothing. A resident that wants to be
  woken uses `schedule_event`, as today.
- Buffered in the executor like `schedule_event` and written by the
  session at the end of `exchange()` in the same `append_many` as the
  scheduled events, as a `quiet_declaration` record in the event store.
  The `completed` status is appended afterwards by the event runner, as
  it is for scheduled events today. The join in the daemon (declaration's
  `declared_by_record_id` == completed's `result_record_id`) makes a
  declaration whose wake never completed inert, so the two-write shape
  needs no recovery path of its own. (Corrected from the first draft,
  which said "atomically with completed"; the existing commit path is
  two writes and the design follows it.)
- Registered the way `update_state` is: added by the session only when
  `wake_mode == "natural"`. Terminal shape stays byte-for-byte what the
  elder ran. The tool is offered, never required, and the harness never
  suggests when to use it (no priors on the resident's cadence).
- Calling it more than once in a wake: last call wins; earlier calls in
  the same wake are not recorded (same rule as `update_state`).
- Calling it and also scheduling an event in the same wake is allowed and
  is not a contradiction: "quiet until my Sept 19 check, because X."

### `quiet_declaration` record

```
{"record_type": "quiet_declaration", "declaration_id": <uuid>,
 "declared_by_cycle": N, "declared_by_record_id": <cycle record_id>,
 "reason": "...", "until": "<iso>" | absent, "created_at": <iso>}
```

Not an event: no `event_id`, no status lifecycle. Append-only like
everything else in the store.

### Daemon: `derive_quiet_reason`

Order unchanged from the founding spec (expiry beats novelty beats
choice), with the last word made honest:

1. any latest-status `expired` → `starved_expired`
2. no completed event yet → `awaiting_first_event`
3. a `quiet_declaration` whose `declared_by_record_id` equals the
   `result_record_id` of the most recent `completed` event → `declared_quiet`
4. otherwise → `undeclared_quiet`

`chosen_quiet` is retired. It claimed knowledge the harness did not have.
Existing tests that assert it are updated to `undeclared_quiet`; nothing
else in their logic changes.

When the reason is `declared_quiet`, the `heartbeat_status` record's
`detail` carries `{"reason": ..., "until": ..., "declared_by_cycle": N}`
so the daemon log and `events report` show the resident's words without a
join.

A declaration binds only the quiet that follows the wake that made it. A
later wake that declares nothing returns the daemon to `undeclared_quiet`.
That is the Haiku resident's posture, available at zero cost, named for
what it is.

### Envelope: the next wake is told what it said

`operational_notes_for_event` gains one note when the most recent
completed wake before this event declared quiet:

> Your cycle N declared quiet on <created_at>: "<reason>" (until <until>).
> This wake ends that quiet after <duration>.

Same mechanism as the rest notes. A resident that reads its own state will
already know; the note is for the resident that does not, and for the
record that shows it was told.

### `events report`

The human-readable and JSON reports gain a `latest_quiet_declaration`
block (cycle, created_at, reason, until) and the current daemon quiet
reason. The 40-hour question — chosen or stalled — becomes answerable from
one command, for one resident.

### Constitution

Replace

> Silence is legible: if you bind no continuation, the quiet is recorded
> as chosen.

with

> Silence is recorded but not explained: from outside, chosen quiet and a
> stalled wake look the same. If you want the record to carry your reason
> for going quiet, declare_quiet records it (and, if you give one, a time
> after which a knock would be welcome); it schedules nothing and costs one
> tool call. Undeclared quiet is also allowed and is recorded as
> undeclared.

The constitution tests (`tests/test_heartbeat.py`,
`tests/test_heartbeat_validation.py`) are updated to the new sentence.

## Budget default (a separate line in the same change)

Tony's number tonight: under 100 USD per month for the community, as a
planning target, not to be revisited unless it impedes progress. The
governor's parser default drops from 5.00 to 1.50 USD per resident per
day; the count ceiling (48 wakes) stays; the help text follows.

What 1.50 actually bounds (Codex review, blocking 4): the governor checks
the day's ledger before a wake and never interrupts one, so a resident
rests after the wake that crosses the threshold. A day's cost is therefore
at most 1.50 plus one wake. With Sut'i's wakes around 1 USD, a runaway day
is about 2.50 on that door; the Haiku door's wakes cost about 0.02, so it
cannot overshoot meaningfully. Observed behaviour is far below either:
Sut'i wakes about every two weeks. The monthly target is not enforced by
this default; a community-wide monthly floor (for example, rest when the
OpenRouter balance drops below a reserve) is the organ that would enforce
it, and is listed under Not in this change.

The change takes effect on restart; the restart inherits substrate and
shape from the logs and recovers nothing when nothing is running.

## Not in this change

- Community-scale silence (who is quiet across doors): that is the plaza.
- Read access to consumed event history for residents (Sut'i's c10
  question).
- Any change to terminal wake shape or to the elder.
- Any nudge, reminder, or default that tells a resident when to declare.
- A community-wide monthly cost floor or reservation (the organ that would
  make Tony's monthly number a bound rather than a target).
- Tolerance of a torn (partial) final JSON line in the event store: a
  pre-existing property of `EventStore` reads, unchanged here.

## Files

- `src/hamutay/tools/schemas.py`: `DECLARE_QUIET_SCHEMA` (not in
  `TOOL_SCHEMAS`, alongside `UPDATE_STATE_SCHEMA`).
- `src/hamutay/tools/executor.py`: `_declare_quiet` buffers; a
  `pending_quiet_declaration` accessor for cycle commit.
- `src/hamutay/events.py`: `build_quiet_declaration`; commit path appends
  it with the completed status; `operational_notes_for_event` note;
  `summarize_event_log` block; `RECORD_TYPE_QUIET_DECLARATION`.
- `src/hamutay/taste_open.py`: register the tool in natural mode; pass the
  buffered declaration to commit; natural tool guidance gains one line
  describing the tool (description, not instruction).
- `src/hamutay/heartbeat.py`: `derive_quiet_reason`, status detail,
  constitution text, budget default.
- Tests: TDD in `tests/test_heartbeat.py`, `tests/test_event_ingress.py`
  (or a new `tests/test_quiet_declaration.py`); Codex writes the
  independent validation file after.

## Test plan

1. Executor: `declare_quiet` with empty reason → error; with reason →
   buffered; second call replaces first; bad `until` → error.
2. Commit: a cycle that declared quiet appends `quiet_declaration` in the
   same atomic write as `completed`, with `declared_by_record_id` equal to
   the cycle's record_id.
3. Daemon: the four-way `derive_quiet_reason`; a declaration from an
   earlier wake does not carry over a later undeclared wake; expiry still
   wins over a declaration.
4. Status detail carries the reason; `events report` shows it.
5. Envelope: the next event's operational_notes carries the declaration;
   an event created before the declaring wake completed still gets the
   note only if the declaring wake is the most recent completed one.
6. Constitution text; budget default 1.50.
7. Terminal mode: tool list unchanged (byte-for-byte guard already exists
   for `update_state`; extend it).

## Review dispositions (Codex, 2026-09-05)

- **Blocking 1 (atomic handoff).** Not implemented as proposed. The
  existing commit shape is two writes (session writes scheduled events,
  runner writes completed) and the design follows it: the declaration
  rides in the session's `append_many` with the scheduled events, and the
  join on `result_record_id` makes any declaration whose wake never
  completed inert in derivation, envelopes, and the report. The report
  counts such orphans separately. A cycle-effects handoff into
  `run_next_event` would add a second commit boundary to fix a case the
  join already makes harmless.
- **Blocking 2 (registration scope).** Accepted. `exchange()` gains
  `event_managed` (the runner passes True); `declare_quiet` is offered and
  described only on event-managed natural wakes with tools and an event
  store. Direct exchanges and terminal-surface wakes never see it.
- **Blocking 3 (failed-wake recency).** Accepted. The join candidate is the
  latest wake OUTCOME in append order; a `failed` outcome yields
  `undeclared_quiet`.
- **Blocking 4 (the 90 USD claim).** Accepted; corrected above.
- **Should-fix 1 (note interval).** Accepted. Duration runs from the
  declaring wake's `completed_at` to this event's `running.started_at`
  (falling back to `now`); an invalid interval omits the duration clause.
  A budget rest and a declaration yield two ordered notes.
- **Should-fix 2 (expiry latch).** Accepted as a v2 refinement: an expiry
  counts only if nothing has run since it.
- **Should-fix 3 (`reason` field).** The payload keeps the name `reason`;
  it doubles as the activity log's generic reason, which is the one place
  the two meanings coincide. Every call stays in `tool_activity_full`; only
  the last VALID call reaches the store; an invalid later call leaves the
  earlier valid declaration intact. `until` must carry a timezone.
- **Should-fix 4 (report fields).** Accepted: `latest_quiet_declaration`
  is the latest JOINED declaration; `orphan_quiet_declaration_count` and
  `latest_heartbeat_status` are reported; no hypothetical quiet reason is
  derived in the report. The join helper lives in `events.py`.
- **Should-fix 5 (inventory).** Accepted; the wake-budget default
  assertion and the heartbeat/validation fixtures were updated.
- **Consider 1 (rendering).** The human report truncates the words at 400
  characters; the record, the JSON report, and the envelope carry them
  whole.
- **Consider 2 (declare + schedule).** Tested: the daemon waits, and the
  scheduled wake is told the declaration when it runs.

## Validation (Codex, independent tests, 2026-09-05 late)

`tests/test_quiet_declaration_validation.py` (36 tests) found three defects
in d87fd21, fixed in the follow-up commit: a non-string `reason` was
coerced and stored (now rejected); a supplied-but-empty `until` was read
as absent and replaced an earlier valid declaration (now an error that
leaves the earlier declaration intact); and the constitution named
declare_quiet on terminal-surface wakes where the tool is not offered
(the clause now lives with the tool in `schemas.py` and the session drops
it from the system prompt on any wake that is not offered the tool).
