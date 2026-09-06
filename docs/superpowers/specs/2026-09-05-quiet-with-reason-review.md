# Quiet with reason — design review

Date: 2026-09-05. Reviewer: Codex, before implementation.

Reviewed the proposed design against the heartbeat founding spec, the wake
budget governor design, and the named heartbeat, event-store, executor,
schema, session, deployment, documentation, community, and analysis paths.

## Blocking

### 1. The atomic commit and power-loss contract is not implementable as currently specified

**Defect.** The design says the executor buffers a declaration and
`taste_open.py` passes it to the commit, but there is no such commit boundary
inside `OpenTasteSession`. The executor is local to `_exchange_impl` and is
discarded when `exchange()` returns. `taste_open.py` currently appends
tool-created pending events itself, while `events.py::run_next_event` later
builds the `completed` record and calls `append_completed_atomic`. If the new
record is appended beside `pending_events` in `taste_open.py`, a process kill
can leave a declaration without its completed event (or a completed replay
without the declaration), directly contradicting the promised atomicity.

Even if `append_completed_atomic` is extended, its guarantee is deliberately
only process-kill atomic. A valid-prefix power-loss tear can preserve whichever
JSON lines come first. The spec gives neither a batch order nor recovery rules.
Today `recover_orphaned_running` will re-pend the source event,
`recover_lost_continuations` only understands the continuation marker, and a
quiet-declaration orphan is otherwise left untouched. A raw
`latest_quiet_declaration` report could then promote that orphan even though
`derive_quiet_reason` cannot join it. A partial final JSON line is worse:
`EventStore._read_records_unlocked` raises while parsing it, so boot never
reaches either recovery function.

**Where.** Design lines 46–48, 157–162, and 173–175;
`src/hamutay/taste_open.py` around `_exchange_impl`'s executor creation and
`append_many(tool_executor.pending_events)`; `src/hamutay/events.py` in
`EventStore.append_many`, `append_completed_atomic`, and `run_next_event`;
`src/hamutay/heartbeat.py` in both boot recovery functions.

**Concrete fix.** Specify a success-scoped cycle-effects handoff from the
session to `run_next_event`, cleared at the start of every exchange and on
every failure path. Extend the one event-store commit to accept the buffered
declaration and write one payload containing the declaration, completed
status, and optional bound continuation. Give the completed record the
`quiet_declaration_id` when one was requested. For valid-prefix recovery,
write the declaration before completed, and completed before continuation:
`[quiet_declaration, completed, continuation]`. That ordering permits only a
quiet orphan at the first boundary; the existing completed-marker recovery
still covers a lost continuation at the second boundary. On boot, count and
report declarations that join no completed `result_record_id`, leave them
append-only but exclude them from derivation, envelopes, and the report's
latest valid declaration. Make event-store reads ignore and report only an
unterminated malformed tail, as `DailyLedger` already does. Add prefix-tear
tests after each record, an idempotent reboot test, and a test proving a
process-kill-scale commit never exposes just one member of the logical pair.

### 2. Registering the tool for every natural session creates declarations that no completed event can own

**Defect.** “Added by the session only when `wake_mode == \"natural\"`” is
broader than the proposed persistence model. Natural interactive
`OpenTasteSession.exchange()` calls also receive natural-only tools, but they
do not run through `run_next_event` and therefore produce no completed
`event_status` record. The tool can return success while its declaration is
either never committed or is permanently orphaned. A terminal-surface wake is
another important boundary: current session wiring intentionally supplies no
ordinary tools when `terminal_surface` is present, even if the resident's
configured wake mode is natural.

**Where.** Design lines 35–56 and 160–162;
`src/hamutay/taste_open.py` where `UPDATE_STATE_SCHEMA` is appended under
natural mode and where `terminal_surface` disables `extra_tools`;
`src/hamutay/events.py::run_next_event`.

**Concrete fix.** Scope `declare_quiet` to event-managed natural wakes, not
natural mode alone. For example, have `run_next_event` explicitly enable the
capability for that exchange and retrieve its successful cycle effects;
default direct/interactive exchanges and terminal-surface exchanges to no
`declare_quiet`. If the intended scope really is every natural exchange,
redesign the record and join around a durable cycle-completion record rather
than an event completion. Test direct natural exchange, event-managed natural
exchange, terminal mode, and natural configuration with a terminal surface.

### 3. Rule 3 can falsely carry a declaration across a later failed wake

