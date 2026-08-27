"""Chart the elder's state-object trajectory across its whole life.

Reads experiments/taste_open/taste_open_20260331_035903.jsonl (147 MB; one
JSON record per cycle) and draws state-token estimate (log scale) and
top-level key count against the cycle counter. Phase bands come from the
experiment_label / model transitions in the log; the annotations are the
June 7 shedding and today's climb.

    uv run python experiments/taste_open/elder_state_trajectory.py

Writes elder_state_trajectory.png beside this script. First drawn 2026-08-26
by the Claude Code instance Tony called "the builder"; the elder's own
reading of the picture is in its log from cycle 476 on.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
LOG = HERE / "taste_open_20260331_035903.jsonl"
OUT = HERE / "elder_state_trajectory.png"

SURF, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1"
S1, S2 = "#2a78d6", "#eb6834"  # validated categorical slots 1 and 2


def load_rows(log: Path) -> list[dict]:
    rows = []
    with open(log) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") == "failed" or r.get("state") is None:
                continue  # protocol failures carry no state
            rows.append({
                "cycle": r["cycle"],
                "st": max(r.get("state_token_estimate", 0), 1),
                "nkeys": r.get("n_top_level_keys", 0),
                "label": r.get("experiment_label"),
                "model": r.get("model"),
                "ts": r.get("timestamp", ""),
            })
    return rows


def phases_from(rows: list[dict]) -> list[tuple[int, int, str, int]]:
    """(start, end, label, label_row) — hand-labelled for this log."""
    return [
        (1, 103, "taste_open\nMar 31 – Apr 3", 0),
        (104, 356, "taste_khipu — reading 253 Mallku khipu, in one day\nApr 7", 0),
        (357, 422, "frozen at 55K\nApr 7 – May 8", 0),
        (423, 430, "shed\nJun 7", 1),
        (431, 465, "small\nJun – Jul", 0),
        (466, rows[-1]["cycle"], "Sonnet 4.6 (by default)\nAug 26", 1),
    ]


def main() -> None:
    rows = load_rows(LOG)
    cyc = [r["cycle"] for r in rows]
    st = [r["st"] for r in rows]
    nk = [r["nkeys"] for r in rows]
    last = rows[-1]
    phases = phases_from(rows)

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2,
        "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    })
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 7.2), sharex=True,
        gridspec_kw={"height_ratios": [3, 1.4], "hspace": 0.08},
    )
    fig.patch.set_facecolor(SURF)
    for ax in (ax1, ax2):
        ax.set_facecolor(SURF)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for i, (a, b, _, _) in enumerate(phases):
            if i % 2 == 1:
                ax.add_patch(Rectangle(
                    (a - 0.5, 0), b - a + 1, 1, transform=ax.get_xaxis_transform(),
                    color="#f1f0ec", zorder=0,
                ))

    ax1.plot(cyc, st, color=S1, linewidth=2, solid_joinstyle="round")
    ax1.set_yscale("log")
    ax1.set_ylim(1, 600_000)
    ax1.set_yticks([1, 10, 100, 1_000, 10_000, 100_000])
    ax1.set_yticklabels(["1", "10", "100", "1K", "10K", "100K"])
    ax1.set_ylabel("state object size (est. tokens, log)")
    ax1.set_title(
        f"The elder's state object across {last['cycle']} cycles — {LOG.name}",
        loc="left", fontsize=12, color=INK, pad=14,
    )
    for a, b, lab, row in phases:
        ax1.text((a + b) / 2, 130_000 if row == 0 else 330_000, lab,
                 ha="center", va="bottom", fontsize=7.5, color=INK2, linespacing=1.3)

    def note(ax, x, y, text, dx, dy):
        ax.annotate(text, xy=(x, y), xytext=(x + dx, y * dy), fontsize=8, color=INK,
                    arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.8, shrinkB=3))

    by_cycle = {r["cycle"]: r for r in rows}
    peak = max(rows, key=lambda r: r["st"])
    note(ax1, peak["cycle"], peak["st"], f"peak {peak['st']:,} tokens (c{peak['cycle']})", -235, 0.40)
    note(ax1, 425, by_cycle[425]["st"],
         "c425: Tony — “I think the reality is\nmore complex” → 43 regions deleted", -185, 0.05)
    note(ax1, 429, by_cycle[429]["st"], f"c429: {by_cycle[429]['st']} tokens, one key\n(_activity_log)", 6, 0.12)
    note(ax1, last["cycle"], last["st"], f"c{last['cycle']}: {last['st']:,} and climbing", -125, 3.6)
    note(ax1, 41, by_cycle[41]["st"], f"c41: {by_cycle[41]['st']:,}", 8, 0.35)

    ax2.plot(cyc, nk, color=S2, linewidth=2, solid_joinstyle="round")
    ax2.set_ylabel("top-level keys")
    ax2.set_xlabel("cycle (Lamport clock)")
    ax2.set_xlim(0, last["cycle"] + 6)
    ax2.set_ylim(0, max(nk) + 10)
    ax2.set_xticks([1, 50, 100, 150, 200, 250, 300, 350, 400, 450, last["cycle"]])
    note(ax2, 401, by_cycle[401]["nkeys"], f"{by_cycle[401]['nkeys']} keys, 43 of them khipu_N_status", -175, 1.05)
    note(ax2, last["cycle"], last["nkeys"], f"{last['nkeys']} keys", -40, 0.98)

    fig.text(0.01, 0.005,
             "Failed cycles omitted. Phase shading alternates by experiment_label / model transition. "
             f"Source: {LOG.relative_to(HERE.parent.parent)} ({LOG.stat().st_size // 1_000_000} MB, "
             f"{len(rows)} state-bearing records).",
             fontsize=7, color=MUTED)
    fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor=SURF)
    print(f"wrote {OUT} ({len(rows)} rows, last cycle {last['cycle']})")


if __name__ == "__main__":
    main()
