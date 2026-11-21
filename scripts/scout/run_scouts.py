"""Send tourist scouts over a rendered territory (public texts only).

Spec: docs/superpowers/specs/2026-10-02-neutrality-scout-design.md.
Deviation from the spec, recorded: the spec says "reuse chasqui". chasqui's
external-scope prompt frames the target "from the perspective of the Yanantin
project" and asks how it "could inform the Yanantin project" -- a directed lens
the tourist brief exists to avoid -- and it writes into yanantin's cairn. This
script keeps the spec's design (cost-weighted varied families, drawn
temperature, max_tokens at the model's maximum, finish reason recorded, quote
check, every report kept) without chasqui's prompt or cairn.

    set -a; . ~/.config/hamutay/heartbeat.env; set +a
    uv run python scripts/scout/run_scouts.py experiments/scout/territory/<id> --n 6 --budget 1.00
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "experiments" / "scout" / "reports"
API = "https://openrouter.ai/api/v1"

BRIEF = """\
You're a tourist. Below are some texts. Look around, make notes, tell us what \
you explored, and tell us what you didn't explore but thought a future scout \
might.

You are not a grader or a reviewer. Nobody is asking you to approve or reject \
anything. Say plainly what you noticed: what caught your eye, what seemed odd, \
what seemed missing, what you liked, what you didn't.

How to write your notes:
- Short sentences. One statement per sentence.
- Every observation quotes the text it is about, in double quotes, exactly as \
written, and names the file. A note with no quote is a feeling, not an \
observation; label it so.
- Say what you know, what you are guessing, and what you made up.

End with two sections:
## What I explored
## What I didn't explore but a future scout might
"""


def get(path: str, key: str) -> dict:
    req = urllib.request.Request(f"{API}{path}", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def post(path: str, key: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API}{path}", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "X-Title": "hamutay:scout"},
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def candidates(models: list[dict], need_ctx: int) -> list[dict]:
    out = []
    for m in models:
        p = m.get("pricing") or {}
        try:
            pin, pout = float(p.get("prompt", "x")), float(p.get("completion", "x"))
        except ValueError:
            continue
        arch = m.get("architecture") or {}
        if "text" not in (arch.get("output_modalities") or ["text"]):
            continue
        if (m.get("context_length") or 0) < need_ctx:
            continue
        # Paid, and bounded so one scout can't eat the budget: <= $3/M in, <= $12/M out.
        if not (0 < pin <= 3e-6 and 0 < pout <= 12e-6):
            continue
        # :batch ids 404 on chat completions (run 20261120T184502Z); :free ones are rate-limited.
        if ":free" in m["id"] or ":batch" in m["id"] or "image" in m["id"]:
            continue
        m["_pin"], m["_pout"] = pin, pout
        out.append(m)
    return out


def pick(cands: list[dict], n: int, rng: random.Random) -> list[dict]:
    """Cost-weighted (1/sqrt price) random choice, at most one model per family (vendor prefix)."""
    chosen, families = [], set()
    pool = list(cands)
    while pool and len(chosen) < n:
        w = [1 / math.sqrt(m["_pin"] + m["_pout"]) for m in pool]
        m = rng.choices(pool, weights=w, k=1)[0]
        fam = m["id"].split("/")[0]
        pool = [x for x in pool if x["id"].split("/")[0] != fam]
        chosen.append(m)
        families.add(fam)
    return chosen


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_check(report: str, territory_text: str) -> dict:
    quotes = [q for q in re.findall(r'"([^"\n]{12,400})"', report)]
    hay = norm(territory_text.replace('\\"', '"'))
    found = [q for q in quotes if norm(q) in hay]
    missing = [q for q in quotes if norm(q) not in hay]
    return {"quotes": len(quotes), "found": len(found), "not_in_territory": missing}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("territory")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--budget", type=float, default=1.00)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--brief", default=None, help="file holding an alternative brief")
    a = ap.parse_args()

    brief = Path(a.brief).read_text() if a.brief else BRIEF
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY not set")
    terr = Path(a.territory)
    files = sorted(p for p in terr.iterdir() if p.is_file())
    corpus = "\n\n".join(f"===== FILE: {p.name} =====\n{p.read_text()}" for p in files)
    need_ctx = max(64_000, len(corpus) // 3 + 20_000)

    seed = a.seed if a.seed is not None else random.SystemRandom().randrange(2**32)
    rng = random.Random(seed)
    models = get("/models", key)["data"]
    chosen = pick(candidates(models, need_ctx), a.n, rng)
    REPORTS.mkdir(parents=True, exist_ok=True)
    spent = 0.0
    run = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for m in chosen:
        if spent >= a.budget:
            print(f"budget reached ({spent:.4f} >= {a.budget}); stopping", file=sys.stderr)
            break
        temp = round(rng.uniform(0.3, 1.3), 3)
        max_out = (m.get("top_provider") or {}).get("max_completion_tokens") or 16000
        body = {
            "model": m["id"], "temperature": temp, "max_tokens": max_out,
            "messages": [{"role": "user", "content": brief + "\n\n" + corpus}],
            "usage": {"include": True},
        }
        meta = {"run": run, "seed": seed, "model": m["id"], "temperature": temp,
                "max_tokens": max_out, "territory": terr.name,
                "brief": a.brief or "default"}
        try:
            r = post("/chat/completions", key, body)
            ch = r["choices"][0]
            text = ch["message"].get("content") or ""
            meta.update(finish_reason=ch.get("finish_reason"), usage=r.get("usage"))
            cost = float((r.get("usage") or {}).get("cost") or 0.0)
        except Exception as e:  # keep the failure as a report too
            text, cost = "", 0.0
            meta.update(error=repr(e))
        spent += cost
        meta["cost_usd"] = cost
        meta["quote_check"] = quote_check(text, corpus)
        safe = m["id"].replace("/", "__").replace(":", "_")
        out = REPORTS / f"{run}-{safe}.md"
        out.write_text("```json\n" + json.dumps(meta, indent=2) + "\n```\n\n" + text + "\n")
        qc = meta["quote_check"]
        print(f"{m['id']:50s} t={temp} finish={meta.get('finish_reason')} "
              f"cost=${cost:.4f} quotes {qc['found']}/{qc['quotes']} -> {out.relative_to(ROOT)}")
    print(f"seed={seed} spent=${spent:.4f}")


if __name__ == "__main__":
    main()
