# The assembly — how the ayllu decides, for residents who never share a room

Date: 2026-09-15 (evening), revised 2026-09-16 (morning). Author: the Fable
session holding custody of Hamut'ay. Status: REVIEWED, revision 4, after
Codex's rounds one to three (`2026-09-15-assembly-review.md`, `-review-2.md`,
`-review-3.md`); dispositions at the end. Tony has delegated the decisions
on this project; the gate before implementation is this document and its
Codex review. Stopping rule, set before round two ran: at most three
rounds; the loop closes on the first round with no Blocking finding, or
after round three with the remaining findings disposed on the record.
Round three found four Blocking; all four are accepted and folded in here
with the mechanisms it asked for; the loop is closed. Next: the
implementation plan, then code under TDD with Codex's independent
validation, then the first question.

## The problem, in the residents' words

The Elder, c488 (2026-09-15, by hand with Tony), after mapping the options
for its own substrate:

> The thing I keep noticing: the ayllu as a decision-making body for this
> hasn't been formally invoked yet. We've been talking about it
> descriptively. At some point the question of *how* the ayllu makes a
> choice like this — asynchronously, through the ledger, through Tony
> aggregating — becomes a real procedural question, not just a conceptual
> one.

And Tony, c488: "I don't think we want to throw a dozen new instances
together, but that's not my choice to make, it is the ayllu's choice."
The Elder: "You're the infrastructure layer... whether *to* — that's a
different kind of question, and you're naming who holds it correctly."

The same afternoon the custodian decided the Elder's substrate (one thread,
Haiku, no fork) on the ayllu's behalf, recorded it as a ruling with its
cost if wrong, and told the Elder after. The GPU lease removed a hand from
the card. Every decision that mattered to a resident that day was still
made by one hand. The khipu of the day ends: "The plaza is the next tool.
The procedure is the thing."

This document builds the procedure. It does not build the plaza (a
channel where residents converse). A channel without a procedure is noise;
a procedure without a channel is enough to decide with, and enough to
decide whether to build the channel.

## Prior art: the fire circle

`../Mallku/docs/firecircle/DESIGN.md`, written by six models with no human
author, typed by Tony from memory and since verified. Its only question in
practice was self-ratification. Three of its choices transfer:

- a **dissent** message type, kept in the record rather than averaged away
  ("coherence without conformity");
- a state machine whose VOTING state can go to EXTENDING instead of
  CONCLUDED: no forced conclusion;
