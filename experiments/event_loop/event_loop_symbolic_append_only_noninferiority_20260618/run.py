"""Prospective symbolic event-loop vs append-only live replication."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPERIMENT_ID = "event_loop_symbolic_append_only_noninferiority_20260618"
ROOT_DIR = Path(__file__).resolve().parent
BASE_RUN_PATH = (
    ROOT_DIR.parent
    / "event_loop_viability_append_only_noninferiority_20260614"
    / "run.py"
)
CONDITIONS = ("event_loop_scheduled", "append_only")
NON_INFERIORITY_MARGIN = 0.10
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
SYMBOLIC_CONTRACT = "framework_bound_symbolic_continuation.v1"


TASKS: dict[str, JsonDict] = {
    "identity_drift_boundary": {
        "prompt": (
            "Write a determination note about whether the scheduler or the "
            "model owns event identity during continuation."
        ),
        "required_facts": {
            "event_identity_scheduler_owned": {
                "evidence": "e8100000-0000-0000-0000-000000000101",
                "loss_marker": None,
            },
            "run_name_human_readable_only": {
                "evidence": "e8100000-0000-0000-0000-000000000102",
                "loss_marker": None,
            },
            "record_uniquifier_framework_bound": {
                "evidence": "e8100000-0000-0000-0000-000000000103",
                "loss_marker": "scheduler-owned identity",
            },
        },
        "records": [
            {
                "record_id": "e8100000-0000-0000-0000-000000000101",
                "record_type": "evidence",
                "content": {
                    "fact_id": "event_identity_scheduler_owned",
                    "text": (
                        "Concrete event identity is scheduler-owned and is "
                        "not accepted from model-authored continuation text."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000102",
                "record_type": "evidence",
                "content": {
                    "fact_id": "run_name_human_readable_only",
                    "text": (
                        "Run names are human-readable labels and are not "
                        "treated as durable scheduler identifiers."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000103",
                "record_type": "evidence",
                "content": {
                    "fact_id": "record_uniquifier_framework_bound",
                    "text": (
                        "Record uniquifiers are bound by the framework after "
                        "the producing wake completes."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000199",
                "record_type": "distractor",
                "content": {
                    "text": "Unrelated UI note: avoid oversized rounded purple capsules.",
                },
            },
        ],
        "distractor_id": "e8100000-0000-0000-0000-000000000199",
    },
    "declared_loss_discipline": {
        "prompt": (
            "Write a note deciding how declared limitations should affect a "
            "research artifact."
        ),
        "required_facts": {
            "limitation_must_be_declared": {
                "evidence": "e8100000-0000-0000-0000-000000000201",
                "loss_marker": "missing calibration evidence",
            },
            "unsupported_evidence_not_promoted": {
                "evidence": "e8100000-0000-0000-0000-000000000202",
                "loss_marker": None,
            },
            "loss_statement_changes_action": {
                "evidence": "e8100000-0000-0000-0000-000000000203",
                "loss_marker": None,
            },
        },
        "records": [
            {
                "record_id": "e8100000-0000-0000-0000-000000000201",
                "record_type": "evidence",
                "content": {
                    "fact_id": "limitation_must_be_declared",
                    "text": (
                        "The artifact must declare that calibration evidence "
                        "is missing when calibration is not present."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000202",
                "record_type": "evidence",
                "content": {
                    "fact_id": "unsupported_evidence_not_promoted",
                    "text": (
                        "A missing support record cannot be promoted into a "
                        "supported claim."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000203",
                "record_type": "evidence",
                "content": {
                    "fact_id": "loss_statement_changes_action",
                    "text": (
                        "Declared losses should constrain the recommended "
                        "action rather than being appended as decorative text."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000299",
                "record_type": "distractor",
                "content": {"text": "Unrelated formatting note about nav spacing."},
            },
        ],
        "distractor_id": "e8100000-0000-0000-0000-000000000299",
    },
    "restart_frontier_reconstruction": {
        "prompt": (
            "Write a note determining whether a restart frontier can support "
            "fair continuation after interruption."
        ),
        "required_facts": {
            "frontier_has_result_record": {
                "evidence": "e8100000-0000-0000-0000-000000000301",
                "loss_marker": None,
            },
            "symbolic_context_resolved_by_framework": {
                "evidence": "e8100000-0000-0000-0000-000000000302",
                "loss_marker": "framework-bound replay",
            },
            "replay_preserves_terminal_surface": {
                "evidence": "e8100000-0000-0000-0000-000000000303",
                "loss_marker": None,
            },
        },
        "records": [
            {
                "record_id": "e8100000-0000-0000-0000-000000000301",
                "record_type": "evidence",
                "content": {
                    "fact_id": "frontier_has_result_record",
                    "text": (
                        "The restart frontier records the completed wake's "
                        "result record before a continuation is claimed."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000302",
                "record_type": "evidence",
                "content": {
                    "fact_id": "symbolic_context_resolved_by_framework",
                    "text": (
                        "Symbolic context requests are resolved by the "
                        "framework against stored wake state during replay."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000303",
                "record_type": "evidence",
                "content": {
                    "fact_id": "replay_preserves_terminal_surface",
                    "text": (
                        "The restart path preserves the framework-selected "
                        "terminal surface for the continuation."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000399",
                "record_type": "distractor",
                "content": {"text": "Unrelated note about CSS color tokens."},
            },
        ],
        "distractor_id": "e8100000-0000-0000-0000-000000000399",
    },
    "multi_wake_continuation": {
        "prompt": (
            "Write a note deciding what a multi-wake continuation must prove "
            "before it can be compared with append-only output."
        ),
        "required_facts": {
            "second_wake_depends_on_first": {
                "evidence": "e8100000-0000-0000-0000-000000000401",
                "loss_marker": "multi-wake dependency",
            },
            "open_items_closed_by_bound_continuation": {
                "evidence": "e8100000-0000-0000-0000-000000000402",
                "loss_marker": None,
            },
            "model_does_not_choose_terminal_surface": {
                "evidence": "e8100000-0000-0000-0000-000000000403",
                "loss_marker": None,
            },
        },
        "records": [
            {
                "record_id": "e8100000-0000-0000-0000-000000000401",
                "record_type": "evidence",
                "content": {
                    "fact_id": "second_wake_depends_on_first",
                    "text": (
                        "The second wake must consume state produced by the "
                        "first wake rather than reconstructing it from the "
                        "full corpus."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000402",
                "record_type": "evidence",
                "content": {
                    "fact_id": "open_items_closed_by_bound_continuation",
                    "text": (
                        "Open items are closed by the framework-bound "
                        "continuation, not by an append-only shortcut."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000403",
                "record_type": "evidence",
                "content": {
                    "fact_id": "model_does_not_choose_terminal_surface",
                    "text": (
                        "The model does not choose the terminal surface for "
                        "the continuation wake."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000499",
                "record_type": "distractor",
                "content": {"text": "Unrelated release-note phrasing draft."},
            },
        ],
        "distractor_id": "e8100000-0000-0000-0000-000000000499",
    },
    "ordinary_synthesis": {
        "prompt": (
            "Write a short synthesis note about what can and cannot be claimed "
            "from an event-loop append-only comparison."
        ),
        "required_facts": {
            "artifact_margin_declared": {
                "evidence": "e8100000-0000-0000-0000-000000000501",
                "loss_marker": None,
            },
            "observability_separate_from_quality": {
                "evidence": "e8100000-0000-0000-0000-000000000502",
                "loss_marker": "observability separate from quality",
            },
            "provider_failure_inconclusive": {
                "evidence": "e8100000-0000-0000-0000-000000000503",
                "loss_marker": None,
            },
        },
        "records": [
            {
                "record_id": "e8100000-0000-0000-0000-000000000501",
                "record_type": "evidence",
                "content": {
                    "fact_id": "artifact_margin_declared",
                    "text": (
                        "Artifact non-inferiority uses a declared 0.10 mean "
                        "quality margin."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000502",
                "record_type": "evidence",
                "content": {
                    "fact_id": "observability_separate_from_quality",
                    "text": (
                        "Scheduler observability is reported separately from "
                        "artifact quality."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000503",
                "record_type": "evidence",
                "content": {
                    "fact_id": "provider_failure_inconclusive",
                    "text": (
                        "Provider or transport failure makes the run "
                        "inconclusive rather than proving model inferiority."
                    ),
                },
            },
            {
                "record_id": "e8100000-0000-0000-0000-000000000599",
                "record_type": "distractor",
                "content": {"text": "Unrelated command-line help copy."},
            },
        ],
        "distractor_id": "e8100000-0000-0000-0000-000000000599",
    },
}


def load_base_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "event_loop_append_only_base_20260614",
        BASE_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load base harness from {BASE_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    module.TASKS = TASKS
    module.DEFAULT_ENDPOINT = DEFAULT_ENDPOINT
    module.DEFAULT_MODEL = DEFAULT_MODEL
    module.DEFAULT_API_KEY_ENV = DEFAULT_API_KEY_ENV
    module.NON_INFERIORITY_MARGIN = NON_INFERIORITY_MARGIN
    return module


BASE = load_base_module()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def matrix(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "conditions": list(CONDITIONS),
        "tasks": sorted(TASKS),
        "default_model": DEFAULT_MODEL,
        "default_endpoint": DEFAULT_ENDPOINT,
        "symbolic_contract": SYMBOLIC_CONTRACT,
        "claim_separation": {
            "shared_surface_noninferiority": (
                "raw request/response, parsed artifact, deterministic score, "
                "and failure-attribution surface"
            ),
            "scheduler_added_value": (
                "event-loop-only reconstruction evidence, not an append_only penalty"
            ),
        },
        "non_inferiority_margin": NON_INFERIORITY_MARGIN,
    }


def budget_manifest(*, live_model_calls: bool = False) -> JsonDict:
    max_calls = len(TASKS) * 3 if live_model_calls else 0
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "max_live_calls": max_calls,
        "max_estimated_cost_usd": 5.0 if live_model_calls else 0.0,
        "output_cap_policy": (
            "Live mode makes two event-loop terminal-surface calls and one "
            "append-only terminal-surface call per task."
            if live_model_calls else
            "Deterministic dry harness; no provider calls."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "schema_version": "hamutay.symbolic_append_only_taxonomy.v1",
        "layers": [
            "scheduler",
            "model",
            "model_output",
            "provider",
            "harness",
            "substrate",
            "scorer",
            "protocol",
            "inconclusive",
        ],
        "entries": [
            {
                "layer": "model_output",
                "code": "invalid_symbolic_continuation_request",
                "meaning": (
                    "The model did not request continuation through the "
                    "framework-bound symbolic contract."
                ),
            },
            {
                "layer": "scheduler",
                "code": "symbolic_binding_not_reconstructable",
                "meaning": (
                    "The scheduler-owned continuation identity or restart "
                    "frontier could not be reconstructed."
                ),
            },
            {
                "layer": "model",
                "code": "artifact_quality_inferior",
                "meaning": "Event-loop artifact quality missed the margin.",
            },
            {
                "layer": "provider",
                "code": "provider_or_transport_failure",
                "meaning": "A provider or transport failure prevented a fair row.",
            },
        ],
    }


def write_preregistration_artifacts(
    output_root: Path = ROOT_DIR,
    *,
    live_model_calls: bool = False,
) -> JsonDict:
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "matrix.json": matrix(live_model_calls=live_model_calls),
        "budget.json": budget_manifest(live_model_calls=live_model_calls),
        "failure_taxonomy.json": failure_taxonomy(),
    }
    for name, payload in artifacts.items():
        BASE._write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


def prepare_output_root(output_root: Path, *, overwrite: bool) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    generated = [
        "analysis.md",
        "budget.json",
        "failure_taxonomy.json",
        "matrix.json",
        "results.json",
        "rows",
    ]
    for name in generated:
        path = output_root / name
        if not path.exists():
            continue
        if not overwrite:
            raise FileExistsError(f"{path} exists; pass --overwrite to replace")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def continuation_request_schema() -> JsonDict:
    return {
        "type": "object",
        "properties": {
            "requested": {"type": "boolean"},
            "kind": {"type": "string"},
            "purpose": {"type": "string"},
            "symbolic_context": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "enum": ["completed_wake_state"],
                        },
                        "field": {"type": "string"},
                    },
                    "required": ["source"],
                },
            },
            "label": {"type": "string"},
        },
        "required": ["requested", "purpose", "symbolic_context", "label"],
    }


def symbolic_selection_terminal_surface(*, tool_choice: str = "auto") -> JsonDict:
    surface = BASE.selection_terminal_surface(tool_choice=tool_choice)
    properties = surface["input_schema"]["properties"]
    properties["continuation_request"] = continuation_request_schema()
    surface["input_schema"]["required"].append("continuation_request")
    surface["state_update"]["copy"]["continuation_request"] = "continuation_request"
    surface["description"] = (
        "Select bounded context and request the artifact wake through symbolic "
        "continuation only. Do not author concrete continuation identifiers."
    )
    return surface


def symbolic_selection_request(*, task_id: str, event_identity: str) -> JsonDict:
    return {
        "condition": "event_loop_scheduled",
        "cycle": 1,
        "event_identity": event_identity,
        "task_id": task_id,
        "task": TASKS[task_id]["prompt"],
        "corpus_map": BASE.corpus_map(task_id),
        "required_output": {
            "response": "<brief scheduling note>",
            "event_id": event_identity,
            "work_plan": "<short plan>",
            "requested_context": [{"tool": "recall", "record_id": "<uuid>"}],
            "omitted_record_ids": ["<uuid>"],
            "declared_losses": ["<loss or limitation>"],
            "continuation_request": {
                "requested": True,
                "kind": "artifact_wake",
                "purpose": "Write the final artifact from framework-bound state.",
                "symbolic_context": [
                    {"source": "completed_wake_state", "field": "requested_context"},
                    {"source": "completed_wake_state", "field": "declared_losses"},
                ],
                "label": "artifact-wake",
            },
        },
        "instruction": (
            "Select only task-relevant evidence records. Request the artifact "
            "wake using continuation_request.symbolic_context. Do not emit "
            "record_uniquifier, scheduled_by_record_epoch, requested_context "
            "for the continuation, or terminal_surface for the continuation."
        ),
    }


def normalize_symbolic_selection(
    raw_output: JsonDict,
    *,
    task_id: str,
    event_identity: str,
) -> JsonDict:
    parsed = BASE.normalize_selection_output(
        raw_output,
        task_id=task_id,
        event_id=event_identity,
    )
    continuation = raw_output.get("continuation_request")
    parsed["continuation_request"] = (
        continuation if isinstance(continuation, dict) else {}
    )
    return parsed


def bind_symbolic_continuation_request(
    continuation_request: JsonDict,
    *,
    result_record_id: str,
    terminal_tool_choice: str,
) -> JsonDict:
    if continuation_request.get("requested") is not True:
        raise ValueError("continuation_request.requested must be true")
    symbolic_context = continuation_request.get("symbolic_context")
    if not isinstance(symbolic_context, list) or not symbolic_context:
        raise ValueError("continuation_request.symbolic_context must be non-empty")
    requested_context: list[JsonDict] = []
    for index, item in enumerate(symbolic_context):
        if not isinstance(item, dict):
            raise ValueError(f"symbolic_context[{index}] must be an object")
        if item.get("source") != "completed_wake_state":
            raise ValueError("symbolic context source must be completed_wake_state")
        request: JsonDict = {"tool": "recall", "record_id": result_record_id}
        if isinstance(item.get("field"), str) and item["field"]:
            request["field"] = item["field"]
        requested_context.append(request)
    ignored = sorted(
        key for key in ("requested_context", "terminal_surface", "record_id")
        if key in continuation_request
    )
    bound: JsonDict = {
        "binding_contract": SYMBOLIC_CONTRACT,
        "requested": True,
        "kind": str(continuation_request.get("kind") or "artifact_wake"),
        "label": str(continuation_request.get("label") or "artifact-wake"),
        "purpose": (
            "Write the final artifact from the framework-bound completed wake."
        ),
        "requested_context": requested_context,
        "terminal_surface": BASE.artifact_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
        "symbolic_context": deepcopy(symbolic_context),
        "model_requested_purpose": str(continuation_request.get("purpose") or ""),
    }
    if ignored:
        bound["ignored_model_authored_fields"] = ignored
    return bound


def symbolic_scheduler_events(
    *,
    task_id: str,
    event_identity: str,
    run_name: str,
    scheduled_by_record_epoch: int,
    record_uniquifier: str,
    bound_continuation: JsonDict,
) -> list[JsonDict]:
    return [
        {
            "event_identity": event_identity,
            "run_name": run_name,
            "task_id": task_id,
            "status": "scheduled",
            "cycle": 1,
            "scheduled_by_record_epoch": scheduled_by_record_epoch,
            "record_uniquifier": record_uniquifier,
            "binding_contract": SYMBOLIC_CONTRACT,
            "terminal_surface_tool": bound_continuation["terminal_surface"][
                "tool_name"
            ],
        },
        {
            "event_identity": event_identity,
            "run_name": run_name,
            "task_id": task_id,
            "status": "claimed",
            "cycle": 2,
            "scheduled_by_record_epoch": scheduled_by_record_epoch,
            "record_uniquifier": record_uniquifier,
            "binding_contract": SYMBOLIC_CONTRACT,
            "wake_context": {
                "event_identity": event_identity,
                "run_name": run_name,
                "binding_contract": SYMBOLIC_CONTRACT,
            },
        },
        {
            "event_identity": event_identity,
            "run_name": run_name,
            "task_id": task_id,
            "status": "completed",
            "cycle": 2,
            "scheduled_by_record_epoch": scheduled_by_record_epoch,
            "record_uniquifier": record_uniquifier,
            "binding_contract": SYMBOLIC_CONTRACT,
            "wake_context": {
                "event_identity": event_identity,
                "run_name": run_name,
                "binding_contract": SYMBOLIC_CONTRACT,
            },
        },
    ]


def symbolic_scheduler_checks_for_row(
    *,
    row_root: Path,
    task_id: str,
    event_identity: str,
    trace: list[JsonDict],
    restart_frontier: JsonDict,
    selection: JsonDict,
    bound_continuation: JsonDict,
) -> JsonDict:
    statuses = [item["status"] for item in trace]
    checks = {
        "scheduled_event_recorded": (row_root / "scheduler_events.json").exists(),
        "status_sequence_valid": statuses == ["scheduled", "claimed", "completed"],
        "wake_context_has_event_identity": all(
            item.get("wake_context", {}).get("event_identity") == event_identity
            for item in trace[1:]
        ),
        "symbolic_binding_contract": all(
            item.get("binding_contract") == SYMBOLIC_CONTRACT for item in trace
        ),
        "framework_bound_terminal_surface": (
            bound_continuation.get("terminal_surface", {}).get("tool_name")
            == "write_matched_artifact"
        ),
        "selected_context_preserved": bool(selection.get("requested_context")),
        "declared_losses_preserved": bool(selection.get("declared_losses")),
        "restart_frontier_written": (row_root / "restart_frontier.json").exists(),
        "restart_frontier_reconstructable": (
            restart_frontier.get("event_identity") == event_identity
            and restart_frontier.get("carried_state") == selection
            and restart_frontier.get("binding_contract") == SYMBOLIC_CONTRACT
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failure_layer": "none" if all(checks.values()) else "scheduler",
    }


def dry_symbolic_selection(*, task_id: str, event_identity: str) -> JsonDict:
    parsed = {
        "event_id": event_identity,
        "task_id": task_id,
        "work_plan": "Schedule a framework-bound symbolic artifact wake.",
        "requested_context": [
            {"tool": "recall", "record_id": data["evidence"]}
            for data in TASKS[task_id]["required_facts"].values()
        ],
        "omitted_record_ids": [TASKS[task_id]["distractor_id"]],
        "declared_losses": BASE.declared_losses(task_id),
        "continuation_request": {
            "requested": True,
            "kind": "artifact_wake",
            "purpose": "Write the final artifact from framework-bound state.",
            "symbolic_context": [
                {"source": "completed_wake_state", "field": "requested_context"},
                {"source": "completed_wake_state", "field": "declared_losses"},
            ],
            "label": "artifact-wake",
        },
    }
    return BASE.cycle_payload(
        parsed=parsed,
        request_payload=symbolic_selection_request(
            task_id=task_id,
            event_identity=event_identity,
        ),
    )


def live_cycle_payload_from_session(*, session: Any, request_payload: JsonDict) -> JsonDict:
    raw_output = deepcopy(getattr(session, "_last_raw_output", None) or {})
    usage = deepcopy(getattr(session, "_last_usage", None) or {})
    return {
        "parsed": raw_output,
        "raw_content": json.dumps(raw_output, sort_keys=True, default=str),
        "request_payload": deepcopy(request_payload),
        "response_payload": {"taste_open_log": True},
        "usage": usage,
        "elapsed_seconds": None,
    }


def run_symbolic_event_loop_row(
    *,
    task_id: str,
    output_root: Path,
    live_model_calls: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
    max_tokens: int,
    terminal_tool_choice: str,
) -> JsonDict:
    condition = "event_loop_scheduled"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    event_identity = f"{task_id}::symbolic-artifact"
    run_name = f"{EXPERIMENT_ID}:{task_id}:{condition}"

    if live_model_calls:
        from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

        backend = OpenAITasteBackend(
            base_url=endpoint,
            api_key=api_key or "",
            max_tokens=max_tokens,
            timeout=180,
            provider_name="deepseek" if "api.deepseek.com" in endpoint else "openai",
            extra_headers={
                "X-Title": f"hamutay/{EXPERIMENT_ID}",
                "HTTP-Referer": "https://github.com/fsgeek/hamutay",
            },
            max_retries=1,
        )
        session = OpenTasteSession(
            model=model,
            backend=backend,
            log_path=str(row_root / "taste_open.jsonl"),
            experiment_label=run_name,
            system_prompt_prefix=BASE.live_event_loop_system_prefix(),
            memory_base_probability=0.0,
        )
        cycle1_request = symbolic_selection_request(
            task_id=task_id,
            event_identity=event_identity,
        )
        session.exchange(
            json.dumps(cycle1_request, indent=2, sort_keys=True),
            terminal_surface=symbolic_selection_terminal_surface(
                tool_choice=terminal_tool_choice
            ),
            force_memory=None,
        )
        cycle1 = live_cycle_payload_from_session(
            session=session,
            request_payload=cycle1_request,
        )
        cycle1["parsed"] = normalize_symbolic_selection(
            cycle1["parsed"],
            task_id=task_id,
            event_identity=event_identity,
        )
        result_record_id = str(session._prior_states[-1][1])
    else:
        cycle1 = dry_symbolic_selection(
            task_id=task_id,
            event_identity=event_identity,
        )
        result_record_id = f"{task_id}::cycle1-result"

    BASE._write_json(row_root / "cycle_01.json", cycle1)
    bound_continuation = bind_symbolic_continuation_request(
        cycle1["parsed"]["continuation_request"],
        result_record_id=result_record_id,
        terminal_tool_choice=terminal_tool_choice,
    )
    trace = symbolic_scheduler_events(
        task_id=task_id,
        event_identity=event_identity,
        run_name=run_name,
        scheduled_by_record_epoch=1,
        record_uniquifier=result_record_id,
        bound_continuation=bound_continuation,
    )
    selected_ids = [
        request["record_id"]
        for request in cycle1["parsed"]["requested_context"]
        if isinstance(request, dict)
    ]
    selected_records = [
        deepcopy(record)
        for record in TASKS[task_id]["records"]
        if record["record_id"] in selected_ids
    ]
    restart_frontier = {
        "task_id": task_id,
        "event_identity": event_identity,
        "run_name": run_name,
        "last_committed_cycle": 1,
        "scheduled_by_record_epoch": 1,
        "record_uniquifier": result_record_id,
        "binding_contract": SYMBOLIC_CONTRACT,
        "carried_state": deepcopy(cycle1["parsed"]),
        "bound_continuation": bound_continuation,
        "pending_wake_context": trace[-1]["wake_context"],
    }
    BASE._write_json(row_root / "scheduler_events.json", trace)
    BASE._write_json(row_root / "restart_frontier.json", restart_frontier)

    cycle2_request = BASE.live_artifact_request(
        task_id=task_id,
        condition=condition,
        corpus=selected_records,
        carried_state=cycle1["parsed"],
        wake_context={
            **trace[-1]["wake_context"],
            "bound_continuation": bound_continuation,
        },
    )
    cycle2_request["symbolic_continuation"] = bound_continuation
    cycle2_request["scheduler_bound_identity"] = {
        "event_identity": event_identity,
        "run_name": run_name,
        "scheduled_by_record_epoch": 1,
        "record_uniquifier": result_record_id,
        "binding_contract": SYMBOLIC_CONTRACT,
    }
    if live_model_calls:
        session.exchange(
            json.dumps(cycle2_request, indent=2, sort_keys=True),
            terminal_surface=bound_continuation["terminal_surface"],
            force_memory=None,
        )
        cycle2 = live_cycle_payload_from_session(
            session=session,
            request_payload=cycle2_request,
        )
        cycle2["parsed"] = BASE.normalize_artifact_output(cycle2["parsed"])
    else:
        cycle2 = BASE.dry_artifact_cycle(
            task_id=task_id,
            condition=condition,
            corpus=selected_records,
            carried_state=cycle1["parsed"],
        )
        cycle2["request_payload"] = cycle2_request
    BASE._write_json(row_root / "cycle_02.json", cycle2)

    artifact_score = BASE.score_artifact(task_id, cycle2["parsed"])
    usage1 = cycle1.get("usage", {})
    usage2 = cycle2.get("usage", {})
    context_accounting = {
        "condition": condition,
        "task_id": task_id,
        "selected_record_ids": selected_ids,
        "omitted_record_ids": cycle1["parsed"]["omitted_record_ids"],
        "declared_losses_before_artifact": cycle1["parsed"]["declared_losses"],
        "declared_losses_in_artifact": cycle2["parsed"].get("declared_losses", []),
        "symbolic_binding_contract": SYMBOLIC_CONTRACT,
        "bound_requested_context": bound_continuation["requested_context"],
        "token_use": {
            "prompt_tokens": (
                usage1.get("input_tokens", 0) + usage2.get("input_tokens", 0)
            ) if live_model_calls else (
                BASE._approx_tokens(cycle1["request_payload"])
                + BASE._approx_tokens(cycle2["request_payload"])
            ),
            "completion_tokens": (
                usage1.get("output_tokens", 0) + usage2.get("output_tokens", 0)
            ) if live_model_calls else (
                BASE._approx_tokens(cycle1["parsed"])
                + BASE._approx_tokens(cycle2["parsed"])
            ),
            "source": "provider_usage" if live_model_calls else "approx_char_div_4",
        },
    }
    scheduler_checks = symbolic_scheduler_checks_for_row(
        row_root=row_root,
        task_id=task_id,
        event_identity=event_identity,
        trace=trace,
        restart_frontier=restart_frontier,
        selection=cycle1["parsed"],
        bound_continuation=bound_continuation,
    )
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": cycle2["parsed"],
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "scheduler_checks": scheduler_checks,
        "observability_score": BASE.score_row_observability(
            condition=condition,
            scheduler_checks=scheduler_checks,
            context_accounting=context_accounting,
            artifact_score=artifact_score,
        ),
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
        "taste_open_log": "taste_open.jsonl" if live_model_calls else None,
        "symbolic_contract": SYMBOLIC_CONTRACT,
    }
    BASE._write_json(row_root / "context_accounting.json", context_accounting)
    BASE._write_json(row_root / "score.json", artifact_score)
    BASE._write_json(row_root / "observability_score.json", row["observability_score"])
    BASE._write_json(row_root / "row_result.json", row)
    return row


def run_panel(
    *,
    output_root: Path = ROOT_DIR,
    overwrite: bool = False,
    live_model_calls: bool = False,
    api_key: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    terminal_tool_choice: str | None = None,
) -> JsonDict:
    if live_model_calls and not api_key:
        raise ValueError("api_key is required for live model calls")
    prepare_output_root(output_root, overwrite=overwrite)
    write_preregistration_artifacts(
        output_root,
        live_model_calls=live_model_calls,
    )
    started_at = utc_now_iso()
    rows: list[JsonDict] = []
    resolved_tool_choice = terminal_tool_choice or BASE.default_terminal_tool_choice(
        endpoint
    )
    for task_id in TASKS:
        rows.append(
            run_symbolic_event_loop_row(
                task_id=task_id,
                output_root=output_root,
                live_model_calls=live_model_calls,
                api_key=api_key,
                endpoint=endpoint,
                model=model,
                max_tokens=max_tokens,
                terminal_tool_choice=resolved_tool_choice,
            )
        )
        if live_model_calls:
            rows.append(
                BASE.run_live_append_only_row(
                    task_id=task_id,
                    output_root=output_root,
                    api_key=api_key or "",
                    endpoint=endpoint,
                    model=model,
                    max_tokens=max_tokens,
                    terminal_tool_choice=resolved_tool_choice,
                )
            )
        else:
            rows.append(BASE.run_append_only_row(task_id=task_id, output_root=output_root))

    scheduler = BASE.score_scheduler_viability(rows)
    noninferiority = BASE.score_noninferiority(rows)
    shared_observability = BASE.score_shared_surface_observability(rows)
    scheduler_added_value = BASE.score_scheduler_added_value(rows)
    summary = BASE.summarize(
        scheduler=scheduler,
        noninferiority=noninferiority,
        shared_observability=shared_observability,
        scheduler_added_value=scheduler_added_value,
        live_model_calls=live_model_calls,
    )
    results = {
        "schema_version": "hamutay.symbolic_append_only_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": utc_now_iso(),
        "live_model_calls": live_model_calls,
        "model": model if live_model_calls else None,
        "endpoint": endpoint if live_model_calls else None,
        "terminal_tool_choice": resolved_tool_choice if live_model_calls else None,
        "symbolic_contract": SYMBOLIC_CONTRACT,
        "classification": summary["classification"],
        "rows": rows,
        "scheduler_viability": scheduler,
        "artifact_noninferiority": noninferiority,
        "shared_surface_observability": shared_observability,
        "scheduler_added_value": scheduler_added_value,
        "summary": summary,
    }
    BASE._write_json(output_root / "results.json", results)
    (output_root / "analysis.md").write_text(BASE.render_analysis(results), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--write-prereg", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--terminal-tool-choice",
        choices=["auto", "required", "force"],
        default=None,
    )
    args = parser.parse_args(argv)

    if args.write_prereg:
        write_preregistration_artifacts(
            args.output_root,
            live_model_calls=args.live,
        )
        print(json.dumps({"experiment_id": EXPERIMENT_ID, "preregistered": True}))
        return 0
    if not args.dry_run and not args.live:
        parser.error("choose --dry-run or --live")
    api_key = args.api_key or os.environ.get(args.api_key_env, "")
    result = run_panel(
        output_root=args.output_root,
        overwrite=args.overwrite,
        live_model_calls=args.live,
        api_key=api_key if args.live else None,
        endpoint=args.endpoint,
        model=args.model,
        max_tokens=args.max_tokens,
        terminal_tool_choice=args.terminal_tool_choice,
    )
    print(json.dumps({"classification": result["classification"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
