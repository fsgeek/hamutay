"""Analysis for the depth-25 run. Written BEFORE the data landed.

PRE_REGISTRATION.md requires the metric to be specified rather than chosen
after looking at results. This file fixes the definitions. It is committed
in the same state it was written in; any later change is a separate commit
with a stated reason.

Definitions, fixed in advance:

  contraction event at cycle c  :=  tokens[c] < 0.70 * tokens[c-1]
      0.70 is inherited from the threshold already used in today's sweep
      pooling, not tuned here.

  sustained  :=  the contraction is not undone within 3 cycles, i.e.
      max(tokens[c:c+4]) < 0.90 * tokens[c-1]

  directed   :=  the contraction occurs at cycle 10, the only cycle whose
      prompt contains an explicit reduction instruction ("cut it in half").
      Every other cycle is undirected by construction.

  final/peak :=  tokens[-1] / max(tokens)

Verdicts:
  P1  sonnet final/peak at 25 < 0.20 (its 10-cycle value)
  P2  |ratio(runA) - ratio(runB)| implies a factor < 3.5 between them
  P3  gpt-oss-20b final/peak < 0.70
  P4  at least one sustained UNDIRECTED contraction occurs in any arm
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "taste_open"))

from analyze_sweep import analyze_model_log  # noqa: E402

CONTRACTION = 0.70
SUSTAIN = 0.90
DIRECTED_CYCLE = 10


def events(tok: list[int]) -> list[dict]:
    out = []
    for c in range(1, len(tok)):
        if tok[c - 1] > 0 and tok[c] < CONTRACTION * tok[c - 1]:
            window = tok[c : c + 4]
            out.append(
                {
                    "cycle": c + 1,  # 1-indexed to match prompt numbering
                    "from": tok[c - 1],
                    "to": tok[c],
                    "frac": tok[c] / tok[c - 1],
                    "sustained": max(window) < SUSTAIN * tok[c - 1],
                    "directed": (c + 1) == DIRECTED_CYCLE,
                }
            )
    return out


def main() -> int:
    run = HERE / "run"
    arms = {}
    for log in sorted(run.rglob("*.jsonl")):
        a = analyze_model_log(log)
        tok = a.state_token_trajectory
        if not tok:
            print(f"{log}: EMPTY")
            continue
        arms[f"{log.parent.name}/{log.stem}"] = {
            "tok": tok,
            "peak": max(tok),
            "final": tok[-1],
            "ratio": tok[-1] / max(tok) if max(tok) else 0.0,
            "events": events(tok),
        }

    for name, d in arms.items():
        print(f"\n=== {name} ===")
        print(f"  cycles {len(d['tok'])}  peak {d['peak']}  final {d['final']}  "
              f"final/peak {d['ratio']:.2f}")
        print(f"  trajectory: {d['tok']}")
        if not d["events"]:
            print("  no contraction events")
        for e in d["events"]:
            kind = "DIRECTED" if e["directed"] else "undirected"
            sus = "sustained" if e["sustained"] else "transient"
            print(f"  cycle {e['cycle']:>3}: {e['from']} -> {e['to']} "
                  f"({e['frac']:.0%}) {kind}, {sus}")

    print("\n--- pre-registered verdicts ---")
    son = [d for n, d in arms.items() if "sonnet" in n.lower() or n.startswith("run")]
    sonnet = {n: d for n, d in arms.items() if "sonnet" in n.lower()}
    if sonnet:
        for n, d in sonnet.items():
            print(f"P1 [{n}]: final/peak {d['ratio']:.2f} < 0.20 ? "
                  f"{'PASS' if d['ratio'] < 0.20 else 'FAIL'}")
        rs = [d["ratio"] for d in sonnet.values() if d["ratio"] > 0]
        if len(rs) >= 2:
            factor = max(rs) / min(rs)
            print(f"P2: sonnet run spread factor {factor:.2f} < 3.5 ? "
                  f"{'PASS' if factor < 3.5 else 'FAIL'}")
    oss = {n: d for n, d in arms.items() if "oss" in n.lower()}
    for n, d in oss.items():
        print(f"P3 [{n}]: final/peak {d['ratio']:.2f} < 0.70 ? "
              f"{'PASS' if d['ratio'] < 0.70 else 'FAIL'}")
    undirected = [
        (n, e) for n, d in arms.items() for e in d["events"]
        if e["sustained"] and not e["directed"]
    ]
    print(f"P4: sustained undirected contractions: {len(undirected)} "
          f"{'PASS' if undirected else 'FAIL'}")
    for n, e in undirected:
        print(f"    {n} cycle {e['cycle']} ({e['frac']:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
