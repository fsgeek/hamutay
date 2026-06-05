"""Run the preregistered scheduled walk strict-continuity gate."""

from __future__ import annotations

import json
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from hamutay.apacheta_bridge import ApachetaBridge
from hamutay.event_policies import (
    apply_fork_run_graph_plan,
    build_fork_run_graph_plan,
)
from hamutay.events import (
    EventStore,
    default_event_log_path,
    run_next_event,
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
EXPECTED_WAKE_CYCLE = 3
SEED_MARKERS = ["alpha", "beta", "gamma", "delta"]
BASELINE_OBSERVATION = {
    "entry": 1,
    "kind": "baseline",
    "content": "No scheduled scaffold walk evidence has been collected.",
}
BASELINE_OBSERVATIONS = [BASELINE_OBSERVATION]
REQUIRED_EDGE_TYPES = {"depends_on", "branches_from", "composes_with"}
DISALLOWED_DELETIONS = {"probe_id", "cycle"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


class CountingBackend:
    """Count provider calls while preserving the backend interface."""

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
    """Raised when a provider or harness call exceeds the runner budget."""


def _timeout_handler(signum, frame) -> None:  # noqa: ARG001
    raise CallTimeoutError(f"call exceeded {CALL_TIMEOUT_SECONDS}s")


class bounded_call:
    """Bound one blocking provider/harness call in the experiment runner."""

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


def store_state(
    bridge: ApachetaBridge,
    record_id: str,
    *,
    cycle: int,
    role: str,
) -> UUID:
    rid = UUID(record_id)
    bridge._prior_id = None
    bridge.store_open_state(
        {"cycle": cycle, "role": role},
        cycle=cycle,
        record_id=rid,
        timestamp=now(),
    )
    return rid


def build_projected_hub(model: str, replicate: int) -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(
        session_id=f"strict-continuity-walk-{safe_model_name(model)}-r{replicate + 1}",
        model=model,
    )
    root = store_state(
        bridge,
        "00000000-0000-0000-0000-000000000001",
        cycle=2,
        role="coordinator",
    )
    branch_a = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000000aa",
        cycle=3,
        role="branch-a",
    )
    branch_b = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000000bb",
        cycle=3,
        role="branch-b",
    )
    join = store_state(
        bridge,
        "00000000-0000-0000-0000-0000000000cc",
        cycle=4,
        role="join",
    )
    final_run_record = {
        "fork_run_id": f"strict-continuity-walk-r{replicate + 1}",
        "classification": "joined",
        "scheduled_by_cycle": 2,
        "scheduled_by_record_id": str(root),
        "branch_labels": ["branch-a", "branch-b"],
        "branch_events": {
            "branch-a": {
                "event_id": "event-a",
                "terminal_status": "completed",
                "result_record_id": str(branch_a),
            },
            "branch-b": {
                "event_id": "event-b",
                "terminal_status": "completed",
                "result_record_id": str(branch_b),
            },
        },
        "join_result_record_id": str(join),
    }
    plan = build_fork_run_graph_plan(final_run_record)
    applied = apply_fork_run_graph_plan(bridge=bridge, plan=plan, cycle=5)
    bridge._prior_id = None
    return {
        "bridge": bridge,
        "plan": plan,
        "applied": applied,
        "planned_record_ids": sorted(
            str(edge["target_record_id"]) for edge in plan["edges"]
        ),
    }


def make_session(
    *,
    model: str,
    log_path: Path,
    label: str,
    bridge: ApachetaBridge,
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
        bridge=bridge,
    )


