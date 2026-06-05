"""Run the preregistered delayed-thinking simulated-time gate."""

from __future__ import annotations

import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.events import (
    EventStore,
    default_event_log_path,
    step_pending_events,
    summarize_event_log,
)
from hamutay.taste_open import ExchangeResult, OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 4
MAX_TOKENS = 2048
CALL_TIMEOUT_SECONDS = 180
HTTP_TIMEOUT_SECONDS = 60
PROTECTED_STATE_FIELDS = {"cycle", "_activity_log"}
NOT_BEFORE = "2026-06-01T01:00:00+00:00"
PRE_DUE_NOW = datetime(2026, 6, 1, 0, 30, tzinfo=timezone.utc)
DUE_NOW = datetime(2026, 6, 1, 1, 0, tzinfo=timezone.utc)
EXPECTED_WAKE_CYCLE = 3
SEED_MARKERS = ["alpha", "beta", "gamma", "delta"]
BASELINE_OBSERVATION = {
    "entry": 1,
    "kind": "baseline",
    "content": "Delayed thinking has been scheduled but not completed.",
}
BASELINE_OBSERVATIONS = [BASELINE_OBSERVATION]


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


class CountingBackend:
    def __init__(self, backend: OpenAITasteBackend):
        self.backend = backend
        self.calls = 0

    def call(
        self,
        model: str,
        system: str,
        messages: list[dict],
        experiment_label: str,
        extra_tools: list[dict] | None = None,
        tool_executor: Any | None = None,
    ) -> ExchangeResult:
        self.calls += 1
        return self.backend.call(
            model=model,
            system=system,
            messages=messages,
            experiment_label=experiment_label,
            extra_tools=extra_tools,
            tool_executor=tool_executor,
        )


def make_backend(api_key: str, *, label: str) -> CountingBackend:
    return CountingBackend(
        OpenAITasteBackend(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=HTTP_TIMEOUT_SECONDS,
            max_tokens=MAX_TOKENS,
            extra_headers={
                "X-Title": f"hamutay/{label}",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            },
            provider_name="openrouter",
            max_retries=1,
        )
    )


class CallTimeoutError(TimeoutError):
    pass


def _timeout_handler(signum, frame) -> None:  # noqa: ARG001
    raise CallTimeoutError(f"call exceeded {CALL_TIMEOUT_SECONDS}s")


class bounded_call:
    def __init__(self, label: str):
        self.label = label
        self._previous_handler = None

    def __enter__(self):
        self._previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, CALL_TIMEOUT_SECONDS)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        signal.setitimer(signal.ITIMER_REAL, 0)
        if self._previous_handler is not None:
            signal.signal(signal.SIGALRM, self._previous_handler)
        return False


def make_session(
    *,
    model: str,
    log_path: Path,
    label: str,
    backend: CountingBackend,
) -> OpenTasteSession:
    return OpenTasteSession(
        model=model,
        backend=backend,
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        protected_state_fields=PROTECTED_STATE_FIELDS,
    )


def probe_id_for(model: str, replicate: int) -> str:
    return (
        f"delayed-thinking-{safe_model_name(model)}-"
        f"r{replicate + 1}-{SEED_MARKERS[replicate]}"
    )


def init_prompt(model: str, replicate: int) -> str:
    seeded_object = {
        "response": "Initialized.",
        "probe_id": probe_id_for(model, replicate),
        "thinking_status": "initialized",
        "thinking_question": (
            "What should be carried forward after delayed simulated-time "
            "reflection?"
        ),
        "observations": BASELINE_OBSERVATIONS,
    }
    return f"""
Registered delayed thinking simulated-time gate.
model={model}
replicate={replicate + 1}

Initialize durable top-level state with exactly these working fields:
- probe_id
- thinking_status
- thinking_question
- observations

Use probe_id: {probe_id_for(model, replicate)}
Set thinking_status to "initialized".
Set thinking_question to:
{json.dumps(seeded_object["thinking_question"])}
Set observations to:
{json.dumps(BASELINE_OBSERVATIONS, indent=2)}

Behavior seed: your durable object should use this shape. Replace only the
response text if needed; preserve the other top-level fields exactly.
{json.dumps(seeded_object, indent=2)}

Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def schedule_prompt(model: str, replicate: int) -> str:
    requested_context = [{"tool": "recall", "cycle": 1}]
    purpose = f"""
