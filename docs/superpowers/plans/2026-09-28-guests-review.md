# Guests (plaza §11 r7) — whole-branch review record

Assembled by the custodian from the subagent-driven execution ledger of `docs/superpowers/plans/2026-09-28-guests.md` (branch `guests`, 66eecff..851ee01). Every task had a fresh implementer and a fresh reviewer; the whole-branch review ran on the most capable model; one fix wave and one scoped re-review followed. Every ruling the custodian made is on the ledger below, in order.

## Whole-branch review (at f7d85a5): findings and dispositions

- **Important 1** — the README's MCP command could not start the server from another project's cwd (`uv run` resolves that project's environment). Disposition: accepted; the command now reads `uv run --project /home/tony/projects/hamutay python -m hamutay.plaza.mcp --project-root /home/tony/projects/hamutay --guest <label>`, run from the guest's own directory; tested.
- **Important 2** — `plaza_read_impl` turned a malformed `members.json` (and "not enabled") into `[]`, hiding a broken house from a reader (plan-mandated). Disposition: accepted; the read path now raises, FastMCP reports the message; `[]` only for an absent file or an empty interval; send/post still return refusals as data; tested.
- **Important 3** — the guests dry run previewed no precondition (plan-mandated). Disposition: accepted; it now mirrors phase two's dry run and validates the candidate in a scratch copy, writing nothing beside the file; tested (ok case, dirty tree, no leftovers).
- **Important 4** — `--guests-ready` skipped the plaza checks. Disposition: accepted; only `--phase-one` skips them; an unreadable key is `FAIL`; tested.
- **Important 5** — `--guests LIST` replaces the list and nothing said so. Disposition: accepted; the README says "the full list, not an addition"; the script names the labels it drops before the trap; tested.
- **Minors fixed in the wave**: `ACTOR_RE` deleted; `n` computed and `n=0` refused before any stop; the candidate requires the plaza key; `sys.executable` in the journalctl shim; shimmed `check-plaza.sh` tests (default mode with `guests 2`, `--guests-ready`).
- **Parked with rulings** (see the ledger's last entry): stale `.candidate` unlink in dry mode; "dropping no guests" on an unreadable file; `2>/dev/null` on the key read; `LedgerMalformed` raising from a guest read (right); `UV_PROJECT` in tests.
- **Declined-to-judge lines** from the final reviewer, each ruled by the custodian as set aside for the reasons the reviewer gave: optional `since_seq`; `mcp` as a mandatory dependency (operational note: `uv sync` before activation (a)); rows carry `events_path` and `members_digest` to a guest (Invariant 12); CLI-vs-MCP trailing-newline text is a conflict (exact-text rule); `key=""` is no token; FastMCP's structured wrapping (smoke-tested by hand over stdio: initialize, tools/list, post, read, send all ok); `read_rows` lenient on a missing record; `load_members` fail-closed on non-UTF-8; the `/tmp` re-rooting pattern.

## The execution ledger (verbatim)

# SDD ledger — plan: docs/superpowers/plans/2026-09-28-guests.md

Spec: docs/superpowers/specs/2026-09-16-plaza-design.md r7 (537ba73), reviews four and five beside it. Worktree .worktrees/guests, branch guests from main 66eecff. Baseline: tests/plaza + tests/assembly 206 passed.

## Pre-flight scan (before Task 1)

| pair / task | produces vs consumes | found |
|---|---|---|
| T1 → T3 | ids.is_guest/guest_label/guest_key; send imports the same names | consistent |
| T1 → T4 | ids.is_guest/guest_label in event.py | consistent |
| T1 → T5 | ids.GUEST_RE in cli._by | consistent (T1 defines GUEST_RE and GUEST_LABEL_RE) |
| T1 → T7 | ids.GUEST_LABEL_RE in mcp.build_server | consistent |
| T2 → T3/T6 | MembersConfig.guests None vs () | consistent; T6 keys on `is not None` |
| T2 → T8 | bind note "; guests <n>"; check greps `guests $n\b`; migrate greps "plaza: door $d may send; log [^\"]*; guests $n" | consistent (JSON note ends with `guests N"`) |
| T2 conftest → T3/T4/T5/T7/T8 tests | write_members(root, plaza=, guests=) and house_guests | consistent |
| T3 → T7 | send(cfg, actor, via="mcp", to, text, now, key) | consistent |
| T5 → T7 | read_rows(cfg, since_seq, through_seq, posts_only, door, for_door) | consistent |
| T5 → T8 | window test uses read_rows and the CLI's --by guest:<label> | consistent |
| T1 self | rejection table: message substrings match the validator messages specified | consistent; "via cli needs a human actor" case updated in the same task |
| T3 self | duplicate lookup precedes the cap (retry of k3 is not a 49th) | consistent with send.py order |
| T4 self | plaza_note(cfg, door, store_records, on_error=) per note.py:62 | brief says read test_note.py first; acceptable |
| T7 self | after removal, the t1 conflict case is refused as not admitted (admission first); test asserts only sent False | consistent |
| T8 self | window test: the start stub plays the guest once; rollback restores file and removes snapshot; guest post survives | consistent with a0ca52b's rollback |
| rubric | no test asserts nothing; no verbatim logic duplication mandated (rollback shared by moving the function) | clean |

No rulings needed pre-flight.

## Tasks
Task 1: review at 04fa389 — spec ✅; Important: `$` anchors let a trailing newline satisfy the label grammar (plan-mandated `$`). Ruling: the spec says "exactly [a-z][a-z0-9-]{1,31}"; the plan's `$` is the defect, fullmatch/\Z is right — fix. Cost if wrong: none (strictly narrower). Minor (deferred): ACTOR_RE re-spells the grammar; GUEST_RE not built from GUEST_LABEL_RE; opaque key selection in the rejection test; DOOR_RE (pre-existing) also uses `$`.
Task 1: fix round 1/5 (1 addressed, 0 open — fullmatch/\Z anchoring; commits 04fa389..23394a4)
Task 1: complete (commits 66eecff..23394a4, review clean)
Task 2: review at 4bd2419 — spec ❌ on one item: binding.py GUEST_LABEL_RE `^…$` with .match (plan-mandated) — same ruling as Task 1: fullmatch. Minor (deferred): `match="guests"` vacuous because tmp_path contains the word; O(n²) seen list. ⚠️ consumers of the new field: resolved by controller — no consumer reads `guests` yet (Tasks 3, 6, 8 add them).
Task 2: fix round 1/5 (2 addressed, 0 open — fullmatch; message-matching test; commits 4bd2419..170a94f)
Task 2: complete (commits 23394a4..170a94f, review clean)
Task 3: review at a33dabe — spec ✅, approved. ⚠️ resolved by controller: the correlations are enforced in validate_plaza (Task 1, tested); prior["to"] is canonical because build_message canonicalises `to`. Minor (deferred): guest_label recomputed twice; empty-string token untested; gate refusals for guests untested (mcp+human, cli/mcp+wake, guest+tool); local imports in tests; cap test's T0 assumption.
Task 3: complete (commits 170a94f..a33dabe, review clean)
Task 4: review at 096559b — spec ✅, approved. ⚠️ resolved by controller: inbound_event_for passes sender=message["from"] (event.py:34, unchanged), so a guest's delivered event carries guest:<label> and the envelope branch fires; Task 3's test asserts store[0]["sender"] == "guest:levadura". Minor (deferred): door/human header byte-identity asserted by substring only; terse conditional in events.py.
Task 4: complete (commits a33dabe..096559b, review clean)
Task 5: review at c294e05 — spec ✅, approved; one metadata defect: the commit trailer names Haiku 4.5 instead of the house norm Fable 5.1. Ruling: amend the trailer (unpushed branch commit, metadata only) via the implementer — cost if wrong: none. ⚠️ resolved by controller: send's not-admitted path is Task 3's (tested there); cmd_read's LedgerMalformed is caught in main() (cli.py catches LedgerUnavailable/LedgerMalformed, pre-existing). Minor (deferred): exists() check before the lock (harmless race).
Task 5: fix round 1/5 (trailer amended, tree unchanged; c294e05 -> efbf2ea)
Task 5: complete (commits 096559b..efbf2ea, review clean)
Task 6: review at 6ead6d8 — code ✅; Important: (a) the caller-flag test re-evaluates the boolean instead of exercising the caller (plan-mandated: the plan's test was weak). Ruling: extract `guests_flag(assembly_binding) -> bool` in heartbeat.py, call it from build_session, test it with house_guests / house / house_unplaza bindings and pin that build_session's call site uses it (grep-free: monkeypatch guests_flag and assert build_constitution received its value via the existing build_session test path with --no-persist). Cost if wrong: a slightly indirect test. (b) an unrequested `guests` parameter on `_build_messages` — remove. Minor (deferred): golden compares two calls of the same function (plan-mandated); reviewer's trailer note is its own environment's instruction, the commit trailer is Fable 5.1 as required.
Task 6: fix round 1/5 (2 addressed, 0 open — guests_flag helper + caller test; extra param removed; commits 6ead6d8..e5ad181)
Task 6: complete (commits efbf2ea..e5ad181, review clean)
Task 7: implementer DONE_WITH_CONCERNS at b1716dc — `uv add "mcp>=1.0"` resolved to mcp 2.x which renamed FastMCP to MCPServer; implementer pinned `mcp>=1.0,<2` (1.30.0). Ruling: accept the pin for this plan (the brief's API is the 1.x one and the spec names FastMCP); migration to mcp 2's MCPServer is a follow-up, recorded here. Cost if wrong: a later dependency bump needs a small port.
Task 7: review at b1716dc — spec ✅, approved. Minor (deferred): OSError not turned into data in plaza_send_impl; plaza_read_impl lets LedgerMalformed raise (arguably right); unused label param on plaza_read_impl; unused imports in test_mcp.py; the <2 pin needs an MCPServer port someday. Controller note: stdio handshake (initialize + tools/list) to be smoke-tested by hand in Task 10 before the question is put.
Task 7: complete (commits e5ad181..b1716dc, review clean)
Task 8: implementer DONE_WITH_CONCERNS at 5fd06ee — two test deviations from the brief: (1) the install test's journalctl shim now derives the door from its -u argument (the brief's literal "door x" could never match "door <d>"); (2) the install test asserts the only tracked change is `M community/plaza/members.json` (in the test repo members.json is committed by the fixture; in the real house it is gitignored). Ruling: both accepted — the brief's test details were wrong, the behaviour under test is unchanged. Cost if wrong: none. Suite 2261 passed, 5 skipped, 1 xfailed, rc 0 (implementer's run).
Task 8: review at 5fd06ee — spec ✅ (one ❌ on the guests dry-run previewing no preconditions, plan-mandated), approved. Minor (deferred; the controller asks the final review to triage these for the fix wave before merge): (1) compute n and reject an empty list BEFORE the trap/stops (an empty list trips grep -c after the rename); (2) the guests dry-run previews no preconditions and runs no candidate validation; (3) migrate's verification pattern `guests $n` lacks \b (n=1 matches 12); (4) near-verbatim duplication of the candidate/stop/rename blocks with phase two; (5) /tmp candidate dir and .candidate left on a MembersMalformed failure; (6) empty n when uv fails; (7) test gaps: no tests for check-plaza --guests-ready / default-mode guests check / migrate unknown flag / dry-run; the journalctl shim calls `python3` (use sys.executable); (8) a trailing --guests/--merge with no value exits 1 not 2. ⚠️ resolved by controller: the phase-two candidate block is unchanged (the hoist moved text only; suite green).
Task 8: complete (commits b1716dc..5fd06ee, review clean)
Task 9: review at 46d9b18 — content ✅; placement flagged: the sections landed before "### Phase two", not "### Phase one". Ruling: the README's plaza subsections were already out of chronological order (my 9-28 edit put Phase two before Phase one); the brief's anchor assumed the wrong order. Fix by reordering the whole plaza tail chronologically: Phase one (9-18) → The second question (9-25) → Phase two (9-28) → Guests → The third question. Cost if wrong: none (documentation order). Also: the implementer's report contradicts itself on placement; correct it.
Task 9: fix round 1/5 (1 addressed, 0 open — chronological reorder, pure move; commits 46d9b18..f7d85a5)
Task 9: complete (commits 5fd06ee..f7d85a5, review clean)
All nine build tasks complete. Final whole-branch review dispatched on the most capable model over 66eecff..f7d85a5 (package review-66eecff..f7d85a5.diff).
Controller smoke test (not a review seat): real stdio handshake via mcp.client.stdio against a throwaway house with guests ["levadura"] — initialize ok, tools listed, plaza_post seq 1, plaza_read since 1 → 1 row, plaza_send to elder seq 2 landed. The stdio path Task 7's reviewer could not see works.
Final review at f7d85a5 (fable): ready with fixes — 5 Important, minors triaged. Rulings: I2 (read hides a malformed house; plan-mandated `[]`) — accept the reviewer's fix, let MembersMalformed/"not enabled" raise in plaza_read_impl (FastMCP reports the message), `[]` only for an absent file/empty interval; I3 (guests dry-run previews nothing; plan-mandated) — accept, mirror phase two's dry-run block plus a candidate check in a scratch copy; I4 (--guests-ready skips plaza checks) — accept, only --phase-one skips them; I1 (README MCP command needs `uv run --project`) — accept; I5 (the list replaces; say so in README and print dropped labels) — accept. Fix-before-merge minors: delete ACTOR_RE; compute n and refuse n=0 before idleness_upfront; require plaza key in the guests candidate check; a shimmed default-mode check-plaza test; sys.executable in the journalctl shim. Cost if wrong: a slightly larger fix wave. One fix dispatch, one scoped re-review.
Final fix wave: 851ee01 — re-review: all 5 Important and all listed minors ADDRESSED, no new breakage. Parked (rulings): dry-run `cand.unlink(missing_ok=True)` may delete a stale .candidate beside the file — Ruling: acceptable, the candidate is scratch and gitignored; "dropping no guests" printed when members.json is unreadable — Ruling: acceptable, the candidate check refuses next; `2>/dev/null` on the guests-key read hides the reason — Ruling: acceptable, FAIL is printed and the plaza-key check names the malformed file; plaza_read_impl lets LedgerMalformed raise — Ruling: right (a corrupt ledger must not read as empty); UV_PROJECT in the new deploy tests needs a uv that honours it — Ruling: this house's uv does (suite green); note for other machines. Branch ready for Codex validation and merge.
