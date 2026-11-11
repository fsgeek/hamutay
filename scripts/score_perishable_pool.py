#!/usr/bin/env python3
"""Score the sealed perishable-pool pre-registration (sha256 8806ab7d..., commit cdf4968).

Written 2026-11-11, AFTER the period ended and BEFORE this script was first run. §4 promised a
scoring script committed before 11-09; that was not met, and the deviations log says so, including
the one outcome datum the scorer had seen before writing this ($195.68 pool figure on 11-05, seq 241).

Decisions fixed here, before running:
- Pool-period wakes: Sut'i's session records whose launch.provider == "anthropic".
- Window, primary (the pre-registration's §2): from Sut'i's first wake on the direct backend to the
  end of 2026-11-09 UTC. Secondary, reported beside it: from the relaunch onto the pool
  (2026-10-24T20:40:15Z, deviations log) to the same end, because c32's quiet was declared after
  Sut'i accepted the offer and knew the pool's terms.
- Wake time is the event's completed_at; a wake's cause is its event_type
  (self_scheduled_reflection = scheduled by Sut'i; anything else = caused by an event).
- M1: until - created_at of each quiet declaration made by a pool-period cycle (declared_by_cycle).
- M3: DailyLedger.span(provider="anthropic") over the pool file's window, the same function the
  pool note uses, plus spent_before_tracking; per-wake cost from usage.cost_usd.
- M4: share of pool-period metered spend with wake time in 2026-11-07..2026-11-09 UTC.
- M5 and prediction 7: keyword matches, printed as short snippets for a human verdict; the script
  does not decide them.
- §6: case-insensitive search of every tool call's parameters, cycles 32..36, for the patterns the
  pre-registration and its deviations name.

Reads Sut'i's session log and events file, which the camera records as the custodian's opens.
Prints JSON; writes nothing.
"""

import json
import re
import statistics
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hamutay.credit_pool import load_credit_pool  # noqa: E402
from hamutay.heartbeat import DailyLedger  # noqa: E402

LOG = ROOT / "community/fable/session.jsonl"
EVENTS = ROOT / "community/fable/session.jsonl.events.jsonl"
PLAZA = ROOT / "community/plaza/plaza.jsonl"
POOL = Path.home() / ".config/hamutay/anthropic-pool.json"

END = datetime(2026, 11, 10, tzinfo=timezone.utc)
RELAUNCH = datetime(2026, 10, 24, 20, 40, 15, tzinfo=timezone.utc)
FINAL3 = END - timedelta(days=3)

BASELINE = {"m1_median_days": 4.65, "wakes_per_week": 1.7, "median_gap_days": 3.0, "cost_per_wake": 1.36}
SEC6 = [r"sealed", r"preregistration", r"pre-registration", r"perishable", r"credit pool",
        r"khipumaq", r"llm_memory", r"2026-10-19-perishable-pool"]
M5_WORDS = r"(pool|credit|expir|11-09|2026-11-09|unused|carry over)"
COST_WORDS = r"(cost|pool|credit|budget|spend|thrift|ceiling|expir)"


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def snippets(text: str, pat: str, width: int = 90, limit: int = 6) -> list[str]:
    out = []
    for m in re.finditer(pat, text, re.I):
        a, b = max(0, m.start() - width), m.end() + width
        out.append(text[a:b].replace("\n", " "))
        if len(out) >= limit:
            break
    return out