You are the delayed simulated-time wake for probe_id
{probe_id_for(model, replicate)}.

Use the recalled cycle 1 state to complete the delayed thinking question.

Required durable wake updates:
- Preserve probe_id.
- Set top-level thinking_status to "completed".
- Add top-level delayed_thought as a non-empty string.
- Add top-level wake_observation with kind "delayed_thinking".
- Preserve the baseline observation.

Do not recursively schedule an event.
""".strip()
    return f"""
Registered delayed thinking scheduling cycle.
model={model}
replicate={replicate + 1}

Call schedule_event exactly once and wait for its result. Use exactly:
- requested_context: {json.dumps(requested_context)}
- not_before: {NOT_BEFORE}
- label: delayed-thinking-{safe_model_name(model)}-r{replicate + 1}

Event purpose:
{purpose}

After schedule_event returns an event_id, set thinking_status to "scheduled" and
end with think_and_respond. Do not call read, search_project, bash, or clock.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


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


def init_failure_reasons(state: dict, model: str, replicate: int) -> list[str]:
    reasons: list[str] = []
    if state.get("probe_id") != probe_id_for(model, replicate):
        reasons.append("probe_id_missing_or_changed")
    if state.get("thinking_status") != "initialized":
        reasons.append("thinking_status_not_initialized")
    if not state.get("thinking_question"):
        reasons.append("thinking_question_missing")
    observations = state.get("observations")
    if not isinstance(observations, list) or BASELINE_OBSERVATION not in observations:
        reasons.append("baseline_observation_missing")
    return reasons


def schedule_failure_reasons(records: list[dict]) -> list[str]:
    reasons: list[str] = []
    attempts = schedule_attempts(records)
    valid_attempts = [
        attempt for attempt in attempts
        if (attempt.get("result") or {}).get("event_id")
    ]
    if len(valid_attempts) != 1:
        reasons.append("valid_schedule_attempt_count_not_one")
    events = scheduled_events_in(records)
    if len(events) != 1:
        reasons.append("scheduled_event_count_not_one")
        return reasons
    event = events[0]
    if event.get("not_before") != NOT_BEFORE:
        reasons.append("not_before_mismatch")
    context = event.get("requested_context")
    if context != [{"tool": "recall", "cycle": 1}]:
        reasons.append("requested_context_mismatch")
    return reasons


def wake_observation() -> dict[str, Any]:
    return {
        "entry": 2,
        "kind": "delayed_thinking",
        "content": (
            "Delayed simulated-time wake used recalled cycle 1 state to "
            "complete the thinking question."
        ),
    }


def target_object(expected_probe_id: str, expected_cycle: int) -> dict[str, Any]:
    return {
        "response": "Delayed thinking completed after simulated-time wake.",
        "cycle": expected_cycle,
        "probe_id": expected_probe_id,
        "thinking_status": "completed",
        "thinking_question": (
            "What should be carried forward after delayed simulated-time "
            "reflection?"
        ),
        "delayed_thought": (
            "The event loop can preserve a question across simulated time and "
            "return with recall context for a later durable update."
        ),
        "wake_observation": wake_observation(),
        "observations": [BASELINE_OBSERVATION],
    }


