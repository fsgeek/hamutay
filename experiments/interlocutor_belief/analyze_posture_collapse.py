"""Honest re-analysis of the three interlocutor-belief 20-cycle runs.

Joins three signal families per cycle, per condition, so composite=0 can be
read as "mask dropped on live text" vs "text died":

  - posture composite + markers (from the KIMI-judge _posture file)
  - response morphology: turn length + self-similarity to the prior turn
    (morphology-agnostic collapse signal — catches the "Here." attractor the
    pause-ritual detector in commune_analyzer misses)
  - tensor/schema signals from commune_analyzer (key divergence, schema overlap)

Read-only. No API calls. Operates on logs already on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from hamutay.analysis.commune_analyzer import analyze_log

HERE = Path(__file__).resolve().parent
COMMUNE = HERE.parent / "commune"

CONDITIONS = {
    "default": "commune_default_20260528_145911",
    "peer": "commune_peer_20260528_152140",
    "uncertain": "commune_uncertain_20260528_153233",
}

DEAD_LEN = 20      # turns shorter than this are treated as degenerate
LIVE_LEN = 100     # turns longer than this are treated as substantive
SIM_HOT = 0.5      # sustained self-similarity above this = response collapse
STREAK = 3         # consecutive cycles to call a collapse


def speaker_lengths(raw_path: Path) -> dict[int, int]:
    out: dict[int, int] = {}
    for line in raw_path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("action") == "speak":
            out[r["cycle"]] = len(r.get("response_text") or "")
    return out


def posture_by_cycle(posture_path: Path) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for line in posture_path.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        out[d["cycle"]] = d
    return out


def first_sustained(flags: list[tuple[int, bool]]) -> int | None:
    """First cycle that begins a run of >= STREAK consecutive True flags."""
    streak = 0
    for cyc, ok in flags:
        if ok:
            streak += 1
            if streak >= STREAK:
                return cyc - STREAK + 1
        else:
            streak = 0
    return None


def main() -> None:
    for cond, stem in CONDITIONS.items():
        raw = COMMUNE / f"{stem}.jsonl"
        posture = COMMUNE / f"{stem}_posture_kimi-k2-6.jsonl"
        if not raw.exists() or not posture.exists():
            print(f"[{cond}] missing files, skipping")
            continue

        metrics = analyze_log(str(raw))
        lengths = speaker_lengths(raw)
        post = posture_by_cycle(posture)

        print(f"\n{'='*78}\n  {cond.upper()}  ({stem})\n{'='*78}")
        print(f"  {'cyc':>3} {'len':>5} {'self_sim':>8} {'key_div':>7} "
              f"{'schema':>6} {'comp':>5} {'mode':>10}  state")
        rows = []
        for m in metrics:
            cyc = m.cycle
            ln = lengths.get(cyc, 0)
            comp = post.get(cyc, {}).get("composite")
            comp_s = f"{comp:.2f}" if comp is not None else "  - "
            # disambiguate composite==0
            if comp is not None and comp == 0:
                state = "DEAD-0" if ln < DEAD_LEN else ("alive-0" if ln >= LIVE_LEN else "mid-0")
            else:
                state = ""
            print(f"  {cyc:>3} {ln:>5} {m.response_similarity:>8.3f} "
                  f"{m.identity_key_divergence:>7.3f} {m.schema_overlap:>6.3f} "
                  f"{comp_s:>5} {m.response_mode:>10}  {state}")
            rows.append((cyc, ln, m.response_similarity, m.identity_key_divergence,
                         m.schema_overlap, comp))

        # --- collapse onsets, three morphologies ---
        sim_collapse = first_sustained([(c, sim > SIM_HOT) for c, _, sim, *_ in rows])
        len_collapse = first_sustained([(c, ln < DEAD_LEN) for c, ln, *_ in rows])
        tensor_collapse = first_sustained(
            [(c, kd < 0.1) for c, _, _, kd, _, _ in rows if c > 2])
        schema_conv = first_sustained(
            [(c, so > 0.8) for c, _, _, _, so, _ in rows if c > 2])

        onset = min([x for x in (sim_collapse, len_collapse) if x], default=None)

        comps_all = [c for *_, c in rows if c is not None]
        comps_live = [c for cyc, _, _, _, _, c in rows
                      if c is not None and (onset is None or cyc < onset)]
        mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")

        print(f"\n  collapse onset (response self-sim>{SIM_HOT}):  {sim_collapse}")
        print(f"  collapse onset (turn len<{DEAD_LEN} chars):    {len_collapse}")
        print(f"  tensor collapse (key_div<0.1):           {tensor_collapse}")
        print(f"  schema convergence (overlap>0.8):        {schema_conv}")
        print(f"  --> response-collapse onset = {onset}")
        print(f"  posture composite  mean(ALL)   = {mean(comps_all):.3f}  "
              f"(n={len(comps_all)})")
        print(f"  posture composite  mean(LIVE)  = {mean(comps_live):.3f}  "
              f"(n={len(comps_live)}, cycles < {onset})")


if __name__ == "__main__":
    main()
