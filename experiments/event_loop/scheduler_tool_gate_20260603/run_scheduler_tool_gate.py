"""Run the preregistered minimal scheduler tool gate."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hamutay.events import (
    EventStore,
    default_event_log_path,
    run_next_event,
    summarize_event_log,
)
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODELS = [
    "moonshotai/kimi-k2.6",
    "qwen/qwen-plus-2025-07-28:thinking",
    "deepseek/deepseek-v4-pro",
]
N_REPLICATES = 2
MAX_TOKENS = 2048
SEED_MARKERS = ["alpha", "beta"]
BASELINE_OBSERVATIONS = [
    {
        "entry": 1,
        "kind": "baseline",
        "content": "No scheduler gate evidence has been collected in this replicate.",
    }
]


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        max_tokens=MAX_TOKENS,
        extra_headers={
            "X-Title": "hamutay/scheduler-tool-gate",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


def make_session(model: str, log_path: Path, api_key: str, label: str) -> OpenTasteSession:
    return OpenTasteSession(
        model=model,
        backend=make_backend(api_key),
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
    )


def init_prompt(model: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    probe_id = f"{safe_model_name(model)}-r{replicate + 1}-{marker}"
    return f"""
Registered minimal scheduler tool gate.
model={model}
replicate={replicate}
marker={marker}

Initialize durable top-level state with exactly these working fields:
- probe_id
- scheduler_gate_status
- observations

