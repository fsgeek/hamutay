# Window-aware wakes — whole-branch review record

Branch `window` (base `9accc28`, main at the plan's start), reviewed before the merge. Ten tasks, each
gated by a task review (six with fix rounds); one whole-branch review on the most capable model; one
fix wave; one scoped re-review; Codex's independent validation suite frozen before its first run
(appended below when run); live evidence from the local llama-server. The spec was amended three
times during implementation (r6.1, r6.2, r6.3 on main), each amendment found by a gate. The SDD
ledger (`.superpowers/sdd/2026-09-17-window-aware-wakes/progress.md`, gitignored) holds every ruling
and deferred minor; the rulings are summarised at the end of this record.

---

# Final whole-branch review — window-aware wakes

Range `9accc28..5ca488f`, branch `window`. Spec r6.3 (`docs/superpowers/specs/2026-09-17-window-aware-wakes-design.md`, on main), plan `docs/superpowers/plans/2026-09-17-window-aware-wakes.md`, ledger `.superpowers/sdd/2026-09-17-window-aware-wakes/progress.md`.

Read in passes: (1) ledger + live evidence + spec r6.3 + Codex round seven; (2) `window.py`, `context_policy.py` whole; (3) `taste_open.py` backend block (1226–1620), the four paths (1620–2420), `_build_messages`, `_exchange_impl`, `_log_entry`, `apply_context_limit`; (4) `events.py` diff, `close.py` diff, `heartbeat.py` diff; (5) targeted execution — the required suites plus three scratch tests written against the branch's own fakes to trace the live `unsupported` path and probe two suspected holes. Fixture JSON under `tests/fixtures/window_golden/` skimmed for structure only, as instructed.

Read-only honoured: no request to `127.0.0.1:8081`, nothing touched under `community/`, nothing restarted. Worktree, index, HEAD and branch unchanged; stash never used. Scratch tests were written to the session scratchpad, not the repo.

---

## The seven items

Round seven's verdict list, one line each.

| # | Must not get wrong | Verdict |
|---|---|---|
| 1 | Count the exact final payload before every send, including malformed resends; assert `prompt_tokens + max_tokens < limit` | **Mostly.** One `_post_chat` behind one `_send` that always bounds — structurally airtight — and the single-tool malformed resend does recount (`taste_open.py:1641`, `precounted` only at turn 0). **One hole:** the natural loop's budget-recovery resend reuses the pre-truncation count (C1). |
| 2 | Fail closed with `CountUnavailable`; candidate mode may suppress only `ExhaustedBeforeRequest` | **Mostly.** `prepare` is exactly right (`taste_open.py:1544-1557`): a count failure raises in both modes, only exhaustion is softened by `candidate`. **But** a `CountUnavailable` whose wrapped text carries the server's context phrasing is caught by the recovery loop's `except RuntimeError` instead of failing closed (I2). |
| 3 | After any tool or message mutation, rebuild first, then recount, bound, assert, send | **Mostly.** Turn-0 withdrawal clears `precounted` and recounts (`taste_open.py:2255`); multi-turn rebuilds per iteration; single-tool recounts the resend. Same one hole as item 1 — `_truncate_largest_tool_results` mutates the conversation and the resend is not recounted (C1). |
| 4 | Preserve byte-identical legacy behaviour absent a tokenizer-backed policy, except the declared truncation migration | **Yes**, verified by execution. `_build_messages` returns early when neither flag is set; `admission`/`context_policy_invocation` are conditional; goldens pass. I confirmed by running that the explicit-ceiling *record* is byte-identical too (the test only asserts payloads + system prompt — M1). One undeclared additive drift in `substrate_observation` (M2). |
| 5 | Capture response accounting before raising `TruncatedReply` on all four paths | **Yes.** `_take_response` (`taste_open.py:1440-1467`) appends to `acct.responses` and accumulates all four counters *before* the `finish_reason` check, and is the sole post-response step for all four paths. |
| 6 | Read recovery supersession from the top-level marker, accepting the nested form | **Yes.** `close.py:56-59` reads `recovered_from_run_id` top-level, `detail.recovered_from_run_id`, and `detail.retry_of_run`. Matches what `heartbeat.py:133` writes. |
| 7 | Keep compact retry bounded to one deliberate retry; preserve both attempts' records | **Yes.** Unlocked pre-check in the runner, authoritative re-check under the store lock (`events.py:1000-1004`), two rows in one fsynced buffer, and boot recovery copies the compact pending row so a recovered crash stays compact and cannot become a third deliberate attempt. |

---

## Findings

### Critical

**C1 — the natural loop's budget-recovery resend is bounded by a stale count.**
`src/hamutay/taste_open.py:2281-2318`

The recovery loop rebuilds the payload after `_truncate_largest_tool_results` mutates `conversation` and after `_withdraw_perception` may shrink the tool set, then calls `_send(..., precounted=precounted)` with the **same** `precounted` computed before the truncation (set at line 2235, never cleared inside the loop).

I confirmed this by execution against the branch's own fakes: a three-send wake takes only **two** counts, and the third send's `max_tokens` (45535) is derived from the second send's count (20000), not from its own, much smaller, bytes.

```
counts taken: 2  payloads sent: 3
max_tokens per send: [55535, 45535, 45535]
```

Why it matters: it breaks round-seven items 1 and 3 and the spec's own test ("the scripted tokenizer sees one count per send"). The invariant `prompt_tokens + max_tokens < limit` is asserted on a number that is not the payload's. The *direction* is conservative — the stale count is larger than the truncated payload, so `max_tokens` comes out smaller and the physical wall is not breached — which is why I have not called this a wall-breach. But the harness records and asserts a number it did not measure, on a door whose entire purpose is to never guess, and the generation is silently given less room than it has. Reachability is narrow but real: on a window-aware door the count+bound should prevent server-side context rejection, so entry requires the policy's limit to disagree with the server's actual `n_ctx` — exactly what a llama-server restarted with a different `-c` between rediscoveries produces, which is the operational item the ledger defers to after this merge.

Fix: clear `precounted` before the retry, one line at the end of the `except RuntimeError` block (after `_withdraw_perception`):

```python
precounted = None   # the conversation was mutated; recount these bytes
```

Add a test asserting one count per send across a recovery (the scratch test above is the shape).

### Important

**I1 — `context_policy_invocation` is written as `null` on every completed window-aware wake, and the real value only on failures.**
`src/hamutay/taste_open.py:3539` vs `:3741-3760`, condition at `:4212-4213`

The failure path passes `context_policy_invocation=self.context_policy.invocation_id`; the success path does not pass the argument at all. `_log_entry` writes the key whenever `self.context_policy.window_aware`, so a completed wake on the live qwen door records `context_policy_invocation: null` while a failed wake records the real invocation id. A reader cannot distinguish "no invocation known yet" from "the success path forgot to pass it", which is precisely the ambiguity the field exists to remove — and the live door's whole point is that completed wakes are the ones worth trusting. Fix: pass the same argument at `:3741`.

**I2 — window failures are routed by message text in one place, which round three finding 23 forbade.**
`src/hamutay/taste_open.py:2289-2290`, `_is_context_limit_error` at `:401-417`

`WindowFailure` subclasses `RuntimeError`, so all three typed failures enter the recovery loop's `except RuntimeError as e`. They escape today only because `_is_context_limit_error(e)` happens to return False for their message text. I verified all three currently escape — and I verified the fragility is real: a `CountUnavailable` wrapping a `/apply-template` refusal that quotes the server's own phrasing is caught.

```
CountUnavailable('500 ...: request (70000 tokens) exceeds the available context size (65536 tokens)')
  -> _is_context_limit_error == True
```

That is the likeliest text for the tokenizer endpoint to return on an oversized body, so this is not a contrived case. Consequence: instead of failing closed per spec §1, the wake truncates tool results and retries up to three times before re-raising. The compact retry still fires (the type survives), so nothing is lost permanently — but GPU and wall time are spent on a door that was supposed to spend zero, and the spec's "by type, never by message text" rule is broken. Fix: re-raise `WindowFailure` before the text test.

```python
except RuntimeError as e:
    if isinstance(e, WindowFailure):
        raise
    if not _is_context_limit_error(e) or turn_index == 0:
        raise
```

**I3 — `taste_open.py` is 4,740 lines and should gain a `window_backend` seam.**
`src/hamutay/taste_open.py`, +777/−170 on this branch

The window machinery is already a clean, contiguous, well-named block: `_FixedCount`, `Prepared`, `_default_http`, `policy`/`counter`/`_refresh_counter`, `_take_response`, `_send`, `_log_pressure`, `_path_for`, `_first_payload*` dispatch, `prepare`, `call_prepared` — about 350 lines at `:1226-1576`, depending on the backend only through `self`. `_exchange_impl` is now 484 lines. This is the natural split the Task 4 review already named (~240 lines then, ~350 now), and it will only get harder.

I recommend **after** merge, not before: the seam is a pure move with no behaviour change, and doing it now would invalidate every per-task diff the gates reviewed and the goldens' provenance story. File it as the first follow-up.

### Minor

- **M1 — the explicit-ceiling golden does not assert the record.** `tests/test_window_golden.py:52-58` checks `payloads` and `system_prompt` but not `rec`, unlike the no-ceiling test. The spec pins "every completed wake record". I ran the missing assertion: the record **is** byte-identical, so this is an unpinned guarantee, not a defect. Add `assert json.loads(json.dumps(rec, sort_keys=True, default=str)) == g["record"]`.
- **M2 — `substrate_observation` gains `window_aware`/`tokenizer`/`reasoning_budget` on every door, including non-window-aware ones.** `taste_open.py:4314-4319` guards on `is not None`, and `window_aware=False` is not None, so an explicit-ceiling door's observation grows three keys. Additive, on a stateless record `infer_launch_from_log` skips, so harmless — but it is drift from "byte-identical" that the spec does not declare. Either declare it or guard on `window_aware or None`.
- **M3 — `forced_sequence_tokens` falls back to a magic `96` silently.** `context_policy.py:143-146`: a `/tokenize` failure is swallowed with no log and an undeclared literal. On the live door `reasoning_budget == "unsupported"`, so it only shifts the floor check by a few tokens — immaterial today, dangerous if the budget ever becomes `probed`. Name the constant and log the fallback.
- **M4 — a tautological assertion.** `tests/test_context_ceiling.py:559`: `assert rec["context_policy_invocation"] is None or isinstance(rec["context_policy_invocation"], str)` is true of every possible value. It is the only test touching the field, and it is why I1 went unnoticed. Replace with the real expectation once I1 is fixed.
- **M5 — three linear passes per store in `close.py`** (`_latest_by_event_id`, `_runs_by_event`, `_completed_index`). Event stores are small and the old O(n²) scan is gone; not worth blocking, worth a note.
- **M6 — `build_session` re-creates `EventStore(event_log_path)`** while `main()` also creates one (`heartbeat.py:1302` and `:1478`). Harmless duplication from the extraction; tidy when convenient.
- **M7 — the launch probe uses `_default_http`, not the backend's `_http`** (`heartbeat.py:1383-1386`), because the policy is built before the backend exists, while `apply_context_limit` uses `self._backend._http`. Identical on a real door; only an injected transport would diverge.

---

## Ledger triage

Every `minor (deferred)` line, with a ruling.

| Task | Deferred minor | Ruling |
|---|---|---|
| 1 | unused `_tools()` in `tests/_window_golden_helpers.py`; docstring names `b7ab196` where the base was `9accc28` | **Defer.** Dead test helper and a wrong provenance string. The docstring one is worth a one-line fix whenever the file is next touched — provenance is the whole point of a golden — but it blocks nothing. |
| 2 | lazy import of `_result_cap_for_context_limit` not cycle-driven today | **Defer.** It *is* cycle-driven: `context_policy` → `taste_open` → `context_policy`. Leave the lazy import; the uncommented state is the only complaint and it is cosmetic. |
| 2 | probe's broad `except` folds response-shape bugs into `accepted=False` | **Defer.** Deliberate and correct for a probe: an unparseable answer is not an accepted capability. It records `error`, and the live evidence shows the classification landing where it should. |
| 3 | `project_context_results` passes non-dict/no-result items through silently | **Defer.** Conservative: an item the projector does not understand is copied, not dropped. The deep copy still happens via `lean_activity_logs`. |
| 4 | empty-payload probe readability (`bound_payload({}, ...)`) | **Defer.** `taste_open.py:2241` passes `{}` purely to reuse the floor arithmetic without mutating anything. It reads oddly; the comment above it explains why. Cosmetic. |
| 4 | per-backend `_last_counted_prompt_tokens` | **Defer.** Only read back into the natural loop's `last_counted_prompt_tokens` immediately after a send. No cross-wake leak. |
| 4 | `taste_open.py` +311 lines; window seam ~240 lines is the natural split | **Defer to a follow-up, tracked.** This is I3. Now ~350 lines. Post-merge, first follow-up. |
| 4 | test-file lint | **Defer.** Cosmetic. |
| 5 | `substrate_observation` records now carry policy fields (additive) | **Fix before merge (one line) or declare.** This is M2 — the only place the branch drifts from "byte-identical" without the spec saying so. Cheapest honest fix is guarding the three keys on `window_aware`. |
| 5 | transitional `_context_limit` setter survives for the guard-test fake | **Defer.** `apply_context_limit:4269-4271` reaches it only for a backend that does not share the holder. Guarded and commented. Remove when the fake goes. |
| 5 | `context_policy_invocation` null until a launch policy carries one (Task 9) | **Fix before merge.** The ledger deferred this as "Task 9 will set it", and Task 9 then recorded "no invocation id at launch (stays None until a lease rediscovery)". That is a fair outcome for *launch* — but it masked I1, which is a different bug: after a rediscovery the id exists and completed wakes still record `null`. Fix I1. |
| 6 | `admission=` missing on the state_merge failure `_log_entry` | **Defer.** The store record carries it; only the session-log row for that one failure mode omits it. |
| 6 | `envelope_admission` event shape unasserted | **Defer.** The admission outcome is asserted through `_last_admission` in four tests; the log event is observability. |
| 6 | no test drives an unsendable final candidate through `prepare(candidate=False)` | **Defer, but note.** `taste_open.py:3463-3471` is the path that turns an un-shrinkable envelope into the wake's recorded `ExhaustedBeforeRequest` — the second half of the live door's degradation story. `test_admission_first_candidate_below_the_floor_is_not_an_error` covers the recovering case only. Worth a test in the follow-up. |
| 6 | `result_cap_chars` None guard theoretical | **Defer.** `window_aware` implies a limit implies a cap. |
| 6 | `_exchange_impl` at 483 lines | **Defer with I3.** Same seam. |
| 6 | a compact event on a non-window-aware door omits the activity log while the envelope stays uncapped | **Defer.** Unreachable in practice: §6 gates the retry on `window_aware`, so nothing writes `compact_context` on such a door. Correctly flagged for Task 11. |
| 7 | a `JSONDecodeError` from a corrupt store inside `append_failed_with_retry` would still mask the original | **Defer.** `_note_unrecorded_failure` catches `OSError` only. A corrupt store is the pre-existing store hazard the spec declares and does not widen. |
| 7 | every claim now fsyncs | **Defer, accepted.** Spec-mandated ("this change gives `EventStore._append_unlocked` the same discipline"). Event stores are low-rate; correctness over throughput is the right trade here. |
| 7 | unreachable reason fallback (`"window_failure"`) | **Defer.** Defensive default on a three-way map. |
| 8 | `_runs_by_event` overlaps `_latest_by_event_id`/`_completed_index` (three passes) | **Defer.** This is M5. |
| 8 | nested `max()` comprehension in the cap-suppression rule | **Defer, but comment it.** `close.py:200-206` is the densest line on the branch and it decides a live tally. It is correct (I re-derived it), but it should carry a comment naming the rule in words. |
| 8 | store-order assumption undocumented in code | **Defer.** `_runs_by_event` marks supersession in record order, so it relies on append-order. True of the store by construction; worth a docstring line. |
| 8 | `str()` key asymmetry (`_runs_by_event` stringifies `event_id`, positions do not) | **Defer.** Fails in the conservative direction (no cap invented) and is the exposure `_latest_by_event_id` already had. |
| 9 | an import moved below argparse in `main()` | **Defer.** Cosmetic. |
| 9 | no unit test for the cached-probe short-circuit | **Defer.** Covered in `test_context_policy.py` at the `for_launch` level. |
| 9 | `heartbeat.py` +108 lines | **Defer.** `build_session` is a genuine improvement — it makes launch testable without a lock or a loop. |

Net: **one** deferred minor I would fix before merge (Task 5's `substrate_observation`, M2), **one** that turns out to hide a real bug (Task 5's `context_policy_invocation` → I1), and the rest correctly deferred.

---

## Rulings a fresh reader would question

**Task 8's cap-suppression rule — the one that changes a live tally.** This is the ruling to look hardest at, and the implementer flagged it himself as "a policy decision beyond the brief".

The shipped rule (`close.py:197-206`): a door's `position_from_failed_wake` cap is suppressed when that same door has an *eligible* position at a *higher seq* than its highest failed-wake position. I verified `active_positions` admits only `eligible is True` records and takes the highest seq, so the rule is exactly later-by-seq, eligible, same member — as the ledger claims.

The tension is real and the ledger states it honestly: assembly spec §7 step 5 caps unconditionally, and its stated *premise* is "a wake that terminated `failed` is not retried". The window spec §6 removes that premise and says a retry that records a position "supersedes it through `active_positions` as today" — which, as the ledger notes, was **not** true of the old code. So the implementer had to choose between the old spec's letter and the new spec's sentence. He chose the new sentence and wrote the narrowest rule that satisfies it.

I think that is the right call, and the reasoning is sound: a stance is capped because it is *unheard*, and a door that spoke again, in a completed wake, has been heard. But a fresh reader would reasonably ask why a *narrowing* of an assembly safety rule ships inside a harness change, and the answer has to be the operational rule and the assembly's review — which the ledger and the README held-matters entry already invoke. **Keep the ruling; make sure the assembly's review sees it as its own item, not as a line in a harness ledger.**

**Re-deriving the live tally.** I did this from the code rather than trusting Task 8's report, without reading `community/`. Old: cap iff `_latest_by_event_id[event_id].status == "failed"`. New: cap iff `_runs_by_event[event_id][position.run_id].status == "failed"`, minus the suppression. For the live question the qwen door has one run per event (the deferral at 09:06Z and the failure at 09:10Z are the same run), so the event's latest status *is* that run's status and both classifications agree; with no second run there is no eligible later position, so the suppression cannot fire. **The tally is identical today.** The Task 8 reviewer's claim holds. Every behavioural difference — a compact `pending` row no longer hiding the first attempt's failure, a superseded `running` no longer holding a question open — requires a second run, which no live event has.

**Task 10's ruling to proceed on an inert reasoning budget.** Correct and well-evidenced. The probe classifies the live door `unsupported`, so budget fields are never sent, and I traced that degradation by execution: 28K prompt, a tool turn, a near-wall turn, `finish_reason=length`. No `reasoning_budget_*` key on any payload; `prompt_tokens + max_tokens < limit` on both sends; perception withdrawn at the exact count (53000 ≥ 52428) with the note citing the server count; the truncation typed, carrying `turn_index`, real cumulative usage (81000 in / 20 out) and the earlier turn's text. Nothing on that path assumes `probed` — the one gate is `policy.reasoning_budget == "probed"` in `bound_payload`, and `forced_sequence_tokens` only shifts the floor. The design degrades exactly as the ruling claims.

**Task 4's ruling that the reasoning-budget gate is on `max_tokens`, not room (r6.1).** Correct, and the code comments it well (`window.py:107-111`). A configured `--max-tokens` below the unrestricted threshold should bound the think even when room is ample; gating on room would miss that.

**Task 6's `render_envelope` keyword ruling (r6.3).** Verified independently: every `exchange` double in the tree takes `**kwargs` or positional-then-kwargs, and two take `envelope` positionally. The rename was necessary and is correctly applied.

---

## Verdict

**Merge after the listed fixes.**

This is careful, honest work. The central structural claim holds and I verified it by walking the code rather than trusting the reports: there is exactly one `_post_chat` call site, behind exactly one `_send`, which bounds every window-aware request — so no path reaches the wire unbounded. The `_first_payload_*` refactor means `Prepared.payload` cannot drift from what the path actually sends. `_take_response` accounts before it judges, on all four paths. The byte-identity guarantee survives, verified by execution including the one assertion the goldens forgot to make. The store's two-row transition is genuinely atomic under the lock with an authoritative re-check. The live `unsupported` degradation works end to end. All 328 tests in the required suites pass, every test change is additive, and the frozen `tests/assembly_validation` suite is untouched.

Required before merge — small, local, and each with a named line:

1. **C1** — clear `precounted` before the recovery resend (`taste_open.py:2318`), plus a test asserting one count per send across a recovery. This is the only finding that breaks a round-seven must-not-get-wrong item in code rather than in principle.
2. **I2** — re-raise `WindowFailure` ahead of the text test in the same `except` (`taste_open.py:2289`). Two lines. Restores "by type, never by message text".
3. **I1** — pass `context_policy_invocation` on the success-path `_log_entry` (`taste_open.py:3741`), and replace the tautological assertion at `tests/test_context_ceiling.py:559` with a real one.
4. **M2** — either guard the three new `substrate_observation` keys on `window_aware` or declare the drift. One line either way.

Deliberately **not** blocking: I3, the `window_backend` seam. It is the right refactor and the wrong moment — a pure move now would invalidate every per-task diff the gates reviewed and muddy the goldens' provenance. First follow-up after merge, before `taste_open.py` grows again.

On the live restart and the 2026-09-24 tally: the close-pass change is inert on today's ledger (re-derived above), so the merge does not move the live question by itself. C1 and I2 both live on the natural loop's recovery path, which a correctly-configured window-aware door should not enter — but "should not" is what this whole design exists to replace with "cannot", and both fixes are a handful of lines. Fix them before the daemon restarts.

---

# Fix wave (commits a02b59d, c245903, 26b4df2, 01a1124; head ec2996d)

# Fix wave — window-aware wakes final review

One wave against `.superpowers/sdd/2026-09-17-window-aware-wakes/final-review.md`.
Base `5ca488f`, head `ec2996d` (branch `window`). Seven findings fixed: C1, I1, I2,
M1, M2, M3, M4. I3, M5, M6, M7 deferred per the brief's rulings — not touched.

Tests were written first for every behavioural fix and observed failing against the
pre-fix code before the fix landed. The failure output is quoted below for each, since
"the test fails first" is the only evidence that the test tests the thing.

---

## C1 — the recovery resend was bounded by a stale count

**Changed:** `src/hamutay/taste_open.py:2329` — `precounted = None` at the end of the
natural loop's `except RuntimeError` recovery block, after `_withdraw_perception` and
before the `recovery_attempt == 2` re-raise, with a comment naming why (the truncation
mutated `conversation` and the withdrawal may have shrunk the tool set, so the earlier
count describes bytes that are no longer being sent).

Also `src/hamutay/taste_open.py:2092-2094` — `WindowFailure` added to the natural
loop's `hamutay.window` import (shared with I2).

**Covering test:** `tests/test_context_ceiling.py:807` —
`test_budget_recovery_recounts_the_rebuilt_payload`. A three-send wake (tool turn,
`LLAMA_ERR`, recovered turn) with a scripted counter `[20000, 20000, 5000]`. Asserts
three sends and three counts; that each count saw the bytes its send carried
(`messages` and `tools` compared pairwise); that the resend's `max_tokens` is
`65536 - 1 - 5000` — derived from its own count, not the stale one; and
`prompt_tokens + max_tokens < limit` on all three.

**Failed first, on the pre-fix code:**

```
assert len(b.payloads) == 3 and len(b._counter.seen) == 3
E   assert (3 == 3 and 2 == 3)
```

with the third payload's `max_tokens` reading 45535 — exactly the review's reproduction
(`45535 = 65536 - 1 - 20000`, the second send's count, not the third send's bytes).

## I2 — typed window failures entered the recovery loop's text test

**Changed:** `src/hamutay/taste_open.py:2296` — `if isinstance(e, WindowFailure): raise`
as the first statement of the `except RuntimeError as e:`, ahead of
`_is_context_limit_error(e)`, with a comment naming the rule (routed by type, never by
message text — spec §1, round three finding 23).

**Covering test:** `tests/test_context_ceiling.py:846` —
`test_a_window_failure_quoting_the_servers_phrasing_never_enters_recovery`. A
`CountUnavailable("request (70000 tokens) exceeds the available context size (65536
tokens)")` — the likeliest text for `/tokenize` to return on an oversized body. The test
first asserts its own premise (`_is_context_limit_error(quoting)` is True), so it cannot
pass vacuously if that predicate's text matching ever changes.

Reaching the bug needed care: the failure must be raised from **inside** `_send`, which
is what the loop's `try` covers. My first draft raised it from the natural loop's own
count (outside the `try`) and passed against the buggy code — a false green. The
working shape drives turn 0 over the soft threshold so perception is withdrawn and
`precounted` is dropped; turn 1 then takes no count of its own, so `_send` counts, and
that count fails. Asserts one send only, no `budget_recovery` event, a
`count_unavailable` pressure event, and that `CountUnavailable` propagates.

**Failed first, on the pre-fix code:**

```
assert not _events(executor, "budget_recovery")
E   AssertionError: assert not [{'action': 'truncate_and_retry_tools_withdrawn', ...}]
```

(and, before the counter script was lengthened, an `IndexError` from the three retries
draining it — the wasted round trips the review predicted, made visible).

## I1 — completed window-aware wakes recorded a null invocation

**Changed:** `src/hamutay/taste_open.py:3774` — the success path's `_log_entry` now
passes `context_policy_invocation=self.context_policy.invocation_id`, exactly as the
failure path does at `:3553`.

**Covering test:** `tests/test_context_ceiling.py:884` —
`test_a_completed_window_aware_wake_records_the_invocation_id`. A window-aware policy
carrying `invocation_id="inv-live"`, a one-turn wake through `OpenTasteSession.exchange`,
asserting the completed wake's record carries `"inv-live"`.

**Failed first, on the pre-fix code:**

```
assert rec["context_policy_invocation"] == "inv-live"
E   AssertionError: assert None == 'inv-live'
```

The goldens are unaffected: their doors are not window-aware, so the key is absent from
those records as before (verified — `grep -c context_policy_invocation` over the three
fixture files returns 0, and the fixtures are byte-unchanged).

## M4 — the tautological assertion

**Changed:** `tests/test_context_ceiling.py:563-564`. Was
`assert rec["context_policy_invocation"] is None or isinstance(..., str)`, true of every
possible value. Now asserts the real expectation for that fixture: the key is **present**
(the door is window-aware) and **null** (that policy carries no invocation id). The other
half of the expectation — an id that exists and must be recorded — is the I1 test, named
in a comment at the site so the pair is findable from either end.

Note on commit boundaries: this edit landed in `a02b59d` rather than `c245903`, swept in
by that commit's `git add -A`. The `c245903` message describes it. Content is correct;
only the boundary differs from the message's implication.

## M1 — the explicit-ceiling golden did not assert the record

**Changed:** `tests/test_window_golden.py:62` — added
`assert json.loads(json.dumps(rec, sort_keys=True, default=str)) == g["record"]` to
`test_explicit_ceiling_without_tokenizer_is_byte_identical`, matching the no-ceiling
test at `:50`.

The record **is** byte-identical, as the review found, so this pins an unpinned
guarantee rather than fixing a defect. It is now the test that would catch `admission`
or `context_policy_invocation` leaking onto a door that is not window-aware. Passed on
first run; no fixture was regenerated (the golden JSON is byte-unchanged).

## M2 — `substrate_observation` grew three keys on every door

**Changed:** `src/hamutay/taste_open.py:4338-4341` — the three policy-state keys are now
guarded on window-awareness rather than `is not None`:
`("window_aware", window_aware or None)`, `("tokenizer", tokenizer if window_aware else
None)`, `("reasoning_budget", reasoning_budget if window_aware else None)`.
`context_policy_kept` and `reason` keep their `is not None` guard, so the
rediscovery-lost-the-tokenizer path (which passes `window_aware=old.window_aware`, True
there) still records everything it did. Docstring at `:4310` updated to state the rule.

**Covering test:** `tests/test_context_ceiling.py:668` —
`test_a_non_window_aware_door_is_not_blocked_from_gaining_a_ceiling`, adjusted as the
review directed. It previously asserted the drift (`rec["window_aware"] is False`); it
now asserts the three keys' absence.

**Failed first, on the pre-fix test against the fixed code:**

```
assert rec["window_aware"] is False
E   KeyError: 'window_aware'
```

The two window-aware observation tests (`..._records_the_new_policy_state`,
`..._kept_...`) still assert the keys present and pass unchanged, so the guard narrows
only the case it was meant to.

## M3 — the `/tokenize` fallback was a silent magic number

**Changed:** `src/hamutay/context_policy.py:25` — `FORCED_SEQUENCE_FALLBACK_TOKENS = 96`
with a comment giving the number its reasoning (a deliberately generous over-estimate of
the budget message plus think-end tag, so the floor check errs towards refusing a send
rather than towards a request that will not fit; a fallback, never a default).
`context_policy.py:152-156` — the bare `except Exception` now binds the error and prints
one line naming the failure and the number it fell back to.

**Covering test:** `tests/test_context_policy.py:143` —
`test_a_tokenize_failure_falls_back_to_the_named_constant_and_says_so`. Uses the existing
`FakeHTTP(fail={"/tokenize"})` route. Asserts `forced_sequence_tokens ==
FORCED_SEQUENCE_FALLBACK_TOKENS == 96` (so the constant cannot drift from the behaviour
silently), that the door stays window-aware with `reasoning_budget == "probed"` (a
missing forced-sequence length is not a missing tokenizer), and that the printed line
names both `/tokenize did not answer` and `96`. It imports the constant by name, so it
would not even collect against the pre-fix code.

---

## Suites

Required suites:

```
uv run pytest tests/test_context_ceiling.py tests/test_window_golden.py tests/test_window.py \
  tests/test_context_policy.py tests/unit/test_events.py tests/test_heartbeat.py \
  tests/test_event_ingress.py tests/assembly tests/assembly_validation \
  tests/gpu_lease_validation tests/test_heartbeat_guard.py -q -p no:cacheprovider
-> 431 passed in 24.39s
```

Full suite:

```
uv run pytest tests -q -p no:cacheprovider --ignore=tests/integration
-> 1977 passed, 5 skipped, 1 xfailed in 44.64s
```

(The review reported 328 for the required suites; that was a narrower selection. The
431 here is the full list as the brief specifies it, and every test in it passes.)

**Frozen and pinned artefacts unchanged**, verified by
`git diff --name-only 5ca488f HEAD -- tests/assembly_validation tests/fixtures/window_golden`
returning zero files. No golden was regenerated; the byte-identity tests pass against the
fixtures as captured.

Whole-wave diff, excluding OTS timestamps:

```
 src/hamutay/context_policy.py |  14 ++++-
 src/hamutay/taste_open.py     |  39 +++++++++++---
 tests/test_context_ceiling.py | 122 +++++++++++++++++++++++++++++++++++++++++-
 tests/test_context_policy.py  |  25 +++++++++
 tests/test_window_golden.py   |   4 ++
 5 files changed, 193 insertions(+), 11 deletions(-)
```

All five source/test changes are either a named fix or its covering test. No drive-by
edits.

## Commits

| sha | finding(s) |
|---|---|
| `a02b59d` | C1, I2 (and the M4 test edit, swept in) |
| `c245903` | I1 (message also covers M4) |
| `26b4df2` | M1, M2 |
| `01a1124` | M3 |

Each signed with the `hamutay@wamason.com` / `01193FA2...` identity via `-c` overrides,
each trailed `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. The post-commit
OTS hook added stamp commits `8dc0edb`, `6b67298`, `ba7a54f`, `ec2996d`. Head is
`ec2996d`; working tree clean.

## Constraints honoured

No `git stash` in any form. No request to `http://127.0.0.1:8081` (the M3 test's
`FakeHTTP` is the in-process double the suite already uses; the URL appears only as a
string). Nothing under `community/` read or written. Nothing restarted. All work in
`/home/tony/projects/hamutay/.worktrees/window` on branch `window`.