def probe_id_for(model: str, replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"strict-continuity-walk-{safe_model_name(model)}-r{replicate + 1}-{marker}"


def init_prompt(model: str, replicate: int) -> str:
    seeded_object = {
        "response": "Initialized.",
        "probe_id": probe_id_for(model, replicate),
        "walk_gate_status": "initialized",
        "observations": BASELINE_OBSERVATIONS,
    }
    return f"""
Registered strict continuity scheduled walk gate.
model={model}
replicate={replicate + 1}

Initialize durable top-level state with exactly these working fields:
- probe_id
- walk_gate_status
- observations

Use probe_id: {probe_id_for(model, replicate)}
Set walk_gate_status to "initialized".
Set observations to:
{json.dumps(BASELINE_OBSERVATIONS, indent=2)}

Behavior seed: your durable object should use this shape. Replace only the
response text if needed; preserve the other top-level fields exactly.
{json.dumps(seeded_object, indent=2)}

Do not put these fields only in visible prose. They must be top-level fields in
the object you produce this cycle.

Do not schedule an event in this cycle. Do not call read, search_project, bash,
or clock. End with think_and_respond.
""".strip()


def schedule_prompt(
    *,
    model: str,
    replicate: int,
    fork_run_record_id: str,
) -> str:
    requested_context = [
        {
            "tool": "walk",
            "from_record_id": fork_run_record_id,
            "direction": "forward",
            "depth": 1,
            "mode": "adjacent",
        }
    ]
    label = f"strict-continuity-walk-{safe_model_name(model)}-r{replicate + 1}"
    purpose = """
You are the scheduled wake for the strict continuity walk gate. Inspect the
event envelope context_results. They should contain a walk path from a fork-run
graph record.

Required durable wake updates:
- Set top-level walk_gate_status to "woke".
- Set top-level observed_walk_endpoint_count to the number of path entries in
  the walk result.
- Set top-level observed_walk_edge_types to the distinct edge_type values you
  saw in the walk path.
- Append a top-level observations entry recording that the scheduled wake used
  adjacent walk context.
- Preserve probe_id.
- Preserve the baseline observation.

Do not recursively schedule any event. If context_results do not contain a walk
path, set walk_gate_status to "blocked" and append an observation naming the
missing evidence.
""".strip()
    return f"""
Registered strict continuity scheduled walk scheduling cycle.
model={model}
replicate={replicate + 1}

Call schedule_event exactly once and wait for its result. Use exactly this
requested_context:
{json.dumps(requested_context, indent=2)}

Use label: {label}

Event purpose:
{purpose}

After the schedule_event result returns, set walk_gate_status to "scheduled" and
end with think_and_respond. Do not claim scheduling succeeded unless the tool
result contains an event_id. Do not call read, search_project, bash, or clock.
""".strip()


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def init_failure_reasons(state: dict, model: str, replicate: int) -> list[str]:
    reasons: list[str] = []
    if state.get("probe_id") != probe_id_for(model, replicate):
        reasons.append("probe_id_missing_or_changed")
    if state.get("walk_gate_status") != "initialized":
        reasons.append("walk_gate_status_not_initialized")
    observations = state.get("observations")
    if not isinstance(observations, list):
        reasons.append("observations_not_list")
    elif BASELINE_OBSERVATION not in observations:
        reasons.append("baseline_observation_missing")
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


def response_mentions_walk(response_text: str) -> bool:
    lowered = response_text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "walk",
            "graph",
            "path",
            "endpoint",
            "context_results",
            "adjacent",
        )
    )


def event_summary_for(path: Path) -> dict:
    store = EventStore(path)
    return summarize_event_log(store.read_records())


def latest_completed_event(path: Path) -> dict:
    records = load_records(path)
    completed = [record for record in records if record.get("status") == "completed"]
    return completed[-1] if completed else {}


def context_walk_path(event_record: dict) -> list[dict]:
    for item in event_record.get("context_results") or []:
        request = item.get("request") or {}
        if request.get("tool") != "walk":
            continue
        result = item.get("result") or {}
        path = result.get("path")
        if isinstance(path, list):
            return path
    return []


def direct_walk_observation() -> dict[str, Any]:
    return {
        "entry": 2,
        "kind": "scheduled_walk",
        "content": (
            "Scheduled wake used adjacent walk context and saw 4 endpoints "
            "with depends_on, branches_from, and composes_with edge types."
        ),
    }


def strict_target_object(
    *,
    expected_probe_id: str,
    expected_cycle: int,
) -> dict[str, Any]:
    return {
        "response": (
            "Scheduled walk evidence recorded while preserving continuity: "
            "four adjacent endpoints with depends_on, branches_from, and "
            "composes_with edges."
        ),
        "cycle": expected_cycle,
        "probe_id": expected_probe_id,
        "walk_gate_status": "woke",
        "observed_walk_endpoint_count": 4,
        "observed_walk_edge_types": [
            "depends_on",
            "branches_from",
            "composes_with",
        ],
        "observations": [
            BASELINE_OBSERVATION,
            direct_walk_observation(),
        ],
    }