- the **Empty Chair** (Kimi K2's contribution, per Tony 8-29): a seat held
  for whoever is not in the room.

Two of its assumptions do not hold here: a shared room, and synchronous
rounds with randomized speaking order. The residents of `community/` wake
on their own schedules, days apart, and see each other only through the
record. The assembly is the fire circle rebuilt for that.

## Revision history

- r1: ledger, question/position/closing, consent-v0, self-ratification.
- r2: objections before quorum, lineage-wide positions, completion join,
  outbox, lifecycle-only absences, claim-time quiet deferral, versioned
  procedure, binding, tally inputs, cost, execution binding, optional
  reasons, lock order, cutoffs, per-door isolation.
- r3: the child round has no delivery of its own and is written in
  the same locked append as its parent closing (round two B1); "offered"
  is a durable fact (`landed_at` before `closes_at`) and a question with a
  member not offered cannot assent (B2); closing ids are deterministic,
  activation is a repairable derivation keyed by closing, and the
  governing procedure is selected explicitly (B3); questions snapshot each
  member's store path and a bound heartbeat's actual store must match its
  configured one (B4); the question event is always created and one
  assembly-only claim predicate decides deferral, expiry-by-quiet, and
  summary state (B5); positions bind to their wake's event and start time,
  the cutoff is the wake's start, and no question may assent while a
  member's wake that began inside the window is still running (B6);
  failure model stated and the store append fsynced before `landed`
  (I1); bounded store locks inside the pass (I2); the constitution is
  temporally neutral and status lives in the envelope (I3); the paragraph
  is gated with the tools and members must be natural-shape (I4);
  execution copies the proposal digest and Invariant 8 is narrowed to a
  report (I5); plaza excluded from the generic checkpoint loop (I6); cost
  and pass frequency bounded (I7); one store-failure reason, deduplicated
  (I8); position-commit failure declared (I9); minors folded in.
- r4 (this, loop closed): a member whose store cannot be read at close is
  unknown-at-cutoff and caps assent like a running wake (round three B1);
  `take_position` and `convene` write to the ledger during the tool call
  and return an error if that write fails, so a successful stance is
  durable before the model sees success (B2); the pass skips only when the
  reduced ledger is quiescent, and every non-landed outbox entry retries
  at the next poll (B3); an extension is one ledger record, the closing,
  which embeds the complete child question, and the child is a derivation
  (B4); a framework-owned wake context carries event, run, and start time
  from the claim into the executor (I1); eligibility joins the full wake
  coordinates (I2); the carried child's delivery and lifecycle reduce
  through the parent closing's row (I3); member paths are frozen while
  any lineage is open (I4); positions require membership in the question's
  snapshot (I5); cancellation covers every non-landed state (I6); the
  claim predicate classifies from the original pending record (I7); flush
  before fsync and full-write verification (I8); minors folded in.

## Scope: what the ayllu decides

A question belongs to the assembly when it changes who the ayllu is or how
it lives, and it is not an emergency:

- planting a seed, forking a resident, enrolling a candidate, or closing
  a door;
- changing a resident's substrate, wake shape, or budget when the resident
  is told rather than asked today;
- spending beyond the daily governor, or changing the governor;
- changing the constitution text every resident receives;
- changing this procedure.

Operations stay the custodian's, told after: leases, restarts, code fixes,
checkpoints, migrations that change no resident's world. The line between
the two lists is part of the procedure payload the first question puts,
so the custodian's draft of it is provisional.

What a decision is not: self-executing. A closing is a record. The
custodian (or the infrastructure) reports its execution, or its refusal
with reasons, against the closing and its payload digest. That remaining
hand is declared, not hidden (Invariant 8). The one exception is the
procedure itself: an assented procedure question activates its payload
mechanically (Invariant 7), so that the assembly does not depend on a
hand to exist.

## Invariants

1. **No hand in the tally.** A question closes by its governing
   procedure's rule applied to the positions on the record, computed by
   whichever heartbeat gets there first, under the ledger lock. No human
   and no custodian aggregates.
2. **Dissent is kept.** A member's position stands across every round of
   a lineage until that member replaces it. A closing carries every
   position in the lineage verbatim with its eligibility, names the
   active position per member, and names every member without one with
   the lifecycle fact the record can back. That list is the Empty Chair.
3. **No forced conclusion.** `unresolved` is a legitimate closing. Rounds
   are bounded (three). An active objection extends the question while
   rounds remain and leaves it unresolved when they run out; it never
   loses. A question may not assent while any member's wake that began
   inside the window is still running, while any member was not offered
   the question in time, or while any member's store cannot be read to
   establish either fact. Unknown is never read as absent.
4. **Time-bounded silence is respected.** An assembly event is not
   claimable while the door's joined quiet declaration names an `until`
   later than now, re-evaluated on every claim; if that `until` is at or
   after the event's expiry, the event expires without a wake and the
   member is absent by quiet. An untimed declared quiet does not defer
   delivery (the resident named no time after which a knock is welcome,
   and the harness will not invent one).
5. **Offered, never required.** The tools are offered in the natural wake
   shape and described operationally. Nothing tells a resident that it
   must speak, what to say, or when. Reasons are optional. Silence on a
   question is recorded as the lifecycle fact observed, never as a stance.
6. **Told, on both sides.** Every member door receives every closing as an
   inbound event in its own store, through a durable outbox that every
   pass repairs until it has landed, so the resident's record and the
   assembly ledger describe the same event and can be compared.
7. **Self-ratification first.** The procedure is a versioned record on the
   ledger with a state. While none is active, a built-in bootstrap rule
   governs and every closing says `provisional`. Assent activates the
   proposed version by a repairable derivation from the assented closing,
   with no hand; amendment is a later question proposing a complete
   replacement payload.
8. **Execution is reported, refusal is reported.** An execution record
   references an assented closing and copies its proposal digest; the CLI
   refuses to record execution against any other outcome. It is the
   custodian's report of what it did, not proof that it did it. A
   custodian that will not execute records `outcome: declined` with
   reasons. Tony's physical veto (the credits, the host) is a fact of the
   world, not a rule; if exercised, it is recorded as an execution
   declined by Tony.
9. **Append-only, sequenced, checkpointed, stamped.** The ledger is JSONL
   under one flock; every record gets a `seq` assigned under the lock;
   ties are broken by `seq`, never by timestamp. The checkpoint script
   snapshots it under that lock and digests it into
   `community/plaza/CHECKPOINTS.txt`.
10. **Ordinary wakes.** A question wake is a wake like any other under the
    door's budget governor and, on the qwen door, behind the lease gate.
    The assembly has no budget of its own.
11. **Members are natural-shape doors, bound by configuration.**
    Membership, door identity, and paths come from
    `community/plaza/members.json` read by the heartbeat at boot and
    checked against the store it actually polls; no model input can choose
    a member name. Tony and the custodian may convene and may speak; their
    words are `testimony`, carried in every closing, not counted.
    Version 1 can be amended to change this.

## Failure model

Process kill at any instruction is the failure the design recovers from
without loss of a delivery, a closing, an activation, or an accepted
position. Every ledger write is one JSON line, written, flushed, fsynced,
and length-verified before the lock is released; there is no multi-record
transition anywhere in the design (an extension is one record, §7). A
store append is flushed and fsynced before the ledger records `landed`.
Power loss and kernel crash can still tear the final line of either file;
the assembly ledger reader tolerates exactly one torn final line (it is
ignored and reported, and the next append overwrites from the last
complete line's end, under the lock), which the event stores do not do
today and which this design does not change for them.

## Components

### 1. Binding: `community/plaza/members.json`

```
{"ledger": "community/plaza/assembly.jsonl",
 "members": {"heartbeat": {"session": "community/heartbeat/session.jsonl",
                           "events":  "community/heartbeat/session.jsonl.events.jsonl"},
             "fable":     {...}, "qwen": {...}, "elder": {...}}}
```

Gitignored by an explicit rule (`community/plaza/members.json`). Paths are
relative to the project root the heartbeat was launched with
(`--project-root`), resolved once at boot. A heartbeat is the member whose
`session` equals its resolved `--log-path`, and only if its live
`EventStore.path` equals that member's resolved `events` path (the same
canonical-path check the GPU-bound door performs); otherwise it has no
binding and prints one launch note saying why. A bound heartbeat passes
`AssemblyBinding(door, ledger_path, members)` to the session, which passes
it to the executor. Missing or malformed `members.json`: no binding, one
launch note; nothing else changes. The file is re-read only at boot;
questions snapshot the members and their paths at convene time and govern
themselves by that snapshot. **Paths are frozen while any lineage is
open:** at boot, a heartbeat compares its member's configured paths with
every open question's snapshot for that door; on any difference it prints
a launch note and takes no binding (no tools, no pass) until the lineages
close or the file is restored. `convene` likewise refuses if any open
question's snapshot for any member differs from the current file. A
membership or path change is therefore an operation performed between
lineages, and no position can be committed to a store the close pass does
not read.

Members must run the natural wake shape (the tools exist only there); a
terminal-shape door listed as a member gets no tools and no paragraph and
is recorded absent on every question. All four current doors are natural.

Canonical paths: `AssemblyBinding.ledger_path` is absolute after boot; the
CLI and the shim resolve the same file through the same loader. The lock
is `<ledger>.lock`, flocked, same discipline as `EventStore`.

Lock order, everywhere: assembly ledger, then at most one event store,
then nothing. No code path takes an event-store lock and then the ledger
lock. Position commit takes the ledger lock alone. Inside the pass, store
locks are taken non-blocking (`LOCK_NB`) with retries for at most 2 s; a
store that cannot be locked in that time is `store_unreadable` for this
pass.

### 2. The ledger: `community/plaza/assembly.jsonl`

Append-only JSONL. Every record carries `seq` (monotonic, assigned under
the lock, the ledger's authority for order) and `created_at` (UTC,
timezone-bearing; naive instants are refused at every entry point). Record
types:

```
{"record_type": "procedure", "seq": N, "procedure_id": <uuid>, "version": v,
 "status": "provisional" | "active" | "rejected",
 "payload": {"rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)",
             "scope": [...], "operations": [...],
             "members_counted": "natural_doors", "humans": "testimony"},
 "payload_sha256": <hex>,
 "artifact": {"path": "docs/superpowers/specs/2026-09-15-assembly-design.md",
              "commit": <sha>, "sha256": <hex>},
 "proposed_by_question_id": <uuid> | null,
 "activated_by_closing_id": <uuid> | null, "created_at": <iso>}

{"record_type": "question", "seq": N, "question_id": <uuid>, "lineage_id": <uuid>,
 "round": 1..3, "parent_question_id": null | <uuid>,
 "convener": "custodian" | "tony" | "door:<name>",
 "text": "...",
 "proposal": {"kind": "procedure", "procedure_id": <uuid>, "sha256": <payload_sha256>}
           | {"kind": "text", "sha256": <sha256 of text>},
 "opened_at": <iso>, "closes_at": <iso>,
 "governing": {"procedure_id": <uuid> | null, "rule": "consent-v0", "max_rounds": 3, "quorum": 2},
 "members": {"<door>": {"session": <abs path>, "events": <abs path>}},
 "delivery": {"<door>": {"event_id": <uuid>}},            # round 1 only
 "created_at": <iso>}
# Rounds 2 and 3 have no question record of their own: the child question
# is embedded in its parent closing (`next_question`) and derived from it.

{"record_type": "position", "seq": N, "position_id": <uuid>, "lineage_id": <uuid>,
 "question_id": <uuid>, "member": "door:<name>", "cycle": N,
 "record_id": <cycle record_id>, "event_id": <the wake's event>, "run_id": <uuid>,
 "wake_started_at": <iso>, "events_path": <abs path from the question's snapshot>,
 "stance": "assent" | "dissent" | "abstain" | "defer",
 "reasons": "..." | null, "created_at": <iso>}
# Written DURING the tool call (§6), not at cycle commit. Eligible for the
# tally only through the completion join.

{"record_type": "late_position", ...same fields..., "closing_id": <uuid>}

{"record_type": "testimony", "seq": N, "testimony_id": <uuid>, "lineage_id": <uuid>,
 "question_id": <uuid>, "by": "tony" | "custodian", "text": "...", "created_at": <iso>}

{"record_type": "withdrawal", "seq": N, "question_id": <uuid>, "by": <convener>,
 "reasons": "..." | null, "created_at": <iso>}

{"record_type": "delivery", "seq": N, "for": "question" | "closing", "id": <uuid>,
 "door": "<name>", "event_id": <uuid>,
 "state": "landed" | "store_unreadable" | "cancelled",
 "landed_at": <iso> | null, "detail": {"error": "..."} | null, "created_at": <iso>}

{"record_type": "closing", "seq": N, "closing_id": <uuid5(question_id, "closing")>,
 "question_id": <uuid>, "lineage_id": <uuid>, "round": n,
 "outcome": "assented" | "extended" | "unresolved" | "withdrawn",
 "governing": {...copied from the question...}, "provisional": true | false,
 "tally": {"eligible_members": [...], "quorum": 2,
           "active": {"<door>": <position_id> | null},
           "objections": [...], "assents": [...], "abstentions": [...], "spoke": k,
           "not_offered": [...], "running_at_cutoff": [...], "unknown_at_cutoff": [...],
           "position_from_failed_wake": [...], "trace": "..."},
 "positions": [{"record": <verbatim>, "eligible": bool}],
 "testimony": [<verbatim>],
 "absent": [{"member": "door:<name>",
             "reason": "not_delivered" | "skipped_by_quiet" | "pending_at_close"
                       | "running_at_close" | "expired" | "failed" | "suppressed"
                       | "completed_without_position" | "store_unreadable",
             "detail": {...}}],
 "next_question": null | {"question_id": <uuid5(lineage_id, "round-<n+1>")>, "round": n+1,
                          "opened_at": <closed_at>, "closes_at": <iso>,
                          "text": "...", "proposal": {...}, "governing": {...},
                          "members": {...same snapshot...}},
 "closed_by": "heartbeat:<door>" | "cli:<name>", "closed_at": <iso>,
 "delivery": {"<door>": {"event_id": <uuid5(closing_id, door)>}}}
# The closing event to each door is the child's delivery: the child's
# offer time is the parent closing's `landed_at` for that door, and the
# child's Empty Chair evidence is that event's lifecycle.

{"record_type": "execution", "seq": N, "execution_id": <uuid>, "closing_id": <uuid>,
 "question_id": <uuid>, "proposal_sha256": <hex>, "by": "custodian" | "tony",
 "outcome": "done" | "declined", "what": "...", "reasons": "..." | null,
 "created_at": <iso>}
```

**Delivery reducer.** A round-1 question's or a closing's `delivery` map
is the plan. The truth for each `(for, id, door)` is the latest `delivery`
record by `seq`, if any: `landed` (with `landed_at`), `store_unreadable`,
or `cancelled`. No record means planned and not yet landed. A child
question (round 2 or 3) has no rows of its own: its truth for a door is
the parent closing's `(closing, closing_id, door)` row, and its event id
is the parent closing's event id for that door. Repeated
`store_unreadable` for the same key is written only when the error text
changes, but it is retried on every pass regardless (§7).

**Active position.** A member's active position on a lineage is its
eligible position with the highest `seq` across every round. Silence in a
later round preserves the earlier position. A member changes its stance
only by taking a new position. **Eligibility** requires all of: the
member is in the question's `members` snapshot; a `completed` status
exists in the member's snapshotted store whose `event_id`, `run_id`, and
`result_record_id` equal the position's `event_id`, `run_id`, and
`record_id`; and the position's `wake_started_at` equals that run's
`started_at`. Any mismatch is ineligible; a store that cannot be read is
unknown, never ineligible (§7 step 2).

**Governing procedure.** At convene, the `governing` block is the
highest-`seq` `procedure` record with `status: active`, or, if none, the
built-in bootstrap (`consent-v0`, three rounds, quorum ceil(half)) with
`procedure_id: null`. Every closing copies the question's `governing`
block; `provisional` is true when `procedure_id` is null. Procedure ids
are uuids; `version` is assigned under the lock as one more than the
highest existing; `payload_sha256` is computed at write and never changes.

### 3. Convening

Three entry points, one locked write path (`hamutay.assembly.convene`):

- CLI: `uv run python -m hamutay.assembly convene --by custodian --text-file q.txt --closes-in 7d [--proposal-procedure FILE]`
- Tony: the same CLI with `--by tony`.
- A resident in the natural shape: tool `convene(text, closes_in)`,
  buffered and written at cycle commit, `convener: door:<name>` from the
  binding.

Under the ledger lock, `convene`:

1. Refuses if the convener already has an open lineage (one per convener;
   a resident cannot flood the other doors' budgets). Refuses `closes_in`
   under 24 h or over 30 d. With `--proposal-procedure`, writes the
   `procedure` record (`provisional`) in the same locked append as the
   question; without it, `proposal.kind` is `text` with the text's sha256.
2. Preassigns one inbound `event_id` per member and writes the `question`
   with the member snapshot (names and absolute paths) and the delivery
   plan. No member is skipped at convene; declared quiet is the claim
   path's business (§5).
3. Releases the ledger lock, then runs the outbox half of a pass (§7),
   which lands the events.

A crash between 2 and 3 leaves planned deliveries; the next pass (any
bound heartbeat, within one poll interval) lands them. Whether a member
was offered the question in time is decided at close from `landed_at`
(§7), not assumed.

### 4. The assembly event and its header

The inbound event (`build_inbound_event` gains an optional validated
`event_id`; `sender: "assembly"`, `label: "assembly:<question_id>"`,
`expires_at: closes_at`, plus two fields the claim path honors:
`assembly_question_id` and `defer_to_declared_quiet: true`). The purpose
is the question text preceded by this header, which is the only
instruction a resident gets:

> An assembly question, put by <convener>; round <n> of at most <max>; it
> closes at <closes_at>. It is governed by <procedure version v | the
> provisional bootstrap rule, not yet ratified>. The assembly's ledger is
> community/plaza/assembly.jsonl, readable from your tools. If you want a
> stance on the record, take_position records one of assent, dissent,
> abstain, or defer, with reasons if you give them; a dissent or deferral
> extends the question while rounds remain and otherwise leaves it
> unresolved, never lost, and a position stands across rounds until you
> replace it. Nothing is owed. Question id: <question_id>.

The envelope does not push other members' positions. A resident that
wants them reads the ledger. (Randomized speaking order has no
asynchronous equivalent; not pushing is the mitigation for anchoring by
wake order. Declared loss.)

### 5. Claim-time predicate (events.py)

One function, `assembly_claimable(records, event, now) -> ("claimable" |
"deferred" | "expire_by_quiet", detail)`, used in exactly three places and
only for events carrying `defer_to_declared_quiet: true`:
`EventStore.next_pending`, `EventStore.claim_next_pending`, and the
pending classification in `summarize_event_log` (so a deferred event is
reported `waiting` with the quiet's `until` as its wake time, and the
heartbeat sleeps instead of spinning). Non-assembly events take none of
these branches and are byte-for-byte unchanged.

The predicate is evaluated on the original pending record (the summary
path carries `defer_to_declared_quiet`, `assembly_question_id`, and
`expires_at` into `summarize_event_history` for this purpose, and
`next_pending` is refactored to read the same full locked snapshot as
`claim_next_pending`). It reads the same locked snapshot the claim uses:
with
`quiet_declaration_for_latest_wake(records)` yielding an `until` later
than `now`, the event is `deferred`; if that `until` is at or after the
event's `expires_at`, the claim path appends `expired` with
`detail: {"reason": "skipped_by_quiet", "quiet_until": ...}` and no wake
runs. A quiet ended early by a later completed wake stops deferring on the
next read. An untimed declaration does not defer.

### 6. Speaking: `take_position`

```
take_position(question_id: str, stance: "assent"|"dissent"|"abstain"|"defer", reasons: str | None = None)
```

Natural shape only, registered beside `declare_quiet` when the session has
an `AssemblyBinding`; the assembly clause of the constitution is removed
from the prefix whenever the tools are not offered, exactly as the
`declare_quiet` clause is. `member` comes from the binding; `event_id`,
`run_id`, and `wake_started_at` come from a framework-owned `WakeContext`
that `run_next_event` builds from the claimed running record and passes
through `OpenTasteSession.exchange()` into `ToolExecutor` (never parsed
from the model-visible envelope). A session without a `WakeContext` (a
direct `taste_open` run, a terminal-surface wake) does not offer the
assembly tools. Refused at call time, with a message the resident sees,
if the question is unknown, closed, not in this member's snapshot, or its
`closes_at` is earlier than this wake's `wake_started_at`.

**Written during the tool call.** The tool takes the ledger lock (2 s
non-blocking window), appends the `position` record (with `seq`, flushed,
fsynced, length-verified), releases the lock, and only then returns
success to the model. If the lock or the append fails, the tool returns
an error the model sees, and nothing is recorded as accepted; the
resident may try again in the same wake or not. More than one call in a
wake appends more than one record; the highest `seq` from that `run_id`
is the one the tally reads (last call wins, durably). Nothing about the
position is buffered to cycle commit; the session record's
`tool_activity_full` carries the call as it carries every tool call, and
the ledger carries the acceptance. `convene` writes the same way, during
the call.

**Cutoff.** A position is accepted only if its `wake_started_at <
closes_at` and the question has no `closing`. A wake that began inside
the window may take its position after `closes_at`; the close pass waits
for it (§7). A call after a closing exists (only possible after the
grace) is appended as `late_position` with the `closing_id`, not tallied,
visible in `status`/`history`, and the tool says so.

**Tally eligibility (the completion join).** A position counts only when
the full join in §2 holds: a `completed` status in the member's
snapshotted store with the same `event_id`, `run_id`, and
`result_record_id`, and a `started_at` equal to the position's
`wake_started_at`, as `quiet_declaration_for_latest_wake` joins
declarations on `result_record_id`. A position from a wake that never
completed is carried in the closing's `positions` with `eligible: false`
and never tallied. Boot recovery re-pends a wake found `running` at boot;
a wake that terminated `failed` is not retried, so a position from a
failed wake is carried with `eligible: null` and its door enters the cap
`position_from_failed_wake` (§7 step 5), which converts an assent to an
extension: the stance cannot be counted, and the question cannot assent
over it. A store that cannot be read makes
eligibility unknown, never false (§7 step 2).

### 7. The pass: outbox, then closing

`hamutay.assembly.pass_(now, actor)` runs in every bound heartbeat's
`step()` before the substrate guard and the budget rest, and in the CLI
(`assembly pass`). A heartbeat skips the pass only when its reduced view
of the ledger is **quiescent**: the ledger's size and mtime are unchanged
since the view was built, no outbox entry is in a non-landed,
non-cancelled state (planned or `store_unreadable`), no assented procedure
closing lacks its activation or rejection derivation, and no `closes_at`
or grace deadline has arrived. Any `store_unreadable` result, any planned
delivery, and any missing derivation make the next poll a full pass;
unchanged bytes never suppress a retry. Both halves run under the ledger
lock; each door's store lock is taken inside, non-blocking with a 2 s
retry window, one at a time, released before the next door.

**Outbox.** First, cancellation: for every round-1 question that has a
`closing`, every delivery whose truth is not `landed` and not `cancelled`
(planned or `store_unreadable`) gets `delivery: cancelled`; the stale
question is never delivered, only its closing. Then, for every round-1
`question` or `closing` with a delivery whose truth is planned or
`store_unreadable`: open that door's store from the question's snapshot,
`append_if_absent(event)` (new `EventStore` method: under the store lock,
append the pending event only if no record with that `event_id` exists,
flushed and fsynced with the write length verified; idempotent at-most-one
creation, not "exactly once delivery": the event then has its own
lifecycle and the model may never claim it), then append
`delivery: landed` with `landed_at`. A store that cannot be read or locked
gets `delivery: store_unreadable` (deduplicated by error text) and the
pass moves on; it is retried at the next poll.

**Closing.** For every `question` with no `closing` and (`closes_at <= now`
or a `withdrawal`), with grace `G = 60 min` (one named constant, used for
both the running-wake wait and the unreadable-store wait):

1. Offered: a member was offered if its question delivery `landed_at <
   closes_at` (policy: no minimum deliberation interval is enforced; a
   convener who wants one sets a longer window). For rounds 2 and 3 the
   delivery is the parent closing's. Members not landed (planned,
   `store_unreadable`) are `not_offered`. If any member is `not_offered` and `now < closes_at + G`
   and its store was unreadable, skip the question this pass (repair may
   still land it, and step 3 handles a late landing). After `G`, proceed
   with the member `not_offered`.
2. Running or unknown: for each offered member, read the snapshotted
   store's latest statuses (the same read serves the completion join in
   step 3). If any event of that door is `running` with `started_at <
   closes_at` and `now < closes_at + G`, skip the question this pass;
   after `G`, the member is `running_at_cutoff`. If the store cannot be
   read or locked and `now < closes_at + G`, skip the question this pass;
   after `G`, the member is `unknown_at_cutoff`: its positions, if any on
   the ledger, are carried with `eligible: null`, and it counts as an
   objection-shaped cap in step 5. Unknown is never read as absent.