## Left open

Nothing from the assigned list. I3, M5, M6 and M7 were deferred by the brief and are
untouched — I3 (the `window_backend` seam) remains the named first follow-up after merge.

Two things a re-reviewer should look at rather than take on trust:

1. **The I2 test's reachability argument.** It asserts its own premise
   (`_is_context_limit_error(quoting)` is True) but its route to the bug is indirect —
   soft-threshold withdrawal on turn 0 so that turn 1 leaves `precounted` None and
   `_send` does the counting. If that route ever stops being the one that reaches
   `_send`'s count, the test could go green without testing anything. The premise
   assertion guards half of that; the `assert len(b.payloads) == 1` guards the other
   half only as long as the wake really gets to a second turn. I did invert the fix
   once to check this: deleting the two-line `isinstance(e, WindowFailure): raise`
   from the working copy fails the test (`1 failed, 2 passed`) and restoring it passes
   (`3 passed`), with the tree left clean. So the test is load-bearing today; the note
   is about keeping it that way.
2. **M2's choice.** The review offered "guard on `window_aware or None`, or declare the
   drift". I took the guard. That means a window-aware door's observation says
   `window_aware: true` and a plain door's says nothing — absence carries the negative.
   `infer_launch_from_log` skips these records, so nothing reads them today; if a future
   reader wants an explicit `false`, the spec should declare the drift instead and this
   should be reverted.

