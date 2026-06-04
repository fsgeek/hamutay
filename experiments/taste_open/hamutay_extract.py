#!/usr/bin/env python3
"""
hamutay_extract.py - structural audit pass over taste_open JSONL run logs.

Streams each file line-by-line (never loads a whole file into memory), pulls the
per-cycle scalar/structural fields, writes a compact <file>.cycles.csv, and
prints a report whose numbers line up with the specific claims in the blog draft
so each can be marked supported / qualify / cut.

Stdlib only. Reads only; the CSVs it writes are small (one row per cycle).

Usage:
    python3 hamutay_extract.py taste_open_20260331_035903.jsonl
    python3 hamutay_extract.py *.jsonl

Treats the record's `state` object as the tensor and its top-level keys
(reported by the harness as `top_level_keys` / `n_top_level_keys`) as the
"strands". Falls back to computing strand keys from `state` directly if needed.
"""
import sys, json, csv, statistics as st
from glob import glob

def strands_of(rec):
    """Return the set of strand names for a cycle."""
    tlk = rec.get("top_level_keys")
    if isinstance(tlk, list) and tlk:
        return set(tlk)
    state = rec.get("state")
    if isinstance(state, dict):
        return set(k for k in state.keys() if k != "cycle")
    return set()

def cv(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = st.mean(xs)
    return (st.pstdev(xs) / m) if m else None

def process(path):
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            usage = r.get("usage") or {}
            strands = strands_of(r)
            rows.append({
                "cycle": r.get("cycle"),
                "model": r.get("model"),
                "n_strands": r.get("n_top_level_keys") if isinstance(r.get("n_top_level_keys"), int) else len(strands),
                "state_tokens": r.get("state_token_estimate"),
                "sys_tokens": r.get("system_prompt_tokens"),
                "in_tok": usage.get("input_tokens"),
                "out_tok": usage.get("output_tokens"),
                "stop_reason": usage.get("stop_reason"),
                "n_updated": len(r.get("updated_regions") or []),
                "n_deleted": len(r.get("deleted_regions") or []),
                "resp_len": len(r.get("response_text") or ""),
                "_strands": strands,
            })
    rows.sort(key=lambda x: (x["cycle"] if isinstance(x["cycle"], int) else 0))

    # write compact csv (drop the set column)
    out = path + ".cycles.csv"
    cols = ["cycle","model","n_strands","state_tokens","sys_tokens","in_tok","out_tok","stop_reason","n_updated","n_deleted","resp_len"]
    with open(out, "w", newline="", encoding="utf-8") as g:
        w = csv.DictWriter(g, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    n = len(rows)
    ncounts = [r["n_strands"] for r in rows if isinstance(r["n_strands"], int)]
    toks = [r["state_tokens"] for r in rows if isinstance(r["state_tokens"], int)]
    stops = {}
    for r in rows:
        stops[r["stop_reason"]] = stops.get(r["stop_reason"], 0) + 1

    # strand stability: consecutive Jaccard + survival (frac of prev strands kept)
    jac, surv, dropped, added = [], [], [], []
    name_cycles = {}  # strand name -> set of cycles seen
    for r in rows:
        for s in r["_strands"]:
            name_cycles.setdefault(s, set()).add(r["cycle"])
    for a, b in zip(rows, rows[1:]):
        A, B = a["_strands"], b["_strands"]
        if A or B:
            jac.append(len(A & B) / len(A | B) if (A | B) else 1.0)
        if A:
            surv.append(len(A & B) / len(A))
        dropped.append(len(A - B))   # strands present last cycle, gone this cycle (shed signal)
        added.append(len(B - A))

    # name-level transience: fraction of distinct strand names appearing in exactly one cycle
    distinct = len(name_cycles)
    once = sum(1 for s, cs in name_cycles.items() if len(cs) == 1)
    transience = (once / distinct) if distinct else None

    # breathing: treat a cycle as a "shed" when strands dropped >= max(2, 0.5*prev_count)
    shed_cycles = []
    for i, r in enumerate(rows[1:], start=1):
        prev = rows[i-1]["n_strands"] or 0
        d = dropped[i-1]
        if d >= max(2, 0.5 * prev) and d > 0:
            shed_cycles.append(r["cycle"])
    intervals = [b - a for a, b in zip(shed_cycles, shed_cycles[1:])]

    def stat(xs):
        xs = [x for x in xs if x is not None]
        if not xs:
            return "n/a"
        return f"min={min(xs)} max={max(xs)} mean={st.mean(xs):.2f} median={st.median(xs)}"

    print("=" * 70)
    print(f"FILE: {path}")
    print(f"cycles: {n} | model(s): {sorted(set(r['model'] for r in rows))}")
    print(f"-> wrote {out}")
    print("-" * 70)
    print(f"[strand count]  {stat(ncounts)}")
    print(f"   distribution: {dict(sorted({c: ncounts.count(c) for c in set(ncounts)}.items()))}")
    print(f"   (blog: 'curation richness stochastic, 3 to 49 strands')")
    print(f"[strand stability] consecutive Jaccard mean={st.mean(jac):.3f}  survival mean={st.mean(surv):.3f}  (n={len(jac)})")
    print(f"   (blog: 'strand stability 9%' -> compare to survival mean above)")
    print(f"[strand-name transience] {transience:.3f} of {distinct} distinct names appear in exactly ONE cycle")
    print(f"   (blog: 'concept transience 87%' -- this is a NAME-level proxy; true claim is content-level)")
    print(f"[state token size] {stat(toks)}")
    print(f"   count >= 4090: {sum(1 for t in toks if t >= 4090)} | >= 15000: {sum(1 for t in toks if t >= 15000)}")
    print(f"   (blog: '4096 ceiling was a config bug; real tensors run to 15000')")
    print(f"[stop_reason] {stops}")
    print(f"   (blog: silent truncation -> look for 'max_tokens' here)")
    print(f"[breathing/shed] shed cycles n={len(shed_cycles)} | intervals n={len(intervals)} "
          f"mean={st.mean(intervals):.2f} CV={cv(intervals):.3f}" if intervals else
          f"[breathing/shed] shed cycles n={len(shed_cycles)} | too few intervals to test")
    print(f"   (blog: 'aperiodic, CV=0.87, Poisson-like' -> compare CV above; CV~1 => Poisson-like)")
    print(f"[mature strands] last cycle ({rows[-1]['cycle']}) keys:")
    print(f"   {sorted(rows[-1]['_strands'])}")
    print(f"   (use these to locate the loss-changelog & metacognition strands for the content pass)")

def main():
    args = sys.argv[1:]
    paths = []
    for a in args:
        paths.extend(glob(a))
    if not paths:
        print("usage: python3 hamutay_extract.py <file.jsonl> [more.jsonl ...]")
        return
    for p in sorted(set(paths)):
        try:
            process(p)
        except Exception as e:
            print(f"!! {p}: {type(e).__name__}: {e}")

if __name__ == "__main__":
    main()