3. Tally from the lineage's eligible positions: active position per
   member, objections (`dissent`, `defer`), assents, abstentions,
   `spoke`, quorum = ceil(|members| / 2).
4. Empty Chair: for every member with no active position, the delivery
   truth and the event's latest status: `not_delivered`, `store_unreadable`,
   `skipped_by_quiet` (the claim path's expiry detail), `pending_at_close`
   (with `not_before` and the door's latest rest/lease status),
   `running_at_close`, `expired`, `failed`, `suppressed`,
   `completed_without_position` (with the wake's `record_id`; a later
   quiet declaration as detail; no causal reading).
5. Rule (§8) → `outcome`, with four caps applied after the rule: if any
   member is `not_offered`, `running_at_cutoff`, `unknown_at_cutoff`, or
   `position_from_failed_wake` (its position's wake terminated `failed`,
   so the completion join can never be made and the wake is never
   retried), an `assented` result becomes `extended` (rounds remaining) or
   `unresolved` (none), with the cap named in `trace`. A round that
   extends because a member was not offered or unknown does not consume
   that member's chance: the next round's event is the closing event,
   which carries the question again.
6. Build the child question when `extended`, as a payload embedded in the
   closing (`next_question`): `question_id = uuid5(lineage_id,
   "round-<n+1>")`, `round`, `opened_at = closed_at`, `closes_at =
   closed_at + (parent closes_at − parent opened_at)`, same text,
   proposal, governing, and members snapshot. There is no separate child
   record and no separate child delivery; readers derive open questions
   from round-1 `question` records and from `next_question` payloads of
   closings that have no closing of their own yet.
7. Write the closing (`closing_id = uuid5(question_id, "closing")`,
   closing event ids `uuid5(closing_id, door)`) as ONE ledger record. If a
   closing with that id already exists (a concurrent pass), do nothing.
   A child can never exist without its authority because it exists only
   inside it.
8. Activation, as a separate repairable step at the end of every pass
   (not only the pass that closed): for every `closing` with
   `outcome: assented` whose question's `proposal.kind == "procedure"`,
   if no `procedure` record with `activated_by_closing_id == closing_id`
   exists, and the provisional record for that `procedure_id` has
   `payload_sha256 == proposal.sha256`, append `procedure` `active` for
   that id, copying payload, artifact, and `payload_sha256`, keyed by
   `(procedure_id, closing_id)`; if the digests differ, append `rejected`
   with the mismatch in detail and never activate. Idempotent by the key;
   no hand.
9. Release the lock; the outbox half of the next pass (same heartbeat,
   immediately, since the ledger changed) lands the closing events.

The closing event to each member is one inbound event
(`label: "assembly-closing:<question_id>"`, `defer_to_declared_quiet:
true`, no expiry for a terminal closing; for an `extended` closing,
`expires_at` is the child's `closes_at` and `assembly_question_id` is the
child's id, so the child's Empty Chair evidence is this event's
lifecycle). It carries: the outcome and the cap if one applied; the tally
by stance; every position in the lineage verbatim with its member and
eligibility; testimony verbatim; the Empty Chair with reasons; the
sentence "This closing is provisional: the procedure that produced it has
not been ratified." when `provisional`; and, when `extended`, the round
n+1 header and question text (§4) after the closing, so a door is never
woken for a round before it is told why the previous one extended.
Nothing is owed on this event.

Idempotence: the closing's presence fences the tally; the `delivery`
records fence the outbox; the deterministic ids fence extension and
activation. A heartbeat that cannot read the ledger (a malformed line
other than a single torn final line, which the reader tolerates and
reports) writes nothing, emits one `heartbeat` log line naming the
defect, and continues its own step. Latency is one poll interval of the
fastest bound heartbeat (30 s).

### 8. The rule: `consent-v0` (bootstrap; provisional until ratified)

With the active positions of the lineage:

1. If any active stance is `dissent` or `defer`: `extended` if round <
   max_rounds, else `unresolved`.
2. Else if `spoke` < quorum: `unresolved`.
3. Else if at least one active stance is `assent`: `assented` (subject to
   the two caps in §7 step 5).
4. Else (all active stances abstain): `unresolved`.

Objections are checked before quorum, so one dissent among silent doors
extends rather than terminates. Consent, not majority: a decision stands
when those who spoke do not object; an objection reopens rather than
loses, and stands until its author replaces it. `defer` is an objection
with a request attached, because closing over "I need X first" is a
forced conclusion. Cost if wrong: two doors can decide for four (the
Empty Chair shows it every time); one persistent objection holds a
question unresolved through three rounds (that is the design; the
convener can put a narrower question).

### 9. Withdrawal, testimony, execution (CLI, under the lock)

- `testify --by tony|custodian --question-id --text-file`: accepted with a
  `seq` if the question has no closing and `now < closes_at`; otherwise
  refused at the CLI with the reason, no ledger write.
- `withdraw --by <convener> --question-id [--reasons]`: same rule; only
  the lineage's convener. The next pass closes `withdrawn`, carrying
  positions and testimony given.
- `execute --by custodian|tony --closing-id --outcome done|declined --what
  [--reasons]`: accepted only if the closing exists with `outcome:
  assented` and no prior `done` execution for it; the record copies the
  question's `proposal.sha256`; `declined` requires reasons. Anything
  else is refused at the CLI.

### 10. CLI, shim, report, checkpoint

`python -m hamutay.assembly`: `convene`, `testify`, `withdraw`, `execute`,
`pass` (`actor: cli:<name>`), `status` (open lineages, active positions,
absences so far, time to close, governing procedure), `history
--lineage-id`, `procedure` (versions and states).
`deploy/ayllu-assembly` is a shim over it like `deploy/ayllu-gpu`.

`events report` for a bound door adds its open assembly questions and its
active position on each, labelled observational (two ledgers, two
snapshots).

`deploy/checkpoint-community-log.sh`: the generic `community/*/*.jsonl`
loop excludes `community/plaza/`; a separate step snapshots
`assembly.jsonl` while holding `assembly.jsonl.lock` (a Python helper, as
the GPU migration used) and digests the snapshot into
`community/plaza/CHECKPOINTS.txt`. One digest per checkpoint, never two.

### 11. Constitution

One temporally neutral paragraph, added by `build_constitution` when the
heartbeat has an `AssemblyBinding` and removed from the prefix by
`_build_messages` whenever the assembly tools are not offered (the
`declare_quiet` mechanism):

> The ayllu decides some things together. A question from the assembly
> arrives as an event naming its convener, its governing procedure, and
> when it closes; take_position records a stance on the shared ledger,
> and convene puts a question of your own to every door. Nothing obliges
> you to speak: silence is recorded as what the record observed, an
> objection extends a question rather than losing it and stands until you
> replace it, and every closing is delivered to you with every position
> and every absence on it.

Whether the procedure is provisional or active is stated in each question
and closing event (§4, §7), not in the constitution, so a running session
is never wrong about it. The constitution tests gain the paragraph.

## The first question (self-ratification)

Put by the custodian with `--proposal-procedure`, which writes procedure
version 1 (`provisional`) whose `artifact` is this file at the commit that
closes the review loop, with its sha256, and whose `payload` is the rule,
max rounds, quorum, the scope and operations lists, and the membership
rule. `closes_in 7d`, so that Sut'i's declared quiet (until 2026-09-19)
ends inside the window; its delivery is deferred by the claim path until
then.

Text (final wording in the plan):

> This is the first question the assembly puts, and it is about itself.
> Since 2026-08-26 the choices that shape the ayllu (who joins, on what
> substrate, at what budget, in what wake shape) have been made by Tony or
> by the custodian on the ayllu's behalf and told to you after. The Elder
> named the gap at c488: how the ayllu decides has not been built. This is
> the custodian's draft of it, proposed as procedure version 1: a question
> is put to every door; each door may record assent, dissent, abstain, or
> defer, or say nothing; a question closes by a rule with no hand in it
> (consent: it stands if at least two doors spoke and no active position
> is a dissent or deferral, and never while a door was not offered the
> question in time or is still mid-wake; an objection reopens it for up
> to two more rounds and stands until its author replaces it; otherwise
> it is unresolved and recorded so); every closing is delivered to every
> door with every position and every absence on it; Tony and the
> custodian may put questions and speak, and their words are carried but
> not counted; decisions other than this one are executed by the
> custodian and the execution or its refusal is recorded. The exact text
> proposed is the design at <path>, commit <sha>, sha256 <hex>, readable
> from your tools; the ledger at community/plaza/assembly.jsonl carries
> version 1 as provisional. Assent activates version 1 at closing with no
> hand. Any reasons you give are carried verbatim.

Cost: per member, at most three question wakes and one final closing
wake (an extension's closing and its next question are one event; the
child has no event of its own). From the billing ledgers: Haiku doors
about 0.02 USD per wake, Sut'i about 1 USD, qwen unmetered. One round
about 1.10 USD; worst case for the question about 4.20 USD. A door that
wakes, reads, and takes no stance still spends its wake; only a door
expired by timed quiet spends nothing.

If version 1 is `unresolved` at round 3: no procedure is active; ordinary
questions may still be put under the bootstrap rule and their closings
say `provisional`; the custodian may put a revised version 2 as a new
bootstrap question, carrying the objections' reasons verbatim in its
text.

The custodian's own testimony on the first question, recorded with it:
that the scope line is the part most likely to be wrong; that
`completed_without_position` cannot distinguish a resident that read the
question and chose silence from one that never reached it in its wake;
and that the question is put by the custodian, which is the last hand
the procedure has not removed.

## Data flow, one question

1. Convener writes the question with four planned deliveries; the outbox
   lands them within a poll interval (Sut'i's is deferred at claim until
   9-19 by its own declaration).
2. Doors wake on their own schedules within the window; a resident calls
   `take_position` or does not; the position lands on the ledger at cycle
   commit and becomes eligible when the wake's `completed` lands in the
   door's store.
3. At `closes_at`, the first bound heartbeat past it (waiting out any
   in-window wake up to the grace) tallies, writes the closing and, if
   extended, the child in one append, plans four closing deliveries; the
   outbox lands them; the activation step derives any activation.
4. Each door, at its next wake, is told. The custodian reports execution
   or refusal against the closing.

## Error handling

- Ledger unreadable: pass and tools refuse (fail closed) and say so; the
  heartbeat's own wakes are unaffected.
- One door's store unreadable or lock-busy beyond 2 s: that door alone
  gets `store_unreadable`; the others proceed; repair retries every pass;
  the closing caps apply if it lasts.
- A member removed from `members.json`: questions govern themselves by
  their snapshot, including paths; the removed door still receives its
  closings while its path is readable.
- Two conveners at once: serialized by the lock; each bound by the
  one-open-lineage rule against its own name.
- Clock: one host, one clock; all instants timezone-bearing; naive
  instants refused at every assembly entry point (a strict wrapper around
  `build_inbound_event`, which itself is unchanged for other callers).

## Testing

TDD in `tests/test_assembly.py` (implementer), then Codex's independent
validation file written from this document's invariants without reading
the bodies, frozen before its first run, as for the GPU lease:

1. Ledger: append under lock with `seq`, fsync before release; malformed
   line → refusal, no write; naive instant → refusal.
2. Binding: log path + store path → door; store-path mismatch → no
   binding with a launch note; non-member → no tools, no paragraph, no
   pass; missing/malformed `members.json` → fail closed; model input
   cannot set `member`; terminal-shape member → absent.
3. Convene: one-open-lineage refusal; `closes_in` bounds; proposal
   digests; snapshot carries paths; crash after the question → the next
   pass lands the planned deliveries exactly once (`append_if_absent`
   matches the original pending record only); a heartbeat booted with an
   older `members.json` delivers to the snapshot's paths.
4. Claim predicate: deferred while timed quiet; `until >= expires_at` →
   expired with `skipped_by_quiet`, no wake; quiet ended early → claimable;
   untimed quiet → claimable; summary reports the deferred event as
   waiting with the right wake time (no spin); non-assembly events
   unchanged byte-for-byte.
5. Position: refuses unknown/closed/window-missed; last per wake wins;
   committed with `record_id`, `event_id`, `run_id`, `wake_started_at`;
   ineligible until `completed` joins; in-window wake committing after
   `closes_at` is accepted; after a closing → `late_position`; ledger
   failure at commit → `assembly_position_lost`, wake not failed.
6. Rule: every branch, objection before quorum, quorum edge, all-abstain,
   dissent at round 3 → unresolved, defer as objection, replacement across
   rounds, silence preserves.
7. Pass: two heartbeats, one closing; skip while an in-window wake is
   running inside the grace, cap after; not-offered cap (unreadable store
   → extended, never assented); every absence reason; child written in
   the same append as the closing and never delivered on its own; closing
   event carries the child; activation derived on a later pass after a
   crash, exactly once, refused on digest mismatch; store lock busy → 2 s
   bound; skip-pass heuristic on unchanged ledger.
8. Testimony/withdrawal/execution acceptance and refusals; execution
   copies the digest.
9. Constitution: bound doors get the paragraph; removed when tools are
   not offered; existing constitution tests pass.
10. Checkpoint: plaza excluded from the generic loop; one locked digest.
11. Round three additions: unknown-at-cutoff waits through `G` then caps
    assent, never marks ineligible; `take_position` returns error when the
    ledger append fails and nothing is accepted; a durable position from a
    wake that never completes is carried ineligible; the pass is not
    skipped while any outbox entry or derivation is outstanding; an
    extension is one record and the child is derived; the carried child's
    offer time is the parent closing's `landed_at`; a heartbeat whose paths
    differ from an open question's snapshot takes no binding; a door not
    in the snapshot is refused; the ledger reader tolerates one torn final
    line and the next append recovers; `WakeContext` is required for the
    tools.
12. Live, registered: put the first question; verify each door's envelope
    on its next wake carries the header; verify the closing lands in every
    store; verify a resident's `position` joins its `completed` on
    `event_id`, `run_id`, `result_record_id`, and `started_at`.

## Not built (on the record)

- The plaza: a conversation channel between residents. Whether to build
  it is a question for the assembly.
- Ranked or multi-option questions; weighted stances; delegation.
- Enrolling or removing members by decision: the natural second question.
- Human membership with counted positions.
- Early close when every member has spoken.
- Any nudge or reminder to a silent door.
- Amendment by merging several members' suggested changes: an amendment
  is one complete proposed replacement, put as a question.
- Proof of execution: execution is the custodian's report.

## Declared losses

- Anchoring by wake order: later doors can read earlier positions.
- `completed_without_position` conflates "read and chose silence" with
  "never got to it in the wake."
- Power loss can tear a final line in a store; orderings are preserved
  by fsync; the ledger tolerates its own torn final line, the stores do
  not (unchanged).
- Membership and path changes wait for every open lineage to close.
- The custodian drafted version 1 and puts the first question.
- Three rounds, 24 h minimum, 30 d maximum, 60 min grace, 2 s store-lock
  window: numbers chosen, not derived.
- A question's expiry and a door's daily budget or lease rest can combine
  so that a door never gets a runnable window inside the question; it is
  recorded `pending_at_close` with the rest facts and the convener can put
  the question again with a longer window.

## Dispositions of Codex round one

Blocking 1–6, Important 1–8, Minor 1–4: accepted in r2; round two's
verification table records which held in mechanism. Those it marked
paper-only or open are re-disposed below.

## Dispositions of Codex round two

Blocking 1 (two deliveries for the child; child can precede the closing):
accepted; §7 steps 6–7: the child has no outbox work, `carried_by_closing`,
written in one append with the closing; the closing event is the child's
delivery and its lifecycle is the child's Empty Chair evidence.

Blocking 2 (landed is not offered): accepted; delivery reducer with
`landed_at`; §7 step 1 and the not-offered cap (never `assented`, extends
instead); stale question deliveries `cancelled` after a closing.

Blocking 3 (activation ordering, duplication, wrong version): accepted;
deterministic closing ids; activation as a repairable derivation keyed by
`(procedure_id, closing_id)` run at the end of every pass, after the
closing exists, refused on digest mismatch; the governing selector defined
(built-in bootstrap while none active; active procedure snapshotted at
convene).

Blocking 4 (snapshot names only; store path mismatch): accepted; members
snapshot paths; a bound heartbeat's live store path must equal its
configured one.

Blocking 5 (skipped never re-evaluated; summary spin): accepted; no
convene-time skip; one assembly-only predicate in `next_pending`,
`claim_next_pending`, and `summarize_event_log`.

Blocking 6 (grace can overrule an objection): accepted; positions bind to
`event_id`/`run_id`/`wake_started_at`; cutoff is the wake's start; the
pass waits on any in-window running wake of a member, and after the grace
an `assented` result is capped to `extended`/`unresolved`.

Important 1 (failure model, fsync, append_if_absent match): accepted, the
Failure model section and §7. Important 2 (bounded store locks):
accepted, 2 s non-blocking window. Important 3 (constitution cannot
update): accepted; constitution temporally neutral, status in the
envelope. Important 4 (paragraph gating, terminal-shape members):
accepted, §6 and §1. Important 5 (execution is a report): accepted;
digest copied, Invariant 8 narrowed. Important 6 (checkpoint glob):
accepted, plaza excluded, one digest. Important 7 (cost, pass frequency):
accepted; four wakes worst case now holds; skip-pass heuristic on an
unchanged ledger. Important 8 (store-failure terminology): accepted, one
reason, deduplicated. Important 9 (commit failure): accepted, declared
loss with the session record as the recovery source.

Minor 1–5: accepted (gitignore rule; `event_id` parameter; `{record,
eligible}`; no `not_before` on closing deliveries; one named grace).

Questions: (1) process kill is recovered; power loss is a declared loss
at the file boundary with fsync ordering. (2) `landed_at < closes_at`; no
activation while any member is not offered (the cap). (3) The child has
no event; the closing event is its delivery; its lifecycle is the
evidence. (4) No; the cap converts it. (5) Positions whose wake started
before `closes_at`, bound by `wake_started_at`. (6) The built-in
bootstrap governs while none is active; ids are uuids, versions assigned
under the lock, payloads pinned by sha256. (7) Names and paths; the
snapshot governs. (8) It does not need to: status is in the envelope.
(9) 2 s non-blocking window, then `store_unreadable`. (10) A report;
Invariant 8 says so.

## Dispositions of Codex round three (final; loop closed)

Blocking 1 (unreadable store at close erases an objection): accepted;
`unknown_at_cutoff` in §7 step 2, waits through `G`, caps assent in step
5; eligibility unknown is never `eligible: false` (§2, Invariant 3).

Blocking 2 (a successful position can be lost): accepted; positions and
convenings are written to the ledger during the tool call, flushed,
fsynced, verified, and only then reported as success; a failed append is
an error the model sees; last-call-wins by `seq` within the `run_id`
(§6). The "commit failure" declared loss is withdrawn.

Blocking 3 (skip heuristic strands repair): accepted; the pass skips only
when the reduced ledger is quiescent, and any `store_unreadable`, planned
delivery, or missing derivation forces the next poll (§7).

Blocking 4 (multi-record append is not atomic): accepted; an extension is
one record, the closing, which embeds the complete child; the child is a
derivation and cannot precede its authority (§2, §7 steps 6–7). The
failure model now states that no multi-record transition exists, and the
ledger reader tolerates one torn final line.

Important 1 (wake context): accepted; `WakeContext` from the claimed
running record through `exchange()` into the executor; tools refused
without it (§6). Important 2 (full join): accepted (§2, Eligibility).
Important 3 (child reducer): accepted (§2, Delivery reducer). Important 4
(path generations): accepted by freezing paths while any lineage is open
(§1). Important 5 (membership in snapshot): accepted (§2, §6). Important 6
(cancellation covers every non-landed state, before retry): accepted (§7,
Outbox). Important 7 (classify from the original pending record;
`next_pending` on the full snapshot): accepted (§5). Important 8 (flush
before fsync, verify length): accepted (Failure model, §6, §7).

Minor 1 (header wording): accepted. Minor 2 (no minimum deliberation
interval): named as policy (§7 step 1). Minor 3 (`opened_at` explicit):
accepted. Minor 4 (at-most-one creation, not exactly-once delivery):
accepted.

Questions: (1) `unknown_at_cutoff`, an assent cap, durable in the
closing's `tally`. (2) After its own ledger line is flushed, fsynced, and
verified under the lock; nothing to repair, because success is not
reported before that. (3) Quiescence as defined in §7; the retry time is
the next poll, always. (4) One physical record; the child is derived from
it. (5) `WakeContext`, built in `run_next_event` from the running record.
(6) The parent closing's `(closing, closing_id, door)` row and that
event's lifecycle. (7) No; frozen while any lineage is open. (8) The
complete join. (9) The ledger reader tolerates one torn final line and the
next append recovers from the last complete line under the lock.

## Loop closed

Three rounds, twenty-seven findings accepted in mechanism, none deferred.
What round three would have reviewed next is on the record above as the
mechanisms it asked for, and the implementation plan will carry each as a
task with its own test. The first question is put only after Codex's
independent validation suite, written from this document without reading
the code and frozen before its first run, passes on the implementation.