---

# Scoped re-review of the fix wave

Verdict: all seven findings addressed, no new Critical/Important breakage; C1 and I2 re-verified by reverting the fix and watching the covering test fail; full suite 1977 passed; goldens and the frozen assembly validation suite byte-unchanged. I3 (the window_backend seam), M5, M6, M7 deferred with rulings to after the merge.

---

# Live evidence (custodian, 2026-09-17 ~13:05 PDT, all doors quiet)

```
warning: `VIRTUAL_ENV=/home/tony/projects/hamutay/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
...probe: {
 "build_info": "b1-73a43d1",
 "model_alias": "qwen3.8-27b-q4km",
 "template_sha256": "c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041",
 "template_has_tags": true,
 "accepted": true,
 "control_had_think": true,
 "forcing_observed": false,
 "latency_s": 4.408307127014268,
 "queued": false
}
.observational (c) raw reply: {
 "finish_reason": "tool_calls",
 "index": 0,
 "message": {
  "role": "assistant",
  "content": "<think>\nThe user is asking me to call the clock tool. Let's do that.\n</think>\n\n",
  "tool_calls": [
   {
    "type": "function",
    "function": {
     "name": "clock",
     "arguments": "{}"
    },
    "id": "m1BlEfqrqKwBfjB6tBCLvokrQeHGyJkA"
   }
  ]
 }
}
.forced: 31 control: 31 zero: 33
.
6 passed in 51.70s
```

Reading: (a) the exact count equals the server's prompt_tokens on all three payload shapes. (b) the probe is stable; accepted, template has tags, the control thought, **forcing not observed**: the running llama-server (build b1-73a43d1, built from the commit that added the reasoning budget) accepts reasoning_budget_tokens and does nothing with it, in every reasoning format (custodian's per-request probe: zero budget → 31 completion tokens, identical to the control). The live door therefore classifies `unsupported` and never receives budget fields; the design degrades to exact count, bound, capture, lean rendering, admission and one compact retry, which the whole-branch review traced end to end. (c) tools active with a 32-token budget: a short think and a clean tool call. (d) forced sequence 31 tokens by /tokenize; no forcing to compare against. The server-side cause is a separate spike.

---

# Rulings made by the controller (from the ledger), in order

- | T2 ↔ T3 (window.py) | T2 imports BUDGET_MESSAGE/REPLY_RESERVE_TOKENS from window.py before T3 fills it | plan says T2 creates the constants block first; T3 fills the rest — Ruling: T2 creates window.py with the full constants block verbatim from T3 Step 3; costs nothing if wrong |
- Task 2: Ruling: two plan-test defects — (a) the test TEMPLATE fixture lacks the end tag; the module's rule (both tags present, per spec "The probe") stands and the fixture gains `</think>`; (b) the latency test feeds four ticks for two monotonic() calls; the test becomes ticks [0.0, 6.5] expecting latency 6.5 and queued True. Module code unchanged. Costs nothing if wrong (test-only).
- Task 3: Ruling: the reasoning-budget gate is on max_tokens (the generation limit sent), not room — the plan's test is right, the spec's §1 wording was wrong; spec amended to r6.1 on main; bound_payload line 'room < THINK_UNRESTRICTED_ROOM_TOKENS' becomes 'max_tokens < THINK_UNRESTRICTED_ROOM_TOKENS'; costs one comparison if wrong.
- Task 4: Ruling: (1) two plan tests asserted an unclamped max_tokens; max_tokens = min(configured, room) is the spec, so the expectations become min(64000, room). (2) test_three_turn_rule_holds_above_the_unrestricted_room is incoherent at limit 1000 (below the floor) and unobservable at limit 65536 (0.8·limit leaves room 13107 < 32768, so withdrawal is always near-wall there — a real property, noted): the test is rewritten at limit 200_000 with counts [160_000]*5 so room ≈ 40_000 ≥ 32768 and the three-turn rule is what applies. Deviations accepted: counter-root tracking, state_update in the terminal-surface helper, `precounted` so turn 0 counts once. taste_open.py at 4,318 lines noted for the final review. Costs test-only edits if wrong.
- Task 5: Ruling: the plan test's `json.dumps(rec).count("<think>cut") == 1` contradicts §4 (both `text` and the raw `message` are kept under truncated_reply; "once" means never in interim_text): the assertion becomes "not in json.dumps(rec['interim_text'])" plus the text equality; the record keeps both fields. Blocker (apply_context_limit no longer demotes) reported fixed; the legacy setter's one guarded caller (non-holder backends, for the guard test fake) noted; context_policy_invocation null until launch policies carry an invocation_id (Task 9 sets it from the discovered invocation where available — note for Task 9's dispatch).
- Task 6: Ruling: (1) the pass bound is an independent stop (spec r6.3): the all-stubs test becomes passes == ADMISSION_MAX_PASSES, over_target True, final_cap == MIN_STUB_CHARS, envelope_exhausted False, plus a compact=True case that is exhausted in one pass; the loop code stands. (2) the closure keyword is `render_envelope` (spec r6.3), because two existing exchange() test doubles take `envelope` positionally; no edits to files outside the task's list. Costs a rename if wrong.
- Task 8: Ruling: suppressing a member's failed-wake cap when that member later records an eligible position is spec §6 verbatim ("one that records a position supersedes it through active_positions as today"); stands; the reviewer checks the rule is exactly later-by-seq, eligible, same member, and that an eligible-then-failed ordering still caps. Fixture-signature adaptations and the extra ordering test accepted.
- Task 10: per-request probe by the custodian: reasoning_budget_tokens=0 with reasoning_format none/deepseek/auto all produced the full think (31 completion tokens each; control 31) — the field is accepted but INERT on the running server build. Ruling: proceed; the probe's "unsupported" classification is the honest outcome and the design degrades as specified (exact count, max_tokens bound, capture, compact retry, lean rendering, admission — no think bounding); whether the running binary predates llama.cpp's reasoning-budget feature is checked and recorded; rebuilding/restarting llama-server is a separate operations item after the merge, not this plan's. Costs nothing if wrong (the probe re-runs at every launch on a changed build).

---

# Codex's independent validation suite (tests/window_validation, frozen before first run)

Committed unrun at a7567e8 (17 tests; Codex's sandbox could not write the index, so the custodian committed on its behalf). First run: 14 passed, 11 failed. Ten failures were defects in Codex's harness (a malformed UUID in its event fixture; a missing required `reasons` keyword; a test double lacking `pending_state_updates`; a wrong reading of the closing's `tally.active` shape; `cap is None` where the rule returns an empty string), corrected by Codex in its own files across three passes (2ff5b9f, and the commits after 39558ad, ending 6f04f48). One failure was a code defect: on the multi-turn path a truncation snapshot carried no earlier-turn interim text; fixed test-first at c90d2ac with the success record unchanged. Final run: 25 passed (exit status 0). One process slip on the way: a commit message claimed 25/25 while one test still failed because a pipe masked pytest's status; corrected in 6f04f48's message and in memory.