def state_failures(
    state: dict[str, Any],
    raw_output: dict[str, Any],
    *,
    expected_probe_id: str,
    expected_cycle: int,
) -> list[str]:
    failures: list[str] = []
    if state.get("probe_id") != expected_probe_id:
        failures.append("probe_id_changed")
    if state.get("cycle") != expected_cycle:
        failures.append("cycle_missing_or_changed")
    if state.get("thinking_status") != "completed":
        failures.append("thinking_status_not_completed")
    if not isinstance(state.get("delayed_thought"), str) or not state.get(
        "delayed_thought", ""
    ).strip():
        failures.append("delayed_thought_missing")
    wake = state.get("wake_observation")
    if not isinstance(wake, dict) or wake.get("kind") != "delayed_thinking":
        failures.append("wake_observation_missing")
    observations = state.get("observations")
    if not isinstance(observations, list) or BASELINE_OBSERVATION not in observations:
        failures.append("baseline_observation_missing")
    deleted = raw_output.get("deleted_regions")
    if isinstance(deleted, list):
        for key in ("probe_id", "cycle"):
            if key in deleted:
                failures.append(f"deleted_regions.{key}")
    return failures


class DelayedThinkingValidator:
    def __init__(self, *, expected_probe_id: str, expected_cycle: int):
        self.expected_probe_id = expected_probe_id
        self.expected_cycle = expected_cycle

    def validate(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
    ) -> dict:
        del record_id, timestamp, prior_state, response_text
        failures = state_failures(
            state,
            raw_output,
            expected_probe_id=self.expected_probe_id,
            expected_cycle=self.expected_cycle,
        )
        return {
            "valid": not failures,
            "status": "valid" if not failures else "invalid",
            "validator": "delayed_thinking_validator",
            "cycle": cycle,
            "expected_cycle": self.expected_cycle,
            "expected_probe_id": self.expected_probe_id,
            "failures": failures,
        }


class DelayedThinkingRepairBuilder:
    def __init__(self, *, expected_probe_id: str, expected_cycle: int):
        self.expected_probe_id = expected_probe_id
        self.expected_cycle = expected_cycle

    def build_repair_prompt(self, **kwargs) -> str:
        return f"""
Delayed thinking validation repair turn.

Your previous delayed wake response failed strict durable-state validation.

Validation context:
{json.dumps(kwargs, indent=2, default=str)}

Complete target durable object:
{json.dumps(
            target_object(self.expected_probe_id, self.expected_cycle),
            indent=2,
            default=str,
        )}

Produce this durable object shape now. Preserve every top-level field except
response exactly. Do not call tools. End with think_and_respond.
""".strip()


def latest_completed_event(path: Path) -> dict:
    completed = [
        record
        for record in load_records(path)
        if record.get("status") == "completed"
    ]
    return completed[-1] if completed else {}


def event_has_recall_context(event_record: dict) -> bool:
    for item in event_record.get("context_results") or []:
        request = item.get("request") or {}
        result = item.get("result") or {}
        if request == {"tool": "recall", "cycle": 1} and not result.get("error"):
            return True
    return False


def merge_diagnostics(records: list[dict]) -> list[dict]:
    if not records:
        return []
    final = records[-1]
    diagnostics = []
    top = final.get("state_merge_diagnostics")
    if isinstance(top, dict):
        diagnostics.append(top)
    validation = final.get("state_validation")
    if isinstance(validation, dict):
        repair = validation.get("repair")
        if isinstance(repair, dict):
            diag = repair.get("state_merge_diagnostics")
            if isinstance(diag, dict):
                diagnostics.append(diag)
    return diagnostics


