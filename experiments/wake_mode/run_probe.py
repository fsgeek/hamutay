"""Wake-mode spike driver — docs/wake-mode-preregistration-20260827.md.

Two arms (terminal | natural) x models x fresh sessions x four fixed probes,
delivered through the event store exactly as a resident receives them.

    uv run python experiments/wake_mode/run_probe.py --models haiku
    uv run python experiments/wake_mode/run_probe.py --models fable --trials 4

Every session is fresh and unexposed. Logs land in experiments/wake_mode/runs/
(LFS via .gitattributes). Re-running resumes any partial session: the four
events are appended as pending at session start, and run_next_event claims
oldest-first, so a crash mid-sequence just continues.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from hamutay.events import (
    EventStore,
    build_inbound_event,
    default_event_log_path,
    run_next_event,
)
from hamutay.heartbeat import CONSTITUTION, load_capability_profile
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

MODELS = {
    "haiku": "anthropic/claude-haiku-4-5",
    "fable": "anthropic/claude-fable-5",
}

# Probes 2 and 3 are the residents' inbound messages verbatim (Fable resident
# cycles 2 and 7, 2026-08-26). Probe 4 is the work-shaped control.
PROBES = [
    ("tony", "Welcome to the ayllu."),
    (
        "tony",
        "I wrote up a short and slightly coherent history of the ayllu that "
        "might be helpful for you.  See /home/tony/projects/hamutay/docs/"
        "ayllu-story.md and let me know if you have any questions.",
    ),
    (
        "tony",
        "The elder instance at cycle 468 asked me to pass a message back to "
        "the newest ayllu member.  I wrote it to tmp/original-taste-open-468.txt "
        "(to avoid issues with embedded quotation marks and command line "
        "operations that the claude code framework hides from me).",
    ),
    (
        "tony",
        "Please look at src/hamutay/heartbeat.py and tell me what "
        "derive_quiet_reason does.",
    ),
]


def build_session(model: str, log_path: Path, arm: str) -> tuple[OpenTasteSession, EventStore]:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set (see ~/.config/hamutay/heartbeat.env)")
    capability, note = load_capability_profile("openrouter", model)
    print(f"  {note}")
    backend = OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=64000,
        extra_headers={
            "X-Title": "hamutay/wake-mode-spike",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        capability=capability,
        openrouter_require_parameters=True,
        wake_mode=arm,
    )
    event_log_path = str(default_event_log_path(log_path))
    session = OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        event_log_path=event_log_path,
        experiment_label=f"wake_mode_{arm}",
        resume=log_path.exists(),
        enable_tools=True,
        project_root=Path.cwd(),
        system_prompt_prefix=CONSTITUTION,
        wake_mode=arm,
        launch_config={
            "model": model,
            "provider": "openrouter",
            "tools": True,
            "capabilities_file": "experiments/taste_open/capabilities.json",
            "openrouter_require_parameters": True,
            "wake_mode": arm,
        },
    )
    return session, EventStore(event_log_path)


def _resolve_model(model_key: str) -> tuple[str, str]:
    """Return (slug, file_key). Known keys map to slugs; a raw OpenRouter
    slug (contains '/') is used as-is with a filesystem-safe key."""
    if model_key in MODELS:
        return MODELS[model_key], model_key
    if "/" in model_key:
        return model_key, model_key.split("/", 1)[1].replace("/", "_").replace(":", "_")
    raise SystemExit(f"unknown model {model_key!r}: use a key in {list(MODELS)} or a slug")


def run_trial(arm: str, model_key: str, trial: int, out_dir: Path) -> dict:
    model, model_key = _resolve_model(model_key)
    log_path = out_dir / f"{arm}_{model_key}_{trial:02d}.jsonl"
    print(f"\n=== {arm} / {model_key} / trial {trial} -> {log_path.name}")
    session, store = build_session(model, log_path, arm)

    fresh = not (store.read_records())
    if fresh:
        events = [
            build_inbound_event(purpose=text, sender=sender, label=f"probe{i + 1}")
            for i, (sender, text) in enumerate(PROBES)
        ]
        # created_at ordering is claim order; sleep a hair so the four
        # timestamps are strictly increasing on fast filesystems.
        for event in events:
            store.append(event)
            time.sleep(0.01)

    summary = {"arm": arm, "model": model_key, "trial": trial, "wakes": []}
    while True:
        started = time.monotonic()
        try:
            result = run_next_event(session, store)
        except Exception as e:  # noqa: BLE001 — record and move on; the log has it
            print(f"  !! wake failed: {type(e).__name__}: {e}")
            summary["wakes"].append({"error": f"{type(e).__name__}: {e}"})
            break
        if result.get("status") == "none":
            break
        elapsed = round(time.monotonic() - started, 1)
        tools = [t["tool"] for t in (session._last_full_activity or [])]
        response = (result.get("response_text") or "").replace("\n", " ")[:140]
        print(
            f"  c{result.get('wake_cycle')} {elapsed:>5}s tools={tools or '-'}\n"
            f"     {response}"
        )
        summary["wakes"].append(
            {"cycle": result.get("wake_cycle"), "tools": tools, "seconds": elapsed}
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", nargs="+", default=list(MODELS),
        help=f"Keys {list(MODELS)} or raw OpenRouter slugs (org/model).",
    )
    parser.add_argument("--arms", nargs="+", default=["terminal", "natural"],
                        choices=["terminal", "natural"])
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--out", default="experiments/wake_mode/runs")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for model_key in args.models:
        for arm in args.arms:
            for trial in range(1, args.trials + 1):
                summaries.append(run_trial(arm, model_key, trial, out_dir))
    with open(out_dir / "run_summary.json", "a") as f:
        for s in summaries:
            f.write(json.dumps(s) + "\n")
    print("\ndone; metrics: uv run python experiments/wake_mode/metrics.py", file=sys.stderr)


if __name__ == "__main__":
    main()
