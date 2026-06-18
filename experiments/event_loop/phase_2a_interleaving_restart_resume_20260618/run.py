"""Phase 2A interleaving plus restart/resume stress probe."""

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

EXPERIMENT_ID = "phase_2a_interleaving_restart_resume_20260618"
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

LARGER_RUN_PATH = (
    ROOT_DIR.parent / "phase_2a_larger_multi_entity_loop_20260618" / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
INTERRUPTED_ENTITY_ID = "entity_green"
INTERRUPTED_ROUND = 2


def load_larger_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "phase_2a_larger_multi_entity_for_restart_resume",
        LARGER_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {LARGER_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    module.PROBE.EXPERIMENT_ID = EXPERIMENT_ID
    module.PROBE.ROOT_DIR = ROOT_DIR
    return module


LARGER = load_larger_module()
PROBE = LARGER.PROBE


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
            "base_protocol": "phase_2a_larger_multi_entity_loop_20260618",
            "interruption": {
                "event_type": "entity_continuation",
                "entity_id": INTERRUPTED_ENTITY_ID,
                "round_index": INTERRUPTED_ROUND,
                "point": "after claim as running before exchange",
                "expected_history": [
                    "pending",
                    "running",
                    "pending",
                    "running",
                    "completed",
                ],
            },
            "expected_completed_event_count": len(LARGER.expected_event_type_sequence()),
            "expected_event_type_sequence": LARGER.expected_event_type_sequence(),
            "yanantin_enabled": False,
        },
        "budget.json": {
            "experiment_id": EXPERIMENT_ID,
            "live_model_calls": live_model_calls,
            "max_live_calls": 1 + len(LARGER.expected_event_type_sequence())
            if live_model_calls
            else 0,
            "max_estimated_cost_usd": 6.0 if live_model_calls else 0.0,
        },
        "failure_taxonomy.json": {
            "schema_version": "hamutay.phase_2a_interleaving_restart_taxonomy.v1",
            "layers": [
                "restart_frontier",
                "event_lifecycle",
                "state_reconstruction",
                "state_isolation",
                "identity",
                "interleaving",
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


def reconstruct_entity_maps(session_log: Path) -> tuple[dict[str, JsonDict], dict[str, str]]:
    entity_states: dict[str, JsonDict] = {}
    entity_record_ids: dict[str, str] = {}
    for record in read_jsonl(session_log):
        state = record.get("state")
        if not isinstance(state, dict):
            continue
        entity_id = state.get("entity_id")
        if entity_id not in LARGER.ENTITY_IDS:
            continue
        entity_states[str(entity_id)] = json.loads(json.dumps(state, default=str))
        entity_record_ids[str(entity_id)] = str(record.get("record_id"))
    return entity_states, entity_record_ids


def completed_entity_record_ids(paths: Any) -> list[str]:
    return [
        str(record.get("record_id"))
        for record in read_jsonl(paths.session_log)
        if isinstance(record.get("state"), dict)
        and record["state"].get("entity_id") in LARGER.ENTITY_IDS
    ]


def add_recovery_success(
    *,
    base_success: JsonDict,
    records: list[JsonDict],
    recovered_records: list[JsonDict],
    suppressed_records: list[JsonDict],
    interrupted_event_id: str,
    reconstructed_entity_ids: list[str],
) -> JsonDict:
    histories = event_histories(records)
    interrupted_history = histories.get(interrupted_event_id, [])
    recovered_types = [record.get("event_type") for record in recovered_records]
    checks = dict(base_success["checks"])
    checks.update(
        {
            "recovered_one_interrupted_entity_continuation": recovered_types
            == ["entity_continuation"],
            "no_suppressed_events": suppressed_records == [],
            "interrupted_event_recovered_and_completed": interrupted_history
            == ["pending", "running", "pending", "running", "completed"],
            "reconstructed_entity_state_for_resume": INTERRUPTED_ENTITY_ID
            in reconstructed_entity_ids,
        }
    )
    return {
        **base_success,
        "passed": all(checks.values()),
        "checks": checks,
        "recovered_event_records": recovered_records,
        "suppressed_event_records": suppressed_records,
        "interrupted_event_id": interrupted_event_id,
        "interrupted_event_history": interrupted_history,
        "reconstructed_entity_ids": reconstructed_entity_ids,
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
    reconstructed_entity_ids: list[str] | None = None,
    extra: JsonDict | None = None,
) -> JsonDict:
    records = store.read_records()
    summary = PROBE.summarize_event_log(records)
    base_success = LARGER.required_success(summary, records, paths=paths)
    success = add_recovery_success(
        base_success=base_success,
        records=records,
        recovered_records=recovered_records or [],
        suppressed_records=suppressed_records or [],
        interrupted_event_id=interrupted_event_id or "",
        reconstructed_entity_ids=reconstructed_entity_ids or [],
    )
    failures = PROBE.collect_failures(paths, records, success)
    classification = "passed" if success["passed"] and not failures else "failed"
    results = {
        "schema_version": "hamutay.phase_2a_interleaving_restart_resume.v1",
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


def run_entity_inbound(
    *,
    session: Any,
    store: Any,
    paths: Any,
    frontier: Any,
    memory: Any,
    ledger: Any,
    run_id: str,
    entity: JsonDict,
    round_index: int,
    terminal_tool_choice: str,
    seed_state: JsonDict,
    seed_record_id: str,
    entity_states: dict[str, JsonDict],
    entity_record_ids: dict[str, str],
    all_entity_record_ids: list[str],
) -> JsonDict:
    context_record_id = entity_record_ids.get(entity["entity_id"], seed_record_id)
    LARGER.set_entity_wake_state(
        session,
        entity=entity,
        entity_states=entity_states,
        seed_state=seed_state,
    )
    LARGER.append_entity_inbound(
        store,
        session,
        entity,
        round_index,
        terminal_tool_choice,
        context_record_id=context_record_id,
    )
    inbound = LARGER.run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if inbound.get("status") == "completed":
        LARGER.remember_entity_state(
            session,
            entity=entity,
            entity_states=entity_states,
            entity_record_ids=entity_record_ids,
        )
        all_entity_record_ids.append(str(inbound["result_record_id"]))
        LARGER.commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after inbound {entity['entity_id']} round {round_index}"},
        )
    return inbound


def run_entity_continuation(
    *,
    session: Any,
    store: Any,
    paths: Any,
    frontier: Any,
    memory: Any,
    ledger: Any,
    run_id: str,
    entity: JsonDict,
    round_index: int,
    inbound_record_id: str,
    terminal_tool_choice: str,
    seed_state: JsonDict,
    entity_states: dict[str, JsonDict],
    entity_record_ids: dict[str, str],
    all_entity_record_ids: list[str],
) -> JsonDict:
    LARGER.set_entity_wake_state(
        session,
        entity=entity,
        entity_states=entity_states,
        seed_state=seed_state,
    )
    LARGER.append_entity_continuation(
        store,
        session,
        entity,
        round_index,
        inbound_record_id,
        terminal_tool_choice,
    )
    continuation = LARGER.run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if continuation.get("status") == "completed":
        LARGER.remember_entity_state(
            session,
            entity=entity,
            entity_states=entity_states,
            entity_record_ids=entity_record_ids,
        )
        all_entity_record_ids.append(str(continuation["result_record_id"]))
        LARGER.commit_frontier(
            paths,
            frontier,
            memory,
            ledger,
            store,
            session,
            run_id,
            {"boundary": f"after continuation {entity['entity_id']} round {round_index}"},
        )
    return continuation


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
    terminal_tool_choice = terminal_tool_choice or PROBE.default_terminal_tool_choice(endpoint)
    if backend is None:
        if live_model_calls:
            backend = PROBE.make_live_backend(endpoint=endpoint, api_key=api_key or "", max_tokens=max_tokens)
        else:
            backend = PROBE.ScriptedTerminalBackend(LARGER.scripted_outputs())
    store, memory, ledger, frontier = LARGER.initialize_run(paths, run_id, live_model_calls, endpoint, model, terminal_tool_choice)
    session = PROBE.make_session(paths=paths, backend=backend, model=model, resume=False)
    try:
        session.exchange(
            json.dumps(
                {
                    "event": "initialize_phase_2a_interleaving_restart_resume",
                    "instruction": "Initialize durable state for an interleaved restart/resume probe.",
                    "required_output": {
                        "response": "<brief initialization note>",
                        "probe_status": "ready",
                        "open_items": [],
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            terminal_surface=PROBE.seed_terminal_surface(tool_choice=terminal_tool_choice),
            force_memory=None,
        )
    except Exception as exc:
        PROBE.record_failure(paths, PROBE.classify_exception(exc, stage="seed_exchange"))
        return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": "seed_exchange"})

    seed_state = LARGER.clone_json(session._state or {})
    seed_record_id = str(session._prior_states[-1][1])
    entity_states: dict[str, JsonDict] = {}
    entity_record_ids: dict[str, str] = {}
    all_entity_record_ids: list[str] = []
    all_shared_record_ids: list[str] = []
    LARGER.commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after seed"})

    interrupted_event_id = ""
    reconstructed_entity_ids: list[str] = []
    load = None

    for round_index in LARGER.ROUNDS:
        inbound_results: dict[str, JsonDict] = {}
        for entity in LARGER.ENTITIES:
            inbound = run_entity_inbound(
                session=session,
                store=store,
                paths=paths,
                frontier=frontier,
                memory=memory,
                ledger=ledger,
                run_id=run_id,
                entity=entity,
                round_index=round_index,
                terminal_tool_choice=terminal_tool_choice,
                seed_state=seed_state,
                seed_record_id=seed_record_id,
                entity_states=entity_states,
                entity_record_ids=entity_record_ids,
                all_entity_record_ids=all_entity_record_ids,
            )
            if inbound.get("status") != "completed":
                return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"inbound_{entity['entity_id']}_round_{round_index}"})
            inbound_results[entity["entity_id"]] = inbound

        for entity in LARGER.ENTITIES:
            if (
                round_index == INTERRUPTED_ROUND
                and entity["entity_id"] == INTERRUPTED_ENTITY_ID
            ):
                LARGER.set_entity_wake_state(
                    session,
                    entity=entity,
                    entity_states=entity_states,
                    seed_state=seed_state,
                )
                LARGER.append_entity_continuation(
                    store,
                    session,
                    entity,
                    round_index,
                    str(inbound_results[entity["entity_id"]]["result_record_id"]),
                    terminal_tool_choice,
                )
                LARGER.commit_frontier(
                    paths,
                    frontier,
                    memory,
                    ledger,
                    store,
                    session,
                    run_id,
                    {"boundary": "before interrupted entity continuation claim"},
                )
                claimed = store.claim_next_pending(run_id=UUID(run_id))
                if claimed is None:
                    PROBE.record_failure(
                        paths,
                        PROBE.model_output_failure(
                            code="missing_interrupted_claim",
                            stage="interruption",
                            message="interrupted entity continuation was not claimable",
                        ),
                    )
                    return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": "interrupted_claim"})
                interrupted_event_id = str(claimed[0]["event_id"])

                resumed_memory = PROBE.LocalMemorySubstrate()
                resumed_ledger = PROBE.ActionLedger(paths.action_log)
                resumed_frontier = PROBE.RestartFrontierStore(
                    frontier_path=paths.frontier_log,
                    memory_snapshot_path=paths.memory_snapshot,
                )
                load = resumed_frontier.load_latest(
                    run_id=run_id,
                    memory=resumed_memory,
                    ledger=resumed_ledger,
                    event_store=store,
                )
                resumed_session = PROBE.make_session(
                    paths=paths,
                    backend=backend,
                    model=model,
                    resume=True,
                )
                entity_states, entity_record_ids = reconstruct_entity_maps(paths.session_log)
                reconstructed_entity_ids = sorted(entity_states)
                LARGER.set_entity_wake_state(
                    resumed_session,
                    entity=entity,
                    entity_states=entity_states,
                    seed_state=seed_state,
                )
                continuation = LARGER.run_one_event(
                    session=resumed_session,
                    store=store,
                    paths=paths,
                    terminal_tool_choice=terminal_tool_choice,
                )
                if continuation.get("status") != "completed":
                    return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, recovered_records=load.recovered_event_records if load else [], suppressed_records=load.suppressed_event_records if load else [], interrupted_event_id=interrupted_event_id, reconstructed_entity_ids=reconstructed_entity_ids, extra={"stopped_after": "resumed_continuation"})
                session = resumed_session
                memory = resumed_memory
                ledger = resumed_ledger
                frontier = resumed_frontier
                LARGER.remember_entity_state(
                    session,
                    entity=entity,
                    entity_states=entity_states,
                    entity_record_ids=entity_record_ids,
                )
                all_entity_record_ids = completed_entity_record_ids(paths)
                LARGER.commit_frontier(
                    paths,
                    frontier,
                    memory,
                    ledger,
                    store,
                    session,
                    run_id,
                    {"boundary": "after resumed interrupted entity continuation"},
                )
                continue

            continuation = run_entity_continuation(
                session=session,
                store=store,
                paths=paths,
                frontier=frontier,
                memory=memory,
                ledger=ledger,
                run_id=run_id,
                entity=entity,
                round_index=round_index,
                inbound_record_id=str(inbound_results[entity["entity_id"]]["result_record_id"]),
                terminal_tool_choice=terminal_tool_choice,
                seed_state=seed_state,
                entity_states=entity_states,
                entity_record_ids=entity_record_ids,
                all_entity_record_ids=all_entity_record_ids,
            )
            if continuation.get("status") != "completed":
                return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"continuation_{entity['entity_id']}_round_{round_index}"})

        LARGER.set_global_wake_state(
            session,
            seed_state=seed_state,
            entity_record_ids=entity_record_ids,
            completed_entity_events=len(all_entity_record_ids),
        )
        LARGER.append_housekeeping(
            store,
            session,
            round_index,
            list(entity_record_ids.values()),
            terminal_tool_choice,
        )
        housekeeping = LARGER.run_one_event(
            session=session,
            store=store,
            paths=paths,
            terminal_tool_choice=terminal_tool_choice,
        )
        if housekeeping.get("status") != "completed":
            return finalize_results(paths=paths, run_id=run_id, live_model_calls=live_model_calls, endpoint=endpoint, model=model, terminal_tool_choice=terminal_tool_choice, store=store, extra={"stopped_after": f"housekeeping_round_{round_index}"})
        all_shared_record_ids.append(str(housekeeping["result_record_id"]))
        LARGER.commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": f"after housekeeping round {round_index}"})

    LARGER.set_global_wake_state(
        session,
        seed_state=seed_state,
        entity_record_ids=entity_record_ids,
        completed_entity_events=len(all_entity_record_ids),
    )
    LARGER.append_final(
        store,
        session,
        [*all_entity_record_ids, *all_shared_record_ids],
        terminal_tool_choice,
    )
    final = LARGER.run_one_event(
        session=session,
        store=store,
        paths=paths,
        terminal_tool_choice=terminal_tool_choice,
    )
    if final.get("status") == "completed":
        LARGER.commit_frontier(paths, frontier, memory, ledger, store, session, run_id, {"boundary": "after final artifact"})
    return finalize_results(
        paths=paths,
        run_id=run_id,
        live_model_calls=live_model_calls,
        endpoint=endpoint,
        model=model,
        terminal_tool_choice=terminal_tool_choice,
        store=store,
        recovered_records=load.recovered_event_records if load else [],
        suppressed_records=load.suppressed_event_records if load else [],
        interrupted_event_id=interrupted_event_id,
        reconstructed_entity_ids=reconstructed_entity_ids,
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
