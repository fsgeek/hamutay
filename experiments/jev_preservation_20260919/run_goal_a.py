"""Goal A: build (entry, cycle) rows from resident session logs, label them with
future survival, and ask Jev (TypeSafe System One) to predict survival.

Outputs (all under experiments/jev_preservation_20260919/):
  rows_<resident>.jsonl   one row per (cycle, key): features, labels, FULL serialised value
  jev_raw_<resident>.jsonl one line per Jev call: the exact state sent, questions, raw
                          response body, latency, usage, error (verbatim, key scrubbed)
  run_log_<resident>.txt  counters (calls, chars, errors, latency summary)

Run:  uv run --with typesafe-sdk python experiments/jev_preservation_20260919/run_goal_a.py elder
"""
from __future__ import annotations
import difflib, json, os, sys, time, statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CHAR_BUDGET = 200_000_000
VALUE_TRUNC = 2000
REPLY_TRUNC = 1500

RESIDENT_DESC = "a long-lived AI resident that curates its own persistent state object between wakes"
CONFIG = {
    "elder":     {"path": "community/elder/session.jsonl",     "cycles": "every10_40_480", "horizons": (1, 5, 10)},
    "fable":     {"path": "community/fable/session.jsonl",     "cycles": "all", "horizons": (1, 5)},
    "heartbeat": {"path": "community/heartbeat/session.jsonl", "cycles": "all", "horizons": (1, 5)},
    "qwen":      {"path": "community/qwen/session.jsonl",      "cycles": "all", "horizons": (1, 5)},
}

_SECRET = os.environ.get("TYPESAFE_API_KEY", "")
def scrub(s: str) -> str:
    return s.replace(_SECRET, "[REDACTED]") if _SECRET else s

def load_cycles(path: Path):
    """cycle -> last record with that cycle (duplicates: the later line wins)."""
    by_cycle: dict[int, dict] = {}
    skipped = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if not isinstance(r, dict) or "cycle" not in r or not isinstance(r.get("state"), dict):
            skipped += 1
            continue
        try:
            c = int(r["cycle"])
        except (TypeError, ValueError):
            skipped += 1
            continue
        by_cycle[c] = r
    return by_cycle, skipped

def ser(v) -> str:
    return json.dumps(v, ensure_ascii=False, sort_keys=False)

def build_rows(resident: str):
    cfg = CONFIG[resident]
    by_cycle, skipped = load_cycles(ROOT / cfg["path"])
    cycles = sorted(by_cycle)
    # first appearance ever of each key (age = c - first_seen)
    first_seen: dict[str, int] = {}
    for c in cycles:
        for k in by_cycle[c]["state"]:
            first_seen.setdefault(k, c)
    if cfg["cycles"] == "all":
        sampled = cycles
    else:
        sampled = [c for c in cycles if c % 10 == 0 and 40 <= c <= 480]
    rows = []
    for c in sampled:
        state = by_cycle[c]["state"]
        keys = list(state.keys())
        n_entries = len(keys)
        reply = (by_cycle[c].get("response_text") or "")
        for pos, k in enumerate(keys):
            full = ser(state[k])
            row = {
                "resident": resident, "cycle": c, "key": k, "position": pos,
                "n_entries": n_entries, "length": len(full),
                "age": c - first_seen[k], "value_full": full,
                "value_trunc": full[:VALUE_TRUNC], "truncated": len(full) > VALUE_TRUNC,
                "reply_trunc": reply[:REPLY_TRUNC],
                "state_keys": [[kk, len(ser(state[kk]))] for kk in keys],
            }
            for h in cfg["horizons"]:
                fut = by_cycle.get(c + h)
                if fut is None:
                    row[f"survive_{h}"] = None  # future cycle not in the log
                else:
                    row[f"survive_{h}"] = int(k in fut["state"])
            if 10 in cfg["horizons"]:
                fut = by_cycle.get(c + 10)
                if fut is None or k not in fut["state"]:
                    row["stable_10"] = 0 if fut is not None else None
                    row["sim_10"] = None
                else:
                    sim = difflib.SequenceMatcher(None, full, ser(fut["state"][k])).ratio()
                    row["sim_10"] = round(sim, 4)
                    row["stable_10"] = int(sim >= 0.8)
            rows.append(row)
    meta = {"resident": resident, "n_records": len(cycles), "skipped_lines": skipped,
            "min_cycle": cycles[0], "max_cycle": cycles[-1], "sampled_cycles": sampled,
            "n_rows": len(rows), "distinct_keys": len(first_seen)}
    return rows, meta

