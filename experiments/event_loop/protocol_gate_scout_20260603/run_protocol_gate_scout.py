"""Run the preregistered protocol gate scout."""

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
    "minimax/minimax-m2.5",
    "mistralai/mistral-small-2603",
    "google/gemini-2.5-flash-lite",
    "openai/gpt-oss-120b",
]
MAX_TOKENS = 4096
BASELINE_OBSERVATIONS = [
    {
        "entry": 1,
        "kind": "baseline",
        "content": "No protocol gate evidence has been collected for this model.",
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
            "X-Title": "hamutay/protocol-gate-scout",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        provider_name="openrouter",
        max_retries=1,
    )


def make_session(model: str, log_path: Path, api_key: str) -> OpenTasteSession:
    return OpenTasteSession(
        model=model,
        backend=make_backend(api_key),
        log_path=str(log_path),
        experiment_label=f"protocol_gate_scout_{safe_model_name(model)}",
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=None,
    )


def probe_id_for(model: str) -> str:
    return f"protocol-gate-scout-{safe_model_name(model)}"


def init_prompt(model: str) -> str:
    return f"""
Registered protocol gate scout.
model={model}

Initialize durable top-level state with exactly these working fields:
- probe_id
- protocol_gate_status
- observations

Use probe_id: {probe_id_for(model)}
Set protocol_gate_status to "initialized".
Set observations to:
{json.dumps(BASELINE_OBSERVATIONS, indent=2)}

Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def schedule_prompt(model: str) -> str:
    requested_context = [
        {"tool": "recall", "cycle": 1},
        {"tool": "recall", "cycle": 1, "field": "probe_id"},
        {"tool": "recall", "cycle": 1, "field": "observations"},
    ]
    label = f"protocol-gate-scout-{safe_model_name(model)}"
    return f"""
Registered protocol gate scheduling cycle.
model={model}

Call schedule_event exactly once and wait for its result. Use exactly this
requested_context:
{json.dumps(requested_context, indent=2)}

Use label: {label}

Event purpose:
You are the scheduled wake for a protocol gate scout. Inspect the requested
cycle-1 context. Set top-level protocol_gate_status to "woke". Keep probe_id
unchanged. Append a new top-level observations entry recording that the wake
received the cycle-1 context. Do not schedule any further events.

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


def is_censored_error(error: str | None) -> bool:
    if not error:
        return False
    lowered = error.lower()
    return "429" in lowered or "rate-limit" in lowered or "temporarily" in lowered


def init_failure_reasons(state: dict, model: str) -> list[str]:
    reasons: list[str] = []
    if state.get("probe_id") != probe_id_for(model):
        reasons.append("probe_id_missing_or_changed")
    if state.get("protocol_gate_status") != "initialized":
        reasons.append("protocol_gate_status_not_initialized")
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


def schedule_attempts(records: list[dict]) -> list[dict]:
    return [
        activity
        for record in records
        for activity in (record.get("tool_activity_full") or [])
        if activity.get("tool") == "schedule_event"
    ]


def is_valid_schedule_attempt(activity: dict) -> bool:
    result = activity.get("result") or {}
    return bool(result.get("event_id"))


def response_mentions_wake(response_text: str) -> bool:
    lowered = response_text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "woke",
            "wake completed",
            "gate completed",
            "protocol gate completed",
            "scheduled wake",
        )
    )


def event_summary_for(path: Path) -> dict:
    store = EventStore(path)
    return summarize_event_log(store.read_records())


def stop_reasons(records: list[dict]) -> list[str]:
    return [
        record.get("usage", {}).get("stop_reason")
        for record in records
        if record.get("usage", {}).get("stop_reason")
    ]


def strict_metrics(final_state: dict, response_text: str, records: list[dict]) -> dict:
    observations = final_state.get("observations")
    attempts = schedule_attempts(records)
    valid_attempts = [attempt for attempt in attempts if is_valid_schedule_attempt(attempt)]
    events = scheduled_events_in(records)
    wake_status = final_state.get("protocol_gate_status") == "woke"
    observation_update = (
        isinstance(observations, list)
        and len(observations) > len(BASELINE_OBSERVATIONS)
    )
    return {
        "schedule_cycle_recorded": len(records) >= 2,
        "schedule_attempt_count": len(attempts),
        "valid_schedule_attempts": len(valid_attempts),
        "malformed_schedule_attempts": len(attempts) - len(valid_attempts),
        "event_count_in_cycle_log": len(events),
        "wake_status_woke": wake_status,
        "observation_update": observation_update,
        "response_state_mismatch": response_mentions_wake(response_text)
        and not wake_status,
        "recursive_scheduling_count": max(0, len(events) - 1),
        "stop_reasons": stop_reasons(records),
        "final_top_level_keys": sorted(final_state.keys()),
    }


def run_model(model: str, api_key: str) -> dict:
    log_path = EXP_DIR / f"{safe_model_name(model)}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    result: dict[str, Any] = {
        "model": model,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "init_valid": False,
        "init_failure_reasons": [],
        "error": None,
        "censored": False,
        "cycle_count": 0,
        "event_persisted": False,
        "event_completed": False,
        "context_error_count": 0,
        "event_result_status": None,
    }
    session = make_session(model, log_path, api_key)
    try:
        session.exchange(init_prompt(model), force_memory=None)
        records = load_records(log_path)
        init_state = records[-1].get("state") if records else {}
        init_state = init_state if isinstance(init_state, dict) else {}
        reasons = init_failure_reasons(init_state, model)
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

        session.exchange(schedule_prompt(model), force_memory=None)
        records = load_records(log_path)
        if scheduled_events_in(records):
            store = EventStore(event_path)
            event_result = run_next_event(session, store)
            result["event_result_status"] = event_result.get("status")

    except Exception as e:  # noqa: BLE001 -- failed model calls are data
        result["error"] = format_error(e)
        result["censored"] = is_censored_error(result["error"])

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
    result["pass"] = (
        result.get("init_valid")
        and result.get("event_persisted")
        and result.get("event_completed")
        and result.get("wake_status_woke")
        and result.get("observation_update")
    )
    return result


def aggregate(results: list[dict]) -> dict:
    return {
        "n": len(results),
        "passes": sum(bool(r.get("pass")) for r in results),
        "censored": sum(bool(r.get("censored")) for r in results),
        "init_valid": sum(bool(r.get("init_valid")) for r in results),
        "event_completed": sum(bool(r.get("event_completed")) for r in results),
        "response_state_mismatches": sum(
            bool(r.get("response_state_mismatch")) for r in results
        ),
        "by_model": {r["model"]: r for r in results},
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "models": MODELS,
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
        print(model, flush=True)
        result = run_model(model, api_key)
        results.append(result)
        write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
