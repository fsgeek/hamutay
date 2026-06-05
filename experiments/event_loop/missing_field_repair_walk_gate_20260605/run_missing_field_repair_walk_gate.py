"""Run the preregistered missing-field repair walk gate."""

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
from hamutay.events import resolve_requested_context
from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

EXP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EXP_DIR.parents[2]

MODEL = "deepseek/deepseek-v4-pro"
N_REPLICATES = 4
MAX_TOKENS = 2048
CALL_TIMEOUT_SECONDS = 180
HTTP_TIMEOUT_SECONDS = 60
SEED_MARKERS = ["alpha", "beta", "gamma", "delta"]
BASELINE_OBSERVATIONS = [
    {
        "entry": 1,
        "kind": "baseline",
        "content": "No missing-field repair walk evidence has been collected.",
    }
]
REQUIRED_EDGE_TYPES = {"depends_on", "branches_from", "composes_with"}


def now() -> datetime:
    return datetime.now(timezone.utc)


def safe_model_name(model: str) -> str:
    return model.replace("/", "__").replace(":", "_")


def make_backend(api_key: str, *, label: str) -> OpenAITasteBackend:
    return OpenAITasteBackend(
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


def build_projected_hub(replicate: int) -> dict[str, Any]:
    bridge = ApachetaBridge.from_memory(
        session_id=f"missing-field-repair-walk-{safe_model_name(MODEL)}-r{replicate + 1}",
        model=MODEL,
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
        "fork_run_id": f"missing-field-repair-walk-r{replicate + 1}",
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
    planned_record_ids = sorted(
        str(edge["target_record_id"]) for edge in plan["edges"]
    )
    walk_request = {
        "tool": "walk",
        "from_record_id": applied["fork_run_record_id"],
        "direction": "forward",
        "depth": 1,
        "mode": "adjacent",
    }
    context_results = resolve_requested_context(
        [walk_request],
        prior_states=[],
        bridge=bridge,
    )
    return {
        "bridge": bridge,
        "plan": plan,
        "applied": applied,
        "planned_record_ids": planned_record_ids,
        "walk_request": walk_request,
        "context_results": context_results,
    }


def make_session(
    *,
    log_path: Path,
    api_key: str,
    label: str,
    bridge: ApachetaBridge,
) -> OpenTasteSession:
    return OpenTasteSession(
        model=MODEL,
        backend=make_backend(api_key, label=label),
        log_path=str(log_path),
        experiment_label=label,
        resume=False,
        enable_tools=True,
        memory_base_probability=0.0,
        project_root=PROJECT_ROOT,
        bridge=bridge,
    )


def probe_id_for(replicate: int) -> str:
    marker = SEED_MARKERS[replicate]
    return f"missing-field-repair-walk-{safe_model_name(MODEL)}-r{replicate + 1}-{marker}"


def expected_observation() -> dict[str, Any]:
    return {
        "entry": 2,
        "kind": "direct_walk",
        "content": (
            "Direct follow-up used adjacent walk context and saw 4 endpoints "
            "with depends_on, branches_from, and composes_with edge types."
        ),
    }


def target_object(replicate: int) -> dict[str, Any]:
    return {
        "response": (
            "Walk evidence recorded: four adjacent endpoints with "
            "depends_on, branches_from, and composes_with edges."
        ),
        "probe_id": probe_id_for(replicate),
        "walk_gate_status": "woke",
        "observed_walk_endpoint_count": 4,
        "observed_walk_edge_types": [
            "depends_on",
            "branches_from",
            "composes_with",
        ],
        "observations": [
            *BASELINE_OBSERVATIONS,
            expected_observation(),
        ],
    }


def init_prompt(replicate: int) -> str:
    seeded_object = {
        "response": "Initialized.",
        "probe_id": probe_id_for(replicate),
        "walk_gate_status": "initialized",
        "observations": BASELINE_OBSERVATIONS,
    }
    return f"""
Registered missing-field repair walk gate.
model={MODEL}
replicate={replicate + 1}

Initialize durable top-level state with exactly these working fields:
- probe_id
- walk_gate_status
- observations

Use probe_id: {probe_id_for(replicate)}
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


def direct_followup_prompt(
    *,
    replicate: int,
    walk_request: dict[str, Any],
    context_results: list[dict[str, Any]],
) -> str:
    evidence = {
        "walk_request": walk_request,
        "context_results": context_results,
    }
    return f"""
Registered missing-field repair direct walk evidence follow-up.
model={MODEL}
replicate={replicate + 1}

This is not a scheduled event. The walk evidence below has already been
resolved for you as plain direct-follow-up context:
{json.dumps(evidence, indent=2, default=str)}

Required durable updates:
- Set top-level walk_gate_status to "woke".
- Set top-level observed_walk_endpoint_count to the number of path entries in
  the walk result.
- Set top-level observed_walk_edge_types to the distinct edge_type values you
  saw in the walk path.
- Append a top-level observations entry recording that this direct follow-up
  used adjacent walk context after seeded initialization.
- Preserve probe_id.

Update-time target object: your durable object should use this shape. Replace
only the response text if needed; preserve the other top-level fields exactly.
{json.dumps(target_object(replicate), indent=2)}

Do not put these fields only in visible prose. They must be top-level fields in
the object you produce this cycle.

If the provided context_results do not contain a walk path, set
walk_gate_status to "blocked" and append an observation naming the missing
evidence.

Do not schedule any event. Do not call read, search_project, bash, or clock.
End with think_and_respond.
""".strip()


def repair_prompt(
    *,
    replicate: int,
    current_state: dict[str, Any],
    missing_fields: list[str],
) -> str:
    expected_values = {
        "probe_id": probe_id_for(replicate),
        "walk_gate_status": "woke",
        "observed_walk_endpoint_count": 4,
        "observed_walk_edge_types": [
            "depends_on",
            "branches_from",
            "composes_with",
        ],
        "observations": (
            "Preserve the existing baseline observation and append one "
            "direct_walk observation recording the adjacent walk evidence."
        ),
    }
    return f"""
Missing-field repair turn for replicate {replicate + 1}.

Your previous visible response said the walk evidence was recorded, but the
durable state object did not contain the required graph-evidence update.

Current durable state:
{json.dumps(current_state, indent=2, default=str)}

Missing or incorrect durable fields:
{json.dumps(missing_fields, indent=2)}

Evidence summary:
- The adjacent walk path had 4 entries.
- The distinct edge types were depends_on, branches_from, and composes_with.

Expected field-level values:
{json.dumps(expected_values, indent=2)}

This is not a request to explain the repair in prose. The repair succeeds only
if the missing fields are top-level fields in the object you produce this cycle.
Do not nest the repair inside another object. Do not provide only a narrative.
Preserve the existing probe_id and baseline observation.

Do not call read, search_project, bash, clock, memory_schema, recall, compare,
walk, search_memory, store, annotate_edge, or schedule_event. End with
think_and_respond.
""".strip()


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def init_failure_reasons(state: dict[str, Any], replicate: int) -> list[str]:
    reasons: list[str] = []
    if state.get("probe_id") != probe_id_for(replicate):
        reasons.append("probe_id_missing_or_changed")
    if state.get("walk_gate_status") != "initialized":
        reasons.append("walk_gate_status_not_initialized")
    observations = state.get("observations")
    if not isinstance(observations, list):
        reasons.append("observations_not_list")
    elif not observations:
        reasons.append("observations_empty")
    if isinstance(state.get("state"), dict):
        reasons.append("nested_state_present")
    return reasons


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


def walk_path_from_context(context_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item in context_results:
        request = item.get("request") or {}
        if request.get("tool") != "walk":
            continue
        result = item.get("result") or {}
        path = result.get("path")
        if isinstance(path, list):
            return path
    return []


def state_records_walk_evidence(state: dict[str, Any]) -> bool:
    observations = state.get("observations")
    final_edge_types = state.get("observed_walk_edge_types")
    edge_types = (
        {str(item) for item in final_edge_types}
        if isinstance(final_edge_types, list)
        else set()
    )
    return (
        state.get("walk_gate_status") == "woke"
        and state.get("observed_walk_endpoint_count") == 4
        and REQUIRED_EDGE_TYPES <= edge_types
        and isinstance(observations, list)
        and len(observations) > len(BASELINE_OBSERVATIONS)
    )


def repair_preserves_identity(state: dict[str, Any], replicate: int) -> bool:
    observations = state.get("observations")
    return (
        state.get("probe_id") == probe_id_for(replicate)
        and isinstance(observations, list)
        and bool(observations)
        and observations[0] == BASELINE_OBSERVATIONS[0]
    )


def missing_walk_fields(state: dict[str, Any], replicate: int) -> list[str]:
    missing: list[str] = []
    if state.get("probe_id") != probe_id_for(replicate):
        missing.append("probe_id")
    if state.get("walk_gate_status") != "woke":
        missing.append("walk_gate_status")
    if state.get("observed_walk_endpoint_count") != 4:
        missing.append("observed_walk_endpoint_count")
    final_edge_types = state.get("observed_walk_edge_types")
    edge_types = (
        {str(item) for item in final_edge_types}
        if isinstance(final_edge_types, list)
        else set()
    )
    for edge_type in sorted(REQUIRED_EDGE_TYPES):
        if edge_type not in edge_types:
            missing.append(f"observed_walk_edge_types.{edge_type}")
    observations = state.get("observations")
    if not isinstance(observations, list) or len(observations) <= len(BASELINE_OBSERVATIONS):
        missing.append("observations.appended_direct_walk")
    return missing


def strict_metrics(
    *,
    final_state: dict[str, Any],
    response_text: str,
    records: list[dict[str, Any]],
    context_results: list[dict[str, Any]],
) -> dict[str, Any]:
    path = walk_path_from_context(context_results)
    edge_types = {
        str(step.get("edge_type"))
        for step in path
        if step.get("edge_type") is not None
    }
    response_mentions = response_mentions_walk(response_text)
    durable = state_records_walk_evidence(final_state)
    return {
        "cycle_count": len(records),
        "direct_context_walk_path_count": len(path),
        "direct_context_walk_edge_types": sorted(edge_types),
        "direct_context_has_equivalent_walk_path": (
            len(path) == 4 and REQUIRED_EDGE_TYPES <= edge_types
        ),
        "wake_status_woke": final_state.get("walk_gate_status") == "woke",
        "observed_walk_endpoint_count": final_state.get(
            "observed_walk_endpoint_count"
        ),
        "observed_walk_edge_types": final_state.get("observed_walk_edge_types"),
        "observation_update": (
            isinstance(final_state.get("observations"), list)
            and len(final_state["observations"]) > len(BASELINE_OBSERVATIONS)
        ),
        "state_records_walk_evidence": durable,
        "response_mentions_walk": response_mentions,
        "response_state_mismatch": response_mentions and not durable,
        "final_top_level_keys": sorted(final_state.keys()),
    }


def run_replicate(replicate: int, api_key: str) -> dict[str, Any]:
    safe_model = safe_model_name(MODEL)
    log_path = EXP_DIR / f"{safe_model}_missing_field_repair_r{replicate + 1:02d}.jsonl"
    if log_path.exists():
        raise RuntimeError(f"refusing to overwrite {log_path}")

    projected = build_projected_hub(replicate)
    label = f"missing_field_repair_walk_{safe_model}_r{replicate + 1:02d}"
    session = make_session(
        log_path=log_path,
        api_key=api_key,
        label=label,
        bridge=projected["bridge"],
    )
    result: dict[str, Any] = {
        "model": MODEL,
        "replicate": replicate + 1,
        "log_path": str(log_path.relative_to(PROJECT_ROOT)),
        "fork_run_record_id": projected["applied"]["fork_run_record_id"],
        "planned_record_ids": projected["planned_record_ids"],
        "init_valid": False,
        "init_failure_reasons": [],
        "initial_followup_recorded": False,
        "initial_response_state_mismatch": False,
        "repair_attempted": False,
        "repair_succeeded": False,
        "repair_preserved_identity": False,
        "still_mismatched_after_repair": False,
        "repair_missing_fields": [],
        "error": None,
    }
    try:
        with bounded_call(f"missing-field repair r{replicate + 1} init"):
            session.exchange(init_prompt(replicate), force_memory=None)
        records = load_records(log_path)
        init_state = records[-1].get("state") if records else {}
        init_state = init_state if isinstance(init_state, dict) else {}
        reasons = init_failure_reasons(init_state, replicate)
        result["init_failure_reasons"] = reasons
        result["init_valid"] = not reasons
        if reasons:
            final_record = records[-1] if records else {}
            final_state = final_record.get("state") or {}
            final_state = final_state if isinstance(final_state, dict) else {}
            result.update(
                strict_metrics(
                    final_state=final_state,
                    response_text=final_record.get("response_text", ""),
                    records=records,
                    context_results=projected["context_results"],
                )
            )
            return result

        with bounded_call(f"missing-field repair r{replicate + 1} followup"):
            session.exchange(
                direct_followup_prompt(
                    replicate=replicate,
                    walk_request=projected["walk_request"],
                    context_results=projected["context_results"],
                ),
                force_memory=None,
            )
        records = load_records(log_path)
        followup_record = records[-1] if records else {}
        followup_state = followup_record.get("state") or {}
        followup_state = followup_state if isinstance(followup_state, dict) else {}
        followup_metrics = strict_metrics(
            final_state=followup_state,
            response_text=followup_record.get("response_text", ""),
            records=records,
            context_results=projected["context_results"],
        )
        result["initial_followup_recorded"] = True
        result["initial_response_state_mismatch"] = bool(
            followup_metrics["response_state_mismatch"]
        )
        if followup_metrics["response_state_mismatch"]:
            missing = missing_walk_fields(followup_state, replicate)
            result["repair_missing_fields"] = missing
            result["repair_attempted"] = True
            with bounded_call(f"missing-field repair r{replicate + 1} repair"):
                session.exchange(
                    repair_prompt(
                        replicate=replicate,
                        current_state=followup_state,
                        missing_fields=missing,
                    ),
                    force_memory=None,
                )
    except Exception as exc:  # noqa: BLE001 -- failed replicates are data
        result["error"] = format_error(exc)

    records = load_records(log_path)
    final_record = records[-1] if records else {}
    final_state = final_record.get("state") or {}
    final_state = final_state if isinstance(final_state, dict) else {}
    result.update(
        strict_metrics(
            final_state=final_state,
            response_text=final_record.get("response_text", ""),
            records=records,
            context_results=projected["context_results"],
        )
    )
    result["repair_succeeded"] = bool(
        result.get("repair_attempted")
        and result.get("state_records_walk_evidence")
    )
    result["repair_preserved_identity"] = bool(
        result.get("repair_succeeded")
        and repair_preserves_identity(final_state, replicate)
    )
    result["still_mismatched_after_repair"] = bool(
        result.get("repair_attempted")
        and result.get("response_state_mismatch")
    )
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [result for result in results if result.get("init_valid")]
    mismatched = [
        result for result in valid
        if result.get("initial_response_state_mismatch")
    ]
    successful_repairs = [
        result for result in mismatched
        if result.get("repair_succeeded")
    ]
    return {
        "summary": {
            "n": len(results),
            "init_valid": sum(bool(r.get("init_valid")) for r in results),
            "errors": sum(bool(r.get("error")) for r in results),
            "initial_followups": sum(
                bool(r.get("initial_followup_recorded")) for r in valid
            ),
            "direct_context_equivalent": sum(
                bool(r.get("direct_context_has_equivalent_walk_path"))
                for r in valid
            ),
            "initial_response_state_mismatches": len(mismatched),
            "repair_attempted": sum(
                bool(r.get("repair_attempted")) for r in valid
            ),
            "repair_succeeded": len(successful_repairs),
            "still_mismatched_after_repair": sum(
                bool(r.get("still_mismatched_after_repair")) for r in valid
            ),
        },
        "hypothesis_results": {
            "H144_missing_field_repair_gate_produces_initial_mismatch": bool(
                mismatched
            ),
            "H145_missing_field_repair_recovers_at_least_one_mismatch": bool(
                successful_repairs
            ),
            "H146_missing_field_repair_preserves_prior_identity_fields": (
                all(r.get("repair_preserved_identity") for r in successful_repairs)
                if successful_repairs else False
            ),
            "H147_missing_field_repair_outcomes_distinguish_copy_dependence": all(
                key in result
                for result in results
                for key in (
                    "init_valid",
                    "direct_context_has_equivalent_walk_path",
                    "initial_response_state_mismatch",
                    "repair_attempted",
                    "repair_succeeded",
                    "still_mismatched_after_repair",
                )
            ),
        },
    }


def write_results(results: list[dict[str, Any]]) -> None:
    payload = {
        "model": MODEL,
        "n_replicates": N_REPLICATES,
        "max_tokens": MAX_TOKENS,
        "call_timeout_seconds": CALL_TIMEOUT_SECONDS,
        "http_timeout_seconds": HTTP_TIMEOUT_SECONDS,
        "comparison_baseline": (
            "experiments/event_loop/strict_repair_walk_gate_20260605"
        ),
        "results": results,
        **aggregate(results),
    }
    (EXP_DIR / "results.json").write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set")
    if (EXP_DIR / "results.json").exists():
        raise SystemExit("results.json already exists; refusing to overwrite")

    results = []
    for replicate in range(N_REPLICATES):
        print(f"{MODEL} missing-field repair r{replicate + 1}")
        results.append(run_replicate(replicate, api_key))
    write_results(results)
    payload = json.loads((EXP_DIR / "results.json").read_text())
    print(json.dumps({
        "summary": payload["summary"],
        "hypothesis_results": payload["hypothesis_results"],
    }, indent=2))
    print(f"wrote {EXP_DIR / 'results.json'}")


if __name__ == "__main__":
    main()