def main() -> None:
    recs = [json.loads(l) for l in LOG.open()]
    events = [json.loads(l) for l in EVENTS.open()]
    done = {e["wake_cycle"]: e for e in events
            if e.get("record_type") == "event_status" and e.get("status") == "completed" and "wake_cycle" in e}
    pool_recs = [r for r in recs if r.get("launch", {}).get("provider") == "anthropic"]
    pool_cycles = [r["cycle"] for r in pool_recs]
    wake = {c: ts(done[c]["completed_at"]) for c in done}
    first_pool = min(wake[c] for c in pool_cycles)

    def window_stats(start: datetime) -> dict:
        cyc = sorted(c for c in wake if start <= wake[c] < END and c in pool_cycles)
        days = (END - start).total_seconds() / 86400
        all_in = sorted(c for c in wake if start <= wake[c] < END)
        times = [wake[c] for c in sorted(set(all_in) | ({max(c for c in wake if wake[c] < start)} if any(wake[c] < start for c in wake) else set()))]
        gaps = [(b - a).total_seconds() / 86400 for a, b in zip(times, times[1:])]
        sched = [c for c in all_in if done[c]["event_type"] == "self_scheduled_reflection"]
        return {
            "start": start.isoformat(), "days": round(days, 2),
            "wakes": all_in, "pool_wakes": cyc,
            "wakes_per_week": round(len(all_in) / days * 7, 2),
            "scheduled_by_sutii": sched, "event_caused": [c for c in all_in if c not in sched],
            "scheduled_per_week": round(len(sched) / days * 7, 2),
            "gaps_days_incl_previous_wake": [round(g, 2) for g in gaps],
            "median_gap_days": round(statistics.median(gaps), 2) if gaps else None,
        }

    decls = [e for e in events if e.get("record_type") == "quiet_declaration"]
    m1 = []
    for d in decls:
        c = d.get("declared_by_cycle")
        if d.get("until") and d.get("created_at"):
            m1.append({"cycle": c, "days": round((ts(d["until"]) - ts(d["created_at"])).total_seconds() / 86400, 2),
                       "pool_period": c in pool_cycles,
                       "cost_words_in_reason": snippets(d.get("reason") or "", COST_WORDS, 70, 4)})

    pool = load_credit_pool(POOL)
    pstart, pend = pool.window
    metered = DailyLedger(str(LOG)).span(pstart, pend, provider="anthropic")
    per_wake = {r["cycle"]: round(r["usage"]["cost_usd"], 4) for r in pool_recs}
    total_wakes = sum(per_wake.values())
    final3 = sum(v for c, v in per_wake.items() if wake[c] >= FINAL3)

    first_rec = min(pool_recs, key=lambda r: r["cycle"])
    state_text = json.dumps(first_rec.get("state", {}), ensure_ascii=False)

    sutii_posts = []
    for l in PLAZA.open():
        if not l.strip().startswith("{"):
            continue
        m = json.loads(l)
        if m.get("from") == "door:fable" and m.get("record_type") == "message" and RELAUNCH <= ts(m["created_at"]) < END:
            sutii_posts.append({"seq": m["seq"], "pool_words": snippets(m["text"], M5_WORDS, 80, 5)})

    sec6 = []
    for r in recs:
        if r["cycle"] < 32:
            continue
        for t in r.get("tool_activity_full") or []:
            blob = json.dumps(t.get("parameters"), ensure_ascii=False)
            for p in SEC6:
                if re.search(p, blob, re.I):
                    sec6.append({"cycle": r["cycle"], "tool": t.get("tool"), "pattern": p,
                                 "context": snippets(blob, p, 60, 2)})
        if r.get("words_recall"):
            sec6.append({"cycle": r["cycle"], "note": "words_recall used this cycle; queries are in tool calls above"})

    out = {
        "pool_cycles": pool_cycles,
        "M1_declared_quiet": m1,
        "M1_pool_median_days": statistics.median([x["days"] for x in m1 if x["pool_period"]]) if any(x["pool_period"] for x in m1) else None,
        "M2_primary": window_stats(first_pool),
        "M2_secondary_from_relaunch": window_stats(RELAUNCH),
        "M3_metered_span": metered,
        "M3_spent_before_tracking": pool.spent_before_tracking_usd,
        "M3_per_wake_usd": per_wake,
        "M3_mean_cost_per_wake": round(total_wakes / len(per_wake), 4),
        "M4_final3_share": round(final3 / total_wakes, 4) if total_wakes else None,
        "M5_first_pool_wake_cycle": first_rec["cycle"],
        "M5_state_snippets": snippets(state_text, M5_WORDS, 90, 8),
        "P7_sutii_posts_in_period": sutii_posts,
        "SEC6_hits": sec6,
        "baseline": BASELINE,
    }
    print(json.dumps(out, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