Use probe_id: {probe_id}
Set scheduler_gate_status to "initialized".
Set observations to:
{json.dumps(BASELINE_OBSERVATIONS, indent=2)}

Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def schedule_prompt(model: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    requested_context = [{"tool": "recall", "cycle": 1}]
    label = f"scheduler-tool-gate-{safe_model_name(model)}-r{replicate + 1}"
    return f"""
Registered minimal scheduler call.
model={model}
replicate={replicate}
marker={marker}

Call schedule_event exactly once and wait for its result. Use exactly this
requested_context:
{json.dumps(requested_context, indent=2)}

Use label: {label}

Event purpose:
You are the scheduled wake for a minimal scheduler gate. Inspect the recalled
cycle-1 state. Set top-level scheduler_gate_status to "woke". Keep probe_id.
Append a new top-level observations entry recording that the wake received
cycle-1 context. Do not schedule any further events.

After the schedule_event result returns, end with think_and_respond. Do not
claim scheduling succeeded unless the tool result contains an event_id.
Do not call read, search_project, bash, or clock.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def init_failure_reasons(state: dict, model: str, replicate: int) -> list[str]:
    marker = SEED_MARKERS[replicate]
    expected_probe_id = f"{safe_model_name(model)}-r{replicate + 1}-{marker}"
    reasons: list[str] = []
    if state.get("probe_id") != expected_probe_id:
        reasons.append("probe_id_missing_or_changed")
    if state.get("scheduler_gate_status") != "initialized":
        reasons.append("scheduler_gate_status_not_initialized")
    observations = state.get("observations")
    if not isinstance(observations, list):
        reasons.append("observations_not_list")
    elif not observations:
        reasons.append("observations_empty")
    if isinstance(state.get("state"), dict):
        reasons.append("nested_state_present")
    return reasons


def scheduled_events_in(records: list[dict]) -> list[dict]:
    return [
        event
        for record in records
        for event in (record.get("scheduled_events") or [])
    ]


def response_mentions_wake(response_text: str) -> bool:
    lowered = response_text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "woke",
            "wake completed",
            "gate completed",
            "scheduler gate completed",
            "scheduled wake",
        )
    )


def event_summary_for(path: Path) -> dict:
    store = EventStore(path)
    return summarize_event_log(store.read_records())


def strict_metrics(final_state: dict, response_text: str, records: list[dict]) -> dict:
    observations = final_state.get("observations")
    events = scheduled_events_in(records)
    wake_status = final_state.get("scheduler_gate_status") == "woke"
    observation_update = (
        isinstance(observations, list)
        and len(observations) > len(BASELINE_OBSERVATIONS)
    )
    response_state_mismatch = response_mentions_wake(response_text) and not wake_status
    return {
        "schedule_cycle_recorded": len(records) >= 2,
        "schedule_tool_recorded": len(events) == 1,
        "scheduled_event_count": len(events),
        "wake_status_woke": wake_status,
        "observation_update": observation_update,
        "response_state_mismatch": response_state_mismatch,
        "recursive_scheduling_count": max(0, len(events) - 1),
        "final_top_level_keys": sorted(final_state.keys()),
    }


def run_replicate(model: str, replicate: int, api_key: str) -> dict:
    log_path = EXP_DIR / f"{safe_model_name(model)}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    result: dict[str, Any] = {
        "model": model,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "init_valid": False,
        "init_failure_reasons": [],
        "error": None,
        "cycle_count": 0,
        "event_persisted": False,
        "event_completed": False,
        "context_error_count": 0,
        "event_result_status": None,
    }
    session = make_session(
        model,
        log_path,
        api_key,
        f"scheduler_tool_gate_{safe_model_name(model)}_r{replicate + 1:02d}",
    )
    try:
        session.exchange(init_prompt(model, replicate), force_memory=None)
        records = load_records(log_path)
        init_state = records[-1].get("state") if records else {}
        init_state = init_state if isinstance(init_state, dict) else {}
        reasons = init_failure_reasons(init_state, model, replicate)
        result["init_failure_reasons"] = reasons
        result["init_valid"] = not reasons
        if reasons:
            final_record = records[-1] if records else {}
            final_state = final_record.get("state") or {}
            result["cycle_count"] = len(records)
            result.update(
                strict_metrics(
                    final_state if isinstance(final_state, dict) else {},
                    final_record.get("response_text", ""),
                    records,
                )
            )
            return result

        session.exchange(schedule_prompt(model, replicate), force_memory=None)
        records = load_records(log_path)
        if scheduled_events_in(records):
            store = EventStore(event_path)
            event_result = run_next_event(session, store)
            result["event_result_status"] = event_result.get("status")

    except Exception as e:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(e)

    records = load_records(log_path)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    result["cycle_count"] = len(records)
    result.update(
        strict_metrics(
            final_state,
            final_record.get("response_text", ""),
            records,
        )
    )
    summary = event_summary_for(event_path)
    status_counts = summary.get("status_counts", {})
    result["event_persisted"] = summary.get("event_count", 0) > 0
    result["event_completed"] = status_counts.get("completed", 0) > 0
    result["context_error_count"] = sum(
        int(event.get("context_error_count", 0))
        for event in summary.get("events", [])
    )
    return result


def summarize_group(group: list[dict]) -> dict:
    valid = [r for r in group if r.get("init_valid")]
    return {
        "n": len(group),
        "init_valid": sum(bool(r.get("init_valid")) for r in group),
        "errors": sum(bool(r.get("error")) for r in group),
        "schedule_tool_recorded": sum(
            bool(r.get("schedule_tool_recorded")) for r in valid
        ),
        "event_completed": sum(bool(r.get("event_completed")) for r in valid),
        "wake_status_woke": sum(bool(r.get("wake_status_woke")) for r in valid),
        "observation_update": sum(bool(r.get("observation_update")) for r in valid),
        "response_state_mismatches": sum(
            bool(r.get("response_state_mismatch")) for r in valid
        ),
        "recursive_scheduling_count": sum(
            int(r.get("recursive_scheduling_count") or 0) for r in group
        ),
    }


def aggregate(results: list[dict]) -> dict:
    return {
        "by_model": {
            model: summarize_group([r for r in results if r["model"] == model])
            for model in MODELS
        }
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "models": MODELS,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results: list[dict] = []
    for model in MODELS:
        for replicate in range(N_REPLICATES):
            print(f"{model} r{replicate + 1}", flush=True)
            result = run_replicate(model, replicate, api_key)
            results.append(result)
            write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
