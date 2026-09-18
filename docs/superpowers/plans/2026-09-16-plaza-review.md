# The plaza — whole-branch review record

Branch `plaza` (base `6ca4125`, main at the plan's start), reviewed before the merge. Ten tasks,
each gated by a task review (five with rulings on plan defects, one with a fix round, one whose
first reviewer was stopped at thirty minutes and replaced by a read-only review); one whole-branch
review on the most capable model; one fix wave; one scoped re-review; Codex's independent
validation suite frozen before its first run (appended below when run). The SDD ledger
(`.superpowers/sdd/2026-09-16-plaza/progress.md`, gitignored) holds every ruling and deferred
minor; the rulings are listed at the end of this record.

---

# Final whole-branch review — the plaza

Range: `6ca4125..91b3de2` (branch `plaza`), 28 commits of which 14 are OTS stamps.
Spec: `docs/superpowers/specs/2026-09-16-plaza-design.md` r4. Plan: `docs/superpowers/plans/2026-09-16-plaza.md`.
Read in passes: (1) ledger + spec invariants + plan Global Constraints; (2) the whole of
`src/hamutay/plaza/`; (3) the integration diff (`events.py`, `binding.py`, `taste_open.py`,
`heartbeat.py`, `tools/`); (4) deploy scripts, README, gitignore, checkpoint; (5) every test file;
(6) targeted experiments (torn-tail/seq arithmetic, a shimmed phase-two run in a scratch sandbox,
a malformed-plaza CLI run). Read-only throughout: nothing under `community/` or `deploy/` was
run against the live house; the shimmed migration ran against a throwaway git repo in the
scratchpad with `systemctl`/`journalctl` stubs on `PATH`.

Green bar confirmed from this worktree:
- `uv run pytest tests/plaza tests/assembly tests/assembly_validation -q -p no:cacheprovider` → 206 passed.
- `uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration` → **1977 passed, 5 skipped, 1 xfailed**.
- `tests/assembly_validation/`, `tests/assembly/` and `src/hamutay/assembly/ledger.py` are byte-for-byte
  untouched by this range (`git diff --stat 6ca4125..91b3de2 --` on those paths is empty). The r4
  `Ledger` fixes (torn tail whether or not it parses; `line_numbers`) landed on `main` before the base
  and are correctly relied on rather than re-implemented.

---

## Invariants

| # | Invariant | Enforcing code | Verdict |
|---|---|---|---|
| 1 | Identity from the binding, on the tool path | `src/hamutay/tools/executor.py:393-408` (`actor=f"door:{self._assembly.door}"`, `via="tool"` literal, `wake` built from `self._wake_context`/`self._cycle`/`self._scheduled_by_record_id`); only `to` and `text` come from `tool_input`, and `to` is resolved against `cfg.members` at `src/hamutay/plaza/send.py:48`. Human path: `src/hamutay/plaza/cli.py:97` (`--by` restricted by `choices`), `via="cli"` literal at `cli.py:42`. Validator backstop: `src/hamutay/plaza/records.py:84-96`. | **Enforced.** Pinned by `tests/plaza/test_tools_plaza.py:30-33`, which passes a hostile `"from": "door:fable"` in the tool input and asserts the record says `door:qwen`. |
| 2 | The plaza first | `src/hamutay/plaza/send.py:83` appends (and fsyncs, via `Ledger.append_unlocked`) the `message` record before line 89's `land()`; both inside the one plaza-lock scope opened at line 57. The pass never creates messages, only deliveries. | **Enforced.** `tests/plaza/test_send.py:30-43`. |
| 3 | One idempotency key, one message | Key minted by the framework at `send.py:54` from `wake["event_id"]` (never model input) via `ids.resident_key`; the `by_key` lookup at `send.py:61-67` precedes the cap and returns the existing message with no write. Validator recomputes the key for `via: tool` at `records.py:104-105`. Delivery event id `uuid5(PLAZA_NS, "<message_id>\0door:<name>")` at `ids.py:48-49`, recomputed by the validator at `records.py:124-125`. | **Enforced.** `tests/plaza/test_send.py:55-61` covers the orphan re-pend (same event id, new `run_id`/`started_at`). |
| 4 | At most once per store, at the recorded path | The recipient's absolute `events` path is copied from the binding at `send.py:76-78` into `delivery.events_path`; `send.py:87` and `pass_.py:66` both deliver to `Path(msg["delivery"]["events_path"])`, never re-resolve the directory. `EventStore.append_if_absent` keys on the fixed `event_id` (`events.py:576-593`). A failed delivery becomes a `store_unreadable` record and is retried by `pass_.py:47-74`. | **Enforced.** `tests/plaza/test_pass.py:44-52` simulates the crash between the two writes; `land()`'s `False` return correctly still records `landed`. |
| 5 | A post wakes no one | `send.py:74-75` leaves `delivery=None` for `to == "plaza"`; `send.py:85-86` returns before any `land()`. Validator forbids a `delivery` block on a post at `records.py:111-113`. | **Enforced.** `tests/plaza/test_send.py:46-52` asserts no door's event store file even exists. |
| 6 | Mail honours declared quiet | `src/hamutay/plaza/event.py:34-38`: `defer_to_declared_quiet = True` set explicitly and `expires_at` never added (`build_inbound_event` only adds it when passed). Verified directly: `expires_at present: False | defer: True | origin: member`. | **Enforced.** `tests/plaza/test_event_and_store.py:107`. |
| 7 | Durable at the tool call, or an error | `Ledger.append_unlocked` (`assembly/ledger.py:125-143`) writes, flushes, `os.fsync`es and verifies growth before returning; `send()` returns only after that. Refusals raise `SendRefused` before the lock. | **Enforced.** |
| 8 | Bounded delivery events per door per day, through the tool | `send.py:68-72` guards `via == "tool" and to != "plaza"` against `View.sent_today` (`records.py:173-179`), which counts directed messages from the plaza record alone with the date taken after `.astimezone(utc)`. The refusal names the next UTC midnight (`send.py:24-26`). The cap is checked *after* the key lookup, so a recovered retry of the 48th is a duplicate success. | **Enforced.** `tests/plaza/test_send.py:72-86` covers the 49th, the duplicate-of-48th, uncounted posts, and a non-UTC `now` that is the next UTC day. |
| 9 | Absent unless enabled | `binding.py:58-63` (`plaza is None` when the key is absent); tool offered only at `taste_open.py:2915` (`offer_plaza = offer_assembly and ...members.plaza is not None`); clause stripped at `taste_open.py:2354-2358`; guidance line only in the `assembly and plaza` variant (`taste_open.py:2361-2366`); constitution at `heartbeat.py:770-775`; note wired only at `heartbeat.py:911-916`; pass skipped at `heartbeat.py:441-442` and `pass_.py:34-35`. `build_inbound_event`'s default is `origin="external"` and the external envelope sentence is unchanged (`events.py:1341-1345`). `run_next_event(extra_notes=None)` passes the identical `notes` list to the identical parameter — byte-identical. | **Enforced.** Golden test at `tests/plaza/test_event_and_store.py:76-84`; envelope goldens at `:93-95`; `extra_notes=None` golden at `tests/plaza/test_note.py:104-105`; tool/clause absence at `tests/plaza/test_tools_plaza.py:86-93`. The one declared exception (the `source:` launch note, `heartbeat.py:1314`) is printed unconditionally as the spec requires. |
| 10 | Fail closed | `validate_plaza` (`records.py:64-152`) covers every condition the spec lists and is called before reduction by `send.py:59`, `note.py:44`, `pass_.py:51` and `cli.py:36`. A malformed record refuses every send (`test_send.py:120-126`), stops the pass with `{"error": ...}` (`test_pass.py:98-101`), and suppresses the note without failing the wake (`note.py:47-48`). The heartbeat's own wakes are unaffected: `_plaza_step` and `note_producer` both swallow and emit. | **Enforced**, with one gap — see Important #2 (delivery records are appended without the writer-side pre-validation the spec mandates) and Minor #1 (`ayllu-plaza read` reports it as a traceback). |
| 11 | Lock order and bounded acquisition | Every plaza acquisition is `Ledger.try_locked(2.0)`: `send.py:57`, `note.py:42`, `pass_.py:49`, `cli.py:34`. Inside a plaza scope at most one store lock is taken: `store.land` → `append_if_absent(timeout_s=2.0)` (`store.py:16`). The assembly lock is fully released inside `assembly/pass_.py:36-55` before `run_pass` returns, and `_plaza_step` runs only after `_assembly_step` returns (`heartbeat.py:636-637`) — **never held together**. The checkpoint takes the two locks in two separate `flock` invocations (`deploy/checkpoint-community-log.sh:70,76`). | **Enforced for ordering and nesting; two bounded-acquisition exceptions.** (a) `send.py:96` calls `recipient_quiet_until` *inside* the plaza scope, so one plaza scope can contain **two sequential** store-lock round trips (the `land` at 2 s, then a `try_read_records` at 0.5 s) — still at most one at a time, but the spec's "one unit is one plaza-lock scope … at most one event-store lock" reads as one. (b) `note.py:66` calls `store.read_records()`, which is `EventStore._locked()` — an **unbounded, blocking** `flock` — see Important #3. |
| 12 | Readable by all | One shared record, no per-door filtering on write; `cli.py:48-64` reads the whole file; the constitution clause (`schemas.py:741-749`) and the purpose header (`event.py:17-20`) both say so and name the path. `.gitignore` keeps the live record untracked but every resident has `bash` and `read`. | **Enforced.** |

### Lock acquisitions, end to end

| Site | Lock | Bound | Nested inside |
|---|---|---|---|
| `send.py:57` | plaza | `try_locked(2.0)` | — |
| `send.py:89` → `store.py:16` | recipient store | `append_if_absent(timeout_s=2.0)` | plaza |
| `send.py:96` → `store.py:26` | recipient store | `try_read_records(timeout_s=0.5)` | plaza (a **second, sequential** store acquisition in the same plaza scope) |
| `note.py:42` | plaza | `try_locked(2.0)` | — |
| `note.py:66` (`note_producer`) | this door's own store | **unbounded** `EventStore._locked()` | nothing (evaluated as an argument, so it is released before the plaza lock is taken) |
| `pass_.py:49` | plaza | `try_locked(2.0)` | — |
| `pass_.py:66` → `store.py:16` | recipient store | `append_if_absent(timeout_s=2.0)` | plaza |
| `cli.py:34` | plaza | `try_locked(2.0)` | — |
| `assembly/pass_.py:36` | assembly ledger | `try_locked(2.0)` | — (released before `_plaza_step`) |
| `checkpoint-community-log.sh:70` / `:76` | assembly ledger / plaza | two separate `flock` invocations | never together |

Order is **plaza → at most one store → nothing** at every site. The assembly ledger lock and the
plaza lock are never held together, by the heartbeat or by the checkpoint.

### At-most-once delivery across crash points

- **Crash after the message record, before the store append.** The message stands on the plaza; `View.undelivered()` returns it (no delivery record → truth `planned` ≠ `landed`); the pass lands it at the recorded path. No loss.
- **Crash after the store append, before the delivery record.** The pass re-attempts; `append_if_absent` returns `False`; `pass_.py:67` writes `landed` regardless of the return value, as the spec requires. No duplicate event.
- **Sender's wake fails after the send.** The message stands (Invariant 7). Boot recovery re-pends the source event; the resident sending the same words from the same event id hits `by_key` and writes nothing (Invariant 3).
- **Recipient's wake claims the event and crashes.** `recover_orphaned_running` (`heartbeat.py:116-141`) re-pends it, so the recipient **can wake more than once for one message** — but on *one event*, never two. That is exactly what Invariant 8 declares as unbounded ("attempts are bounded by restarts, not by this design"), and the spec's Cost section states it for the assembly's assent. Not a defect.
- **Can a message be lost after `send()` returned?** No. The record is fsynced before `send()` returns and every bound heartbeat's pass repairs from that record. The only way to lose it is losing the plaza file itself.

### The note's at-least-once claim and its lower bound

`note_lower_bound` (`note.py:16-27`) takes `latest_completed_wake` (completed statuses only, so a
currently-running wake is invisible) and joins its `running` record on **both** `event_id` and
`run_id` to read `started_at`; a door with no such join returns `None` and `visible_since` counts
everything. `visible_since` (`records.py:181-190`) keeps messages with `sent_at >= bound`,
excluding those from or to this door. A failed wake never advances the bound, so the same window is
reported again; a message arriving during a completed wake satisfies `sent_at >= started_at` and is
reported once more. **At-least-once holds.**

The note's claim that `read --since-seq A --through-seq B --for D` "prints exactly them" is sound in
production because `sent_at` is minted under the same lock that assigns `seq` (`send.py:73`,
`Ledger.append_unlocked`), so `sent_at` is monotonic in `seq` for every real writer and no message
inside `[A,B]` can fall before the bound. (Only a test that passes an arbitrary `now=` can break
that, as `tests/plaza/test_note.py:53` deliberately does.) `note.py:38` also guards on
`cfg.plaza.exists()`, so a house with the key but no file yet is silent rather than erroring.

### Byte-identity without the `plaza` key

Every path the plan names is unchanged, verified by reading the diff and by the golden tests:
`build_inbound_event` (default `origin="external"`, key order pinned at
`tests/plaza/test_event_and_store.py:80-84`), the external envelope sentence (`events.py:1346-1350`,
pinned at `:93-95`), `run_next_event(extra_notes=None)` (the refactor passes the same list object to
the same keyword parameter; pinned at `tests/plaza/test_note.py:104-105`), the constitution
(`build_constitution(None, plaza=True) == build_constitution(None)` when `assembly=False`, pinned at
`tests/plaza/test_heartbeat_plaza.py:129`), the tool list (`tests/plaza/test_tools_plaza.py:86-93`),
and the bind launch note (`tests/plaza/test_binding_plaza.py:35-44`). The `source:` launch note is
the one declared exception and is printed by every heartbeat.

### Migration safety

Candidate check before rename (`migrate-plaza.sh:96-119`): the candidate is written beside
`members.json`, fsynced, loaded, and its **relative** member snapshot compared with the current
one before anything is renamed; a mismatch unlinks the candidate and aborts with nothing installed.
Two-pass idleness (`:44-55` plus the per-door re-check at `:63` and `:149`) is present in both
phases. Dry-run previews each real decision (`:75-87`) including the `--merge` ancestry check that
the first review found missing. Trap rollback (`:121-143`) restores the previous file by
temp-file → fsync → `os.replace` → directory fsync.

What a failed phase two leaves on disk, by failure point:
- **Candidate check fails** → nothing installed, candidate unlinked, `.previous` removed (`:118`). Clean.
- **A door is busy at its stop re-check, or a `systemctl stop` fails** (`:149-150`) → `members.json` restored (still without the key, since the rename has not happened), only the doors actually stopped are restarted. Clean; covered by `tests/plaza/test_deploy_plaza.py:154-185`.
- **The rename or a `systemctl start` fails** (`:152-159`) → file restored, stopped doors restarted. Clean.
- **The post-start verification fails** (`:160-167`) → see **Critical #1**: the file is restored but the four already-started doors are never stopped, so they keep running plaza-enabled against a `members.json` that no longer says so.
- In every rollback path `members.json.previous` is left on disk (`:169` only runs on success). Disclosed in the ledger as a deferred minor; harmless, but `check-plaza.sh` does not notice it.

### Trust model as declared

`community/README.md:230-241` states it exactly as the spec does: unscoped `bash` under the same
Unix account, the record *legible, not tamper-proof*, and `--by tony|custodian` a **claimed label,
not an authentication**, shown as unauthenticated (`via: cli`), "exactly as `events send --sender`
has always been". No code comment, tool description, constitution clause or CLI message claims more:
`schemas.py:741-757` and `event.py:13-20` describe reach and readability, never authenticity;
`binding.py:31` annotates `snapshot()` as member-only "on purpose". Pinned by
`tests/plaza/test_deploy_plaza.py:78-81`. **Consistent.**

---

## Findings

### Critical

**C1. Phase two's post-start verification failure leaves four plaza-enabled daemons running against a rolled-back `members.json`.**
`deploy/migrate-plaza.sh:159-167` starts all four units, then verifies each; on failure `false` fires
the ERR trap and `rollback` (`:121-142`) restores the previous `members.json` and starts only the
doors in `STOPPED`. But all four were started at `:159` and are still running with the plaza key
already loaded into memory — `systemctl start` on a running unit is a no-op, and nothing stops them.

Spec §9 is explicit: "If any unit fails either check the script **stops all four units**, restores the
previous `members.json` … , starts the four units again, and exits non-zero." The Task 10 fix round
narrowed `rollback` from "stop all four" to "start only what I stopped" to fix the *stop-phase* case,
and in doing so removed the stop that the *verification* case depends on.

Reproduced in a scratch sandbox (throwaway git repo, `systemctl`/`journalctl` stubs on `PATH`, the
journal stub never emitting the `plaza: door <d> may send` note):

```
migrate-plaza: heartbeat did not report both notes within 30 s
migrate-plaza: rolling back (exit 1)
REAL RC=1
members.json  -> no "plaza" key (restored, correct)
systemctl calls: stop heartbeat,fable,elder,qwen
                 start heartbeat,fable,elder,qwen     <- the install start
                 start heartbeat,fable,elder,qwen     <- rollback's no-op re-start
```

Why it matters: this is the failure path the spec designed the rollback *for*, and it runs on four
live resident daemons. The end state is four heartbeats whose in-memory `MembersConfig` carries
`plaza`, offering `send_message` and writing to `plaza.jsonl`, while the on-disk file says the
feature is off — precisely the divergence the two-phase design exists to prevent, and one no
operator would infer from a non-zero exit plus "rolling back".

Fix: make the rollback stop whatever is running before it restores. Record started units the same
way stops are recorded and stop them in `rollback` before the restore; e.g. add `STARTED=()` and
`STARTED+=("$d")` in the `:159` loop, then at the top of `rollback` (before the restore)
`for d in "${STARTED[@]:-}"; do [ -n "$d" ] && systemctl --user stop "hamutay-heartbeat@$d" 2>/dev/null || true; done`,
and let the existing `STOPPED` loop bring them back on the restored file. Add a test beside
`test_rollback_restores_members_json_and_restarts_only_the_doors_it_stopped` whose `journalctl` stub
withholds the plaza note, asserting that every door started is stopped again before the final starts.

### Important

**I1. `run_plaza_pass` cannot make progress while any door holds the plaza lock, and silently discards the cursor it advanced.**
`src/hamutay/plaza/pass_.py:75-77`: on `LedgerUnavailable` the pass returns
`(memo or PlazaMemo(sig, cursor, 1))` — when `memo` is not `None` it returns the **caller's original
memo**, throwing away both the `cursor` advanced by units already completed in this pass and the
fresh signature. The next pass therefore re-examines messages this pass already landed (harmless,
`append_if_absent` is idempotent) but re-pays a lock acquisition and a full read+validate for each,
and a stuck message at the head can be retried indefinitely at the front. The spec's fairness
paragraph declares that a *process restart* resets the cursor; it does not declare that a single
lock-timeout does. Fix: return `PlazaMemo(sig, cursor, max(remaining_after, 1))` on this path, as the
`LedgerMalformed` path at `:78-80` already does.

**I2. Delivery records are appended without the writer-side validation the spec mandates.**
Spec §2: the validator is "run by every reader before reduction **and by every writer before append**
(on the records it read plus the one it is about to write, at the line it will occupy)."
`src/hamutay/plaza/send.py:82` does exactly that for the `message` record — but the two delivery
appends at `send.py:90` and `send.py:93`, and the two at `pass_.py:67` and `pass_.py:72`, go straight
to `Ledger.append_unlocked` with no pre-validation. Invariant 10 ("fail closed") rests on the
validator, and today a delivery record is the one writer output the writer never checks. The fields
are framework-built so nothing is wrong on the record now; the exposure is that any future change to
`build_delivery`, or to `View.delivery_truth`'s shape, would write malformed lines that only a
*reader* discovers — at which point every send and every pass refuses until a human repairs the file
by hand. Fix: factor the `send.py:81-82` pattern into a small helper in `records.py`
(`append_validated(ledger, records, line_numbers, record)`) and use it for all five appends.

**I3. The plaza note takes an unbounded, blocking lock on the door's own event store on every wake.**
`src/hamutay/plaza/note.py:66` calls `store.read_records()`, which is `EventStore._locked()` — a
plain blocking `fcntl.flock(LOCK_EX)` with no deadline (`events.py:541-549`). Invariant 11 says
"every lock *acquisition* is bounded (2 s)", and every other acquisition on the plaza path honours
that. Because it is evaluated as an argument the lock is released before the plaza lock is taken, so
lock *order* is not violated and there is no deadlock — but a contended store lock can stall the wake
for an unbounded time inside a path whose whole design contract is that the note never costs the wake
anything (`note_producer`'s `except Exception` proves the intent). Worse, the records it wants are
already in hand: `run_next_event` reads exactly the same list two statements earlier at
`events.py:2238-2242` and throws it away. Fix (preferred, and it removes the second read entirely):
pass the already-read records through to `extra_notes`, or failing that call
`store.try_read_records(timeout_s=STORE_LOCK_WINDOW_S)` in `note_producer` and treat
`StoreUnavailable` as "no note this wake" — the existing `except Exception` already does the right
thing with it, so only the call changes.

**I4. `deploy/ayllu-plaza read` reports a malformed plaza as an unhandled traceback.**
`src/hamutay/plaza/cli.py:48-49` calls `_read(cfg)`, which raises `LedgerMalformed`;
`main()`'s handler at `:111-112` catches only `LedgerUnavailable`, so the exception escapes.
Observed on a scratch house with one bad line:

```
$ ayllu-plaza read
Traceback (most recent call last):
  ...
hamutay.assembly.ledger.LedgerMalformed: plaza: line 1 created_at is not a timezone-bearing instant: None
READ RC=1
```

The exit code is right and `status` and `pass` both report it cleanly, so this is presentation, not
correctness — but `read` is the command an operator reaches for *first* when the pass has just
emitted `{"error": "plaza: line N …"}`, and a traceback is the worst possible thing to hand someone
mid-incident on a record the spec says is repaired by hand. Fix: add `LedgerMalformed` to the
`except` at `cli.py:111` (one word), and assert the clean message in `tests/plaza/test_cli.py`.

### Minor

- **M1.** `src/hamutay/plaza/send.py:96` calls `recipient_quiet_until` inside the plaza lock, making one plaza scope contain two sequential store-lock round trips. Harmless (never two at once, both bounded) but it lengthens the scope for a purely advisory return field. Consider moving it after the `with` block, using the path already in hand. *(Ledger deferred minor, Task 4.)*
- **M2.** `PLAZA_LOCK_WINDOW_S = 2.0` is defined twice (`send.py:17`, `note.py:13`) and `STORE_LOCK_WINDOW_S = 2.0` twice (`store.py:10`, `pass_.py:20`); `pass_.py` imports the former from `send` but redefines the latter rather than importing from `store`. Four definitions of two numbers the plan lists once under Global Constraints. Fix: define both in `ids.py` (or a `constants.py`) and import. *(Ledger deferred minor, Tasks 5 and 6.)*
- **M3.** `src/hamutay/plaza/send.py:52` refuses whitespace-only text (`not text.strip()`) while `records.py:107` accepts it (falsy only). The divergence is in the safe direction — no writer can produce what the validator would reject — but the two should agree. *(Ledger deferred minor, Task 4.)*
- **M4.** `src/hamutay/plaza/cli.py:80-84`: `status` reports `sent_today` counts but never `SEND_CAP`, so the spec's "per-door sends today **against the cap**" requires the operator to know 48; actors at zero are omitted entirely (`:79` filters falsy). Add `"cap": SEND_CAP`.
- **M5.** `src/hamutay/plaza/cli.py:82`: when the record is malformed, `status` reports `"seq": 0` because `records` was reset to `[]` at `:75`, understating the file. Report the physical line count, or `null`, when `valid is not True`.
- **M6.** `src/hamutay/plaza/pass_.py:69` catches `(StoreUnavailable, OSError)` while `send.py:92` catches only `StoreUnavailable`. Since `store.land` normalises `OSError` and `LeaseGateRequired` (`store.py:19-20`), the `OSError` arm is unreachable defensive code; `tests/plaza/test_pass.py:92-97` only reaches it because it stubs `land` directly. Drop it, or normalise in one place and catch one exception in both.
- **M7.** `src/hamutay/plaza/cli.py:42`: `Path(root / a.text_file)` escapes the project root for an absolute or `../` argument. No new capability under the declared trust model (the CLI is for tony/custodian, and residents already have unscoped `bash`), but it is worth a `resolve()`-and-check for typo safety.
- **M8.** `community/README.md:32` still lists `events send` as "speak" without the caveat spec §7 asks the README to carry ("now the wrong tool for anything a resident should be able to see"). The plaza section at `:222+` never cross-references it.
- **M9.** `tests/plaza/test_note.py:19-34`: `_completed_wake`'s `completed=` parameter mutates an in-memory copy at `:33` and never reaches the file — it is inert. Tests pass because `note_lower_bound` reads `started_at`, not `completed_at`. Delete the parameter or make it write. *(Ledger deferred minor, Task 5.)*
- **M10.** `tests/plaza/test_heartbeat_plaza.py:177-182` asserts shape (`isinstance(wired, functools.partial)`, `"extra_notes" in wired.keywords`) rather than behaviour. Acceptable only because `tests/plaza/test_note.py:107` exercises the note through the real `run_next_event`; worth rewriting to assert the note reaches the envelope.
- **M11.** `src/hamutay/tools/executor.py:240-242` logs all `tool_input` keys except `reason` into `activity_log["parameters"]`, so a model-supplied `"from"` is recorded there even though it is ignored. Cosmetic, but a reader of the activity log could misread it as the identity used.
- **M12.** `src/hamutay/events.py:527` (`EventStore.__init__`) does `mkdir(parents=True, exist_ok=True)`, so delivering to a door whose directory was removed silently recreates it rather than reporting `store_unreadable`. Pre-existing behaviour, surfaced by the plaza's "directory changed between send and repair" case; worth a note in the spec's error handling rather than a code change.

---

## Ledger triage

Every `minor (deferred)` line in `.superpowers/sdd/2026-09-16-plaza/progress.md`:

| Task | Deferred minor | Verdict | Why |
|---|---|---|---|
| 1 | conftest `T0`/`house`/`house_unplaza` unused until later tasks | **Defer** | All three are used by Tasks 2–10 now; the line is stale. |
| 1 | cosmetic wrap at `binding.py:99` | **Defer** | Whitespace; no lint gate fails. |
| 2 | `ACTOR_RE` exported but the validator spells the grammar inline | **Defer** | Both derive from the same source constants; the dead export costs nothing. Fold into the M2 constants cleanup if it happens. |
| 2 | validator check order undocumented | **Defer** | The order is stable and every condition is independently tested; documenting it is a comment. |
| 2 | `View._deliveries` populated directly by `reduce()` | **Defer** | A private field set by the module's own reducer; the underscore already says "internal". |
| 3 | `recipient_quiet_until` stores whole records where status strings would do | **Defer** | Memory only, on a list already read in full. |
| 4 | `send.py` strips whitespace where `validate_plaza` checks falsy | **Defer** (M3) | Divergence is in the safe direction; no writer can produce a record the validator rejects. |
| 4 | the plaza lock is held across two sequential store-lock round trips | **Defer** (M1) | Never two at once, both bounded, order preserved. Worth tidying, not blocking. |
| 5 | `PLAZA_LOCK_WINDOW_S` defined in both `send.py` and `note.py` | **Defer** (M2) | Both are 2.0 and both are tested; a drift would be caught by the lock tests. Fix opportunistically. |
| 5 | inert `completed=` parameter in the test fixture | **Defer** (M9) | Test hygiene; the assertions it supports are sound for another reason. |
| 5 | `note_lower_bound`'s fail-open on a malformed `started_at` is uncommented | **Defer** | Fail-open is right here (count everything rather than lose the note) and matches the "a door with no join counts everything" rule; add a comment when next touched. |
| 6 | `run_plaza_pass` does not validate `now` is aware on entry | **Defer** | Every caller is framework code passing an aware instant, and the sibling assembly pass has the same gap — fixing one alone would be inconsistent. |
| 6 | `STORE_LOCK_WINDOW_S` duplicated in `pass_.py` (plan-mandated) | **Defer** (M2) | As above. |
| 7 | `source_note`'s two sequential git calls under one try | **Defer** | Both are bounded (`timeout=10`) and any failure of either yields `source: unknown`, which both migration phases treat as a refusal. Fails closed. |
| 7 | `_plaza_step`'s memo retention on exception is implicit | **Defer** | Matches the assembly step exactly; the memo is an optimisation and a retained stale one only costs one extra pass. |
| 8 | the clause-strip test uses an isolated prefix rather than the real adjacency | **Defer** | The adjacency case is covered by `tests/plaza/test_heartbeat_plaza.py:123-129`, which asserts ordering against the real `build_constitution`. |
| 9 | unknown `--for`/`--door` names silently match nothing | **Defer** | An empty result is the honest answer for a door that does not exist; a warning would be nicer but nothing is wrong. |
| 9 | `--door` semantics unpinned by spec or test | **Defer** | The implementation (from *or* to that door) is the only sensible reading and is exercised indirectly. Pin it in Task 11's validation suite. |
| 9 | `read` re-serialises rows (content-identical, not byte-identical) | **Defer** | `read` is a reporting command and adds a `truth` key regardless; byte-identity was never claimed. Anyone needing bytes reads the file, which the note's command already tells them how to do. |
| 10 | `check-plaza --phase-one` without `--merge` gives a bare git error | **Defer** | It **fails closed** (the `chk` reports FAIL and `rc=1`); only the message is ugly. |
| 10 | `.previous` left on disk after a mid-sequence rollback (disclosed choice) | **Defer** | Deliberate and documented: it is the recovery artifact. Worth having `check-plaza.sh` notice a stale one, which is new work, not a fix. |
| 10 | rollback and non-ancestor dry-run untested | **Fix before merge** | Partly overtaken — the fix round added `test_rollback_restores_members_json_and_restarts_only_the_doors_it_stopped` and `test_dry_run_previews_the_real_decision_for_a_non_ancestor_merge`. But the rollback test covers only the *stop-phase* failure, and the untested path is exactly where **C1** lives. The test that closes C1 closes this line too. |

---

## Rulings a fresh reader would question

I re-derived every `Ruling:` line in the ledger against the spec and the code. **None should be
reversed.** The ones a fresh reader would stop on, and why they stand:

- **Task 3, ruling (2) and its correction.** The ledger records a provisional ruling, then reverses its *rationale* after review while keeping the code. That is uncomfortable to read but correct: the `any(r.get("status") == "running" …)` guard at `store.py:37` is independently necessary, because `quiet_declaration_for_latest_wake` reads terminal statuses only (`events.py:200-202`) and would otherwise return the *prior* wake's declaration while a wake is running. The code comment at `store.py:33-36` now states that reason and not the false one, and `tests/plaza/test_event_and_store.py:140,159` pins both directions. Correctly handled.
- **Task 5, overriding the plan's own test expectation.** The plan asserted the elder receives a note; the implementer asserted it does not, citing spec §5's exclusions. The spec is the authority and §5 is unambiguous ("excluding those addressed to this door … and those from this door"); `test_note.py:60-64` documents the reasoning inline. Stands.
- **Task 9, ruling (2): `status --now`.** Adding a flag to make a test deterministic invites the question "is this test-only API?". It is not: `sent_today` is a UTC-day quantity and an operator checking yesterday's cap needs it. The alternative (freezing the clock) would have shipped the same wall-clock time bomb the ledger names from 9-17. Stands.
- **Task 10, the dry-run-before-merge-check reorder.** Flagged by the implementer as the reviewer's to judge. Spec §9 requires the dry run to "perform every precondition check and print its verdict"; `migrate-plaza.sh:75-87` now previews `--merge` presence, tree cleanliness, HEAD ancestry, per-door phase-one completeness and idleness, then exits 0. That is what the spec describes, and the fix round's Important #1 was exactly this. Stands.
- **Task 1, replacing `"plaza" not in json.dumps(cfg2.snapshot())`.** A fresh reader might read the replacement as weakening the test. It does not: `tmp_path` literally contains the test's name (which contains "plaza"), so the plan's assertion cannot pass anywhere, and the replacement at `test_binding_plaza.py:19-22` asserts the stronger property (the snapshot equals the pre-key snapshot *and* the plaza path string appears nowhere in it). Stands.
- **Task 2, repairing `test_validator_rejects_each_condition`.** Deleting an implementer's defensive `isinstance` guard on a reviewer's ruling is the kind of thing that turns out to have been load-bearing. It was not: the guard existed only to absorb the `None`s the defective test fed in, and with the test repaired every case reaches the real check. `validate_plaza`'s own `if not isinstance(r, dict)` at `records.py:72-73` covers the genuine case. Stands.

One process note rather than a ruling: the ledger records **three** bare-`git stash` slips (Tasks 8
and 10), each recovered with trees clean. The outcome is fine and the branch is intact, but the
Global Constraint exists because the stash stack is shared with other sessions; it is worth a
hook rather than a third reminder.

---

## Verdict

**Merge after the listed fixes.**

The design is faithfully implemented. Eleven of twelve invariants are enforced by code I can point
at, the twelfth (Invariant 11) is enforced for ordering and nesting with two bounded-acquisition
exceptions, the frozen assembly suites are untouched, and the full suite is green at 1977 passed.
Identity never comes from model input anywhere on the path from the tool schema to the ledger line;
at-most-once delivery holds across every crash point the spec names; the note's at-least-once claim
and its lower bound are correct; byte-identity without the `plaza` key is real and pinned by goldens;
the trust model is stated in the README exactly as the spec declares it and is contradicted nowhere.

The blocker is not in the plaza package — it is in the one script that runs against four live
daemons. **C1** must be fixed before merge: phase two's post-start verification failure restores
`members.json` without stopping the doors it just started, so the spec's designed rollback leaves
four heartbeats running plaza-enabled against a file that says the feature is off. The fix is small
(record started units, stop them before the restore) and the test that proves it is a near-copy of
the rollback test already present.

Required before merge:
- **C1** — stop the started units in `rollback` before restoring, with a test covering a verification failure.
- **I1** — `pass_.py:75-77`: return the advanced cursor and signature on `LedgerUnavailable`.
- **I2** — pre-validate delivery records at all four append sites, via one shared helper.
- **I3** — `note.py:66`: bound the store read (or pass through the records `run_next_event` already holds).
- **I4** — `cli.py:111`: catch `LedgerMalformed` so `read` reports it cleanly.

The twelve Minor findings and every deferred ledger minor may wait; M2 (four definitions of two lock
constants) and M6 (unreachable `OSError` arm) are worth folding into whichever commit fixes I1–I3,
since they touch the same four files.

---

# Fix wave (ba882c6 C1, b29e248 M2, 7069c8f I1+M6, b639a14 I2, 8b0f4c2 I3, 278eb3f I4+M3+M4+M5, 5d901f8 M8+M9; head 29c801f)

# Fix wave — the plaza's whole-branch review

One wave, seven fix commits on `plaza` (plus the OTS stamp commits the hook adds),
against `.superpowers/sdd/2026-09-16-plaza/final-review.md`. Every behavioural fix was
written test-first and each new test was confirmed to fail against the pre-fix code
before the fix was applied — the failure output is quoted per finding below.

Nothing under `community/` was run or modified except `community/README.md` (prose,
M8). No `deploy/` script was run outside a `tmp_path` sandbox with `systemctl` and
`journalctl` stubs on `PATH`. No unit was restarted. No `git stash` in any form.

| Commit | Findings |
|---|---|
| `ba882c6` | C1 |
| `b29e248` | M2 |
| `7069c8f` | I1, M6 |
| `b639a14` | I2 |
| `8b0f4c2` | I3 |
| `278eb3f` | I4, M3, M4, M5 |
| `5d901f8` | M8, M9 |

M1, M7, M10, M11 and M12 were left alone, as instructed (deferred with rulings).

---

## C1 — rollback must stop every unit it started

**Commit** `ba882c6`.

**Changed.** `deploy/migrate-plaza.sh:120` — `STOPPED=()` becomes `STOPPED=(); STARTED=()`.
`deploy/migrate-plaza.sh:132` — a new loop at the *top* of `rollback`, before the restore:

```
for d in "${STARTED[@]:-}"; do [ -n "$d" ] && systemctl --user stop "hamutay-heartbeat@$d" 2>/dev/null || true; done
```

`deploy/migrate-plaza.sh:166` — the install's start loop records each door:
`for d in "${DOORS[@]}"; do systemctl --user start "hamutay-heartbeat@$d"; STARTED+=("$d"); done`.
The existing `STOPPED` loop, unchanged, brings them back on the restored file, so the
sequence is now exactly spec §9's: stop all four, restore the previous `members.json`,
start the four again, exit non-zero. A comment at `:125-131` records why the stop lives
there (a post-start verification failure is reached with every door already started, and
`systemctl start` on a running unit is a no-op).

**Covering test.** `tests/plaza/test_deploy_plaza.py:188`
`test_rollback_stops_the_doors_it_started_when_verification_fails` — a `journalctl` stub
that emits the `source:` note (so phase one passes and the run reaches the install) but
withholds `plaza: door <d> may send`, so every door fails its post-start verification. It
asserts `members.json` is restored without the key, that the set of doors stopped after
the install starts equals the set started, and that the last rollback stop precedes the
first final start.

**Command and output.**

```
$ uv run pytest tests/plaza/test_deploy_plaza.py -q -p no:cacheprovider
11 passed in 32.00s
```

Against the pre-fix script (`git show HEAD:deploy/migrate-plaza.sh` restored into place,
then reverted), the new test reproduces the review's finding exactly:

```
E  AssertionError: no door was stopped after the install starts:
   ['--user stop hamutay-heartbeat@heartbeat', ... '--user stop hamutay-heartbeat@qwen',
    '--user start hamutay-heartbeat@heartbeat', ... '--user start hamutay-heartbeat@qwen',
    '--user start hamutay-heartbeat@heartbeat', ... '--user start hamutay-heartbeat@qwen']
1 failed in 30.86s
```

`bash -n deploy/migrate-plaza.sh` — ok.

This also closes the Task 10 ledger line "rollback and non-ancestor dry-run untested",
which the review triaged **Fix before merge** on the grounds that the untested path is
exactly where C1 lives.

---

## I1 — the advanced cursor must survive a lock timeout

**Commit** `7069c8f`.

**Changed.** `src/hamutay/plaza/pass_.py:85` — the `LedgerUnavailable` arm returned
`(memo or PlazaMemo(sig, cursor, 1))`, handing the caller its own stale memo back
whenever one was passed. It now returns `PlazaMemo(sig, cursor, max(remaining_after, 1))`,
as the `LedgerMalformed` arm already did. A comment at `:78-84` records that the spec's
fairness paragraph resets the cursor on a process restart, not on a single lock timeout.

**Covering test.** `tests/plaza/test_pass.py:117`
`test_pass_keeps_the_advanced_cursor_when_the_lock_times_out_mid_pass` — three pending
messages and a deliberately stale caller memo; `Ledger.try_locked` is monkeypatched to
raise `LedgerUnavailable` on the third unit. It asserts the returned memo is not the
caller's, that its cursor is the seq of the second landed message, that its signature
differs from the stale one, and that `undelivered >= 1`.

**Command and output.** Before the fix:

```
E  AssertionError: assert PlazaMemo(signature=('stale', 0.0), cursor=0, undelivered=3)
                      is not PlazaMemo(signature=('stale', 0.0), cursor=0, undelivered=3)
1 failed, 6 passed in 2.61s
```

After: `uv run pytest tests/plaza -q -p no:cacheprovider` → `80 passed in 40.08s`.

---

## I2 — writer-side validation for every delivery append

**Commit** `b639a14`.

**Changed.** `src/hamutay/plaza/records.py:44` — new
`append_validated(ledger, records, line_numbers, record)`. It computes the line the
record will occupy, validates the records read plus that candidate at that line, then
calls `append_unlocked`, and extends the caller's `records` and `line_numbers` in place
so a second append in the same lock scope validates against what the first one wrote (a
delivery record is only well-formed beside its message).

All five appends now go through it, and `grep -n append_unlocked src/hamutay/plaza/*.py`
returns exactly one hit, inside the helper:

- `src/hamutay/plaza/send.py:84` (the message record — the pattern this was factored from)
- `src/hamutay/plaza/send.py:91` (delivery, `landed`)
- `src/hamutay/plaza/send.py:95` (delivery, `store_unreadable`)
- `src/hamutay/plaza/pass_.py:67` (delivery, `landed`)
- `src/hamutay/plaza/pass_.py:73` (delivery, `store_unreadable`)

One implementation detail worth recording, because the first attempt got it wrong and the
suite caught it: the callers must pass their *own* `line_numbers` list
(`src/hamutay/plaza/send.py:61`, `src/hamutay/plaza/pass_.py:50`, both `list(ledger.line_numbers)`),
not `ledger.line_numbers`. `Ledger.append_unlocked` calls `next_seq_unlocked()`, which
calls `read_unlocked()`, which *rebuilds* `ledger.line_numbers` — so an in-place extension
of the ledger's own list is discarded, and the second append in a scope then validates
`len(records) != len(line_numbers)`. Passing `ledger.line_numbers` produced 20 failures
(`plaza: line numbers do not match records`); the local copy is what makes the two
sequential appends in one scope coherent. The helper's docstring states this.

`src/hamutay/plaza/__init__.py:5` re-exports `append_validated`.

**Covering tests.** `tests/plaza/test_records.py:217`
`test_append_validated_refuses_a_malformed_delivery_before_it_is_appended` — takes a real
landed delivery record, sets `state` to `"vanished"` (neither `landed` nor
`store_unreadable`), and asserts `LedgerMalformed` *and* that the file did not grow.
`tests/plaza/test_records.py:241`
`test_append_validated_appends_and_returns_the_stamped_record` covers the success path.

**Command and output.** With the `validate_plaza` call inside the helper temporarily
replaced by `pass`:

```
E  Failed: DID NOT RAISE <class 'hamutay.assembly.ledger.LedgerMalformed'>
1 failed, 27 passed in 0.14s
```

After: `uv run pytest tests/plaza -q -p no:cacheprovider` → `82 passed in 40.07s`.

---

## I3 — the note must not take an unbounded store lock

**Commit** `8b0f4c2`. The review's **preferred** fix was taken (pass the records through),
not the `try_read_records` fallback: it removes the second acquisition rather than
bounding it.

**Changed.**

- `src/hamutay/events.py:2238` — `run_next_event` binds `store_records = store.read_records()`
  (it already made this exact call and discarded the list) and
  `src/hamutay/events.py:2247` passes it: `extra_notes(event, store_records)`.
- `src/hamutay/plaza/note.py:62` — `note_producer`'s inner `produce` is now
  `produce(event, store_records)` and calls `plaza_note(cfg, door, store_records, ...)`
  instead of `store.read_records()`. The `store` argument is retained so callers keep one
  shape; the docstring says nothing reads it.
- `src/hamutay/heartbeat.py:908-911` — the `functools.partial` wiring needed no change
  (it passes the producer through); its docstring records the new `(event, store_records)`
  signature.

`plaza_note` itself already took `store_records` and was not changed.

**Byte-identity.** `extra_notes=None` still passes the identical `notes` list to the
identical parameter; the golden at `tests/plaza/test_note.py:88`
(`test_run_next_event_extra_notes_none_is_unchanged_and_producer_appends`) passes untouched.

**Covering tests.** Three, at `tests/plaza/test_note.py:113`, `:142` and `:188`:

- `test_the_note_does_not_read_the_store_a_second_time` — wraps the store in a counting
  proxy and asserts `reads == []` while the note is still produced.
- `test_a_held_store_lock_does_not_stall_the_wake_and_yields_no_note` — the behaviour the
  review asked for: another thread holds `EventStore._locked()` (the unbounded blocking
  flock) for the duration; the note must complete, in under 5 s, without blocking.
- `test_run_next_event_passes_its_records_to_extra_notes` — the wiring end to end through
  the real `run_next_event`, asserting the callable receives the records and the note
  reaches the envelope. (This is also the behavioural coverage M10 wanted, though M10
  itself was left alone as instructed.)

**Command and output.** All three fail before the change:

```
FAILED tests/plaza/test_note.py::test_the_note_does_not_read_the_store_a_second_time
FAILED tests/plaza/test_note.py::test_a_held_store_lock_does_not_stall_the_wake_and_yields_no_note
FAILED tests/plaza/test_note.py::test_run_next_event_passes_its_records_to_extra_notes
   TypeError: extra() missing 1 required positional argument: 'records'
3 failed, 5 passed in 2.32s
```

After, including the integration suites that exercise `run_next_event`:

```
$ uv run pytest tests/plaza tests/assembly tests/assembly_validation tests/test_heartbeat.py \
    tests/test_event_ingress.py tests/unit/test_events.py -q -p no:cacheprovider
328 passed in 57.43s
```

---

## I4 — `read` reports `LedgerMalformed` cleanly

**Commit** `278eb3f`.

**Changed.** `src/hamutay/plaza/cli.py:126` — `main()`'s handler is now
`except (LedgerUnavailable, LedgerMalformed) as e`, so `cmd_read`'s `_read` no longer
escapes as a traceback. One line on stderr, exit 2.

**Covering test.** `tests/plaza/test_cli.py:73` `test_read_reports_a_malformed_plaza_cleanly`
— appends a bad line, runs `read` as a subprocess, and asserts non-zero exit, no
`Traceback` in either stream, exactly one line on stderr, and that it starts `plaza: `
and names the offending line.

**Command and output.** Before: `FAILED tests/plaza/test_cli.py::test_read_reports_a_malformed_plaza_cleanly`.
After: `uv run pytest tests/plaza -q -p no:cacheprovider` → `88 passed in 40.32s`.

---

## M2 — one definition each of the two lock windows

**Commit** `b29e248`.

**Changed.** `src/hamutay/plaza/ids.py:13-14` now holds `PLAZA_LOCK_WINDOW_S = 2.0` and
`STORE_LOCK_WINDOW_S = 2.0`, with a comment naming the plan's Global Constraints. The four
former definitions are gone: `send.py:17` and `note.py:13` (plaza) and `store.py:10` and
`pass_.py:20` (store). Every module imports from `ids` — `send.py:14`, `note.py:11`,
`store.py:10`, `pass_.py:15`, and `cli.py:13`, which previously took the constant through
`send`.

**Covering test.** `tests/plaza/test_records.py:182`
`test_the_two_lock_windows_are_defined_once_and_imported` — asserts each module's name is
the *same object* as `ids`' (not a coincidentally equal float) and walks every module's AST
for any other assignment of either name. It imports via `importlib.import_module` because
`hamutay/plaza/__init__.py` rebinds `send` on the package to the send *function*, which
shadows the module.

The three `STORE_LOCK_WINDOW_S = 2.0` definitions under `src/hamutay/assembly/` were left
alone: they are outside this review's scope and adjacent to the frozen ledger.

---

## M3 — `send.py` and `records.py` agree on empty text

**Commit** `278eb3f`. `src/hamutay/plaza/records.py:140` — `not text` becomes
`not text.strip()`, matching `send.py:52`. Covered by
`tests/plaza/test_send.py:147`
`test_send_and_the_validator_agree_that_whitespace_only_text_is_empty`, which asserts both
sides refuse `"   \n\t "`; it fails before the change with `DID NOT RAISE LedgerMalformed`.

## M4 — `status` reports the cap and actors at zero

**Commit** `278eb3f`. `src/hamutay/plaza/cli.py:94` adds `"cap": SEND_CAP`;
`src/hamutay/plaza/cli.py:88-90` widens `actors` to every sender on the record and drops
the `if v.sent_today(...)` filter that omitted actors at zero.

One judgement call: the review says "includes actors at zero". The old `actors` set was
built from senders of *directed* messages only, so a door that had only posted was absent
from `sent_today` entirely. I widened it to `{m["from"] for m in v.messages}` — a poster is
an actor worth reporting even though posts do not count against the cap (Invariant 8), and
reporting it at 0 is the honest answer. The comment at `:87-89` says so. The pre-existing
exact-equality assertion at `tests/plaza/test_cli.py:48`
(`sent_today == {"tony": 1, "door:elder": 1}`) still passes: in that test every sender sent
something directed.

## M5 — `status` reports the physical line count on a malformed record

**Commit** `278eb3f`. `src/hamutay/plaza/cli.py:95-97` — when `records` was reset to `[]`
by a `LedgerMalformed`, `seq` reported `0`; it now reports the physical non-empty line
count via the new `_physical_lines(cfg)` (`src/hamutay/plaza/cli.py:33`), or `null` if the
file cannot be read.

M4 and M5 share `tests/plaza/test_cli.py:90`
`test_status_reports_the_cap_actors_at_zero_and_a_physical_line_count`, which fails before
the change with `KeyError: 'door:qwen'`.

## M6 — the unreachable `OSError` arm

**Commit** `7069c8f`. `src/hamutay/plaza/pass_.py:69` — `except (StoreUnavailable, OSError)`
becomes `except StoreUnavailable`, since `store.land` (`store.py:19-20`) normalises
`OSError` and `LeaseGateRequired` into `StoreUnavailable`. The test that reached the dead
arm only did so by stubbing `land` directly; `tests/plaza/test_pass.py:99` now raises
`StoreUnavailable("disk")`, which is what a real `land` raises, with a comment saying why.

## M8 — the README's `events send` caveat

**Commit** `5d901f8`. `community/README.md:32-35` — the operations line becomes "speak (one
door only)" and carries spec §7's caveat verbatim ("the wrong tool for anything a resident
should be able to see"), pointing at `deploy/ayllu-plaza send`.
`community/README.md:245-247` — the plaza section cross-references it. Pinned by
`tests/plaza/test_deploy_plaza.py:237`
`test_readme_carries_the_spec_seven_caveat_on_events_send_and_cross_references_it`, which
requires the sentence in both regions of the file.

## M9 — the inert `completed=` parameter

**Commit** `5d901f8`. `tests/plaza/test_note.py:19` — `_completed_wake`'s `completed=`
parameter mutated an in-memory copy at the old `:33` that never reached the file. Removed
(the review's first option), with the reason recorded in the docstring: `note_lower_bound`
joins the completed wake back to its running record and reads `started_at`, never
`completed_at`, so a completed time is not a parameter of anything under test. The three
call sites were updated.

---

## Suite counts

Scoped, as required after the wave:

```
$ uv run pytest tests/plaza tests/assembly tests/assembly_validation tests/test_heartbeat.py \
    tests/test_event_ingress.py tests/unit/test_events.py -q -p no:cacheprovider
332 passed in 58.77s
```

Full:

```
$ uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration
1989 passed, 5 skipped, 1 xfailed in 75.54s (0:01:15)
```

The review recorded 1977 passed on the same command; this wave adds 12 tests
(C1 1, M2 1, I1 1, I2 2, I3 3, I4 1, M3 1, M4/M5 1, M8 1) and changes no existing
test's outcome.

**Frozen suites untouched**, as the constraint requires:

```
$ git diff --stat 6ca4125..HEAD -- tests/assembly_validation tests/assembly src/hamutay/assembly/ledger.py
(empty)
```

**Scripts.** `bash -n deploy/migrate-plaza.sh` — ok. It is the only script this wave
touched.

---

## Left open

Nothing from the assigned list. All ten assigned findings (C1, I1–I4, M2–M6, M8, M9) are
fixed, each with a covering test confirmed to fail beforehand.

Deliberately not touched, per instructions: **M1** (the second sequential store-lock round
trip inside `send`'s plaza scope), **M7** (`Path(root / a.text_file)` escaping the project
root), **M10** (`test_heartbeat_plaza.py`'s shape assertion on the `functools.partial` —
note that I3's third test now covers that behaviour through the real `run_next_event`, so
if M10 is ever taken up the behavioural coverage already exists), **M11** (the activity
log recording an ignored model-supplied `"from"`), **M12** (`EventStore.__init__`'s
`mkdir(parents=True, exist_ok=True)`).

Two things a re-reviewer may want to look at specifically, since they are the places where
I made a call rather than transcribing the review:

1. **I2's local `line_numbers` copy.** The helper mutates the caller's lists, and the
   callers must not hand it `ledger.line_numbers` (rebuilt by every `append_unlocked`).
   This is load-bearing for the two-appends-in-one-scope case and is the kind of thing a
   future edit could undo silently — `test_append_validated_appends_and_returns_the_stamped_record`
   and the existing send/pass suites are what catch it.
2. **M4's widened `actors` set**, described above: posters are now reported at 0.

---

# Scoped re-review of the fix wave

Verdict: all twelve findings addressed, no new Critical/Important breakage. The Critical (C1) was verified by restoring the pre-fix script and running the new test, which reproduced the review's call trace (four stops, four starts, four no-op starts, zero rollback stops); the ERR trap's arming, disarming and non-reentrance were traced; every door the install starts is stopped and restarted on the restored file. Suites: 332 scoped, 1989 full; frozen assembly suites byte-identical. Residual cosmetics: the spec's wiring sentence for extra_notes (amended on main as r4.1), a half-stale test name, note_producer's unread store parameter. M1, M7, M10, M11, M12 deferred with rulings.

---

# Rulings made by the controller (from the ledger), in order

- | T2 ↔ T4/T5/T6 (src/hamutay/plaza/__init__.py) | File Structure says __init__ exports send, run_plaza_pass, plaza_note, which exist only after T4–T6 | Ruling: T2's __init__ exports only PLAZA_NS and what T2 creates; T4, T5, T6 each add their own export — because an import of a module that does not exist yet breaks every plaza import; costs nothing if wrong (a later task adds a line) |
- Task 1: Ruling: no `tests/__init__.py` — the brief's absolute import `from tests.plaza.conftest import …` is replaced by the relative `from .conftest import …`, the pattern tests/assembly_validation already uses — because a repo-root package file changes collection for every suite and is outside the task's files; costs nothing if wrong (one import line).
- Task 1: Ruling: the verbatim assertion `"plaza" not in json.dumps(cfg2.snapshot())` is replaced by structural assertions (snapshot keys == the three doors; the string "community/plaza/plaza.jsonl" appears nowhere in it) — because tmp_path carries the test's own name and the plan's assertion cannot pass anywhere; the intent (member-only snapshot) is kept; costs nothing if wrong.
- Task 2: Ruling: the plan's `test_validator_rejects_each_condition` is defective (its mutate lambdas return None, so 19 of 20 cases pass None to the validator); the implementer's defensive isinstance guard is removed and the test is repaired so each case mutates in place and returns (recs, ln) — because a validator test that exercises "reject non-list" nineteen times validates nothing the spec §2 requires, and unrequested defensive code hides that; costs one small test edit if wrong.
- Task 2: Ruling: `visible_since(bound: datetime | None, door)` (plan) stands over the spec prose's `visible_since(seq, door)` — the plan's preamble says the plan wins on names and signatures; costs a rename if wrong.
- Task 5: Ruling: the plan's final assertion in test_note_names_exact_seqs_and_a_bounded_command (elder receives a note) contradicts spec §5 ("excluding those addressed to this door … and those from this door") and Task 2's visible_since; the implementer's corrected expectation stands — because the spec is the authority; costs one assertion if wrong.
- Task 6: Ruling: the brief's fifth test closure re-read the ledger under a blocking lock inside the pass's held lock (self-deadlock in the plan's test); the implementer hoisted the one needed value out of the closure; accepted because the plan itself said the lambda must be simplified and the fix touches the test only; costs nothing if wrong.
- Task 9: Ruling: (1) the brief's `_read()` used Ledger.read() (unbounded lock); the implementer's try_locked(PLAZA_LOCK_WINDOW_S) stands (spec: every acquisition bounded). (2) `status`'s sent_today must mean the UTC day of `now`, not the actor's last-send day (the brief's fixed-date test was a wall-clock time bomb, the same class as the assembly validation defect of 9-17); `status` gains `--now ISO` (default: the real clock) and the test passes `--now 2026-09-20T12:00:00+00:00`. Costs one flag if wrong.
- Task 10: review Needs fixes — Important: (1) phase-two dry run skips the --merge ancestry check entirely (neither refuses nor reports); (2) no trap-based rollback for mid-sequence failures in phase two (plan-mandated); (3) phase-one/two idleness check lacks the up-front all-doors pass migrate-assembly.sh has (plan-mandated). Ruling: fix all three (the plan's script text was wrong; the spec's "rolls back atomically if any step fails" and "mirror the idleness check" govern), plus the README trust paragraph gains the sentence that --by is a claimed, unauthenticated label (via: cli). Minor deferred: orphaned members.json.previous on candidate abort; bare git error on check --phase-one with no merge; rollback and non-ancestor dry-run untested.
