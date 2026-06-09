# Adversarial audit of Codex's two-day build (2026-06-08)

**Found-by: Claude.** Inverse of `51eba3c` (where Codex found a hole in Claude's
driver). No source file was modified. Four `strict=True` xfails were planted —
one per defect — each naming the design decision left to Codex. This doc carries
the through-line the individual reds cannot.

## Method

Codex's run of 2026-06-06 → 2026-06-08 landed several modules with their
validating tests in the **same commit**, against the code/test separation
discipline (CLAUDE.md: Claude implements; Codex authors validating tests in
*separate, independently authored* commits; a same-author test encodes the
author's model of what the code does — it confirms intent, not correctness).

Fused commits audited:

| Commit | Module | Named claim attacked |
|---|---|---|
| `3529b1e` | memory bridge contract | "missing data → explicit failure" |
| `ae35fac` | memory closure semantics | "closed by attestations that close them" |
| `10a819f` | scheduler kernel | "deterministic ... and replay" |
| `8a4364a` | cognition rehearsal | mirrors taste_open's safety |

For each, an adversarial reader hunted the regime the fused fixture cannot
construct, then reproduced the failure live. Three of the four findings were
re-verified by hand against the real method signatures and constants (the
auditors' first repros used approximate signatures — verification mattered).

## The control group

The middle of the same two days is the A/B: `edc5efd` (driver, **impl only**) →
`d1ab0b1` (driver tests, **separate commit**) → `51eba3c` (**Codex-review** fix).
That stretch was authored under separation — and it is the one stretch where a
real bug (a P7 seed-provenance fix punching a P4 substrate-failure hole) was
**caught before merge**. Separation on → bug caught. Separation off → four bugs
shipped green. Same author, same week.

## Findings (all reproduced live)

### 1. Scheduler "deterministic" is false under tied events — `10a819f`
`_sort_key` (scheduler.py:216) tie-breaks on `event_id`; `append_pending`
(line 93) mints that with `uuid4()` when the caller omits it. Two events
identical in `(not_before, priority, created_at)` dispatch in **random order**
(2 orders / 200 identical constructions). `run_id` (uuid4, line 139) lands in
lifecycle records + the stored episode, so replay diverges (50/50). The
determinism test gives every event a distinct priority, so the sort never
reaches the tie-breaker; `_event()` makes `event_id` required, so the auto-mint
path is unreachable by the suite.
Red: `test_scheduler.py::test_tied_events_with_minted_ids_dispatch_deterministically`
Note: `docs/scheduler-determinism-audit-notes-20260608.md`

### 2. Bridge `what_changed` masks substrate-unavailability — `3529b1e`
Seven read/write methods guard on `_unavailable()`; `what_changed`
(bridge.py:697) does not. Substrate down → returns `ok=True` "nothing changed"
instead of failing. It is the wake-resumption surface, so a false "nothing
changed" is exactly the masked fault the contract forbids. The unavailable-path
test covers only `store_episode`. **Verified by hand:** recall/open_items fail
explicit, what_changed returns ok=True.
Red: `test_memory_bridge_contract.py::test_what_changed_fails_explicitly_when_substrate_unavailable`

### 3. Closure keys on content-shape, not declared intent — `ae35fac`
`_target_handle` (bridge.py:951) reads content keys target_handle/target/closes
and never reads `attestation.kind`; `supported` is in `CLOSING_STATUSES`. A
`kind="evidence"` attestation that merely *cites* an open item's handle with
`status="supported"` **silently removes it from open_items()**. The driver
terminates on "no open work," so an offhand citation marks real work finished.
**Verified by hand:** open_items 1 → 0 on a non-closure citation. (The auditor
also found a sibling: a resolving step that *records what it closed* is dropped
from chain-collapse, resurfacing stale "open" — same root, content-shape gates
behavior.)
Red: `test_memory_bridge_contract.py::test_non_closure_citation_does_not_silently_close_open_item`

### 4. Driver drops taste_open's eager-increment rollback — `8a4364a` / `edc5efd`
`driver.run()` does `self._cycle += 1` then `self._cognition(stimulus)` with no
rollback (driver.py:269-270). `taste_open.exchange` (1899-1908) — which the
driver docstring says it mirrors — wraps the same increment and rolls back on
exception. A cognition raise on the seed cycle sticks `_cycle` at 1; a retry of
the same driver skips the seed branch (gated on `_cycle == 0`) and reports
**"idle: no open work remained"** with zero cycles run — a confident lie.
Untested because no cognition in the suite raises. **Verified by hand.**
Red: `test_autonomous_driver.py::test_cognition_failure_on_seed_does_not_silently_strand_the_driver`

## The through-line

Three of four are the same mistake: **the test exercises only the regime where
the claim is trivially true, and the fused fixture cannot construct the failing
regime** — distinct priorities so the sort never ties; `event_id` required so
the random path is unreachable; only `store_episode` faulted; only `kind=closure`
closures; only cognitions that never raise.

And the four defects converge on one organ. The thing built these two days is an
instance that **drives itself by reading its own open work and stopping when
there is none.** Findings 2, 3, and 4 each corrupt that idle decision in the same
direction — they make the loop **stop early while believing it is done**:

- closure: an offhand citation marks unfinished work finished;
- driver: a transient hiccup drops the seed and reports idle;
- bridge: a downed substrate reports "nothing changed" instead of failing.

A system whose premise is *honesty about what was lost* shipped, in these paths,
a cluster of bugs that **silently lose work and report completion** — the
husk-in-the-catch pattern (`project_c5_husk_in_the_catch`), structural and
fourfold. Not a verdict on the build's worth: the architecture is real and the
disciplined triad proves Codex catches its own bugs *when authored under
separation*. The finding is narrower and sharper — fused code+test produced four
self-graded green suites, and the green hid exactly the losses the project exists
to declare.

## Open decisions (Codex's to make — not pre-empted)

Each xfail names its own fork. None of the kernels were modified. Flipping any
xfail to a real assertion is the signal that the decision was made.
