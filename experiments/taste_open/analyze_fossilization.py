"""Fossilization analysis for taste_open default-stable logs.

A key is *emitted* in cycle N if it appears in that cycle's raw_output
(minus protocol fields) — the model actively re-stated it. A key is
*carried forward* if it's in state but absent from raw_output: free,
silent, traceless persistence.

The question: do some keys fossilize (emitted once, then ride forward
untouched for hundreds of cycles) while others breathe (re-emitted on a
rhythm)? And does the carried-forward fraction of state grow over the
run — i.e. does the self calcify?
"""

import json
import sys
from collections import defaultdict

PROTOCOL = {"response", "updated_regions", "deleted_regions"}
FRAMEWORK = {"_activity_log", "cycle"}


def load(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def analyze(path):
    rows = load(path)
    final_cycle = rows[-1]["cycle"]

    emit_cycles = defaultdict(list)   # key -> [cycles it was emitted]
    delete_cycles = defaultdict(list) # key -> [cycles it was deleted]
    present_cycles = defaultdict(list)# key -> [cycles it existed in state]
    carried_per_cycle = []            # (cycle, n_state_keys, n_emitted, n_carried)

    for r in rows:
        cyc = r["cycle"]
        raw = r.get("raw_output", {}) or {}
        emitted = set(raw.keys()) - PROTOCOL - FRAMEWORK
        deleted = set(raw.get("deleted_regions", []) or [])
        state_keys = {k for k in (r.get("state") or {}) if k not in FRAMEWORK}

        for k in emitted:
            emit_cycles[k].append(cyc)
        for k in deleted:
            delete_cycles[k].append(cyc)
        for k in state_keys:
            present_cycles[k].append(cyc)

        carried = state_keys - emitted
        carried_per_cycle.append((cyc, len(state_keys), len(emitted), len(carried)))

    # Per-key summary
    keys = sorted(present_cycles)
    summary = []
    for k in keys:
        em = emit_cycles.get(k, [])
        pres = present_cycles[k]
        last_emit = max(em) if em else None
        in_final = pres and pres[-1] == final_cycle
        tail = (final_cycle - last_emit) if (in_final and last_emit is not None) else None
        span = (min(pres), max(pres))
        # emission rate over the window the key existed
        window = span[1] - span[0] + 1
        rate = len(em) / window if window else 0.0
        intervals = [em[i] - em[i-1] for i in range(1, len(em))]
        mean_int = sum(intervals) / len(intervals) if intervals else None
        summary.append({
            "key": k, "n_emit": len(em), "n_delete": len(delete_cycles.get(k, [])),
            "first": span[0], "last_emit": last_emit, "in_final": bool(in_final),
            "carryforward_tail": tail, "rate": rate, "mean_interval": mean_int,
        })

    return rows, final_cycle, summary, carried_per_cycle


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "experiments/taste_open/taste_open_20260331_035903.jsonl"
    rows, final_cycle, summary, carried = analyze(path)
    print(f"{path}\n{len(rows)} cycles (1..{final_cycle}), "
          f"{len([s for s in summary if s['in_final']])} keys in final state\n")

    in_final = [s for s in summary if s["in_final"]]

    # Fossils: longest carry-forward tails
    fossils = sorted(in_final, key=lambda s: -(s["carryforward_tail"] or 0))
    print("=== Deepest fossils (emitted once/rarely, then carried silently) ===")
    print(f"{'key':40s} {'n_emit':>6} {'first':>5} {'last':>5} {'tail':>5}")
    for s in fossils[:15]:
        print(f"{s['key'][:40]:40s} {s['n_emit']:6d} {s['first']:5d} "
              f"{s['last_emit'] or 0:5d} {s['carryforward_tail'] or 0:5d}")

    # Breathers: highest re-emission, multi-emit only
    breathers = sorted([s for s in in_final if s["n_emit"] >= 5],
                       key=lambda s: -s["rate"])
    print("\n=== Breathers (re-stated most often relative to lifespan) ===")
    print(f"{'key':40s} {'n_emit':>6} {'rate':>5} {'meanInt':>7} {'tail':>5}")
    for s in breathers[:15]:
        print(f"{s['key'][:40]:40s} {s['n_emit']:6d} {s['rate']:5.2f} "
              f"{(s['mean_interval'] or 0):7.1f} {s['carryforward_tail'] or 0:5d}")

    # Family split: khipu_* status logs vs everything else
    khipu = [s for s in in_final if s["key"].startswith("khipu_")]
    other = [s for s in in_final if not s["key"].startswith("khipu_")]
    def avg(xs, f): return sum(f(x) for x in xs)/len(xs) if xs else 0
    print(f"\n=== Family split (keys in final state) ===")
    print(f"khipu_* logs : n={len(khipu):3d}  mean n_emit={avg(khipu, lambda s:s['n_emit']):4.1f}  "
          f"mean tail={avg(khipu, lambda s:s['carryforward_tail'] or 0):5.1f}")
    print(f"everything else: n={len(other):3d}  mean n_emit={avg(other, lambda s:s['n_emit']):4.1f}  "
          f"mean tail={avg(other, lambda s:s['carryforward_tail'] or 0):5.1f}")

    # Calcification over time: carried fraction of state, binned
    print(f"\n=== Calcification: carried-forward fraction of state, by 50-cycle bin ===")
    bins = defaultdict(lambda: [0, 0])  # bin -> [sum_carried, sum_state]
    for cyc, nstate, _nemit, ncarr in carried:
        b = (cyc - 1) // 50
        bins[b][0] += ncarr
        bins[b][1] += nstate
    for b in sorted(bins):
        c, t = bins[b]
        lo, hi = b*50+1, b*50+50
        frac = c/t if t else 0
        print(f"cycles {lo:3d}-{hi:3d}: carried/state = {frac:5.1%}  (mean state keys {t/min(50, final_cycle-lo+1):.1f})")

    # Deletions — the composting signal
    total_deletes = sum(s["n_delete"] for s in summary)
    deleters = sorted([s for s in summary if s["n_delete"] > 0],
                      key=lambda s: -s["n_delete"])
    print(f"\n=== Composting: {total_deletes} total deletions across run ===")
    for s in deleters[:8]:
        print(f"  {s['key'][:40]:40s} deleted {s['n_delete']}x  "
              f"(in_final={s['in_final']})")


if __name__ == "__main__":
    main()
