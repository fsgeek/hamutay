# Assembly: whole-branch review, fix wave, and Codex validation — the record

Plan: docs/superpowers/plans/2026-09-16-assembly.md (Task 12, Step 1 asked for this file).
Spec: docs/superpowers/specs/2026-09-15-assembly-design.md (revision 4 at 5617261, amended at merge).
Merged to main as 859a16e (2026-09-16, signed, no-ff).

The three records below were written during the build in the assembly worktree's
subagent-driven-development ledger (`.superpowers/sdd/2026-09-16-assembly/`), which is
untracked. They are copied here verbatim on 2026-09-16 (evening, PDT) by the custodian that
followed the one who built the branch, because the plan said the findings and dispositions
belong in the repository and the previous session closed before copying them.

The per-task briefs, reports and review diffs remain in the worktree's ledger for as long as
the worktree exists.

---

# Part 1 — the SDD progress ledger (tasks 1–11, the whole-branch review, the rulings)

# SDD ledger — plan: docs/superpowers/plans/2026-09-16-assembly.md
Worktree: /home/tony/projects/hamutay/.worktrees/assembly (branch assembly, base 64b773e on main).
Spec: docs/superpowers/specs/2026-09-15-assembly-design.md r4 (5617261) + reviews 1-3. Spec is the binding authority.

## Pre-flight conflict scan (2026-09-16)
| Pair / task | Produces vs consumes | Finding |
|---|---|---|
| T1/T3 | Ledger.append_unlocked returns record with seq; View reads seq | consistent |
| T3/T6 | build_delivery(for_,id_,door,event_id,state,landed_at,detail); View.delivery_truth(for_,id_,door) | consistent |
| T3/T8 | View.outstanding_deliveries/missing_activations/quiescent/next_deadline; closing fields proposal, proposal_sha256, next_question | T8 writes both proposal and proposal_sha256; T6's test closing supplies proposal_sha256 only, and View.missing_activations reads c.get("proposal",{}) tolerantly — consistent |
| T5/T6 | build_inbound_event(event_id=, assembly=) sets expires_at + defer flag | consistent; T6's terminal closing sets defer flag without expiry by hand |
| T5/T7 | WakeContext(event_id, run_id, started_at, event) | consistent |
| T5/T8 | EventStore.try_read_records(timeout_s) raises StoreUnavailable | consistent |
| T7/T9 | ASSEMBLY_CONSTITUTION_CLAUSE defined in schemas (T7); build_constitution(assembly=) inserts it (T9); _build_messages strips it when not offered (T7) | consistent |
| T8/T9/T10 | run_pass(binding,*,now,actor,memo,open_store)->(dict,PassMemo); CLI uses a "cli" binding whose .member is never read | consistent |
| T8/T10 | eligible_positions(view, lineage_id, stores, members), active_positions(elig, members) | consistent |
| T9/T11 | checkpoint script excludes plaza; README section | consistent |
| T5 internal | claim_next_pending snippet contains scaffold text `if False else records` | Ruling: bind `records = self._read_records_unlocked()` once at the top of the locked block, derive `latest` from it, drop the scaffold — the plan's prose already says so; cost if wrong: a second read per claim, no behaviour change |
| T3 internal | derived child `convener` copied from the parent question when present | consistent (round-1 question always precedes its closing) |
| T6 internal | convene appends the procedure record twice (second carries proposed_by_question_id) | Ruling: acceptable; View.procedures keeps a list; derive_activations takes the latest provisional — cost if wrong: one redundant line per bootstrap question |
| T8 internal | try_close reads every member store even when a delivery was never landed | consistent with spec §7 step 2 (the read serves the join); cost: four bounded reads per close |
| T12 | live-door steps by the custodian, not a subagent | noted |

Global constraints copied to every dispatch: hamutay commit identity; add only named files; never git stash; uv run pytest; lock order; timezone-bearing instants; one JSON line per ledger write with flush+fsync+verify; non-assembly events byte-for-byte unchanged; tmp_path only until Task 12.

