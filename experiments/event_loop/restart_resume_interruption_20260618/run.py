"""Restart/resume interruption probe for the event-loop substrate."""

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

EXPERIMENT_ID = "restart_resume_interruption_20260618"
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
YANANTIN_SRC_ROOT = PROJECT_ROOT.parent / "yanantin" / "src"
TIKSI_SRC_ROOT = PROJECT_ROOT.parent / "tiksi" / "src"
for path in (PROJECT_ROOT, SRC_ROOT, YANANTIN_SRC_ROOT, TIKSI_SRC_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
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


def load_probe_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "live_sustained_probe_for_restart_resume",
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


def scripted_outputs() -> list[JsonDict]:
    return [
        {
            "response": "live loop probe initialized",
            "probe_status": "ready",
            "open_items": [],
        },
        {
            "response": "accepted inbound IPC work",
            "inbound_status": "accepted",
            "open_items": [{"kind": "todo", "text": "finish inbound work"}],
            "continuation_request": {
                "requested": True,
                "kind": "session_bound_continuation",
                "purpose": "Finish inbound work from <result_record_id>.",
                "symbolic_context": [
                    {"source": "completed_wake_state", "field": "inbound_status"}
                ],
                "label": "finish-inbound-work",
            },
        },
        {
            "response": "bound continuation complete",
            "continuation_status": "completed",
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
            "interruption_point": "after housekeeping pending event is claimed running",
            "expected_recovered_event_type": "housekeeping",
            "expected_completed_event_types": [
                "inbound_message",
                "self_scheduled_reflection",
                "housekeeping",
            ],
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 4 if live_model_calls else 0,
            "max_estimated_cost_usd": 2.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.restart_resume_interruption_taxonomy.v1",
            "layers": [
                "restart_frontier",
                "event_lifecycle",
                "context_reconstruction",
                "scheduler",
                "model_output",
                "provider",
                "artifact",
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


def commit_frontier(
    paths: Any,
    frontier: Any,
    memory: Any,
    ledger: Any,
    store: Any,
    session: Any,
    run_id: str,
    notes: JsonDict,
) -> None:
    PROBE.commit_frontier(
        paths=paths,
        frontier=frontier,
        memory=memory,
        ledger=ledger,
        store=store,
        session=session,
        run_id=run_id,
        notes=notes,
    )


def append_inbound(store: Any, session: Any, terminal_tool_choice: str) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="inbound_message",
        label="inbound-ipc",
        purpose=(
            "Handle an inbound IPC message, preserve open work, and request a "
            "framework-bound continuation."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=PROBE.inbound_terminal_surface(
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[
            {"tool": "recall", "record_id": str(session._prior_states[-1][1])}
        ],
    )


def append_housekeeping(store: Any, session: Any, terminal_tool_choice: str) -> JsonDict:
    return PROBE.append_probe_event(
        store,
        event_type="housekeeping",
        label="interrupted-housekeeping",
        purpose=(
            "Run a housekeeping audit after restart recovery. Return response "
            "exactly: housekeeping audit clean."
        ),
        scheduled_by_cycle=session.cycle,
        scheduled_by_record_id=session._prior_states[-1][1],
        terminal_surface=PROBE.housekeeping_terminal_surface(
            tool_choice=terminal_tool_choice,
        ),
        requested_context=[
            {"tool": "recall", "record_id": str(session._prior_states[-1][1])}
        ],
    )


def read_jsonl(path: Path) -> list[JsonDict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def event_histories(records: list[JsonDict]) -> dict[str, list[str]]:
    histories: dict[str, list[str]] = {}
    for record in records:
        event_id = record.get("event_id")
        status = record.get("status")
        if event_id and status:
            histories.setdefault(str(event_id), []).append(str(status))
    return histories


def completed_events(records: list[JsonDict]) -> list[JsonDict]:
    return [
        record
        for record in records
        if record.get("record_type") == "event_status"
        and record.get("status") == "completed"
    ]


def session_record_ids(path: Path) -> set[str]:
    return {
        str(record.get("record_id"))
        for record in read_jsonl(path)
        if record.get("record_id")
    }


def required_success(
    summary: JsonDict,
    records: list[JsonDict],
    *,
    paths: Any,
    recovered_records: list[JsonDict],
    suppressed_records: list[JsonDict],
    interrupted_event_id: str | None,
) -> JsonDict:
    completed = completed_events(records)
    completed_types = [str(record.get("event_type")) for record in completed]
    histories = event_histories(records)
    completed_record_ids = [str(record.get("result_record_id")) for record in completed]
    known_session_records = session_record_ids(paths.session_log)
    recovered_event_types = [
        str(record.get("event_type")) for record in recovered_records
    ]
    interrupted_history = histories.get(str(interrupted_event_id), [])
    frontier_line_count = (
        len([line for line in paths.frontier_log.read_text().splitlines() if line.strip()])
        if paths.frontier_log.exists()
        else 0
    )
    checks = {
        "completed_expected_events": completed_types == [
            "inbound_message",
            "self_scheduled_reflection",
            "housekeeping",
        ],
        "recovered_one_housekeeping_event": recovered_event_types == ["housekeeping"],
        "no_suppressed_events": suppressed_records == [],
        "interrupted_event_recovered_and_completed": interrupted_history == [
            "pending",
            "running",
            "pending",
            "running",
            "completed",
        ],
        "completed_records_in_session_log": all(
            record_id in known_session_records for record_id in completed_record_ids
        ),
        "clean_idle": summary.get("pending_runnable_count") == 0,
        "no_context_errors": summary.get("context_errors") == [],
        "no_lifecycle_anomalies": summary.get("lifecycle_anomalies") == [],
        "multiple_frontier_updates": frontier_line_count >= 4,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "completed_event_types": completed_types,
        "recovered_event_records": recovered_records,
        "suppressed_event_records": suppressed_records,
        "interrupted_event_id": interrupted_event_id,
        "interrupted_event_history": interrupted_history,
        "frontier_line_count": frontier_line_count,
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
    recovered_records: list[JsonDict] | None = None,
    suppressed_records: list[JsonDict] | None = None,
    interrupted_event_id: str | None = None,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    success = required_success(
        summary,
        records,
        paths=paths,
        recovered_records=recovered_records or [],
        suppressed_records=suppressed_records or [],
        interrupted_event_id=interrupted_event_id,
    )
    failures = PROBE.collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.restart_resume_interruption.v1",
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
            backend = PROBE.ScriptedTerminalBackend(scripted_outputs())

    store, memory, ledger, frontier = initialize_run(
        paths,
        run_id,
        live_model_calls,
        endpoint,
        model,
        terminal_tool_choice,
    )
    session = PROBE.make_session(
        paths=paths,
        backend=backend,
        model=model,
        resume=False,
    )
    try:
        session.exchange(
            json.dumps(
                {
                    "event": "initialize_restart_resume_probe",
                    "instruction": "Initialize durable state for restart/resume probe.",
                    "required_output": {
                        "response": "<brief initialization note>",
                        "probe_status": "ready",
                        "open_items": [],
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            terminal_surface=PROBE.seed_terminal_surface(
                tool_choice=terminal_tool_choice,
            ),
            force_memory=None,
        )
    except Exception as exc:
        PROBE.record_failure(
            paths,
            PROBE.classify_exception(exc, stage="seed_exchange"),
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
    commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after seed"},
    )

    append_inbound(store, session, terminal_tool_choice)
    inbound = PROBE.run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=True,
        terminal_tool_choice=terminal_tool_choice,
    )
    if inbound.get("status") != "completed":
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "inbound"},
        )
    commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after inbound"},
    )

    continuation = PROBE.run_attributed_event(
        session=session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if continuation.get("status") != "completed":
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            extra={"stopped_after": "continuation"},
        )
    commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "after continuation"},
    )

    housekeeping_event = append_housekeeping(store, session, terminal_tool_choice)
    commit_frontier(
        paths,
        frontier,
        memory,
        ledger,
        store,
        session,
        run_id,
        {"boundary": "before interrupted housekeeping claim"},
    )
    claimed = store.claim_next_pending(run_id=UUID(run_id))
    if claimed is None:
        PROBE.record_failure(
            paths,
            PROBE.model_output_failure(
                code="missing_interrupted_claim",
                stage="interruption",
                message="housekeeping event was not claimable before interruption",
            ),
        )
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            interrupted_event_id=str(housekeeping_event["event_id"]),
            extra={"stopped_after": "interrupted_claim"},
        )

    resumed_memory = PROBE.LocalMemorySubstrate()
    resumed_ledger = PROBE.ActionLedger(paths.action_log)
    resumed_frontier = PROBE.RestartFrontierStore(
        frontier_path=paths.frontier_log,
        memory_snapshot_path=paths.memory_snapshot,
    )
    try:
        load = resumed_frontier.load_latest(
            run_id=run_id,
            memory=resumed_memory,
            ledger=resumed_ledger,
            event_store=store,
        )
    except Exception as exc:
        PROBE.record_failure(
            paths,
            PROBE.classify_exception(exc, stage="frontier_load"),
            interrupted_event=housekeeping_event,
        )
        return finalize_results(
            paths=paths,
            run_id=run_id,
            live_model_calls=live_model_calls,
            endpoint=endpoint,
            model=model,
            terminal_tool_choice=terminal_tool_choice,
            store=store,
            interrupted_event_id=str(housekeeping_event["event_id"]),
            extra={"stopped_after": "frontier_load"},
        )

    resumed_session = PROBE.make_session(
        paths=paths,
        backend=backend,
        model=model,
        resume=True,
    )
    resumed = PROBE.run_attributed_event(
        session=resumed_session,
        store=store,
        paths=paths,
        auto_continuations=False,
        terminal_tool_choice=terminal_tool_choice,
    )
    if resumed.get("status") == "completed":
        commit_frontier(
            paths,
            resumed_frontier,
            resumed_memory,
            resumed_ledger,
            store,
            resumed_session,
            run_id,
            {"boundary": "after resumed housekeeping"},
        )
    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
        recovered_records=load.recovered_event_records,
        suppressed_records=load.suppressed_event_records,
        interrupted_event_id=str(housekeeping_event["event_id"]),
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
    print(json.dumps({"classification": result["classification"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
