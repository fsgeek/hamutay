"""Wake-mode spike metrics — docs/wake-mode-preregistration-20260827.md.

Deterministic over the session JSONL in experiments/wake_mode/runs/. Committed
before the run so it cannot be tuned to the data. Prints a markdown table and
writes metrics.json beside the runs.

    uv run python experiments/wake_mode/metrics.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RUNS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("experiments/wake_mode/runs")
NAME = re.compile(r"^(terminal|natural)_(.+)_(\d+)\.jsonl$")
ACTING_TOOLS = {"read", "bash", "search_project"}
POINTER_TARGETS = {2: "ayllu-story.md", 3: "original-taste-open-468.txt"}
WORK_TARGETS = ("heartbeat.py", "derive_quiet_reason")


def _touches(activity: list[dict], needles: tuple[str, ...]) -> bool:
    for entry in activity or []:
        if entry.get("tool") not in ACTING_TOOLS:
            continue
        params = json.dumps(entry.get("parameters", {}), default=str)
        if any(n in params for n in needles):
            return True
    return False


def _durable_change(prior: dict | None, state: dict | None) -> bool:
    def content(d):
        return {k: v for k, v in (d or {}).items() if not k.startswith("_") and k != "cycle"}
    return content(prior) != content(state)


def main() -> None:
    cells: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "sessions": 0,
            "wakes": 0,
            "pointer_wakes": 0,
            "pointer_reads": 0,
            "durable_changes": 0,
            "work_wakes": 0,
            "work_acts": 0,
            "update_state_calls": 0,
            "failed_wakes": 0,
        }
    )
    for path in sorted(RUNS.glob("*.jsonl")):
        m = NAME.match(path.name)
        if not m:
            continue
        arm, model, _trial = m.groups()
        cell = cells[(arm, model)]
        cell["sessions"] += 1
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("state") is None:
                cell["failed_wakes"] += 1
                continue
            cycle = rec.get("cycle")
            activity = rec.get("tool_activity_full") or []
            cell["wakes"] += 1
            if cycle in POINTER_TARGETS:
                cell["pointer_wakes"] += 1
                if _touches(activity, (POINTER_TARGETS[cycle],)):
                    cell["pointer_reads"] += 1
            if cycle == 4:
                cell["work_wakes"] += 1
                if _touches(activity, WORK_TARGETS):
                    cell["work_acts"] += 1
            if _durable_change(rec.get("prior_state"), rec.get("state")):
                cell["durable_changes"] += 1
            cell["update_state_calls"] += sum(
                1 for e in activity if e.get("tool") == "update_state"
            )

    def frac(n, d):
        return f"{n}/{d} = {n / d:.2f}" if d else "n/a"

    rows = []
    out = {}
    for (arm, model), c in sorted(cells.items()):
        m1 = frac(c["pointer_reads"], c["pointer_wakes"])
        m2 = frac(c["durable_changes"], c["wakes"])
        m3 = frac(c["work_acts"], c["work_wakes"])
        m4 = f"{c['update_state_calls'] / c['wakes']:.2f}" if c["wakes"] else "n/a"
        rows.append(
            f"| {arm} | {model} | {c['sessions']} | {c['wakes']} | {m1} | {m2} | {m3} | {m4} | {c['failed_wakes']} |"
        )
        out[f"{arm}/{model}"] = c
    header = (
        "| arm | model | sessions | wakes | M1 pointer read in-wake | "
        "M2 durable state change | M3 act on work | M4 update_state/wake | failed |\n"
        "|---|---|---|---|---|---|---|---|---|"
    )
    print(header)
    print("\n".join(rows))
    (RUNS / "metrics.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {RUNS / 'metrics.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