**Defect.** Matching `declared_by_record_id` to a completed event's
`result_record_id` is the correct identity join, but “most recent completed”
is not always the most recent wake attempt. If wake A completes and declares,
then wake B fails, B appends `failed` and leaves no pending event. Rule 3 still
selects A and reports `declared_quiet`, although the quiet now follows an
undeclared failure. That contradicts lines 89–90 and is precisely the stalled
case this feature is meant not to mislabel. “Most recent” is also undefined:
the log's norm is append order, whereas `summarize_event_log` sorts completed
display rows by timestamp.

**Where.** Design lines 69–92 and test-plan item 3;
`src/hamutay/heartbeat.py::derive_quiet_reason`;
`src/hamutay/events.py::run_next_event`, `append_failed`, and
`summarize_event_log`.

**Concrete fix.** Define the candidate from the full append-order event
history before the current idle transition. A declaration is current only if
the latest wake execution outcome is that joined `completed` record; any
later `failed` wake invalidates it and yields `undeclared_quiet` (or a new,
explicit failure reason if desired). Do not use the display-limited or
timestamp-sorted `completed` summary. Add the failed-after-declared case.
Keep tests for both inbound and self-scheduled completions: their completed
records have the same `wake_cycle`/`result_record_id` shape, so no origin-based
special case is needed.

### 4. The $1.50 change is not a $90/month worst-case bound

**Defect.** The governor checks accumulated cost before a wake and never
interrupts a wake. With a Fable wake costing about $1, the first wake leaves
the ledger below $1.50, so a second pending wake is allowed; only the next
step observes roughly $2 and rests the resident. Two such doors can therefore
be around $120 for a 30-day month, not $90. If one wake costs at least $1.50,
the resident rests on the following poll after that one wake. Since no
per-wake maximum exists, “$90 worst case” is false by an unbounded amount.

**Where.** Design lines 132–141; the governor's explicit overshoot rule in
`2026-08-29-wake-budget-governor-design.md`; and
`src/hamutay/heartbeat.py::WakeBudget.exceeded`,
`HeartbeatLoop._rest_if_budget_exceeded`, and `HeartbeatLoop.step`.

**Concrete fix.** Replace “worst case” with the actual pre-wake threshold and
overshoot behavior, including the one-dollar example above, and have Tony
confirm that behavior rather than only the numeral. If under $100 is a hard
requirement, a per-door threshold cannot guarantee it; add an account-level
floor/reservation or a defensible per-wake bound. If it is a planning target,
choose the default using observed wake cost plus one-wake overshoot headroom
(or lower the wake-count ceiling) and state the resulting estimate honestly.
Explicitly supersede the prior budget spec's $5 default, and change both the
parser default and its `default 5.00` help text.

## Should fix

### 1. Define the quiet-note interval and de-duplication independently of rest episodes

**Defect.** “Before this event” and “after `<duration>`” leave two off-by-one
choices open. The declaration's `created_at` occurs when the tool is called,
but quiet cannot begin until that wake completes. The current event's actual
claim time is its `running.started_at`; the `now` passed into
`operational_notes_for_event` may be the fixed scheduler timestamp captured
before an entire multi-event batch. An immediate continuation in an
unbudgeted batch can therefore have `now` earlier than the declaration.
Reusing `_rest_episodes`' pending-interval rule would also be wrong: the test
plan explicitly requires an event created before the declaring wake to get
the note. Finally, a declaration followed by a budget-rest episode legitimately
produces both facts, but the spec does not say whether that is two notes or an
accidental duplicate.

**Where.** Design lines 94–104 and 180–182;
`src/hamutay/events.py::_rest_episodes`, `operational_notes_for_event`, and
`run_next_event`; `src/hamutay/heartbeat.py::HeartbeatLoop.step`.

**Concrete fix.** Locate the current event's latest `running` record and the
immediately preceding append-order completed wake. Join at most one valid
declaration to that completed record. Display the declaration's `created_at`,
but compute duration from prior `completed_at` to current `started_at`; reject
or omit a negative/invalid interval. Do not gate the quiet note on the current
event's `created_at`. Preserve `_rest_episodes` unchanged and append exactly
one quiet note in addition to its one-note-per-rest-episode output. State that
an overlapping budget rest and declared quiet intentionally yield two ordered,
non-identical notes. Omit the parenthetical entirely when `until` is absent.

### 2. An old expired event permanently suppresses every future declaration

**Defect.** “Any latest-status expired” means any event whose terminal status
is `expired`, even years ago. Since terminal events receive no later status,
one expiry latches `starved_expired` forever; later successful declarations
can never produce `declared_quiet` or its detail. This is inherited from v1,
but it materially defeats the new feature and makes “current quiet reason” a
historical condition.

