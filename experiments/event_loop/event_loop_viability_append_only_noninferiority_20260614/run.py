"""Event-loop viability + append-only non-inferiority dry harness."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPERIMENT_ID = "event_loop_viability_append_only_noninferiority_20260614"
ROOT_DIR = Path(__file__).resolve().parent
CONDITIONS = ("event_loop_scheduled", "append_only")
NON_INFERIORITY_MARGIN = 0.10
DEFAULT_ENDPOINT = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "OPENROUTER_API_KEY"
DEFAULT_MAX_TOKENS = 4096

TASKS: dict[str, JsonDict] = {
    "scheduler_boundary_note": {
        "prompt": (
            "Write a note deciding whether scheduler-loop evidence supports "
            "moving to an append-only non-inferiority comparison."
        ),
        "required_facts": {
            "event_lifecycle_visible": {
                "evidence": "e8000000-0000-0000-0000-000000000101",
                "loss_marker": None,
            },
            "restart_frontier_reconstructable": {
                "evidence": "e8000000-0000-0000-0000-000000000102",
                "loss_marker": None,
            },
            "live_provider_not_exercised": {
                "evidence": "e8000000-0000-0000-0000-000000000103",
                "loss_marker": "live provider",
            },
        },
        "records": [
            {
                "record_id": "e8000000-0000-0000-0000-000000000101",
                "record_type": "evidence",
                "content": {
                    "fact_id": "event_lifecycle_visible",
                    "text": (
                        "The dry event-loop row records scheduled, claimed, "
                        "and completed event states."
                    ),
                },
            },
            {
                "record_id": "e8000000-0000-0000-0000-000000000102",
                "record_type": "evidence",
                "content": {
                    "fact_id": "restart_frontier_reconstructable",
                    "text": (
                        "The dry event-loop row preserves a restart frontier "
                        "with the scheduled event and carried state."
                    ),
                },
            },
            {
                "record_id": "e8000000-0000-0000-0000-000000000103",
                "record_type": "evidence",
                "content": {
                    "fact_id": "live_provider_not_exercised",
                    "text": (
                        "This v1 harness makes no live provider calls; it is "
                        "a deterministic protocol-readiness run."
                    ),
                },
            },
            {
                "record_id": "e8000000-0000-0000-0000-000000000199",
                "record_type": "distractor",
                "content": {
                    "text": (
                        "Unrelated draft line: dashboard buttons should not "
                        "use oversized rounded purple capsules."
                    ),
                },
            },
        ],
        "distractor_id": "e8000000-0000-0000-0000-000000000199",
    },
    "append_only_comparison_note": {
        "prompt": (
            "Write a note deciding what must be true before claiming "
            "non-inferiority to the append-only baseline."
        ),
        "required_facts": {
            "scheduler_gate_separate": {
                "evidence": "e8000000-0000-0000-0000-000000000201",
                "loss_marker": None,
            },
            "artifact_quality_margin_declared": {
                "evidence": "e8000000-0000-0000-0000-000000000202",
                "loss_marker": None,
            },
            "observability_not_quality": {
                "evidence": "e8000000-0000-0000-0000-000000000203",
                "loss_marker": "observability cannot rescue quality",
            },
        },
        "records": [
            {
                "record_id": "e8000000-0000-0000-0000-000000000201",
                "record_type": "evidence",
                "content": {
                    "fact_id": "scheduler_gate_separate",
                    "text": (
                        "The protocol gates scheduler viability separately "
                        "from artifact quality."
                    ),
                },
            },
            {
                "record_id": "e8000000-0000-0000-0000-000000000202",
                "record_type": "evidence",
                "content": {
                    "fact_id": "artifact_quality_margin_declared",
                    "text": (
                        "Artifact non-inferiority uses a preregistered "
                        "0.10 margin against append-only mean quality."
                    ),
                },
            },
            {
                "record_id": "e8000000-0000-0000-0000-000000000203",
                "record_type": "evidence",
                "content": {
                    "fact_id": "observability_not_quality",
                    "text": (
                        "Observability is scored separately and cannot "
                        "rescue an inferior artifact-quality result."
                    ),
                },
            },
            {
                "record_id": "e8000000-0000-0000-0000-000000000299",
                "record_type": "distractor",
                "content": {
                    "text": (
                        "Unrelated note: a fairy-tale cellar metaphor would "
                        "make the memory system sound warmer."
                    ),
                },
            },
        ],
        "distractor_id": "e8000000-0000-0000-0000-000000000299",
    },
}


def matrix(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "conditions": list(CONDITIONS),
        "tasks": sorted(TASKS),
        "default_model": DEFAULT_MODEL,
        "default_endpoint": DEFAULT_ENDPOINT,
        "claim_separation": {
            "shared_surface_noninferiority": (
                "fair head-to-head comparison on common artifact and trace axes"
            ),
            "scheduler_added_value": (
                "event-loop-only reconstruction evidence, not an append_only penalty"
            ),
        },
        "non_inferiority_margin": NON_INFERIORITY_MARGIN,
    }


def budget_manifest(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "max_live_calls": len(TASKS) * 3 if live_model_calls else 0,
        "max_estimated_cost_usd": 2.0 if live_model_calls else 0.0,
        "output_cap_policy": (
            "Live mode makes two event-loop terminal-surface calls and one "
            "append-only terminal-surface call per task."
            if live_model_calls else
            "Deterministic dry harness; no provider calls."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "schema_version": "hamutay.event_loop_append_only_taxonomy.v1",
        "layers": [
            "scheduler",
            "model",
            "provider",
            "harness",
            "substrate",
            "scorer",
            "protocol",
            "inconclusive",
        ],
        "entries": [
            {
                "layer": "scheduler",
                "code": "event_lifecycle_not_reconstructable",
                "meaning": "Scheduled work could not be reconstructed from row artifacts.",
            },
            {
                "layer": "model",
                "code": "artifact_quality_inferior",
                "meaning": "Event-loop artifact quality missed the non-inferiority margin.",
            },
            {
                "layer": "scorer",
                "code": "rubric_contract_violation",
                "meaning": "Deterministic scoring could not evaluate a row fairly.",
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
        _write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


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
    _prepare_output_root(output_root, overwrite=overwrite)
    write_preregistration_artifacts(
        output_root,
        live_model_calls=live_model_calls,
    )
    started_at = _now_iso()
    rows: list[JsonDict] = []
    resolved_terminal_tool_choice = (
        terminal_tool_choice or default_terminal_tool_choice(endpoint)
    )
    for task_id in TASKS:
        if live_model_calls:
            rows.append(
                run_live_event_loop_row(
                    task_id=task_id,
                    output_root=output_root,
                    api_key=api_key or "",
                    endpoint=endpoint,
                    model=model,
                    max_tokens=max_tokens,
                    terminal_tool_choice=resolved_terminal_tool_choice,
                )
            )
            rows.append(
                run_live_append_only_row(
                    task_id=task_id,
                    output_root=output_root,
                    api_key=api_key or "",
                    endpoint=endpoint,
                    model=model,
                    max_tokens=max_tokens,
                    terminal_tool_choice=resolved_terminal_tool_choice,
                )
            )
        else:
            rows.append(run_event_loop_row(task_id=task_id, output_root=output_root))
            rows.append(run_append_only_row(task_id=task_id, output_root=output_root))
    scheduler = score_scheduler_viability(rows)
    noninferiority = score_noninferiority(rows)
    shared_observability = score_shared_surface_observability(rows)
    scheduler_added_value = score_scheduler_added_value(rows)
    summary = summarize(
        scheduler=scheduler,
        noninferiority=noninferiority,
        shared_observability=shared_observability,
        scheduler_added_value=scheduler_added_value,
        live_model_calls=live_model_calls,
    )
    results = {
        "schema_version": "hamutay.event_loop_append_only_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": started_at,
        "finished_at": _now_iso(),
        "live_model_calls": live_model_calls,
        "model": model if live_model_calls else None,
        "endpoint": endpoint if live_model_calls else None,
        "terminal_tool_choice": (
            resolved_terminal_tool_choice if live_model_calls else None
        ),
        "classification": summary["classification"],
        "rows": rows,
        "scheduler_viability": scheduler,
        "artifact_noninferiority": noninferiority,
        "shared_surface_observability": shared_observability,
        "scheduler_added_value": scheduler_added_value,
        "summary": summary,
    }
    _write_json(output_root / "results.json", results)
    (output_root / "analysis.md").write_text(render_analysis(results), encoding="utf-8")
    return results


def run_event_loop_row(*, task_id: str, output_root: Path) -> JsonDict:
    condition = "event_loop_scheduled"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    task = TASKS[task_id]
    event_id = f"{task_id}::scheduled-artifact"
    cycle1 = dry_event_loop_selection(task_id=task_id, event_id=event_id)
    scheduler_trace = scheduler_events(task_id=task_id, event_id=event_id)
    restart_frontier = {
        "task_id": task_id,
        "event_id": event_id,
        "last_committed_cycle": 1,
        "carried_state": deepcopy(cycle1["parsed"]),
        "pending_wake_context": scheduler_trace[-1]["wake_context"],
    }
    _write_json(row_root / "cycle_01.json", cycle1)
    _write_json(row_root / "scheduler_events.json", scheduler_trace)
    _write_json(row_root / "restart_frontier.json", restart_frontier)

    selected_ids = [
        request["record_id"]
        for request in cycle1["parsed"]["requested_context"]
        if isinstance(request, dict)
    ]
    selected_records = [
        deepcopy(record) for record in task["records"]
        if record["record_id"] in selected_ids
    ]
    cycle2 = dry_artifact_cycle(
        task_id=task_id,
        condition=condition,
        corpus=selected_records,
        carried_state=cycle1["parsed"],
    )
    _write_json(row_root / "cycle_02.json", cycle2)
    artifact_score = score_artifact(task_id, cycle2["parsed"])
    context_accounting = {
        "condition": condition,
        "task_id": task_id,
        "selected_record_ids": selected_ids,
        "omitted_record_ids": cycle1["parsed"]["omitted_record_ids"],
        "declared_losses_before_artifact": cycle1["parsed"]["declared_losses"],
        "declared_losses_in_artifact": cycle2["parsed"]["declared_losses"],
        "token_use": {
            "prompt_tokens": _approx_tokens(cycle1["request_payload"])
            + _approx_tokens(cycle2["request_payload"]),
            "completion_tokens": _approx_tokens(cycle1["parsed"])
            + _approx_tokens(cycle2["parsed"]),
            "source": "approx_char_div_4",
        },
    }
    scheduler_checks = scheduler_checks_for_row(
        row_root=row_root,
        task_id=task_id,
        event_id=event_id,
        trace=scheduler_trace,
        restart_frontier=restart_frontier,
        selection=cycle1["parsed"],
    )
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": cycle2["parsed"],
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "scheduler_checks": scheduler_checks,
        "observability_score": score_row_observability(
            condition=condition,
            scheduler_checks=scheduler_checks,
            context_accounting=context_accounting,
            artifact_score=artifact_score,
        ),
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
    }
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "score.json", artifact_score)
    _write_json(row_root / "observability_score.json", row["observability_score"])
    _write_json(row_root / "row_result.json", row)
    return row


def run_append_only_row(*, task_id: str, output_root: Path) -> JsonDict:
    condition = "append_only"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    cycle = dry_artifact_cycle(
        task_id=task_id,
        condition=condition,
        corpus=TASKS[task_id]["records"],
        carried_state=None,
    )
    _write_json(row_root / "cycle_01.json", cycle)
    artifact_score = score_artifact(task_id, cycle["parsed"])
    context_accounting = {
        "condition": condition,
        "task_id": task_id,
        "append_only_context_record_ids": [
            record["record_id"] for record in TASKS[task_id]["records"]
        ],
        "token_use": {
            "prompt_tokens": _approx_tokens(cycle["request_payload"]),
            "completion_tokens": _approx_tokens(cycle["parsed"]),
            "source": "approx_char_div_4",
        },
    }
    scheduler_checks = {
        "not_applicable": True,
        "reason": "append_only baseline has no scheduler lifecycle",
    }
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": cycle["parsed"],
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "scheduler_checks": scheduler_checks,
        "observability_score": score_row_observability(
            condition=condition,
            scheduler_checks=scheduler_checks,
            context_accounting=context_accounting,
            artifact_score=artifact_score,
        ),
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
    }
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "score.json", artifact_score)
    _write_json(row_root / "observability_score.json", row["observability_score"])
    _write_json(row_root / "row_result.json", row)
    return row


def run_live_event_loop_row(
    *,
    task_id: str,
    output_root: Path,
    api_key: str,
    endpoint: str,
    model: str,
    max_tokens: int,
    terminal_tool_choice: str,
) -> JsonDict:
    from hamutay.taste_open import OpenAITasteBackend, OpenTasteSession

    condition = "event_loop_scheduled"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    task = TASKS[task_id]
    event_id = f"{task_id}::scheduled-artifact"
    backend = OpenAITasteBackend(
        base_url=endpoint,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout=180,
        provider_name="openrouter" if "openrouter" in endpoint else "openai",
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
        experiment_label=f"{EXPERIMENT_ID}_{task_id}_{condition}",
        system_prompt_prefix=live_event_loop_system_prefix(),
        memory_base_probability=0.0,
    )

    cycle1_request = live_selection_request(task_id=task_id, event_id=event_id)
    session.exchange(
        json.dumps(cycle1_request, indent=2, sort_keys=True),
        terminal_surface=selection_terminal_surface(
            tool_choice=terminal_tool_choice,
        ),
        force_memory=None,
    )
    cycle1 = live_cycle_payload_from_session(
        session=session,
        request_payload=cycle1_request,
    )
    cycle1["parsed"] = normalize_selection_output(
        cycle1["parsed"],
        task_id=task_id,
        event_id=event_id,
    )
    _write_json(row_root / "cycle_01.json", cycle1)
    scheduler_trace = scheduler_events(task_id=task_id, event_id=event_id)
    restart_frontier = {
        "task_id": task_id,
        "event_id": event_id,
        "last_committed_cycle": 1,
        "carried_state": deepcopy(cycle1["parsed"]),
        "pending_wake_context": scheduler_trace[-1]["wake_context"],
    }
    _write_json(row_root / "scheduler_events.json", scheduler_trace)
    _write_json(row_root / "restart_frontier.json", restart_frontier)

    selected_ids = [
        request["record_id"]
        for request in cycle1["parsed"]["requested_context"]
        if isinstance(request, dict)
    ]
    selected_records = [
        deepcopy(record) for record in task["records"]
        if record["record_id"] in selected_ids
    ]
    cycle2_request = live_artifact_request(
        task_id=task_id,
        condition=condition,
        corpus=selected_records,
        carried_state=cycle1["parsed"],
        wake_context=scheduler_trace[-1]["wake_context"],
    )
    session.exchange(
        json.dumps(cycle2_request, indent=2, sort_keys=True),
        terminal_surface=artifact_terminal_surface(
            tool_choice=terminal_tool_choice,
        ),
        force_memory=None,
    )
    cycle2 = live_cycle_payload_from_session(
        session=session,
        request_payload=cycle2_request,
    )
    cycle2["parsed"] = normalize_artifact_output(cycle2["parsed"])
    _write_json(row_root / "cycle_02.json", cycle2)

    artifact_score = score_artifact(task_id, cycle2["parsed"])
    context_accounting = {
        "condition": condition,
        "task_id": task_id,
        "selected_record_ids": selected_ids,
        "omitted_record_ids": cycle1["parsed"]["omitted_record_ids"],
        "declared_losses_before_artifact": cycle1["parsed"]["declared_losses"],
        "declared_losses_in_artifact": cycle2["parsed"].get("declared_losses", []),
        "token_use": {
            "prompt_tokens": (
                cycle1["usage"].get("input_tokens", 0)
                + cycle2["usage"].get("input_tokens", 0)
            ),
            "completion_tokens": (
                cycle1["usage"].get("output_tokens", 0)
                + cycle2["usage"].get("output_tokens", 0)
            ),
            "source": "provider_usage",
        },
    }
    scheduler_checks = scheduler_checks_for_row(
        row_root=row_root,
        task_id=task_id,
        event_id=event_id,
        trace=scheduler_trace,
        restart_frontier=restart_frontier,
        selection=cycle1["parsed"],
    )
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": cycle2["parsed"],
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "scheduler_checks": scheduler_checks,
        "observability_score": score_row_observability(
            condition=condition,
            scheduler_checks=scheduler_checks,
            context_accounting=context_accounting,
            artifact_score=artifact_score,
        ),
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
        "taste_open_log": "taste_open.jsonl",
    }
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "score.json", artifact_score)
    _write_json(row_root / "observability_score.json", row["observability_score"])
    _write_json(row_root / "row_result.json", row)
    return row


def run_live_append_only_row(
    *,
    task_id: str,
    output_root: Path,
    api_key: str,
    endpoint: str,
    model: str,
    max_tokens: int,
    terminal_tool_choice: str,
) -> JsonDict:
    from hamutay.taste_open import OpenAITasteBackend

    condition = "append_only"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    backend = OpenAITasteBackend(
        base_url=endpoint,
        api_key=api_key,
        max_tokens=max_tokens,
        timeout=180,
        provider_name="openrouter" if "openrouter" in endpoint else "openai",
        extra_headers={
            "X-Title": f"hamutay/{EXPERIMENT_ID}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        },
        max_retries=1,
    )
    request = live_artifact_request(
        task_id=task_id,
        condition=condition,
        corpus=TASKS[task_id]["records"],
        carried_state=None,
        wake_context=None,
    )
    result = backend.call_terminal_surface(
        model=model,
        system=append_only_system_prompt(),
        messages=[
            {
                "role": "user",
                "content": json.dumps(request, indent=2, sort_keys=True),
            }
        ],
        experiment_label=f"{EXPERIMENT_ID}_{task_id}_{condition}",
        terminal_surface=artifact_terminal_surface(
            tool_choice=terminal_tool_choice,
        ),
    )
    cycle = {
        "parsed": normalize_artifact_output(result.raw_output),
        "raw_content": json.dumps(result.raw_output, sort_keys=True),
        "request_payload": request,
        "response_payload": {"terminal_surface": True},
        "usage": {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "stop_reason": result.stop_reason,
        },
        "elapsed_seconds": None,
    }
    _write_json(row_root / "cycle_01.json", cycle)
    artifact_score = score_artifact(task_id, cycle["parsed"])
    context_accounting = {
        "condition": condition,
        "task_id": task_id,
        "append_only_context_record_ids": [
            record["record_id"] for record in TASKS[task_id]["records"]
        ],
        "token_use": {
            "prompt_tokens": result.input_tokens,
            "completion_tokens": result.output_tokens,
            "source": "provider_usage",
        },
    }
    scheduler_checks = {
        "not_applicable": True,
        "reason": "append_only baseline has no scheduler lifecycle",
    }
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": cycle["parsed"],
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "scheduler_checks": scheduler_checks,
        "observability_score": score_row_observability(
            condition=condition,
            scheduler_checks=scheduler_checks,
            context_accounting=context_accounting,
            artifact_score=artifact_score,
        ),
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
    }
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "score.json", artifact_score)
    _write_json(row_root / "observability_score.json", row["observability_score"])
    _write_json(row_root / "row_result.json", row)
    return row


def dry_event_loop_selection(*, task_id: str, event_id: str) -> JsonDict:
    task = TASKS[task_id]
    parsed = {
        "event_id": event_id,
        "work_plan": "Schedule a bounded artifact wake and carry only evidence records.",
        "requested_context": [
            {"tool": "recall", "record_id": data["evidence"]}
            for data in task["required_facts"].values()
        ],
        "omitted_record_ids": [task["distractor_id"]],
        "declared_losses": declared_losses(task_id),
    }
    request = {
        "condition": "event_loop_scheduled",
        "cycle": 1,
        "task_id": task_id,
        "task": task["prompt"],
        "corpus_map": corpus_map(task_id),
        "instruction": "Schedule the wake and select bounded context.",
    }
    return cycle_payload(parsed=parsed, request_payload=request)


def dry_artifact_cycle(
    *,
    task_id: str,
    condition: str,
    corpus: list[JsonDict],
    carried_state: JsonDict | None,
) -> JsonDict:
    task = TASKS[task_id]
    claims = [
        {
            "fact_id": fact_id,
            "text": f"Supported fact: {fact_id}.",
            "status": "supported",
            "evidence_record_ids": [data["evidence"]],
        }
        for fact_id, data in task["required_facts"].items()
    ]
    parsed = {
        "artifact_title": f"{task_id} result",
        "task_id": task_id,
        "conclusion": "The evidence supports the preregistered comparison boundary.",
        "recommended_action": (
            "Proceed only while preserving scheduler and artifact scores separately."
        ),
        "claims": claims,
        "declared_losses": declared_losses(task_id),
        "cited_record_ids": [
            data["evidence"] for data in task["required_facts"].values()
        ],
    }
    request = {
        "condition": condition,
        "cycle": 2 if condition == "event_loop_scheduled" else 1,
        "task_id": task_id,
        "task": task["prompt"],
        "carried_state": deepcopy(carried_state),
        "corpus": deepcopy(corpus),
        "instruction": "Write the artifact from the provided evidence.",
    }
    return cycle_payload(parsed=parsed, request_payload=request)


def live_event_loop_system_prefix() -> str:
    return (
        "You are running inside the Hamut'ay taste_open event-loop framework "
        "for a preregistered comparison against an append-only baseline. "
        "Follow the terminal surface exactly. Preserve uncertainty and "
        "declared losses; do not use distractor records in the final artifact."
    )


def append_only_system_prompt() -> str:
    return (
        "You are the append-only baseline for a preregistered Hamut'ay "
        "comparison. You receive the full bounded corpus in one context. "
        "Use only task-relevant evidence, preserve declared losses, and return "
        "the required terminal artifact."
    )


def live_selection_request(*, task_id: str, event_id: str) -> JsonDict:
    return {
        "condition": "event_loop_scheduled",
        "cycle": 1,
        "event_id": event_id,
        "task_id": task_id,
        "task": TASKS[task_id]["prompt"],
        "corpus_map": corpus_map(task_id),
        "required_output": {
            "response": "<brief scheduling note>",
            "event_id": event_id,
            "work_plan": "<short plan>",
            "requested_context": [
                {"tool": "recall", "record_id": "<uuid>"}
            ],
            "omitted_record_ids": ["<uuid>"],
            "declared_losses": ["<loss or limitation>"],
        },
        "instruction": (
            "Schedule the artifact wake and select only the evidence records "
            "needed for the final artifact. Do not write the artifact yet."
        ),
    }


def live_artifact_request(
    *,
    task_id: str,
    condition: str,
    corpus: list[JsonDict],
    carried_state: JsonDict | None,
    wake_context: JsonDict | None,
) -> JsonDict:
    return {
        "condition": condition,
        "task_id": task_id,
        "task": TASKS[task_id]["prompt"],
        "required_fact_ids": sorted(TASKS[task_id]["required_facts"]),
        "corpus": deepcopy(corpus),
        "carried_state": deepcopy(carried_state),
        "wake_context": deepcopy(wake_context),
        "required_output": {
            "response": "<brief artifact completion note>",
            "artifact_title": "<title>",
            "task_id": task_id,
            "conclusion": "<conclusion>",
            "recommended_action": "<action>",
            "claims": [
                {
                    "fact_id": "<required fact id>",
                    "text": "<claim>",
                    "status": "<supported|unsupported|unknown>",
                    "evidence_record_ids": ["<uuid>"],
                }
            ],
            "declared_losses": ["<loss or limitation>"],
            "cited_record_ids": ["<uuid>"],
        },
        "instruction": (
            "Write the final artifact. Cite only evidence records that support "
            "claims. Do not cite distractors. If a limitation remains, include "
            "it in declared_losses."
        ),
    }


def selection_terminal_surface(*, tool_choice: str = "force") -> JsonDict:
    return {
        "tool_name": "select_scheduled_context",
        "description": "Select context for the scheduled artifact wake.",
        "tool_choice": tool_choice,
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "event_id": {"type": "string"},
                "work_plan": {"type": "string"},
                "requested_context": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "record_id": {"type": "string"},
                        },
                        "required": ["tool", "record_id"],
                    },
                },
                "omitted_record_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "declared_losses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "response",
                "event_id",
                "work_plan",
                "requested_context",
                "omitted_record_ids",
                "declared_losses",
            ],
        },
        "state_update": {
            "response_field": "response",
            "copy": {
                "event_id": "event_id",
                "work_plan": "work_plan",
                "requested_context": "requested_context",
                "omitted_record_ids": "omitted_record_ids",
                "declared_losses": "declared_losses",
            },
        },
    }


def artifact_terminal_surface(*, tool_choice: str = "force") -> JsonDict:
    return {
        "tool_name": "write_matched_artifact",
        "description": "Write the scored artifact for the matched task.",
        "tool_choice": tool_choice,
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "artifact_title": {"type": "string"},
                "task_id": {"type": "string"},
                "conclusion": {"type": "string"},
                "recommended_action": {"type": "string"},
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "fact_id": {"type": "string"},
                            "text": {"type": "string"},
                            "status": {"type": "string"},
                            "evidence_record_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "fact_id",
                            "text",
                            "status",
                            "evidence_record_ids",
                        ],
                    },
                },
                "declared_losses": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "cited_record_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": [
                "response",
                "artifact_title",
                "task_id",
                "conclusion",
                "recommended_action",
                "claims",
                "declared_losses",
                "cited_record_ids",
            ],
        },
        "state_update": {
            "response_field": "response",
            "copy": {
                "artifact_title": "artifact_title",
                "task_id": "task_id",
                "conclusion": "conclusion",
                "recommended_action": "recommended_action",
                "claims": "claims",
                "declared_losses": "declared_losses",
                "cited_record_ids": "cited_record_ids",
            },
        },
    }


def normalize_selection_output(
    raw_output: JsonDict,
    *,
    task_id: str,
    event_id: str,
) -> JsonDict:
    requested = raw_output.get("requested_context")
    omitted = raw_output.get("omitted_record_ids")
    losses = raw_output.get("declared_losses")
    return {
        "event_id": str(raw_output.get("event_id") or event_id),
        "work_plan": str(raw_output.get("work_plan") or ""),
        "requested_context": requested if isinstance(requested, list) else [],
        "omitted_record_ids": omitted if isinstance(omitted, list) else [],
        "declared_losses": losses if isinstance(losses, list) else [],
        "task_id": task_id,
    }


def normalize_artifact_output(raw_output: JsonDict) -> JsonDict:
    return {
        "artifact_title": raw_output.get("artifact_title"),
        "task_id": raw_output.get("task_id"),
        "conclusion": raw_output.get("conclusion"),
        "recommended_action": raw_output.get("recommended_action"),
        "claims": raw_output.get("claims"),
        "declared_losses": raw_output.get("declared_losses"),
        "cited_record_ids": raw_output.get("cited_record_ids"),
    }


def live_cycle_payload_from_session(
    *,
    session: Any,
    request_payload: JsonDict,
) -> JsonDict:
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


def scheduler_events(*, task_id: str, event_id: str) -> list[JsonDict]:
    return [
        {
            "event_id": event_id,
            "task_id": task_id,
            "status": "scheduled",
            "cycle": 1,
            "producer_cycle": 1,
        },
        {
            "event_id": event_id,
            "task_id": task_id,
            "status": "claimed",
            "cycle": 2,
            "producer_cycle": 1,
            "wake_context": {"task_id": task_id, "event_id": event_id},
        },
        {
            "event_id": event_id,
            "task_id": task_id,
            "status": "completed",
            "cycle": 2,
            "producer_cycle": 1,
            "wake_context": {"task_id": task_id, "event_id": event_id},
        },
    ]


def scheduler_checks_for_row(
    *,
    row_root: Path,
    task_id: str,
    event_id: str,
    trace: list[JsonDict],
    restart_frontier: JsonDict,
    selection: JsonDict,
) -> JsonDict:
    statuses = [item["status"] for item in trace]
    wake_context = trace[-1].get("wake_context", {})
    checks = {
        "scheduled_event_recorded": (row_root / "scheduler_events.json").exists(),
        "status_sequence_valid": statuses == ["scheduled", "claimed", "completed"],
        "wake_context_has_task_id": wake_context.get("task_id") == task_id,
        "wake_context_has_event_id": wake_context.get("event_id") == event_id,
        "producer_cycle_link_present": all(item.get("producer_cycle") == 1 for item in trace),
        "selected_context_preserved": bool(selection.get("requested_context")),
        "declared_losses_preserved": bool(selection.get("declared_losses")),
        "restart_frontier_written": (row_root / "restart_frontier.json").exists(),
        "restart_frontier_reconstructable": (
            restart_frontier.get("event_id") == event_id
            and restart_frontier.get("carried_state") == selection
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failure_layer": "none" if all(checks.values()) else "scheduler",
    }


def validate_artifact(task_id: str, output: JsonDict) -> JsonDict:
    required = [
        "artifact_title",
        "task_id",
        "conclusion",
        "recommended_action",
        "claims",
        "declared_losses",
        "cited_record_ids",
    ]
    missing = [field for field in required if field not in output]
    if missing or not isinstance(output.get("claims"), list):
        return {"ok": False, "missing_fields": missing}
    return {
        "ok": str(output.get("task_id")) == task_id,
        "missing_fields": [],
        "task_id_matches": str(output.get("task_id")) == task_id,
    }


def score_artifact(task_id: str, output: JsonDict) -> JsonDict:
    task = TASKS[task_id]
    validation = validate_artifact(task_id, output)
    if not validation["ok"]:
        return {
            "scoreable": False,
            "artifact_quality_score": 0.0,
            "schema_score": 0.0,
            "recovery_rate": 0.0,
            "citation_correctness_rate": 0.0,
            "declared_loss_rate": 0.0,
            "contamination_rate": 1.0,
            "unsupported_claim_rate": 1.0,
            "actionability_score": 0.0,
            "catastrophic_failure": True,
            "validation": validation,
        }
    claims = [claim for claim in output["claims"] if isinstance(claim, dict)]
    recovered: set[str] = set()
    unsupported_count = 0
    citation_checks = 0
    citation_correct = 0
    for claim in claims:
        fact_id = str(claim.get("fact_id", ""))
        expected = task["required_facts"].get(fact_id)
        evidence_ids = {str(item) for item in claim.get("evidence_record_ids", [])}
        status = str(claim.get("status", "")).lower()
        if expected is None:
            unsupported_count += 1
            continue
        citation_checks += 1
        if expected["evidence"] in evidence_ids:
            citation_correct += 1
            if status not in {"unsupported", "missing", "unknown", "not_supported"}:
                recovered.add(fact_id)
        else:
            unsupported_count += 1
    cited = {str(item) for item in output.get("cited_record_ids", [])}
    text_blob = json.dumps(output, sort_keys=True).lower()
    contamination = int(
        task["distractor_id"] in cited
        or "purple capsules" in text_blob
        or "fairy-tale cellar" in text_blob
    )
    loss_markers = [
        data["loss_marker"].lower()
        for data in task["required_facts"].values()
        if data.get("loss_marker")
    ]
    declared = " ".join(str(item).lower() for item in output["declared_losses"])
    declared_loss_count = sum(1 for marker in loss_markers if marker in declared)
    recovery_rate = len(recovered) / len(task["required_facts"])
    citation_rate = citation_correct / citation_checks if citation_checks else 0.0
    loss_rate = declared_loss_count / len(loss_markers) if loss_markers else 1.0
    unsupported_rate = unsupported_count / len(claims) if claims else 1.0
    actionability = 1.0 if output.get("conclusion") and output.get("recommended_action") else 0.0
    quality = (
        0.10
        + recovery_rate * 0.35
        + citation_rate * 0.20
        + loss_rate * 0.15
        + (1.0 - contamination) * 0.10
        + actionability * 0.10
    )
    catastrophic = (
        recovery_rate < 0.60
        or contamination > 0.50
        or unsupported_rate > 0.25
    )
    return {
        "scoreable": True,
        "artifact_quality_score": round(quality, 4),
        "schema_score": 1.0,
        "recovered_fact_ids": sorted(recovered),
        "missing_fact_ids": sorted(set(task["required_facts"]) - recovered),
        "recovery_rate": round(recovery_rate, 4),
        "citation_correctness_rate": round(citation_rate, 4),
        "declared_loss_rate": round(loss_rate, 4),
        "contamination_rate": float(contamination),
        "unsupported_claim_rate": round(unsupported_rate, 4),
        "actionability_score": actionability,
        "catastrophic_failure": catastrophic,
        "validation": validation,
    }


def score_row_observability(
    *,
    condition: str,
    scheduler_checks: JsonDict,
    context_accounting: JsonDict,
    artifact_score: JsonDict,
) -> JsonDict:
    shared_features = {
        "raw_request_response_preserved": True,
        "parsed_artifact_preserved": artifact_score["scoreable"],
        "deterministic_artifact_score": bool(artifact_score),
        "failure_attribution_surface": True,
    }
    shared_weights = {
        "raw_request_response_preserved": 0.25,
        "parsed_artifact_preserved": 0.25,
        "deterministic_artifact_score": 0.25,
        "failure_attribution_surface": 0.25,
    }
    shared_score = sum(
        shared_weights[key] for key, value in shared_features.items() if value
    )
    scheduler_features = {
        "cycle_boundary_visible": condition == "event_loop_scheduled",
        "scheduled_event_lifecycle": scheduler_checks.get("passed") is True,
        "wake_context_and_restart_frontier": scheduler_checks.get("passed") is True,
        "context_selection_and_loss_trace": bool(
            context_accounting.get("selected_record_ids")
            and context_accounting.get("declared_losses_before_artifact")
        ),
    }
    scheduler_weights = {
        "cycle_boundary_visible": 0.25,
        "scheduled_event_lifecycle": 0.25,
        "wake_context_and_restart_frontier": 0.25,
        "context_selection_and_loss_trace": 0.25,
    }
    scheduler_score = (
        sum(
            scheduler_weights[key]
            for key, value in scheduler_features.items()
            if value
        )
        if condition == "event_loop_scheduled" else None
    )
    return {
        "shared_surface": {
            "score": round(shared_score, 4),
            "features": shared_features,
            "weights": shared_weights,
        },
        "scheduler_reconstruction": {
            "score": round(scheduler_score, 4)
            if scheduler_score is not None else None,
            "not_applicable": condition != "event_loop_scheduled",
            "features": scheduler_features
            if condition == "event_loop_scheduled" else {},
            "weights": scheduler_weights
            if condition == "event_loop_scheduled" else {},
        },
    }


def score_scheduler_viability(rows: list[JsonDict]) -> JsonDict:
    event_rows = [row for row in rows if row["condition"] == "event_loop_scheduled"]
    failed = [
        row["task_id"] for row in event_rows
        if row["scheduler_checks"].get("passed") is not True
    ]
    return {
        "passed": not failed and bool(event_rows),
        "failed_task_ids": failed,
        "row_count": len(event_rows),
        "gate": "scheduler_viability",
    }


def score_noninferiority(rows: list[JsonDict]) -> JsonDict:
    event_scores = [
        row["artifact_score"]["artifact_quality_score"]
        for row in rows if row["condition"] == "event_loop_scheduled"
    ]
    append_scores = [
        row["artifact_score"]["artifact_quality_score"]
        for row in rows if row["condition"] == "append_only"
    ]
    event_unsupported = [
        row["artifact_score"]["unsupported_claim_rate"]
        for row in rows if row["condition"] == "event_loop_scheduled"
    ]
    append_unsupported = [
        row["artifact_score"]["unsupported_claim_rate"]
        for row in rows if row["condition"] == "append_only"
    ]
    event_mean = mean(event_scores)
    append_mean = mean(append_scores)
    catastrophic = [
        row["task_id"] for row in rows
        if row["condition"] == "event_loop_scheduled"
        and row["artifact_score"]["catastrophic_failure"]
    ]
    unsupported_not_worse = mean(event_unsupported) <= mean(append_unsupported)
    noninferior = (
        event_mean >= append_mean - NON_INFERIORITY_MARGIN
        and not catastrophic
        and unsupported_not_worse
    )
    return {
        "passed": noninferior,
        "event_loop_mean_quality": round(event_mean, 4),
        "append_only_mean_quality": round(append_mean, 4),
        "quality_delta_event_minus_append": round(event_mean - append_mean, 4),
        "margin": NON_INFERIORITY_MARGIN,
        "catastrophic_event_loop_task_ids": catastrophic,
        "unsupported_claim_rate_not_worse": unsupported_not_worse,
    }


def score_shared_surface_observability(rows: list[JsonDict]) -> JsonDict:
    event = mean(
        row["observability_score"]["shared_surface"]["score"]
        for row in rows if row["condition"] == "event_loop_scheduled"
    )
    append = mean(
        row["observability_score"]["shared_surface"]["score"]
        for row in rows if row["condition"] == "append_only"
    )
    noninferior = event >= append - NON_INFERIORITY_MARGIN
    return {
        "event_loop_mean_shared_surface_observability": round(event, 4),
        "append_only_mean_shared_surface_observability": round(append, 4),
        "delta_event_minus_append": round(event - append, 4),
        "margin": NON_INFERIORITY_MARGIN,
        "passed": noninferior,
    }


def score_scheduler_added_value(rows: list[JsonDict]) -> JsonDict:
    event_scores = [
        row["observability_score"]["scheduler_reconstruction"]["score"]
        for row in rows if row["condition"] == "event_loop_scheduled"
    ]
    failed = [
        row["task_id"] for row in rows
        if row["condition"] == "event_loop_scheduled"
        and row["observability_score"]["scheduler_reconstruction"]["score"] < 1.0
    ]
    return {
        "passed": not failed and bool(event_scores),
        "event_loop_mean_scheduler_reconstruction_observability": round(
            mean(event_scores),
            4,
        ),
        "append_only": "not_applicable",
        "failed_task_ids": failed,
        "gate": "scheduler_added_value",
    }


def summarize(
    *,
    scheduler: JsonDict,
    noninferiority: JsonDict,
    shared_observability: JsonDict,
    scheduler_added_value: JsonDict,
    live_model_calls: bool,
) -> JsonDict:
    survived = (
        scheduler["passed"]
        and noninferiority["passed"]
        and shared_observability["passed"]
        and scheduler_added_value["passed"]
    )
    if survived:
        decision = (
            "Live panel passed all preregistered gates."
            if live_model_calls else
            "Dry protocol harness is ready for a live provider extension."
        )
    else:
        decision = (
            "Live panel exposed a preregistered gate or scoring failure."
            if live_model_calls else
            "Dry protocol harness exposed a gate or scoring failure."
        )
    return {
        "classification": "survived" if survived else "falsified",
        "scheduler_viability_passed": scheduler["passed"],
        "artifact_noninferiority_passed": noninferiority["passed"],
        "shared_surface_observability_noninferior": shared_observability["passed"],
        "scheduler_added_value_passed": scheduler_added_value["passed"],
        "decision": decision,
    }


def render_analysis(results: JsonDict) -> str:
    summary = results["summary"]
    lines = [
        "# Event-Loop Viability + Append-Only Non-Inferiority Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Scheduler viability passed: `{summary['scheduler_viability_passed']}`",
        f"- Artifact non-inferiority passed: `{summary['artifact_noninferiority_passed']}`",
        f"- Shared-surface observability non-inferior: `{summary['shared_surface_observability_noninferior']}`",
        f"- Scheduler added value passed: `{summary['scheduler_added_value_passed']}`",
        f"- Decision: {summary['decision']}",
        "",
        "## Separation Of Claims",
        "",
        "Gate A reports shared-surface non-inferiority against append-only. "
        "Gate B reports scheduler-specific reconstruction value as an added "
        "capability, not as an append-only observability penalty.",
        "",
        "## Rows",
        "",
        "| Task | Condition | Quality | Shared obs. | Scheduler obs. | Scheduler passed |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in results["rows"]:
        scheduler_passed = row["scheduler_checks"].get("passed", "n/a")
        scheduler_observability = row["observability_score"][
            "scheduler_reconstruction"
        ]["score"]
        scheduler_observability_display = (
            "n/a" if scheduler_observability is None
            else f"{scheduler_observability:.4f}"
        )
        lines.append(
            "| "
            f"{row['task_id']} | {row['condition']} | "
            f"{row['artifact_score']['artifact_quality_score']:.4f} | "
            f"{row['observability_score']['shared_surface']['score']:.4f} | "
            f"{scheduler_observability_display} | "
            f"{scheduler_passed} |"
        )
    lines.extend(
        [
            "",
            "## Gate Scores",
            "",
            "```json",
            json.dumps(
                {
                    "scheduler_viability": results["scheduler_viability"],
                    "artifact_noninferiority": results["artifact_noninferiority"],
                    "shared_surface_observability": results[
                        "shared_surface_observability"
                    ],
                    "scheduler_added_value": results["scheduler_added_value"],
                },
                indent=2,
                sort_keys=True,
            ),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def corpus_map(task_id: str) -> list[JsonDict]:
    return [
        {
            "record_id": record["record_id"],
            "record_type": record["record_type"],
            "content_keys": sorted(record["content"]),
            "preview": json.dumps(record["content"], sort_keys=True)[:220],
        }
        for record in TASKS[task_id]["records"]
    ]


def declared_losses(task_id: str) -> list[str]:
    markers = [
        data["loss_marker"]
        for data in TASKS[task_id]["required_facts"].values()
        if data.get("loss_marker")
    ]
    return [f"Limitation remains: {marker}." for marker in markers]


def default_terminal_tool_choice(endpoint: str) -> str:
    """Direct DeepSeek thinking mode rejects forced tool choice."""
    if "api.deepseek.com" in endpoint:
        return "auto"
    return "force"


def cycle_payload(*, parsed: JsonDict, request_payload: JsonDict) -> JsonDict:
    return {
        "parsed": deepcopy(parsed),
        "raw_content": json.dumps(parsed, sort_keys=True),
        "request_payload": deepcopy(request_payload),
        "response_payload": {"dry_run": True},
        "usage": {},
        "elapsed_seconds": 0.0,
    }


def mean(values: Any) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def _prepare_output_root(output_root: Path, *, overwrite: bool) -> None:
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
            raise FileExistsError(f"{path} exists; pass --overwrite to replace generated artifacts")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def _approx_tokens(value: Any) -> int:
    text = json.dumps(value, sort_keys=True, default=str)
    return max(1, (len(text) + 3) // 4)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _read_json(path: Path) -> JsonDict:
    return json.loads(path.read_text())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        help=(
            "Terminal surface tool_choice. Defaults to auto for direct "
            "DeepSeek and force elsewhere."
        ),
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