## Progress
Task 1: dispatched (implementer haiku, BASE 64b773e, 16:06Z)
Task 1: implementer DONE at 5989840 with a deviation (append tolerates a malformed middle line); reviewer (sonnet) dispatched 16:11Z
Task 1: review — spec ❌ (Critical: append() fails open past a malformed middle line; Important: duplicated parse loop, undocumented state flags)
Task 1: Ruling: the brief's test `test_read_raises_on_a_malformed_middle_line` was wrong (it appended after the garbage without expecting a raise); the spec's fail-closed rule wins — append()/next_seq_unlocked propagate LedgerMalformed on any malformed line other than a torn final line, and the test asserts the raise on both the append and the read. Cost if wrong: a corrupt ledger blocks all assembly writes until a human repairs it, which is the designed behaviour.
Task 1: fix round 1/5 dispatched re-review (commit 3b482c5)
Task 1: fix round 1/5 (4 addressed, 0 open; commits 5989840..3b482c5)
Task 1: complete (commits 64b773e..3b482c5, review clean after one fix round)
Task 2: dispatched (implementer haiku, BASE 3b482c5, 16:15Z)
Note: the worktree's .venv lacked the ots client (dev extra), so 5989840 and 3b482c5 were not stamped (hook skipped). Installed via uv sync --extra dev at 16:16Z; later branch commits stamp normally; the merge commit on main covers the earlier two.
Task 2: implementer DONE at d267fb7; reviewer dispatched 16:18Z
Task 2: review — spec ✅ with ⚠️ (open_snapshots wiring and caller honesty: owned by Task 9; gitignore rule: owned by Task 11); Important: duplicate session paths across members silently mis-attribute the door → fix round 1
Task 2: minor (deferred): note-string duplication in bind() (brief-mandated wording)
Task 2: fix round 1/5 dispatched re-review (commits 0ede54e..f36af6b)
Task 2: fix round 1/5 (1 addressed, 0 open; commits 0ede54e..f36af6b)
Task 2: complete (commits 3b482c5..f36af6b, review clean after one fix round)
Task 3: dispatched (implementer haiku, BASE f36af6b, 16:22Z)
Task 3: implementer DONE_WITH_CONCERNS at 60d2f0c; left an UNCOMMITTED change to ledger.py assigning procedure versions inside Ledger.append_unlocked
Task 3: Ruling: the ledger knows nothing about procedures; version numbering is convene's job (spec §2 "version is assigned under the lock as one more than the highest existing", implemented in Task 6 via View.next_version()). The brief's test was wrong to expect version 1 from a bare append of build_procedure(); the test passes version=1 explicitly. The ledger change is discarded. Cost if wrong: none to behaviour; the assignment happens in Task 6 where the spec puts it.
Note: subagent commits carry a "Co-Authored-By: Claude Haiku 4.5" trailer the plan did not ask for; left as is (the record shows who typed).
Task 3: fix round 1/5 committed dcd413c (ledger change discarded); full-range review dispatched 16:27Z
Side note (live door, not this plan): qwen c11 completed 16:27Z on the fixed code (8 turns, loan note present, budget note fired as user-role and degraded instead of breaking, check 8 self-scheduled 2026-09-17 09:00Z, quiet declared). Two follow-ups for the custodian outside this plan: (a) the resident's state names the custodian "Sut'i" (that is the fable door's resident) — correct it in the next message; (b) the budget note reports last_reported_prompt_tokens (39,280) while the trigger is estimated_next_input_tokens ≥ threshold (52,428): the note should name the estimate that fired, test-first.
Task 3: review — spec ❌ per reviewer (Critical 1: missing_activations reads closing.proposal; Critical 2: build_execution reads closing.proposal_sha256; Important 3: no tests for missing_activations/build_execution/quorum_for; Minor 4: reduce trusts input order; Minor 5: build_late_position unvalidated)
Task 3: Ruling on Critical 1 and 2: NOT defects. The plan's closing record (Task 8 try_close, Task 6's test closing, Task 10 execute) carries `proposal` (copied from the question) and `proposal_sha256`; the plan header says the plan wins on names and shapes where it is more specific than the spec, and the spec's §9 "execution copies the question's proposal.sha256" is satisfied by copying it through the closing. Both functions are correct against the plan's shape. Cost if wrong: a closing written without those fields would make quiescence blind to activations and execution impossible — Task 8's tests pin the shape.
Task 3: fix round 1 → add the missing tests (Important 3) against the plan's closing shape, and sort by seq in reduce() (Minor 4, cheap). Minor 5 deferred.
Task 3: minor (deferred): build_late_position validates nothing (only ever fed a built position)
Task 3: fix round 2/5 dispatched re-review (commits 24f6bc7..c5dd183)
Task 3: fix round 2/5 (2 addressed, 0 open; commits 24f6bc7..c5dd183)
Task 3: complete (commits f36af6b..c5dd183, review clean after two fix rounds, Critical 1-2 ruled not defects)
Task 4: dispatched (implementer haiku, BASE c5dd183, 16:32Z)
Task 4: implementer DONE at 7d689be; reviewer dispatched 16:34Z
Task 4: complete (commits c5dd183..7d689be, review clean)
Task 5: dispatched (implementer sonnet, BASE 7d689be, 16:36Z); carries the scaffold ruling from the pre-flight scan
Task 5: implementer BLOCKED (correctly): run_next_event passes wake_context= but OpenTasteSession.exchange has no such parameter until Task 7; 22 existing tests would fail.
Task 5: Ruling: Task 5 adds the minimal seam — `OpenTasteSession.exchange(..., wake_context=None)` accepted and threaded to `_exchange_impl(..., wake_context=None)` where it is unused for now — so the keyword exists before Task 7 gives it meaning. taste_open.py joins Task 5's file list. Cost if wrong: none; Task 7 replaces the no-op with the real wiring.
Task 5: implementer DONE at c58bb0d (seam in taste_open.py per ruling); reviewer (sonnet) dispatched 16:42Z
Task 5: review — spec ❌ (Important, plan-mandated: append_if_absent does not verify the write length; Minor: duplicated expiry-record construction; Minor: defer_to_declared_quiet: False on every summary) → fix round 1 (all three; the minors are cheap and in the same function region)
Task 5: fix round 1/5 committed 44c9d71; re-review dispatched
Task 5: fix round 1/5 (3 addressed, 0 open; commits c58bb0d..6d86ad9)
Task 5: complete (commits 7d689be..6d86ad9, review clean after one fix round; seam in taste_open.py by ruling)
Task 6: dispatched (implementer sonnet, BASE 6d86ad9, 16:48Z)
Task 6: implementer DONE at 2af7558; reviewer dispatched 16:50Z
Task 6: complete (commits 6d86ad9..2af7558, review clean)
Task 6: minor (deferred): a comment on the closing-delivery path lookup in outbox.py
Task 7: dispatched (implementer sonnet, BASE 2af7558, 16:52Z)
Task 7: implementer DONE at 5684dab with a concern: the plan reused gpu_lease.state.parse_ttl for closes_in, which caps at 72h, so a 7-day question could never be convened from the tool or the CLI.
Task 7: Ruling: plan defect. The assembly gets its own duration parser `parse_closes_in(s) -> timedelta` in hamutay.assembly.convene (units m/h/d, no cap of its own; convene() enforces MIN/MAX_CLOSES_IN), used by the executor's _convene now and by Task 10's CLI. Cost if wrong: none; parse_ttl stays the lease's.
Task 7: fix round 1/5 committed 4382c0e (parse_closes_in); full-range reviewer dispatched 17:01Z
Task 7: review — spec ✅; Important: the session test does not exercise "wake_context present, no binding" → fix round 2; minors (deferred): duplicated error shape in _take_position/_convene; untyped record_id param
Task 7: fix round 2/5 committed 0829abc (test only); re-review dispatched
Task 7: fix round 2/5 (1 addressed, 0 open; commits 05c5ce0..4e98c34)
Task 7: complete (commits 2af7558..4e98c34, review clean after two fix rounds; parse_closes_in by ruling)
Task 8: dispatched (implementer sonnet, BASE 4e98c34, 17:06Z)
Task 8: implementer DONE at 73e2e6c (one test fix: parse_instant on closed_at); reviewer (opus) dispatched 17:10Z
Task 8: complete (commits 4e98c34..73e2e6c, review clean; opus reviewer)
Task 8: minor (deferred): step 2 reads every member's store, not only offered members' (double-reports a not_offered+unknown member; conservative); derive_activations relies on convene minting fresh ids for its idempotence; absence detail nests detail; run_pass freezes open_questions before the loop (correct by arithmetic; comment wanted)
Task 8: Ruling on the reviewer's operational observation (an orphaned running row caps a door's assent until repaired): faithful to the spec, and mitigated by the heartbeat's boot recovery, which re-pends orphaned running events on restart so the latest status becomes pending (pending_at_close, no cap). Residual: a door whose process stays dead keeps capping assent until it restarts — that is the fail-closed intent (a dead member is unknown, not absent). A permanently decommissioned door is a membership change made between lineages. Carried to Task 12's notes and to the spec's declared losses at merge. Cost if wrong: a stalled door holds the assembly at 'extended' until someone restarts it.
Task 9: dispatched (implementer sonnet, BASE 73e2e6c, 17:14Z)
Task 9: implementer DONE at 544812f; reviewer (sonnet) dispatched 17:19Z
Task 9: review — spec ❌ (Critical: a RAISED exception from the pass escapes step() and would kill the daemon; Important: the observational summarize callback is unguarded the same way) → fix round 1; minors (deferred): members.json parsed twice at boot; report wording about the unbound callback
Task 9: fix round 1/5 committed 773b493; re-review dispatched
Task 9: fix round 1/5 (2 addressed, 0 open; commits 544812f..a77306b)
Task 9: complete (commits 73e2e6c..a77306b, review clean after one fix round)
Task 10: dispatched (implementer sonnet, BASE a77306b, 17:26Z); carries the parse_closes_in ruling
Task 10: implementer DONE at 7762ec3 (parse_closes_in; gpgsign off in the test fixture's throwaway repo; status catches StoreUnavailable only); reviewer dispatched 17:30Z
Task 10: review — spec ❌ (Important: _artifact raises SystemExit out of main(); Important: history omits withdrawal/delivery/execution records lacking lineage_id) → fix round 1, including the cheap minor (withdraw --by restricted to tony|custodian); minor (deferred): history re-reduces per procedure row
Task 10: fix round 1/5 committed 33ff426; re-review dispatched
Task 10: fix round 1/5 (3 addressed, 0 open; commits 7762ec3..c22d226)
Task 10: complete (commits a77306b..c22d226, review clean after one fix round)
Task 11: dispatched (implementer sonnet, BASE c22d226, 17:35Z)
Task 11: implementer DONE at 4ec992e; reviewer dispatched 17:39Z
Task 11: review — spec ❌ (Critical, plan-mandated: journalctl --since rejects the ISO-Z timestamp the brief used, so the bind-wait could never succeed; Important: check script's bound check reads all journal history; Important/Minor: redundant gitignore lock rule) → fix round 1; minors (deferred): inactive units skipped silently; report overstated verification depth
Task 11: fix round 1/5 committed e080200; re-review dispatched
Task 11: fix round 1/5 (3 addressed, 0 open; commits 4ec992e..32fce59)
Task 11: complete (commits c22d226..32fce59, review clean after one fix round)
Final whole-branch review dispatched (opus) over 64b773e..32fce59 at 17:45Z
Final review (opus): With fixes. C1 (spec defect §6 vs failure model): a position from a wake that later FAILED is marked ineligible and the question can assent over a live dissent; boot recovery re-pends running orphans only, never failed. I1: next_pending now blocks unboundedly on the store flock for every door. I2: the pass can hold the ledger lock ~16 s under store contention, starving take_position. I3: the path freeze misses an ADDED member. I4: convene --by unconstrained (a human can sign as a resident). I5: the migration's running-wake check is advisory ~90 s before the restarts. Minors M1-M5; promotes two comments (Task 6 outbox lookup, Task 8 run_pass freeze).
Final review: Ruling on C1 — accepted as a spec defect. Fix: a position whose wake's latest status is `failed` is neither eligible nor ignorable: it is carried with eligible: null and its door enters a fourth cap, `position_from_failed_wake`, which converts assented to extended/unresolved like the other three. Rationale: the join genuinely did not complete, so the stance cannot be counted, but "never loses" holds because the question cannot assent over it and the next round gives the door another wake. The spec's §6 sentence about boot recovery is corrected at merge. Cost if wrong: a failed wake extends a question by one round; that is the fail-closed direction.
Final review: Ruling amending Task 8's orphan ruling — boot recovery re-pends running orphans only; failed wakes are terminal; C1's cap is what makes failed wakes fail closed.
Final review: Ruling on I2 — bound the pass's ledger lock (try_locked 10 s, error emitted not raised) and fix M1 (one latest-status index per store) rather than reordering the store reads; store reads stay inside the lock because eligibility must be judged against a store snapshot no older than the ledger snapshot.
Final review: fix wave dispatched (one implementer, opus) for C1, I1-I5, M1, the two promoted comments, a closing-shape test, and a four-process concurrency test.
Final fix wave committed 6ab2fa5..d47cddd (7 groups, 1875 tests); scoped re-review dispatched 18:14Z
Codex validation suite (frozen-before-run) dispatched 18:15Z into tests/assembly_validation/
Final fix wave: scoped re-review (opus) — all findings ADDRESSED, no new breakage; residual: spec §2 positions schema line stale (doc only) — fixed by the custodian at merge
NOTE (custodian's own defect, 9-16): the waiter for Codex's validation run polled `pgrep -f 'codex exec -s workspace-write'`, which matched the waiter's own command line and never exited; the session sat idle from 11:22 PT until Tony asked at 16:42 PT. Three earlier waiters of the same shape were also still alive and were killed by pid. Lesson saved to memory.
Codex validation suite frozen at bff4a28 and run once: 13 passed, 6 failed.
  Ruling on the four cap tests: CODE defect. Spec §7 step 5 says the cap is "named in trace"; the code recorded it only in tally.cap. Fix: the closing's tally.trace gains "; cap:<name>:<doors>" when a cap applied (tally.cap stays).
  Ruling on the digest-mismatch test: CODE gap. Codex built a closing from the spec's §2 schema, which never listed the plan's copied proposal/proposal_sha256, so missing_activations skipped it. Fix: missing_activations/derive_activations fall back to the question's proposal when the closing carries none; the spec's §2 closing schema documents proposal and proposal_sha256 as copied from the question.
  Ruling on test_quiet_outlasting_expiry_expires_without_a_wake: TEST defect. claim_next_pending returns (event, expired_record) for every expiry by house convention (the runner treats it as no wake); Codex corrects its own test to assert the returned status is expired with detail.reason skipped_by_quiet and that no running record exists.

---

# Part 2 — the final-review fix wave

# Final-review fix wave — report

Branch `assembly`, worktree `/home/tony/projects/hamutay/.worktrees/assembly`.
Base at the start of the wave: `32fce59` (1860 passing). Seven commits, one per finding
group, test-first for every behaviour change. Each is followed by its `ots: stamp` commit.

| Group | Commit | Subject |
|---|---|---|
| C1 | `6ab2fa5` | a recorded objection is not discarded when its wake fails — the fourth cap |
| I1 | `58e4b6b` | next_pending takes a bounded store-lock window |
| I2 + M1 | `3d2120a` | the pass bounds its ledger lock at 10 s; one latest-status index per store |
| I3 | `fe5cc7a` | the freeze covers the member set, not only the paths |
| I4 | `63c86b5` | convene --by restricted to tony or custodian |
| I5 | `f19375c` | the migration re-checks for a running wake before each restart, with --force |
| tests + comments | `8954103` | the closing's key set, four-process close-once, two named lookups |

---

## C1 (Critical, spec defect) — a recorded objection discarded when its wake fails

**Changed.** `src/hamutay/assembly/close.py`, `rule.py`, and the spec.

- `eligible_positions` gained an optional `latest` argument (the per-store latest-status
  index) and a new branch: when no `completed` join exists *at all* for the position's
  `record_id`, it looks up that position's `event_id` in the member's store. If the latest
  status there is `failed`, the entry becomes `{"record": p, "eligible": None,
  "reason": "wake_failed"}`. `running`, `pending` and a *mismatched* join still yield
  `eligible: False`; an unreadable store still yields `eligible: None` with no `reason`.
- `rule.apply_caps` gained a fourth keyword `position_from_failed_wake: list[str] | None`,
  checked after `unknown_at_cutoff`, with the same conversion (assented → extended if
  rounds remain, else unresolved) and trace `cap:position_from_failed_wake:<doors>`.
- `try_close` computes
  `failed_positions = sorted({door for e in elig if e.get("reason") == "wake_failed"})`,
  passes it to `apply_caps`, and records it in `tally["position_from_failed_wake"]`.
  The door's Empty Chair entry is untouched — it stays `failed`, the lifecycle fact; the
  tally field is what says a stance was attempted and could not be counted.

**Spec.** `docs/superpowers/specs/2026-09-15-assembly-design.md`:
- §6's sentence about boot recovery replaced with the corrected text (boot recovery
  re-pends a wake found `running`; a `failed` wake is not retried, so its position is
  carried with `eligible: null` and its door enters `position_from_failed_wake`).
- §7 step 5 now says "four caps" and names the new one with its rationale.
- §2's closing `tally` schema gained `unknown_at_cutoff` (which had been missing from the
  schema although it was always written) and `position_from_failed_wake`.

**Covering tests.** `tests/assembly/test_close.py`:
`test_a_position_from_a_failed_wake_caps_assent_and_is_neither_eligible_nor_ignorable`
(door c records `dissent`, its wake is marked `failed` via `store.append_failed(...)`,
a and b assent; asserts `outcome == "extended"`, `cap == "cap:position_from_failed_wake:c"`,
`tally["position_from_failed_wake"] == ["c"]`, the position carried with `eligible: None`
and `reason: "wake_failed"`, `objections == []`, and the Empty Chair entry still `failed`)
and `test_a_position_from_a_running_wake_is_still_ineligible_not_unknown` (the carve-out
is narrow: running keeps `eligible: False` with no `reason`).
`tests/assembly/test_rule.py`: the cap parametrisation extended to four caps, plus
`test_position_from_a_failed_wake_is_the_last_cap_checked_and_names_its_doors` (sorted
door names; an earlier cap still wins when both apply).

**Command and output.**

```
$ uv run pytest tests/assembly/test_close.py tests/assembly/test_rule.py -q -p no:cacheprovider
# before the fix
8 failed, 14 passed in 1.16s
# after
22 passed in 1.10s
```

---

## I1 (Important) — `next_pending` blocked indefinitely on the store flock

**Changed.** `src/hamutay/events.py`. `next_pending` now takes `self._try_locked(
NEXT_PENDING_LOCK_WINDOW_S)` (a new module constant, 2.0) instead of the blocking
`_locked()`; on `StoreUnavailable` it falls back to `self._read_records_unlocked()`,
returning `None` on a `json.JSONDecodeError` from that unlocked read. A docstring names
why: the read is advisory (the claim path re-checks under the lock) and the poll loop
calls it for every door, so one busy door must not stall the others.

**Covering test.** `tests/assembly/test_events_assembly.py::
test_next_pending_does_not_block_indefinitely_on_a_held_store_lock` — a thread holds
`store._locked()` for 10 s; the test asserts `next_pending` returns in under 2.5 s and
still finds the pending event.

**Command and output.**

```
$ uv run pytest tests/assembly/test_events_assembly.py -q -p no:cacheprovider
# before the fix
AssertionError: next_pending blocked for 10.0s on the store lock
1 failed in 10.07s
# after
9 passed in 2.40s
```

---

## I2 (Important) + M1 (Minor) — the pass's ledger lock, and the O(n²) running scan

**Changed.**

- `src/hamutay/assembly/pass_.py`: `with ledger.locked()` → `with ledger.try_locked(
  LEDGER_LOCK_WINDOW_S)`, a new module constant of 10.0 with a comment explaining why the
  store reads stay inside the lock (eligibility must be judged against a store snapshot no
  older than the ledger snapshot). The existing `except (LedgerMalformed,
  LedgerUnavailable)` clause already covered this path — confirmed by the test, which sees
  `{"skipped": False, "error": ..., "closed": [], "activated": []}` and the memo unchanged.
- `src/hamutay/assembly/close.py`: `_latest_status(records, event_id)` (a full scan per
  call) replaced by `_latest_by_event_id(records)` (one pass per store, `event_id → latest
  status row`). `try_close` builds `latest[door]` once per readable store and uses it for
  the running scan, for `absence_for` (new optional `latest` argument) and for
  `eligible_positions` (new optional `latest` argument). The running scan now iterates the
  index's values rather than re-scanning the whole store for each `running` row to test
  whether it is the latest — same semantics, O(n) instead of O(n²).
- The promoted `pass_.py` comment is in this commit: `open_questions()` is frozen before
  the loop because a child created by an extension in this pass has `closes_at > now` and
  cannot be due in the same pass.

**Covering test.** `tests/assembly/test_close.py::
test_run_pass_bounds_the_ledger_lock_and_leaves_the_memo_unchanged` — a thread holds the
ledger lock for 30 s; asserts `run_pass` returns between 9.5 and 10.5 s with
`skipped: False`, `"busy" in error`, empty `closed`/`activated`, the memo identical to the
one passed in, and no closing written. The existing close tests are unchanged and pass.

**Command and output.**

```
$ uv run pytest tests/assembly/test_close.py::test_run_pass_bounds_the_ledger_lock_and_leaves_the_memo_unchanged -q -p no:cacheprovider
# before the fix
AssertionError: run_pass waited 29.9s for the ledger lock
1 failed in 30.07s
# after (whole assembly suite)
$ uv run pytest tests/assembly -q -p no:cacheprovider
96 passed in 15.53s
```

---

## I3 (Important) — the path freeze missed an ADDED member

**Changed.**

- `src/hamutay/assembly/convene.py`: before the per-door path comparison, `convene()` now
  refuses when `set(snapshot) != set(snap)` for any open question's snapshot, naming the
  added and/or removed doors ("the member set is frozen while a lineage is open (added
  fable)").
- `src/hamutay/assembly/binding.py`: `bind()` now refuses (no binding) when the current
  config's member set differs from any open snapshot's key set, with the note "assembly:
  member set changed while a lineage is open (added heartbeat); no binding", before the
  existing own-door path check.

**Covering tests.** `tests/assembly/test_binding.py`:
`test_bind_refuses_when_a_member_is_added_while_a_lineage_is_open`,
`test_bind_refuses_when_a_member_is_removed_while_a_lineage_is_open`,
`test_bind_allows_an_unchanged_member_set`.
`tests/assembly/test_convene_outbox.py`:
`test_convene_refuses_when_a_member_was_added_while_a_lineage_is_open`,
`test_convene_refuses_when_a_member_was_removed_while_a_lineage_is_open`.

**One pre-existing test adjusted, not weakened.**
`test_bind_refuses_when_an_open_question_snapshot_differs` built a snapshot naming only
`qwen` while `members.json` names `qwen` and `heartbeat`, so the new member-set check
fired first and the test would have passed for the wrong reason. Its snapshot now names
both doors (so it still exercises the *path* freeze it was written for) and it asserts on
"paths are frozen" rather than the substring "frozen", which both messages share.

**Command and output.**

```
$ uv run pytest tests/assembly/test_binding.py tests/assembly/test_convene_outbox.py -q -p no:cacheprovider
# before the fix
3 failed, 19 passed in 0.38s
# after (full suite)
1871 passed, 5 skipped, 1 xfailed in 32.14s
```

---

## I4 (Important) — `convene --by` was unconstrained

**Changed.** `src/hamutay/assembly/cli.py`: the convene subparser's `--by` gained
`choices=["tony", "custodian"]`, matching testify, withdraw and execute. The resident's
path is untouched: a door convenes through `record_convene`, which takes the member name
from the binding, never from an argument.

**Covering test.** `tests/assembly/test_cli.py::
test_convene_by_is_restricted_to_tony_or_custodian` — `--by door:qwen` raises `SystemExit`
with code 2, prints "invalid choice", and writes no question to the ledger.

**Command and output.**

```
$ uv run pytest tests/assembly/test_cli.py -q -p no:cacheprovider
# before the fix: the command succeeded and wrote a question convened by door:qwen
1 failed in 0.13s
# after
7 passed in 0.49s
```

---

## I5 (Important) — the migration's running-wake check was advisory

**Changed.** `deploy/migrate-assembly.sh`. The inline running-wake probe is now a shell
function `running_wake <door>` (exit 0 when the door's store has an event whose latest
status is `running`). It is called twice: the original up-front pass over all four doors
(so a busy door stops the migration before anything is written) and again inside the
per-door loop immediately before that door's `systemctl --user restart`, which is the
window the reviewer identified — the up-front pass can be ~90 s stale by the last door.
A new `--force` flag turns both refusals into a loud `say "WARNING --force: ..."` line and
proceeds; it is documented in the script's usage comment block at the top.

**Covering test.** `tests/assembly/test_deploy_assembly.py::
test_migration_checks_for_a_running_wake_inside_the_restart_loop_and_documents_force` —
text-asserts that `--force` and a usage block are present, and that within the restart
loop the `running_wake` call precedes `systemctl --user restart` and `FORCE` is consulted.

**Manual smoke test** against a scratch root with a store whose latest status is `running`:

```
$ bash deploy/migrate-assembly.sh --root $T
migrate-assembly: door qwen has a running wake; refusing to migrate now (--force overrides)
rc=1
$ bash deploy/migrate-assembly.sh --root $T --force
migrate-assembly: WARNING --force: door qwen has a running wake; migrating anyway
migrate-assembly: installed community/plaza/members.json
migrate-assembly: heartbeat did not report a binding within 30 s; stopping here
```

(the binding wait fails in the scratch root because there is no systemd unit there, which
is the correct fail-closed behaviour; the scratch root was removed afterwards.)

**Command and output.**

```
$ uv run pytest tests/assembly/test_deploy_assembly.py -q -p no:cacheprovider
# before the fix
AssertionError: assert ('--force' in '#!/usr/bin/env bash...')
1 failed, 7 passed in 0.12s
# after
8 passed in 0.09s
```

---

## The tests and comments the reviewer promoted

**`tests/assembly/test_close.py::test_closing_shape`.** Pins the closing's full key set
(`record_type, closing_id, question_id, lineage_id, round, outcome, governing, provisional,
proposal, proposal_sha256, tally, positions, testimony, absent, next_question, closed_by,
closed_at, delivery, seq, created_at`) and the tally's key set (`eligible_members, quorum,
active, objections, assents, abstentions, spoke, not_offered, running_at_cutoff,
unknown_at_cutoff, position_from_failed_wake, trace, cap`), as module constants so a
schema change has to be made deliberately. Also pins the shape of each `delivery` entry,
each `positions` entry (`record`, `eligible`, and optionally `reason`) and each `absent`
entry.

**`tests/assembly/test_close.py::test_four_processes_close_once`.** Four
`multiprocessing.get_context("fork")` processes, synchronised on a `ctx.Barrier(4)`, each
load members, bind their own door and run `run_pass` on the same due question at the same
instant. Asserts: every process exits 0; exactly one `closing` record with the
deterministic `closing_id`; exactly one landed closing-delivery row per door; the ledger's
`seq` values are contiguous `1..n`; and no door's store contains a duplicate `event_id`.

*Verified the test can fail.* With the pass's ledger lock replaced by a `nullcontext`, the
test fails with `assert (4 == 1)` — four closings for one question. The lock was restored
immediately; that mutation is not in any commit.

**Comments.** `outbox.py` at the closing-delivery path lookup (a closing carries no
`members` of its own; the path comes from the QUESTION's snapshot, which is frozen for the
whole lineage) and `pass_.py` where `open_questions()` is frozen before the loop (a child
created by an extension in this pass has `closes_at > now` and cannot be due in the same
pass — committed with I2/M1, which touched that function).

**Command and output.**

```
$ uv run pytest tests/assembly/test_close.py -q -p no:cacheprovider
13 passed in 11.64s
```

---

## Full suite

```
$ uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration
1875 passed, 5 skipped, 1 xfailed in 33.75s
```

(1860 at the start of the wave; 15 tests added, none removed, one pre-existing test's
fixture corrected as described under I3. Working tree clean at `d47cddd`.)

---

# Part 3 — the two defects found by Codex's frozen validation suite

# Validation fix report — two defects from Codex's independent suite

## Defect 1: the cap wasn't named in the trace

Spec §7 step 5 says an assented result converted by a cap becomes
extended/unresolved "with the cap named in trace". `try_close` in
`src/hamutay/assembly/close.py` recorded the cap only in `tally["cap"]`;
`tally["trace"]` kept the rule's own trace text, so a reader following
`trace` alone never learned why the outcome changed.

Fix: when `cap` is non-empty, `trace = f"{trace}; {cap}"`. `tally["cap"]`
is unchanged.

Test-first: added an assertion to
`tests/assembly/test_close.py::test_not_offered_member_caps_assent` —
`"cap:not_offered" in c["tally"]["trace"]` and `c["tally"]["cap"]`
unchanged. Confirmed red before the fix, green after.
`test_closing_shape` (the key-set pin) was re-run and still passes
unchanged — no new/removed keys.

## Defect 2: activation skipped a closing with no `proposal`

`View.missing_activations()` and `derive_activations()`
(`src/hamutay/assembly/records.py`, `src/hamutay/assembly/close.py`) read
`proposal`/`proposal_sha256` directly off the closing record. `try_close`
happens to copy those from the question, but the spec's §2 closing
schema never documented them, so a closing built strictly to the
documented schema (no `proposal`) was silently skipped and never
activated.

Fix: both functions now resolve
`proposal = c.get("proposal") or view.questions[c["question_id"]]["proposal"]`
(in `View.missing_activations`, skip the closing if the question is
also unknown). Updated the spec's §2 closing schema block: added
`"proposal": {...copied from the question...}, "proposal_sha256": <hex>,`
after the `"provisional"` line, and a sentence after the closing block
documenting the copy-and-fallback contract.

Test-first, added:
- `tests/assembly/test_records.py::test_missing_activations_falls_back_to_the_question_proposal_when_the_closing_lacks_one`
  — a hand-built assented procedure closing without `proposal`/`proposal_sha256`
  is still listed by `missing_activations()`.
- `tests/assembly/test_close.py::test_derive_activations_falls_back_to_the_question_proposal_when_the_closing_lacks_one`
  — `derive_activations` activates it, reading the proposal from the question.
- `tests/assembly/test_close.py::test_derive_activations_rejects_on_digest_mismatch_when_the_closing_lacks_a_proposal`
  — same shape, but the question's proposal digest doesn't match the
  provisional procedure's payload digest; activation is rejected, not
  silently skipped.

All three confirmed red before the fix, green after.

## Commits (hamutay identity, signed, no Co-Authored-By)

1. `446f6aa` — `fix: name the cap in the closing's trace (spec §7 step 5)`
2. `5b82b5f` — `fix: activation reads a closing without proposal by falling back to its question`

Each is followed by an automatic `ots: stamp <hash>` commit from the
post-commit hook (`45e5675`, `3c90af9`).

## Verification output

`uv run pytest tests/assembly -q -p no:cacheprovider`:
```
108 passed in 16.35s
```
(105 pre-existing + 3 new tests, all passing.)

`uv run pytest tests/assembly_validation -q -p no:cacheprovider` (frozen suite, untouched):
```
19 passed in 2.02s
```
All 19 pass, including `test_quiet_outlasting_expiry_expires_without_a_wake`.
That test currently passes because of a pre-existing, uncommitted edit to
`tests/assembly_validation/test_quiet_binding_and_constitution.py` already
present in this worktree before this session started (not made by this
session, not staged or committed by this session) — Codex's own
in-progress correction to that test's defect, mentioned as separate work
in the task brief.

Full suite: `uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration`:
```
1897 passed, 5 skipped, 1 xfailed in 34.80s
```

## Notes

- Left `tests/assembly_validation/test_quiet_binding_and_constitution.py`
  exactly as found (modified, unstaged, uncommitted) — did not touch,
  stage, or commit it, per instructions to leave the frozen validation
  suite to Codex.
- One commit-message hiccup: the first attempt at the defect-2 commit
  message used inline backticks in a `-m` string, which bash interpreted
  as command substitution, garbling the message. Caught it immediately,
  soft-reset the two bad commits (stray "fix" commit plus its ots-stamp,
  and a stray amended-stamp commit) without touching the working tree,
  cleaned up two orphaned `timestamps/` files the bad attempts had
  created, and recommitted the same diff with a heredoc-based message
  file. Final history has exactly one commit per defect, both with the
  intended messages.