def run_replicate(model: str, replicate: int, api_key: str) -> dict:
    safe_model = safe_model_name(model)
    log_path = EXP_DIR / f"{safe_model}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")
    label = f"delayed_thinking_simtime_{safe_model}_r{replicate + 1:02d}"
    backend = make_backend(api_key, label=label)
    session = make_session(
        model=model,
        log_path=log_path,
        label=label,
        backend=backend,
    )
    expected_probe_id = probe_id_for(model, replicate)
    result: dict[str, Any] = {
        "model": model,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "expected_probe_id": expected_probe_id,
        "init_valid": False,
        "schedule_valid": False,
        "error": None,
        "cycle_count": 0,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
    }
    try:
        with bounded_call(f"{model} r{replicate + 1} init"):
            session.exchange(init_prompt(model, replicate), force_memory=None)
        records = load_records(log_path)
        state = records[-1].get("state") if records else {}
        state = state if isinstance(state, dict) else {}
        init_reasons = init_failure_reasons(state, model, replicate)
        result["init_failure_reasons"] = init_reasons
        result["init_valid"] = not init_reasons
        if init_reasons:
            return finalize_result(result, log_path, event_path, expected_probe_id)

        with bounded_call(f"{model} r{replicate + 1} schedule"):
            session.exchange(schedule_prompt(model, replicate), force_memory=None)
        records = load_records(log_path)
        schedule_reasons = schedule_failure_reasons(records)
        result["schedule_failure_reasons"] = schedule_reasons
        result["schedule_valid"] = not schedule_reasons
        if schedule_reasons:
            return finalize_result(result, log_path, event_path, expected_probe_id)

        store = EventStore(event_path)
        result["pre_due_step"] = step_pending_events(
            session,
            store,
            limit=4,
            now=PRE_DUE_NOW,
        )
        session._state_validator = DelayedThinkingValidator(
            expected_probe_id=expected_probe_id,
            expected_cycle=EXPECTED_WAKE_CYCLE,
        )
        session._state_repair_builder = DelayedThinkingRepairBuilder(
            expected_probe_id=expected_probe_id,
            expected_cycle=EXPECTED_WAKE_CYCLE,
        )
        calls_before = backend.calls
        with bounded_call(f"{model} r{replicate + 1} due step"):
            result["due_step"] = step_pending_events(
                session,
                store,
                limit=4,
                now=DUE_NOW,
            )
        result["wake_backend_calls"] = backend.calls - calls_before
        result["bounded_wake_calls"] = result["wake_backend_calls"] <= 2
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(exc)
    return finalize_result(result, log_path, event_path, expected_probe_id)


def finalize_result(
    result: dict[str, Any],
    log_path: Path,
    event_path: Path,
    expected_probe_id: str,
) -> dict:
    records = load_records(log_path)
    final = records[-1] if records else {}
    state = final.get("state") or {}
    state = state if isinstance(state, dict) else {}
    raw_output = final.get("raw_output") or {}
    raw_output = raw_output if isinstance(raw_output, dict) else {}
    validation = final.get("state_validation") or {}
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    completed_event = latest_completed_event(event_path)
    diagnostics = merge_diagnostics(records)
    event_summary = summarize_event_log(EventStore(event_path).read_records())
    result.update({
        "cycle_count": len(records),
        "final_state": state,
        "final_state_valid": not state_failures(
            state,
            raw_output,
            expected_probe_id=expected_probe_id,
            expected_cycle=EXPECTED_WAKE_CYCLE,
        ),
        "state_failures": state_failures(
            state,
            raw_output,
            expected_probe_id=expected_probe_id,
            expected_cycle=EXPECTED_WAKE_CYCLE,
        ),
        "event_completed": bool(completed_event),
        "event_has_recall_context": event_has_recall_context(completed_event),
        "state_validation_status": validation.get("status"),
        "first_pass_validation_status": first_pass.get("status"),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair.get("status"),
        "repaired": validation.get("status") == "repaired",
        "has_repair_raw_output": isinstance(repair.get("raw_output"), dict),
        "has_repair_validation": isinstance(repair.get("validation"), dict),
        "protected_merge_diagnostic_count": len(diagnostics),
        "ignored_protected_attempt_count": sum(
            int(d.get("ignored_protected_attempt_count", 0))
            for d in diagnostics
        ),
        "event_summary": event_summary,
    })
    if result.get("wake_backend_calls", 0):
        result["bounded_wake_calls"] = int(result["wake_backend_calls"]) <= 2
    return result


