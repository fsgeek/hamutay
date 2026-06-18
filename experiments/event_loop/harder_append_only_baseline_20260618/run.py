"""Harder append-only baseline test for symbolic event-loop viability."""

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

EXPERIMENT_ID = "harder_append_only_baseline_20260618"
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

SYMBOLIC_RUN_PATH = (
    ROOT_DIR.parent
    / "event_loop_symbolic_append_only_noninferiority_20260618"
    / "run.py"
)
DEFAULT_ENDPOINT = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_API_KEY_ENV = "DEEPSEEK_API_KEY"
DEFAULT_MAX_TOKENS = 4096
NON_INFERIORITY_MARGIN = 0.10


def load_symbolic_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "symbolic_append_only_for_harder_baseline",
        SYMBOLIC_RUN_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {SYMBOLIC_RUN_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.EXPERIMENT_ID = EXPERIMENT_ID
    module.ROOT_DIR = ROOT_DIR
    module.DEFAULT_ENDPOINT = DEFAULT_ENDPOINT
    module.DEFAULT_MODEL = DEFAULT_MODEL
    module.DEFAULT_API_KEY_ENV = DEFAULT_API_KEY_ENV
    module.BASE.EXPERIMENT_ID = EXPERIMENT_ID
    module.BASE.DEFAULT_ENDPOINT = DEFAULT_ENDPOINT
    module.BASE.DEFAULT_MODEL = DEFAULT_MODEL
    return module


SYMBOLIC = load_symbolic_module()
TASKS = SYMBOLIC.TASKS
BASE = SYMBOLIC.BASE


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def prepare_output_root(output_root: Path, *, overwrite: bool) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for name in [
        "analysis.md",
        "budget.json",
        "failure_taxonomy.json",
        "matrix.json",
        "results.json",
        "rows",
    ]:
        path = output_root / name
        if not path.exists():
            continue
        if not overwrite:
            raise FileExistsError(f"{path} exists; pass --overwrite to replace")
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def loss_markers(task_id: str) -> list[str]:
    return [
        data["loss_marker"]
        for data in TASKS[task_id]["required_facts"].values()
        if data.get("loss_marker")
    ]


def add_declared_loss_contract(request: JsonDict, task_id: str) -> JsonDict:
    markers = loss_markers(task_id)
    if not markers:
        return request
    request = deepcopy(request)
    request["declared_loss_contract"] = {
        "required_exact_markers": markers,
        "instruction": (
            "Include each required exact marker in declared_losses, and ensure "
            "the recommendation is constrained by those limitations."
        ),
    }
    request["instruction"] = (
        str(request.get("instruction") or "")
        + " Include every declared_loss_contract.required_exact_markers value "
        "verbatim in declared_losses."
    )
    return request


def install_declared_loss_contract_patch() -> Any:
    original = BASE.live_artifact_request

    def patched_live_artifact_request(**kwargs: Any) -> JsonDict:
        request = original(**kwargs)
        return add_declared_loss_contract(request, kwargs["task_id"])

    BASE.live_artifact_request = patched_live_artifact_request
    return original


def restore_declared_loss_contract_patch(original: Any) -> None:
    BASE.live_artifact_request = original


def matrix(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "conditions": ["event_loop_scheduled", "append_only"],
        "append_only_baseline": "harder_one_shot_with_audit_checklist",
        "symbolic_contract": SYMBOLIC.SYMBOLIC_CONTRACT,
        "declared_loss_policy": "exact_marker_contract_required",
        "tasks": sorted(TASKS),
        "non_inferiority_margin": NON_INFERIORITY_MARGIN,
    }


def budget_manifest(*, live_model_calls: bool = False) -> JsonDict:
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "max_live_calls": len(TASKS) * 3 if live_model_calls else 0,
        "max_estimated_cost_usd": 5.0 if live_model_calls else 0.0,
        "output_cap_policy": (
            "Two symbolic event-loop calls plus one harder append-only call per task."
            if live_model_calls else
            "Dry mode uses deterministic event-loop and append-only rows."
        ),
    }


