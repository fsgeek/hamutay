"""Autonomous driver: the loop that beats without a hand on the keyboard.

`chat.py` runs Hamut'ay as a human-driven instrument — `while True: input()`.
This module replaces the human with the instance consulting its OWN memory:
each cycle the driver wakes, reads its open items through the memory bridge,
forms the next stimulus from them (not from a keystroke), runs one cognition
step, writes the result back as an episode, surfaces what the result left
open, and binds the next wake to that episode. That is the missing autonomic
loop — the thing that turns a chat session into a self-driving instance.

Boundary discipline (see docs/yanantin-substrate-position.md and the
single-principal standing decision):

- The driver is a CONSUMER. It owns "what to do next" (relevance, intention).
  The substrate it drives owns structure and provenance. The driver never
  reaches past the MemoryPort contract.
- Cognition is injected, not hard-wired — it is a REQUIRED constructor argument
  with no default. `ChatSession.exchange` satisfies the `Cognition` contract and
  is the intended production wiring (spends API tokens); a deterministic callable
  can be supplied instead to run the loop end-to-end with no model calls. There
  is deliberately no default cognition: a driver with no cognition is not a thing
  that should silently no-op. This keeps the driver testable without burning a
  preparation run, exactly as the Projector was a replay instrument before it was
  a production path. (The live wiring is proven by signature, not yet exercised
  against the API — no autonomous run has spent tokens.)
- Every cycle is stored with production-time coordinates kept distinct from
  the consumption-time reason that drove the wake. The bridge enforces the
  layer separation; the driver must not smuggle a reason into production.

The driver does NOT schedule wall-clock wakes or bind to result records across
process restarts — that is substrate-side (Yanantin) and gated. What it proves
today is the closed cognition↔memory loop against the local substrate: the
instance's stored state shapes its next thought without a human in between.

THREE TERMINATIONS, all real and tested:
- IDLE — a cycle wakes, finds nothing open, and ends the run. Reachable today
  whenever the instance surfaces no open work.
- RESOLUTION-IDLE — accumulated open work is explicitly closed by append-only
  attestations in the substrate, so the next wake sees no live open items while
  the original work and its closure chain remain recallable.
- BUDGET — max_cycles guillotine; the loop never runs unbounded.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from hamutay.memory.bridge import MemoryPort

# A cognition step: given the stimulus text for this cycle, produce the
# instance's response text. ChatSession.exchange satisfies this contract (the
# intended production wiring); a deterministic stand-in lets the loop run with no
# API calls. Required — there is no default cognition.
Cognition = Callable[[str], str]

# Given a cycle's stimulus and response, decide what this cycle leaves OPEN for
# the next wake to pick up. Returns a list of open-item dicts (may be empty).
# Default extracts nothing; a real instance would parse its tensor's declared
# losses / instructions-for-next. Injected so the loop is testable.
OpenItemExtractor = Callable[[str, str], list[dict]]


def _default_open_items(stimulus: str, response: str) -> list[dict]:
    """No open items by default. A working instance overrides this to surface
    its tensor's declared_losses / instructions_for_next so the loop continues."""
    return []


@dataclass
class CycleResult:
    """What one autonomous cycle did. Production-time facts only — the reason
    that drove the wake is logged consumption-time by the bridge, not here."""

    cycle: int
    record_id: str
    stimulus: str
    response: str
    open_items_surfaced: list[dict]
    woke_on: str  # "seed" | "open_items" | "idle"
    wake_omission: dict = field(default_factory=dict)  # what the wake dropped


@dataclass
class DriverReport:
    """The arc of an autonomous run, in the driver's own (interior) terms."""

    cycles: list[CycleResult] = field(default_factory=list)
    stopped_because: str = ""

    @property
    def ran(self) -> int:
        return len(self.cycles)


