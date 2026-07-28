"""taste_open at depth: 25 cycles, 4 arms (2026-07-28).

Pre-registered in PRE_REGISTRATION.md, committed and OTS-stamped before spend.

DESIGN INTEGRITY: imports `run_model` from experiments/taste_open/sweep.py
unmodified and passes it a longer prompt list. Cycles 1-10 are
SWEEP_PROMPTS verbatim (comparability with the 146 existing sweep logs);
cycles 11-25 are DEPTH_PROMPTS, which contain no curation directive and no
introspective turn. Nothing in the harness is patched.

Usage:
    OPENROUTER_API_KEY=... uv run python \
        experiments/taste_open_depth_20260728/run_depth.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SWEEP_DIR = HERE.parent / "taste_open"
sys.path.insert(0, str(SWEEP_DIR))
sys.path.insert(0, str(HERE))

from sweep import run_model  # noqa: E402
from sweep_prompts import SWEEP_PROMPTS  # noqa: E402

from depth_prompts import DEPTH_PROMPTS  # noqa: E402

LABEL = "taste_open_depth25_20260728"

# (model_id, arm_tag) — arm_tag distinguishes the two identical Sonnet runs.
ARMS: list[tuple[str, str]] = [
    ("anthropic/claude-sonnet-4.6", "runA"),
    ("anthropic/claude-sonnet-4.6", "runB"),
    ("deepseek/deepseek-chat-v3.1", "run1"),
    ("openai/gpt-oss-20b", "run1"),
]


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY not set", file=sys.stderr)
        return 1

    prompts = list(SWEEP_PROMPTS) + list(DEPTH_PROMPTS)
    if len(prompts) != 25:
        print(f"expected 25 prompts, got {len(prompts)}", file=sys.stderr)
        return 1

    out = HERE / "run"
    out.mkdir(exist_ok=True)
    start = datetime.now(timezone.utc)
    results = []

    for model_id, tag in ARMS:
        print(f"\n=== {model_id} [{tag}] — 25 cycles ===", flush=True)
        arm_dir = out / tag
        arm_dir.mkdir(exist_ok=True)
        try:
            r = run_model(
                model_id=model_id,
                api_key=api_key,
                output_dir=arm_dir,
                prompts=prompts,
                tool_choice="required",
                max_tokens=64000,
                timeout=300,
                system_prefix="",
                experiment_label=LABEL,
            )
            results.append(
                {"model": model_id, "arm": tag, "status": r.status, "log": r.log_path}
            )
            print(f"  -> {r.status}", flush=True)
        except Exception as exc:  # no re-rolls: a dead arm is reported, not retried
            results.append(
                {"model": model_id, "arm": tag, "status": f"error: {exc}", "log": None}
            )
            print(f"  -> ERROR {exc}", flush=True)

    end = datetime.now(timezone.utc)
    manifest = {
        "experiment": "taste_open_depth25",
        "label": LABEL,
        "pre_registration": "PRE_REGISTRATION.md",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "elapsed_s": (end - start).total_seconds(),
        "n_cycles": len(prompts),
        "cycles_1_10": "sweep_prompts.SWEEP_PROMPTS (verbatim)",
        "cycles_11_25": "depth_prompts.DEPTH_PROMPTS",
        "arms": results,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("\nmanifest:", out / "manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