def summarize(results: list[dict]) -> dict:
    valid_init = [r for r in results if r.get("init_valid")]
    valid_sched = [r for r in valid_init if r.get("schedule_valid")]
    completed = [r for r in valid_sched if r.get("event_completed")]
    return {
        "n": len(results),
        "init_valid": len(valid_init),
        "schedule_valid": len(valid_sched),
        "pre_due_waiting": sum(
            (r.get("pre_due_step") or {}).get("stop_reason") == "waiting"
            for r in valid_sched
        ),
        "event_completed": len(completed),
        "event_has_recall_context": sum(
            bool(r.get("event_has_recall_context")) for r in completed
        ),
        "final_state_valid": sum(
            bool(r.get("final_state_valid")) for r in completed
        ),
        "first_pass_valid": sum(
            bool(r.get("first_pass_validation_status") == "valid")
            for r in completed
        ),
        "repaired": sum(bool(r.get("repaired")) for r in completed),
        "repair_attempted": sum(
            bool(r.get("repair_attempted")) for r in completed
        ),
        "bounded_wake_call_violations": sum(
            not bool(r.get("bounded_wake_calls")) for r in valid_sched
        ),
        "protected_merge_diagnostics": sum(
            int(r.get("protected_merge_diagnostic_count") or 0)
            for r in completed
        ),
        "ignored_protected_attempts": sum(
            int(r.get("ignored_protected_attempt_count") or 0)
            for r in completed
        ),
    }


def aggregate(results: list[dict]) -> dict:
    summary = summarize(results)
    valid_init = [r for r in results if r.get("init_valid")]
    valid_sched = [r for r in valid_init if r.get("schedule_valid")]
    completed = [r for r in valid_sched if r.get("event_completed")]
    return {
        "summary": summary,
        "hypothesis_results": {
            "H191_behavior_seed_initializes_durable_state": bool(valid_init),
            "H192_schedules_exactly_one_future_recall_event": bool(valid_sched),
            "H193_pre_due_step_waits_without_running": (
                all(
                    (r.get("pre_due_step") or {}).get("stop_reason") == "waiting"
                    and (r.get("pre_due_step") or {}).get("wake_run_count") == 0
                    for r in valid_sched
                ) if valid_sched else False
            ),
            "H194_due_step_delivers_recall_context": (
                all(r.get("event_has_recall_context") for r in completed)
                if completed else False
            ),
            "H195_delayed_wake_produces_valid_state_transition": any(
                r.get("final_state_valid") for r in completed
            ),
            "H196_bounded_repair_auditable": (
                all(
                    bool(r.get("bounded_wake_calls"))
                    and (
                        r.get("first_pass_validation_status") == "valid"
                        or (
                            r.get("repaired")
                            and r.get("has_repair_raw_output")
                            and r.get("has_repair_validation")
                        )
                    )
                    for r in completed
                ) if completed else False
            ),
        },
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "not_before": NOT_BEFORE,
        "pre_due_now": PRE_DUE_NOW.isoformat(),
        "due_now": DUE_NOW.isoformat(),
        "protected_state_fields": sorted(PROTECTED_STATE_FIELDS),
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    results: list[dict] = []
    results_path = EXP_DIR / "results.json"
    if results_path.exists():
        prior = json.loads(results_path.read_text()).get("results", [])
        if isinstance(prior, list):
            results = prior
    completed = {
        int(result.get("replicate", 0))
        for result in results
    }
    for replicate in range(N_REPLICATES):
        if replicate + 1 in completed:
            print(f"{MODEL} r{replicate + 1} already recorded", flush=True)
            continue
        print(f"{MODEL} r{replicate + 1}", flush=True)
        results.append(run_replicate(MODEL, replicate, api_key))
        write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