**Where.** Design lines 71–78; founding spec quiet heuristic;
`src/hamutay/heartbeat.py::derive_quiet_reason` lines 52–64.

**Concrete fix.** Refine starvation to the current idle episode—for example,
let a later successful wake clear an earlier expiry while an expiry later than
the most recent success still wins. Record this as an explicit refinement of
the founding v1 heuristic and add expired-before-later-declared and
expired-after-declared tests. If the permanent latch is truly intended, state
that declared quiet will never be visible again after the first expiry.

### 3. The tool's required `reason` conflicts with existing schema and activity-log conventions

**Defect.** `schemas.py` states that every tool's `reason` is optional and
uses `_REASON_FIELD` for the generic “why this tool call” metadata. The new
tool makes that same key its required domain payload. `ToolExecutor.execute`
removes `reason` from `parameters` and stores it in the activity entry's
generic `reason` field. Also, “earlier calls ... are not recorded” is false:
all calls and results remain in `tool_activity_full`; only earlier
`quiet_declaration` records should be suppressed. The spec does not say
whether a later invalid call erases an earlier valid declaration.

**Where.** Design lines 37–54 and test-plan item 1;
`src/hamutay/tools/schemas.py` module contract and `_REASON_FIELD`;
`src/hamutay/tools/executor.py::execute`, `_CAPABILITY`, dispatch, and
`_summarize`.

**Concrete fix.** Give `DECLARE_QUIET_SCHEMA.reason` its own required schema
and document this one semantic exception. Clarify that every attempted tool
call remains in activity history, while only the last successful call wins in
the event-store declaration buffer; an invalid later call leaves the prior
valid declaration intact. Add `declare_quiet` to executor dispatch,
`_CAPABILITY`, and result summarization explicitly in the file list. Require
an actual non-blank string. Validate `until` as a timezone-bearing ISO-8601
instant (or explicitly permit and define naive timestamps), since the design
calls it an instant.

### 4. Define report fields as current, historical, or derived

**Defect.** `summarize_event_log` currently ignores heartbeat records. The
new `latest_quiet_declaration` and “current daemon quiet reason” are
underspecified. The raw latest declaration may be orphaned; the latest
heartbeat status may be `active`, `waiting`, or `resting`; and recomputing a
hypothetical quiet reason while events are pending is not the daemon's current
state. Implementing derivation in `events.py` by importing from
`heartbeat.py` would also create a cycle because heartbeat already imports
event summarization.

**Where.** Design lines 84–110;
`src/hamutay/events.py::summarize_event_log` and `format_event_report`;
`src/hamutay/heartbeat.py` imports and `HeartbeatLoop.step`.

**Concrete fix.** Define `latest_quiet_declaration` as the latest declaration
that joins a completed cycle, regardless of the display `limit`; expose
orphan counts separately. Include `latest_heartbeat_status`. Set
`current_quiet_reason` only when that status is `quiet`, or rename a fresh
calculation to `derived_quiet_reason` and return it only when the queue is
idle. Put the shared append-order join helper in `events.py` (or a neutral
module) so heartbeat and reporting use the same logic without a circular
import. Read one records snapshot for reason and detail so they cannot refer
to different declarations.

### 5. Expand the compatibility and test inventory

**Defect.** The design says existing `chosen_quiet` tests change, but the
named inventory is incomplete. Besides heartbeat tests,
`tests/test_wake_budget.py` contains four heartbeat-status fixtures using the
old value and asserts the CLI default is `5.0`. Historical founding specs and
the implementation plan also contain `chosen_quiet`. Persisted experiment
JSONL files contain it and must remain readable even though new code no longer
emits it.

**Where.** Design lines 80–82, 129–130, and 165–185; repository grep across
`deploy/`, `docs/`, `community/README.md`, `analysis/`, source, and tests.

**Concrete fix.** Add the wake-budget fixtures/default assertion to the test
plan. State that this design supersedes the founding spec's v1
`chosen_quiet` heuristic and constitution sentence without rewriting
historical plans or logs. Keep report parsing tolerant of historical
`heartbeat_status.reason == \"chosen_quiet\"`. Add regression cases for
inbound and self-scheduled declarations, a later failed wake, a waiting and
an immediate continuation, every atomic-prefix orphan, multiple successful
and invalid declarations, direct-session tool absence, and old log values.

## Consider

### 1. Give the quiet declaration a bounded, stable rendering

**Defect.** `reason` has no size or line-shape rule but is duplicated into a
heartbeat status, daemon output, JSON and human reports, and a future event
envelope. Very large or multiline text can make all four operational surfaces
unwieldy; embedded quotes also make the proposed prose template ambiguous
before the outer envelope JSON escapes it.