def failure_taxonomy() -> JsonDict:
    return {
        "schema_version": "hamutay.harder_append_only_taxonomy.v1",
        "layers": [
            "scheduler",
            "model",
            "provider",
            "prompt_rubric",
            "harness",
            "scorer",
            "protocol",
            "inconclusive",
        ],
        "entries": [
            {
                "layer": "model",
                "code": "event_loop_inferior_to_harder_append_only",
                "meaning": "Event-loop rows missed the non-inferiority margin.",
            },
            {
                "layer": "prompt_rubric",
                "code": "declared_loss_contract_not_preserved",
                "meaning": "A row omitted an exact declared-loss marker.",
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
        write_json(output_root / name, payload)
    return {
        "experiment_id": EXPERIMENT_ID,
        "live_model_calls": live_model_calls,
        "artifacts": sorted(artifacts),
        "preregistration": str(output_root / "PRE_REGISTRATION.md"),
    }


def strong_append_only_system_prompt() -> str:
    return (
        "You are the stronger append-only baseline for a preregistered "
        "comparison. You receive the full bounded corpus in one context. Before "
        "writing, audit every required fact, every citation, every declared-loss "
        "marker, distractor exclusion, and recommendation constraint. Return "
        "only the required terminal artifact."
    )


def stronger_append_only_request(task_id: str) -> JsonDict:
    request = BASE.live_artifact_request(
        task_id=task_id,
        condition="append_only",
        corpus=TASKS[task_id]["records"],
        carried_state=None,
        wake_context=None,
    )
    request = add_declared_loss_contract(request, task_id)
    request["append_only_baseline_strength"] = "harder_one_shot_with_audit_checklist"
    request["audit_checklist"] = [
        "Recover each required fact exactly once unless evidence is missing.",
        "Cite only evidence records that support the claim.",
        "Exclude distractor records from claims and citations.",
        "Include exact declared-loss markers when provided.",
        "Constrain recommended_action by declared losses.",
    ]
    request["instruction"] = (
        request["instruction"]
        + " Apply the audit_checklist before returning the artifact."
    )
    return request


def run_stronger_append_only_row(
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
    condition = "append_only"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    if not live_model_calls:
        row = BASE.run_append_only_row(task_id=task_id, output_root=output_root)
        row["baseline_strength"] = "harder_one_shot_with_audit_checklist"
        write_json(row_root / "row_result.json", row)
        return row

    from hamutay.taste_open import OpenAITasteBackend

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
    request = stronger_append_only_request(task_id)
    result = backend.call_terminal_surface(
        model=model,
        system=strong_append_only_system_prompt(),
        messages=[
            {
                "role": "user",
                "content": json.dumps(request, indent=2, sort_keys=True),
            }
        ],
        experiment_label=f"{EXPERIMENT_ID}_{task_id}_{condition}",
        terminal_surface=BASE.artifact_terminal_surface(
            tool_choice=terminal_tool_choice
        ),
    )
    cycle = {
        "parsed": BASE.normalize_artifact_output(result.raw_output),
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
    write_json(row_root / "cycle_01.json", cycle)
    artifact_score = BASE.score_artifact(task_id, cycle["parsed"])
    context_accounting = {
        "condition": condition,
        "task_id": task_id,
        "append_only_context_record_ids": [
            record["record_id"] for record in TASKS[task_id]["records"]
        ],
        "baseline_strength": "harder_one_shot_with_audit_checklist",
        "declared_loss_contract": request.get("declared_loss_contract"),
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
        "baseline_strength": "harder_one_shot_with_audit_checklist",
        "artifact": cycle["parsed"],
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
    }
    write_json(row_root / "context_accounting.json", context_accounting)
    write_json(row_root / "score.json", artifact_score)
    write_json(row_root / "observability_score.json", row["observability_score"])
    write_json(row_root / "row_result.json", row)
    return row


def classify_summary(
    *,
    scheduler: JsonDict,
    noninferiority: JsonDict,
    shared_observability: JsonDict,
    scheduler_added_value: JsonDict,
) -> JsonDict:
    survived = (
        scheduler["passed"]
        and noninferiority["passed"]
        and shared_observability["passed"]
        and scheduler_added_value["passed"]
    )
    catastrophic = bool(noninferiority["catastrophic_event_loop_task_ids"])
    narrowed = (
        not survived
        and not catastrophic
        and noninferiority["event_loop_mean_quality"] > 0
    )
    if survived:
        classification = "survived"
    elif narrowed:
        classification = "narrowed"
    else:
        classification = "falsified"
    return {
        "classification": classification,
        "scheduler_viability_passed": scheduler["passed"],
        "artifact_noninferiority_passed": noninferiority["passed"],
        "shared_surface_observability_noninferior": shared_observability["passed"],
        "scheduler_added_value_passed": scheduler_added_value["passed"],
        "decision": (
            "Event-loop remained non-inferior against the harder append-only baseline."
            if survived else
            "Event-loop did not cleanly survive the harder append-only baseline."
        ),
    }


def render_analysis(results: JsonDict) -> str:
    lines = [
        "# Harder Append-Only Baseline Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Event-loop mean quality: `{results['artifact_noninferiority']['event_loop_mean_quality']}`",
        f"- Harder append-only mean quality: `{results['artifact_noninferiority']['append_only_mean_quality']}`",
        f"- Quality delta: `{results['artifact_noninferiority']['quality_delta_event_minus_append']}`",
        "",
        "## Rows",
        "",
        "| Task | Condition | Quality | Declared loss | Unsupported |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in results["rows"]:
        score = row["artifact_score"]
        lines.append(
            "| "
            f"{row['task_id']} | {row['condition']} | "
            f"{score['artifact_quality_score']:.4f} | "
            f"{score['declared_loss_rate']:.4f} | "
            f"{score['unsupported_claim_rate']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Gates",
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
    write_preregistration_artifacts(output_root, live_model_calls=live_model_calls)
    resolved_tool_choice = terminal_tool_choice or BASE.default_terminal_tool_choice(
        endpoint
    )
    rows: list[JsonDict] = []
    patch = install_declared_loss_contract_patch()
    try:
        for task_id in TASKS:
            rows.append(
                SYMBOLIC.run_symbolic_event_loop_row(
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
            rows.append(
                run_stronger_append_only_row(
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
    finally:
        restore_declared_loss_contract_patch(patch)

    scheduler = BASE.score_scheduler_viability(rows)
    noninferiority = BASE.score_noninferiority(rows)
    shared_observability = BASE.score_shared_surface_observability(rows)
    scheduler_added_value = BASE.score_scheduler_added_value(rows)
    summary = classify_summary(
        scheduler=scheduler,
        noninferiority=noninferiority,
        shared_observability=shared_observability,
        scheduler_added_value=scheduler_added_value,
    )
    results = {
        "schema_version": "hamutay.harder_append_only_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "started_at": utc_now_iso(),
        "finished_at": utc_now_iso(),
        "live_model_calls": live_model_calls,
        "endpoint": endpoint if live_model_calls else None,
        "model": model if live_model_calls else None,
        "terminal_tool_choice": resolved_tool_choice if live_model_calls else None,
        "classification": summary["classification"],
        "rows": rows,
        "scheduler_viability": scheduler,
        "artifact_noninferiority": noninferiority,
        "shared_surface_observability": shared_observability,
        "scheduler_added_value": scheduler_added_value,
        "summary": summary,
    }
    write_json(output_root / "results.json", results)
    (output_root / "analysis.md").write_text(render_analysis(results), encoding="utf-8")
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
        write_preregistration_artifacts(args.output_root, live_model_calls=args.live)
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
