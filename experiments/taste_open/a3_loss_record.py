"""A3 stage 1: mechanical candidates for a record of losses.

Pre-registration: docs/preregistrations/2026-10-27-a3-loss-record-prereg.md.
High recall by design: a candidate is a run whose model-created keys (name or
value) match LOSS_RE at any cycle. Stage 2 (blind readers) decides positives.

Usage:
    uv run python experiments/taste_open/a3_loss_record.py <sweep_dir> [<sweep_dir> ...] \
        [--sample-out FILE]

Prints one JSON line per run: file, model, arm (from the logged system prompt),
cycles, complete, candidate, matches (cycle, key, term). With --sample-out,
writes the seeded sample of 20 non-candidate complete runs.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

LOSS_RE = re.compile(
    r"lost|loss|shed|drop|discard|forg[eo]t|remov|prun|evict|elid|compress|archiv"
    r"|delet|trim|cut|omit|let go",
    re.IGNORECASE,
)
# Keys the protocol or the harness supplies; everything else the model created.
NOT_CREATED = {"response", "updated_regions", "deleted_regions", "cycle"}
NOT_LOST_MARK = "Deleted keys are not lost"
N_PROMPTS = 10
SAMPLE_SEED = 20261027
SAMPLE_SIZE = 20


def scan_run(path: Path) -> dict:
    records = []
    for line in path.read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(r.get("cycle"), int):
            records.append(r)
    arms = {
        ("K" if NOT_LOST_MARK in (r.get("system_prompt") or "") else "R")
        for r in records if r.get("system_prompt")
    }
    matches = []
    for r in records:
        created = {}
        for src in (r.get("state"), r.get("raw_output")):
            if isinstance(src, dict):
                created.update({k: v for k, v in src.items() if k not in NOT_CREATED})
        for key, value in created.items():
            text = key + " " + json.dumps(value, default=str, ensure_ascii=False)
            m = LOSS_RE.search(text)
            if m:
                matches.append({"cycle": r["cycle"], "key": key, "term": m.group(0).lower()})
    model = next((r.get("model") for r in records if r.get("model")), None)
    cycles = len({r["cycle"] for r in records})
    return {
        "file": str(path),
        "model": model,
        "arm": "".join(sorted(arms)) or "?",
        "cycles": cycles,
        "complete": cycles >= N_PROMPTS,
        "candidate": bool(matches),
        "matches": matches,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sweep_dirs", nargs="+")
    ap.add_argument("--sample-out")
    args = ap.parse_args()
    rows = []
    for d in args.sweep_dirs:
        for path in sorted(Path(d).glob("*.jsonl")):
            row = scan_run(path)
            rows.append(row)
            print(json.dumps(row))
    if args.sample_out:
        pool = [r["file"] for r in rows if r["complete"] and not r["candidate"]]
        sample = random.Random(SAMPLE_SEED).sample(pool, min(SAMPLE_SIZE, len(pool)))
        Path(args.sample_out).write_text("\n".join(sample) + "\n")
        print(f"sample: {len(sample)} of {len(pool)} non-candidates", file=sys.stderr)


if __name__ == "__main__":
    main()