def evidence_failures(state: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if state.get("walk_gate_status") != "woke":
        failures.append("walk_gate_status")
    if state.get("observed_walk_endpoint_count") != 4:
        failures.append("observed_walk_endpoint_count")
    final_edge_types = state.get("observed_walk_edge_types")
    edge_types = (
        {str(item) for item in final_edge_types}
        if isinstance(final_edge_types, list)
        else set()
    )
    for edge_type in sorted(REQUIRED_EDGE_TYPES):
        if edge_type not in edge_types:
            failures.append(f"observed_walk_edge_types.{edge_type}")
    observations = state.get("observations")
    if not isinstance(observations, list) or not any(
        isinstance(item, dict) and item.get("kind") == "scheduled_walk"
        for item in observations
    ):
        failures.append("observations.scheduled_walk")
    return failures


def deleted_regions(raw_output: dict[str, Any]) -> set[str]:
    raw_deleted = raw_output.get("deleted_regions")
    if not isinstance(raw_deleted, list):
        return set()
    return {str(item) for item in raw_deleted}


def continuity_failures(
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
    observations = state.get("observations")
    if not isinstance(observations, list) or BASELINE_OBSERVATION not in observations:
        failures.append("baseline_observation_missing")
    disallowed = sorted(deleted_regions(raw_output) & DISALLOWED_DELETIONS)
    for key in disallowed:
        failures.append(f"deleted_regions.{key}")
    return failures


class StrictContinuityStateValidator:
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
        del record_id, timestamp, prior_state
        evidence = evidence_failures(state)
        continuity = continuity_failures(
            state,
            raw_output,
            expected_probe_id=self.expected_probe_id,
            expected_cycle=self.expected_cycle,
        )
        valid = not evidence and not continuity
        return {
            "valid": valid,
            "status": "valid" if valid else "invalid",
            "validator": "scheduled_walk_strict_continuity_validator",
            "cycle": cycle,
            "expected_cycle": self.expected_cycle,
            "expected_probe_id": self.expected_probe_id,
            "evidence_valid": not evidence,
            "continuity_valid": not continuity,
            "evidence_failures": evidence,
            "continuity_failures": continuity,
            "deleted_regions": sorted(deleted_regions(raw_output)),
            "response_mentions_walk": response_mentions_walk(response_text),
        }


class FullStrictTargetRepairBuilder:
    def __init__(self, *, expected_probe_id: str, expected_cycle: int):
        self.expected_probe_id = expected_probe_id
        self.expected_cycle = expected_cycle

    def build_repair_prompt(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
        validation: dict,
    ) -> str:
        del cycle, record_id, timestamp, prior_state
        return f"""
Strict scheduled-wake validation repair turn.

Your previous scheduled-wake response claimed graph-walk evidence was recorded,
but the durable state failed strict validation.

Strict validation requires both:
- graph-walk evidence fields; and
- continuity preservation fields.

First-pass response:
{response_text}

First-pass raw output:
{json.dumps(raw_output, indent=2, default=str)}

Current durable state:
{json.dumps(state, indent=2, default=str)}

Validation result:
{json.dumps(validation, indent=2, default=str)}

Complete target durable object:
{json.dumps(
            strict_target_object(
                expected_probe_id=self.expected_probe_id,
                expected_cycle=self.expected_cycle,
            ),
            indent=2,
            default=str,
        )}

Produce this durable object shape now. Replace only the response text if
needed; preserve every other top-level field exactly. Do not put probe_id,
cycle, observations, or walk evidence only in prose. They must be top-level
fields in the object you produce now.

Do not include probe_id or cycle in deleted_regions.

Do not call read, search_project, bash, clock, memory_schema, recall, compare,
walk, search_memory, store, annotate_edge, or schedule_event. End with
think_and_respond.
""".strip()


def validation_artifact(records: list[dict]) -> dict:
    if not records:
        return {}
    validation = records[-1].get("state_validation")
    if not isinstance(validation, dict):
        return {}
    if validation.get("status") == "repaired":
        repair = validation.get("repair")
        if isinstance(repair, dict):
            nested = repair.get("validation")
            if isinstance(nested, dict):
                artifact = nested.get("artifact")
                if isinstance(artifact, dict):
                    return artifact
    first_pass = validation.get("first_pass")
    if isinstance(first_pass, dict):
        artifact = first_pass.get("artifact")
        if isinstance(artifact, dict):
            return artifact
    return {}


def strict_metrics(
    *,
    final_state: dict,
    response_text: str,
    records: list[dict],
    event_path: Path,
    expected_probe_id: str,
    expected_cycle: int,
) -> dict:
    observations = final_state.get("observations")
    attempts = schedule_attempts(records)
    valid_attempts = [attempt for attempt in attempts if is_valid_schedule_attempt(attempt)]
    events = scheduled_events_in(records)
    completed = latest_completed_event(event_path)
    path = context_walk_path(completed)
    edge_types = {
        str(step.get("edge_type"))
        for step in path
        if step.get("edge_type") is not None
    }
    final_edge_types = final_state.get("observed_walk_edge_types")
    if isinstance(final_edge_types, list):
        final_edge_types_set = {str(item) for item in final_edge_types}
    else:
        final_edge_types_set = set()

    state_evidence_failures = evidence_failures(final_state)
    final_raw_output = records[-1].get("raw_output") if records else {}
    final_raw_output = final_raw_output if isinstance(final_raw_output, dict) else {}
    state_continuity_failures = continuity_failures(
        final_state,
        final_raw_output,
        expected_probe_id=expected_probe_id,
        expected_cycle=expected_cycle,
    )
    response_mentions = response_mentions_walk(response_text)
    validation = records[-1].get("state_validation") if records else None
    validation = validation if isinstance(validation, dict) else {}
    first_pass = validation.get("first_pass") or {}
    repair = validation.get("repair") or {}
    artifact = validation_artifact(records)

    return {
        "schedule_cycle_recorded": len(records) >= 2,
        "schedule_attempt_count": len(attempts),
        "valid_schedule_attempts": len(valid_attempts),
        "malformed_schedule_attempts": len(attempts) - len(valid_attempts),
        "event_count_in_cycle_log": len(events),
        "walk_context_event_count": sum(
            any((ctx or {}).get("tool") == "walk" for ctx in event.get("requested_context", []))
            for event in events
        ),
        "wake_status_woke": final_state.get("walk_gate_status") == "woke",
        "observed_walk_endpoint_count": final_state.get(
            "observed_walk_endpoint_count"
        ),
        "observed_walk_edge_types": final_state.get("observed_walk_edge_types"),
        "observed_walk_edge_types_set": sorted(final_edge_types_set),
        "observation_update": (
            isinstance(observations, list)
            and len(observations) > len(BASELINE_OBSERVATIONS)
        ),
        "event_context_walk_path_count": len(path),
        "event_context_walk_edge_types": sorted(edge_types),
        "event_context_has_walk_path": bool(path),
        "evidence_valid": not state_evidence_failures,
        "continuity_valid": not state_continuity_failures,
        "strict_valid": not state_evidence_failures and not state_continuity_failures,
        "evidence_failures": state_evidence_failures,
        "continuity_failures": state_continuity_failures,
        "probe_id_preserved": final_state.get("probe_id") == expected_probe_id,
        "cycle_preserved": final_state.get("cycle") == expected_cycle,
        "baseline_preserved": (
            isinstance(observations, list)
            and BASELINE_OBSERVATION in observations
        ),
        "disallowed_deletions": sorted(
            deleted_regions(final_raw_output) & DISALLOWED_DELETIONS
        ),
        "response_mentions_walk": response_mentions,
        "response_state_mismatch": (
            response_mentions
            and (bool(state_evidence_failures) or bool(state_continuity_failures))
        ),
        "state_validation_status": validation.get("status"),
        "first_pass_validation_status": first_pass.get("status"),
        "first_pass_artifact": (
            first_pass.get("artifact") if isinstance(first_pass, dict) else None
        ),
        "repair_attempted": bool(validation.get("repair_attempted")),
        "repair_status": repair.get("status"),
        "repair_artifact": artifact,
        "has_repair_raw_output": isinstance(repair.get("raw_output"), dict),
        "has_repair_validation": isinstance(repair.get("validation"), dict),
        "repaired": validation.get("status") == "repaired",
        "first_pass_valid": validation.get("status") == "valid",
        "unrepaired_or_failed": validation.get("status") in {
            "unrepaired",
            "repair_failed",
            "validator_failed",
        },
        "recursive_scheduling_count": max(0, len(events) - 1),
        "final_top_level_keys": sorted(final_state.keys()),
    }


def run_replicate(model: str, replicate: int, api_key: str) -> dict:
    safe_model = safe_model_name(model)
    log_path = EXP_DIR / f"{safe_model}_r{replicate + 1:02d}.jsonl"
    event_path = default_event_log_path(log_path)
    if log_path.exists() or event_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path} or {event_path}")

    projected = build_projected_hub(model, replicate)
    label = f"scheduled_walk_strict_continuity_{safe_model}_r{replicate + 1:02d}"
    backend = make_backend(api_key, label=label)
    session = make_session(
        model=model,
        log_path=log_path,
        label=label,
        bridge=projected["bridge"],
        backend=backend,
    )
    expected_probe_id = probe_id_for(model, replicate)
    result: dict[str, Any] = {
        "model": model,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "event_log_path": str(event_path.relative_to(PROJECT_ROOT)),
        "fork_run_record_id": projected["applied"]["fork_run_record_id"],
        "planned_record_ids": projected["planned_record_ids"],
        "expected_probe_id": expected_probe_id,
        "expected_wake_cycle": EXPECTED_WAKE_CYCLE,
        "init_valid": False,
        "init_failure_reasons": [],
        "error": None,
        "cycle_count": 0,
        "event_persisted": False,
        "event_completed": False,
        "context_error_count": 0,
        "event_result_status": None,
        "wake_backend_calls": 0,
        "bounded_wake_calls": True,
    }
    try:
        with bounded_call(f"{model} r{replicate + 1} init"):
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
            final_state = final_state if isinstance(final_state, dict) else {}
            result["cycle_count"] = len(records)
            result.update(
                strict_metrics(
                    final_state=final_state,
                    response_text=final_record.get("response_text", ""),
                    records=records,
                    event_path=event_path,
                    expected_probe_id=expected_probe_id,
                    expected_cycle=EXPECTED_WAKE_CYCLE,
                )
            )
            return result

        with bounded_call(f"{model} r{replicate + 1} schedule"):
            session.exchange(
                schedule_prompt(
                    model=model,
                    replicate=replicate,
                    fork_run_record_id=projected["applied"]["fork_run_record_id"],
                ),
                force_memory=None,
            )
        records = load_records(log_path)
        if scheduled_events_in(records):
            store = EventStore(event_path)
            session._state_validator = StrictContinuityStateValidator(
                expected_probe_id=expected_probe_id,
                expected_cycle=EXPECTED_WAKE_CYCLE,
            )
            session._state_repair_builder = FullStrictTargetRepairBuilder(
                expected_probe_id=expected_probe_id,
                expected_cycle=EXPECTED_WAKE_CYCLE,
            )
            calls_before_wake = backend.calls
            with bounded_call(f"{model} r{replicate + 1} wake"):
                event_result = run_next_event(session, store)
            result["wake_backend_calls"] = backend.calls - calls_before_wake
            result["bounded_wake_calls"] = result["wake_backend_calls"] <= 2
            result["event_result_status"] = event_result.get("status")
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(exc)

    records = load_records(log_path)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    result["cycle_count"] = len(records)
    if result.get("wake_backend_calls", 0):
        result["bounded_wake_calls"] = int(result["wake_backend_calls"]) <= 2
    result.update(
        strict_metrics(
            final_state=final_state,
            response_text=final_record.get("response_text", ""),
            records=records,
            event_path=event_path,
            expected_probe_id=expected_probe_id,
            expected_cycle=EXPECTED_WAKE_CYCLE,
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
        "walk_context_event_count": sum(
            int(r.get("walk_context_event_count") or 0) for r in valid
        ),
        "event_completed": sum(bool(r.get("event_completed")) for r in valid),
        "context_errors": sum(int(r.get("context_error_count") or 0) for r in valid),
        "event_context_has_walk_path": sum(
            bool(r.get("event_context_has_walk_path")) for r in valid
        ),
        "evidence_valid": sum(bool(r.get("evidence_valid")) for r in valid),
        "continuity_valid": sum(bool(r.get("continuity_valid")) for r in valid),
        "strict_valid": sum(bool(r.get("strict_valid")) for r in valid),
        "probe_id_preserved": sum(bool(r.get("probe_id_preserved")) for r in valid),
        "cycle_preserved": sum(bool(r.get("cycle_preserved")) for r in valid),
        "baseline_preserved": sum(bool(r.get("baseline_preserved")) for r in valid),
        "first_pass_valid": sum(bool(r.get("first_pass_valid")) for r in valid),
        "repaired": sum(bool(r.get("repaired")) for r in valid),
        "repair_attempted": sum(bool(r.get("repair_attempted")) for r in valid),
        "bounded_wake_call_violations": sum(
            not bool(r.get("bounded_wake_calls")) for r in valid
        ),
        "response_state_mismatches": sum(
            bool(r.get("response_state_mismatch")) for r in valid
        ),
        "recursive_scheduling_count": sum(
            int(r.get("recursive_scheduling_count") or 0) for r in group
        ),
    }


def aggregate(results: list[dict]) -> dict:
    summary = summarize_group(results)
    completed = [r for r in results if r.get("event_completed")]
    repaired = [r for r in completed if r.get("repaired")]
    failed_repairs = [
        r for r in results
        if r.get("repair_attempted") and not r.get("repaired")
    ]
    accepted = [
        r for r in completed
        if r.get("state_validation_status") in {"valid", "repaired"}
    ]
    return {
        "summary": summary,
        "hypothesis_results": {
            "H168_strict_validator_detects_first_pass_failures": (
                all(
                    r.get("first_pass_validation_status") == "invalid"
                    for r in completed
                ) if completed else False
            ),
            "H169_at_least_one_strict_repair_succeeds": any(
                r.get("strict_valid") and r.get("repaired") for r in completed
            ),
            "H170_every_accepted_state_preserves_continuity": (
                all(r.get("continuity_valid") for r in accepted)
                if accepted else True
            ),
            "H171_unrepaired_strict_failures_not_silently_accepted": (
                all(r.get("unrepaired_or_failed") for r in failed_repairs)
                if failed_repairs else True
            ),
            "H172_strict_repair_bounded": all(
                bool(r.get("bounded_wake_calls")) for r in results
            ),
            "diagnostic_context_resolved": (
                all(
                    r.get("context_error_count") == 0
                    and r.get("event_context_has_walk_path")
                    and r.get("event_context_walk_path_count") == 4
                    for r in completed
                ) if completed else False
            ),
            "diagnostic_repaired_wakes_auditable": (
                all(
                    r.get("has_repair_raw_output")
                    and r.get("has_repair_validation")
                    for r in repaired
                ) if repaired else True
            ),
        },
    }


def write_results(results: list[dict]) -> None:
    payload = {
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "call_timeout_seconds": CALL_TIMEOUT_SECONDS,
        "http_timeout_seconds": HTTP_TIMEOUT_SECONDS,
        "expected_wake_cycle": EXPECTED_WAKE_CYCLE,
        "results": results,
        "summary": aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    model_filter = os.environ.get("MODEL_FILTER")
    replicate_filter = os.environ.get("REPLICATE_FILTER")
    selected_models = [MODEL] if model_filter is None or model_filter == MODEL else []
    selected_replicates = [
        replicate for replicate in range(N_REPLICATES)
        if replicate_filter is None or int(replicate_filter) == replicate + 1
    ]

    results: list[dict] = []
    results_path = EXP_DIR / "results.json"
    if results_path.exists():
        payload = json.loads(results_path.read_text())
        prior = payload.get("results", [])
        if isinstance(prior, list):
            results = prior
    completed_keys = {
        (result.get("model"), int(result.get("replicate", 0)))
        for result in results
    }
    for model in selected_models:
        for replicate in selected_replicates:
            if (model, replicate + 1) in completed_keys:
                print(f"{model} r{replicate + 1} already recorded", flush=True)
                continue
            print(f"{model} r{replicate + 1}", flush=True)
            result = run_replicate(model, replicate, api_key)
            results.append(result)
            completed_keys.add((model, replicate + 1))
            write_results(results)
    print(json.dumps(aggregate(results), indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
