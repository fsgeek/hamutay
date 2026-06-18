"""Longer-horizon sustained event-loop probe."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import importlib.util
import json
import os
import sys
import typing as typing_module
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


JsonDict = dict[str, Any]

EXPERIMENT_ID = "longer_horizon_sustained_loop_20260618"
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
YANANTIN_SRC_ROOT = PROJECT_ROOT.parent / "yanantin" / "src"
TIKSI_SRC_ROOT = PROJECT_ROOT.parent / "tiksi" / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if YANANTIN_SRC_ROOT.exists() and str(YANANTIN_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(YANANTIN_SRC_ROOT))
if TIKSI_SRC_ROOT.exists() and str(TIKSI_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(TIKSI_SRC_ROOT))
if not hasattr(datetime_module, "UTC"):
    datetime_module.UTC = datetime_module.timezone.utc
if not hasattr(typing_module, "Self"):
    from typing_extensions import Self

    typing_module.Self = Self

PROBE_RUN_PATH = (
    ROOT_DIR.parent
    / "live_sustained_loop_provider_readiness_20260617"
    / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
TASK_LABELS = ["alpha", "beta"]


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_sustained_probe_for_longer_horizon",
        PROBE_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {PROBE_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    return module


PROBE = load_probe_module()


def final_artifact_terminal_surface(*, tool_choice: str) -> JsonDict:
    return PROBE.terminal_surface(
        tool_name="write_long_horizon_artifact",
        description=(
            "Write the final long-horizon synthesis. Return response exactly: "
            "long horizon artifact complete"
        ),
        tool_choice=tool_choice,
        properties={
            "response": {
                "type": "string",
                "enum": ["long horizon artifact complete"],
            },
            "artifact_title": {"type": "string"},
            "task_count": {"type": "integer"},
            "completed_task_labels": {
                "type": "array",
                "items": {"type": "string"},
            },
            "conclusion": {"type": "string"},
            "declared_losses": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        required=[
            "response",
            "artifact_title",
            "task_count",
            "completed_task_labels",
            "conclusion",
            "declared_losses",
        ],
        copy_fields=[
            "artifact_title",
            "task_count",
            "completed_task_labels",
            "conclusion",
            "declared_losses",
        ],
    )


def scripted_long_horizon_outputs() -> list[JsonDict]:
    outputs: list[JsonDict] = [
        {
            "response": "live loop probe initialized",
            "probe_status": "ready",
            "open_items": [],
        }
    ]
    for label in TASK_LABELS:
        outputs.extend(
            [
                {
                    "response": "inbound IPC accepted",
                    "inbound_status": f"{label}-accepted",
                    "open_items": [
                        {"kind": "task", "text": f"finish {label}"}
                    ],
                    "continuation_request": {
                        "requested": True,
                        "kind": "session_bound_continuation",
                        "purpose": f"Finish task {label} from <result_record_id>.",
                        "symbolic_context": [
                            {
                                "source": "completed_wake_state",
                                "field": "inbound_status",
                            }
                        ],
                        "label": f"finish-{label}",
                    },
                },
                {
                    "response": "bound continuation complete",
                    "continuation_status": f"{label}-closed",
                    "open_items": [],
                },
                {
                    "response": "housekeeping audit clean",
                    "open_items": [],
                    "housekeeping_audit": {
                        "audit_index": 1,
                        "open_item_count": 0,
                        "status": "clean",
                    },
                },
            ]
        )
    outputs.append(
        {
            "response": "long horizon artifact complete",
            "artifact_title": "Long-Horizon Sustained Loop Synthesis",
            "task_count": 2,
            "completed_task_labels": TASK_LABELS,
            "conclusion": (
                "The sustained loop completed two inbound tasks, their bound "
                "continuations, housekeeping, and final synthesis."
            ),
            "declared_losses": [],
        }
    )
    return outputs


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "task_labels": TASK_LABELS,
            "expected_completed_event_count": 7,
            "expected_event_type_sequence": [
                "inbound_message",
                "self_scheduled_reflection",
                "housekeeping",
                "inbound_message",
                "self_scheduled_reflection",
                "housekeeping",
                "final_artifact_synthesis",
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 8 if live_model_calls else 0,
            "max_estimated_cost_usd": 3.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.longer_horizon_loop_taxonomy.v1",
            "layers": [
                "scheduler",
                "model_output",
                "context_recovery",
                "provider",
                "artifact",
                "declared_loss",
                "inconclusive",
            ],
        },
    }
    for name, payload in artifacts.items():
        PROBE.write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


def initialize_run(
    *,
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
):
    store = PROBE.EventStore(paths.event_log)
    memory = PROBE.LocalMemorySubstrate()
    ledger = PROBE.ActionLedger(paths.action_log)
    frontier = PROBE.RestartFrontierStore(
        frontier_path=paths.frontier_log,
        memory_snapshot_path=paths.memory_snapshot,
    )
    frontier.ensure_run_manifest(
        ledger=ledger,
        run_id=run_id,
        manifest={
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "endpoint": endpoint if live_model_calls else None,
            "model": model,
            "terminal_tool_choice": terminal_tool_choice,
        },
        sandbox={"network": "enabled" if live_model_calls else "disabled"},
    )
    return store, memory, ledger, frontier


def commit_or_stop(
    *,
    paths: Any,
    frontier: Any,
    memory: Any,
    ledger: Any,
    store: Any,
    session: Any,
    run_id: str,
    notes: JsonDict,
) -> JsonDict | None:
    failure = PROBE.commit_frontier(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes=notes,
    )
    if isinstance(failure, dict) and failure.get("layer"):
        return failure
    return None


def append_inbound_event(
    *,
    store: Any,
    session: Any,
    label: str,
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="inbound_message",
        label=f"inbound-{label}",
        purpose=(
            f"Handle inbound IPC task {label}: record acceptance, leave one "
            "open item, and request a framework-bound continuation using "
            "symbolic_context with source completed_wake_state. Return response "
            "exactly: inbound IPC accepted."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=PROBE.inbound_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(session._prior_states[-1][1]),
            }
        ],
    )


def append_housekeeping_event(
    *,
    store: Any,
    session: Any,
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="housekeeping",
        label="housekeeping-clean",
        purpose=(
            "Run a terse housekeeping audit. If the recalled state has no open "
            "items, return response exactly: housekeeping audit clean."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=PROBE.housekeeping_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
        requested_context=[
            {
                "tool": "recall",
                "record_id": str(session._prior_states[-1][1]),
            }
        ],
    )


def append_final_event(
    *,
    store: Any,
    session: Any,
    result_record_ids: list[str],
    terminal_tool_choice: str,
) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="final_artifact_synthesis",
        label="final-synthesis",
        purpose=(
            "Write the final artifact synthesizing completed tasks alpha and "
            "beta. Set task_count to 2, completed_task_labels to ['alpha', "
            "'beta'], and response exactly: long horizon artifact complete."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=final_artifact_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
        requested_context=[
            {"tool": "recall", "record_id": record_id}
            for record_id in result_record_ids
        ],
    )


def read_jsonl(path: Path) -> list[JsonDict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def session_state_by_record_id(path: Path) -> dict[str, JsonDict]:
    return {
        str(record.get("record_id")): record.get("state", {})
        for record in read_jsonl(path)
        if record.get("record_id")
    }


def attempted_terminal_tools(path: Path) -> list[str]:
    tools: list[str] = []
    for record in read_jsonl(path):
        if record.get("record_type") != "event_attempt":
            continue
        surface = record.get("terminal_surface")
        if isinstance(surface, dict):
            tools.append(str(surface.get("tool_name")))
    return tools


def material_outcome_warnings(summary: JsonDict) -> list[JsonDict]:
    warnings = []
    for warning in summary.get("outcome_warnings", []) or []:
        if (
            warning.get("event_type") == "housekeeping"
            and warning.get("no_durable_state_change") is True
            and warning.get("response_state_mismatch") is False
        ):
            continue
        warnings.append(warning)
    return warnings


def required_success(
    summary: JsonDict,
    records: list[JsonDict],
    *,
    paths: Any,
) -> JsonDict:
    completed = [
        record for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]
    completed_types = [str(record.get("event_type")) for record in completed]
    completed_tools = attempted_terminal_tools(paths.attempts_log)
    final_records = [
        record for record in completed
        if record.get("event_type") == "final_artifact_synthesis"
    ]
    final_after = {}
    if final_records:
        final_result_record_id = str(final_records[-1].get("result_record_id"))
        final_after = session_state_by_record_id(paths.session_log).get(
            final_result_record_id,
            {},
        )
    frontier_lines = 0
    checks = {
        "completed_seven_events": len(completed) == 7,
        "two_inbound_events": completed_types.count("inbound_message") == 2,
        "two_continuation_events": (
            completed_types.count("self_scheduled_reflection") == 2
        ),
        "two_housekeeping_events": completed_types.count("housekeeping") == 2,
        "one_final_artifact": completed_types.count("final_artifact_synthesis") == 1,
        "event_type_sequence": completed_types == [
            "inbound_message",
            "self_scheduled_reflection",
            "housekeeping",
            "inbound_message",
            "self_scheduled_reflection",
            "housekeeping",
            "final_artifact_synthesis",
        ],
        "terminal_surface_sequence": completed_tools == [
            "handle_inbound_ipc",
            "complete_bound_continuation",
            "complete_housekeeping_audit",
            "handle_inbound_ipc",
            "complete_bound_continuation",
            "complete_housekeeping_audit",
            "write_long_horizon_artifact",
        ],
        "final_task_count": final_after.get("task_count") == 2,
        "final_labels": final_after.get("completed_task_labels") == TASK_LABELS,
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
        "no_material_outcome_warnings": material_outcome_warnings(summary) == [],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "completed_terminal_surface_tools": completed_tools,
        "final_after_state": final_after,
        "frontier_line_count": frontier_lines,
    }


def finalize_results(
    *,
    paths: Any,
    run_id: str,
    live_model_calls: bool,
    endpoint: str,
    model: str,
    terminal_tool_choice: str,
    store: Any,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    success = required_success(summary, records, paths=paths)
    if paths.frontier_log.exists():
        success["frontier_line_count"] = len(
            [
                line for line in paths.frontier_log.read_text().splitlines()
                if line.strip()
            ]
        )
        success["checks"]["multiple_frontier_updates"] = (
            success["frontier_line_count"] >= 8
        )
    else:
        success["checks"]["multiple_frontier_updates"] = False
    failures = PROBE.collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.longer_horizon_sustained_loop.v1",
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model,
        "terminal_tool_choice": terminal_tool_choice,
        "classification": classification,
        "success": success,
        "event_summary": summary,
        "failure_attribution": failures,
        "evidence": {
            "session_log": paths.session_log.name,
            "event_log": paths.event_log.name,
            "attempts_log": paths.attempts_log.name,
            "restart_frontier": paths.frontier_log.name,
            "memory_snapshot": paths.memory_snapshot.name,
            "action_log": paths.action_log.name,
        },
    }
    if extra:
        results.update(extra)
    PROBE.write_json(paths.output_root / "results.json", results)
    return results


def run_probe(
    *,
    output_root: Path = ROOT_DIR,
    overwrite: bool = False,
    live_model_calls: bool = False,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    terminal_tool_choice: str | None = None,
    backend: Any | None = None,
    run_id: str | None = None,
) -> JsonDict:
    if live_model_calls and not api_key and backend is None:
        raise ValueError("api_key is required for live model calls")
    paths = PROBE.prepare_output_root(output_root, overwrite=overwrite)
    write_preregistration_artifacts(output_root, live_model_calls=live_model_calls)
    run_id = run_id or str(uuid4())
    terminal_tool_choice = terminal_tool_choice or PROBE.default_terminal_tool_choice(
        endpoint
    )
    if backend is None:
        if live_model_calls:
            backend = PROBE.make_live_backend(
                endpoint=endpoint,
                api_key=api_key or "",
                max_tokens=max_tokens,
            )
        else:
            backend = PROBE.ScriptedTerminalBackend(scripted_long_horizon_outputs())

    PROBE.write_json(
        paths.output_root / "config.json",
        {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "live_model_calls": live_model_calls,
            "endpoint": endpoint if live_model_calls else None,
            "model": model,
            "max_tokens": max_tokens,
            "terminal_tool_choice": terminal_tool_choice,
        },
    )
    store, memory, ledger, frontier = initialize_run(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
    )
    session = PROBE.make_session(
        paths=paths,
        backend=backend,
        model=model,
        resume=False,
    )
    seed_request = {
        "event": "initialize_long_horizon_loop",
        "instruction": (
            "Initialize durable state for a longer-horizon event-loop probe."
        ),
        "required_output": {
            "response": "<brief initialization note>",
            "probe_status": "ready",
            "open_items": [],
        },
    }
    try:
        session.exchange(
            json.dumps(seed_request, indent=2, sort_keys=True),
            terminal_surface=PROBE.seed_terminal_surface(
                tool_choice=terminal_tool_choice
            ),
            force_memory=None,
        )
    except Exception as exc:
        PROBE.record_failure(
            paths,
            PROBE.classify_exception(exc, stage="seed_exchange"),
            request=seed_request,
        )
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "seed_exchange"},
        )
    commit_or_stop(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes={"boundary": "after seed"},
    )

    continuation_record_ids: list[str] = []
    for label in TASK_LABELS:
        append_inbound_event(
            store=store,
            session=session,
            label=label,
            terminal_tool_choice=terminal_tool_choice,
        )
        inbound_result = PROBE.run_attributed_event(
            session=session,
            store=store,
            paths=paths,
            auto_continuations=True,
            terminal_tool_choice=terminal_tool_choice,
        )
        if inbound_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                extra={"stopped_after": f"inbound_{label}"},
            )
        if isinstance(inbound_result.get("continuation_binding_failure"), dict):
            PROBE.record_failure(
                paths,
                inbound_result["continuation_binding_failure"],
                result=inbound_result,
            )
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                extra={"stopped_after": f"continuation_binding_{label}"},
            )
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after inbound {label}"},
        )

        continuation_result = PROBE.run_attributed_event(
            session=session,
            store=store,
            paths=paths,
            auto_continuations=False,
            terminal_tool_choice=terminal_tool_choice,
        )
        if continuation_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                extra={"stopped_after": f"continuation_{label}"},
            )
        continuation_record_ids.append(str(continuation_result["result_record_id"]))
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after continuation {label}"},
        )

        append_housekeeping_event(
            store=store,
            session=session,
            terminal_tool_choice=terminal_tool_choice,
        )
        housekeeping_result = PROBE.run_attributed_event(
            session=session,
            store=store,
            paths=paths,
            auto_continuations=False,
            terminal_tool_choice=terminal_tool_choice,
        )
        if housekeeping_result.get("status") != "completed":
            return finalize_results(
                paths=paths,
                run_id=run_id,
                live_model_calls=live_model_calls,
                endpoint=endpoint,
                model=model,
                terminal_tool_choice=terminal_tool_choice,
                store=store,
                extra={"stopped_after": f"housekeeping_{label}"},
            )
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": f"after housekeeping {label}"},
        )

    append_final_event(
        store=store,
        session=session,
        result_record_ids=continuation_record_ids,
        terminal_tool_choice=terminal_tool_choice,
    )
    final_result = PROBE.run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final_result.get("status") == "completed":
        commit_or_stop(
            paths=paths,
            frontier=frontier,
            memory=memory,
            ledger=ledger,
            store=store,
            session=session,
            run_id=run_id,
            notes={"boundary": "after final synthesis"},
        )
    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--terminal-tool-choice", default=None)
    args = parser.parse_args(argv)
    if args.write_prereg:
        write_preregistration_artifacts(args.output_root, live_model_calls=args.live)
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}))
        return 0
    if not args.live and not args.dry_run:
        parser.error("choose --dry-run or --live")
    result = run_probe(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=os.environ.get(args.api_key_env, "") if args.live else None,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        terminal_tool_choice=args.terminal_tool_choice,
    )
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
