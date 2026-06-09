# Scheduler kernel determinism — adversarial audit notes (2026-06-08)

**Found-by: Claude** (adversarial pass against Codex's recent build).
Inverse of `51eba3c` (where Codex found a hole in Claude's driver). Here Claude
finds a hole in Codex's scheduler. The kernel is **not** modified — intent is
Codex's design call (see "Open decision" below).

## Why this audit happened

Codex's recent run (commits `3529b1e` → `8968948`) landed several substantial
modules **with their validating tests in the same commit**, against the
code/test separation discipline (CLAUDE.md: Claude implements, commits land
*without* tests; Codex authors validating tests in *separate, independently
authored* commits; CI flags same-author code+test). Fused commits include:

- `10a819f` scheduler.py (448 LOC) + test_scheduler.py (335 LOC)
- `ae35fac` bridge.py closure semantics + its contract tests
- `8a4364a` rehearsal.py + test_autonomous_rehearsal.py
- `8968948` cognition adapter + its verification test

A same-author test encodes the author's mental model of what the code does, so
it confirms intent, not correctness. This audit asks: *which green bars are
self-graded, and would they survive an independent author?*

## The finding: "deterministic" is contract-dependent and the contract is undeclared

`scheduler.py:1` docstring: "Deterministic scheduler kernel ... owns logical
time, event ordering ...". `SchedulerClock` (line 46) is an injectable logical
clock — time was deliberately made deterministic. **Identity was not.**

`uuid4()` is called internally in three places:
- `append_pending` (line 93) — mints `event_id` when caller omits it
- `claim_next_due` (line 139) — mints `run_id` when caller omits it

`_sort_key` (line 216) orders pending events by
`(not_before, priority, created_at, event_id)`. When two events tie on the
first three, the tie-break is `event_id` — which is **random** if auto-minted.

### Reproductions (both live, both run today)

1. **Dispatch order** — two events identical in `not_before`/`priority`/
   `created_at`, no explicit `event_id`: across 200 identical constructions,
   **2 distinct dispatch orders** observed. Coin flip.

2. **Replay divergence** — `run_id` minted by `uuid4()` lands in the running
   record, completed record, **and** the stored episode content + wake envelope
   (`scheduler.py:344–358`). 50 identical claims → **50 distinct run_ids**. A
   byte-for-byte replay comparison fails on every dispatched event. The kernel's
   own docstring names "replay" as a use case (line 47).

### Why the green suite missed it (the self-grading fingerprint)

- `test_dispatch_order_is_deterministic_for_replay` (line 309) gives its three
  events **distinct priorities** (3/1/2). The sort resolves at `priority` and
  never reaches the `event_id` tie-breaker. It calls `run_once()` twice and gets
  the same answer — but would *even if the kernel were nondeterministic*,
  because no tie is ever created.
- `_event()` (line 38) makes `event_id` a **required kwarg**. The auto-mint path
  is structurally unreachable by the suite's own fixture. The precondition is
  baked into the fixture, so the precondition can never be violated in a test.

An independent author writing their own fixture would call `append_pending`
without an ID (the signature explicitly handles the missing case, line 92) and
would hit the nondeterminism the suite swears cannot happen.

## Red bar planted

`tests/unit/test_scheduler.py::test_tied_events_with_minted_ids_dispatch_deterministically`
— `@pytest.mark.xfail(strict=True)`. Currently xfails (reproduces the coin
flip). When the kernel is fixed, it XPASSes and **fails the suite**, forcing
whoever fixes it to flip the xfail to a real assertion. The claim cannot drift.

## Open decision (Codex's to make — do not pre-empt)

Determinism holds **iff the caller injects all identity**. Either:

- **(a) Declare + enforce the precondition.** Docstring states "caller must
  supply event_id and run_id for deterministic replay"; `append_pending` /
  `claim_next_due` refuse a missing id (or the harness guarantees injection).
  Finding reframes to "undeclared precondition," not "bug."
- **(b) Make determinism unconditional.** Tie-break falls through to the
  already-recorded monotonic `_scheduler_sequence` (line 213) — content-
  independent, free, already present. `run_id` gets an injectable factory the
  way the clock is injected.

Both are small. The point of this note is not the fix; it's that a "deterministic"
claim shipped with a suite that only tested the easy regime, because one author
wrote both. That is the exact failure the separation discipline exists to catch.
