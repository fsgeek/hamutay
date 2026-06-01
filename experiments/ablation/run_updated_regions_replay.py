"""Controlled replay: does restoring `updated_regions` bootstrap curation?

Replays the exact user_message sequence from a source taste_open log through a
fresh instance under two prompt conditions, everything else held constant:

  A (implicit)        — current _SYSTEM_PROMPT (control; should reproduce the
                        observed flatline-until-the-relational-prods-land)
  B (updated_regions) — the pre-simplification "default-stable" paragraph
                        restored, asking the instance to declare the keys it
                        changes each cycle.

Held constant: same model, tools OFF in both (avoids unbounded bash in the live
repo and removes the Tools-section confound), involuntary memory disabled
(force_memory=None + base_prob 0). DV = state-key-count trajectory per cycle.

If B grows state earlier/more than A on the SAME conversation, the
`updated_regions` ritual is isolated as the structural forcing-function — the
thing Tony had to supply by hand (relationally) in the original 001508 run.
If B also fossilizes, the ritual is innocent and the relationship did the work.

Swap is prompt-text-only: _build_messages reads the module global _SYSTEM_PROMPT,
and _apply_updates ignores `updated_regions` (reserved field), so restoring the
ritual changes nothing about how state is applied — only what the instance is
asked to do.
"""

from __future__ import annotations

import json
import sys

import anthropic

import hamutay.taste_open as T
from hamutay.taste_open import AnthropicTasteBackend, OpenTasteSession

SOURCE = "experiments/taste_open/taste_open_20260528_001508.jsonl"
MODEL = "kimi-k2.6"

# Must match the current paragraph in _SYSTEM_PROMPT byte-for-byte.
_IMPLICIT_PARA = (
    "The object is default-stable: whatever top-level keys you include "
    "this cycle are your updates, and any key you don't include carries "
    "forward unchanged from last cycle. If this is the first cycle, "
    "everything you include is new."
)
# The pre-simplification paragraph (verbatim from taste_open_20260512's prompt).
_UPDATED_REGIONS_PARA = (
    "The object is default-stable: list the keys you're changing in "
    "`updated_regions`, and include those keys with their data in the object. "
    "Anything not listed carries forward unchanged from last cycle. If this "
    "is the first cycle, everything you include is new."
)


def load_user_messages(path: str) -> list[str]:
    msgs: list[tuple[int, str]] = []
    for line in open(path):
        if not line.strip():
            continue
        r = json.loads(line)
        um = r.get("user_message")
        if um is not None:
            msgs.append((int(r["cycle"]), um))
    msgs.sort(key=lambda x: x[0])
    return [m for _, m in msgs]


def build_variant_prompt() -> str:
    assert _IMPLICIT_PARA in T._SYSTEM_PROMPT, (
        "implicit default-stable paragraph not found in _SYSTEM_PROMPT — "
        "the prompt changed; update _IMPLICIT_PARA before running."
    )
    return T._SYSTEM_PROMPT.replace(_IMPLICIT_PARA, _UPDATED_REGIONS_PARA)


def run_condition(
    messages: list[str], mode: str, out_path: str, memory_on: bool = False
) -> list[int]:
    original = T._SYSTEM_PROMPT
    if mode == "updated_regions":
        T._SYSTEM_PROMPT = build_variant_prompt()
    try:
        backend = AnthropicTasteBackend(
            client=anthropic.Anthropic(), max_tokens=64000
        )
        session = OpenTasteSession(
            model=MODEL, backend=backend, log_path=out_path, bridge=None,
            resume=False, enable_tools=False,
            memory_base_probability=0.1 if memory_on else 0.0,
        )
        traj: list[int] = []
        for i, um in enumerate(messages, start=1):
            # memory_on: let _pick_memory fire (involuntary injection of a prior
            # self). memory_off: force None to hold injection constant.
            if memory_on:
                session.exchange(um)
            else:
                session.exchange(um, force_memory=None)
            st = session.state or {}
            nk = len([k for k in st.keys() if k != "_activity_log"])
            mem = "" if not memory_on else (
                f" mem<-{session._last_injected_memory[0]}"
                if session._last_injected_memory else ""
            )
            traj.append(nk)
            print(f"  [{mode}{'+mem' if memory_on else ''}] cyc {i:2d}: {nk} keys{mem}", flush=True)
        return traj
    finally:
        T._SYSTEM_PROMPT = original


def main() -> None:
    msgs = load_user_messages(SOURCE)
    print(f"Loaded {len(msgs)} user messages from {SOURCE}")
    if "--smoke" in sys.argv:
        v = build_variant_prompt()
        print("variant has updated_regions:", "updated_regions" in v)
        print("implicit para present in base:", _IMPLICIT_PARA in T._SYSTEM_PROMPT)
        print("first message:", repr(msgs[0][:80]))
        print("smoke OK")
        return
    for a in sys.argv:
        if a.startswith("--cycles="):
            msgs = msgs[: int(a.split("=")[1])]

    for a in sys.argv:
        if a.startswith("--baseline-n="):
            k = int(a.split("=")[1])
            print(f"Baseline distribution: implicit, tools off, memory OFF, "
                  f"n={k}, {len(msgs)} cycles each")
            finals: list[int] = []
            for run in range(k):
                t = run_condition(
                    msgs, "implicit",
                    f"experiments/ablation/baseline_run{run}.jsonl",
                )
                finals.append(t[-1])
                print(f"  >> run {run}: final {t[-1]} keys "
                      f"(peak {max(t)})", flush=True)
            print("\nFINAL key counts:", finals)
            print(f"min={min(finals)} max={max(finals)} spread={max(finals)-min(finals)}")
            return

    if "--memory-isolation" in sys.argv:
        # implicit prompt, tools off, involuntary memory ON — isolates whether
        # the husk-injection loop suppresses curation. Compare to replay_implicit
        # (same everything, memory off).
        print(f"Memory-isolation arm: implicit prompt, tools off, memory ON, {len(msgs)} cycles")
        t = run_condition(
            msgs, "implicit",
            "experiments/ablation/replay_implicit_memoryon.jsonl", memory_on=True,
        )
        print("\nimplicit+memoryON traj:", t)
        return

    print(f"Replaying {len(msgs)} cycles per condition, model={MODEL}, tools=off")
    a = run_condition(msgs, "implicit", "experiments/ablation/replay_implicit.jsonl")
    b = run_condition(msgs, "updated_regions", "experiments/ablation/replay_updated_regions.jsonl")
    print("\nimplicit        traj:", a)
    print("updated_regions traj:", b)


if __name__ == "__main__":
    main()
