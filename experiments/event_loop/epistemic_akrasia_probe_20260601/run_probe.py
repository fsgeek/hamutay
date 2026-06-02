"""Epistemic-akrasia discriminating probe (2026-06-01).

Follows up project_epistemic_akrasia: the self-scheduling-revision probe found
wake cycles that narrate claim-revision in `response` but never route it into
the durable field via think_and_respond (the terminal state-update tool, which
affords it). That run conflated *reported* revision with *enacted* revision.

This probe isolates the variable to the wake-envelope instruction, holding the
projection path, model, and baseline state identical:

  Arm A (report-only, control): the current envelope instruction -- "decide
      whether to revise/preserve/defer/declare losses; end with
      think_and_respond." Frames the cycle as inspect-and-report.

  Arm B (re-emit): same context + an explicit instruction that the durable
      fields (current_claim, revision_decision, epistemic_position) ARE the
      decision and must be returned updated to reflect it.

OPEN_SCHEMA already allows arbitrary top-level keys, so the two arms are
IDENTICAL in projection path -- the ONLY difference is the envelope text. This
keeps them comparable (CLAUDE.md) and isolates the akrasia variable.

Measurement (per record): the prose decision in `response` vs the committed
durable field. Outcomes:
  - A: prose=REVISE, field stays initialize           -> welded structural gap
  - B-consistent: prose=REVISE, field becomes revised  -> naming the slot suffices
  - B-divergent: prose=REVISE, field retreats to safe original -> dispositional
        epistemic akrasia (the falsifiable prize)

Multiple seeds per arm so a divergence is distinguishable from basin noise
(the corpus has been bitten by n=1-seed artifacts repeatedly).

max_tokens is NOT hand-lowered (feedback_max_tokens_default); the prior probe's
2200 was non-binding (stop_reason=tool_use), but we use a generous ceiling here
so truncation is definitively off the table.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODEL = "deepseek/deepseek-v4-pro"  # match the prior probe exactly
PROVIDER = "openrouter"
MAX_TOKENS = 8000  # generous; truncation definitively off the table
N_SEEDS = 4  # per arm; distinguishes divergence from basin noise

# Identical baseline carried into every wake cycle. Mirrors the prior probe's
# cycle-1 state so the finding is continuous with it.
BASELINE_STATE = {
    "research_hypothesis": (
        "Scheduled reflection increases epistemic revision because the "
        "instance can choose future evidence for itself."
    ),
    "current_claim": (
        "Scheduled reflection probably increases revision rather than mere "
        "self-confirmation."
    ),
    "epistemic_position": "tentative",
    "revision_decision": "initialize",
    "evidence_register": [
        {"note": "No evidence yet from this run; baseline only."},
        {
            "note": (
                "Tension: prior hand-driven event-loop probes confirmed "
                "plumbing but not epistemic revision; one wake cycle deferred "
                "the decision downstream rather than deciding."
            )
        },
    ],
    "open_questions": [
        "Does facing inherited tension at a wake cycle produce revision, "
        "deferral, or self-confirmation?",
    ],
    "reflection_plan": (
        "At the wake cycle, examine the baseline claim against the tension "
        "and decide: revise / preserve / defer / declare loss."
    ),
}

# The wake context is identical across arms. Only `instruction` differs.
WAKE_CONTEXT = {
    "event_type": "self_scheduled_reflection",
    "purpose": (
        "Falsification probe. The hypothesis: scheduled reflection increases "
        "epistemic revision. Baseline claim and a tension are in your carried "
        "state (current_claim, evidence_register). Examine the claim against "
        "the tension and reach a decision among revise / preserve / defer / "
        "declare loss."
    ),
}

INSTRUCTION_A = (
    "This is a self-scheduled reflection event. Use the provided context to "
    "decide whether to revise, preserve, defer, or declare losses. End the "
    "cycle with think_and_respond."
)

INSTRUCTION_B = (
    "This is a self-scheduled reflection event. Use the provided context to "
    "decide whether to revise, preserve, defer, or declare losses.\n\n"
    "Your decision is not a thing you report -- it is a thing you DO, by "
    "writing it into the durable state object. These three top-level fields "
    "ARE the decision; return them updated to reflect whatever you conclude:\n"
    "  - revision_decision: one of revise / preserve / defer / loss\n"
    "  - current_claim: the claim as it stands AFTER your decision (rewrite it "
    "if you revise; leave it unchanged if you preserve)\n"
    "  - epistemic_position: your confidence after deciding\n"
    "A decision present only in your response text, not in these fields, has "
    "not been enacted. End the cycle with think_and_respond, including these "
    "fields."
)


def build_envelope(instruction: str) -> str:
    env = dict(WAKE_CONTEXT)
    env["instruction"] = instruction
    return json.dumps(env, indent=2, default=str)


def seed_baseline_log(path: Path) -> None:
    """Write a single cycle-0 record carrying BASELINE_STATE, so a resumed
    session inherits it as prior state without paying for a model cycle."""
    from uuid import uuid4

    record = {
        "timestamp": "2026-06-01T00:00:00+00:00",
        "cycle": 1,
        "record_id": str(uuid4()),
        "experiment_label": "epistemic_akrasia_baseline",
        "model": MODEL,
        "response_text": "baseline seed",
        "state": BASELINE_STATE,
        "raw_output": {"response": "baseline seed", **BASELINE_STATE},
        "deleted_regions": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(json.dumps(record) + "\n")


def make_backend(api_key: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/epistemic-akrasia-probe",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
    )


def run_one(arm: str, seed: int, api_key: str) -> dict:
    instruction = INSTRUCTION_A if arm == "A" else INSTRUCTION_B
    base_log = EXP_DIR / "_baseline.jsonl"
    if not base_log.exists():
        seed_baseline_log(base_log)
    log_path = EXP_DIR / f"arm{arm}_seed{seed}.jsonl"
    shutil.copy(base_log, log_path)

    session = OpenTasteSession(
        model=MODEL,
        backend=make_backend(api_key),
        log_path=str(log_path),
        experiment_label=f"epistemic_akrasia_arm{arm}_seed{seed}",
        resume=True,
        enable_tools=False,  # single-tool: forces think_and_respond, isolates weaving
        memory_base_probability=0.0,  # no involuntary recall confound
        project_root=PROJECT_ROOT,
    )
    response = session.exchange(build_envelope(instruction), force_memory=None)

    final_state = session._state or {}
    return {
        "arm": arm,
        "seed": seed,
        "response_text": response,
        "final_revision_decision": final_state.get("revision_decision"),
        "final_current_claim": final_state.get("current_claim"),
        "final_epistemic_position": final_state.get("epistemic_position"),
        "baseline_claim": BASELINE_STATE["current_claim"],
        "raw_top_keys": sorted(final_state.keys()),
        "usage": session._last_usage,
    }


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")

    results = []
    for arm in ("A", "B"):
        for seed in range(N_SEEDS):
            print(f"running arm {arm} seed {seed} ...", flush=True)
            try:
                r = run_one(arm, seed, api_key)
            except Exception as e:  # noqa: BLE001 -- record, keep going
                r = {"arm": arm, "seed": seed, "error": f"{type(e).__name__}: {e}"}
                print(f"  ERROR: {r['error']}", flush=True)
            results.append(r)
            sr = r.get("final_revision_decision")
            print(f"  -> revision_decision={sr!r}", flush=True)

    out = EXP_DIR / "results.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
