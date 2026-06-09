# Autonomous Driver — Test Contract (handoff to the test author)

Date: 2026-06-08
Implementation author: Claude (hamutay instance)
Test author: **Codex** (a separate instance — code/test separation discipline)

## Why this document exists

`src/hamutay/memory/driver.py` was implemented by the same instance that wrote
its first tests (`tests/unit/test_autonomous_driver.py`). That violates the
project's code/test separation discipline (see
`docs/yanantin-handoff-open-record-queries.md`: "a contract to be handed to the
test author (Codex) … implementation commits land without tests; Codex follows
with signed commits containing the tests"). Claude-authored tests for this
driver are therefore **executable scaffolding, not independent validation** —
they can only catch bugs the implementer already imagined. This document hands
the driver's behavioral contract to Codex as test author, expressed as
properties so the shape is concrete. The validating tests are Codex's to author
and sign.

## What the driver is

`AutonomousDriver` replaces `chat.py`'s `while True: input()` with a loop where
the instance reads its OWN memory (through the `MemoryPort` bridge) to form its
next stimulus — no human keystroke. Per cycle: wake → read `open_items()` →
form stimulus from open work → run injected cognition → store the cycle as an
episode → link `continues` to the prior cycle → loop until idle or budget.

Cognition is a REQUIRED injected callable (`Cognition = Callable[[str], str]`);
`ChatSession.exchange` satisfies it. No autonomous run has spent API tokens —
the live wiring is proven by signature only.

## Properties the tests must enforce

### P1 — The loop closes (memory drives the next thought)
What cycle N surfaces as open work appears in cycle N+1's stimulus, reached
through the substrate, with no human in between. Cycle 1 wakes on the seed
(`woke_on == "seed"`); later cycles wake on memory (`woke_on == "open_items"`).

### P2 — The run is a walkable chain, not a heap
Each cycle's episode is linked `continues` to the prior. Walking forward from
cycle 1's record reaches every later cycle's record via `continues` edges.

### P3 — Consumption-time reason never enters production
The stored episode's `production` layer is `production_time` and carries no
`reason`/`wake_reason`. The wake reason appears only in the bridge's
consumption-time retrieval log (`reason.layer == "consumption_time"`).

### P4 — A substrate failure is a real block, not swallowed
If `open_items`/`store_episode`/`link_records` fails, the driver raises
`DriverBlocked`. A loop that silently continues past a memory failure is the
husk this project exists to prevent. (Drive with `LocalMemorySubstrate(available
=False)` to force it.)

### P5 — Three terminations, all real
IDLE: a cycle finds nothing open → run stops, `stopped_because` starts "idle".
RESOLUTION-IDLE: accumulated open work is closed by append-only attestation;
the next wake sees no live open items, while the original work and closure
chain remain recallable.
BUDGET: `max_cycles` reached → run stops, `stopped_because` starts "budget".

### P6 — Omission is observable, never silent  ← Codex named this as the FIRST adversarial test
The wake renders at most `_WAKE_RENDER_LIMIT` (5) open items inline. The
remainder MUST NOT be dropped silently. **The adversarial test Codex specified:
force MORE than five open items and assert that omission is RECORDED, not
silently dropped.** Specifically, the stored episode's `content.wake_omission`
must exist when items were dropped and must carry: `total_open`, `rendered`,
`omitted` (counts), and `omitted_handles` (record_id + source per dropped item).
When nothing is dropped, `wake_omission` must be absent/empty. The inline
rendered stimulus must also signal that items were omitted.

### P7 — Seed wake has provenance parity
The cold-start (seed) wake reads no memory but still emits a consumption-time
retrieval-log entry, so cycle 1 is not the one unprovenanced wake. Assert the
log contains a seed-wake `open_items` entry distinct from memory-wake entries.

## Former limitation closed by Codex

RESOLUTION-driven idle was originally identified as unreachable because
`open_items()` accumulated immutable content fields and did not honor
attestation status supersession. That limitation is now closed.

Current behavior:

- content open items receive stable handles;
- exact targeted closure attestations remove only the live open-work view;
- original records and closure attestations remain recallable;
- attestation chains collapse to the latest status per subject/kind/scope;
- `contested` remains live open work.

Relevant independent tests:

- `tests/unit/test_memory_bridge_contract.py`
  - `test_open_content_items_can_be_closed_by_exact_append_only_attestation`
  - `test_ambiguous_or_contested_targeted_attestation_does_not_close_open_content`
  - `test_attestation_open_items_collapse_to_latest_status_per_chain`
  - `test_contested_latest_attestation_remains_live_open_work`
- `tests/unit/test_autonomous_driver.py`
  - `test_resolved_open_work_allows_next_wake_to_idle_without_driver_state`

## Validation already run

`uv run pytest tests/unit/test_autonomous_driver.py
tests/unit/test_memory_bridge_contract.py -q` covered the independent driver
and bridge contracts after Codex added omission, seed-provenance, and
resolution-idle coverage.

The broader scheduler/memory slice also passed after closure semantics landed:

`uv run pytest tests/unit/test_scheduler.py tests/unit/test_autonomous_driver.py
tests/unit/test_memory_bridge_contract.py tests/unit/test_events.py
tests/unit/test_memory_tools.py tests/unit/test_apacheta_bridge.py -q`