class AutonomousDriver:
    """Drives a cognition step from the instance's own memory, no human input.

    The loop, per cycle:
      1. WAKE   — read open_items() from the bridge (the instance's own
                  unfinished business), forming the next stimulus.
      2. DECIDE — open work continues it; nothing open falls back to the seed
                  intention, then to idle (which ends the run).
      3. ACT    — run the injected cognition step on the stimulus.
      4. WRITE  — store the cycle as an episode (production coords distinct
                  from the consumption-time wake reason) and link it to the
                  prior cycle so the graph is walkable.
      5. BIND   — remember this episode as the anchor for the next what_changed,
                  loop until budget exhausts or the instance goes idle.
    """

    def __init__(
        self,
        substrate: MemoryPort,
        cognition: Cognition,
        *,
        seed_intention: str,
        open_item_extractor: OpenItemExtractor = _default_open_items,
        instance_id: str = "hamutay-autonomous",
    ) -> None:
        self._substrate = substrate
        self._cognition = cognition
        self._seed = seed_intention
        self._extract_open = open_item_extractor
        self._instance_id = instance_id
        self._cycle = 0
        self._last_record_id: str | None = None

    # How many open items the wake stimulus renders inline. The rest are NOT
    # dropped silently — they are recorded as an omission (count + handles) in
    # the stored episode, because a consumer that owns budget owns observable
    # omission. "omission is data" (project discipline).
    _WAKE_RENDER_LIMIT = 5

    def _next_stimulus(self) -> tuple[str, str, str, dict]:
        """Form the next stimulus from the instance's own memory.

        Returns (stimulus_text, wake_reason, woke_on, omission). woke_on is
        "seed" on the first cycle, "open_items" when continuing prior work,
        "idle" when nothing is open — which ends the run. omission is a record
        of what the wake rendering selected vs. dropped (empty {} when nothing
        was dropped); it is stored on the episode so truncation is never silent."""
        if self._cycle == 0:
            # The seed wake reads no memory, but is logged for provenance parity
            # with memory wakes — otherwise cycle 1 is the one unprovenanced wake.
            # A failure here is a real block, with the SAME discipline as the
            # memory wake below: a provenance write that silently fails would
            # leave cycle 1 unprovenanced after claiming it was logged.
            seed_log = self._substrate.open_items(
                reason="autonomous seed wake: cold start (reads nothing)"
            )
            if not seed_log.ok:
                raise DriverBlocked(
                    "seed-wake open_items failed: "
                    f"{seed_log.error.code if seed_log.error else 'unknown'}"
                )
            return (self._seed, "cold start from seed intention", "seed", {})

        items = self._substrate.open_items(
            reason="autonomous wake: what is unfinished?"
        )
        # A read failure is a real blocking condition, not an empty result.
        if not items.ok:
            raise DriverBlocked(
                f"open_items failed: {items.error.code if items.error else 'unknown'}"
            )
        open_list = items.data.get("items", [])
        if not open_list:
            return ("", "nothing open", "idle", {})

        selected = open_list[: self._WAKE_RENDER_LIMIT]
        dropped = open_list[self._WAKE_RENDER_LIMIT :]
        omission: dict = {}
        if dropped:
            omission = {
                "total_open": len(open_list),
                "rendered": len(selected),
                "omitted": len(dropped),
                # handles, not full items: enough to find them, not a second copy
                "omitted_handles": [
                    {"record_id": it["record_id"], "source": it["source"]}
                    for it in dropped
                ],
            }
        rendered = "; ".join(
            f"[{it['source']}] {it['item']}" for it in selected
        )
        if dropped:
            rendered += (
                f" (+{len(dropped)} more open item(s) omitted from this wake's "
                "rendering; see episode omission record)"
            )
        stimulus = (
            "Continue your own open work. Outstanding items from prior cycles: "
            f"{rendered}"
        )
        return (stimulus, "continuing open work from prior cycle", "open_items", omission)

    def _store_cycle(
        self,
        stimulus: str,
        response: str,
        wake_reason: str,
        woke_on: str,
        wake_omission: dict,
    ) -> tuple[str, list[dict]]:
        """Write this cycle back as an episode and link it to the prior one.
        Returns (record_id, open_items_surfaced). Raises DriverBlocked on a
        substrate write failure — a loop that can't persist is not autonomous.

        wake_omission records what this cycle's wake rendering dropped (empty
        when nothing dropped); stored on the episode so truncation is auditable,
        never silent."""
        surfaced = self._extract_open(stimulus, response)
        record_id = str(uuid4())
        content: dict[str, Any] = {
            "stimulus": stimulus,
            "response": response,
        }
        if surfaced:
            content["open_items"] = surfaced
        if wake_omission:
            content["wake_omission"] = wake_omission

        stored = self._substrate.store_episode(
            record_id=record_id,
            record_type="autonomous_cycle",
            content=content,
            production={
                "who": {"instance": self._instance_id},
                "what": {"artifact": "autonomous_cycle"},
                "when": {"cycle": self._cycle},
                "where": {"project": "hamutay"},
            },
            execution_trace={"tool_path": "autonomous_driver", "woke_on": woke_on},
        )
        if not stored.ok:
            raise DriverBlocked(
                f"store_episode failed: {stored.error.code if stored.error else 'unknown'}"
            )

        # Link to the prior cycle so the run is a walkable chain, not a heap.
        if self._last_record_id is not None:
            linked = self._substrate.link_records(
                from_record_id=self._last_record_id,
                to_record_id=record_id,
                relation_type="continues",
                provenance={"actor": self._instance_id, "wake_reason": wake_reason},
            )
            if not linked.ok:
                raise DriverBlocked(
                    "link_records failed: "
                    f"{linked.error.code if linked.error else 'unknown'}"
                )
        return record_id, surfaced

    def run(self, max_cycles: int) -> DriverReport:
        """Beat for up to max_cycles, or until the instance goes idle (nothing
        open) or hits a blocking substrate condition. max_cycles is the budget
        guillotine — the driver never runs unbounded."""
        report = DriverReport()
        for _ in range(max_cycles):
            stimulus, wake_reason, woke_on, wake_omission = self._next_stimulus()
            if woke_on == "idle":
                report.stopped_because = "idle: no open work remained"
                return report

            self._cycle += 1
            try:
                response = self._cognition(stimulus)
                record_id, surfaced = self._store_cycle(
                    stimulus, response, wake_reason, woke_on, wake_omission
                )
            except Exception:
                self._cycle -= 1
                raise
            self._last_record_id = record_id
            report.cycles.append(
                CycleResult(
                    cycle=self._cycle,
                    record_id=record_id,
                    stimulus=stimulus,
                    response=response,
                    open_items_surfaced=surfaced,
                    woke_on=woke_on,
                    wake_omission=wake_omission,
                )
            )

        report.stopped_because = f"budget: reached max_cycles={max_cycles}"
        return report


class DriverBlocked(RuntimeError):
    """The loop hit a real blocking condition — a substrate read/write failed.
    Raised rather than swallowed: an autonomous loop that silently continues
    past a memory failure is the husk this whole project exists to prevent."""
