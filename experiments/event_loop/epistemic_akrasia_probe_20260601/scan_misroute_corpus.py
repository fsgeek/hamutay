"""Cross-family scan for the 'misrouting' membrane failure (2026-06-03).

Companion to verify_b1_misroute.py. That script proved ONE run (B1, DeepSeek)
misrouted its decision into a `parameter` wrapper. This asks: is misrouting a
DeepSeek quirk, or a real second hole in the response->state membrane that
appears across model families?

Misroute signature in a persisted record's `raw_output`: the dict's keys are a
lone opaque wrapper (`parameter`, `arguments`+`name`, `input`, ...) with NONE of
the real top-level fields the projection/state path expects (`response`,
`strands`, `current_claim`, ...). I.e. the real payload is sealed one level deep
and the durable reader sees nothing.

NOTE (methods, learned the hard way): an earlier ad-hoc version of this scan
printed a 0-based non-empty-line counter but called it a "line number", which
sent a follow-up read to the WRONG record and nearly produced a false "signature
evaporated" conclusion. This version reports the record INDEX (0-based over all
records) and re-opens by that index so the hit is reproducible.

Result on the corpus at write time: 2 hits / 6218 records (~0.03%), two families:
  - DeepSeek (armB_seed1, cycle 2): wrapper key `parameter`, model nested its
    own payload one level deep.
  - Nemotron (taste_open sweep 20260411, cycle 10): keys `{name, arguments}` --
    the raw tool-call envelope leaked into the slot; the harness's unwrap of
    `arguments` did not strip `{name, arguments}`.
Same signature & same consequence (decision lands nowhere durable), but DISTINCT
proximate causes: a model behavior vs a parsing-layer behavior. Misrouting is
cross-family and real, AND it is rare and not monocausal -- both matter.

Usage:
    uv run python experiments/event_loop/epistemic_akrasia_probe_20260601/scan_misroute_corpus.py
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root (…/hamutay)

WRAPPER_KEYS = {
    "parameter", "parameters", "input", "arguments", "args", "kwargs",
    "payload", "data", "body",
}
# A real top-level emit has at least one of these. `name` is excluded on purpose:
# `{name, arguments}` is itself a leaked tool-call envelope, i.e. a misroute.
REAL_FIELDS = {
    "response", "strands", "current_claim", "declared_losses",
    "revision_decision", "instructions_for_next", "open_questions", "state",
}


def scan() -> list[dict]:
    hits: list[dict] = []
    scanned = 0
    for path in glob.glob(str(ROOT / "experiments" / "**" / "*.jsonl"), recursive=True):
        try:
            lines = Path(path).read_text().splitlines()
        except OSError:
            continue
        records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        for idx, d in enumerate(records):
            scanned += 1
            ro = d.get("raw_output")
            if not isinstance(ro, dict):
                continue
            keys = set(ro.keys())
            wrap = keys & WRAPPER_KEYS
            if wrap and not (keys & REAL_FIELDS):
                hits.append({
                    "path": str(Path(path).relative_to(ROOT)),
                    "record_index": idx,  # 0-based over all records in the file
                    "cycle": d.get("cycle"),
                    "wrapper_keys": sorted(wrap),
                    "all_keys": sorted(keys),
                    "model": d.get("model") or "?",
                })
    scan.scanned = scanned  # type: ignore[attr-defined]
    return hits


def main() -> None:
    hits = scan()
    print(f"records scanned : {scan.scanned}")  # type: ignore[attr-defined]
    print(f"misroute hits   : {len(hits)}")
    families = {h["model"] for h in hits}
    print(f"distinct models : {sorted(families)}")
    for h in hits:
        print(
            f"  {h['path']} [idx {h['record_index']}, cycle {h['cycle']}] "
            f"wrap={h['wrapper_keys']} keys={h['all_keys']} model={h['model']}"
        )
    # The finding: misrouting is cross-family (>1 distinct model), not a quirk.
    assert len(families) >= 2, (
        f"expected misrouting in >=2 model families; found {sorted(families)}. "
        "If this fails, the cross-family claim needs re-examination."
    )
    print(f"\nVERIFIED: misrouting appears across {len(families)} model families "
          "-- a real second membrane hole, not a single-model artifact.")
    print("(Rare: ~%.3f%% of records. Same signature, distinct proximate causes -- "
          "see module docstring.)" % (100.0 * len(hits) / scan.scanned))  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