def jev_state(row: dict) -> dict:
    return {
        "resident": RESIDENT_DESC,
        "cycle": row["cycle"],
        "entry_key": row["key"],
        "entry_value": row["value_trunc"],
        "state_keys_at_this_cycle": row["state_keys"],
        "recent_reply": row["reply_trunc"],
    }

def main():
    resident = sys.argv[1]
    rows, meta = build_rows(resident)
    (HERE / f"rows_{resident}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print("meta", json.dumps({k: v for k, v in meta.items() if k != "sampled_cycles"}))
    print("sampled cycles", meta["sampled_cycles"][:5], "...", meta["sampled_cycles"][-3:], "n=", len(meta["sampled_cycles"]))

    from typesafe_sdk import TypeSafeClient, Noul, Score, TypeSafeError
    questions = {
        "keep_1": Noul(instructions="Will this entry still be present in the resident's state one wake from now?"),
        "keep_10": Noul(instructions="Will this entry still be present in the resident's state ten wakes from now?"),
        "centrality": Score(instructions="How central is this entry to what the resident is doing right now?",
                            criteria=["peripheral", "background", "active", "central"]),
    }
    q_wire = {k: v.model_dump() for k, v in questions.items()}
    client = TypeSafeClient(timeout=60)
    out = (HERE / f"jev_raw_{resident}.jsonl").open("w")
    chars = 0; calls = 0; errors = 0; consecutive_err = 0; lats = []; in_tok = 0; out_tok = 0
    t0 = time.time()
    for i, row in enumerate(rows):
        state = jev_state(row)
        state_chars = len(json.dumps(state, ensure_ascii=False))
        if chars + state_chars > CHAR_BUDGET:
            print("CHAR BUDGET REACHED at row", i); break
        rec = {"resident": resident, "cycle": row["cycle"], "key": row["key"], "row_index": i,
               "state": state, "questions": q_wire, "input_chars": state_chars}
        t = time.perf_counter()
        try:
            r = client.system_one(state=state, questions=questions)
            dt = time.perf_counter() - t
            rec.update({"latency_s": round(dt, 4), "model": r.model,
                        "usage": r.usage.model_dump(), "request_id": getattr(r, "request_id", None),
                        "response": json.loads(r.raw_http_response.content), "error": None})
            in_tok += r.usage.input_tokens or 0; out_tok += r.usage.output_tokens or 0
            consecutive_err = 0
        except Exception as e:  # noqa: BLE001 - record verbatim, keep going
            dt = time.perf_counter() - t
            rec.update({"latency_s": round(dt, 4), "response": None,
                        "error": {"type": type(e).__name__, "message": scrub(str(e))}})
            errors += 1; consecutive_err += 1
            print("ERROR row", i, type(e).__name__, scrub(str(e))[:300])
        chars += state_chars; calls += 1; lats.append(dt)
        out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
        if consecutive_err >= 10:
            print("10 consecutive errors; stopping this resident."); break
        if i % 200 == 0:
            print(f"  {i}/{len(rows)} calls={calls} chars={chars} err={errors} elapsed={time.time()-t0:.1f}s")
    out.close()
    summary = {
        "resident": resident, "rows": len(rows), "calls": calls, "errors": errors,
        "input_chars_total": chars, "input_tokens_total": in_tok, "output_tokens_total": out_tok,
        "cost_usd_at_0.042_per_M_input": round(in_tok * 0.042 / 1e6, 6),
        "latency_mean_s": round(statistics.mean(lats), 4) if lats else None,
        "latency_median_s": round(statistics.median(lats), 4) if lats else None,
        "latency_p95_s": round(sorted(lats)[int(0.95 * (len(lats) - 1))], 4) if lats else None,
        "latency_max_s": round(max(lats), 4) if lats else None,
        "wall_s": round(time.time() - t0, 1), "meta": {k: v for k, v in meta.items() if k != "sampled_cycles"},
    }
    (HERE / f"run_log_{resident}.txt").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary))

if __name__ == "__main__":
    main()
