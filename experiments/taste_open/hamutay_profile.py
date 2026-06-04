#!/usr/bin/env python3
"""
hamutay_profile.py - schema profiler for taste_open JSONL run logs.

Purpose: show the STRUCTURE of the records (keys, types, nesting) without
dumping content, so an extractor can be written against the real schema.
Stdlib only. Streams; never loads the whole file into memory.

Usage:
    python3 hamutay_profile.py taste_open_20260331_035903.jsonl
    python3 hamutay_profile.py FILE --sample 8 --preview 100

Paste the output back. Nothing here writes or sends anything.
"""
import sys, json, argparse

def short(v, n):
    s = v if isinstance(v, str) else repr(v)
    s = s.replace("\n", "\\n")
    return s if len(s) <= n else s[:n] + "…(+%d)" % (len(s) - n)

def outline(obj, preview, indent=0, maxlist=1):
    pad = "  " * indent
    if isinstance(obj, dict):
        for k, v in obj.items():
            t = type(v).__name__
            if isinstance(v, dict):
                print(f"{pad}{k}: dict({len(v)} keys)")
                outline(v, preview, indent + 1, maxlist)
            elif isinstance(v, list):
                et = type(v[0]).__name__ if v else "empty"
                print(f"{pad}{k}: list(len={len(v)}, elem={et})")
                if v and isinstance(v[0], (dict, list)):
                    outline(v[0], preview, indent + 1, maxlist)
                elif v:
                    print(f"{pad}  e.g. {short(v[0], preview)}")
            else:
                print(f"{pad}{k}: {t} = {short(v, preview)}")
    elif isinstance(obj, list):
        et = type(obj[0]).__name__ if obj else "empty"
        print(f"{pad}list(len={len(obj)}, elem={et})")
        if obj and isinstance(obj[0], (dict, list)):
            outline(obj[0], preview, indent + 1, maxlist)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--sample", type=int, default=6, help="records to scan for key presence")
    ap.add_argument("--preview", type=int, default=90, help="max chars per scalar preview")
    a = ap.parse_args()

    total = 0
    key_counts = {}
    first = None
    scanned = 0
    with open(a.path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            if scanned < a.sample:
                try:
                    rec = json.loads(line)
                except Exception as e:
                    print(f"[line {total}] JSON parse error: {e}")
                    continue
                if first is None:
                    first = rec
                if isinstance(rec, dict):
                    for k in rec.keys():
                        key_counts[k] = key_counts.get(k, 0) + 1
                scanned += 1

    print("=" * 60)
    print(f"FILE: {a.path}")
    print(f"records (lines): {total}")
    print(f"scanned for key presence: {scanned}")
    print("=" * 60)
    print("TOP-LEVEL KEY PRESENCE (key: seen in N of %d sampled):" % scanned)
    for k, c in sorted(key_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {c}")
    print("-" * 60)
    print("STRUCTURE OF FIRST RECORD (types + short previews):")
    if first is not None:
        outline(first, a.preview)
    print("=" * 60)
    print("If any field looks like the tensor/summary, run again pointed at it,")
    print("or tell me which key holds: strands, open questions, declared losses,")
    print("metacognition/self-state, and token counts.")

if __name__ == "__main__":
    main()