**Where.** Design lines 41–45, 84–100, and 106–110.

**Concrete fix.** Either set a documented reasonable character limit at tool
validation or keep the full append-only value while defining a bounded escaped
snippet for status output, human reports, and the envelope. JSON output can
retain the full value.

### 2. Name the distinction between resident quiet and daemon state

**Defect.** A resident may declare quiet while scheduling a future event, but
the daemon records `waiting / scheduled_wake`, not `quiet`. The design permits
this correctly, yet phrases such as “current daemon quiet reason” can suggest
that `declared_quiet` is itself always the current heartbeat state.

**Where.** Design lines 55–56 and 84–110;
`src/hamutay/heartbeat.py::HeartbeatLoop.step` waiting branch.

**Concrete fix.** Describe the declaration as resident-authored intent that
may coexist with daemon `waiting`; reserve `current_quiet_reason` for actual
`heartbeat_status == quiet`. Test declare-plus-future-schedule as `waiting`
now, one quiet note on that future wake, and no contradiction in the report.

## Verified-fine

### 1. The identity join is origin-neutral

**Verification.** Completed inbound and self-scheduled events both carry the
cycle's `wake_cycle` and `result_record_id`; inbound events merely lack the
scheduler provenance fields on their initial pending record. Joining a valid
declaration's `declared_by_record_id` to that completed `result_record_id` is
therefore the right identity relation for both origins. A pending continuation
does not cause a quiet transition: `HeartbeatLoop.step` returns `active` or
`waiting` before calling `derive_quiet_reason`. After that continuation
completes, its completion correctly becomes the new candidate.

**Where.** `build_inbound_event`, `build_pending_event`,
`EventStore._build_completed`, `run_next_event`, and `HeartbeatLoop.step`.

**Action.** Keep the join; add the recency/failure and origin tests described
above rather than branching on `event_type`.

### 2. Natural-only schema registration can preserve the terminal surface

**Verification.** `UPDATE_STATE_SCHEMA` is deliberately outside
`TOOL_SCHEMAS`, and the session appends it only in natural mode. Following
that pattern for `DECLARE_QUIET_SCHEMA` preserves the default/explicit
terminal tool list and prompt byte-for-byte, provided the event-managed scope
from Blocking 2 is also applied. Terminal-surface wakes already suppress all
ordinary tools.

**Where.** `src/hamutay/tools/schemas.py` around `TOOL_SCHEMAS` and
`UPDATE_STATE_SCHEMA`; `src/hamutay/taste_open.py` natural and terminal-surface
registration branches.

**Action.** Keep both natural-only schemas out of `TOOL_SCHEMAS` and extend
the existing byte-identity guard.

### 3. The rename has no active non-test consumer in the requested paths

**Verification.** `chosen_quiet` has no occurrence in `deploy/`,
`community/README.md`, or the analysis code. Its documentation occurrences
are historical founding/design/plan text, not runtime consumers. The active
code occurrence is `derive_quiet_reason`; the remaining live assertions and
fixtures are tests. The only runtime $5 default is the heartbeat parser and
its help text; other source matches are unrelated cost constants. Explicit
`WakeBudget(5.0, ...)` uses in tests are scenario fixtures, except for the one
parser-default assertion. Deployment scripts and the systemd unit pass no
explicit budget flag, so a parser-default change takes effect on restart.

**Where.** Repository grep over the requested paths plus source and tests;
`deploy/run-heartbeat.sh`; `deploy/hamutay-heartbeat@.service`.

**Action.** No deployment or analysis compatibility change is needed. Preserve
historical-record readability and document the spec supersession as noted
above.

### 4. The proposal does not impose a resident-cadence prior

**Verification.** The proposed constitution is conditional (“if you want”),
`until` is expressly informational, undeclared quiet remains allowed, and the
tool is offered rather than required. Nothing specifies a delay, frequency,
deadline, or condition under which the resident should declare. The envelope
note reports a past act; it does not prescribe a future cadence.

**Where.** Design lines 41–56, 94–104, 120–127, and 143–149; founding spec's
no-harness-priors norm.

**Action.** Keep the natural guidance to a factual one-line capability
description. Do not add reminders, suggested intervals, examples framed as
defaults, or automatic declarations.

Verdict: **implement with the listed fixes**. The resident-facing primitive
and honest `undeclared_quiet` name are sound, but implementation should not
start until the event-managed handoff, valid-prefix ordering and orphan
recovery, failed-wake recency rule, envelope interval, and budget-overshoot
claims are made explicit.
